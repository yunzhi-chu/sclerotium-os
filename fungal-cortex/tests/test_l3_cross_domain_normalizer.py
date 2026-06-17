"""Tests for L3: CrossDomainClaimNormalizer — 跨域Claim标准化器."""

import numpy as np
import pytest

from src.l3.cross_domain_claim_normalizer import (
    CrossDomainClaimNormalizer,
    Domain,
    EvidenceItem,
    NormalizerConfig,
    StandardClaim,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def config() -> NormalizerConfig:
    return NormalizerConfig(
        default_domain=Domain.FINANCE,
        max_claims_per_skill=10,
        domain_detection_confidence=0.7,
    )


@pytest.fixture
def normalizer(config: NormalizerConfig) -> CrossDomainClaimNormalizer:
    return CrossDomainClaimNormalizer(config=config)


@pytest.fixture
def sample_skill_text() -> str:
    return """# Financial Analysis Skill

This skill covers stock market analysis and portfolio optimization.

Claim: Value stocks outperform growth stocks during high-interest-rate environments.
Claim: The Sharpe ratio of a diversified portfolio exceeds that of individual stocks.

When volatility spikes above 30%, then risk-parity rebalancing should be triggered.

Patient diagnosis requires at least 3 independent clinical findings.

This design must meet seismic rating >= 8 per building code.
"""


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests
# ═══════════════════════════════════════════════════════════════════════


class TestNormalizerInit:
    """Test initialization and configuration."""

    def test_default_init(self) -> None:
        n = CrossDomainClaimNormalizer()
        assert n.stats["normalize_count"] == 0
        assert n.stats["default_domain"] == "finance"

    def test_custom_config(self, normalizer: CrossDomainClaimNormalizer) -> None:
        assert normalizer._config.default_domain == Domain.FINANCE
        assert normalizer._config.max_claims_per_skill == 10

    def test_initial_stats(self, normalizer: CrossDomainClaimNormalizer) -> None:
        stats = normalizer.stats
        assert stats["stored_claims"] == 0
        assert "finance" in stats["by_domain"]
        assert stats["verifiable_count"] == 0


class TestDomainDetection:
    """Test automatic domain detection from text."""

    def test_detect_finance_domain(self, normalizer: CrossDomainClaimNormalizer) -> None:
        text = "This stock has strong alpha and a Sharpe ratio above 2.0"
        domain, confidence = normalizer.detect_domain(text)
        assert domain == Domain.FINANCE
        assert confidence > 0.0

    def test_detect_medical_domain(self, normalizer: CrossDomainClaimNormalizer) -> None:
        text = "The patient shows symptoms of infection and requires antibiotic therapy"
        domain, confidence = normalizer.detect_domain(text)
        assert domain == Domain.MEDICAL
        assert confidence > 0.0

    def test_detect_legal_domain(self, normalizer: CrossDomainClaimNormalizer) -> None:
        text = "This contract clause violates the compliance regulation and creates liability"
        domain, confidence = normalizer.detect_domain(text)
        assert domain == Domain.LEGAL

    def test_detect_engineering_domain(self, normalizer: CrossDomainClaimNormalizer) -> None:
        text = "The structural design must meet seismic load tolerance specifications"
        domain, confidence = normalizer.detect_domain(text)
        assert domain == Domain.ENGINEERING

    def test_detect_ai_ml_domain(self, normalizer: CrossDomainClaimNormalizer) -> None:
        text = "The transformer model achieves 95% accuracy on the benchmark after fine-tuning"
        domain, _ = normalizer.detect_domain(text)
        assert domain == Domain.AI_ML

    def test_detect_cybersecurity_domain(self, normalizer: CrossDomainClaimNormalizer) -> None:
        text = "This vulnerability CVE-2025-12345 allows privilege escalation via SQL injection"
        domain, _ = normalizer.detect_domain(text)
        assert domain == Domain.CYBERSECURITY

    def test_unknown_text_uses_default(self, normalizer: CrossDomainClaimNormalizer) -> None:
        text = "This is some random text without any domain-specific keywords at all"
        domain, confidence = normalizer.detect_domain(text)
        assert domain == normalizer._config.default_domain
        assert confidence == 0.0

    def test_detect_chinese_finance(self, normalizer: CrossDomainClaimNormalizer) -> None:
        text = "股票收益率预期超过指数基准"
        domain, confidence = normalizer.detect_domain(text)
        assert domain == Domain.FINANCE


class TestClaimNormalization:
    """Test claim normalization to StandardClaim format."""

    def test_normalize_string(self, normalizer: CrossDomainClaimNormalizer) -> None:
        claim = normalizer.normalize("Stock X will return >5% in 30 days")
        assert isinstance(claim, StandardClaim)
        assert len(claim.claim_id) > 0
        assert claim.predicate == "Stock X will return >5% in 30 days"

    def test_normalize_dict(self, normalizer: CrossDomainClaimNormalizer) -> None:
        claim = normalizer.normalize({"predicate": "Test claim", "confidence": 0.8})
        assert claim.confidence == 0.8
        assert claim.predicate == "Test claim"

    def test_normalize_dict_with_alt_key(self, normalizer: CrossDomainClaimNormalizer) -> None:
        claim = normalizer.normalize({"claim": "Test with claim key"})
        assert claim.predicate == "Test with claim key"

    def test_normalize_already_standard(self, normalizer: CrossDomainClaimNormalizer) -> None:
        existing = StandardClaim(claim_id="existing-1", domain=Domain.FINANCE, predicate="Test")
        result = normalizer.normalize(existing)
        assert result.claim_id == "existing-1"

    def test_normalize_with_explicit_domain(self, normalizer: CrossDomainClaimNormalizer) -> None:
        claim = normalizer.normalize("Patient needs surgery", domain=Domain.MEDICAL)
        assert claim.domain == Domain.MEDICAL

    def test_normalize_with_source_skill(self, normalizer: CrossDomainClaimNormalizer) -> None:
        claim = normalizer.normalize("Test", source_skill="path/to/SKILL.md")
        assert claim.source_skill == "path/to/SKILL.md"

    def test_normalize_extracts_time_horizon(self, normalizer: CrossDomainClaimNormalizer) -> None:
        claim = normalizer.normalize("Stock will change within 14 days")
        assert claim.time_horizon_days == 14.0

    def test_normalize_default_time_horizon(self, normalizer: CrossDomainClaimNormalizer) -> None:
        claim = normalizer.normalize("Some claim without specific time")
        assert claim.time_horizon_days == 30.0

    def test_normalize_increments_count(self, normalizer: CrossDomainClaimNormalizer) -> None:
        assert normalizer.stats["normalize_count"] == 0
        normalizer.normalize("Test claim")
        assert normalizer.stats["normalize_count"] == 1

    def test_normalize_batch(self, normalizer: CrossDomainClaimNormalizer) -> None:
        claims = normalizer.normalize_batch(["Claim A", "Claim B", "Claim C"])
        assert len(claims) == 3
        for c in claims:
            assert isinstance(c, StandardClaim)

    def test_normalize_tracks_domain_stats(self, normalizer: CrossDomainClaimNormalizer) -> None:
        normalizer.normalize("Stock market prediction")
        stats = normalizer.stats
        assert stats["by_domain"]["finance"] >= 1


class TestSkillExtraction:
    """Test extracting claims from SKILL.md files."""

    def test_extract_explicit_claims(self, normalizer: CrossDomainClaimNormalizer, sample_skill_text: str) -> None:
        claims = normalizer.extract_from_skill(sample_skill_text, "skills/finance.md")
        # Should extract at least 2 explicit Claim: patterns
        assert len(claims) >= 2

    def test_extract_claims_have_source(self, normalizer: CrossDomainClaimNormalizer, sample_skill_text: str) -> None:
        claims = normalizer.extract_from_skill(sample_skill_text, "skills/test.md")
        for c in claims:
            assert c.source_skill == "skills/test.md"

    def test_extract_respects_max_limit(self) -> None:
        config = NormalizerConfig(max_claims_per_skill=3)
        normalizer = CrossDomainClaimNormalizer(config=config)
        # Text with many claims
        many_claims = "Claim: A\n" * 20
        claims = normalizer.extract_from_skill(many_claims, "test.md")
        assert len(claims) <= 3

    def test_extract_auto_detects_domain(self, normalizer: CrossDomainClaimNormalizer) -> None:
        """Claims from medical skill should be auto-classified as medical."""
        medical_skill = "Patient diagnosis requires clinical trial validation. Claim: Drug X reduces mortality by 30%."
        claims = normalizer.extract_from_skill(medical_skill, "skills/medical.md")
        for c in claims:
            assert c.domain == Domain.MEDICAL

    def test_extract_empty_skill(self, normalizer: CrossDomainClaimNormalizer) -> None:
        claims = normalizer.extract_from_skill("No claims here.", "empty.md")
        assert len(claims) == 0


class TestStandardClaim:
    """Test StandardClaim data structure."""

    def test_net_evidence(self) -> None:
        claim = StandardClaim(claim_id="c1", domain=Domain.FINANCE, predicate="Test")
        claim.evidence.append(EvidenceItem(source="s1", content="e1", strength=0.8, reliability=1.0))
        claim.evidence.append(EvidenceItem(source="s2", content="e2", strength=0.6, reliability=0.9))
        claim.counter_evidence.append(EvidenceItem(source="s3", content="e3", strength=0.5, reliability=0.8, direction="refute"))
        # net = (0.8*1.0 + 0.6*0.9) - (0.5*0.8) = 1.34 - 0.4 = 0.94
        assert claim.net_evidence > 0.0

    def test_is_verifiable_true(self) -> None:
        claim = StandardClaim(claim_id="c1", domain=Domain.FINANCE, predicate="Test")
        claim.evidence.append(EvidenceItem(source="s1", content="evidence"))
        assert claim.is_verifiable is True

    def test_is_verifiable_false_no_predicate(self) -> None:
        claim = StandardClaim(claim_id="c1", domain=Domain.FINANCE, predicate="")
        assert claim.is_verifiable is False

    def test_is_verifiable_false_no_evidence(self) -> None:
        claim = StandardClaim(claim_id="c1", domain=Domain.FINANCE, predicate="Test")
        assert claim.is_verifiable is False


class TestQueryMethods:
    """Test querying normalized claims."""

    def test_get_claim_by_id(self, normalizer: CrossDomainClaimNormalizer) -> None:
        claim = normalizer.normalize("Test claim")
        retrieved = normalizer.get_claim(claim.claim_id)
        assert retrieved is not None
        assert retrieved.claim_id == claim.claim_id

    def test_get_claim_not_found(self, normalizer: CrossDomainClaimNormalizer) -> None:
        assert normalizer.get_claim("nonexistent") is None

    def test_get_claims_by_domain(self, normalizer: CrossDomainClaimNormalizer) -> None:
        normalizer.normalize("Patient symptoms", domain=Domain.MEDICAL)
        normalizer.normalize("Stock analysis", domain=Domain.FINANCE)
        medical = normalizer.get_claims_by_domain(Domain.MEDICAL)
        assert len(medical) == 1

    def test_get_verifiable_claims(self, normalizer: CrossDomainClaimNormalizer) -> None:
        c = normalizer.normalize("Test")
        # Not verifiable yet (no evidence)
        assert len(normalizer.get_verifiable_claims()) == 0
        c.evidence.append(EvidenceItem(source="s", content="evidence"))
        assert len(normalizer.get_verifiable_claims()) == 1


class TestReset:
    """Test normalizer reset."""

    def test_reset_clears_all(self, normalizer: CrossDomainClaimNormalizer) -> None:
        normalizer.normalize("Test claim")
        normalizer.extract_from_skill("Claim: test", "test.md")

        normalizer.reset()
        assert normalizer.stats["normalize_count"] == 0
        assert normalizer.stats["stored_claims"] == 0
        assert all(v == 0 for v in normalizer.stats["by_domain"].values())
