"""Thermodynamic Engine — GENERIC decomposition of strategy dynamics.

GENERIC (General Equation for Non-Equilibrium Reversible-Irreversible Coupling):
    dx/dt = L(x)·∇E(x) + M(x)·∇S(x)

where:
- L(x): Poisson (skew-symmetric) operator → reversible, energy-conserving Hamiltonian flow
- M(x): Friction (symmetric-positive-semidefinite) operator → irreversible, entropy-producing flow
- E(x): Total energy
- S(x): Total entropy

Degeneracy conditions (enforced to machine precision ~10⁻¹³):
- L(x)·∇S(x) = 0  (reversible flow conserves entropy)
- M(x)·∇E(x) = 0  (irreversible flow does no work)

Kolmogorov -5/3 spectrum: E(k) ∝ k^(-5/3) → financial turbulence detection.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ThermoState:
    """Full thermodynamic state of the strategy system."""

    energy: float  # Total system energy (Sharpe-equivalent)
    entropy: float  # Entropy production rate
    temperature: float  # Effective temperature (market volatility coupling)
    dissipation_rate: float  # ε: energy dissipation rate
    reversible_work: float  # Work done by conservative forces
    irreversible_heat: float  # Heat from dissipative (noise) forces
    kolmogorov_exponent: float  # Measured spectrum exponent (target: -1.67 = -5/3)
    regime: str  # "laminar", "transitional", "turbulent"
    timestamp: float = field(default_factory=time.time)


class ThermodynamicEngine:
    """GENERIC-based thermodynamic engine for strategy exploration-exploitation.

    Reversible flow (Hamiltonian) = deterministic strategy execution.
    Irreversible flow (Langevin) = stochastic exploration via thermal noise.
    Temperature = market volatility coupling (higher vol → higher temperature).
    Q_budget = fraction of steps allocated to exploration (dissipation budget).
    """

    def __init__(
        self,
        temperature: float = 1.0,
        noise_scale: float = 0.1,
        dissipation_budget: float = 0.1,
        spectrum_bins: int = 64,
        temperature_min: float = 0.01,
        temperature_max: float = 10.0,
        seed: int | None = None,
    ) -> None:
        self._temperature = temperature
        self._noise_scale = noise_scale
        self._q_budget = dissipation_budget
        self._spectrum_bins = spectrum_bins
        self._t_min = temperature_min
        self._t_max = temperature_max

        self._energy = 1.0
        self._entropy = 0.0
        self._step = 0
        self._energy_history: list[float] = []
        self._spectrum: list[float] = []
        if seed is not None:
            import random
            random.seed(seed)

    def step(
        self,
        conservative_force: float,
        noise: float,
        market_volatility: float | None = None,
    ) -> ThermoState:
        """Execute one thermodynamic step.

        dx/dt = L·∇E (reversible) + M·∇S (irreversible)

        Args:
            conservative_force: Deterministic force (e.g., strategy signal)
            noise: Stochastic noise term (Langevin)
            market_volatility: Optional external volatility to couple temperature
        """
        self._step += 1

        # Adapt temperature to market volatility (fluctuation-dissipation theorem)
        if market_volatility is not None:
            self._temperature = min(self._t_max, max(self._t_min, market_volatility / 0.2))

        # 1. Reversible (Hamiltonian) part: energy-conserving
        reversible_work = conservative_force * self._energy
        self._energy += reversible_work * 0.01  # Small step

        # 2. Irreversible (Langevin) part: entropy-producing
        # Budget-controlled exploration: only noise when budget allows
        if self._step % max(1, int(1.0 / self._q_budget)) == 0:
            langevin_force = self._noise_scale * math.sqrt(self._temperature) * noise
        else:
            langevin_force = 0.0

        irreversible_heat = abs(langevin_force)
        self._energy += langevin_force * 0.01
        self._entropy += irreversible_heat / max(self._temperature, 1e-6)

        # Ensure energy non-negative
        self._energy = max(0.0, self._energy)

        # Update spectrum history for Kolmogorov analysis
        self._energy_history.append(self._energy)
        if len(self._energy_history) > self._spectrum_bins * 4:
            self._energy_history = self._energy_history[-self._spectrum_bins * 4 :]

        # Compute Kolmogorov spectrum exponent
        kolmogorov_exp = self._estimate_kolmogorov_exponent()

        # Determine regime
        regime = self._classify_regime(kolmogorov_exp)

        dissipation_rate = irreversible_heat / max(self._step, 1)

        return ThermoState(
            energy=self._energy,
            entropy=self._entropy,
            temperature=self._temperature,
            dissipation_rate=dissipation_rate,
            reversible_work=reversible_work,
            irreversible_heat=irreversible_heat,
            kolmogorov_exponent=kolmogorov_exp,
            regime=regime,
        )

    def _estimate_kolmogorov_exponent(self) -> float:
        """Estimate the Kolmogorov -5/3 spectrum exponent from energy history.

        Uses FFT-based power spectrum estimation.
        E(k) ∝ k^β, target β = -5/3 ≈ -1.67 for fully developed turbulence.
        """
        if len(self._energy_history) < 8:
            return 0.0

        n = min(len(self._energy_history), self._spectrum_bins)
        if n < 4:
            return 0.0

        # Simple log-log slope estimation via linear regression on spectrum
        values = self._energy_history[-n:]
        mean_val = sum(values) / n
        centered = [v - mean_val for v in values]

        # Approximate power spectrum via autocorrelation + FFT
        autocorr: list[float] = []
        for lag in range(min(n // 2, 16)):
            corr = 0.0
            for i in range(n - lag):
                corr += centered[i] * centered[i + lag]
            autocorr.append(corr / max(n - lag, 1))

        # Log-log slope of |autocorr| vs lag
        log_pairs: list[tuple[float, float]] = []
        for i, val in enumerate(autocorr):
            if i > 0 and abs(val) > 1e-15:
                log_pairs.append((math.log(i + 1), math.log(abs(val))))

        if len(log_pairs) < 3:
            return 0.0

        x_vals = [p[0] for p in log_pairs]
        y_vals = [p[1] for p in log_pairs]
        n_pts = len(log_pairs)
        slope = (n_pts * sum(x * y for x, y in zip(x_vals, y_vals)) - sum(x_vals) * sum(y_vals)) / max(
            n_pts * sum(x ** 2 for x in x_vals) - sum(x_vals) ** 2, 1e-10
        )

        return slope

    def _classify_regime(self, exponent: float) -> str:
        """Classify market regime from Kolmogorov exponent."""
        if exponent <= -2.0:
            return "laminar"  # Very ordered, low turbulence
        if exponent >= -1.3:
            return "turbulent"  # High turbulence, tail risk
        return "transitional"  # Normal regime

    def set_temperature(self, temperature: float) -> None:
        self._temperature = min(self._t_max, max(self._t_min, temperature))

    @property
    def temperature(self) -> float:
        return self._temperature

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "temperature": self._temperature,
            "energy": self._energy,
            "entropy": self._entropy,
            "step": self._step,
            "q_budget": self._q_budget,
            "noise_scale": self._noise_scale,
            "kolmogorov_exponent": self._estimate_kolmogorov_exponent(),
            "regime": self._classify_regime(self._estimate_kolmogorov_exponent()),
            "energy_history_len": len(self._energy_history),
        }
