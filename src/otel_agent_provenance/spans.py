"""Span builders for agent provenance, derivation, and acceptance criteria.

Each builder creates or enriches OTel spans with the appropriate semantic
convention attributes. They can be used as context managers or called
imperatively to set attributes on existing spans.

Usage::

    from otel_agent_provenance.spans import ProvenanceSpan

    with ProvenanceSpan(
        tracer,
        agent_id="agent-001",
        tier=1,
        source_type="retrieval",
        source_uris=["https://example.com/doc"],
        model_name="gpt-4o",
    ) as span:
        result = do_work()
        span.set_grounding(coverage=0.85, source_count=3, domain_count=2)
"""

from __future__ import annotations

import contextlib
from typing import Any, Sequence

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode, Tracer

from otel_agent_provenance.conventions import (
    AcceptanceAttributes,
    DerivationAttributes,
    ProvenanceAttributes,
)

_TRACER_NAME = "otel_agent_provenance"


def _set_if(span: Span, key: str, value: Any) -> None:
    if value is not None:
        span.set_attribute(key, value)


class ProvenanceSpan:
    """Context manager that creates a span with provenance attributes.

    Supports all three tiers: self-declared (1), signed (2), and
    verifiable (3). Higher-tier attributes are only set when the
    corresponding values are provided.
    """

    def __init__(
        self,
        tracer: Tracer | None = None,
        *,
        name: str = "agent.provenance",
        agent_id: str,
        tier: int = 1,
        source_type: str | None = None,
        source_uris: Sequence[str] | None = None,
        source_influence: str | None = None,
        confidence: float | None = None,
        model_name: str | None = None,
        model_version: str | None = None,
        identity_tier: int | None = None,
        identity_registry: str | None = None,
        # Tier 2
        hash_algorithm: str | None = None,
        hash_value: str | None = None,
        signature_method: str | None = None,
        signature_value: str | None = None,
        signature_key_id: str | None = None,
        attestation_uri: str | None = None,
        attestation_timestamp: str | None = None,
        # Tier 3
        callback_uri: str | None = None,
        callback_method: str | None = None,
        callback_status: str | None = None,
        # Chain
        parent_span_id: str | None = None,
        chain_depth: int | None = None,
        root_task_id: str | None = None,
    ):
        self._tracer = tracer or trace.get_tracer(_TRACER_NAME)
        self._name = name
        self._attrs: dict[str, Any] = {}

        self._attrs[ProvenanceAttributes.AGENT_ID] = agent_id
        self._attrs[ProvenanceAttributes.OUTPUT_PROVENANCE_TIER] = tier

        _map = {
            ProvenanceAttributes.OUTPUT_SOURCE_TYPE: source_type,
            ProvenanceAttributes.OUTPUT_SOURCE_URI: list(source_uris) if source_uris else None,
            ProvenanceAttributes.OUTPUT_SOURCE_INFLUENCE: source_influence,
            ProvenanceAttributes.OUTPUT_CONFIDENCE: confidence,
            ProvenanceAttributes.OUTPUT_MODEL_NAME: model_name,
            ProvenanceAttributes.OUTPUT_MODEL_VERSION: model_version,
            ProvenanceAttributes.AGENT_IDENTITY_TIER: identity_tier,
            ProvenanceAttributes.AGENT_IDENTITY_REGISTRY: identity_registry,
            ProvenanceAttributes.OUTPUT_HASH_ALGORITHM: hash_algorithm,
            ProvenanceAttributes.OUTPUT_HASH_VALUE: hash_value,
            ProvenanceAttributes.OUTPUT_SIGNATURE_METHOD: signature_method,
            ProvenanceAttributes.OUTPUT_SIGNATURE_VALUE: signature_value,
            ProvenanceAttributes.OUTPUT_SIGNATURE_KEY_ID: signature_key_id,
            ProvenanceAttributes.ATTESTATION_URI: attestation_uri,
            ProvenanceAttributes.ATTESTATION_TIMESTAMP: attestation_timestamp,
            ProvenanceAttributes.CALLBACK_URI: callback_uri,
            ProvenanceAttributes.CALLBACK_METHOD: callback_method,
            ProvenanceAttributes.CALLBACK_STATUS: callback_status,
            ProvenanceAttributes.CHAIN_PARENT_SPAN_ID: parent_span_id,
            ProvenanceAttributes.CHAIN_DEPTH: chain_depth,
            ProvenanceAttributes.CHAIN_ROOT_TASK_ID: root_task_id,
        }
        for key, val in _map.items():
            if val is not None:
                self._attrs[key] = val

        self._span: Span | None = None

    def __enter__(self) -> ProvenanceSpan:
        self._span = self._tracer.start_span(self._name, attributes=self._attrs)
        ctx = trace.set_span_in_context(self._span)
        self._token = contextlib.suppress(Exception) and trace.context_api.attach(ctx)
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, tb: Any) -> bool:
        if self._span is not None:
            if exc_type is not None:
                self._span.set_status(StatusCode.ERROR, str(exc_val))
                self._span.record_exception(exc_val)
            else:
                self._span.set_status(StatusCode.OK)
            self._span.end()
        if hasattr(self, "_token") and self._token:
            with contextlib.suppress(Exception):
                trace.context_api.detach(self._token)
        return False

    @property
    def span(self) -> Span | None:
        return self._span

    def set_grounding(
        self,
        coverage: float | None = None,
        source_count: int | None = None,
        domain_count: int | None = None,
    ) -> None:
        if self._span is None:
            return
        _set_if(self._span, ProvenanceAttributes.OUTPUT_GROUNDING_COVERAGE, coverage)
        _set_if(self._span, ProvenanceAttributes.OUTPUT_GROUNDING_SOURCE_COUNT, source_count)
        _set_if(self._span, ProvenanceAttributes.OUTPUT_GROUNDING_DOMAIN_COUNT, domain_count)

    def set_callback_result(self, status: str) -> None:
        if self._span is None:
            return
        self._span.set_attribute(ProvenanceAttributes.CALLBACK_STATUS, status)

    @staticmethod
    def enrich(
        span: Span,
        *,
        agent_id: str,
        tier: int = 1,
        source_type: str | None = None,
        source_uris: Sequence[str] | None = None,
        confidence: float | None = None,
        model_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Set provenance attributes on an existing span."""
        span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)
        span.set_attribute(ProvenanceAttributes.OUTPUT_PROVENANCE_TIER, tier)
        _set_if(span, ProvenanceAttributes.OUTPUT_SOURCE_TYPE, source_type)
        if source_uris:
            span.set_attribute(ProvenanceAttributes.OUTPUT_SOURCE_URI, list(source_uris))
        _set_if(span, ProvenanceAttributes.OUTPUT_CONFIDENCE, confidence)
        _set_if(span, ProvenanceAttributes.OUTPUT_MODEL_NAME, model_name)
        for key, val in kwargs.items():
            attr_key = getattr(ProvenanceAttributes, key.upper(), None)
            if attr_key and val is not None:
                span.set_attribute(attr_key, val)


class DerivationSpan:
    """Context manager that creates a span with derivation lineage attributes."""

    def __init__(
        self,
        tracer: Tracer | None = None,
        *,
        name: str = "agent.derivation",
        input_spans: Sequence[str] | None = None,
        input_agents: Sequence[str] | None = None,
        strategy: str | None = None,
        weights: Sequence[float] | None = None,
    ):
        self._tracer = tracer or trace.get_tracer(_TRACER_NAME)
        self._name = name
        self._attrs: dict[str, Any] = {}

        if input_spans:
            self._attrs[DerivationAttributes.INPUT_SPANS] = list(input_spans)
        if input_agents:
            self._attrs[DerivationAttributes.INPUT_AGENTS] = list(input_agents)
        _set_map = {
            DerivationAttributes.STRATEGY: strategy,
        }
        for key, val in _set_map.items():
            if val is not None:
                self._attrs[key] = val
        if weights:
            self._attrs[DerivationAttributes.WEIGHT] = list(weights)

        self._span: Span | None = None

    def __enter__(self) -> DerivationSpan:
        self._span = self._tracer.start_span(self._name, attributes=self._attrs)
        ctx = trace.set_span_in_context(self._span)
        self._token = contextlib.suppress(Exception) and trace.context_api.attach(ctx)
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, tb: Any) -> bool:
        if self._span is not None:
            if exc_type is not None:
                self._span.set_status(StatusCode.ERROR, str(exc_val))
                self._span.record_exception(exc_val)
            else:
                self._span.set_status(StatusCode.OK)
            self._span.end()
        if hasattr(self, "_token") and self._token:
            with contextlib.suppress(Exception):
                trace.context_api.detach(self._token)
        return False

    @property
    def span(self) -> Span | None:
        return self._span

    @staticmethod
    def enrich(
        span: Span,
        *,
        input_spans: Sequence[str] | None = None,
        input_agents: Sequence[str] | None = None,
        strategy: str | None = None,
        weights: Sequence[float] | None = None,
    ) -> None:
        """Set derivation attributes on an existing span."""
        if input_spans:
            span.set_attribute(DerivationAttributes.INPUT_SPANS, list(input_spans))
        if input_agents:
            span.set_attribute(DerivationAttributes.INPUT_AGENTS, list(input_agents))
        _set_if(span, DerivationAttributes.STRATEGY, strategy)
        if weights:
            span.set_attribute(DerivationAttributes.WEIGHT, list(weights))


class AcceptanceSpan:
    """Context manager that creates a span with acceptance criteria attributes."""

    def __init__(
        self,
        tracer: Tracer | None = None,
        *,
        name: str = "agent.acceptance",
        task_id: str,
        acceptance_criteria: str | None = None,
        met: bool | None = None,
        score: float | None = None,
        strategy: str | None = None,
        evaluator: str | None = None,
        factors: Sequence[str] | None = None,
    ):
        self._tracer = tracer or trace.get_tracer(_TRACER_NAME)
        self._name = name
        self._attrs: dict[str, Any] = {}

        self._attrs[AcceptanceAttributes.TASK_ID] = task_id
        _map = {
            AcceptanceAttributes.ACCEPTANCE_CRITERIA: acceptance_criteria,
            AcceptanceAttributes.ACCEPTANCE_MET: met,
            AcceptanceAttributes.ACCEPTANCE_SCORE: score,
            AcceptanceAttributes.ACCEPTANCE_STRATEGY: strategy,
            AcceptanceAttributes.ACCEPTANCE_EVALUATOR: evaluator,
        }
        for key, val in _map.items():
            if val is not None:
                self._attrs[key] = val
        if factors:
            self._attrs[AcceptanceAttributes.ACCEPTANCE_FACTORS] = list(factors)

        self._span: Span | None = None

    def __enter__(self) -> AcceptanceSpan:
        self._span = self._tracer.start_span(self._name, attributes=self._attrs)
        ctx = trace.set_span_in_context(self._span)
        self._token = contextlib.suppress(Exception) and trace.context_api.attach(ctx)
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, tb: Any) -> bool:
        if self._span is not None:
            if exc_type is not None:
                self._span.set_status(StatusCode.ERROR, str(exc_val))
                self._span.record_exception(exc_val)
            else:
                self._span.set_status(StatusCode.OK)
            self._span.end()
        if hasattr(self, "_token") and self._token:
            with contextlib.suppress(Exception):
                trace.context_api.detach(self._token)
        return False

    @property
    def span(self) -> Span | None:
        return self._span

    def set_result(self, *, met: bool, score: float | None = None) -> None:
        if self._span is None:
            return
        self._span.set_attribute(AcceptanceAttributes.ACCEPTANCE_MET, met)
        _set_if(self._span, AcceptanceAttributes.ACCEPTANCE_SCORE, score)

    @staticmethod
    def enrich(
        span: Span,
        *,
        task_id: str,
        met: bool | None = None,
        score: float | None = None,
        strategy: str | None = None,
        evaluator: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Set acceptance attributes on an existing span."""
        span.set_attribute(AcceptanceAttributes.TASK_ID, task_id)
        _set_if(span, AcceptanceAttributes.ACCEPTANCE_MET, met)
        _set_if(span, AcceptanceAttributes.ACCEPTANCE_SCORE, score)
        _set_if(span, AcceptanceAttributes.ACCEPTANCE_STRATEGY, strategy)
        _set_if(span, AcceptanceAttributes.ACCEPTANCE_EVALUATOR, evaluator)
