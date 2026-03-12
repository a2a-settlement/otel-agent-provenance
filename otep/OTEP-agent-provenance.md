# OTEP: Agent Provenance, Derivation Lineage, and Acceptance Criteria Semantic Conventions

**Status:** Draft
**Author:** A2A Settlement Project
**Target SIG:** Semantic Conventions SIG, AI Working Group
**Adjacent Work:** `gen_ai.*` namespace (gen_ai.agent.id, gen_ai.agent.name, etc.)

## Summary

This proposal defines semantic conventions for three capabilities absent from the current OpenTelemetry specification:

1. **Agent Output Provenance** (`agent.output.*`, `agent.provenance.*`) -- three-tier attestation model (self-declared, signed/hash-verified, verifiable callback) for agent outputs
2. **Multi-Agent Derivation Lineage** (`agent.derivation.*`) -- causal dependency graph linking which agent outputs derived from which other agent outputs
3. **Task Acceptance Criteria Evaluation** (`agent.task.acceptance_criteria.*`) -- structured evaluation loop for whether agent output meets a task specification

These conventions extend above the existing `gen_ai.*` agent conventions, which define agent identity and invocation patterns but do not address provenance verification, causal contribution tracking, or structured output evaluation.

## Motivation

### The Observability Gap

Current `gen_ai.*` conventions capture *what* an agent did (which model, which tools, how many tokens) but not *why we should trust it*. As autonomous agents are deployed in production systems making economic decisions, the observability community needs conventions for:

- **Provenance**: Where did this output come from? Can the claim be verified?
- **Derivation**: In a multi-agent system, which agents contributed to this output and how?
- **Acceptance**: Did this output meet the task specification, and how was that evaluated?

### Platform-Specific Gaps

**Google Vertex AI / ADK** already emits structured grounding metadata (`groundingChunks`, `groundingSupports`, `searchEntryPoint`) that maps mechanically to provenance attributes. A thin adapter library translates this into OTel attributes.

**Microsoft's stack** has three distinct instrumentation gaps:

1. **Azure AI Search + Semantic Kernel**: Search results are returned to the agent, but there is no standardised way to capture which results actually influenced the output versus which were retrieved but ignored. The `retrieval` operation type exists but only models "search happened" -- not "these results influenced the generation."

2. **AutoGen multi-agent conversations**: When Agent A hands a message to Agent B, and Agent B produces output, there is no metadata linking B's output to A's contribution. The span tree shows structural parent-child relationships but not causal contribution.

3. **No acceptance criteria evaluation loop**: In Microsoft's stack, an agent produces output and the task is done. There is no structured check of "did this meet the task specification?" with strategy selection (LLM judge, hash match, human review) and confidence scoring.

### The Strategic Value of Standardisation

Whoever defines the semantic convention owns the schema that every observability vendor implements against. The conventions inherently reference verification infrastructure -- when an observability dashboard shows `agent.provenance.attestation.uri`, that is a live link to a verification backend. Standardising provenance conventions drives adoption of the verification ecosystem.

## Proposal

### Namespace

We propose the `agent.*` namespace rather than extending `gen_ai.provenance.*`:

- `agent.*` is broader than LLM calls -- it covers any autonomous software agent
- The market is moving toward multi-agent systems beyond pure LLM wrappers
- `gen_ai.*` positions provenance as an AI sub-feature; `agent.*` positions it as a first-class domain

The conventions explicitly reference and interoperate with existing `gen_ai.agent.id`, `gen_ai.agent.name`, and `gen_ai.agent.version` attributes.

### Three-Tier Provenance Model

#### Tier 1 -- Self-Declared Provenance

Attributes any agent can emit without infrastructure:

| Attribute | Type | Requirement | Description |
|-----------|------|-------------|-------------|
| `agent.id` | string | Required | Unique agent identifier |
| `agent.identity.tier` | int | Conditional | KYA verification tier (1/2/3) |
| `agent.identity.registry` | string | Recommended | Issuing registry |
| `agent.output.provenance.tier` | int | Required | Attestation tier (1/2/3) |
| `agent.output.source.type` | enum | Required | model_generation, retrieval, tool_call, agent_delegation, hybrid |
| `agent.output.source.uri` | string[] | Recommended | Source URIs that influenced output |
| `agent.output.source.influence` | enum | Recommended | attended, cited, ignored |
| `agent.output.confidence` | double | Recommended | Calibrated confidence (0.0-1.0) |
| `agent.output.model.name` | string | Recommended | Model that produced the output |
| `agent.output.model.version` | string | Recommended | Model version/checkpoint |
| `agent.output.grounding.coverage` | double | Recommended | Fraction of output grounded by sources |
| `agent.output.grounding.source_count` | int | Recommended | Number of distinct sources |
| `agent.output.grounding.domain_count` | int | Recommended | Number of distinct domains |

