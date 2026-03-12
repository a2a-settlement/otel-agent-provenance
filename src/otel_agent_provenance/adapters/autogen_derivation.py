"""Adapter: AutoGen multi-agent derivation chain -> OTel provenance spans.

This addresses Microsoft Gap #2: multi-agent provenance chains.

AutoGen emits ``create_agent``, ``invoke_agent``, and ``execute_tool``
spans with sender/receiver agent types, but there is no metadata linking
Agent B's output to Agent A's contribution.  The span tree shows
"A called B" but not "B's output derived from A's analysis."

This adapter hooks into AutoGen's runtime to:
1. Track which agent spans produce outputs consumed by downstream agents
2. Set ``agent.derivation.*`` attributes creating causal links
3. Maintain a provenance chain with depth and root task tracking

Usage::

    from otel_agent_provenance.adapters.autogen_derivation import (
        AutoGenDerivationTracker,
        enrich_agent_span,
    )

    tracker = AutoGenDerivationTracker()

    # When Agent A produces output:
    tracker.record_output(agent_id="agent-a", span_id="span-123")

    # When Agent B consumes A's output and produces its own:
    tracker.record_derivation(
        agent_id="agent-b",
        span=current_span,
        input_agent_ids=["agent-a"],
        strategy="synthesis",
    )
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Sequence

from opentelemetry import trace
from opentelemetry.trace import Span, Tracer

from otel_agent_provenance.conventions import (
    DerivationAttributes,
    DerivationStrategy,
    ProvenanceAttributes,
)


@dataclass
class _AgentOutput:
    """Tracks an agent's output span for derivation linking."""

    agent_id: str
    span_id: str
    span_context: Any = None


class AutoGenDerivationTracker:
    """Tracks multi-agent derivation chains in AutoGen conversations.

    Thread-safe tracker that maintains a registry of agent outputs and
    creates derivation links when downstream agents consume upstream
    outputs.

    Typical integration point: wrap AutoGen's runtime message handlers
    to call ``record_output`` when an agent produces a message and
    ``record_derivation`` when an agent processes messages from others.
    """

    def __init__(
        self,
        tracer: Tracer | None = None,
        *,
        root_task_id: str = "",
    ):
        self._tracer = tracer or trace.get_tracer("otel_agent_provenance.autogen")
        self._root_task_id = root_task_id
        self._outputs: dict[str, _AgentOutput] = {}
        self._chain_depth: dict[str, int] = {}
        self._lock = threading.Lock()

    def record_output(
        self,
        agent_id: str,
        span_id: str,
        *,
        span_context: Any = None,
    ) -> None:
        """Register that an agent produced output at a given span."""
        with self._lock:
            self._outputs[agent_id] = _AgentOutput(
                agent_id=agent_id,
                span_id=span_id,
                span_context=span_context,
            )
            if agent_id not in self._chain_depth:
                self._chain_depth[agent_id] = 0

    def record_derivation(
        self,
        agent_id: str,
        span: Span,
        *,
        input_agent_ids: Sequence[str],
        strategy: str = DerivationStrategy.SYNTHESIS,
        weights: Sequence[float] | None = None,
    ) -> None:
        """Set derivation attributes on a span based on consumed inputs.

        Looks up the registered output spans for each input agent and
        creates ``agent.derivation.*`` links on the current span.
        """
        with self._lock:
            input_spans: list[str] = []
            valid_agents: list[str] = []
            max_depth = 0

            for aid in input_agent_ids:
                output = self._outputs.get(aid)
                if output:
                    input_spans.append(output.span_id)
                    valid_agents.append(aid)
                    max_depth = max(max_depth, self._chain_depth.get(aid, 0))

            depth = max_depth + 1
            self._chain_depth[agent_id] = depth

        if input_spans:
            span.set_attribute(DerivationAttributes.INPUT_SPANS, input_spans)
        if valid_agents:
            span.set_attribute(DerivationAttributes.INPUT_AGENTS, valid_agents)

        span.set_attribute(DerivationAttributes.STRATEGY, strategy)

        if weights and len(weights) == len(valid_agents):
            span.set_attribute(DerivationAttributes.WEIGHT, list(weights))

        span.set_attribute(ProvenanceAttributes.CHAIN_DEPTH, depth)
        if self._root_task_id:
            span.set_attribute(
                ProvenanceAttributes.CHAIN_ROOT_TASK_ID, self._root_task_id
            )

    def get_chain_depth(self, agent_id: str) -> int:
        with self._lock:
            return self._chain_depth.get(agent_id, 0)

    def get_output_span_id(self, agent_id: str) -> str | None:
        with self._lock:
            output = self._outputs.get(agent_id)
            return output.span_id if output else None

    def reset(self) -> None:
        with self._lock:
            self._outputs.clear()
            self._chain_depth.clear()


