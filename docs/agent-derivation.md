# Semantic Conventions for Agent Derivation Lineage

**Status:** Development

## Overview

These conventions capture the multi-agent dependency graph: which agent outputs derived from which other agent outputs, with what strategy and relative contribution. This is the layer absent from both Google and Microsoft stacks today.

While the existing `gen_ai.agent.parent_id` (proposed in PR #2247) captures graph topology (structural parent-child), derivation lineage captures *causal contribution*: "Agent B's output derived 60% from Agent A's analysis and 40% from its own tool call."

## Use Cases

- **Root cause analysis**: When a multi-agent system produces an incorrect output, trace back through the derivation chain to find which agent's contribution was the source of error.
- **Cost attribution**: Attribute the cost of a final output to the contributing agents proportionally.
- **Compliance**: Demonstrate the full provenance chain from original task to final output for regulatory or audit purposes.
- **Consensus verification**: When multiple agents vote on an output, capture the individual contributions and aggregation strategy.

## Attributes

| Attribute | Type | Requirement Level | Description | Examples |
|-----------|------|-------------------|-------------|----------|
| `agent.derivation.input_spans` | string[] | Conditional | Span IDs of upstream outputs consumed | `["span-abc", "span-def"]` |
| `agent.derivation.input_agents` | string[] | Conditional | Agent IDs that contributed input | `["researcher", "analyst"]` |
| `agent.derivation.strategy` | enum | Recommended | How inputs were combined | `synthesis` |
| `agent.derivation.weight` | double[] | Recommended | Relative contribution per input | `[0.6, 0.4]` |

## Strategy Values

| Value | Description |
|-------|-------------|
| `synthesis` | Output synthesizes multiple inputs into a new result |
| `delegation` | Output was delegated to a sub-agent and returned as-is or lightly edited |
| `pipeline` | Output is the result of a sequential pipeline (each agent transforms the previous) |
| `consensus` | Output was produced by aggregating or voting across multiple agent outputs |
| `review` | Output is a review, critique, or evaluation of another agent's output |

## Example: AutoGen Multi-Agent Conversation

```
Root span: invoke_agent "orchestrator"
  |
  +-- invoke_agent "researcher"
  |     agent.derivation.strategy = "delegation"
  |     agent.derivation.input_spans = []  (root agent, no upstream)
  |     agent.provenance.chain.depth = 0
  |
  +-- invoke_agent "analyst"
  |     agent.derivation.input_spans = ["<researcher_span_id>"]
  |     agent.derivation.input_agents = ["researcher"]
  |     agent.derivation.strategy = "synthesis"
  |     agent.derivation.weight = [1.0]
  |     agent.provenance.chain.depth = 1
  |
  +-- invoke_agent "writer"
        agent.derivation.input_spans = ["<researcher_span_id>", "<analyst_span_id>"]
        agent.derivation.input_agents = ["researcher", "analyst"]
        agent.derivation.strategy = "synthesis"
        agent.derivation.weight = [0.3, 0.7]
        agent.provenance.chain.depth = 2
```

This trace tells you: the writer's output derived 30% from the researcher's work and 70% from the analyst's synthesis. If the final output contains a factual error, you can follow the derivation chain back to identify whether the researcher retrieved bad data or the analyst misinterpreted it.

## Relationship to Span Parent-Child

Derivation lineage is orthogonal to span parent-child relationships:

- **Span parent-child**: Structural -- "this span was called within that span's execution context"
- **Derivation lineage**: Causal -- "this output was produced using that output as input"

A span may have a parent span that is unrelated to its derivation (e.g., an orchestrator span is the parent of all sub-agent spans, but the sub-agents may derive from each other, not from the orchestrator).
