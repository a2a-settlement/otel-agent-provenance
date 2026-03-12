"""Attribute key constants for agent provenance semantic conventions.

These constants mirror the YAML definitions in ``model/`` and provide
type-safe access to attribute keys for span instrumentation.

Naming follows the OTel dotted namespace convention: ``agent.<domain>.<field>``.
"""

from __future__ import annotations


class ProvenanceAttributes:
    """Attribute keys for agent provenance (Tiers 1-3)."""

    # --- Identity ---
    AGENT_ID = "agent.id"
    AGENT_IDENTITY_TIER = "agent.identity.tier"
    AGENT_IDENTITY_REGISTRY = "agent.identity.registry"

    # --- Tier 1: Self-Declared ---
    OUTPUT_PROVENANCE_TIER = "agent.output.provenance.tier"
    OUTPUT_SOURCE_TYPE = "agent.output.source.type"
    OUTPUT_SOURCE_URI = "agent.output.source.uri"
    OUTPUT_SOURCE_INFLUENCE = "agent.output.source.influence"
    OUTPUT_CONFIDENCE = "agent.output.confidence"
    OUTPUT_MODEL_NAME = "agent.output.model.name"
    OUTPUT_MODEL_VERSION = "agent.output.model.version"

    # --- Grounding ---
    OUTPUT_GROUNDING_COVERAGE = "agent.output.grounding.coverage"
    OUTPUT_GROUNDING_SOURCE_COUNT = "agent.output.grounding.source_count"
    OUTPUT_GROUNDING_DOMAIN_COUNT = "agent.output.grounding.domain_count"

    # --- Tier 2: Signed / Hash-Verified ---
    OUTPUT_HASH_ALGORITHM = "agent.output.hash.algorithm"
    OUTPUT_HASH_VALUE = "agent.output.hash.value"
    OUTPUT_SIGNATURE_METHOD = "agent.output.signature.method"
    OUTPUT_SIGNATURE_VALUE = "agent.output.signature.value"
    OUTPUT_SIGNATURE_KEY_ID = "agent.output.signature.key_id"

    # --- Attestation (Tier 2/3) ---
    ATTESTATION_URI = "agent.provenance.attestation.uri"
    ATTESTATION_TIMESTAMP = "agent.provenance.attestation.timestamp"

    # --- Tier 3: Verifiable Callback ---
    CALLBACK_URI = "agent.provenance.callback.uri"
    CALLBACK_METHOD = "agent.provenance.callback.method"
    CALLBACK_STATUS = "agent.provenance.callback.status"

    # --- Provenance Chain ---
    CHAIN_PARENT_SPAN_ID = "agent.provenance.chain.parent_span_id"
    CHAIN_DEPTH = "agent.provenance.chain.depth"
    CHAIN_ROOT_TASK_ID = "agent.provenance.chain.root_task_id"


class SourceType:
    """Well-known values for ``agent.output.source.type``."""

    MODEL_GENERATION = "model_generation"
    RETRIEVAL = "retrieval"
    TOOL_CALL = "tool_call"
    AGENT_DELEGATION = "agent_delegation"
    HYBRID = "hybrid"


class SourceInfluence:
    """Well-known values for ``agent.output.source.influence``."""

    ATTENDED = "attended"
    CITED = "cited"
    IGNORED = "ignored"


class HashAlgorithm:
    """Well-known values for ``agent.output.hash.algorithm``."""

    SHA256 = "sha256"
    SHA3_256 = "sha3-256"
    SHA384 = "sha384"
    SHA512 = "sha512"


class SignatureMethod:
    """Well-known values for ``agent.output.signature.method``."""

    HMAC = "hmac"
    ED25519 = "ed25519"
    X509 = "x509"


class CallbackStatus:
    """Well-known values for ``agent.provenance.callback.status``."""

    VERIFIED = "verified"
    EXPIRED = "expired"
    REVOKED = "revoked"


class CallbackMethod:
    """Well-known values for ``agent.provenance.callback.method``."""

    GET = "GET"
    POST = "POST"


class DerivationAttributes:
    """Attribute keys for agent derivation lineage."""

    INPUT_SPANS = "agent.derivation.input_spans"
    INPUT_AGENTS = "agent.derivation.input_agents"
    STRATEGY = "agent.derivation.strategy"
    WEIGHT = "agent.derivation.weight"


class DerivationStrategy:
    """Well-known values for ``agent.derivation.strategy``."""

    SYNTHESIS = "synthesis"
    DELEGATION = "delegation"
    PIPELINE = "pipeline"
    CONSENSUS = "consensus"
    REVIEW = "review"


class AcceptanceAttributes:
    """Attribute keys for task acceptance criteria evaluation."""

    TASK_ID = "agent.task.id"
    ACCEPTANCE_CRITERIA = "agent.task.acceptance_criteria"
    ACCEPTANCE_MET = "agent.task.acceptance_criteria.met"
    ACCEPTANCE_SCORE = "agent.task.acceptance_criteria.score"
    ACCEPTANCE_STRATEGY = "agent.task.acceptance_criteria.strategy"
    ACCEPTANCE_EVALUATOR = "agent.task.acceptance_criteria.evaluator"
    ACCEPTANCE_FACTORS = "agent.task.acceptance_criteria.factors"


class AcceptanceStrategy:
    """Well-known values for ``agent.task.acceptance_criteria.strategy``."""

    LLM = "llm"
    HASH = "hash"
    HUMAN = "human"
    HYBRID = "hybrid"
    AUTOMATED = "automated"
