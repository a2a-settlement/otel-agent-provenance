# Gap Analysis: Agent Provenance in OpenTelemetry

## Executive Summary

The OpenTelemetry `gen_ai.*` semantic conventions define how to observe what an agent *does* (model calls, tool use, token consumption) but not why we should *trust* its output. Three critical gaps exist in the current ecosystem, most acutely in Microsoft's AI stack. This document maps each gap to the specific platform deficiency and shows how the `agent.*` provenance conventions fill it.

## Current OTel Coverage

The `gen_ai.*` conventions (Development status, as of March 2026) cover:

| Domain | Attributes | Status |
|--------|-----------|--------|
| Agent identity | `gen_ai.agent.id`, `.name`, `.version`, `.description` | Defined |
| Operations | `create_agent`, `invoke_agent`, `execute_tool`, `retrieval` | Defined |
| LLM calls | `gen_ai.request.model`, `.response.model`, `.usage.*` | Defined |
| Messages | `gen_ai.input.messages`, `.output.messages` | Defined |
| Tools | `gen_ai.tool.definitions` | Defined |
| Data sources | `gen_ai.data_source.id` | Defined |
| Evaluation | `gen_ai.evaluation.score.value`, `.name` | Defined |
| Graph topology | `gen_ai.agent.node.*`, `gen_ai.agent.parent_id` | Proposed (PR #2247) |

### What is NOT covered

| Domain | Status | Impact |
|--------|--------|--------|
| Output provenance (source verification) | **Absent** | No way to verify where output came from |
| Source influence tracking (retrieval -> generation link) | **Absent** | RAG pipeline is opaque |
| Content integrity (hash, signature) | **Absent** | No tamper detection |
| Attestation (verifiable claims) | **Absent** | No link to verification infrastructure |
| Multi-agent causal derivation | **Absent** | Can't trace which agent contributed what |
| Acceptance criteria evaluation | **Basic** | `evaluation.score` exists but no structured protocol |

## The Three Microsoft Gaps

### Gap 1: RAG Retrieval Influence Chain

**Affected platforms:** Azure AI Search, Semantic Kernel, Azure AI Foundry

**The problem:** A RAG pipeline has three stages:
1. **Retrieval**: Documents/chunks returned from search
2. **Selection**: Which documents enter the model's context window
3. **Generation**: What the model produces from those sources

OTel's `retrieval` operation type covers stage 1. Stages 2 and 3 are invisible. There is no convention for "these 3 of 10 retrieved documents actually influenced the output."

**Google comparison:** Vertex AI / ADK returns `groundingChunks[].web.uri` (which sources), `groundingSupports[].segment` (which output segments are grounded), and `groundingMetadata.coverage` (how much output is grounded). This is structured, machine-readable, and maps directly to provenance attributes.

**Microsoft's position:** Semantic Kernel has plugin hooks (`IFunctionFilter`) where instrumentation could be injected, but nobody has defined what to capture. The retrieval step returns results; the generation step produces output; the link between them is developer-specific.

**Convention fill:**
- `agent.output.source.uri` -- which sources influenced the output
- `agent.output.source.influence` -- `attended` | `cited` | `ignored`
- `agent.output.grounding.coverage` -- fraction of output grounded
- `agent.output.grounding.source_count` / `.domain_count` -- diversity metrics

### Gap 2: Multi-Agent Derivation Chain

**Affected platforms:** AutoGen, Semantic Kernel multi-agent

**The problem:** AutoGen emits `invoke_agent` spans with sender/receiver types (improved in PR #6499, May 2025). The proposed `gen_ai.agent.parent_id` (PR #2247) captures graph topology. But neither captures *causal contribution*:

- Structural: "Agent A called Agent B" (span parent-child)
- Causal: "Agent B's output derived 60% from Agent A's analysis and 40% from its own tool call" (derivation lineage)

When a multi-agent system produces an incorrect output, you need to trace which agent's contribution caused the error. The span tree tells you the execution order; derivation lineage tells you the causal chain.

**Google comparison:** ADK's grounding metadata partially addresses this for single-agent RAG (which sources influenced the output), but multi-agent derivation is equally absent from Google's stack.

**Convention fill:**
- `agent.derivation.input_spans` -- span IDs of consumed upstream outputs
- `agent.derivation.input_agents` -- agent IDs that contributed
- `agent.derivation.strategy` -- `synthesis` | `delegation` | `pipeline` | `consensus`
- `agent.derivation.weight` -- relative contribution per input

### Gap 3: Acceptance Criteria Evaluation Loop

**Affected platforms:** AutoGen, Semantic Kernel, all Microsoft AI frameworks

**The problem:** In Microsoft's stack, an agent produces output and the task is complete. There is no structured protocol for evaluating whether the output meets the task specification. The existing `gen_ai.evaluation.score.value` attribute is a single number with no:
- Evaluation strategy (who or what evaluated it)
- Multiple evaluation factors
- Confidence threshold for auto-resolution vs. human escalation
- Link back to the acceptance specification

**Google comparison:** Google's ADK has no built-in acceptance evaluation either. This is a gap across the entire ecosystem, but it is most impactful in Microsoft's stack where multi-agent orchestration (AutoGen) produces outputs that need structured verification.

**Reference implementation:** The A2A-SE AI Mediator implements a 7-factor evaluation framework with confidence-gated auto-resolution, demonstrating the pattern:
1. Deliverable completeness
2. Acceptance criteria specificity
3. Dispute substantiation
4. Reputation history
5. Proportionality
6. Provenance attestation
7. Web grounding

**Convention fill:**
- `agent.task.acceptance_criteria` -- hash/URI of the specification
- `agent.task.acceptance_criteria.met` -- boolean result
- `agent.task.acceptance_criteria.score` -- evaluation score
- `agent.task.acceptance_criteria.strategy` -- `llm` | `hash` | `human` | `hybrid`
- `agent.task.acceptance_criteria.evaluator` -- who evaluated
- `agent.task.acceptance_criteria.factors` -- which factors were considered

## The A2A-SE Wedge

The conventions inherently reference verification infrastructure:

```
Convention defines vocabulary
  -> Observability vendors display the attributes
    -> agent.provenance.attestation.uri points to verification backend
      -> Verification backend is the A2A-SE exchange
```

This creates a flywheel:
1. Define the convention (OTEP) -- standards credibility
2. Ship instrumentation for Microsoft's gaps -- reference implementation
3. Convention attributes reference the exchange -- adoption driver
4. Observability vendors implement the convention -- ecosystem lock-in

Google users get provenance "for free" (thin adapter to existing grounding metadata). Microsoft users need new instrumentation. Whoever provides that instrumentation defines how Microsoft's stack reports provenance.

## Adapter Complexity Comparison

| Platform | Adapter complexity | Reason |
|----------|-------------------|--------|
| Google Vertex AI / ADK | ~200 lines | Mechanical mapping from structured grounding metadata |
| Azure AI Search | ~300 lines | Three-stage RAG pipeline instrumentation (retrieval/selection/generation) |
| Semantic Kernel | ~250 lines | Plugin filter hooks + URI extraction from search results |
| AutoGen | ~250 lines | Runtime monkey-patch for derivation tracking across agent handoffs |
| A2A-SE Exchange | ~200 lines | Map existing Provenance schema to OTel attributes |
| A2A-SE Mediator | ~150 lines | Map verdict/evaluation to acceptance criteria attributes |
| A2A-SE Shim | ~150 lines | Economic Air Gap proxy instrumentation |
