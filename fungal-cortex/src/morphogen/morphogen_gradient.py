"""Morphogen Gradient — global "positional information" for the agent ecosystem.

In embryonic development, morphogen gradients (BMP, Shh, Wnt) tell cells
where they are in the body plan. Without gradients, every cell would be
identical — no differentiation, no specialization.

In Fungal Cortex: the gradient encodes "market regime position" —
where are we in the current market landscape? This global signal
guides agent differentiation (what role should each agent take?).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GradientPoint:
    """A point on the morphogen gradient with position and concentration."""

    position: tuple[float, ...]  # N-dimensional position in "market space"
    concentration: float  # Morphogen concentration at this position
    gradient_vector: list[float]  # ∇C: direction of steepest change


@dataclass
class GradientField:
    """The full morphogen gradient field."""

    points: list[GradientPoint]
    source_position: tuple[float, ...]  # Where morphogen is produced
    decay_length: float  # λ: characteristic decay length
    timestamp: float = field(default_factory=lambda: __import__("time").time())


class MorphogenGradient:
    """Global morphogen gradient — provides positional information to all agents.

    The gradient is centered on a "source" (market regime attractor) and
    decays exponentially with distance: C(x) = C₀ · exp(-|x - source| / λ)

    Agents sense local gradient → determine their "position" in the ecosystem
    → differentiate into appropriate roles (regime/strategy/indicator/tactics/risk).

    BMP-style temporal integration: agents integrate gradient over time,
    not just instantaneous concentration.
    """

    def __init__(self, gradient_length: float = 1.0, dimensions: int = 4) -> None:
        self._length = gradient_length  # λ: decay length
        self._dims = dimensions
        self._source = tuple(0.0 for _ in range(dimensions))
        self._concentration_max = 1.0
        self._history: list[float] = []  # Temporal integration buffer

    def set_source(self, position: tuple[float, ...]) -> None:
        """Set the source position (market regime attractor)."""
        if len(position) != self._dims:
            raise ValueError(f"Expected {self._dims}-dim position, got {len(position)}")
        self._source = position

    def concentration_at(self, position: tuple[float, ...]) -> float:
        """Compute morphogen concentration at a given position.

        C(x) = C₀ · exp(-|x - source| / λ)
        """
        if len(position) != self._dims:
            raise ValueError(f"Expected {self._dims}-dim position, got {len(position)}")

        distance = math.sqrt(sum((p - s) ** 2 for p, s in zip(position, self._source)))
        concentration = self._concentration_max * math.exp(-distance / self._length)
        return concentration

    def gradient_at(self, position: tuple[float, ...]) -> list[float]:
        """Compute gradient vector ∇C at a given position.

        ∂C/∂x_i = -(x_i - source_i) / (λ · |x - source|) · C(x)
        """
        if len(position) != self._dims:
            raise ValueError(f"Expected {self._dims}-dim position, got {len(position)}")

        distance = math.sqrt(sum((p - s) ** 2 for p, s in zip(position, self._source)))
        if distance < 1e-10:
            return [0.0] * self._dims

        concentration = self.concentration_at(position)
        gradient = [
            -(p - s) * concentration / (self._length * distance)
            for p, s in zip(position, self._source)
        ]
        return gradient

    def sense(self, position: tuple[float, ...]) -> GradientPoint:
        """Agent senses local morphogen concentration and gradient."""
        concentration = self.concentration_at(position)
        gradient = self.gradient_at(position)
        self._history.append(concentration)
        if len(self._history) > 1000:
            self._history = self._history[-1000:]
        return GradientPoint(position=position, concentration=concentration, gradient_vector=gradient)

    def sample_field(self, resolution: int = 10) -> GradientField:
        """Sample the full gradient field on a grid."""
        points: list[GradientPoint] = []
        for idx in range(resolution):
            t = idx / (resolution - 1) if resolution > 1 else 0.5
            pos = tuple(t for _ in range(self._dims))
            points.append(self.sense(pos))
        return GradientField(points=points, source_position=self._source, decay_length=self._length)

    def temporal_integration(self, window: int = 10) -> float:
        """BMP-style temporal integration: average concentration over recent window."""
        if not self._history:
            return 0.0
        recent = self._history[-window:]
        return sum(recent) / len(recent)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "source": self._source,
            "decay_length": self._length,
            "dimensions": self._dims,
            "concentration_max": self._concentration_max,
            "temporal_avg": self.temporal_integration(),
            "history_len": len(self._history),
        }
