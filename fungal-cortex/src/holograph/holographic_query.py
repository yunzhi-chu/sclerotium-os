"""Holographic Query — read system state from frequency bands of interference patterns.

Inspired by holographic memory: querying the system isn't reading a log file,
it's reading specific frequency bands of the interference pattern.
Each band encodes a different aspect of system state:
- Band 0 (base): overall health
- Band 1: agent activity
- Band 2: strategy performance
- Band 3: risk levels
- Band 4: data flow
- Band 5: cognitive depth
- Band 6: emergence activity
- Band 7: market regime
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.holograph.fractal_encoder import InterferencePattern


class FrequencyBand(str, Enum):
    BASE = "base"  # 0: Overall system health
    AGENT_ACTIVITY = "agent_activity"  # 1: Agent deployments
    STRATEGY_PERF = "strategy_performance"  # 2: Strategy metrics
    RISK_LEVEL = "risk_level"  # 3: Risk indicators
    DATA_FLOW = "data_flow"  # 4: Pipeline throughput
    COGNITIVE_DEPTH = "cognitive_depth"  # 5: L1-L6 depth
    EMERGENCE = "emergence"  # 6: Emergence events
    MARKET_REGIME = "market_regime"  # 7: Market state


BAND_TO_INDEX: dict[FrequencyBand, int] = {
    FrequencyBand.BASE: 0,
    FrequencyBand.AGENT_ACTIVITY: 1,
    FrequencyBand.STRATEGY_PERF: 2,
    FrequencyBand.RISK_LEVEL: 3,
    FrequencyBand.DATA_FLOW: 4,
    FrequencyBand.COGNITIVE_DEPTH: 5,
    FrequencyBand.EMERGENCE: 6,
    FrequencyBand.MARKET_REGIME: 7,
}


@dataclass
class BandReading:
    band: FrequencyBand
    frequency: float
    amplitude: float
    phase: float
    coherence_contribution: float


class HolographicQuery:
    """Query system state from holographic interference patterns.

    Instead of reading raw logs, we query frequency bands of the interference
    pattern — each band represents a different functional domain.
    Like a hologram, any single band contains information about the whole.
    """

    def __init__(self, pattern: InterferencePattern | None = None) -> None:
        self._pattern = pattern

    def set_pattern(self, pattern: InterferencePattern) -> None:
        self._pattern = pattern

    def read_band(self, band: FrequencyBand) -> BandReading:
        """Read a specific frequency band from the interference pattern."""
        if self._pattern is None or not self._pattern.frequency_bands:
            return BandReading(
                band=band,
                frequency=0.0,
                amplitude=0.0,
                phase=0.0,
                coherence_contribution=0.0,
            )

        idx = BAND_TO_INDEX.get(band, 0)
        n_bands = len(self._pattern.frequency_bands)
        if idx >= n_bands:
            idx = n_bands - 1

        amplitude = self._pattern.amplitudes[idx]
        frequency = self._pattern.frequency_bands[idx]
        phase = self._pattern.phase_angles[idx]

        coherence_contribution = amplitude * (1.0 - abs(phase - 0.5) * 2.0)

        return BandReading(
            band=band,
            frequency=frequency,
            amplitude=amplitude,
            phase=phase,
            coherence_contribution=coherence_contribution,
        )

    def read_all_bands(self) -> list[BandReading]:
        """Read all frequency bands at once."""
        return [self.read_band(band) for band in FrequencyBand]

    def read_composite_health(self) -> float:
        """Compute overall system health from interference pattern coherence."""
        if self._pattern is None:
            return 0.0

        readings = self.read_all_bands()
        if not readings:
            return 0.0

        total_contribution = sum(r.coherence_contribution for r in readings)
        health = total_contribution / len(readings) * self._pattern.coherence
        return min(1.0, max(0.0, health))

    def read_domain_state(self, domain: str) -> dict[str, Any]:
        """Query a specific domain across all relevant bands."""
        domain_band_map = {
            "trading": [FrequencyBand.STRATEGY_PERF, FrequencyBand.RISK_LEVEL, FrequencyBand.MARKET_REGIME],
            "pipeline": [FrequencyBand.DATA_FLOW, FrequencyBand.COGNITIVE_DEPTH],
            "agents": [FrequencyBand.AGENT_ACTIVITY, FrequencyBand.EMERGENCE],
            "system": [FrequencyBand.BASE],
        }

        bands = domain_band_map.get(domain, [FrequencyBand.BASE])
        readings = [self.read_band(b) for b in bands]
        avg_amplitude = sum(r.amplitude for r in readings) / max(len(readings), 1)
        avg_coherence = sum(r.coherence_contribution for r in readings) / max(len(readings), 1)

        return {
            "domain": domain,
            "bands_read": len(readings),
            "amplitude_mean": avg_amplitude,
            "coherence_mean": avg_coherence,
            "healthy": avg_coherence > 0.5,
        }
