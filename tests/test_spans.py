"""Tests for span builders."""

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from otel_agent_provenance.conventions import (
    AcceptanceAttributes,
    DerivationAttributes,
    ProvenanceAttributes,
)
from otel_agent_provenance.spans import AcceptanceSpan, DerivationSpan, ProvenanceSpan


def _setup_tracer():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    return tracer, exporter, provider


class TestProvenanceSpan:
    def test_basic_tier1_span(self):
        tracer, exporter, provider = _setup_tracer()

        with ProvenanceSpan(
            tracer,
            agent_id="test-agent",
            tier=1,
            source_type="retrieval",
            model_name="gpt-4o",
        ):
            pass

        provider.force_flush()
        spans = exporter.get_finished_spans()
        assert len(spans) == 1

        attrs = dict(spans[0].attributes)
        assert attrs[ProvenanceAttributes.AGENT_ID] == "test-agent"
        assert attrs[ProvenanceAttributes.OUTPUT_PROVENANCE_TIER] == 1
        assert attrs[ProvenanceAttributes.OUTPUT_SOURCE_TYPE] == "retrieval"
        assert attrs[ProvenanceAttributes.OUTPUT_MODEL_NAME] == "gpt-4o"

    def test_tier2_with_hash(self):
        tracer, exporter, provider = _setup_tracer()

        with ProvenanceSpan(
            tracer,
            agent_id="test-agent",
            tier=2,
            hash_algorithm="sha256",
            hash_value="abc123",
            signature_method="ed25519",
            attestation_uri="https://exchange.example.com/att/001",
        ):
            pass

        provider.force_flush()
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        assert attrs[ProvenanceAttributes.OUTPUT_PROVENANCE_TIER] == 2
        assert attrs[ProvenanceAttributes.OUTPUT_HASH_ALGORITHM] == "sha256"
        assert attrs[ProvenanceAttributes.OUTPUT_HASH_VALUE] == "abc123"
        assert attrs[ProvenanceAttributes.OUTPUT_SIGNATURE_METHOD] == "ed25519"
        assert attrs[ProvenanceAttributes.ATTESTATION_URI] == (
            "https://exchange.example.com/att/001"
        )

    def test_grounding_enrichment(self):
        tracer, exporter, provider = _setup_tracer()

        with ProvenanceSpan(tracer, agent_id="test-agent") as span:
            span.set_grounding(coverage=0.85, source_count=3, domain_count=2)

        provider.force_flush()
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        assert attrs[ProvenanceAttributes.OUTPUT_GROUNDING_COVERAGE] == 0.85
        assert attrs[ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT] == 3
        assert attrs[ProvenanceAttributes.OUTPUT_GROUNDING_DOMAIN_COUNT] == 2

    def test_static_enrich(self):
        tracer, exporter, provider = _setup_tracer()

        with tracer.start_as_current_span("test") as span:
            ProvenanceSpan.enrich(
                span,
                agent_id="enriched-agent",
                tier=1,
                source_type="model_generation",
                confidence=0.9,
            )

        provider.force_flush()
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        assert attrs[ProvenanceAttributes.AGENT_ID] == "enriched-agent"
        assert attrs[ProvenanceAttributes.OUTPUT_CONFIDENCE] == 0.9


class TestDerivationSpan:
    def test_basic_derivation(self):
        tracer, exporter, provider = _setup_tracer()

        with DerivationSpan(
            tracer,
            input_spans=["span-a", "span-b"],
            input_agents=["agent-a", "agent-b"],
            strategy="synthesis",
            weights=[0.6, 0.4],
        ):
            pass

        provider.force_flush()
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        assert attrs[DerivationAttributes.INPUT_SPANS] == ("span-a", "span-b")
        assert attrs[DerivationAttributes.INPUT_AGENTS] == ("agent-a", "agent-b")
        assert attrs[DerivationAttributes.STRATEGY] == "synthesis"
        assert attrs[DerivationAttributes.WEIGHT] == (0.6, 0.4)

    def test_static_enrich(self):
        tracer, exporter, provider = _setup_tracer()

        with tracer.start_as_current_span("test") as span:
            DerivationSpan.enrich(
                span,
                input_agents=["agent-x"],
                strategy="delegation",
            )

        provider.force_flush()
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        assert attrs[DerivationAttributes.INPUT_AGENTS] == ("agent-x",)
        assert attrs[DerivationAttributes.STRATEGY] == "delegation"


class TestAcceptanceSpan:
    def test_basic_acceptance(self):
        tracer, exporter, provider = _setup_tracer()

        with AcceptanceSpan(
            tracer,
            task_id="task-001",
            strategy="llm",
            evaluator="mediator-001",
            factors=["completeness", "provenance"],
        ) as span:
            span.set_result(met=True, score=0.87)

        provider.force_flush()
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        assert attrs[AcceptanceAttributes.TASK_ID] == "task-001"
        assert attrs[AcceptanceAttributes.ACCEPTANCE_STRATEGY] == "llm"
        assert attrs[AcceptanceAttributes.ACCEPTANCE_EVALUATOR] == "mediator-001"
        assert attrs[AcceptanceAttributes.ACCEPTANCE_MET] is True
        assert attrs[AcceptanceAttributes.ACCEPTANCE_SCORE] == 0.87
        assert attrs[AcceptanceAttributes.ACCEPTANCE_FACTORS] == (
            "completeness",
            "provenance",
        )
