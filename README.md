# otel-agent-provenance

OpenTelemetry semantic conventions and instrumentation for **agent provenance**, **derivation lineage**, and **acceptance criteria evaluation**.

## Why This Exists

OpenTelemetry's `gen_ai.*` conventions tell you *what* an agent did -- which model it called, how many tokens it used, which tools it invoked. They do not tell you *why you should trust the output*. As autonomous agents make economic decisions, delegate to sub-agents, and produce outputs that drive real-world actions, three questions become critical:

1. **Provenance** -- Where did this output come from? Can the claim be verified?
2. **Derivation** -- In a multi-agent system, which agents contributed to this output, and how?
3. **Acceptance** -- Did this output meet the task specification, and how was that determined?

None of these are covered by the current OTel specification. This repo defines the conventions, provides framework-specific adapters, and includes an [OTEP draft](otep/OTEP-agent-provenance.md) for upstream submission.

## The Microsoft Gap

These gaps are most acute in Microsoft's AI stack. See [docs/gap-analysis.md](docs/gap-analysis.md) for the full analysis.

| Gap | Problem | Affected Platforms | Convention Fill |
|-----|---------|-------------------|-----------------|
| **RAG retrieval influence** | Azure AI Search returns N results, but there's no way to capture which results actually influenced the output vs. which were retrieved and ignored | Azure AI Search, Semantic Kernel | `agent.output.source.influence`, `agent.output.grounding.*` |
| **Multi-agent derivation** | When Agent A hands a message to Agent B, there's no metadata linking B's output to A's contribution -- the span tree shows structure, not causation | AutoGen, multi-agent orchestration | `agent.derivation.input_spans`, `agent.derivation.strategy`, `agent.derivation.weight` |
| **Acceptance criteria evaluation** | An agent produces output and the task is done -- no structured check of "did this meet the spec?" with strategy selection and confidence gating | AutoGen, Semantic Kernel, all frameworks | `agent.task.acceptance_criteria.*` |

**Google's position is different**: Vertex AI / ADK already emits structured grounding metadata (`groundingChunks`, `groundingSupports`, coverage scores). A [~180-line adapter](src/otel_agent_provenance/adapters/google_grounding.py) translates this mechanically into OTel attributes. Google users get provenance "for free."

**Microsoft's gaps are structural**: They require new instrumentation at the Semantic Kernel plugin layer, the AutoGen runtime layer, and an entirely new acceptance evaluation component. Whoever provides that instrumentation defines how Microsoft's stack reports provenance.

## Three-Tier Provenance Model

The conventions follow a progressive trust model. Each tier builds on the previous:

| Tier | Name | What It Provides | Infrastructure Required |
|------|------|-----------------|------------------------|
| **1** | Self-Declared | Agent reports its own sources, model, and confidence | None -- any agent can emit these |
| **2** | Signed / Hash-Verified | Content hash, digital signature, attestation record on a verification backend | Signing keys + attestation service |
| **3** | Verifiable Callback | Live endpoint that confirms provenance claims in real-time | Verification backend (e.g. A2A-SE exchange) |

When an observability dashboard shows `agent.provenance.attestation.uri = exchange.a2a-settlement.org/attestation/abc123`, that's a live link to verification infrastructure. The convention defines the vocabulary; the verification backend provides the guarantee.

## Attribute Reference

### Provenance Attributes (`agent.output.*`, `agent.provenance.*`)

