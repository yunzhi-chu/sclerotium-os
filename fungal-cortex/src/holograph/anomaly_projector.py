"""Anomaly Projector — detect anomalies from interference pattern distortions.

Inspired by holographic anomaly detection: when the interference pattern
deviates from its expected multi-fractal spectrum, we can "project" the
distortion back to locate the anomalous subsystem.

Algorithm:
1. Maintain a baseline interference pattern (healthy state)
2. Compare current pattern against baseline (spectral distance)
3. When deviation > sigma threshold → anomaly detected
4. Project deviation back to specific frequency bands → pinpoint source
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.holograph.fractal_encoder import InterferencePattern


@dataclass
class AnomalyProjection:
    """Result of projecting an anomaly back to its source."""

    detected: bool
    anomaly_score: float
    affected_bands: list[int]
    band_deviations: list[float]
    likely_source: str  # Which subsystem is likely affected
    confidence: float
    timestamp: float = field(default_factory=time.time)


class AnomalyProjector:
    """Detect anomalies by comparing current vs baseline interference patterns.

    The baseline is a rolling exponential moving average of interference patterns.
    Anomalies are detected when spectral distance exceeds sigma * std_deviation.
    """

    def __init__(self, sigma_threshold: float = 3.0, window_size: int = 100) -> None:
        self._sigma = sigma_threshold
        self._window = window_size
        self._baseline_amplitudes: list[float] = []
        self._baseline_phases: list[float] = []
        self._baseline_coherence: float = 0.0
        self._deviation_history: list[float] = []
        self._pattern_count = 0
        self._alpha = 0.1  # EMA smoothing factor

    def update_baseline(self, pattern: InterferencePattern) -> None:
        """Update the baseline with a new pattern (EMA)."""
        if not pattern.amplitudes:
            return

        if not self._baseline_amplitudes:
            self._baseline_amplitudes = list(pattern.amplitudes)
            self._baseline_phases = list(pattern.phase_angles)
            self._baseline_coherence = pattern.coherence
        else:
            alpha = self._alpha
            for i in range(len(pattern.amplitudes)):
                if i < len(self._baseline_amplitudes):
                    self._baseline_amplitudes[i] = (
                        alpha * pattern.amplitudes[i] + (1.0 - alpha) * self._baseline_amplitudes[i]
                    )
                if i < len(self._baseline_phases):
                    self._baseline_phases[i] = (
                        alpha * pattern.phase_angles[i] + (1.0 - alpha) * self._baseline_phases[i]
                    )
            self._baseline_coherence = alpha * pattern.coherence + (1.0 - alpha) * self._baseline_coherence

        self._pattern_count += 1

    def project(self, current: InterferencePattern) -> AnomalyProjection:
        """Compare current pattern against baseline and project anomalies."""
        if not self._baseline_amplitudes or not current.amplitudes:
            return AnomalyProjection(
                detected=False,
                anomaly_score=0.0,
                affected_bands=[],
                band_deviations=[],
                likely_source="unknown",
                confidence=0.0,
            )

        n = min(len(current.amplitudes), len(self._baseline_amplitudes))
        band_deviations: list[float] = []
        total_deviation = 0.0

        for i in range(n):
            amp_dev = abs(current.amplitudes[i] - self._baseline_amplitudes[i])
            phase_dev = abs(current.phase_angles[i] - self._baseline_phases[i])
            combined = math.sqrt(amp_dev ** 2 + phase_dev ** 2)
            band_deviations.append(combined)
            total_deviation += combined

        mean_deviation = total_deviation / n

        # Track deviation history for sigma calculation
        self._deviation_history.append(mean_deviation)
        if len(self._deviation_history) > self._window:
            self._deviation_history = self._deviation_history[-self._window:]

        mean_hist = sum(self._deviation_history) / len(self._deviation_history)
        var_hist = sum((d - mean_hist) ** 2 for d in self._deviation_history) / len(self._deviation_history)
        std_hist = math.sqrt(var_hist) if var_hist > 1e-10 else 1e-10

        anomaly_score = mean_deviation / std_hist
        detected = anomaly_score >= self._sigma

        # Find most affected bands
        affected = sorted(
            range(len(band_deviations)),
            key=lambda i: band_deviations[i],
            reverse=True,
        )[:3]

        # Map affected bands to likely source
        band_to_source = {
            0: "system_health",
            1: "agent_network",
            2: "strategy_engine",
            3: "risk_system",
            4: "data_pipeline",
            5: "cognitive_scheduler",
            6: "emergence_detector",
            7: "market_regime_detector",
        }
        likely_source = band_to_source.get(affected[0], "unknown") if affected else "unknown"

        confidence = min(1.0, anomaly_score / (self._sigma * 2.0)) if detected else 0.0

        return AnomalyProjection(
            detected=detected,
            anomaly_score=anomaly_score,
            affected_bands=affected,
            band_deviations=band_deviations,
            likely_source=likely_source,
            confidence=confidence,
        )

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "pattern_count": self._pattern_count,
            "sigma_threshold": self._sigma,
            "baseline_coherence": self._baseline_coherence,
            "mean_deviation": sum(self._deviation_history) / max(len(self._deviation_history), 1) if self._deviation_history else 0.0,
            "window_size": self._window,
        }
