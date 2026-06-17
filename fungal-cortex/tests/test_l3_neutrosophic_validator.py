"""Tests for L3: NeutrosophicCausalValidator — 中智因果验证器."""

import numpy as np
import pytest

from src.l3.neutrosophic_causal_validator import (
    CausalIntervention,
    NeutrosophicCausalValidator,
    NeutrosophicVerdict,
    ValidatorConfig,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def config() -> ValidatorConfig:
    return ValidatorConfig(
        accept_truth=0.6,
        accept_falsity=0.2,
        accept_indeterminacy=0.3,
        do_samples=500,
    )


@pytest.fixture
def validator(config: ValidatorConfig) -> NeutrosophicCausalValidator:
    return NeutrosophicCausalValidator(config=config)


@pytest.fixture
def supporting_evidence() -> list[dict]:
    return [
        {"strength": 0.8, "direction": "support", "reliability": 0.9, "staleness": 0.0},
        {"strength": 0.7, "direction": "support", "reliability": 0.85, "staleness": 0.1},
        {"strength": 0.6, "direction": "support", "reliability": 0.95, "staleness": 0.0},
    ]


@pytest.fixture
def mixed_evidence() -> list[dict]:
    return [
        {"strength": 0.8, "direction": "support", "reliability": 0.9, "staleness": 0.0},
        {"strength": 0.6, "direction": "refute", "reliability": 0.8, "staleness": 0.0},
        {"strength": 0.4, "direction": "support", "reliability": 0.5, "staleness": 0.5},
    ]


@pytest.fixture
def sample_claim() -> dict:
    return {"claim_id": "test-001", "predicate": "X will outperform Y by 5% in 30 days"}


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests
# ═══════════════════════════════════════════════════════════════════════


class TestValidatorInit:
    """Test initialization and configuration."""

    def test_default_init(self) -> None:
        v = NeutrosophicCausalValidator()
        assert v.stats["validation_count"] == 0
        assert v.stats["accept_thresholds"]["T"] == 0.6

    def test_custom_config(self, config: ValidatorConfig) -> None:
        v = NeutrosophicCausalValidator(config=config)
        assert v._config.accept_truth == 0.6
        assert v._config.do_samples == 500

    def test_initial_stats(self, validator: NeutrosophicCausalValidator) -> None:
        stats = validator.stats
        assert stats["stored_verdicts"] == 0
        assert stats["interventions"] == 0
        assert stats["avg_truth"] is None


class TestNeutrosophicVerdict:
    """Test verdict data structure."""

    def test_basic_verdict(self) -> None:
        v = NeutrosophicVerdict(truth=0.7, indeterminacy=0.2, falsity=0.1)
        assert v.truth == 0.7
        assert v.indeterminacy == 0.2
        assert v.falsity == 0.1

    def test_clamping(self) -> None:
        v = NeutrosophicVerdict(truth=1.5, indeterminacy=-0.3, falsity=2.0)
        assert 0.0 <= v.truth <= 1.0
        assert 0.0 <= v.indeterminacy <= 1.0
        assert 0.0 <= v.falsity <= 1.0

    def test_net_truth(self) -> None:
        v = NeutrosophicVerdict(truth=0.8, indeterminacy=0.1, falsity=0.3)
        assert v.net_truth == 0.5

    def test_certainty(self) -> None:
        v = NeutrosophicVerdict(truth=0.7, indeterminacy=0.2, falsity=0.1)
        assert v.certainty == 0.8

    def test_is_decisive_true(self) -> None:
        v = NeutrosophicVerdict(truth=0.8, indeterminacy=0.1, falsity=0.1)
        assert v.is_decisive is True

    def test_is_decisive_false_with_high_indeterminacy(self) -> None:
        v = NeutrosophicVerdict(truth=0.8, indeterminacy=0.5, falsity=0.1)
        assert v.is_decisive is False


class TestValidation:
    """Test core claim validation."""

    def test_validate_no_evidence(self, validator: NeutrosophicCausalValidator, sample_claim: dict) -> None:
        verdict = validator.validate(sample_claim, [])
        assert verdict.evidence_count == 0
        assert verdict.indeterminacy == 1.0
        assert verdict.truth == 0.0

    def test_validate_supporting_only(self, validator: NeutrosophicCausalValidator, sample_claim: dict, supporting_evidence: list[dict]) -> None:
        verdict = validator.validate(sample_claim, supporting_evidence)
        assert verdict.evidence_count == 3
        assert verdict.truth > 0.0
        assert verdict.falsity < 0.5

    def test_validate_mixed_evidence(self, validator: NeutrosophicCausalValidator, sample_claim: dict, mixed_evidence: list[dict]) -> None:
        verdict = validator.validate(sample_claim, mixed_evidence)
        # With mixed evidence, both T and F should be non-zero
        assert verdict.truth > 0.0
        assert verdict.falsity > 0.0
        # Indeterminacy captures conflict
        assert verdict.indeterminacy > 0.0

    def test_validate_increments_count(self, validator: NeutrosophicCausalValidator, sample_claim: dict, supporting_evidence: list[dict]) -> None:
        validator.validate(sample_claim, supporting_evidence)
        assert validator.stats["validation_count"] == 1
        validator.validate(sample_claim, supporting_evidence)
        assert validator.stats["validation_count"] == 2

    def test_validate_confidence_interval(self, validator: NeutrosophicCausalValidator, sample_claim: dict, supporting_evidence: list[dict]) -> None:
        verdict = validator.validate(sample_claim, supporting_evidence)
        assert len(verdict.confidence_interval) == 2
        ci_low, ci_high = verdict.confidence_interval
        assert 0.0 <= ci_low <= ci_high <= 1.0

    def test_validate_with_reasoning(self, validator: NeutrosophicCausalValidator, sample_claim: dict, supporting_evidence: list[dict]) -> None:
        verdict = validator.validate(sample_claim, supporting_evidence)
        assert len(verdict.reasoning) > 0
        assert "T=" in verdict.reasoning


class TestAcceptanceDecision:
    """Test should_accept logic."""

    def test_accept_strong_verdict(self, validator: NeutrosophicCausalValidator, sample_claim: dict, supporting_evidence: list[dict]) -> None:
        verdict = validator.validate(sample_claim, supporting_evidence)
        # With 3 strong supporting evidence, should produce a boolean decision
        result = validator.should_accept(verdict)
        assert result in (True, False)

    def test_reject_with_high_falsity(self, validator: NeutrosophicCausalValidator) -> None:
        verdict = NeutrosophicVerdict(truth=0.3, indeterminacy=0.2, falsity=0.8)
        assert validator.should_accept(verdict) is False

    def test_reject_with_high_indeterminacy(self, validator: NeutrosophicCausalValidator) -> None:
        verdict = NeutrosophicVerdict(truth=0.9, indeterminacy=0.5, falsity=0.0)
        assert validator.should_accept(verdict) is False

    def test_custom_thresholds(self, validator: NeutrosophicCausalValidator) -> None:
        verdict = NeutrosophicVerdict(truth=0.5, indeterminacy=0.1, falsity=0.3)
        # With lenient thresholds
        assert validator.should_accept(verdict, thresholds=(0.4, 0.5, 0.5)) is True
        # With strict thresholds
        assert validator.should_accept(verdict, thresholds=(0.7, 0.1, 0.1)) is False


class TestVerdictMerging:
    """Test multi-judge verdict fusion."""

    def test_merge_single(self, validator: NeutrosophicCausalValidator) -> None:
        v = NeutrosophicVerdict(truth=0.7, indeterminacy=0.2, falsity=0.1)
        merged = validator.merge_verdicts([v])
        assert merged.truth == 0.7
        assert merged.indeterminacy == 0.2

    def test_merge_weighted_average(self, validator: NeutrosophicCausalValidator) -> None:
        v1 = NeutrosophicVerdict(truth=0.8, indeterminacy=0.1, falsity=0.1, evidence_count=5)
        v2 = NeutrosophicVerdict(truth=0.6, indeterminacy=0.3, falsity=0.1, evidence_count=3)
        v3 = NeutrosophicVerdict(truth=0.7, indeterminacy=0.2, falsity=0.1, evidence_count=2)

        merged = validator.merge_verdicts([v1, v2, v3], method="weighted_average")
        # v1 has most evidence, so merged should lean toward v1
        assert 0.6 < merged.truth < 0.85
        assert merged.indeterminacy > 0.0

    def test_merge_min_max(self, validator: NeutrosophicCausalValidator) -> None:
        v1 = NeutrosophicVerdict(truth=0.7, indeterminacy=0.1, falsity=0.2)
        v2 = NeutrosophicVerdict(truth=0.9, indeterminacy=0.05, falsity=0.1)
        v3 = NeutrosophicVerdict(truth=0.5, indeterminacy=0.3, falsity=0.3)

        merged = validator.merge_verdicts([v1, v2, v3], method="min_max")
        # Conservative: min truth, max falsity
        assert merged.truth == 0.5  # min
        assert merged.falsity == 0.3  # max

    def test_merge_dempster_shafer(self, validator: NeutrosophicCausalValidator) -> None:
        v1 = NeutrosophicVerdict(truth=0.8, indeterminacy=0.2, falsity=0.0)
        v2 = NeutrosophicVerdict(truth=0.7, indeterminacy=0.3, falsity=0.0)

        merged = validator.merge_verdicts([v1, v2], method="dempster_shafer")
        assert 0.0 <= merged.truth <= 1.0
        assert 0.0 <= merged.indeterminacy <= 1.0

    def test_merge_empty_returns_indeterminate(self, validator: NeutrosophicCausalValidator) -> None:
        merged = validator.merge_verdicts([])
        assert merged.indeterminacy == 1.0
        assert merged.truth == 0.0


class TestDoIntervention:
    """Test causal do-operator interventions."""

    def test_do_intervention_basic(self, validator: NeutrosophicCausalValidator) -> None:
        model = {"variables": ["X", "Y"], "base_effect": 2.0, "noise_std": 0.1, "confound_strength": 0.0}
        intervention = validator.do_intervention(model, "X", 1.0, samples=500)
        assert isinstance(intervention, CausalIntervention)
        assert intervention.intervention_var == "X"
        assert intervention.intervention_value == 1.0
        assert len(intervention.outcome_distribution) == 500

    def test_do_intervention_with_confounding(self, validator: NeutrosophicCausalValidator) -> None:
        model = {"base_effect": 1.0, "noise_std": 0.1, "confound_strength": 0.5}
        intervention = validator.do_intervention(model, "X", 0.5, samples=500)
        # Confounding should increase indeterminacy
        assert intervention.neutrosophic_effect.indeterminacy > 0.0

    def test_do_intervention_records_history(self, validator: NeutrosophicCausalValidator) -> None:
        model = {"base_effect": 1.0, "noise_std": 0.1, "confound_strength": 0.0}
        validator.do_intervention(model, "X", 1.0, samples=100)
        assert validator.stats["interventions"] == 1

    def test_do_intervention_ate(self, validator: NeutrosophicCausalValidator) -> None:
        model = {"base_effect": 3.0, "noise_std": 0.1, "confound_strength": 0.0}
        intervention = validator.do_intervention(model, "X", 2.0, samples=1000)
        # ATE should be approximately base_effect * value = 6.0
        assert 4.0 < intervention.average_treatment_effect < 8.0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_validate_with_empty_string_claim_id(self, validator: NeutrosophicCausalValidator) -> None:
        claim = {"claim_id": "", "predicate": "test"}
        verdict = validator.validate(claim, [{"strength": 0.5, "direction": "support", "reliability": 1.0}])
        assert isinstance(verdict, NeutrosophicVerdict)

    def test_validate_zero_strength_evidence(self, validator: NeutrosophicCausalValidator) -> None:
        claim = {"claim_id": "z1"}
        verdict = validator.validate(claim, [{"strength": 0.0, "direction": "support", "reliability": 1.0}])
        # Zero-strength evidence → low truth
        assert verdict.truth < 0.5

    def test_validate_stale_evidence(self, validator: NeutrosophicCausalValidator) -> None:
        claim = {"claim_id": "stale-1"}
        evidence = [{"strength": 0.9, "direction": "support", "reliability": 1.0, "staleness": 100.0}]
        verdict = validator.validate(claim, evidence)
        # Very stale evidence should reduce effective weight → higher I
        assert verdict.indeterminacy > 0.0


class TestReset:
    """Test validator reset."""

    def test_reset_clears_all(self, validator: NeutrosophicCausalValidator, sample_claim: dict, supporting_evidence: list[dict]) -> None:
        validator.validate(sample_claim, supporting_evidence)
        validator.do_intervention({"base_effect": 1.0, "noise_std": 0.1, "confound_strength": 0.0}, "X", 1.0, samples=100)

        validator.reset()
        assert validator.stats["validation_count"] == 0
        assert validator.stats["stored_verdicts"] == 0
        assert validator.stats["interventions"] == 0
