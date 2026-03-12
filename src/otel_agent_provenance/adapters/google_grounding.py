"""Adapter: Google Vertex AI / ADK grounding metadata -> OTel provenance spans.

Translates Gemini's ``groundingChunks``, ``groundingSupports``, and
``groundingMetadata`` into ``agent.output.*`` and ``agent.provenance.*``
OTel attributes.

This is the "mechanical adapter" -- Google's structured grounding metadata
maps almost 1:1 to the provenance convention.  ~200 lines to bridge the
entire Google AI stack into the OTel provenance ecosystem.

Usage::

    from otel_agent_provenance.adapters.google_grounding import (
        extract_grounding_attributes,
        enrich_span_from_grounding,
    )

    # From raw Gemini response
    attrs = extract_grounding_attributes(gemini_response)

    # Or from an ADK GroundingResult dict (adk-a2a-settlement format)
    attrs = from_adk_provenance(provenance_dict)

    # Apply to any span
    enrich_span_from_grounding(span, attrs)
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from opentelemetry.trace import Span

from otel_agent_provenance.conventions import (
    CallbackStatus,
    ProvenanceAttributes,
    SourceInfluence,
    SourceType,
)


def extract_grounding_attributes(
    response: Any,
    *,
    agent_id: str = "",
    model_name: str = "",
) -> dict[str, Any]:
    """Extract provenance attributes from a Gemini ``GenerateContentResponse``.

    Navigates ``response.candidates[0].grounding_metadata`` to pull out
    chunks, supports, coverage, and search queries.

    Returns:
        Dict of OTel attribute key -> value, ready for ``span.set_attribute()``.
    """
    attrs: dict[str, Any] = {}

    if agent_id:
        attrs[ProvenanceAttributes.AGENT_ID] = agent_id
    if model_name:
        attrs[ProvenanceAttributes.OUTPUT_MODEL_NAME] = model_name

    attrs[ProvenanceAttributes.OUTPUT_SOURCE_TYPE] = SourceType.RETRIEVAL
    attrs[ProvenanceAttributes.OUTPUT_PROVENANCE_TIER] = 1

    metadata = _get_grounding_metadata(response)
    if metadata is None:
        return attrs

    chunks = getattr(metadata, "grounding_chunks", None) or []
    supports = getattr(metadata, "grounding_supports", None) or []

    uris: list[str] = []
    domains: set[str] = set()
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        if web:
            uri = getattr(web, "uri", "")
            if uri:
                uris.append(uri)
                try:
                    netloc = urlparse(uri).netloc
                    if netloc:
                        domains.add(netloc)
                except Exception:
                    pass

    if uris:
        attrs[ProvenanceAttributes.OUTPUT_SOURCE_URI] = uris
        attrs[ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE] = SourceInfluence.CITED

    attrs[ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT] = len(uris)
    attrs[ProvenanceAttributes.OUTPUT_GROUNDING_DOMAIN_COUNT] = len(domains)

    grounded_text = _get_grounded_text(response)
    coverage = _compute_coverage(grounded_text, supports)
    attrs[ProvenanceAttributes.OUTPUT_GROUNDING_COVERAGE] = round(coverage, 4)

    if coverage >= 0.5 and len(domains) >= 2:
        attrs[ProvenanceAttributes.OUTPUT_PROVENANCE_TIER] = 1
        attrs[ProvenanceAttributes.OUTPUT_CONFIDENCE] = min(0.85, 0.5 + coverage * 0.4)
    elif coverage >= 0.3:
        attrs[ProvenanceAttributes.OUTPUT_CONFIDENCE] = 0.5 + coverage * 0.3

    return attrs


def from_adk_provenance(
    provenance: dict[str, Any],
    *,
    agent_id: str = "",
) -> dict[str, Any]:
    """Convert an ADK ``build_grounded_provenance()`` dict to OTel attributes.

    This bridges the ``adk-a2a-settlement/grounding.py`` output format
    into the provenance convention.
    """
    attrs: dict[str, Any] = {}

    if agent_id:
        attrs[ProvenanceAttributes.AGENT_ID] = agent_id

    source_type = provenance.get("source_type", "web")
    type_map = {
        "web": SourceType.RETRIEVAL,
        "api": SourceType.TOOL_CALL,
        "database": SourceType.RETRIEVAL,
        "generated": SourceType.MODEL_GENERATION,
        "hybrid": SourceType.HYBRID,
    }
    attrs[ProvenanceAttributes.OUTPUT_SOURCE_TYPE] = type_map.get(
        source_type, SourceType.HYBRID
    )

    attestation = provenance.get("attestation_level", "self_declared")
    tier_map = {"self_declared": 1, "signed": 2, "verifiable": 3}
    attrs[ProvenanceAttributes.OUTPUT_PROVENANCE_TIER] = tier_map.get(attestation, 1)

    source_refs = provenance.get("source_refs", [])
    uris = [ref["uri"] for ref in source_refs if ref.get("uri")]
    if uris:
        attrs[ProvenanceAttributes.OUTPUT_SOURCE_URI] = uris
        attrs[ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE] = SourceInfluence.CITED

    gm = provenance.get("grounding_metadata") or {}
    chunks = gm.get("chunks", [])
    coverage = gm.get("coverage", 0.0)

    domains: set[str] = set()
    for chunk in chunks:
        uri = chunk.get("uri", "")
        try:
            netloc = urlparse(uri).netloc
            if netloc:
                domains.add(netloc)
        except Exception:
            pass

    attrs[ProvenanceAttributes.OUTPUT_GROUNDING_COVERAGE] = round(coverage, 4)
    attrs[ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT] = len(chunks)
    attrs[ProvenanceAttributes.OUTPUT_GROUNDING_DOMAIN_COUNT] = len(domains)

    if attestation == "verifiable" and uris:
        attrs[ProvenanceAttributes.CALLBACK_URI] = uris[0]
        attrs[ProvenanceAttributes.CALLBACK_METHOD] = "GET"
        attrs[ProvenanceAttributes.CALLBACK_STATUS] = CallbackStatus.VERIFIED

    return attrs


def enrich_span_from_grounding(span: Span, attrs: dict[str, Any]) -> None:
    """Apply extracted grounding attributes to an OTel span."""
    for key, value in attrs.items():
        if value is not None:
            span.set_attribute(key, value)


def _get_grounding_metadata(response: Any) -> Any | None:
    candidates = getattr(response, "candidates", None)
    if not candidates:
        return None
    return getattr(candidates[0], "grounding_metadata", None)


def _get_grounded_text(response: Any) -> str:
    candidates = getattr(response, "candidates", None)
    if not candidates:
        return ""
    candidate = candidates[0]
    content = getattr(candidate, "content", None)
    if not content:
        return ""
    parts = getattr(content, "parts", None) or []
    return "".join(
        getattr(part, "text", "") for part in parts if hasattr(part, "text")
    )


def _compute_coverage(text: str, supports: list[Any]) -> float:
    if not text or not supports:
        return 0.0
    text_len = len(text)
    covered = bytearray(text_len)
    for support in supports:
        segment = getattr(support, "segment", None)
        if segment is None:
            continue
        start = max(0, min(getattr(segment, "start_index", 0), text_len))
        end = max(start, min(getattr(segment, "end_index", 0), text_len))
        for i in range(start, end):
            covered[i] = 1
    return sum(covered) / text_len