| Attribute | Type | Tier | Description |
|-----------|------|------|-------------|
| `agent.id` | string | 1 | Unique agent identifier |
| `agent.identity.tier` | int | 1 | KYA verification tier (1/2/3) |
| `agent.identity.registry` | string | 1 | Identity registry |
| `agent.output.provenance.tier` | int | 1 | Attestation tier of this output (1/2/3) |
| `agent.output.source.type` | enum | 1 | `model_generation`, `retrieval`, `tool_call`, `agent_delegation`, `hybrid` |
| `agent.output.source.uri` | string[] | 1 | Source URIs that influenced the output |
| `agent.output.source.influence` | enum | 1 | `attended`, `cited`, `ignored` -- how sources influenced output |
| `agent.output.confidence` | double | 1 | Calibrated confidence (0.0-1.0) |
| `agent.output.model.name` | string | 1 | Model that produced the output |
| `agent.output.model.version` | string | 1 | Model version/checkpoint |
| `agent.output.grounding.coverage` | double | 1 | Fraction of output grounded by sources |
| `agent.output.grounding.source_count` | int | 1 | Number of distinct grounding sources |
| `agent.output.grounding.domain_count` | int | 1 | Number of distinct source domains |
| `agent.output.hash.algorithm` | enum | 2 | `sha256`, `sha3-256`, `sha384`, `sha512` |
| `agent.output.hash.value` | string | 2 | Hex-encoded content hash |
| `agent.output.signature.method` | enum | 2 | `hmac`, `ed25519`, `x509` |
| `agent.output.signature.value` | string | 2 | Base64-encoded signature |
| `agent.output.signature.key_id` | string | 2 | Signing key reference |
| `agent.provenance.attestation.uri` | string | 2 | Attestation record URI |
| `agent.provenance.attestation.timestamp` | string | 2 | RFC 3339 timestamp |
| `agent.provenance.callback.uri` | string | 3 | Live verification endpoint |
| `agent.provenance.callback.method` | enum | 3 | `GET` or `POST` |
| `agent.provenance.callback.status` | enum | 3 | `verified`, `expired`, `revoked` |
| `agent.provenance.chain.parent_span_id` | string | 1+ | Parent agent's output span ID |
| `agent.provenance.chain.depth` | int | 1+ | Number of agent hops from the root task |
| `agent.provenance.chain.root_task_id` | string | 1+ | Original task/bounty ID |

### Derivation Lineage Attributes (`agent.derivation.*`)

These capture the multi-agent causal dependency graph -- which agent outputs derived from which other outputs. This is the layer absent from both Google and Microsoft today.

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent.derivation.input_spans` | string[] | Span IDs of upstream outputs this agent consumed |
| `agent.derivation.input_agents` | string[] | Agent IDs that contributed input |
| `agent.derivation.strategy` | enum | `synthesis`, `delegation`, `pipeline`, `consensus`, `review` |
| `agent.derivation.weight` | double[] | Relative contribution weight per input (sums to 1.0) |

### Acceptance Criteria Attributes (`agent.task.*`)

These capture the structured evaluation loop: did the output meet the task specification?

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent.task.id` | string | Task or bounty identifier |
| `agent.task.acceptance_criteria` | string | Hash or URI of the acceptance specification |
| `agent.task.acceptance_criteria.met` | boolean | Whether the output met criteria |
| `agent.task.acceptance_criteria.score` | double | Evaluation score (0.0-1.0) |
| `agent.task.acceptance_criteria.strategy` | enum | `llm`, `hash`, `human`, `hybrid`, `automated` |
| `agent.task.acceptance_criteria.evaluator` | string | Who/what performed the evaluation |
| `agent.task.acceptance_criteria.factors` | string[] | Evaluation factors considered |

## Installation

```bash
pip install -e .

# With framework-specific extras:
pip install -e ".[google]"     # Google ADK / Vertex AI grounding adapter
pip install -e ".[azure]"      # Azure AI Search adapter
pip install -e ".[autogen]"    # AutoGen derivation tracking
pip install -e ".[settlement]" # A2A-SE exchange/mediator/shim instrumentation
pip install -e ".[dev]"        # pytest, ruff, mypy
pip install -e ".[all]"        # Everything
```

## Quick Start

### Provenance Span (Tier 1 -- any agent, no infrastructure)

```python
from otel_agent_provenance.spans import ProvenanceSpan

with ProvenanceSpan(
    agent_id="my-agent",
    tier=1,
    source_type="retrieval",
    source_uris=["https://example.com/data"],
    model_name="gpt-4o",
    confidence=0.85,
) as span:
    result = do_work()
    span.set_grounding(coverage=0.82, source_count=3, domain_count=2)
```

### Provenance Span (Tier 2 -- signed with attestation)

```python
with ProvenanceSpan(
    agent_id="my-agent",
    tier=2,
    source_type="retrieval",
    hash_algorithm="sha256",
    hash_value="9f86d081884c7d659a2feaa0c55ad015...",
    signature_method="ed25519",
    attestation_uri="https://exchange.a2a-settlement.org/attestation/abc123",
    attestation_timestamp="2026-03-11T14:30:00Z",
) as span:
    result = do_verified_work()
```

