"""Coincidence Detector — NMDA receptor-based temporal coincidence detection.

Inspired by 2026 findings:
- Pre-synaptic NMDAR → tLTD (depression, post-before-pre, Δt ≈ -25ms)
- Post-synaptic NMDAR → tLTP (potentiation, pre-before-post, Δt ≈ +10ms)
- Pre and post NMDARs are TWO INDEPENDENT coincidence detectors
- bAP probability gate limits the coincidence window stochastically
- Spine neck resistance (R_neck) tunes the temporal precision of coincidence

The coincidence window Δt determines what "simultaneous" means.
Two signals within Δt → supralinear Ca²⁺ spike (burst encoding).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CoincidenceEvent:
    """Result of a coincidence detection."""

    detected: bool
    signal_a: str
    signal_b: str
    delta_t_ms: float
    pre_synaptic_contribution: float  # tLTD pathway
    post_synaptic_contribution: float  # tLTP pathway
    combined_potentiation: float  # Net plasticity
    bap_gate_open: bool


@dataclass
class NMDASynapse:
    """A single NMDA receptor synapse — independent coincidence detector."""

    synapse_id: str
    pre_synaptic: bool = True  # True=pre-NMDAR (tLTD), False=post-NMDAR (tLTP)
    weight: float = 1.0
    mg_block: float = 0.0  # Mg²⁺ block level (voltage-dependent)


class CoincidenceDetector:
    """NMDA-based coincidence detector for multi-source signal alignment.

    Detection rule:
    1. Two signals must arrive within coincidence_window_ms
    2. Pre-post ordering matters: pre-before-post → LTP, post-before-pre → LTD
    3. bAP probability gate stochastically allows coincidence detection
    4. Combined signal = supralinear integration (strength^exponent)
    """

    def __init__(
        self,
        coincidence_window_ms: float = 25.0,
        supralinear_exponent: float = 1.5,
        bap_probability: float = 0.3,
        seed: int | None = None,
    ) -> None:
        self._window_ms = coincidence_window_ms
        self._exponent = supralinear_exponent
        self._bap_prob = bap_probability
        self._synapses: dict[str, NMDASynapse] = {}
        self._detection_history: list[CoincidenceEvent] = []
        if seed is not None:
            random.seed(seed)

    def add_synapse(self, synapse_id: str, pre_synaptic: bool = True, initial_weight: float = 1.0) -> NMDASynapse:
        synapse = NMDASynapse(synapse_id=synapse_id, pre_synaptic=pre_synaptic, weight=initial_weight)
        self._synapses[synapse_id] = synapse
        return synapse

    def detect(
        self,
        signal_a: str,
        time_a_ms: float,
        signal_b: str,
        time_b_ms: float,
        strength_a: float = 1.0,
        strength_b: float = 1.0,
    ) -> CoincidenceEvent:
        """Detect if two signals are coincident within the temporal window.

        Args:
            signal_a, signal_b: Signal identifiers
            time_a_ms, time_b_ms: Arrival times in milliseconds
            strength_a, strength_b: Signal strengths
        """
        delta_t = abs(time_a_ms - time_b_ms)
        detected = delta_t <= self._window_ms

        # bAP probability gate: stochastic opening of coincidence window
        bap_gate = random.random() < self._bap_prob

        if not detected or not bap_gate:
            return CoincidenceEvent(
                detected=False,
                signal_a=signal_a,
                signal_b=signal_b,
                delta_t_ms=delta_t,
                pre_synaptic_contribution=0.0,
                post_synaptic_contribution=0.0,
                combined_potentiation=0.0,
                bap_gate_open=bap_gate,
            )

        # Pre/post synaptic separation:
        # Pre-before-post (t_a < t_b) → post-synaptic NMDAR → LTP
        # Post-before-pre (t_b < t_a) → pre-synaptic NMDAR → LTD
        time_order = time_b_ms - time_a_ms  # Positive = pre-before-post

        # Temporal kernel: Gaussian around optimal Δt
        pre_contrib = math.exp(-((time_order + 25.0) ** 2) / (2.0 * 15.0 ** 2))
        post_contrib = math.exp(-((time_order - 10.0) ** 2) / (2.0 * 10.0 ** 2))

        # Combined: supralinear integration of signal strengths
        combined_strength = (strength_a + strength_b) ** self._exponent
        combined = combined_strength * (post_contrib - pre_contrib * 0.5)

        event = CoincidenceEvent(
            detected=True,
            signal_a=signal_a,
            signal_b=signal_b,
            delta_t_ms=delta_t,
            pre_synaptic_contribution=pre_contrib * combined_strength,
            post_synaptic_contribution=post_contrib * combined_strength,
            combined_potentiation=combined,
            bap_gate_open=True,
        )

        self._detection_history.append(event)
        if len(self._detection_history) > 100:
            self._detection_history = self._detection_history[-100:]

        return event

    def detect_multi(self, signals: list[tuple[str, float, float]]) -> list[CoincidenceEvent]:
        """Detect coincidences among multiple signals.

        Each signal: (id, time_ms, strength)
        """
        events: list[CoincidenceEvent] = []
        for i in range(len(signals)):
            for j in range(i + 1, len(signals)):
                event = self.detect(
                    signals[i][0], signals[i][1],
                    signals[j][0], signals[j][1],
                    signals[i][2], signals[j][2],
                )
                if event.detected:
                    events.append(event)
        return events

    @property
    def stats(self) -> dict[str, Any]:
        total = len(self._detection_history)
        detected = sum(1 for e in self._detection_history if e.detected)
        return {
            "window_ms": self._window_ms,
            "bap_probability": self._bap_prob,
            "synapses": len(self._synapses),
            "detection_rate": detected / max(total, 1),
            "total_checks": total,
        }
