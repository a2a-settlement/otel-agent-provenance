"""Example: Azure AI Search RAG pipeline with provenance tracing.

Demonstrates the three-stage RAG pipeline tracer that fills Microsoft
Gap #1: the retrieval-to-generation influence chain.

Run::

    python examples/azure_rag_provenance.py
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from otel_agent_provenance.adapters.azure_rag import RagStageTracer, RetrievedDocument


def main() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "azure-rag-example"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    rag_tracer = RagStageTracer(agent_id="agent-rag-001")

    # Stage 1: Retrieval -- Azure AI Search returns 5 documents
    search_results = [
        RetrievedDocument(
            uri="https://docs.microsoft.com/azure/search/overview",
            title="Azure AI Search Overview",
            score=0.95,
        ),
        RetrievedDocument(
            uri="https://learn.microsoft.com/semantic-kernel/concepts",
            title="Semantic Kernel Concepts",
            score=0.88,
        ),
        RetrievedDocument(
            uri="https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
            title="RAG - Wikipedia",
            score=0.82,
        ),
        RetrievedDocument(
            uri="https://arxiv.org/abs/2005.11401",
            title="RAG: Retrieval-Augmented Generation Paper",
            score=0.79,
        ),
        RetrievedDocument(
            uri="https://news.ycombinator.com/item?id=38000000",
            title="HN Discussion on RAG",
            score=0.45,
        ),
    ]

    with rag_tracer.retrieval(query="How does Azure AI Search work with RAG?") as stage:
        stage.record_results(search_results)

    # Stage 2: Selection -- model context window gets top 3
    attended = [r.uri for r in search_results[:3]]
    ignored = [r.uri for r in search_results[3:]]

    with rag_tracer.selection() as stage:
        stage.record_context_window(attended=attended, ignored=ignored)

    # Stage 3: Generation -- model produces output citing 2 sources
    with rag_tracer.generation(model_name="gpt-4o") as stage:
        stage.record_output(
            "Azure AI Search integrates with RAG pipelines by providing "
            "semantic and vector search capabilities...",
            cited_uris=[search_results[0].uri, search_results[2].uri],
            confidence=0.88,
            coverage=0.72,
        )

    provider.force_flush()

    print("=== Azure RAG Pipeline Trace ===\n")
    for span_data in exporter.get_finished_spans():
        print(f"Span: {span_data.name}")
        for key, value in sorted(span_data.attributes.items()):
            print(f"  {key} = {value}")
        print()

    print(f"Total spans: {len(exporter.get_finished_spans())}")
    print("\nNote: 5 documents retrieved -> 3 attended -> 2 cited")
    print("This is the retrieval influence chain that was previously invisible.")


if __name__ == "__main__":
    main()
