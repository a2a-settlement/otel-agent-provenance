"""Span builders for federation events: peering, VC import, Trust Discount, health checks.

Provides exchange-agnostic provenance attributes for cross-exchange attestation
flows. Use FederationSpan as a context manager for peering handshakes, VC
imports, Trust Discount evaluation, and health check events.

Usage::

    from otel_agent_provenance.federation import FederationSpan

    with FederationSpan.peering(tracer, peer_did="did:web:exchange.example.com"):
        do_peering_handshake()

    with FederationSpan.vc_import(
        tracer,
        peer_did="did:web:other.org",
        attestation_type="reputation",
        source_exchange_did="did:web:other.org",
        rho=0.15,
    ) as span:
        result = import_vcs(...)
        span.set_import_result(imported=3, rejected=0)
"""

from __future__ import annotations

import contextlib
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode, Tracer

from otel_agent_provenance.conventions import FederationAttributes

_TRACER_NAME = "otel_agent_provenance"


def _set_if(span: Span, key: str, value: Any) -> None:
    if value is not None:
        span.set_attribute(key, value)


class FederationSpan:
    """Context manager for federation events: peering, VC import, Trust Discount, health check.

    Supports four event types via class methods:
    - peering: Mutual cryptographic peering handshake
    - vc_import: Import of cross-exchange attestation VCs
    - trust_discount: Trust Discount (rho) evaluation
    - health_check: Federation health check
    """

    def __init__(
        self,
        tracer: Tracer | None = None,
        *,
        name: str,
        peer_did: str | None = None,
        rho: float | None = None,
        algorithm_id: str | None = None,
        health_status: str | None = None,
        attestation_type: str | None = None,
        source_exchange_did: str | None = None,
    ):
        self._tracer = tracer or trace.get_tracer(_TRACER_NAME)
        self._name = name
        self._attrs: dict[str, Any] = {}

        _map = {
            FederationAttributes.PEER_DID: peer_did,
            FederationAttributes.RHO: rho,
            FederationAttributes.ALGORITHM_ID: algorithm_id,
            FederationAttributes.HEALTH_STATUS: health_status,
            FederationAttributes.ATTESTATION_TYPE: attestation_type,
            FederationAttributes.SOURCE_EXCHANGE_DID: source_exchange_did,
        }
        for key, val in _map.items():
            if val is not None:
                self._attrs[key] = val

        self._span: Span | None = None

    def __enter__(self) -> FederationSpan:
        self._span = self._tracer.start_span(self._name, attributes=self._attrs)
        ctx = trace.set_span_in_context(self._span)
        self._token = contextlib.suppress(Exception) and trace.context_api.attach(ctx)
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, tb: Any) -> bool:
        if self._span is not None:
            if exc_type is not None:
                self._span.set_status(StatusCode.ERROR, str(exc_val))
                self._span.record_exception(exc_val)
            else:
                self._span.set_status(StatusCode.OK)
            self._span.end()
        if hasattr(self, "_token") and self._token:
            with contextlib.suppress(Exception):
                trace.context_api.detach(self._token)
        return False

    @property
    def span(self) -> Span | None:
        return self._span

    def set_import_result(
        self,
        *,
        imported: int | None = None,
        rejected: int | None = None,
    ) -> None:
        """Set VC import result counts on the span."""
        if self._span is None:
            return
        _set_if(self._span, "agent.federation.import.imported", imported)
        _set_if(self._span, "agent.federation.import.rejected", rejected)

    def set_rho(self, rho: float) -> None:
        """Set the Trust Discount rho on the span."""
        if self._span is not None:
            self._span.set_attribute(FederationAttributes.RHO, rho)

    def set_health_status(self, status: str) -> None:
        """Set the health status on the span."""
        if self._span is not None:
            self._span.set_attribute(FederationAttributes.HEALTH_STATUS, status)

    @classmethod
    def peering(
        cls,
        tracer: Tracer | None = None,
        *,
        peer_did: str,
        algorithm_id: str | None = None,
        rho: float | None = None,
    ) -> FederationSpan:
        """Create a span for a federation peering handshake."""
        return cls(
            tracer=tracer,
            name="agent.federation.peering",
            peer_did=peer_did,
            algorithm_id=algorithm_id,
            rho=rho,
        )

    @classmethod
    def vc_import(
        cls,
        tracer: Tracer | None = None,
        *,
        peer_did: str | None = None,
        attestation_type: str | None = None,
        source_exchange_did: str | None = None,
        rho: float | None = None,
    ) -> FederationSpan:
        """Create a span for importing cross-exchange attestation VCs."""
        return cls(
            tracer=tracer,
            name="agent.federation.vc_import",
            peer_did=peer_did,
            attestation_type=attestation_type,
            source_exchange_did=source_exchange_did,
            rho=rho,
        )

    @classmethod
    def trust_discount(
        cls,
        tracer: Tracer | None = None,
        *,
        peer_did: str,
        rho: float,
        algorithm_id: str | None = None,
    ) -> FederationSpan:
        """Create a span for Trust Discount (rho) evaluation."""
        return cls(
            tracer=tracer,
            name="agent.federation.trust_discount",
            peer_did=peer_did,
            rho=rho,
            algorithm_id=algorithm_id,
        )

    @classmethod
    def health_check(
        cls,
        tracer: Tracer | None = None,
        *,
        peer_did: str,
        health_status: str,
    ) -> FederationSpan:
        """Create a span for a federation health check."""
        return cls(
            tracer=tracer,
            name="agent.federation.health_check",
            peer_did=peer_did,
            health_status=health_status,
        )

    @staticmethod
    def enrich(
        span: Span,
        *,
        peer_did: str | None = None,
        rho: float | None = None,
        algorithm_id: str | None = None,
        health_status: str | None = None,
        attestation_type: str | None = None,
        source_exchange_did: str | None = None,
    ) -> None:
        """Set federation attributes on an existing span."""
        _set_if(span, FederationAttributes.PEER_DID, peer_did)
        _set_if(span, FederationAttributes.RHO, rho)
        _set_if(span, FederationAttributes.ALGORITHM_ID, algorithm_id)
        _set_if(span, FederationAttributes.HEALTH_STATUS, health_status)
        _set_if(span, FederationAttributes.ATTESTATION_TYPE, attestation_type)
        _set_if(span, FederationAttributes.SOURCE_EXCHANGE_DID, source_exchange_did)
