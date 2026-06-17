"""Turing Patterning — local reaction-diffusion for spontaneous pattern formation.

Alan Turing's 1952 paper "The Chemical Basis of Morphogenesis":
Two morphogens (activator + inhibitor) with different diffusion rates
spontaneously generate stable spatial patterns — stripes, spots, labyrinths.

Activator (short-range): auto-catalyzes itself + activates inhibitor
Inhibitor (long-range): suppresses activator, diffuses faster

Pattern outcome depends on the ratio D_inhibitor / D_activator.
D_i/D_a > critical → Turing instability → stable pattern emerges.

2026 update (Caltech): "Guided self-organization" — Turing patterns are
not pure laissez-faire but guided by boundary conditions and mechanical constraints.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TuringParameters:
    """Parameters for the activator-inhibitor reaction-diffusion system."""

    activator_rate: float = 0.5  # a: auto-catalysis rate
    inhibitor_rate: float = 0.3  # b: inhibition rate
    activator_diffusion: float = 0.01  # D_a: short-range
    inhibitor_diffusion: float = 0.1  # D_i: long-range (> D_a)
    degradation: float = 0.05  # Degradation rate for both
    saturation: float = 0.1  # Saturation constant (prevents blowup)


@dataclass
class TuringPattern:
    """The resulting spatial pattern from Turing reaction-diffusion."""

    activator_field: list[list[float]]
    inhibitor_field: list[list[float]]
    pattern_type: str  # "spots", "stripes", "labyrinth", "uniform"
    dominant_wavelength: float
    stability: float  # 0-1, how stable the pattern is
    iteration_count: int


class TuringPatterning:
    """Local Turing reaction-diffusion for agent specialization patterning.

    The standard activator-inhibitor model (Gierer-Meinhardt):
        ∂a/∂t = D_a·∇²a + ρ·(a²/(1+κa²)·h⁻¹) - μ_a·a
        ∂h/∂t = D_h·∇²h + ρ·a² - μ_h·h

    where:
    - a = activator concentration (auto-catalyzing)
    - h = inhibitor concentration (suppresses activator)
    - D_a << D_h (inhibitor diffuses much faster)
    - ρ = production rate, κ = saturation, μ = degradation
    """

    def __init__(
        self,
        grid_size: int = 32,
        activator_rate: float = 0.5,
        inhibitor_rate: float = 0.3,
        activator_diffusion: float = 0.01,
        inhibitor_diffusion: float = 0.1,
        degradation: float = 0.05,
        saturation: float = 0.1,
        seed: int | None = None,
    ) -> None:
        self._grid = grid_size
        self._params = TuringParameters(
            activator_rate=activator_rate,
            inhibitor_rate=inhibitor_rate,
            activator_diffusion=activator_diffusion,
            inhibitor_diffusion=inhibitor_diffusion,
            degradation=degradation,
            saturation=saturation,
        )

        import random
        rng = random.Random(seed)
        self._activator = [[rng.random() * 0.1 for _ in range(grid_size)] for _ in range(grid_size)]
        self._inhibitor = [[rng.random() * 0.1 for _ in range(grid_size)] for _ in range(grid_size)]
        self._iteration = 0

    def step(self, dt: float = 0.01) -> None:
        """Evolve one timestep of the reaction-diffusion system."""
        p = self._params
        n = self._grid
        new_a = [[0.0] * n for _ in range(n)]
        new_h = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                # Laplacian (5-point stencil)
                lap_a = self._laplacian(self._activator, i, j)
                lap_h = self._laplacian(self._inhibitor, i, j)

                a = self._activator[i][j]
                h = self._inhibitor[i][j]

                # Gierer-Meinhardt kinetics
                production = p.activator_rate * (a ** 2) / ((1.0 + p.saturation * a ** 2) * max(h, 1e-6))
                da = p.activator_diffusion * lap_a + production - p.degradation * a
                dh = p.inhibitor_diffusion * lap_h + p.inhibitor_rate * a ** 2 - p.degradation * h

                new_a[i][j] = max(0.0, a + da * dt)
                new_h[i][j] = max(0.0, h + dh * dt)

        self._activator = new_a
        self._inhibitor = new_h
        self._iteration += 1

    def _laplacian(self, field: list[list[float]], i: int, j: int) -> float:
        """5-point discrete Laplacian with periodic boundary conditions."""
        n = len(field)
        up = field[(i - 1) % n][j]
        down = field[(i + 1) % n][j]
        left = field[i][(j - 1) % n]
        right = field[i][(j + 1) % n]
        center = field[i][j]
        return up + down + left + right - 4.0 * center

    def evolve(self, iterations: int, dt: float = 0.01) -> TuringPattern:
        """Evolve the Turing system for a number of iterations."""
        for _ in range(iterations):
            self.step(dt)
        return self.get_pattern()

    def get_pattern(self) -> TuringPattern:
        """Retrieve the current pattern state."""
        n = self._grid
        a_vals = [self._activator[i][j] for i in range(n) for j in range(n)]

        mean_a = sum(a_vals) / len(a_vals)
        var_a = sum((v - mean_a) ** 2 for v in a_vals) / len(a_vals)
        std_a = math.sqrt(var_a)

        # Pattern type classification
        if std_a < 0.05:
            pattern_type = "uniform"
        elif self._estimate_wavelength() > n / 3:
            pattern_type = "spots"
        elif self._estimate_wavelength() < n / 6:
            pattern_type = "labyrinth"
        else:
            pattern_type = "stripes"

        stability = 1.0 / (1.0 + std_a)

        return TuringPattern(
            activator_field=[row[:] for row in self._activator],
            inhibitor_field=[row[:] for row in self._inhibitor],
            pattern_type=pattern_type,
            dominant_wavelength=self._estimate_wavelength(),
            stability=stability,
            iteration_count=self._iteration,
        )

    def _estimate_wavelength(self) -> float:
        """Estimate dominant spatial wavelength via autocorrelation."""
        n = self._grid
        center_row = self._activator[n // 2]
        mean = sum(center_row) / n
        autocorr: list[float] = []
        for lag in range(n // 2):
            corr = 0.0
            for i in range(n - lag):
                corr += (center_row[i] - mean) * (center_row[i + lag] - mean)
            autocorr.append(corr / max(n - lag, 1))

        # Find first zero-crossing → dominant wavelength
        for i in range(1, len(autocorr)):
            if autocorr[i] < 0 and autocorr[i - 1] >= 0:
                return float(i * 2)  # Wavelength = 2 * half-period

        return float(n)

    def set_boundary_condition(self, row_range: tuple[int, int], value: float) -> None:
        """Apply boundary condition (guided self-organization)."""
        r0, r1 = row_range
        for i in range(r0, min(r1, self._grid)):
            for j in range(self._grid):
                self._activator[i][j] = value

    @property
    def params(self) -> TuringParameters:
        return self._params

    @property
    def stats(self) -> dict[str, Any]:
        pattern = self.get_pattern()
        return {
            "grid_size": self._grid,
            "iteration": self._iteration,
            "pattern_type": pattern.pattern_type,
            "dominant_wavelength": pattern.dominant_wavelength,
            "stability": pattern.stability,
            "diffusion_ratio": self._params.inhibitor_diffusion / max(self._params.activator_diffusion, 1e-10),
        }