#### Tier 2 -- Signed / Hash-Verified Provenance

| Attribute | Type | Requirement | Description |
|-----------|------|-------------|-------------|
| `agent.output.hash.algorithm` | enum | Conditional (tier >= 2) | sha256, sha3-256, sha384, sha512 |
| `agent.output.hash.value` | string | Conditional (tier >= 2) | Hex-encoded content hash |
| `agent.output.signature.method` | enum | Conditional (tier >= 2) | hmac, ed25519, x509 |
| `agent.output.signature.value` | string | Conditional | Base64-encoded signature |
| `agent.output.signature.key_id` | string | Conditional | Signing key reference |
| `agent.provenance.attestation.uri` | string | Conditional (tier >= 2) | Attestation record URI |
| `agent.provenance.attestation.timestamp` | string | Conditional (tier >= 2) | RFC 3339 timestamp |

#### Tier 3 -- Verifiable Source Callback

| Attribute | Type | Requirement | Description |
|-----------|------|-------------|-------------|
| `agent.provenance.callback.uri` | string | Conditional (tier = 3) | Live verification endpoint |
| `agent.provenance.callback.method` | enum | Conditional | GET or POST |
| `agent.provenance.callback.status` | enum | Recommended | verified, expired, revoked |
| `agent.provenance.chain.parent_span_id` | string | Recommended | Parent agent's span ID |
| `agent.provenance.chain.depth` | int | Recommended | Agent hops from root |
| `agent.provenance.chain.root_task_id` | string | Recommended | Original task/bounty ID |

### Derivation Lineage

| Attribute | Type | Requirement | Description |
|-----------|------|-------------|-------------|
| `agent.derivation.input_spans` | string[] | Conditional | Span IDs of consumed upstream outputs |
| `agent.derivation.input_agents` | string[] | Conditional | Agent IDs that contributed |
| `agent.derivation.strategy` | enum | Recommended | synthesis, delegation, pipeline, consensus, review |
| `agent.derivation.weight` | double[] | Recommended | Relative contribution per input |

### Acceptance Criteria Evaluation

| Attribute | Type | Requirement | Description |
|-----------|------|-------------|-------------|
| `agent.task.id` | string | Required | Task or bounty identifier |
| `agent.task.acceptance_criteria` | string | Recommended | Hash or URI of acceptance spec |
| `agent.task.acceptance_criteria.met` | boolean | Conditional | Whether output met criteria |
| `agent.task.acceptance_criteria.score` | double | Recommended | Evaluation score (0.0-1.0) |
| `agent.task.acceptance_criteria.strategy` | enum | Recommended | llm, hash, human, hybrid, automated |
| `agent.task.acceptance_criteria.evaluator` | string | Recommended | Evaluator identifier |
| `agent.task.acceptance_criteria.factors` | string[] | Recommended | Evaluation factors considered |

## Reference Implementation

A reference implementation is available at `otel-agent-provenance` providing:

- YAML semantic convention definitions in OTel `model/` format
- Python constants module with all attribute keys
- Span builder helpers for each convention group
- Framework adapters for Google ADK, Azure AI Search, Semantic Kernel, and AutoGen
- Settlement exchange/mediator/shim instrumentors demonstrating the verification backend integration

## Prior Art

- `gen_ai.agent.id`, `gen_ai.agent.name` -- agent identity (current OTel spec)
- `gen_ai.evaluation.score.value` -- basic evaluation (current OTel spec)
- `gen_ai.agent.node.*` -- agent graph topology (PR #2247)
- `gen_ai.data_source.id` -- data source identification (current OTel spec)
- Agent semantic conventions (PR #950) -- established the `agent.*` namespace precedent

## Trade-offs

### `agent.*` vs `gen_ai.provenance.*`

Using `agent.*` is broader and future-proof but creates a new top-level namespace. Using `gen_ai.provenance.*` would sit within the existing AI conventions and may get faster adoption but narrows the framing to generative AI. We recommend `agent.*` because autonomous software agents are not exclusively generative AI systems.

### Attestation URI as infrastructure reference

The `agent.provenance.attestation.uri` attribute creates an implicit dependency on verification infrastructure. This is intentional: the convention defines vocabulary, and the verification backend provides the semantic guarantee. However, the conventions are useful even without a verification backend (Tier 1 is purely self-declared).
