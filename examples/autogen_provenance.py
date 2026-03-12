"""Example: AutoGen multi-agent conversation with derivation tracking.

Shows how to instrument an AutoGen-style multi-agent system with
provenance and derivation lineage spans. Uses an in-memory OTel
exporter so you can see the spans without a backend.

Run::

    python examples/autogen_provenance.py
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from otel_agent_provenance.adapters.autogen_derivation import (
    AutoGenDerivationTracker,
)
from otel_agent_provenance.conventions import DerivationStrategy, SourceType
from otel_agent_provenance.spans import DerivationSpan, ProvenanceSpan


def main() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "autogen-example"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("autogen_example")

    tracker = AutoGenDerivationTracker(
        tracer=tracer,
        root_task_id="task-research-gdp-2026",
    )

    # Agent A: Researcher -- produces initial research
    with ProvenanceSpan(
        tracer,
        name="invoke_agent researcher",
        agent_id="agent-researcher",
        tier=1,
        source_type=SourceType.RETRIEVAL,
        source_uris=["https://data.worldbank.org/gdp", "https://imf.org/data"],
        model_name="gpt-4o",
        confidence=0.82,
    ) as researcher_span:
        researcher_span.set_grounding(coverage=0.75, source_count=2, domain_count=2)
        researcher_span_id = _get_span_id(researcher_span.span)
        tracker.record_output("agent-researcher", researcher_span_id)

    # Agent B: Analyst -- synthesises researcher's output with its own tool calls
    with ProvenanceSpan(
        tracer,
        name="invoke_agent analyst",
        agent_id="agent-analyst",
        tier=1,
        source_type=SourceType.HYBRID,
        model_name="claude-sonnet-4-20250514",
        confidence=0.88,
    ) as analyst_span:
        tracker.record_derivation(
            agent_id="agent-analyst",
            span=analyst_span.span,
            input_agent_ids=["agent-researcher"],
            strategy=DerivationStrategy.SYNTHESIS,
            weights=[0.7],
        )
        analyst_span_id = _get_span_id(analyst_span.span)
        tracker.record_output("agent-analyst", analyst_span_id)

    # Agent C: Writer -- combines researcher + analyst into final output
    with ProvenanceSpan(
        tracer,
        name="invoke_agent writer",
        agent_id="agent-writer",
        tier=1,
        source_type=SourceType.MODEL_GENERATION,
        model_name="gpt-4o",
        confidence=0.91,
    ) as writer_span:
        tracker.record_derivation(
            agent_id="agent-writer",
            span=writer_span.span,
            input_agent_ids=["agent-researcher", "agent-analyst"],
            strategy=DerivationStrategy.SYNTHESIS,
            weights=[0.3, 0.7],
        )

    provider.force_flush()

    print("=== AutoGen Derivation Trace ===\n")
    for span_data in exporter.get_finished_spans():
        print(f"Span: {span_data.name}")
        for key, value in sorted(span_data.attributes.items()):
            print(f"  {key} = {value}")
        print()

    print(f"Total spans: {len(exporter.get_finished_spans())}")


def _get_span_id(span: trace.Span | None) -> str:
    if span is None:
        return ""
    ctx = span.get_span_context()
    return format(ctx.span_id, "016x") if ctx and ctx.is_valid else ""


if __name__ == "__main__":
    main()
