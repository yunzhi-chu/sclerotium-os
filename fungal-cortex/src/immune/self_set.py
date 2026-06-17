"""Self Set — defines "normal" system behavior patterns.

The immune system doesn't store all "bad" patterns (infinitely many) —
it only stores "good" (Self) patterns. Anything that doesn't match Self
is anomalous (Nonself).

Self-set = normal market behavior feature vectors.
Radius r defines the boundary: anything within r of a Self point is "safe".
"""

from __future__ import annotations

import time
from typing import Any


class SelfSet:
    """Self-set of normal behavior feature vectors.

    Trained on historical "normal" market states.
    Detection: if distance to nearest Self point > radius → anomaly.
    """

    def __init__(self, radius: float = 0.1) -> None:
        self._radius = radius
        self._self_points: list[list[float]] = []
        self._feature_names: list[str] = []
        self._trained = False
        self._training_samples = 0
        self._created_at = time.time()

    def train(self, samples: list[list[float]], feature_names: list[str] | None = None) -> None:
        """Train the Self set with normal behavior samples.

        Each sample is a vector of normalized features describing a "normal" state.
        """
        if not samples:
            return
        self._self_points = [list(s) for s in samples]
        self._feature_names = feature_names or [f"f{i}" for i in range(len(samples[0]))]
        self._training_samples = len(samples)
        self._trained = True

    def add_self_point(self, point: list[float]) -> None:
        """Add a single point to the Self set (online learning)."""
        self._self_points.append(list(point))
        self._training_samples += 1
        if not self._feature_names and point:
            self._feature_names = [f"f{i}" for i in range(len(point))]

    def remove_self_point(self, point: list[float]) -> bool:
        """Remove a point from Self set (if behavior is no longer considered normal)."""
        for i, sp in enumerate(self._self_points):
            if self._distance(sp, point) < 1e-9:
                self._self_points.pop(i)
                self._training_samples -= 1
                return True
        return False

    def is_self(self, point: list[float]) -> bool:
        """Check if a point is within the Self boundary.

        Returns True if the point is "normal" (within radius of any Self point).
        """
        if not self._self_points:
            return False
        min_dist = self.min_distance(point)
        return min_dist <= self._radius

    def min_distance(self, point: list[float]) -> float:
        """Compute minimum Euclidean distance to any Self point."""
        if not self._self_points:
            return float("inf")
        return min(self._distance(point, sp) for sp in self._self_points)

    def boundary_violation(self, point: list[float]) -> dict[str, Any]:
        """Detailed violation report for a point."""
        min_dist = self.min_distance(point)
        return {
            "is_self": min_dist <= self._radius,
            "min_distance": round(min_dist, 6),
            "radius": self._radius,
            "violation_magnitude": round(max(0.0, min_dist - self._radius), 6),
            "severity": "normal" if min_dist <= self._radius else (
                "low" if min_dist <= self._radius * 1.5 else (
                    "medium" if min_dist <= self._radius * 2.5 else "high"
                )
            ),
        }

    @staticmethod
    def _distance(a: list[float], b: list[float]) -> float:
        return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

    @property
    def radius(self) -> float:
        return self._radius

    @radius.setter
    def radius(self, value: float) -> None:
        self._radius = max(0.0, value)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "trained": self._trained,
            "training_samples": self._training_samples,
            "self_points": len(self._self_points),
            "radius": self._radius,
            "feature_count": len(self._feature_names),
            "feature_names": list(self._feature_names),
            "coverage_volume": f"~{len(self._self_points) * (self._radius ** len(self._feature_names)):.2e}" if self._feature_names else "N/A",
        }
