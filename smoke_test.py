"""Smoke test: verify all modules import and basic span creation works."""


def main() -> int:
    errors: list[str] = []

    # 1. Core dependency imports
    try:
        import opentelemetry.trace  # noqa: F401
        import opentelemetry.sdk.trace  # noqa: F401
        import pydantic  # noqa: F401
    except Exception as e:
        errors.append(f"dependency import failed: {e}")

    # 2. Package import
    try:
        import otel_agent_provenance  # noqa: F401
    except Exception as e:
        errors.append(f"package import failed: {e}")

    # 3. Conventions
    try:
        from otel_agent_provenance.conventions import (
            AcceptanceAttributes,
            DerivationAttributes,
            ProvenanceAttributes,
            SourceType,
            SourceInfluence,
            DerivationStrategy,
            AcceptanceStrategy,
        )
        assert ProvenanceAttributes.AGENT_ID == "agent.id"
        assert SourceType.RETRIEVAL == "retrieval"
        assert DerivationStrategy.SYNTHESIS == "synthesis"
        assert AcceptanceStrategy.LLM == "llm"
    except Exception as e:
        errors.append(f"conventions failed: {e}")

    # 4. Span builders
    try:
        from otel_agent_provenance.spans import (
            ProvenanceSpan,
            DerivationSpan,
            AcceptanceSpan,
        )

        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = provider.get_tracer("smoke")

        with ProvenanceSpan(tracer, agent_id="smoke-test", tier=1):
            pass

        with DerivationSpan(tracer, input_agents=["a"], strategy="synthesis"):
            pass

        with AcceptanceSpan(tracer, task_id="task-smoke"):
            pass

        provider.force_flush()
        spans = exporter.get_finished_spans()
        assert len(spans) == 3, f"expected 3 spans, got {len(spans)}"
    except Exception as e:
        errors.append(f"span builders failed: {e}")

    # 5. Adapters import
    try:
        from otel_agent_provenance.adapters.google_grounding import (
            from_adk_provenance,
            enrich_span_from_grounding,
        )
        from otel_agent_provenance.adapters.azure_rag import (
            RagStageTracer,
            RetrievedDocument,
        )
        from otel_agent_provenance.adapters.autogen_derivation import (
            AutoGenDerivationTracker,
            enrich_agent_span,
        )
        from otel_agent_provenance.adapters.semantic_kernel_rag import (
            ProvenanceFilter,
            trace_kernel_rag,
        )
    except Exception as e:
        errors.append(f"adapters import failed: {e}")

    # 6. Instruments import
    try:
        from otel_agent_provenance.instruments.settlement_exchange import (
            ExchangeInstrumentor,
            trace_delivery,
        )
        from otel_agent_provenance.instruments.settlement_mediator import (
            MediatorInstrumentor,
            trace_mediation,
        )
        from otel_agent_provenance.instruments.settlement_shim import (
            ShimInstrumentor,
            trace_shim_request,
        )
    except Exception as e:
        errors.append(f"instruments import failed: {e}")

    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1

    print("otel-agent-provenance smoke test: ALL OK")
    print(f"  - conventions: {len(dir(ProvenanceAttributes))} attributes")
    print(f"  - span builders: ProvenanceSpan, DerivationSpan, AcceptanceSpan")
    print(f"  - adapters: google_grounding, azure_rag, autogen_derivation, semantic_kernel_rag")
    print(f"  - instruments: settlement_exchange, settlement_mediator, settlement_shim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
