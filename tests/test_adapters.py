"""Tests for framework adapters."""

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from otel_agent_provenance.adapters.autogen_derivation import (
    AutoGenDerivationTracker,
    enrich_agent_span,
)
from otel_agent_provenance.adapters.azure_rag import RagStageTracer, RetrievedDocument
from otel_agent_provenance.adapters.google_grounding import from_adk_provenance
from otel_agent_provenance.conventions import (
    DerivationAttributes,
    DerivationStrategy,
    ProvenanceAttributes,
    SourceInfluence,
)


def _setup_tracer():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    return tracer, exporter, provider


class TestGoogleGroundingAdapter:
    def test_from_adk_provenance_basic(self):
        provenance = {
            "source_type": "web",
            "source_refs": [
                {"uri": "https://example.com/doc1"},
                {"uri": "https://other.com/doc2"},
            ],
            "attestation_level": "self_declared",
            "grounding_metadata": {
                "chunks": [
                    {"uri": "https://example.com/doc1", "title": "Doc 1"},
                    {"uri": "https://other.com/doc2", "title": "Doc 2"},
                ],
                "coverage": 0.75,
            },
        }

        attrs = from_adk_provenance(provenance, agent_id="agent-test")

        assert attrs[ProvenanceAttributes.AGENT_ID] == "agent-test"
        assert attrs[ProvenanceAttributes.OUTPUT_PROVENANCE_TIER] == 1
        assert len(attrs[ProvenanceAttributes.OUTPUT_SOURCE_URI]) == 2
        assert attrs[ProvenanceAttributes.OUTPUT_GROUNDING_COVERAGE] == 0.75
        assert attrs[ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT] == 2
        assert attrs[ProvenanceAttributes.OUTPUT_GROUNDING_DOMAIN_COUNT] == 2

    def test_verifiable_sets_callback(self):
        provenance = {
            "source_type": "web",
            "source_refs": [{"uri": "https://example.com/verify"}],
            "attestation_level": "verifiable",
            "grounding_metadata": {"chunks": [], "coverage": 0.5},
        }

        attrs = from_adk_provenance(provenance)
        assert attrs[ProvenanceAttributes.OUTPUT_PROVENANCE_TIER] == 3
        assert attrs[ProvenanceAttributes.CALLBACK_URI] == "https://example.com/verify"


class TestAzureRagAdapter:
    def test_rag_pipeline_stages(self):
        tracer, exporter, provider = _setup_tracer()

        rag = RagStageTracer(tracer=tracer, agent_id="agent-rag")

        with rag.retrieval(query="test query") as stage:
            stage.record_results([
                RetrievedDocument(uri="https://a.com/1", score=0.9),
                RetrievedDocument(uri="https://b.com/2", score=0.8),
            ])

        with rag.selection() as stage:
            stage.record_context_window(
                attended=["https://a.com/1"],
                ignored=["https://b.com/2"],
            )

        with rag.generation(model_name="gpt-4o") as stage:
            stage.record_output("output text", cited_uris=["https://a.com/1"])

        provider.force_flush()
        spans = exporter.get_finished_spans()
        assert len(spans) == 3

        retrieval_attrs = dict(spans[0].attributes)
        assert retrieval_attrs[ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT] == 2

        selection_attrs = dict(spans[1].attributes)
        assert selection_attrs[ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE] == (
            SourceInfluence.ATTENDED
        )

        generation_attrs = dict(spans[2].attributes)
        assert generation_attrs[ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE] == (
            SourceInfluence.CITED
        )


class TestAutoGenDerivationAdapter:
    def test_tracker_records_derivation(self):
        tracer, exporter, provider = _setup_tracer()

        tracker = AutoGenDerivationTracker(
            tracer=tracer,
            root_task_id="task-001",
        )

        tracker.record_output("agent-a", "span-aaa")
        tracker.record_output("agent-b", "span-bbb")

        with tracer.start_as_current_span("invoke_agent agent-c") as span:
            tracker.record_derivation(
                agent_id="agent-c",
                span=span,
                input_agent_ids=["agent-a", "agent-b"],
                strategy=DerivationStrategy.SYNTHESIS,
                weights=[0.6, 0.4],
            )

        provider.force_flush()
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        assert attrs[DerivationAttributes.INPUT_SPANS] == ("span-aaa", "span-bbb")
        assert attrs[DerivationAttributes.INPUT_AGENTS] == ("agent-a", "agent-b")
        assert attrs[DerivationAttributes.STRATEGY] == "synthesis"
        assert attrs[DerivationAttributes.WEIGHT] == (0.6, 0.4)
        assert attrs[ProvenanceAttributes.CHAIN_DEPTH] == 1
        assert attrs[ProvenanceAttributes.CHAIN_ROOT_TASK_ID] == "task-001"

    def test_chain_depth_increments(self):
        tracker = AutoGenDerivationTracker(root_task_id="task-001")

        tracker.record_output("a", "span-a")
        assert tracker.get_chain_depth("a") == 0

        tracer, exporter, provider = _setup_tracer()
        with tracer.start_as_current_span("test") as span:
            tracker.record_derivation(
                agent_id="b",
                span=span,
                input_agent_ids=["a"],
            )
        assert tracker.get_chain_depth("b") == 1

        tracker.record_output("b", "span-b")

        with tracer.start_as_current_span("test2") as span:
            tracker.record_derivation(
                agent_id="c",
                span=span,
                input_agent_ids=["b"],
            )
        assert tracker.get_chain_depth("c") == 2

    def test_enrich_agent_span(self):
        tracer, exporter, provider = _setup_tracer()

        with tracer.start_as_current_span("test") as span:
            enrich_agent_span(
                span,
                agent_id="agent-x",
                input_agent_ids=["agent-y"],
                input_span_ids=["span-y"],
                strategy="delegation",
                chain_depth=1,
                root_task_id="task-002",
            )

        provider.force_flush()
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        assert attrs[ProvenanceAttributes.AGENT_ID] == "agent-x"
        assert attrs[DerivationAttributes.INPUT_AGENTS] == ("agent-y",)
        assert attrs[ProvenanceAttributes.CHAIN_DEPTH] == 1
