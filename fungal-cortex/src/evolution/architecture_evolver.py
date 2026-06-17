"""L3: Architecture Evolution — Synaptation-driven system-level restructuring.

Operates at the slowest timescale (weeks). This is the highest evolutionary tier
that restructures the system architecture itself.

Inspired by:
- Synaptation (Bielawski 2026): cross-level selection covariance between components
  with no shared genetics can still produce adaptive complex traits
- Major evolutionary transitions: new "individuality" levels emerge from
  lower-level component interactions
- Evolvability itself evolves: the system learns to learn better over time
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ArchitectureLayer(str, Enum):
    DATA = "data"  # L0-L1: data pipeline
    ANALYSIS = "analysis"  # L2: analysis layer
    STRATEGY = "strategy"  # L3-L4: strategy & debate
    EXECUTION = "execution"  # L5-L6: execution & cognition
    MONITORING = "monitoring"  # L7: monitoring & feedback


@dataclass
class ArchitectureGenome:
    """System architecture genome — evolvable structural properties."""

    layer_connections: dict[str, list[str]]  # layer → [connected_layers]
    pipeline_depth: int  # L0-L7 depth
    parallelism: int  # Number of parallel processing paths
    caching_layers: list[str]  # Layers with caching
    redundancy_level: float  # 0-1, duplicate paths for resilience
    generation: int = 0
    fitness: float = 0.0


@dataclass
class SynaptationEvent:
    """A cross-level selection covariance event.

    Synaptation: even without shared genetics, components can co-evolve
    through shared selection pressure. This is the core mechanism of
    major evolutionary transitions.
    """

    source_layer: ArchitectureLayer
    target_layer: ArchitectureLayer
    covariance_strength: float  # How strongly selection on source affects target
    adaptation_type: str  # "reinforcement", "compensation", "innovation"
    timestamp: float = field(default_factory=time.time)


class ArchitectureEvolver:
    """L3: System architecture evolution through Synaptation.

    Timescale: weekly evaluation.

    Detects cross-level selection covariance (Synaptation) and restructures
    the system architecture to better support emerging patterns of use.

    Key metrics:
    - Pipeline throughput (events/sec)
    - Cross-layer latency (ms)
    - Redundancy utilization (%)
    - Cognitive depth activation (%)
    """

    def __init__(
        self,
        mutation_rate: float = 0.05,
        seed: int | None = None,
    ) -> None:
        self._mutation_rate = mutation_rate
        self._genome = ArchitectureGenome(
            layer_connections={layer.value: [] for layer in ArchitectureLayer},
            pipeline_depth=8,
            parallelism=4,
            caching_layers=["data", "analysis"],
            redundancy_level=0.2,
        )
        self._generation = 0
        self._synaptation_log: list[SynaptationEvent] = []
        self._fitness_history: list[float] = []
        if seed is not None:
            random.seed(seed)

    def evaluate(
        self,
        throughput: float,
        latency_ms: float,
        error_rate: float,
        depth_utilization: float,
        redundancy_efficiency: float,
    ) -> float:
        """Evaluate current architecture fitness."""
        fitness = (
            0.30 * min(throughput / 10000.0, 1.0)
            + 0.25 * (1.0 - min(latency_ms / 5000.0, 1.0))
            + 0.20 * (1.0 - error_rate)
            + 0.15 * depth_utilization
            + 0.10 * redundancy_efficiency
        )
        self._genome.fitness = fitness
        self._fitness_history.append(fitness)
        if len(self._fitness_history) > 100:
            self._fitness_history = self._fitness_history[-100:]
        return fitness

    def detect_synaptation(
        self,
        layer_metrics: dict[ArchitectureLayer, dict[str, float]],
    ) -> list[SynaptationEvent]:
        """Detect cross-level selection covariance (Synaptation events).

        When selection pressure on one layer predicts changes in another,
        this is Synaptation — the basis for major evolutionary transitions.
        """
        events: list[SynaptationEvent] = []
        layers = list(ArchitectureLayer)

        for i in range(len(layers)):
            for j in range(i + 1, len(layers)):
                src = layers[i]
                tgt = layers[j]
                src_metrics = layer_metrics.get(src, {})
                tgt_metrics = layer_metrics.get(tgt, {})

                # Compute covariance between layers' activity levels
                src_activity = src_metrics.get("activity", 0.5)
                tgt_activity = tgt_metrics.get("activity", 0.5)

                covariance = abs(src_activity - tgt_activity)
                if covariance > 0.3:
                    adaptation = "reinforcement" if src_activity > tgt_activity else "compensation"
                    events.append(SynaptationEvent(
                        source_layer=src,
                        target_layer=tgt,
                        covariance_strength=covariance,
                        adaptation_type=adaptation,
                    ))

        self._synaptation_log.extend(events)
        return events

    def evolve(self, synaptation_events: list[SynaptationEvent]) -> ArchitectureGenome:
        """Evolve architecture based on detected Synaptation events."""
        self._generation += 1
        genome = self._genome
        genome.generation = self._generation

        for event in synaptation_events:
            src = event.source_layer.value
            tgt = event.target_layer.value

            if event.adaptation_type == "reinforcement":
                # Strengthen connection between co-varying layers
                if tgt not in genome.layer_connections.get(src, []):
                    genome.layer_connections.setdefault(src, []).append(tgt)

                # Increase parallelism for reinforced paths
                if random.random() < self._mutation_rate:
                    genome.parallelism = min(16, genome.parallelism + 1)

            elif event.adaptation_type == "compensation":
                # Add caching to compensate for lagging layer
                if tgt not in genome.caching_layers:
                    genome.caching_layers.append(tgt)

                # Increase redundancy
                if random.random() < self._mutation_rate:
                    genome.redundancy_level = min(0.8, genome.redundancy_level + 0.05)

            elif event.adaptation_type == "innovation":
                # New connection pattern emerges
                if random.random() < self._mutation_rate:
                    if len(genome.pipeline_depth) < 12:
                        genome.pipeline_depth = min(12, genome.pipeline_depth + 1)

        return genome

    @property
    def genome(self) -> ArchitectureGenome:
        return self._genome

    @property
    def stats(self) -> dict[str, Any]:
        recent_fitness = self._fitness_history[-10:] if self._fitness_history else [0.0]
        return {
            "generation": self._generation,
            "fitness": self._genome.fitness,
            "parallelism": self._genome.parallelism,
            "pipeline_depth": self._genome.pipeline_depth,
            "redundancy_level": self._genome.redundancy_level,
            "caching_layers": self._genome.caching_layers,
            "synaptation_events": len(self._synaptation_log),
            "fitness_trend": sum(recent_fitness) / len(recent_fitness),
        }
