"""Resilience Metrics — distinguish ecological resilience from engineering resilience.

Engineering resilience: how fast a system returns to equilibrium after disturbance.
  Measured as recovery time — faster = "better." But this is dangerous:
  a system that bounces back fast is often brittle (high connectedness, low diversity).

Ecological resilience: how much disturbance a system can absorb before
  flipping to a different regime (alternative stable state).
  Measured as the size of the basin of attraction.

Key metrics:
- Spectral radius: largest eigenvalue of interaction matrix (stability boundary)
- Diversity index: Shannon entropy of agent/strategy distribution
- Modularity: how compartmentalized the system is (firebreaks)
- Reactivity: maximum initial amplification of a perturbation
- Robustness: fraction of components that can fail before system collapse
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResilienceProfile:
    """Complete resilience assessment of the system."""

    ecological_resilience: float  # Size of basin of attraction
    engineering_resilience: float  # Recovery speed
    diversity_index: float  # Shannon entropy of components
    modularity: float  # Compartmentalization degree
    robustness: float  # Fraction of failures tolerated
    reactivity: float  # Amplification of small perturbations
    critical_slowness: float  # Recovery time approaching threshold
    overall_resilience: float
    regime_shift_risk: float  # Probability of flipping to alternative state


class ResilienceMetrics:
    """Compute resilience metrics distinguishing ecological from engineering resilience.

    WARNING: High engineering resilience (fast recovery) often masks
    low ecological resilience — the system bounces back quickly until
    it doesn't bounce back at all (regime shift).
    """

    def __init__(self, component_count: int = 10) -> None:
        self._n = component_count
        self._interaction_matrix: list[list[float]] = [
            [0.0] * component_count for _ in range(component_count)
        ]
        self._component_fitness: list[float] = [1.0] * component_count
        self._disturbance_history: list[float] = []

    def set_interaction(self, from_idx: int, to_idx: int, strength: float) -> None:
        """Set the interaction strength between two components."""
        if 0 <= from_idx < self._n and 0 <= to_idx < self._n:
            self._interaction_matrix[from_idx][to_idx] = strength

    def set_fitness(self, component_idx: int, fitness: float) -> None:
        if 0 <= component_idx < self._n:
            self._component_fitness[component_idx] = fitness

    def compute_ecological_resilience(self) -> float:
        """Estimate ecological resilience as the basin of attraction size.

        Approximated as 1 / spectral_radius of the interaction matrix.
        Larger spectral radius → smaller basin → less resilient.
        """
        spectral_radius = self._estimate_spectral_radius()
        if spectral_radius < 1e-10:
            return 1.0
        return min(1.0, 1.0 / spectral_radius)

    def compute_engineering_resilience(self) -> float:
        """Estimate engineering resilience as recovery speed.

        Approximated as: average of component fitness / spectral radius.
        Higher = faster recovery — but potentially more brittle.
        """
        avg_fitness = sum(self._component_fitness) / max(len(self._component_fitness), 1)
        spectral_radius = self._estimate_spectral_radius()
        if spectral_radius < 1e-10:
            return avg_fitness
        return min(1.0, avg_fitness / spectral_radius)

    def compute_diversity(self) -> float:
        """Shannon diversity index of component fitness distribution."""
        total = sum(self._component_fitness)
        if total == 0:
            return 0.0

        entropy = 0.0
        for f in self._component_fitness:
            if f > 0:
                p = f / total
                entropy -= p * math.log2(p)

        max_entropy = math.log2(max(len(self._component_fitness), 2))
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def compute_modularity(self) -> float:
        """Estimate modularity: how compartmentalized is the interaction matrix.

        High modularity = subsystems are decoupled → firebreaks prevent cascading failures.
        """
        n = self._n
        if n < 2:
            return 1.0

        # Count non-zero interactions within vs across "modules"
        mid = n // 2
        within = 0
        across = 0

        for i in range(n):
            for j in range(n):
                if self._interaction_matrix[i][j] != 0:
                    if (i < mid and j < mid) or (i >= mid and j >= mid):
                        within += 1
                    else:
                        across += 1

        total = within + across
        if total == 0:
            return 0.5
        return within / total

    def compute_robustness(self, failure_threshold: float = 0.3) -> float:
        """Fraction of components that can fail before system collapse.

        Simulates sequential failure of weakest components and checks
        when average fitness drops below threshold.
        """
        sorted_fitness = sorted(self._component_fitness)
        n = len(sorted_fitness)
        cumulative = 0.0

        for i, f in enumerate(sorted_fitness):
            cumulative += f
            remaining = n - i - 1
            if remaining == 0:
                return 1.0
            avg_after_failure = (sum(sorted_fitness) - cumulative) / remaining
            if avg_after_failure < failure_threshold:
                return (i + 1) / n

        return 1.0

    def compute_reactivity(self) -> float:
        """Maximum initial amplification of a small perturbation.

        High reactivity = small disturbances grow quickly → early warning signal.
        """
        max_row_sum = 0.0
        for row in self._interaction_matrix:
            row_sum = sum(abs(v) for v in row)
            max_row_sum = max(max_row_sum, row_sum)
        return min(1.0, max_row_sum)

    def compute_critical_slowness(self) -> float:
        """Recovery rate slows as system approaches tipping point.

        Critical slowing down is a universal early warning signal
        for impending regime shifts.
        """
        if len(self._disturbance_history) < 2:
            return 0.0

        # Autocorrelation at lag-1 as indicator of critical slowing
        recent = self._disturbance_history[-50:]
        n = len(recent)
        if n < 2:
            return 0.0

        mean = sum(recent) / n
        lag1_corr = sum((recent[i] - mean) * (recent[i - 1] - mean) for i in range(1, n)) / max(
            sum((v - mean) ** 2 for v in recent), 1e-10
        )
        return max(0.0, min(1.0, lag1_corr))

    def assess(self) -> ResilienceProfile:
        """Full resilience assessment."""
        eco_res = self.compute_ecological_resilience()
        eng_res = self.compute_engineering_resilience()
        diversity = self.compute_diversity()
        modularity = self.compute_modularity()
        robustness = self.compute_robustness()
        reactivity = self.compute_reactivity()
        critical_slowness = self.compute_critical_slowness()

        # Overall resilience: geometric mean of key components
        overall = (eco_res * diversity * modularity * robustness) ** 0.25

        # Regime shift risk: high when engineering >> ecological resilience
        regime_shift_risk = max(0.0, min(1.0, (eng_res - eco_res) / max(eng_res, 0.1)))

        return ResilienceProfile(
            ecological_resilience=eco_res,
            engineering_resilience=eng_res,
            diversity_index=diversity,
            modularity=modularity,
            robustness=robustness,
            reactivity=reactivity,
            critical_slowness=critical_slowness,
            overall_resilience=overall,
            regime_shift_risk=regime_shift_risk,
        )

    def record_disturbance(self, disturbance: float) -> None:
        self._disturbance_history.append(disturbance)
        if len(self._disturbance_history) > 500:
            self._disturbance_history = self._disturbance_history[-500:]

    def _estimate_spectral_radius(self) -> float:
        """Power iteration to estimate spectral radius (largest |eigenvalue|)."""
        n = self._n
        if n == 0:
            return 0.0

        vec = [1.0] * n
        for _ in range(20):
            new_vec = [0.0] * n
            for i in range(n):
                for j in range(n):
                    new_vec[i] += self._interaction_matrix[i][j] * vec[j]
            norm = math.sqrt(sum(v ** 2 for v in new_vec))
            if norm < 1e-15:
                return 0.0
            vec = [v / norm for v in new_vec]

        # Rayleigh quotient
        av = [0.0] * n
        for i in range(n):
            for j in range(n):
                av[i] += self._interaction_matrix[i][j] * vec[j]
        eigenvalue = sum(vec[i] * av[i] for i in range(n))
        return abs(eigenvalue)

    @property
    def stats(self) -> dict[str, Any]:
        profile = self.assess()
        return {
            "ecological_resilience": profile.ecological_resilience,
            "engineering_resilience": profile.engineering_resilience,
            "diversity": profile.diversity_index,
            "modularity": profile.modularity,
            "robustness": profile.robustness,
            "overall_resilience": profile.overall_resilience,
            "regime_shift_risk": profile.regime_shift_risk,
        }
