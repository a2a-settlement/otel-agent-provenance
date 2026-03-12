"""Adapter: Azure AI Search / Semantic Kernel RAG -> OTel provenance spans.

This addresses Microsoft Gap #1: the RAG retrieval influence chain.

Azure AI Search returns search results to the agent, but there is no
standardised way to capture which results actually influenced the output
versus which were retrieved but ignored.  This adapter instruments the
three-stage RAG pipeline:

1. **Retrieval** -- which documents/chunks came back from the search
2. **Selection** -- which results the model attended to (context window)
3. **Generation** -- what the model produced and which sources it cited

Usage::

    from otel_agent_provenance.adapters.azure_rag import (
        RagStageTracer,
        trace_retrieval,
        trace_selection,
        trace_generation,
    )

    tracer = RagStageTracer(otel_tracer, agent_id="agent-rag-001")

    # Stage 1: Retrieval
    with tracer.retrieval(query="GDP of France") as stage:
        results = search_client.search(query)
        stage.record_results(results)

    # Stage 2: Selection
    with tracer.selection() as stage:
        stage.record_context_window(selected_chunks, ignored_chunks)

    # Stage 3: Generation
    with tracer.generation(model_name="gpt-4o") as stage:
        output = llm.generate(prompt_with_context)
        stage.record_output(output, cited_uris=["..."])
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any, Sequence
from urllib.parse import urlparse

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode, Tracer

from otel_agent_provenance.conventions import (
    ProvenanceAttributes,
    SourceInfluence,
    SourceType,
)

_TRACER_NAME = "otel_agent_provenance.azure_rag"


@dataclass
class RetrievedDocument:
    """A document or chunk returned from Azure AI Search."""

    uri: str
    title: str = ""
    score: float = 0.0
    content_preview: str = ""


@dataclass
class _RetrievalStage:
    """Context manager for the retrieval stage of a RAG pipeline."""

    span: Span
    results: list[RetrievedDocument] = field(default_factory=list)

    def record_results(
        self,
        results: Sequence[RetrievedDocument | dict[str, Any]],
    ) -> None:
        for r in results:
            if isinstance(r, dict):
                r = RetrievedDocument(
                    uri=r.get("uri", r.get("url", "")),
                    title=r.get("title", ""),
                    score=r.get("@search.score", r.get("score", 0.0)),
                    content_preview=r.get("content", "")[:200],
                )
            self.results.append(r)

        uris = [r.uri for r in self.results if r.uri]
        self.span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_URI, uris)
        self.span.set_attribute(
            ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT, len(uris)
        )

        domains: set[str] = set()
        for uri in uris:
            try:
                netloc = urlparse(uri).netloc
                if netloc:
                    domains.add(netloc)
            except Exception:
                pass
        self.span.set_attribute(
            ProvenanceAttributes.OUTPUT_GROUNDING_DOMAIN_COUNT, len(domains)
        )

    def __enter__(self) -> _RetrievalStage:
        return self

    def __exit__(self, *exc_info: Any) -> bool:
        if exc_info[0] is not None:
            self.span.set_status(StatusCode.ERROR, str(exc_info[1]))
        else:
            self.span.set_status(StatusCode.OK)
        self.span.end()
        return False


@dataclass
class _SelectionStage:
    """Context manager for the selection stage -- which results the model attended to."""

    span: Span
    attended_uris: list[str] = field(default_factory=list)
    ignored_uris: list[str] = field(default_factory=list)

    def record_context_window(
        self,
        attended: Sequence[str | RetrievedDocument],
        ignored: Sequence[str | RetrievedDocument] | None = None,
    ) -> None:
        self.attended_uris = [
            d.uri if isinstance(d, RetrievedDocument) else d for d in attended
        ]
        self.ignored_uris = [
            d.uri if isinstance(d, RetrievedDocument) else d for d in (ignored or [])
        ]

        self.span.set_attribute(
            ProvenanceAttributes.OUTPUT_SOURCE_URI, self.attended_uris
        )
        self.span.set_attribute(
            ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE, SourceInfluence.ATTENDED
        )
        self.span.set_attribute(
            ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT, len(self.attended_uris)
        )

    def __enter__(self) -> _SelectionStage:
        return self

    def __exit__(self, *exc_info: Any) -> bool:
        if exc_info[0] is not None:
            self.span.set_status(StatusCode.ERROR, str(exc_info[1]))
        else:
            self.span.set_status(StatusCode.OK)
        self.span.end()
        return False


@dataclass
class _GenerationStage:
    """Context manager for the generation stage -- output + citations."""

    span: Span

    def record_output(
        self,
        output_text: str,
        *,
        cited_uris: Sequence[str] | None = None,
        confidence: float | None = None,
        coverage: float | None = None,
    ) -> None:
        if cited_uris:
            self.span.set_attribute(
                ProvenanceAttributes.OUTPUT_SOURCE_URI, list(cited_uris)
            )
            self.span.set_attribute(
                ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE, SourceInfluence.CITED
            )
        if confidence is not None:
            self.span.set_attribute(ProvenanceAttributes.OUTPUT_CONFIDENCE, confidence)
        if coverage is not None:
            self.span.set_attribute(
                ProvenanceAttributes.OUTPUT_GROUNDING_COVERAGE, coverage
            )

    def __enter__(self) -> _GenerationStage:
        return self

    def __exit__(self, *exc_info: Any) -> bool:
        if exc_info[0] is not None:
            self.span.set_status(StatusCode.ERROR, str(exc_info[1]))
        else:
            self.span.set_status(StatusCode.OK)
        self.span.end()
        return False


class RagStageTracer:
    """Three-stage RAG pipeline tracer for Azure AI Search / Semantic Kernel.

    Creates linked child spans for retrieval, selection, and generation,
    each annotated with the appropriate provenance attributes.
    """

    def __init__(
        self,
        tracer: Tracer | None = None,
        *,
        agent_id: str = "",
        parent_span_name: str = "agent.rag_pipeline",
    ):
        self._tracer = tracer or trace.get_tracer(_TRACER_NAME)
        self._agent_id = agent_id
        self._parent_name = parent_span_name

    def retrieval(self, *, query: str = "") -> _RetrievalStage:
        span = self._tracer.start_span(
            f"{self._parent_name}.retrieval",
            attributes={
                ProvenanceAttributes.AGENT_ID: self._agent_id,
                ProvenanceAttributes.OUTPUT_SOURCE_TYPE: SourceType.RETRIEVAL,
                ProvenanceAttributes.OUTPUT_PROVENANCE_TIER: 1,
            },
        )
        if query:
            span.set_attribute("agent.rag.query", query)
        return _RetrievalStage(span=span)

    def selection(self) -> _SelectionStage:
        span = self._tracer.start_span(
            f"{self._parent_name}.selection",
            attributes={
                ProvenanceAttributes.AGENT_ID: self._agent_id,
                ProvenanceAttributes.OUTPUT_SOURCE_TYPE: SourceType.RETRIEVAL,
            },
        )
        return _SelectionStage(span=span)

    def generation(self, *, model_name: str = "") -> _GenerationStage:
        attrs: dict[str, Any] = {
            ProvenanceAttributes.AGENT_ID: self._agent_id,
            ProvenanceAttributes.OUTPUT_SOURCE_TYPE: SourceType.HYBRID,
            ProvenanceAttributes.OUTPUT_PROVENANCE_TIER: 1,
        }
        if model_name:
            attrs[ProvenanceAttributes.OUTPUT_MODEL_NAME] = model_name
        span = self._tracer.start_span(
            f"{self._parent_name}.generation",
            attributes=attrs,
        )
        return _GenerationStage(span=span)


def trace_retrieval(
    span: Span,
    *,
    agent_id: str,
    result_uris: Sequence[str],
) -> None:
    """One-shot enrichment for a retrieval span."""
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
    span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_TYPE, SourceType.RETRIEVAL)
    span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_URI, list(result_uris))
    span.set_attribute(
        ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT, len(result_uris)
    )


def trace_selection(
    span: Span,
    *,
    attended_uris: Sequence[str],
    ignored_uris: Sequence[str] | None = None,
) -> None:
    """One-shot enrichment for a selection span."""
    span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_URI, list(attended_uris))
    span.set_attribute(
        ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE, SourceInfluence.ATTENDED
    )
    span.set_attribute(
        ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT, len(attended_uris)
    )


def trace_generation(
    span: Span,
    *,
    cited_uris: Sequence[str],
    model_name: str = "",
    confidence: float | None = None,
    coverage: float | None = None,
) -> None:
    """One-shot enrichment for a generation span."""
    span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_URI, list(cited_uris))
    span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE, SourceInfluence.CITED)
    if model_name:
        span.set_attribute(ProvenanceAttributes.OUTPUT_MODEL_NAME, model_name)
    if confidence is not None:
        span.set_attribute(ProvenanceAttributes.OUTPUT_CONFIDENCE, confidence)
    if coverage is not None:
        span.set_attribute(ProvenanceAttributes.OUTPUT_GROUNDING_COVERAGE, coverage)
