"""Example: End-to-end A2A-SE settlement trace with provenance.

Shows the full lifecycle: escrow creation -> delivery with provenance ->
mediator acceptance evaluation -> resolution. Demonstrates all three
convention groups (provenance, derivation, acceptance) in a single trace.

Run::

    python examples/settlement_e2e.py
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from otel_agent_provenance.conventions import (
    AcceptanceStrategy,
    DerivationStrategy,
    SourceType,
)
from otel_agent_provenance.instruments.settlement_exchange import (
    trace_delivery,
    trace_escrow_create,
    trace_escrow_lifecycle,
)
from otel_agent_provenance.instruments.settlement_mediator import (
    MEDIATOR_FACTORS,
    trace_mediation,
    trace_provenance_verification,
)
from otel_agent_provenance.spans import AcceptanceSpan, DerivationSpan, ProvenanceSpan


def main() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider(
        resource=Resource.create({"service.name": "settlement-e2e-example"})
    )
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("settlement_e2e")

    # 1. Escrow creation
    with tracer.start_as_current_span("settlement.escrow.create") as span:
        trace_escrow_create(
            span,
            agent_id="requester-agent",
            escrow_id="esc-abc-123",
            requester_id="requester-agent",
            provider_id="provider-agent",
            amount=500.0,
            task_id="task-research-gdp",
            required_attestation_level="signed",
        )

    # 2. Provider delivers with provenance
    with ProvenanceSpan(
        tracer,
        name="settlement.escrow.deliver",
        agent_id="provider-agent",
        tier=2,
        source_type=SourceType.RETRIEVAL,
        source_uris=[
            "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
            "https://imf.org/external/datamapper/NGDPD",
        ],
        confidence=0.85,
        model_name="gpt-4o",
        hash_algorithm="sha256",
        hash_value="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        attestation_uri="https://exchange.a2a-settlement.org/attestation/esc-abc-123",
        attestation_timestamp="2026-03-11T14:30:00Z",
    ) as delivery_span:
        delivery_span.set_grounding(coverage=0.82, source_count=2, domain_count=2)

        trace_delivery(
            delivery_span.span,
            agent_id="provider-agent",
            escrow_id="esc-abc-123",
            provenance={
                "source_type": "web",
                "source_refs": [
                    {"uri": "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD"},
                    {"uri": "https://imf.org/external/datamapper/NGDPD"},
                ],
                "attestation_level": "signed",
                "grounding_metadata": {"coverage": 0.82, "chunks": [{}, {}]},
            },
        )

    # 3. Derivation: this delivery derived from sub-agent research
    with DerivationSpan(
        tracer,
        name="agent.derivation.research_pipeline",
        input_agents=["sub-agent-researcher", "sub-agent-analyst"],
        strategy=DerivationStrategy.SYNTHESIS,
        weights=[0.4, 0.6],
    ):
        pass

    # 4. Mediator evaluates acceptance criteria
    with AcceptanceSpan(
        tracer,
        name="agent.acceptance.mediation",
        task_id="esc-abc-123",
        acceptance_criteria="sha256:task-spec-hash-here",
        strategy=AcceptanceStrategy.HYBRID,
        evaluator="mediator-agent-001",
        factors=MEDIATOR_FACTORS,
    ) as acceptance_span:
        # Provenance verification sub-span
        with tracer.start_as_current_span("agent.provenance.verify") as prov_span:
            trace_provenance_verification(
                prov_span,
                agent_id="mediator-agent-001",
                tier="signed",
                verified=True,
                confidence=0.85,
                flags=["grounding_strong"],
                grounding_coverage=0.82,
                grounding_source_count=2,
                grounding_domain_count=2,
            )

        # LLM evaluation sub-span
        with tracer.start_as_current_span("agent.acceptance.llm_evaluate") as eval_span:
            trace_mediation(
                eval_span,
                escrow_id="esc-abc-123",
                agent_id="mediator-agent-001",
                verdict={
                    "outcome": "AUTO_RELEASE",
                    "resolution": "release",
                    "confidence": 0.87,
                    "reasoning": "Deliverable meets acceptance criteria with strong provenance.",
                    "factors": [
                        "deliverable_completeness",
                        "provenance_attestation",
                        "web_grounding",
                    ],
                },
            )

        acceptance_span.set_result(met=True, score=0.87)

    # 5. Release escrow
    with tracer.start_as_current_span("settlement.escrow.release") as span:
        trace_escrow_lifecycle(
            span,
            agent_id="requester-agent",
            escrow_id="esc-abc-123",
            operation="release",
            status="released",
            amount=500.0,
        )

    provider.force_flush()

    print("=== Settlement E2E Trace ===\n")
    for span_data in exporter.get_finished_spans():
        print(f"Span: {span_data.name}")
        for key, value in sorted(span_data.attributes.items()):
            print(f"  {key} = {value}")
        print()

    print(f"Total spans: {len(exporter.get_finished_spans())}")
    print(
        "\nThis trace shows the full lifecycle:\n"
        "  escrow create -> delivery with Tier 2 provenance -> "
        "derivation lineage -> mediator acceptance evaluation -> release"
    )


if __name__ == "__main__":
    main()
