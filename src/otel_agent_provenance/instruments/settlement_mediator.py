"""OTel instrumentation for the A2A-SE AI Mediator.

Maps the mediator's 7-factor evaluation framework and confidence-gated
resolution to ``agent.task.acceptance_criteria.*`` spans.  This is the
reference implementation for Microsoft Gap #3: the acceptance criteria
evaluation loop.

Usage::

    from otel_agent_provenance.instruments.settlement_mediator import (
        trace_mediation,
        trace_provenance_verification,
        MediatorInstrumentor,
    )

    # Wrap a mediation call
    with MediatorInstrumentor.mediation_span(
        escrow_id="esc-123",
        agent_id="mediator-001",
    ) as span:
        verdict = mediator.mediate(escrow_id)
        MediatorInstrumentor.record_verdict(span, verdict)
"""

from __future__ import annotations

from typing import Any, Sequence

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode, Tracer

from otel_agent_provenance.conventions import (
    AcceptanceAttributes,
    AcceptanceStrategy,
    ProvenanceAttributes,
)

_TRACER_NAME = "otel_agent_provenance.settlement_mediator"

MEDIATOR_FACTORS = [
    "deliverable_completeness",
    "acceptance_criteria_specificity",
    "dispute_substantiation",
    "reputation_history",
    "proportionality",
    "provenance_attestation",
    "web_grounding",
]


def trace_mediation(
    span: Span,
    *,
    escrow_id: str,
    agent_id: str = "mediator",
    verdict: dict[str, Any] | None = None,
    provenance_result: dict[str, Any] | None = None,
) -> None:
    """Enrich a span with mediation/acceptance attributes.

    Maps the mediator's verdict to acceptance criteria attributes:
    - ``outcome`` -> ``acceptance_criteria.met``
    - ``confidence`` -> ``acceptance_criteria.score``
    - ``factors`` -> ``acceptance_criteria.factors``
    - resolution strategy -> ``acceptance_criteria.strategy``
    """
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
    span.set_attribute(AcceptanceAttributes.TASK_ID, escrow_id)
    span.set_attribute(AcceptanceAttributes.ACCEPTANCE_EVALUATOR, agent_id)

    if verdict:
        outcome = verdict.get("outcome", "")
        resolution = verdict.get("resolution")
        confidence = verdict.get("confidence", 0.0)
        reasoning = verdict.get("reasoning", "")
        factors = verdict.get("factors", [])

        met = outcome in ("AUTO_RELEASE", "auto_release")
        span.set_attribute(AcceptanceAttributes.ACCEPTANCE_MET, met)
        span.set_attribute(AcceptanceAttributes.ACCEPTANCE_SCORE, float(confidence))

        if outcome in ("ESCALATE", "escalate"):
            span.set_attribute(
                AcceptanceAttributes.ACCEPTANCE_STRATEGY, AcceptanceStrategy.HYBRID
            )
        else:
            span.set_attribute(
                AcceptanceAttributes.ACCEPTANCE_STRATEGY, AcceptanceStrategy.LLM
            )

        if factors:
            span.set_attribute(AcceptanceAttributes.ACCEPTANCE_FACTORS, factors)

        span.set_attribute("settlement.mediation.outcome", outcome)
        if resolution:
            span.set_attribute("settlement.mediation.resolution", resolution)
        if reasoning:
            span.set_attribute("settlement.mediation.reasoning", reasoning[:500])

    if provenance_result:
        prov_tier = provenance_result.get("tier", "self_declared")
        prov_confidence = provenance_result.get("confidence", 0.0)
        prov_verified = provenance_result.get("verified", False)
        prov_flags = provenance_result.get("flags", [])

        tier_map = {"self_declared": 1, "signed": 2, "verifiable": 3}
        span.set_attribute(
            ProvenanceAttributes.OUTPUT_PROVENANCE_TIER, tier_map.get(prov_tier, 1)
        )
        span.set_attribute(ProvenanceAttributes.OUTPUT_CONFIDENCE, prov_confidence)
        if prov_flags:
            span.set_attribute("settlement.provenance.flags", prov_flags)


def trace_provenance_verification(
    span: Span,
    *,
    agent_id: str = "mediator",
    tier: str = "self_declared",
    verified: bool = False,
    confidence: float = 0.0,
    flags: Sequence[str] | None = None,
    grounding_coverage: float | None = None,
    grounding_source_count: int | None = None,
    grounding_domain_count: int | None = None,
) -> None:
    """Enrich a span with provenance verification results."""
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)

    tier_map = {"self_declared": 1, "signed": 2, "verifiable": 3}
    span.set_attribute(
        ProvenanceAttributes.OUTPUT_PROVENANCE_TIER, tier_map.get(tier, 1)
    )
    span.set_attribute(ProvenanceAttributes.OUTPUT_CONFIDENCE, confidence)

    if flags:
        span.set_attribute("settlement.provenance.flags", list(flags))
    if grounding_coverage is not None:
        span.set_attribute(
            ProvenanceAttributes.OUTPUT_GROUNDING_COVERAGE, grounding_coverage
        )
    if grounding_source_count is not None:
        span.set_attribute(
            ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT, grounding_source_count
        )
    if grounding_domain_count is not None:
        span.set_attribute(
            ProvenanceAttributes.OUTPUT_GROUNDING_DOMAIN_COUNT, grounding_domain_count
        )


class MediatorInstrumentor:
    """Convenience class for instrumenting mediator operations."""

    _tracer: Tracer | None = None

    @classmethod
    def get_tracer(cls) -> Tracer:
        if cls._tracer is None:
            cls._tracer = trace.get_tracer(_TRACER_NAME)
        return cls._tracer

    @classmethod
    def mediation_span(
        cls,
        *,
        escrow_id: str,
        agent_id: str = "mediator",
    ) -> trace.Span:
        """Create a mediation span as a context manager.

        Usage::

            with MediatorInstrumentor.mediation_span(
                escrow_id="esc-123"
            ) as span:
                ...
        """
        tracer = cls.get_tracer()
        return tracer.start_as_current_span(
            "agent.acceptance.mediation",
            attributes={
                ProvenanceAttributes.AGENT_ID: agent_id,
                AcceptanceAttributes.TASK_ID: escrow_id,
                AcceptanceAttributes.ACCEPTANCE_EVALUATOR: agent_id,
                AcceptanceAttributes.ACCEPTANCE_FACTORS: MEDIATOR_FACTORS,
            },
        )

    @classmethod
    def record_verdict(
        cls,
        span: Span,
        verdict: Any,
    ) -> None:
        """Record a mediator verdict (Verdict or dict) on a span."""
        if hasattr(verdict, "model_dump"):
            v = verdict.model_dump()
        elif isinstance(verdict, dict):
            v = verdict
        else:
            return

        trace_mediation(
            span,
            escrow_id=v.get("escrow_id", ""),
            verdict=v,
        )
