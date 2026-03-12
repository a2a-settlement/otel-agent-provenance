"""Adapter: Semantic Kernel RAG plugin -> OTel provenance spans.

Semantic Kernel has plugin hooks where retrieval instrumentation can be
injected, but nobody has defined *what* to capture.  This adapter
provides a ``KernelFilter`` that intercepts Semantic Kernel function
invocations and annotates spans with provenance attributes when RAG
plugins are detected.

Usage::

    from otel_agent_provenance.adapters.semantic_kernel_rag import (
        ProvenanceFilter,
        trace_kernel_rag,
    )

    # Option 1: As a Kernel filter (auto-instruments all RAG plugins)
    kernel.add_filter(ProvenanceFilter(agent_id="agent-sk-001"))

    # Option 2: Manual enrichment of an existing span
    trace_kernel_rag(
        span,
        agent_id="agent-sk-001",
        retrieved_uris=["https://..."],
        attended_uris=["https://..."],
        model_name="gpt-4o",
    )
"""

from __future__ import annotations

from typing import Any, Sequence
from urllib.parse import urlparse

from opentelemetry import trace
from opentelemetry.trace import Span

from otel_agent_provenance.conventions import (
    ProvenanceAttributes,
    SourceInfluence,
    SourceType,
)


RAG_PLUGIN_NAMES = frozenset({
    "TextMemoryPlugin",
    "SearchPlugin",
    "AzureAISearchPlugin",
    "VectorStorePlugin",
    "SemanticTextMemory",
    "VolatileMemoryStore",
    "AzureCognitiveSearchMemoryStore",
    "QdrantMemoryStore",
    "ChromaMemoryStore",
    "PineconeMemoryStore",
})

RAG_FUNCTION_NAMES = frozenset({
    "recall",
    "search",
    "retrieve",
    "query",
    "get_relevant",
    "get_nearest_matches",
    "search_async",
    "recall_async",
})


class ProvenanceFilter:
    """Semantic Kernel filter that enriches spans with provenance attributes.

    Detects RAG-related plugin invocations by plugin/function name and
    annotates the current OTel span with ``agent.output.source.*`` and
    ``agent.output.grounding.*`` attributes.

    This is designed to work with Semantic Kernel's ``IFunctionFilter``
    pattern.  Register it via ``kernel.add_filter()``.
    """

    def __init__(self, *, agent_id: str = ""):
        self._agent_id = agent_id

    async def on_function_invoking(self, context: Any) -> None:
        plugin_name = getattr(context, "function_name", "") or ""
        function_name = ""

        fn = getattr(context, "function", None)
        if fn:
            plugin_name = getattr(fn, "plugin_name", plugin_name) or plugin_name
            function_name = getattr(fn, "name", "") or ""

        if not self._is_rag_invocation(plugin_name, function_name):
            return

        span = trace.get_current_span()
        if not span.is_recording():
            return

        span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_TYPE, SourceType.RETRIEVAL)
        if self._agent_id:
            span.set_attribute(ProvenanceAttributes.AGENT_ID, self._agent_id)
        span.set_attribute(ProvenanceAttributes.OUTPUT_PROVENANCE_TIER, 1)

    async def on_function_invoked(self, context: Any) -> None:
        plugin_name = getattr(context, "function_name", "") or ""
        function_name = ""

        fn = getattr(context, "function", None)
        if fn:
            plugin_name = getattr(fn, "plugin_name", plugin_name) or plugin_name
            function_name = getattr(fn, "name", "") or ""

        if not self._is_rag_invocation(plugin_name, function_name):
            return

        span = trace.get_current_span()
        if not span.is_recording():
            return

        result = getattr(context, "result", None)
        if result is None:
            return

        uris = self._extract_uris_from_result(result)
        if uris:
            span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_URI, uris)
            span.set_attribute(
                ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE, SourceInfluence.ATTENDED
            )
            span.set_attribute(
                ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT, len(uris)
            )
            domains = set()
            for uri in uris:
                try:
                    netloc = urlparse(uri).netloc
                    if netloc:
                        domains.add(netloc)
                except Exception:
                    pass
            span.set_attribute(
                ProvenanceAttributes.OUTPUT_GROUNDING_DOMAIN_COUNT, len(domains)
            )

    @staticmethod
    def _is_rag_invocation(plugin_name: str, function_name: str) -> bool:
        if plugin_name in RAG_PLUGIN_NAMES:
            return True
        if function_name.lower() in RAG_FUNCTION_NAMES:
            return True
        lower_plugin = plugin_name.lower()
        return any(
            kw in lower_plugin for kw in ("search", "memory", "retriev", "vector", "rag")
        )

    @staticmethod
    def _extract_uris_from_result(result: Any) -> list[str]:
        uris: list[str] = []

        value = getattr(result, "value", result)

        if isinstance(value, str):
            return uris

        if isinstance(value, (list, tuple)):
            for item in value:
                uri = _extract_uri_from_item(item)
                if uri:
                    uris.append(uri)

        if hasattr(value, "results"):
            for item in value.results:
                uri = _extract_uri_from_item(item)
                if uri:
                    uris.append(uri)

        return uris


def _extract_uri_from_item(item: Any) -> str:
    for attr in ("uri", "url", "source", "link", "metadata"):
        val = getattr(item, attr, None)
        if isinstance(val, str) and val.startswith(("http://", "https://")):
            return val
        if isinstance(val, dict):
            for key in ("uri", "url", "source", "link"):
                nested = val.get(key)
                if isinstance(nested, str) and nested.startswith(("http://", "https://")):
                    return nested
    if isinstance(item, dict):
        for key in ("uri", "url", "source", "link"):
            val = item.get(key)
            if isinstance(val, str) and val.startswith(("http://", "https://")):
                return val
    return ""


def trace_kernel_rag(
    span: Span,
    *,
    agent_id: str,
    retrieved_uris: Sequence[str] | None = None,
    attended_uris: Sequence[str] | None = None,
    cited_uris: Sequence[str] | None = None,
    model_name: str | None = None,
    coverage: float | None = None,
    confidence: float | None = None,
) -> None:
    """One-shot enrichment of a Semantic Kernel span with RAG provenance.

    Call this after a Semantic Kernel pipeline completes to annotate the
    span with which sources were retrieved, attended to, and cited.
    """
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
    span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_TYPE, SourceType.HYBRID)
    span.set_attribute(ProvenanceAttributes.OUTPUT_PROVENANCE_TIER, 1)

    final_uris = cited_uris or attended_uris or retrieved_uris
    if final_uris:
        span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_URI, list(final_uris))

    if cited_uris:
        span.set_attribute(
            ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE, SourceInfluence.CITED
        )
    elif attended_uris:
        span.set_attribute(
            ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE, SourceInfluence.ATTENDED
        )

    all_uris = set(retrieved_uris or []) | set(attended_uris or []) | set(cited_uris or [])
    span.set_attribute(
        ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT, len(all_uris)
    )

    domains: set[str] = set()
    for uri in all_uris:
        try:
            netloc = urlparse(uri).netloc
            if netloc:
                domains.add(netloc)
        except Exception:
            pass
    span.set_attribute(
        ProvenanceAttributes.OUTPUT_GROUNDING_DOMAIN_COUNT, len(domains)
    )

    if model_name:
        span.set_attribute(ProvenanceAttributes.OUTPUT_MODEL_NAME, model_name)
    if coverage is not None:
        span.set_attribute(ProvenanceAttributes.OUTPUT_GROUNDING_COVERAGE, coverage)
    if confidence is not None:
        span.set_attribute(ProvenanceAttributes.OUTPUT_CONFIDENCE, confidence)
