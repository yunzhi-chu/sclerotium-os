"""Clonal Selector — affinity maturation via clonal selection.

Inspired by B-cell clonal selection in the adaptive immune system:
- Successful detectors (high detection rate, low false positive) → proliferate (clone)
- Failed detectors (high false positive, low specificity) → apoptose (remove)
- Clones undergo hypermutation → explore variations around successful detectors
- Affinity maturation: each generation improves detection quality

This mirrors A/B testing adoption: winners proliferate, losers apoptose.
"""

from __future__ import annotations

import random
import time
from typing import Any


class ClonalSelector:
    """Clonal selection for detector evolution.

    Manages a population of detectors, selecting the best performers
    for cloning and variation. Poor performers are removed.
    """

    def __init__(self, clone_rate: float = 0.3, mutation_rate: float = 0.1, seed: int | None = None) -> None:
        self._clone_rate = clone_rate
        self._mutation_rate = mutation_rate
        self._rng = random.Random(seed)
        self._detectors: dict[str, dict[str, Any]] = {}
        self._generation = 0
        self._selection_history: list[dict[str, Any]] = []

    def add_detector(self, detector_id: str, params: dict[str, Any]) -> None:
        """Register a detector."""
        self._detectors[detector_id] = {
            "id": detector_id,
            "params": params,
            "fitness": 0.5,
            "true_positives": 0,
            "false_positives": 0,
            "generation": self._generation,
            "created_at": time.time(),
            "parent_id": None,
        }

    def record_detection(self, detector_id: str, correct: bool) -> None:
        """Record a detection result for fitness tracking."""
        det = self._detectors.get(detector_id)
        if det is None:
            return
        if correct:
            det["true_positives"] += 1
        else:
            det["false_positives"] += 1

        total = det["true_positives"] + det["false_positives"]
        precision = det["true_positives"] / max(total, 1)
        recall = det["true_positives"] / max(det["true_positives"] + 1, 1)
        det["fitness"] = 2 * precision * recall / max(precision + recall, 0.001)

    def select_and_clone(self) -> dict[str, Any]:
        """Run one generation of clonal selection.

        1. Rank detectors by fitness
        2. Top clone_rate fraction → clone + hypermutate
        3. Bottom clone_rate fraction → apoptose (remove)
        4. New clones fill the gap
        """
        self._generation += 1

        if not self._detectors:
            return {"generation": self._generation, "cloned": 0, "apoptosed": 0, "population": 0}

        detectors = list(self._detectors.values())
        detectors.sort(key=lambda d: d["fitness"], reverse=True)

        n = len(detectors)
        n_clone = max(1, int(n * self._clone_rate))
        n_apoptose = max(1, int(n * self._clone_rate * 0.5))

        # Top performers → clone
        cloned = 0
        for i in range(min(n_clone, n)):
            parent = detectors[i]
            clone_id = f"{parent['id']}-c{self._generation}"
            mutated_params = self._mutate(parent["params"])
            self._detectors[clone_id] = {
                "id": clone_id,
                "params": mutated_params,
                "fitness": parent["fitness"] * 0.9,
                "true_positives": 0,
                "false_positives": 0,
                "generation": self._generation,
                "created_at": time.time(),
                "parent_id": parent["id"],
            }
            cloned += 1

        # Bottom performers → apoptose
        apoptosed = 0
        for i in range(max(0, n - n_apoptose), n):
            det = detectors[i]
            if det["fitness"] < 0.3 and det.get("parent_id") is not None:
                self._detectors.pop(det["id"], None)
                apoptosed += 1

        result = {
            "generation": self._generation,
            "cloned": cloned,
            "apoptosed": apoptosed,
            "population": len(self._detectors),
            "avg_fitness": round(sum(d["fitness"] for d in self._detectors.values()) / max(len(self._detectors), 1), 4),
            "top_fitness": round(detectors[0]["fitness"], 4) if detectors else 0.0,
        }
        self._selection_history.append(result)
        return result

    def _mutate(self, params: dict[str, Any]) -> dict[str, Any]:
        """Hypermutate detector parameters (small random perturbation)."""
        mutated: dict[str, Any] = {}
        for key, value in params.items():
            if isinstance(value, (int, float)):
                noise = self._rng.gauss(0, self._mutation_rate)
                mutated[key] = value + noise if isinstance(value, float) else value + int(noise * 10)
                if isinstance(value, float):
                    mutated[key] = max(0.0, min(1.0, mutated[key]))
            elif isinstance(value, list):
                mutated[key] = [
                    v + self._rng.gauss(0, self._mutation_rate) if isinstance(v, (int, float)) else v
                    for v in value
                ]
            else:
                mutated[key] = value
        return mutated

    def top_detectors(self, n: int = 5) -> list[dict[str, Any]]:
        detectors = sorted(self._detectors.values(), key=lambda d: d["fitness"], reverse=True)
        return detectors[:n]

    @property
    def stats(self) -> dict[str, Any]:
        detectors = list(self._detectors.values())
        return {
            "population": len(detectors),
            "generation": self._generation,
            "avg_fitness": round(sum(d["fitness"] for d in detectors) / max(len(detectors), 1), 4),
            "total_true_positives": sum(d["true_positives"] for d in detectors),
            "total_false_positives": sum(d["false_positives"] for d in detectors),
            "clone_rate": self._clone_rate,
            "mutation_rate": self._mutation_rate,
        }
