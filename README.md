# otel-agent-provenance

OpenTelemetry semantic conventions and instrumentation for **agent provenance**, **derivation lineage**, and **acceptance criteria evaluation**.

Fills three gaps in the current OpenTelemetry `gen_ai.*` conventions -- primarily exposed by Microsoft's AI stack (AutoGen, Semantic Kernel, Azure AI Search) -- with a three-tier attestation model, multi-agent causal derivation tracking, and structured output evaluation.

## The Gaps

| Gap | Affected Platforms | Convention Fill |
|-----|-------------------|-----------------|
| **RAG retrieval influence chain** -- which retrieved results actually influenced the output vs. were ignored | Azure AI Search, Semantic Kernel | `agent.output.source.influence`, `agent.output.grounding.*` |
| **Multi-agent derivation** -- which agent outputs derived from which other agent outputs | AutoGen, multi-agent systems | `agent.derivation.input_spans`, `agent.derivation.strategy` |
| **Acceptance criteria evaluation** -- did the output meet the task specification, and how was that evaluated | AutoGen, Semantic Kernel, all frameworks | `agent.task.acceptance_criteria.*` |

## Three-Tier Provenance Model

| Tier | Name | Description | Key Attributes |
|------|------|-------------|----------------|
| 1 | Self-Declared | Agent declares its own provenance; no external verification | `agent.output.source.type`, `.uri`, `.confidence` |
| 2 | Signed / Hash-Verified | Content hash + signature; attestation record on verification backend | `agent.output.hash.*`, `agent.output.signature.*`, `agent.provenance.attestation.*` |
| 3 | Verifiable Callback | Live endpoint confirms provenance in real-time | `agent.provenance.callback.*` |

## Installation

```bash
pip install -e .

# With framework-specific adapters:
pip install -e ".[google]"    # Google ADK/Vertex AI grounding
pip install -e ".[azure]"     # Azure AI Search
pip install -e ".[autogen]"   # AutoGen derivation tracking
pip install -e ".[settlement]" # A2A-SE exchange/mediator/shim
pip install -e ".[all]"       # Everything
```

## Quick Start

### Provenance Span (Tier 1)

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

### Derivation Lineage

```python
from otel_agent_provenance.spans import DerivationSpan

with DerivationSpan(
    input_agents=["researcher", "analyst"],
    strategy="synthesis",
    weights=[0.4, 0.6],
):
    combined_output = synthesize(research, analysis)
```

### Acceptance Criteria

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

### Azure RAG Pipeline (fills Microsoft Gap #1)

```python
from otel_agent_provenance.adapters.azure_rag import RagStageTracer

tracer = RagStageTracer(agent_id="my-rag-agent")

with tracer.retrieval(query="How does X work?") as stage:
    results = search_client.search(query)
    stage.record_results(results)

with tracer.selection() as stage:
    stage.record_context_window(attended=top_3, ignored=rest)

with tracer.generation(model_name="gpt-4o") as stage:
    output = llm.generate(prompt)
    stage.record_output(output, cited_uris=["..."], coverage=0.75)
```

### AutoGen Derivation (fills Microsoft Gap #2)

```python
from otel_agent_provenance.adapters.autogen_derivation import AutoGenDerivationTracker

tracker = AutoGenDerivationTracker(root_task_id="task-001")

tracker.record_output("agent-a", span_id_a)

with tracer.start_as_current_span("invoke_agent agent-b") as span:
    tracker.record_derivation(
        agent_id="agent-b",
        span=span,
        input_agent_ids=["agent-a"],
        strategy="synthesis",
    )
```

## Examples

```bash
python examples/autogen_provenance.py    # AutoGen derivation chain
python examples/azure_rag_provenance.py  # Azure RAG pipeline
python examples/adk_grounding.py         # Google ADK grounding adapter
python examples/settlement_e2e.py        # Full settlement lifecycle
```

## Repository Structure

```
otel-agent-provenance/
  model/                           # YAML semantic convention definitions
    agent-provenance.yaml          # Tier 1/2/3 provenance attributes
    agent-derivation.yaml          # Multi-agent derivation lineage
    agent-acceptance.yaml          # Task acceptance criteria evaluation
  docs/
    agent-provenance.md            # Convention specification
    agent-derivation.md            # Derivation lineage spec
    agent-acceptance.md            # Acceptance criteria spec
    gap-analysis.md                # Microsoft/Google/OTel gap analysis
  otep/
    OTEP-agent-provenance.md       # OpenTelemetry Enhancement Proposal
  src/otel_agent_provenance/
    conventions.py                 # Attribute key constants
    spans.py                       # Span builders (ProvenanceSpan, DerivationSpan, AcceptanceSpan)
    adapters/
      google_grounding.py          # Google Vertex AI / ADK -> OTel
      azure_rag.py                 # Azure AI Search / Semantic Kernel RAG -> OTel
      autogen_derivation.py        # AutoGen multi-agent derivation -> OTel
      semantic_kernel_rag.py       # Semantic Kernel plugin hooks -> OTel
    instruments/
      settlement_exchange.py       # A2A-SE exchange instrumentation
      settlement_mediator.py       # AI Mediator -> acceptance criteria spans
      settlement_shim.py           # Economic Air Gap proxy instrumentation
  tests/
  examples/
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## The Strategic Play

The semantic convention defines the vocabulary. The verification backend provides the semantic guarantee. When Datadog shows `agent.provenance.attestation.uri = exchange.a2a-settlement.org/attestation/abc123`, that is a live link to verification infrastructure. The convention drives adoption of the exchange, not the other way around.

See [docs/gap-analysis.md](docs/gap-analysis.md) for the full Microsoft/Google gap analysis and [otep/OTEP-agent-provenance.md](otep/OTEP-agent-provenance.md) for the enhancement proposal.
