"""OTel instrumentation for the A2A-SE Settlement Exchange.

Wraps key exchange operations (escrow create, deliver, release, refund,
dispute, resolve) with provenance-aware spans.  When provenance data is
present on a delivery, it maps the exchange's ``Provenance`` schema to
OTel attributes.

Usage::

    from otel_agent_provenance.instruments.settlement_exchange import (
        ExchangeInstrumentor,
        trace_escrow_lifecycle,
    )

    instrumentor = ExchangeInstrumentor(agent_id="exchange-node-1")
    instrumentor.instrument(app)  # FastAPI app
"""

from __future__ import annotations

from typing import Any, Sequence

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode, Tracer

from otel_agent_provenance.conventions import (
    AcceptanceAttributes,
    ProvenanceAttributes,
    SourceType,
)

_TRACER_NAME = "otel_agent_provenance.settlement_exchange"


def trace_escrow_create(
    span: Span,
    *,
    agent_id: str,
    escrow_id: str,
    requester_id: str,
    provider_id: str,
    amount: float,
    task_id: str | None = None,
    required_attestation_level: str | None = None,
) -> None:
    """Enrich a span with escrow creation attributes."""
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
    span.set_attribute("settlement.escrow.id", escrow_id)
    span.set_attribute("settlement.escrow.requester_id", requester_id)
    span.set_attribute("settlement.escrow.provider_id", provider_id)
    span.set_attribute("settlement.escrow.amount", amount)
    if task_id:
        span.set_attribute(AcceptanceAttributes.TASK_ID, task_id)
    if required_attestation_level:
        tier_map = {"self_declared": 1, "signed": 2, "verifiable": 3}
        tier = tier_map.get(required_attestation_level, 1)
        span.set_attribute(ProvenanceAttributes.OUTPUT_PROVENANCE_TIER, tier)


def trace_delivery(
    span: Span,
    *,
    agent_id: str,
    escrow_id: str,
    provenance: dict[str, Any] | None = None,
    content_hash: str | None = None,
) -> None:
    """Enrich a span with delivery and provenance attributes.

    Maps the exchange's ``Provenance`` schema (source_type, source_refs,
    attestation_level, signature, grounding_metadata) to OTel attributes.
    """
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
    span.set_attribute("settlement.escrow.id", escrow_id)

    if content_hash:
        parts = content_hash.split(":", 1)
        if len(parts) == 2:
            span.set_attribute(ProvenanceAttributes.OUTPUT_HASH_ALGORITHM, parts[0])
            span.set_attribute(ProvenanceAttributes.OUTPUT_HASH_VALUE, parts[1])

    if not provenance:
        span.set_attribute(ProvenanceAttributes.OUTPUT_PROVENANCE_TIER, 1)
        return

    source_type = provenance.get("source_type", "generated")
    type_map = {
        "web": SourceType.RETRIEVAL,
        "api": SourceType.TOOL_CALL,
        "database": SourceType.RETRIEVAL,
        "generated": SourceType.MODEL_GENERATION,
        "hybrid": SourceType.HYBRID,
    }
    span.set_attribute(
        ProvenanceAttributes.OUTPUT_SOURCE_TYPE,
        type_map.get(source_type, SourceType.HYBRID),
    )

    attestation = provenance.get("attestation_level", "self_declared")
    tier_map = {"self_declared": 1, "signed": 2, "verifiable": 3}
    span.set_attribute(
        ProvenanceAttributes.OUTPUT_PROVENANCE_TIER,
        tier_map.get(attestation, 1),
    )

    source_refs = provenance.get("source_refs", [])
    uris = [ref.get("uri", "") for ref in source_refs if ref.get("uri")]
    if uris:
        span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_URI, uris)

    signature = provenance.get("signature")
    if signature:
        span.set_attribute(ProvenanceAttributes.OUTPUT_SIGNATURE_VALUE, signature)

    gm = provenance.get("grounding_metadata")
    if gm:
        coverage = gm.get("coverage")
        if coverage is not None:
            span.set_attribute(
                ProvenanceAttributes.OUTPUT_GROUNDING_COVERAGE, float(coverage)
            )
        chunks = gm.get("chunks", [])
        span.set_attribute(
            ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT, len(chunks)
        )


def trace_resolution(
    span: Span,
    *,
    agent_id: str,
    escrow_id: str,
    resolution: str,
    provenance_result: dict[str, Any] | None = None,
) -> None:
    """Enrich a span with dispute resolution attributes."""
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
    span.set_attribute("settlement.escrow.id", escrow_id)
    span.set_attribute("settlement.resolution", resolution)

    if provenance_result:
        verified = provenance_result.get("verified", False)
        confidence = provenance_result.get("confidence", 0.0)
        tier = provenance_result.get("tier", "self_declared")

        span.set_attribute(ProvenanceAttributes.OUTPUT_CONFIDENCE, confidence)
        span.set_attribute(
            ProvenanceAttributes.OUTPUT_PROVENANCE_TIER,
            {"self_declared": 1, "signed": 2, "verifiable": 3}.get(tier, 1),
        )

        flags = provenance_result.get("flags", [])
        if flags:
            span.set_attribute("settlement.provenance.flags", flags)


def trace_escrow_lifecycle(
    span: Span,
    *,
    agent_id: str,
    escrow_id: str,
    operation: str,
    status: str | None = None,
    amount: float | None = None,
) -> None:
    """Generic escrow lifecycle span enrichment (release, refund, dispute)."""
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
    span.set_attribute("settlement.escrow.id", escrow_id)
    span.set_attribute("settlement.operation", operation)
    if status:
        span.set_attribute("settlement.escrow.status", status)
    if amount is not None:
        span.set_attribute("settlement.escrow.amount", amount)


class ExchangeInstrumentor:
    """Auto-instruments a FastAPI exchange app with provenance spans.

    Wraps settlement route handlers to emit spans with provenance
    attributes.  Designed to be added to the ``a2a-settlement`` exchange.
    """

    def __init__(
        self,
        *,
        agent_id: str = "settlement-exchange",
        tracer: Tracer | None = None,
    ):
        self._agent_id = agent_id
        self._tracer = tracer or trace.get_tracer(_TRACER_NAME)

    def instrument(self, app: Any) -> None:
        """Add OTel middleware to a FastAPI app.

        This adds a middleware that creates provenance-enriched spans
        for settlement API endpoints.
        """
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        instrumentor = self

        class _SettlementOTelMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next: Any) -> Response:
                path = request.url.path
                if not path.startswith("/exchange/") and not path.startswith("/api/v1/"):
                    return await call_next(request)

                operation = path.rsplit("/", 1)[-1]
                with instrumentor._tracer.start_as_current_span(
                    f"settlement.{operation}",
                    attributes={
                        ProvenanceAttributes.AGENT_ID: instrumentor._agent_id,
                        "settlement.operation": operation,
                        "http.method": request.method,
                        "http.url": str(request.url),
                    },
                ) as span:
                    try:
                        response = await call_next(request)
                        span.set_attribute("http.status_code", response.status_code)
                        if response.status_code >= 400:
                            span.set_status(StatusCode.ERROR)
                        return response
                    except Exception as exc:
                        span.set_status(StatusCode.ERROR, str(exc))
                        span.record_exception(exc)
                        raise

        app.add_middleware(_SettlementOTelMiddleware)
