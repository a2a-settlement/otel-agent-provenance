"""Tests for semantic convention constants."""

from otel_agent_provenance.conventions import (
    AcceptanceAttributes,
    AcceptanceStrategy,
    CallbackStatus,
    DerivationAttributes,
    DerivationStrategy,
    HashAlgorithm,
    ProvenanceAttributes,
    SignatureMethod,
    SourceInfluence,
    SourceType,
)


class TestProvenanceAttributes:
    def test_agent_id_key(self):
        assert ProvenanceAttributes.AGENT_ID == "agent.id"

    def test_provenance_tier_key(self):
        assert ProvenanceAttributes.OUTPUT_PROVENANCE_TIER == "agent.output.provenance.tier"

    def test_source_type_key(self):
        assert ProvenanceAttributes.OUTPUT_SOURCE_TYPE == "agent.output.source.type"

    def test_grounding_coverage_key(self):
        assert ProvenanceAttributes.OUTPUT_GROUNDING_COVERAGE == "agent.output.grounding.coverage"

    def test_attestation_uri_key(self):
        assert ProvenanceAttributes.ATTESTATION_URI == "agent.provenance.attestation.uri"

    def test_callback_uri_key(self):
        assert ProvenanceAttributes.CALLBACK_URI == "agent.provenance.callback.uri"

    def test_chain_depth_key(self):
        assert ProvenanceAttributes.CHAIN_DEPTH == "agent.provenance.chain.depth"


class TestEnumValues:
    def test_source_types(self):
        assert SourceType.MODEL_GENERATION == "model_generation"
        assert SourceType.RETRIEVAL == "retrieval"
        assert SourceType.TOOL_CALL == "tool_call"
        assert SourceType.AGENT_DELEGATION == "agent_delegation"
        assert SourceType.HYBRID == "hybrid"

    def test_source_influence(self):
        assert SourceInfluence.ATTENDED == "attended"
        assert SourceInfluence.CITED == "cited"
        assert SourceInfluence.IGNORED == "ignored"

    def test_hash_algorithms(self):
        assert HashAlgorithm.SHA256 == "sha256"
        assert HashAlgorithm.SHA3_256 == "sha3-256"

    def test_signature_methods(self):
        assert SignatureMethod.HMAC == "hmac"
        assert SignatureMethod.ED25519 == "ed25519"
        assert SignatureMethod.X509 == "x509"

    def test_callback_status(self):
        assert CallbackStatus.VERIFIED == "verified"
        assert CallbackStatus.EXPIRED == "expired"
        assert CallbackStatus.REVOKED == "revoked"


class TestDerivationAttributes:
    def test_input_spans_key(self):
        assert DerivationAttributes.INPUT_SPANS == "agent.derivation.input_spans"

    def test_strategy_key(self):
        assert DerivationAttributes.STRATEGY == "agent.derivation.strategy"

    def test_derivation_strategies(self):
        assert DerivationStrategy.SYNTHESIS == "synthesis"
        assert DerivationStrategy.DELEGATION == "delegation"
        assert DerivationStrategy.PIPELINE == "pipeline"
        assert DerivationStrategy.CONSENSUS == "consensus"
        assert DerivationStrategy.REVIEW == "review"


class TestAcceptanceAttributes:
    def test_task_id_key(self):
        assert AcceptanceAttributes.TASK_ID == "agent.task.id"

    def test_acceptance_met_key(self):
        assert AcceptanceAttributes.ACCEPTANCE_MET == "agent.task.acceptance_criteria.met"

    def test_acceptance_strategies(self):
        assert AcceptanceStrategy.LLM == "llm"
        assert AcceptanceStrategy.HASH == "hash"
        assert AcceptanceStrategy.HUMAN == "human"
        assert AcceptanceStrategy.HYBRID == "hybrid"
        assert AcceptanceStrategy.AUTOMATED == "automated"
