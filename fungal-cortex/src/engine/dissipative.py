"""Dissipative Flow — irreversible, entropy-producing dynamics.

M(x)·∇S(x): The friction (symmetric-positive-semidefinite) operator applied to
the entropy gradient produces irreversible dynamics that increase total entropy.

In finance: this represents stochastic exploration (Langevin noise), market impact,
and other entropy-increasing processes. The dissipation budget Q_budget controls
the exploration-exploitation tradeoff.

Degeneracy condition: M(x)·∇E(x) = 0 (irreversible flow does no work on the system).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any


@dataclass
class LangevinNoise:
    """Langevin noise source — thermal fluctuations driving exploration."""

    amplitude: float  # σ = sqrt(2 * γ * k_B * T)
    temperature: float  # T
    friction: float  # γ (damping coefficient)

    def sample(self) -> float:
        """Sample from Langevin noise distribution: N(0, σ²=2γk_B T·dt)."""
        std = math.sqrt(2.0 * self.friction * self.temperature * 0.01) * self.amplitude
        return random.gauss(0.0, std)


class DissipativeFlow:
    """Irreversible dissipative dynamics — entropy production with noise control.

    The dissipation budget Q_budget explicitly controls exploration vs exploitation:
    - Q_budget high → more noise → more exploration
    - Q_budget low → less noise → more exploitation (following conservative flow)

    Financial interpretation:
    - Entropy production = market impact + information decay + model uncertainty
    - Fluctuation-Dissipation Theorem links noise amplitude to market temperature
    """

    def __init__(
        self,
        friction: float = 0.1,
        temperature: float = 1.0,
        noise_amplitude: float = 1.0,
        dissipation_budget: float = 0.1,
        seed: int | None = None,
    ) -> None:
        self._friction = friction
        self._temperature = temperature
        self._noise_amplitude = noise_amplitude
        self._q_budget = dissipation_budget
        self._entropy = 0.0
        self._heat = 0.0
        self._noise = LangevinNoise(amplitude=noise_amplitude, temperature=temperature, friction=friction)
        self._step_count = 0
        if seed is not None:
            random.seed(seed)

    def step(self, gradient: float, dt: float = 0.01) -> dict[str, float]:
        """Apply irreversible dynamics: friction + noise.

        M·∇S = -γ·p + σ·ξ(t)

        where:
        - γ·p: friction term (momentum damping)
        - σ·ξ(t): Langevin noise (thermal fluctuations)
        """
        self._step_count += 1

        # Friction: dissipates energy, increases entropy
        friction_work = -self._friction * gradient * dt
        self._entropy += abs(friction_work) / max(self._temperature, 1e-6)

        # Langevin noise: budget-controlled exploration
        if self._step_count % max(1, int(1.0 / self._q_budget)) == 0:
            noise_term = self._noise.sample() * dt
        else:
            noise_term = 0.0

        self._heat += abs(noise_term)

        # Total irreversible force
        total_force = friction_work + noise_term

        return {
            "friction_work": friction_work,
            "noise_term": noise_term,
            "total_force": total_force,
            "entropy": self._entropy,
            "cumulative_heat": self._heat,
        }

    def set_temperature(self, temperature: float) -> None:
        self._temperature = temperature
        self._noise = LangevinNoise(
            amplitude=self._noise_amplitude,
            temperature=temperature,
            friction=self._friction,
        )

    @property
    def temperature(self) -> float:
        return self._temperature

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "entropy": self._entropy,
            "cumulative_heat": self._heat,
            "friction": self._friction,
            "temperature": self._temperature,
            "noise_amplitude": self._noise_amplitude,
            "q_budget": self._q_budget,
            "step_count": self._step_count,
        }
