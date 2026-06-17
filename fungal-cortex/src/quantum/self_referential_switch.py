"""Self-Referential Switch — DMN-inspired monitoring that controls quantum↔classical transition.

Inspired by 2026 Frontiers in Human Neuroscience:
- Default Mode Network (DMN) self-referential monitoring
- Modulates microtubule electromagnetic boundary conditions
- Controls System 1 (parallel/quantum) vs System 2 (sequential/classical) switching
- Self-referential processing IS the biological switch

The switch monitors:
1. Meta-confidence: not just "what is the answer" but "how sure am I about how sure I am"
2. Time pressure: deadline proximity → bias toward classical (faster)
3. Novelty: unfamiliar situation → bias toward quantum (broader exploration)
4. Resource budget: remaining compute/energy → constrain quantum states
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SwitchReason(str, Enum):
    CONFIDENCE_DROP = "confidence_drop"  # Confidence fell below threshold
    CONFIDENCE_RISE = "confidence_rise"  # Confidence rose above threshold
    TIME_PRESSURE = "time_pressure"  # Deadline forces collapse
    NOVELTY_DETECTED = "novelty_detected"  # New situation → explore
    RESOURCE_LOW = "resource_low"  # Low resources → classical (cheaper)
    RECURRENCE_DONE = "recurrence_done"  # Revisited possibility space


@dataclass
class SwitchEvent:
    from_mode: str
    to_mode: str
    reason: SwitchReason
    confidence_at_switch: float
    timestamp: float = field(default_factory=time.time)


class SelfReferentialSwitch:
    """DMN-inspired self-referential monitor for quantum↔classical switching.

    Like the brain's Default Mode Network, this continuously monitors:
    - System state (confidence, coherence, resource usage)
    - External conditions (time pressure, novelty, risk)
    - Meta-cognitive signals ("am I confident in my confidence?")

    When conditions change, it triggers a mode switch with a traceable reason.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        time_pressure_weight: float = 0.3,
        novelty_weight: float = 0.2,
        resource_weight: float = 0.15,
    ) -> None:
        self._threshold = confidence_threshold
        self._time_w = time_pressure_weight
        self._novelty_w = novelty_weight
        self._resource_w = resource_weight
        self._current_mode = "classical"
        self._switch_history: list[SwitchEvent] = []
        self._last_switch_time = time.time()
        self._cooldown_ms = 500.0  # Prevent rapid oscillation

    def monitor(
        self,
        confidence: float,
        time_pressure: float = 0.0,
        novelty: float = 0.0,
        resource_remaining: float = 1.0,
    ) -> SwitchEvent | None:
        """Monitor conditions and decide whether to switch modes.

        Args:
            confidence: Current confidence (0-1)
            time_pressure: 0=no pressure, 1=imminent deadline
            novelty: 0=familiar, 1=completely novel
            resource_remaining: 1=full, 0=depleted
        """
        now = time.time()
        if (now - self._last_switch_time) * 1000 < self._cooldown_ms:
            return None  # In cooldown period

        # Compute switching signals
        quantum_signal = (
            (1.0 - confidence)  # Low confidence → quantum
            + self._novelty_w * novelty  # Novel situations → explore
            + self._resource_w * resource_remaining  # Resources available → quantum OK
        )
        classical_signal = (
            confidence  # High confidence → classical
            + self._time_w * time_pressure  # Time pressure → execute
            + self._resource_w * (1.0 - resource_remaining)  # Low resources → classical
        )

        target_mode = "quantum" if quantum_signal > classical_signal else "classical"

        if target_mode != self._current_mode:
            reason = self._determine_reason(confidence, time_pressure, novelty, resource_remaining, target_mode)
            event = SwitchEvent(
                from_mode=self._current_mode,
                to_mode=target_mode,
                reason=reason,
                confidence_at_switch=confidence,
            )
            self._current_mode = target_mode
            self._switch_history.append(event)
            if len(self._switch_history) > 100:
                self._switch_history = self._switch_history[-100:]
            self._last_switch_time = now
            return event

        return None

    def _determine_reason(
        self,
        confidence: float,
        time_pressure: float,
        novelty: float,
        resource_remaining: float,
        target_mode: str,
    ) -> SwitchReason:
        """Determine the primary reason for the mode switch."""
        if time_pressure > 0.7:
            return SwitchReason.TIME_PRESSURE
        if novelty > 0.6:
            return SwitchReason.NOVELTY_DETECTED
        if resource_remaining < 0.3:
            return SwitchReason.RESOURCE_LOW
        if confidence < self._threshold and target_mode == "quantum":
            return SwitchReason.CONFIDENCE_DROP
        if confidence >= self._threshold and target_mode == "classical":
            return SwitchReason.CONFIDENCE_RISE
        return SwitchReason.RECURRENCE_DONE

    @property
    def current_mode(self) -> str:
        return self._current_mode

    @property
    def switch_history(self) -> list[SwitchEvent]:
        return list(self._switch_history)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "current_mode": self._current_mode,
            "total_switches": len(self._switch_history),
            "switch_frequency_hz": len(self._switch_history) / max(time.time() - self._switch_history[0].timestamp if self._switch_history else 1, 1),
            "recent_switches": [
                {"from": e.from_mode, "to": e.to_mode, "reason": e.reason.value}
                for e in self._switch_history[-5:]
            ],
        }