def enrich_agent_span(
    span: Span,
    *,
    agent_id: str,
    input_agent_ids: Sequence[str] | None = None,
    input_span_ids: Sequence[str] | None = None,
    strategy: str = DerivationStrategy.SYNTHESIS,
    weights: Sequence[float] | None = None,
    chain_depth: int | None = None,
    root_task_id: str | None = None,
) -> None:
    """One-shot enrichment of an AutoGen agent span with derivation attributes.

    Use this when you have direct access to the span and know the
    derivation inputs, without needing the tracker's registry.
    """
    span.set_attribute(ProvenanceAttributes.AGENT_ID, agent_id)

    if input_span_ids:
        span.set_attribute(DerivationAttributes.INPUT_SPANS, list(input_span_ids))
    if input_agent_ids:
        span.set_attribute(DerivationAttributes.INPUT_AGENTS, list(input_agent_ids))

    span.set_attribute(DerivationAttributes.STRATEGY, strategy)

    if weights:
        span.set_attribute(DerivationAttributes.WEIGHT, list(weights))
    if chain_depth is not None:
        span.set_attribute(ProvenanceAttributes.CHAIN_DEPTH, chain_depth)
    if root_task_id:
        span.set_attribute(ProvenanceAttributes.CHAIN_ROOT_TASK_ID, root_task_id)


def instrument_autogen_runtime(
    runtime: Any,
    tracker: AutoGenDerivationTracker,
) -> None:
    """Monkey-patch an AutoGen runtime to automatically track derivation.

    Wraps ``process_message`` (or equivalent) on SingleThreadedAgentRuntime
    to call ``tracker.record_output`` and ``tracker.record_derivation``
    as messages flow between agents.

    This is a best-effort hook -- AutoGen's internal API may change.
    The adapter degrades gracefully if the expected methods are absent.
    """
    original_process = getattr(runtime, "_process_send", None)
    if original_process is None:
        return

    async def _patched_process(message: Any, *, sender: Any, recipient: Any) -> Any:
        sender_id = _extract_agent_id(sender)
        recipient_id = _extract_agent_id(recipient)

        current_span = trace.get_current_span()
        span_ctx = current_span.get_span_context()
        span_id = format(span_ctx.span_id, "016x") if span_ctx.is_valid else ""

        if sender_id and span_id:
            tracker.record_output(sender_id, span_id)

        result = await original_process(message, sender=sender, recipient=recipient)

        if recipient_id and sender_id:
            result_span = trace.get_current_span()
            result_ctx = result_span.get_span_context()
            result_span_id = (
                format(result_ctx.span_id, "016x") if result_ctx.is_valid else ""
            )
            if result_span_id:
                tracker.record_output(recipient_id, result_span_id)
                tracker.record_derivation(
                    agent_id=recipient_id,
                    span=result_span,
                    input_agent_ids=[sender_id],
                    strategy=DerivationStrategy.DELEGATION,
                )

        return result

    runtime._process_send = _patched_process


def _extract_agent_id(agent: Any) -> str:
    for attr in ("id", "agent_id", "name", "_agent_id"):
        val = getattr(agent, attr, None)
        if val and isinstance(val, str):
            return val
    return str(agent) if agent else ""
