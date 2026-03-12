"""OTel instrumentation for the A2A-SE Security Shim (Economic Air Gap).

The Security Shim is a forward proxy that gates tool access on escrow
balance and injects credentials.  This instrumentor traces the shim's
request flow:

1. Tool/destination resolution
2. Policy validation (allow/deny)
3. Escrow balance check and deduction
4. Credential injection (secret_id -> real credential)
5. Upstream request
6. Audit entry

Each step becomes a child span with provenance attributes showing how
the Economic Air Gap mediates between agents and external systems.

Usage::

    from otel_agent_provenance.instruments.settlement_shim import (
        ShimInstrumentor,
        trace_shim_request,
    )

    instrumentor = ShimInstrumentor(agent_id="shim-node-1")
    instrumentor.instrument(app)
"""

from __future__ import annotations

from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode, Tracer

from otel_agent_provenance.conventions import (
    ProvenanceAttributes,
    SourceType,
)

_TRACER_NAME = "otel_agent_provenance.settlement_shim"


def trace_shim_request(
    span: Span,
    *,
    agent_id: str,
    escrow_id: str | None = None,
    tool_id: str | None = None,
    destination_url: str | None = None,
    mode: str = "full_air_gap",
    cost: float | None = None,
    status_code: int | None = None,
) -> None:
    """Enrich a span with shim request attributes."""
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
    span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_TYPE, SourceType.TOOL_CALL)
    span.set_attribute("settlement.shim.mode", mode)

    if escrow_id:
        span.set_attribute("settlement.escrow.id", escrow_id)
    if tool_id:
        span.set_attribute("settlement.shim.tool_id", tool_id)
    if destination_url:
        span.set_attribute("settlement.shim.destination_url", destination_url)
    if cost is not None:
        span.set_attribute("settlement.shim.cost", cost)
    if status_code is not None:
        span.set_attribute("http.status_code", status_code)


def trace_policy_check(
    span: Span,
    *,
    destination: str,
    allowed: bool,
    policy_name: str | None = None,
) -> None:
    """Record a policy validation result on a span."""
    span.set_attribute("settlement.shim.policy.destination", destination)
    span.set_attribute("settlement.shim.policy.allowed", allowed)
    if policy_name:
        span.set_attribute("settlement.shim.policy.name", policy_name)
    if not allowed:
        span.set_status(StatusCode.ERROR, "Policy denied")


def trace_escrow_deduction(
    span: Span,
    *,
    escrow_id: str,
    cost: float,
    remaining_balance: float | None = None,
    success: bool = True,
) -> None:
    """Record an escrow balance deduction on a span."""
    span.set_attribute("settlement.escrow.id", escrow_id)
    span.set_attribute("settlement.shim.cost", cost)
    if remaining_balance is not None:
        span.set_attribute("settlement.shim.remaining_balance", remaining_balance)
    span.set_attribute("settlement.shim.deduction_success", success)
    if not success:
        span.set_status(StatusCode.ERROR, "Insufficient escrow balance")


def trace_credential_injection(
    span: Span,
    *,
    secret_id: str,
    resolved: bool = True,
) -> None:
    """Record credential resolution (without exposing the credential).

    Only records that a secret_id was resolved, never the credential value.
    """
    span.set_attribute("settlement.shim.secret_id", secret_id)
    span.set_attribute("settlement.shim.credential_resolved", resolved)
    if not resolved:
        span.set_status(StatusCode.ERROR, "Credential resolution failed")


class ShimInstrumentor:
    """Auto-instruments a FastAPI shim app with provenance spans."""

    def __init__(
        self,
        *,
        agent_id: str = "settlement-shim",
        tracer: Tracer | None = None,
    ):
        self._agent_id = agent_id
        self._tracer = tracer or trace.get_tracer(_TRACER_NAME)

    def instrument(self, app: Any) -> None:
        """Add OTel middleware to a FastAPI shim app."""
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        instrumentor = self

        class _ShimOTelMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next: Any) -> Response:
                path = request.url.path
                if not path.startswith("/proxy") and not path.startswith("/tools"):
                    return await call_next(request)

                with instrumentor._tracer.start_as_current_span(
                    "settlement.shim.proxy",
                    attributes={
                        ProvenanceAttributes.AGENT_ID: instrumentor._agent_id,
                        ProvenanceAttributes.OUTPUT_SOURCE_TYPE: SourceType.TOOL_CALL,
                        "settlement.shim.mode": "full_air_gap",
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

        app.add_middleware(_ShimOTelMiddleware)
