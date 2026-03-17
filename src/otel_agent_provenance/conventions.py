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


class AttestationLifecycleAttributes:
    """Attribute keys for attestation TTL, revocation, and renewal spans."""

    ATTESTATION_ID = "agent.provenance.attestation.id"
    ATTESTATION_TYPE = "agent.provenance.attestation.type"
    ATTESTATION_ISSUED_AT = "agent.provenance.attestation.issued_at"
    ATTESTATION_EXPIRES_AT = "agent.provenance.attestation.expires_at"
    ATTESTATION_TTL_REMAINING_S = "agent.provenance.attestation.ttl_remaining_s"
    ATTESTATION_REVOKED_AT = "agent.provenance.attestation.revoked_at"
    ATTESTATION_REVOCATION_REASON = "agent.provenance.attestation.revocation_reason"
    ATTESTATION_RENEWAL_CHAIN_DEPTH = "agent.provenance.attestation.renewal_chain_depth"
    ATTESTATION_STATUS = "agent.provenance.attestation.status"
    ATTESTATION_PARENT_ID = "agent.provenance.attestation.parent_id"
    ATTESTATION_FEE_CHARGED = "agent.provenance.attestation.fee_charged"
    ATTESTATION_EVENT = "agent.provenance.attestation.event"


class AttestationEventType:
    """Well-known values for ``agent.provenance.attestation.event``."""

    ISSUED = "issued"
    EXPIRED = "expired"
    REVOKED = "revoked"
    RENEWED = "renewed"
    WARNING = "ttl_warning"


class AttestationTypeSemconv:
    """Well-known values for ``agent.provenance.attestation.type``."""

    IDENTITY = "identity"
    REPUTATION = "reputation"
    TRANSACTION = "transaction"
    CAPABILITY = "capability"


class RevocationReason:
    """Well-known values for ``agent.provenance.attestation.revocation_reason``."""

    KEY_COMPROMISE = "key_compromise"
    ERRONEOUS_ISSUANCE = "erroneous_issuance"
    DEREGISTRATION = "deregistration"
    POLICY_VIOLATION = "policy_violation"


class EvidenceAttributes:
    """Attribute keys for dispute evidence submission spans."""

    EVIDENCE_TYPE = "agent.evidence.type"
    EVIDENCE_ARTIFACT_COUNT = "agent.evidence.artifact_count"
    EVIDENCE_ENCRYPTED = "agent.evidence.encrypted"
    EVIDENCE_ATTESTOR_ID = "agent.evidence.attestor_id"
    EVIDENCE_CONTENT_HASH = "agent.evidence.content_hash"
    EVIDENCE_ESCROW_ID = "agent.evidence.escrow_id"
    EVIDENCE_SUBMITTER_ID = "agent.evidence.submitter_id"
    EVIDENCE_WINDOW_EXPIRES_AT = "agent.evidence.window_expires_at"
    EVIDENCE_DEFAULT_JUDGMENT = "agent.evidence.default_judgment"
    EVIDENCE_STAKE_AMOUNT = "agent.evidence.stake_amount"
    EVIDENCE_STAKE_RULING = "agent.evidence.stake_ruling"


class EvidenceType:
    """Well-known values for ``agent.evidence.type``."""

    COMPUTE = "compute"
    CONTENT = "content"
    SERVICE = "service"
    BOUNTY = "bounty"
    THIRD_PARTY_ATTESTATION = "third_party_attestation"


class FederationAttributes:
    """Attribute keys for federation events (peering, VC import, Trust Discount, health)."""

    FEDERATION_PEER_DID = "agent.federation.peer_did"
    FEDERATION_RHO = "agent.federation.rho"
    FEDERATION_ALGORITHM_ID = "agent.federation.algorithm_id"
    FEDERATION_HEALTH_STATUS = "agent.federation.health_status"
    FEDERATION_ATTESTATION_TYPE = "agent.federation.attestation_type"
    FEDERATION_SOURCE_EXCHANGE_DID = "agent.federation.source_exchange_did"

    # Aliases for concise usage
    PEER_DID = FEDERATION_PEER_DID
    RHO = FEDERATION_RHO
    ALGORITHM_ID = FEDERATION_ALGORITHM_ID
    HEALTH_STATUS = FEDERATION_HEALTH_STATUS
    ATTESTATION_TYPE = FEDERATION_ATTESTATION_TYPE
    SOURCE_EXCHANGE_DID = FEDERATION_SOURCE_EXCHANGE_DID


class FederationHealthStatus:
    """Well-known values for ``agent.federation.health_status``."""

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class FederationAttestationType:
    """Well-known values for ``agent.federation.attestation_type``."""

    IDENTITY = "identity"
    REPUTATION = "reputation"
    TRANSACTION = "transaction"
    CAPABILITY = "capability"
