"""Negative Selector — generates detectors that cover Nonself space.

Inspired by T-cell maturation in the thymus:
- Generate random candidate detectors
- Eliminate any that match Self (negative selection)
- Only detectors that DON'T match Self survive → cover Nonself space

Target: ≥99% Nonself coverage, <5% false positive rate.
"""

from __future__ import annotations

import random
import time
from typing import Any


class NegativeSelector:
    """Negative selection algorithm for anomaly detection.

    Generates detectors that cover the Nonself space without overlapping Self.
    Each detector is a hypersphere in feature space.
    """

    def __init__(
        self,
        detector_count: int = 1000,
        target_coverage: float = 0.99,
        max_false_positive: float = 0.05,
        seed: int | None = None,
    ) -> None:
        self._target_count = detector_count
        self._target_coverage = target_coverage
        self._max_false_positive = max_false_positive
        self._detectors: list[dict[str, Any]] = []  # Each: {center, radius, id, created_at}
        self._self_set = None  # Reference to SelfSet, set via bind()
        self._feature_count = 0
        self._rng = random.Random(seed)
        self._generation_count = 0
        self._total_candidates = 0
        self._accepted_count = 0

    def bind_self(self, self_set: object) -> None:
        """Bind to a SelfSet instance for negative selection."""
        self._self_set = self_set
        if hasattr(self_set, 'stats'):
            self._feature_count = self_set.stats.get("feature_count", 0)

    def generate_detectors(self) -> dict[str, Any]:
        """Generate detectors via the negative selection algorithm.

        Each candidate detector is a random hypersphere.
        If it overlaps with any Self point → reject.
        If it doesn't overlap with Self → accept (cover Nonself).
        """
        if self._self_set is None:
            return {"error": "SelfSet not bound. Call bind_self() first."}

        self._generation_count += 1
        self._total_candidates = 0
        self._accepted_count = 0

        max_attempts = self._target_count * 10
        attempts = 0

        while len(self._detectors) < self._target_count and attempts < max_attempts:
            attempts += 1
            self._total_candidates += 1

            # Generate random candidate detector
            center = [self._rng.random() for _ in range(self._feature_count)]
            radius = self._rng.uniform(0.01, 0.15)

            # Negative selection: reject if it matches any Self point
            if self._matches_self(center, radius):
                continue

            # Accept: this detector covers Nonself space
            self._detectors.append({
                "id": f"det-{len(self._detectors)}",
                "center": center,
                "radius": radius,
                "created_at": time.time(),
                "detections": 0,
            })
            self._accepted_count += 1

        return {
            "generation": self._generation_count,
            "candidates_tested": self._total_candidates,
            "detectors_accepted": self._accepted_count,
            "total_detectors": len(self._detectors),
            "acceptance_rate": self._accepted_count / max(self._total_candidates, 1),
            "coverage_estimate": self._estimate_coverage(),
        }

    def detect(self, point: list[float]) -> dict[str, Any]:
        """Check if a point is detected as Nonself (anomaly).

        Returns detection result with details.
        """
        if not self._detectors:
            return {"detected": False, "reason": "No detectors available"}

        matching_detectors = []
        for det in self._detectors:
            dist = self._euclidean(point, det["center"])
            if dist <= det["radius"]:
                matching_detectors.append(det)
                det["detections"] += 1

        detected = len(matching_detectors) > 0
        return {
            "detected": detected,
            "matching_detectors": len(matching_detectors),
            "total_detectors": len(self._detectors),
            "detector_ids": [d["id"] for d in matching_detectors[:5]],
            "confidence": min(1.0, len(matching_detectors) / max(len(self._detectors) * 0.01, 1)),
        }

    def _matches_self(self, center: list[float], radius: float) -> bool:
        """Check if a detector candidate overlaps with any Self point."""
        if self._self_set is None:
            return False
        if not hasattr(self._self_set, 'min_distance'):
            return False
        min_dist = self._self_set.min_distance(center)
        return min_dist <= radius + self._self_set.radius

    def _estimate_coverage(self) -> float:
        """Estimate Nonself coverage via Monte Carlo sampling."""
        if not self._detectors or self._feature_count == 0:
            return 0.0
        samples = 1000
        covered = 0
        for _ in range(samples):
            point = [self._rng.random() for _ in range(self._feature_count)]
            # Check if point is Self (exclude from Nonself)
            if self._self_set and hasattr(self._self_set, 'is_self') and self._self_set.is_self(point):
                continue
            # Check if any detector covers this Nonself point
            for det in self._detectors:
                if self._euclidean(point, det["center"]) <= det["radius"]:
                    covered += 1
                    break
        return covered / max(samples, 1)

    @staticmethod
    def _euclidean(a: list[float], b: list[float]) -> float:
        return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

    @property
    def detector_count(self) -> int:
        return len(self._detectors)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_detectors": len(self._detectors),
            "target_count": self._target_count,
            "target_coverage": self._target_coverage,
            "generation_count": self._generation_count,
            "acceptance_rate": self._accepted_count / max(self._total_candidates, 1),
            "coverage_estimate": self._estimate_coverage(),
            "feature_count": self._feature_count,
        }