### Derivation Lineage (multi-agent causal chain)

```python
from otel_agent_provenance.spans import DerivationSpan

with DerivationSpan(
    input_agents=["researcher", "analyst"],
    strategy="synthesis",
    weights=[0.4, 0.6],
):
    combined_output = synthesize(research, analysis)
```

### Acceptance Criteria Evaluation

```python
from otel_agent_provenance.spans import AcceptanceSpan

with AcceptanceSpan(
    task_id="task-001",
    strategy="hybrid",
    evaluator="mediator-001",
    factors=["completeness", "provenance", "grounding"],
) as span:
    result = evaluate(output, criteria)
    span.set_result(met=True, score=0.87)
```

### Enrich Existing Spans (no context manager needed)

```python
from otel_agent_provenance.spans import ProvenanceSpan, DerivationSpan

# On any existing OTel span:
ProvenanceSpan.enrich(span, agent_id="my-agent", tier=1, source_type="retrieval")
DerivationSpan.enrich(span, input_agents=["agent-a"], strategy="delegation")
```

## Framework Adapters

### Azure AI Search / Semantic Kernel RAG (Microsoft Gap #1)

The three-stage RAG pipeline tracer instruments what was previously invisible: the retrieval-to-generation influence chain.

```python
from otel_agent_provenance.adapters.azure_rag import RagStageTracer

tracer = RagStageTracer(agent_id="my-rag-agent")

# Stage 1: Retrieval -- which documents came back from search
with tracer.retrieval(query="How does X work?") as stage:
    results = search_client.search(query)
    stage.record_results(results)  # records URIs, scores, domain count

# Stage 2: Selection -- which results entered the model's context window
with tracer.selection() as stage:
    stage.record_context_window(attended=top_3, ignored=rest)

# Stage 3: Generation -- what the model produced and which sources it cited
with tracer.generation(model_name="gpt-4o") as stage:
    output = llm.generate(prompt)
    stage.record_output(output, cited_uris=["..."], coverage=0.75)
```

### AutoGen Multi-Agent Derivation (Microsoft Gap #2)

Tracks causal contribution across AutoGen agent conversations, not just structural parent-child spans.

```python
from otel_agent_provenance.adapters.autogen_derivation import AutoGenDerivationTracker

tracker = AutoGenDerivationTracker(root_task_id="task-001")

# Agent A produces research output
tracker.record_output("agent-a", span_id_a)

# Agent B consumes A's output and produces its own
with tracer.start_as_current_span("invoke_agent agent-b") as span:
    tracker.record_derivation(
        agent_id="agent-b",
        span=span,
        input_agent_ids=["agent-a"],
        strategy="synthesis",
        weights=[1.0],
    )
```

The resulting trace shows: Agent B's output derived from Agent A's research (chain depth 1, root task "task-001").

### Google ADK / Vertex AI Grounding (mechanical adapter)

```python
from otel_agent_provenance.adapters.google_grounding import from_adk_provenance, enrich_span_from_grounding

# From adk-a2a-settlement's build_grounded_provenance() output:
attrs = from_adk_provenance(provenance_dict, agent_id="my-agent")
enrich_span_from_grounding(span, attrs)
```

### Semantic Kernel Plugin Filter

```python
from otel_agent_provenance.adapters.semantic_kernel_rag import ProvenanceFilter

# Auto-instruments all RAG plugin invocations
kernel.add_filter(ProvenanceFilter(agent_id="my-sk-agent"))
```

## Settlement Instruments

