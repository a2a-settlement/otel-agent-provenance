"""OTel instrumentation for A2A-SE Evidence API operations.

Wraps evidence submission, evidence window expiry, and default judgment
events with provenance-aware spans.

Usage::

    from otel_agent_provenance.instruments.settlement_evidence import (
        trace_evidence_submission,
        trace_evidence_window_expiry,
        trace_default_judgment,
    )
"""

from __future__ import annotations

from opentelemetry.trace import Span

from otel_agent_provenance.conventions import EvidenceAttributes, ProvenanceAttributes


def trace_evidence_submission(
    span: Span,
    *,
    agent_id: str,
    escrow_id: str,
    submitter_id: str,
    evidence_type: str,
    artifact_count: int = 0,
    encrypted: bool = False,
    attestor_id: str | None = None,
    content_hash: str | None = None,
) -> None:
    """Enrich a span with evidence submission attributes."""
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
    span.set_attribute(EvidenceAttributes.EVIDENCE_ESCROW_ID, escrow_id)
    span.set_attribute(EvidenceAttributes.EVIDENCE_SUBMITTER_ID, submitter_id)
    span.set_attribute(EvidenceAttributes.EVIDENCE_TYPE, evidence_type)
    span.set_attribute(EvidenceAttributes.EVIDENCE_ARTIFACT_COUNT, artifact_count)
    span.set_attribute(EvidenceAttributes.EVIDENCE_ENCRYPTED, encrypted)
    if attestor_id:
        span.set_attribute(EvidenceAttributes.EVIDENCE_ATTESTOR_ID, attestor_id)
    if content_hash:
        span.set_attribute(EvidenceAttributes.EVIDENCE_CONTENT_HASH, content_hash)


def trace_evidence_window_expiry(
    span: Span,
    *,
    agent_id: str,
    escrow_id: str,
    window_expires_at: str,
) -> None:
    """Enrich a span with evidence window expiry attributes."""
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
    span.set_attribute(EvidenceAttributes.EVIDENCE_ESCROW_ID, escrow_id)
    span.set_attribute(EvidenceAttributes.EVIDENCE_WINDOW_EXPIRES_AT, window_expires_at)


def trace_default_judgment(
    span: Span,
    *,
    agent_id: str,
    escrow_id: str,
    judgment: str,
    stake_amount: int | None = None,
    stake_ruling: str | None = None,
) -> None:
    """Enrich a span with default judgment attributes."""
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
    span.set_attribute(EvidenceAttributes.EVIDENCE_ESCROW_ID, escrow_id)
    span.set_attribute(EvidenceAttributes.EVIDENCE_DEFAULT_JUDGMENT, judgment)
    if stake_amount is not None:
        span.set_attribute(EvidenceAttributes.EVIDENCE_STAKE_AMOUNT, stake_amount)
    if stake_ruling:
        span.set_attribute(EvidenceAttributes.EVIDENCE_STAKE_RULING, stake_ruling)
