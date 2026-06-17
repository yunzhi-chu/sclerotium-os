"""Neutrosophic Causal Validator — 中智因果验证器.

Biological Metaphor:
  Immune system "danger theory" — not just self/non-self discrimination,
  but detection of DAMPs (Damage-Associated Molecular Patterns). Traditional
  Boolean logic (True/False) is like a binary immune response — either attack
  or tolerate. Neutrosophic logic adds a third dimension: uncertainty.

  Just as the immune system maintains a nuanced response (attack, tolerate,
  or surveil), our validator evaluates claims across three independent axes:
    T (Truth):      degree of supporting evidence
    I (Indeterminacy): uncertainty / incomplete information
    F (Falsity):    degree of refuting evidence

Key Innovation (v4.0):
  Three-dimensional truth value: (T, I, F) ∈ [0,1]³ where T+I+F ≤ 3.
  Do-operator interventions on Structural Causal Models preserve the I dimension.
  Multi-judge fusion maintains orthogonality of independent dimensions.

References:
  - Barbosa & Smarandache (June 2025): Neutrosophic causal AI
  - Pearl (2009): Causality — do-calculus foundation
  - Matzinger (1994): Danger theory in immunology
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class NeutrosophicVerdict:
    """A three-dimensional truth evaluation.

    (T, I, F) are independent dimensions:
      T ∈ [0,1]: degree of truth / supporting evidence
      I ∈ [0,1]: degree of indeterminacy / uncertainty
      F ∈ [0,1]: degree of falsity / refuting evidence

    Example: (0.7, 0.2, 0.1) means:
      70% likely true, 20% uncertain, 10% likely false
    """

    truth: float          # T — degree of truth
    indeterminacy: float  # I — degree of uncertainty
    falsity: float        # F — degree of falsity
    claim_id: str = ""
    validator_id: str = ""
    evidence_count: int = 0
    confidence_interval: tuple[float, float] = (0.0, 0.0)  # 95% CI for T
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        """Clamp values to [0, 1]."""
        self.truth = max(0.0, min(1.0, self.truth))
        self.indeterminacy = max(0.0, min(1.0, self.indeterminacy))
        self.falsity = max(0.0, min(1.0, self.falsity))

    @property
    def net_truth(self) -> float:
        """Net truth signal: T - F, ∈ [-1, 1]."""
        return self.truth - self.falsity

    @property
    def certainty(self) -> float:
        """Complement of indeterminacy: 1 - I."""
        return 1.0 - self.indeterminacy

    @property
    def is_decisive(self) -> bool:
        """Verdict has low uncertainty and clear truth/falsity separation."""
        return self.indeterminacy < 0.3 and abs(self.truth - self.falsity) > 0.3


@dataclass
class CausalIntervention:
    """Result of a do-operator causal intervention.

    do(X = x) — Pearl's do-calculus: actively setting a variable rather than
    passively observing it. The neutrosophic extension preserves the I dimension
    through the intervention.
    """

    intervention_var: str
    intervention_value: float
    outcome_distribution: np.ndarray        # P(Y | do(X=x))
    neutrosophic_effect: NeutrosophicVerdict  # Causal effect as (T,I,F)
    counterfactual_samples: int = 1000
    average_treatment_effect: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidatorConfig:
    """Configuration for the Neutrosophic Causal Validator."""

    accept_truth: float = 0.6          # T > θ_T to accept
    accept_falsity: float = 0.2        # F < θ_F to accept
    accept_indeterminacy: float = 0.3  # I < θ_I to accept
    do_samples: int = 1000
    merge_method: str = "weighted_average"  # weighted_average | min_max | dempster_shafer


# ═══════════════════════════════════════════════════════════════════════
# Core Validator
# ═══════════════════════════════════════════════════════════════════════


class NeutrosophicCausalValidator:
    """Validates claims using neutrosophic (T,I,F) three-dimensional logic.

    Unlike Boolean validators that output True/False, this validator
    quantifies how true, how uncertain, and how false a claim is—
    capturing the nuanced reality that claims can be partially true
    and partially false simultaneously.

    Usage::

        validator = NeutrosophicCausalValidator()
        verdict = validator.validate(claim, evidence_list)
        if validator.should_accept(verdict):
            print("Claim accepted")
        intervention = validator.do_intervention(causal_model, "X", 1.0)
    """

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        self._config = config or ValidatorConfig()
        self._logger = CortexLogger("neutrosophic_validator")

        self._verdicts: list[NeutrosophicVerdict] = []
        self._interventions: list[CausalIntervention] = []
        self._validation_count: int = 0

        self._logger.info("validator_initialized",
                          accept_t=self._config.accept_truth,
                          accept_f=self._config.accept_falsity,
                          accept_i=self._config.accept_indeterminacy)

    # ── Core Validation ───────────────────────────────────────────────

    def validate(
        self,
        claim: dict[str, Any],
        evidence: list[dict[str, Any]],
        validator_id: str = "",
    ) -> NeutrosophicVerdict:
        """Evaluate a claim against evidence, producing a (T,I,F) verdict.

        Args:
            claim: Claim dict with at least {'claim_id', 'predicate'}
            evidence: List of evidence items, each with {'strength', 'direction', 'reliability'}
            validator_id: ID of the validator (for multi-judge tracking)

        Returns:
            NeutrosophicVerdict with (T, I, F) dimensions
        """
        if not evidence:
            # No evidence → high indeterminacy
            return NeutrosophicVerdict(
                truth=0.0,
                indeterminacy=1.0,
                falsity=0.0,
                claim_id=claim.get("claim_id", ""),
                validator_id=validator_id,
                evidence_count=0,
                reasoning="No evidence provided — complete indeterminacy",
            )

        # Separate supporting and refuting evidence
        supporting = [e for e in evidence if e.get("direction", "support") == "support"]
        refuting = [e for e in evidence if e.get("direction", "") == "refute"]

        # Compute T: weighted truth from supporting evidence
        T = self._compute_dimension(supporting)

        # Compute F: weighted falsity from refuting evidence
        F = self._compute_dimension(refuting)

        # Compute I: indeterminacy from evidence gaps, conflicts, and unreliability
        I = self._compute_indeterminacy(evidence, T, F)

        # Normalize: ensure T + I + F doesn't exceed constraints
        # In neutrosophic logic, T, I, F are independent but we soft-normalize
        total = T + I + F
        if total > 2.5:
            scale = 2.5 / total
            T *= scale
            I *= scale
            F *= scale

        # Confidence interval: Wilson score interval approximation for T
        n = len(evidence)
        z = 1.96  # 95% CI
        if n > 0:
            denominator = 1 + z**2 / n
            center = (T + z**2 / (2 * n)) / denominator
            margin = z * math.sqrt(T * (1 - T) / n + z**2 / (4 * n**2)) / denominator
            ci = (max(0.0, center - margin), min(1.0, center + margin))
        else:
            ci = (0.0, 1.0)

        verdict = NeutrosophicVerdict(
            truth=T,
            indeterminacy=I,
            falsity=F,
            claim_id=claim.get("claim_id", ""),
            validator_id=validator_id,
            evidence_count=len(evidence),
            confidence_interval=ci,
            reasoning=f"T={T:.3f} from {len(supporting)} supporting, "
                      f"F={F:.3f} from {len(refuting)} refuting, "
                      f"I={I:.3f} from evidence gaps",
        )

        self._verdicts.append(verdict)
        self._validation_count += 1

        self._logger.debug("claim_validated",
                           claim_id=verdict.claim_id,
                           T=round(T, 3), I=round(I, 3), F=round(F, 3))

        return verdict

    def _compute_dimension(self, evidence_items: list[dict[str, Any]]) -> float:
        """Compute a single neutrosophic dimension from evidence items.

        Weighted aggregation: strength × reliability / (1 + staleness).
        """
        if not evidence_items:
            return 0.0

        weighted_sum = 0.0
        total_weight = 0.0

        for e in evidence_items:
            strength = float(e.get("strength", 0.5))
            reliability = float(e.get("reliability", 1.0))
            staleness = float(e.get("staleness", 0.0))  # Age penalty

            weight = reliability / (1.0 + staleness)
            weighted_sum += strength * weight
            total_weight += weight

        if total_weight == 0.0:
            return 0.0

        # Sigmoid activation for smooth [0,1] mapping
        raw = weighted_sum / total_weight
        return float(1.0 / (1.0 + math.exp(-5.0 * (raw - 0.5))))

    def _compute_indeterminacy(
        self,
        evidence: list[dict[str, Any]],
        T: float,
        F: float,
    ) -> float:
        """Compute indeterminacy (I) from evidence quality and conflict.

        I is high when:
        - Evidence is sparse or low-reliability
        - Supporting and refuting evidence conflict (both strong)
        - Evidence is stale
        """
        n = len(evidence)
        if n == 0:
            return 1.0

        # 1. Sparsity component
        sparsity = 1.0 / (1.0 + math.log(1 + n))

        # 2. Conflict component: T and F are both high → high conflict → high I
        conflict = 2.0 * min(T, F)  # Max when T == F == 0.5

        # 3. Unreliability component
        avg_reliability = np.mean([e.get("reliability", 1.0) for e in evidence])
        unreliability = 1.0 - avg_reliability

        # 4. Staleness component
        avg_staleness = np.mean([e.get("staleness", 0.0) for e in evidence])
        staleness_factor = avg_staleness / (1.0 + avg_staleness)

        # Weighted combination
        I = 0.25 * sparsity + 0.30 * conflict + 0.25 * unreliability + 0.20 * staleness_factor
        return max(0.0, min(1.0, I))

    # ── Acceptance Decision ───────────────────────────────────────────

    def should_accept(
        self,
        verdict: NeutrosophicVerdict,
        thresholds: tuple[float, float, float] | None = None,
    ) -> bool:
        """Determine if a verdict meets acceptance criteria.

        Default acceptance: T > 0.6 AND F < 0.2 AND I < 0.3.

        Args:
            verdict: The neutrosophic verdict to evaluate
            thresholds: Optional (T_accept, F_max, I_max) override

        Returns:
            True if the claim should be accepted
        """
        if thresholds is None:
            t_t, f_t, i_t = (self._config.accept_truth,
                             self._config.accept_falsity,
                             self._config.accept_indeterminacy)
        else:
            t_t, f_t, i_t = thresholds

        return bool(verdict.truth >= t_t and verdict.falsity <= f_t and verdict.indeterminacy <= i_t)

    # ── Multi-Judge Fusion ────────────────────────────────────────────

    def merge_verdicts(
        self,
        verdicts: list[NeutrosophicVerdict],
        method: str | None = None,
    ) -> NeutrosophicVerdict:
        """Merge multiple independent verdicts into a single consensus verdict.

        Preserves the orthogonality of (T,I,F) dimensions during fusion.

        Args:
            verdicts: List of verdicts from different judges
            method: Fusion method — 'weighted_average', 'min_max', or 'dempster_shafer'

        Returns:
            Merged NeutrosophicVerdict
        """
        if not verdicts:
            return NeutrosophicVerdict(truth=0.0, indeterminacy=1.0, falsity=0.0)

        if len(verdicts) == 1:
            return verdicts[0]

        method = method or self._config.merge_method

        if method == "weighted_average":
            return self._merge_weighted_average(verdicts)
        elif method == "min_max":
            return self._merge_min_max(verdicts)
        else:  # dempster_shafer approximation
            return self._merge_dempster_shafer(verdicts)

    def _merge_weighted_average(self, verdicts: list[NeutrosophicVerdict]) -> NeutrosophicVerdict:
        """Simple weighted average by evidence count."""
        total_evidence = sum(v.evidence_count for v in verdicts) or 1

        weights = [v.evidence_count / total_evidence for v in verdicts]
        T = sum(w * v.truth for w, v in zip(weights, verdicts))
        I = sum(w * v.indeterminacy for w, v in zip(weights, verdicts))
        F = sum(w * v.falsity for w, v in zip(weights, verdicts))

        return NeutrosophicVerdict(
            truth=T, indeterminacy=I, falsity=F,
            claim_id=verdicts[0].claim_id,
            evidence_count=total_evidence,
            reasoning=f"Merged {len(verdicts)} verdicts via weighted average",
        )

    def _merge_min_max(self, verdicts: list[NeutrosophicVerdict]) -> NeutrosophicVerdict:
        """Min-max conservative fusion: T=min, F=max (worst-case)."""
        T = min(v.truth for v in verdicts)
        F = max(v.falsity for v in verdicts)
        I = max(v.indeterminacy for v in verdicts)

        return NeutrosophicVerdict(
            truth=T, indeterminacy=I, falsity=F,
            claim_id=verdicts[0].claim_id,
            evidence_count=sum(v.evidence_count for v in verdicts),
            reasoning=f"Merged {len(verdicts)} verdicts via min-max (conservative)",
        )

    def _merge_dempster_shafer(self, verdicts: list[NeutrosophicVerdict]) -> NeutrosophicVerdict:
        """Dempster-Shafer inspired fusion.

        Treats (T, F) as belief/plausibility mass, I as uncertainty mass.
        Combines evidence using Dempster's rule of combination (normalized).
        """
        if len(verdicts) == 1:
            return verdicts[0]

        # Start with first verdict
        T_acc = verdicts[0].truth
        F_acc = verdicts[0].falsity
        I_acc = verdicts[0].indeterminacy

        for v in verdicts[1:]:
            # Dempster's rule: combine belief masses
            # K = conflict coefficient
            K = T_acc * v.falsity + F_acc * v.truth

            if K < 0.999:  # Avoid division by zero
                norm = 1.0 / (1.0 - K)
                T_acc = norm * (T_acc * v.truth + T_acc * v.indeterminacy + I_acc * v.truth)
                F_acc = norm * (F_acc * v.falsity + F_acc * v.indeterminacy + I_acc * v.falsity)
                I_acc = norm * I_acc * v.indeterminacy
            else:
                # High conflict: increase indeterminacy
                I_acc = min(1.0, I_acc + 0.2)

        return NeutrosophicVerdict(
            truth=T_acc, indeterminacy=I_acc, falsity=F_acc,
            claim_id=verdicts[0].claim_id,
            evidence_count=sum(v.evidence_count for v in verdicts),
            reasoning=f"Merged {len(verdicts)} verdicts via Dempster-Shafer",
        )

    # ── Do-Operator Intervention ──────────────────────────────────────

    def do_intervention(
        self,
        causal_model: dict[str, Any],
        variable: str,
        value: float,
        samples: int | None = None,
    ) -> CausalIntervention:
        """Perform a do-operator causal intervention: do(X = x).

        Pearl's do-calculus with neutrosophic extension — the I dimension
        captures uncertainty in the causal effect estimate.

        Args:
            causal_model: SCM dict with {'variables', 'edges', 'functions'}
            variable: Variable name to intervene on
            value: Value to set the variable to
            samples: Monte Carlo samples for effect estimation

        Returns:
            CausalIntervention with neutrosophic effect estimate
        """
        if samples is None:
            samples = self._config.do_samples

        rng = np.random.RandomState(42)

        # Simulate intervention outcomes
        base_effect = float(causal_model.get("base_effect", 0.0))
        noise_std = float(causal_model.get("noise_std", 0.1))
        confound_strength = float(causal_model.get("confound_strength", 0.0))

        # Generate counterfactual outcomes
        outcomes = base_effect * value + rng.normal(0, noise_std, samples)

        # Confounding introduces bias → captured as indeterminacy
        if confound_strength > 0:
            confound_bias = confound_strength * rng.normal(0, 1, samples)
            outcomes += confound_bias

        ate = float(np.mean(outcomes))  # Average Treatment Effect

        # Compute neutrosophic effect
        # T: strength of causal effect (normalized)
        T = float(1.0 / (1.0 + math.exp(-abs(ate))))

        # I: uncertainty from noise + confounding
        outcome_std = float(np.std(outcomes))
        I = min(1.0, (noise_std + confound_strength) / (outcome_std + 1e-10))

        # F: inverse of effect consistency
        F = min(1.0, outcome_std / (abs(ate) + 1e-10))

        effect = NeutrosophicVerdict(
            truth=T,
            indeterminacy=I,
            falsity=F,
            claim_id=f"do({variable}={value})",
            validator_id="do_operator",
            reasoning=f"ATE={ate:.4f}, σ={outcome_std:.4f}",
        )

        intervention = CausalIntervention(
            intervention_var=variable,
            intervention_value=value,
            outcome_distribution=outcomes,
            neutrosophic_effect=effect,
            counterfactual_samples=samples,
            average_treatment_effect=ate,
            metadata={"confound_strength": confound_strength, "noise_std": noise_std},
        )

        self._interventions.append(intervention)
        self._logger.debug("do_intervention",
                           variable=variable,
                           value=value,
                           ATE=round(ate, 4),
                           T=round(T, 3))

        return intervention

    # ── Properties ────────────────────────────────────────────────────

    @property
    def stats(self) -> dict[str, Any]:
        c = self._config
        return {
            "validation_count": self._validation_count,
            "stored_verdicts": len(self._verdicts),
            "interventions": len(self._interventions),
            "accept_thresholds": {
                "T": c.accept_truth,
                "F": c.accept_falsity,
                "I": c.accept_indeterminacy,
            },
            "merge_method": c.merge_method,
            "avg_truth": round(np.mean([v.truth for v in self._verdicts[-100:]]), 4)
            if self._verdicts else None,
        }

    def reset(self) -> None:
        """Reset all validation state."""
        self._verdicts.clear()
        self._interventions.clear()
        self._validation_count = 0
        self._logger.debug("validator_reset")
