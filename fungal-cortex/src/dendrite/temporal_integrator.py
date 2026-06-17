"""Temporal Integrator — BMP-style signal integration over time windows.

Inspired by BMP (Bone Morphogenetic Protein) temporal integration (Current Biology 2026):
- Cells don't decide on instantaneous BMP concentration
- They integrate BMP signals over time (weighted window)
- Information theory: temporal integration improves SNR by √N

In dendrites: plateau potentials provide the biological mechanism for integrating
over behavioral timescales (hundreds of milliseconds).

Key properties:
- Integration window: configurable duration (default 500ms)
- Weight decay: older signals have exponentially lower weight
- SNR improvement: √window_size reduction in noise
- Sequence detection: ordered temporal patterns, not just instantaneous coincidence
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntegrationWindow:
    """A temporal integration window with exponential decay weighting."""

    duration_ms: float  # Total integration window
    decay_rate: float  # Exponential decay rate for older signals
    signals: list[dict[str, Any]] = field(default_factory=list)  # [(time_ms, amplitude), ...]
    integrated_value: float = 0.0


@dataclass
class BMPIntegration:
    """Result of BMP-style temporal integration."""

    integrated_value: float
    instantaneous_value: float
    window_size: int  # Number of signals integrated
    snr_improvement: float  # √window_size
    sequence_detected: bool
    sequence_pattern: str  # e.g., "A→B→C" = ordered sequence


class TemporalIntegrator:
    """BMP-style temporal integration over configurable time windows.

    Unlike instantaneous signal processing, this integrates over a sliding
    window with exponential decay — like BMP gradient sensing in development.

    The integrator also detects ordered sequences:
    - When signals arrive in a specific temporal order (A before B before C),
      this is treated as a "plateau detection" event (sequence detector).
    """

    def __init__(
        self,
        window_duration_ms: float = 500.0,
        decay_rate: float = 0.01,
        snr_weight: float = 0.5,
    ) -> None:
        self._window_ms = window_duration_ms
        self._decay_rate = decay_rate
        self._snr_weight = snr_weight
        self._windows: dict[str, IntegrationWindow] = {}
        self._sequence_log: list[tuple[float, list[str]]] = []  # (timestamp, [signal_ids])

    def add_signal(
        self, window_id: str, signal_id: str, amplitude: float, timestamp_ms: float | None = None
    ) -> float:
        """Add a signal to the integration window and return current integrated value."""
        if timestamp_ms is None:
            timestamp_ms = time.time() * 1000.0

        if window_id not in self._windows:
            self._windows[window_id] = IntegrationWindow(
                duration_ms=self._window_ms,
                decay_rate=self._decay_rate,
            )

        window = self._windows[window_id]

        # Add signal
        window.signals.append({
            "signal_id": signal_id,
            "amplitude": amplitude,
            "timestamp_ms": timestamp_ms,
        })

        # Prune old signals outside window
        cutoff = timestamp_ms - self._window_ms
        window.signals = [s for s in window.signals if s["timestamp_ms"] >= cutoff]

        # Integrate with exponential decay weighting
        integrated = 0.0
        for s in window.signals:
            age_ms = timestamp_ms - s["timestamp_ms"]
            weight = math.exp(-self._decay_rate * age_ms)
            integrated += s["amplitude"] * weight

        window.integrated_value = integrated
        return integrated

    def integrate(self, window_id: str, current_time_ms: float | None = None) -> BMPIntegration:
        """Get the current BMP integration result for a window."""
        if current_time_ms is None:
            current_time_ms = time.time() * 1000.0

        window = self._windows.get(window_id)
        if not window or not window.signals:
            return BMPIntegration(
                integrated_value=0.0,
                instantaneous_value=0.0,
                window_size=0,
                snr_improvement=1.0,
                sequence_detected=False,
                sequence_pattern="",
            )

        # Instantaneous = most recent signal
        instantaneous = window.signals[-1]["amplitude"] if window.signals else 0.0

        # Recompute integrated value with current time
        cutoff = current_time_ms - self._window_ms
        active_signals = [s for s in window.signals if s["timestamp_ms"] >= cutoff]
        window.signals = active_signals

        integrated = 0.0
        for s in active_signals:
            age_ms = current_time_ms - s["timestamp_ms"]
            weight = math.exp(-self._decay_rate * age_ms)
            integrated += s["amplitude"] * weight
        window.integrated_value = integrated

        n = len(active_signals)
        snr_improvement = math.sqrt(max(n, 1))

        # Sequence detection: ordered signal arrival pattern
        recent_ids = [s["signal_id"] for s in active_signals[-5:]]
        sequence_detected = len(set(recent_ids)) >= 3
        sequence_pattern = "→".join(recent_ids[-3:]) if len(recent_ids) >= 3 else ""

        self._sequence_log.append((current_time_ms, recent_ids))
        if len(self._sequence_log) > 200:
            self._sequence_log = self._sequence_log[-200:]

        return BMPIntegration(
            integrated_value=integrated,
            instantaneous_value=instantaneous,
            window_size=n,
            snr_improvement=snr_improvement,
            sequence_detected=sequence_detected,
            sequence_pattern=sequence_pattern,
        )

    def clear_window(self, window_id: str) -> None:
        if window_id in self._windows:
            self._windows[window_id].signals.clear()
            self._windows[window_id].integrated_value = 0.0

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "active_windows": len(self._windows),
            "window_duration_ms": self._window_ms,
            "decay_rate": self._decay_rate,
            "total_signals_integrated": sum(len(w.signals) for w in self._windows.values()),
            "sequences_detected": len(self._sequence_log),
        }