For projects using the [A2A Settlement Exchange](https://github.com/a2a-settlement/a2a-settlement), dedicated instrumentors map the exchange's existing provenance schema, mediator evaluation, and security shim operations to OTel spans:

```python
from otel_agent_provenance.instruments.settlement_exchange import ExchangeInstrumentor
from otel_agent_provenance.instruments.settlement_mediator import MediatorInstrumentor
from otel_agent_provenance.instruments.settlement_shim import ShimInstrumentor

# Auto-instrument FastAPI apps
ExchangeInstrumentor(agent_id="exchange-node-1").instrument(exchange_app)
ShimInstrumentor(agent_id="shim-node-1").instrument(shim_app)

# Or use the mediator span builder
with MediatorInstrumentor.mediation_span(escrow_id="esc-123") as span:
    verdict = mediator.mediate(escrow_id)
    MediatorInstrumentor.record_verdict(span, verdict)
```

## Examples

Four runnable examples demonstrate every convention group with in-memory OTel exporters (no backend needed):

```bash
python examples/autogen_provenance.py     # 3-agent derivation chain with depth tracking
python examples/azure_rag_provenance.py   # 5 retrieved -> 3 attended -> 2 cited
python examples/adk_grounding.py          # Google grounding -> OTel in ~10 lines
python examples/settlement_e2e.py         # Full escrow lifecycle (7 spans, all 3 convention groups)
```

## Repository Structure

```
otel-agent-provenance/
  model/                            # YAML semantic convention definitions (OTel format)
    agent-provenance.yaml           #   Tier 1/2/3 provenance attributes
    agent-derivation.yaml           #   Multi-agent derivation lineage
    agent-acceptance.yaml           #   Task acceptance criteria evaluation
  docs/
    agent-provenance.md             # Convention specification
    agent-derivation.md             # Derivation lineage spec
    agent-acceptance.md             # Acceptance criteria spec
    gap-analysis.md                 # Microsoft / Google / OTel gap analysis
  otep/
    OTEP-agent-provenance.md        # OpenTelemetry Enhancement Proposal draft
  src/otel_agent_provenance/
    conventions.py                  # Attribute key constants (52 keys + enum classes)
    spans.py                        # Span builders: ProvenanceSpan, DerivationSpan, AcceptanceSpan
    adapters/
      google_grounding.py           # Google Vertex AI / ADK grounding -> OTel
      azure_rag.py                  # Azure AI Search 3-stage RAG pipeline -> OTel
      autogen_derivation.py         # AutoGen multi-agent derivation chain -> OTel
      semantic_kernel_rag.py        # Semantic Kernel plugin filter -> OTel
    instruments/
      settlement_exchange.py        # A2A-SE exchange escrow lifecycle instrumentation
      settlement_mediator.py        # AI Mediator 7-factor evaluation -> acceptance spans
      settlement_shim.py            # Economic Air Gap proxy instrumentation
  tests/                            # 31 tests
  examples/                         # 4 runnable examples
```

## Tests

```bash
pip install -e ".[dev]"
pytest -v
```

## Relationship to Existing OTel Conventions

These conventions sit above the existing `gen_ai.*` namespace and are designed to interoperate:

| This Repo | Existing OTel | Relationship |
|-----------|---------------|-------------|
| `agent.id` | `gen_ai.agent.id` | May be the same value; provenance `agent.id` is required |
| `agent.output.model.name` | `gen_ai.request.model` | `gen_ai.*` is per-call; `agent.output.*` is per-output |
| `agent.task.acceptance_criteria.score` | `gen_ai.evaluation.score.value` | `gen_ai.*` is a single number; acceptance adds strategy, factors, evaluator |
| `agent.output.source.uri` | `gen_ai.data_source.id` | `gen_ai.*` identifies the data source; `agent.*` identifies specific sources within it |
| `agent.provenance.chain.parent_span_id` | `gen_ai.agent.parent_id` | `gen_ai.*` is structural topology; `agent.*` is causal derivation |

We use `agent.*` rather than `gen_ai.provenance.*` because these conventions apply to any autonomous software agent, not only generative AI systems.

## Related Repositories

| Repository | Role |
|-----------|------|
| [a2a-settlement](https://github.com/a2a-settlement/a2a-settlement) | Settlement Exchange -- escrow, provenance verification, KYA identity |
| [a2a-settlement-mediator](https://github.com/a2a-settlement/a2a-settlement-mediator) | AI Mediator -- 7-factor dispute resolution (reference for acceptance criteria) |
| [adk-a2a-settlement](https://github.com/a2a-settlement/adk-a2a-settlement) | Google ADK integration (source for grounding adapter) |
| [a2a-settlement-auth](https://github.com/a2a-settlement/a2a-settlement-auth) | OAuth + spending limits + SecretVault |
| [a2a-settlement-mcp](https://github.com/a2a-settlement/a2a-settlement-mcp) | MCP server for settlement operations |
| [mcp-trust-gateway](https://github.com/a2a-settlement/mcp-trust-gateway) | MCP trust layer above OAuth |

## License

Apache 2.0
