"""Example: Google ADK grounding metadata -> OTel provenance.

Shows the ~200-line mechanical adapter that translates Google's
structured grounding metadata into OTel provenance attributes.

Run::

    python examples/adk_grounding.py
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from otel_agent_provenance.adapters.google_grounding import (
    enrich_span_from_grounding,
    from_adk_provenance,
)
from otel_agent_provenance.spans import ProvenanceSpan


def main() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "adk-grounding-example"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("adk_grounding_example")

    # Simulate output from adk-a2a-settlement's build_grounded_provenance()
    adk_provenance = {
        "source_type": "web",
        "source_refs": [
            {
                "uri": "https://en.wikipedia.org/wiki/France",
                "method": "google_search_grounding",
                "timestamp": "2026-03-11T14:00:00Z",
                "content_hash": None,
            },
            {
                "uri": "https://data.worldbank.org/country/france",
                "method": "google_search_grounding",
                "timestamp": "2026-03-11T14:00:00Z",
                "content_hash": None,
            },
        ],
        "attestation_level": "verifiable",
        "signature": None,
        "grounding_metadata": {
            "chunks": [
                {"uri": "https://en.wikipedia.org/wiki/France", "title": "France - Wikipedia"},
                {
                    "uri": "https://data.worldbank.org/country/france",
                    "title": "France | World Bank",
                },
            ],
            "supports": [],
            "search_queries": ["GDP of France 2025"],
            "coverage": 0.78,
        },
    }

    # Convert ADK provenance to OTel attributes
    attrs = from_adk_provenance(adk_provenance, agent_id="agent-adk-research")

    print("=== ADK Provenance -> OTel Attributes ===\n")
    for key, value in sorted(attrs.items()):
        print(f"  {key} = {value}")

    # Apply to a span
    with ProvenanceSpan(
        tracer,
        name="invoke_agent adk_researcher",
        agent_id="agent-adk-research",
        tier=3,
        model_name="gemini-2.5-flash",
    ) as prov_span:
        enrich_span_from_grounding(prov_span.span, attrs)

    provider.force_flush()

    print("\n=== Span Attributes ===\n")
    for span_data in exporter.get_finished_spans():
        print(f"Span: {span_data.name}")
        for key, value in sorted(span_data.attributes.items()):
            print(f"  {key} = {value}")
        print()

    print(
        "Note: Google's grounding metadata maps mechanically to OTel attributes.\n"
        "This is the 'free provenance' path for Google/ADK users."
    )


if __name__ == "__main__":
    main()
