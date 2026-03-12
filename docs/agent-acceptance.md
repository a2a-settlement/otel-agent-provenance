# Semantic Conventions for Agent Task Acceptance Criteria

**Status:** Development

## Overview

These conventions capture the acceptance criteria evaluation loop: did the agent's output meet the task specification? They extend the basic `gen_ai.evaluation.*` attributes with task-specific semantics including evaluation strategy, confidence gating, and multi-factor assessment.

This is the layer absent from Microsoft's stack (AutoGen, Semantic Kernel) and minimal in Google's ADK. The A2A-SE AI Mediator's 7-factor evaluation framework serves as the reference implementation.

## Use Cases

- **Automated quality gates**: Auto-release payment when evaluation confidence exceeds a threshold; escalate to human review below it.
- **Dispute resolution**: When a requester disputes an agent's output, the evaluation record provides structured evidence for mediation.
- **SLA enforcement**: Track acceptance rates, evaluation scores, and strategy distribution to enforce service-level agreements.
- **Audit trail**: The evaluation factors and strategy provide an auditable record of why an output was accepted or rejected.

## Attributes

| Attribute | Type | Requirement Level | Description | Examples |
|-----------|------|-------------------|-------------|----------|
| `agent.task.id` | string | Required | Task or bounty identifier | `task-research-001` |
| `agent.task.acceptance_criteria` | string | Recommended | Hash or URI of acceptance spec | `sha256:a3f2b8c...` |
| `agent.task.acceptance_criteria.met` | boolean | Conditional | Whether output met criteria | `true` |
| `agent.task.acceptance_criteria.score` | double | Recommended | Evaluation score (0.0-1.0) | `0.92` |
| `agent.task.acceptance_criteria.strategy` | enum | Recommended | Evaluation strategy | `llm` |
| `agent.task.acceptance_criteria.evaluator` | string | Recommended | Evaluator identifier | `mediator-001` |
| `agent.task.acceptance_criteria.factors` | string[] | Recommended | Evaluation factors | `["completeness", ...]` |

## Strategy Values

| Value | Description |
|-------|-------------|
| `llm` | Acceptance evaluated by an LLM judge |
| `hash` | Acceptance determined by content hash match |
| `human` | Acceptance determined by human review |
| `hybrid` | Combination of strategies (e.g. LLM pre-screen with human escalation) |
| `automated` | Acceptance determined by automated tests or checks |

## Reference: 7-Factor Evaluation Framework

The A2A-SE AI Mediator evaluates disputes using seven factors. These map directly to the `acceptance_criteria.factors` attribute:

| Factor | Description |
|--------|-------------|
| `deliverable_completeness` | Were all required artifacts submitted? Do hashes match? |
| `acceptance_criteria_specificity` | How specific vs. subjective are the criteria? |
| `dispute_substantiation` | Is the dispute specific and substantiated, or vague? |
| `reputation_history` | Dispute patterns for requester and provider |
| `proportionality` | Economic vs. quality motivation for the dispute |
| `provenance_attestation` | Credibility of claimed sources (tier and verification result) |
| `web_grounding` | Coverage, source diversity, and domain count from grounding |

## Example: Mediation Flow

```
Span: agent.acceptance.mediation
  agent.task.id = "escrow-abc-123"
  agent.task.acceptance_criteria = "sha256:9f86d081..."
  agent.task.acceptance_criteria.strategy = "hybrid"
  agent.task.acceptance_criteria.evaluator = "mediator-001"
  agent.task.acceptance_criteria.factors = [
    "deliverable_completeness",
    "acceptance_criteria_specificity",
    "dispute_substantiation",
    "reputation_history",
    "proportionality",
    "provenance_attestation",
    "web_grounding"
  ]
  agent.task.acceptance_criteria.met = true
  agent.task.acceptance_criteria.score = 0.87
  agent.output.provenance.tier = 2
  agent.output.confidence = 0.87
  settlement.mediation.outcome = "AUTO_RELEASE"
  settlement.mediation.resolution = "release"
```

This tells the observability dashboard: the mediator evaluated the disputed escrow using all 7 factors, achieved 87% confidence (above the auto-resolution threshold), and auto-released payment to the provider.

## Relationship to `gen_ai.evaluation.*`

The existing `gen_ai.evaluation.score.value` and `gen_ai.evaluation.name` attributes provide a basic evaluation score. The acceptance criteria conventions extend this with:

- **Strategy**: Who or what performed the evaluation
- **Specification**: What the output was evaluated against
- **Multi-factor**: Which specific factors were considered
- **Confidence gating**: Score that drives automated resolution decisions
- **Evaluator identity**: Which agent or human performed the evaluation
