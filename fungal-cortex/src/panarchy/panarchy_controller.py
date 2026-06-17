"""Panarchy Controller — manages nested adaptive cycles with cross-scale connections.

Four nested scale levels:
- Signal (minutes): fastest — market ticks, signals, alerts
- Strategy (days): strategies adapt to changing conditions
- Agent (weeks): agent lifecycle and specialization
- System (months): architecture and overall system health

Cross-scale connections:
- Revolt ↑: small fast perturbation → cascades up → triggers larger collapse
  (e.g., single strategy failure → agent drawdown → cluster crisis → system restructure)
- Remember ↓: large-scale memory → constrains smaller-scale recovery
  (e.g., system-level lessons → shape agent behavior → constrain strategy generation)

The controller monitors all scales and manages the Revolt/Remember dynamics
to maintain system resilience without suppressing necessary disturbance.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.panarchy.adaptive_cycle import AdaptiveCycle, CyclePhase


class ScaleLevel(str, Enum):
    SIGNAL = "signal"  # Minutes
    STRATEGY = "strategy"  # Days
    AGENT = "agent"  # Weeks
    SYSTEM = "system"  # Months


@dataclass
class CrossScaleSignal:
    """A signal that crosses between Panarchy scale levels."""

    direction: str  # "revolt" (upward cascade) or "remember" (downward constraint)
    from_scale: ScaleLevel
    to_scale: ScaleLevel
    intensity: float  # 0-1 signal strength
    trigger_event: str
    timestamp: float = field(default_factory=time.time)


class PanarchyController:
    """Controller for nested adaptive cycles with Revolt/Remember dynamics.

    Revolt: fast, small → triggers larger collapse.
      e.g., Signal failure → Strategy adjustment → Agent apoptosis → System restructure.

    Remember: large, slow → constrains recovery of smaller.
      e.g., System risk limits → Agent risk profiles → Strategy parameters → Signal thresholds.
    """

    def __init__(
        self,
        revolt_threshold: float = 0.5,
        remember_strength: float = 0.3,
        intermediate_disturbance: float = 0.15,
    ) -> None:
        self._revolt_t = revolt_threshold
        self._remember = remember_strength
        self._optimal_disturbance = intermediate_disturbance

        self._cycles: dict[ScaleLevel, AdaptiveCycle] = {
            ScaleLevel.SIGNAL: AdaptiveCycle("signal", r_duration=5, k_duration=15, omega_threshold=0.6),
            ScaleLevel.STRATEGY: AdaptiveCycle("strategy", r_duration=15, k_duration=45, omega_threshold=0.65),
            ScaleLevel.AGENT: AdaptiveCycle("agent", r_duration=30, k_duration=90, omega_threshold=0.7),
            ScaleLevel.SYSTEM: AdaptiveCycle("system", r_duration=60, k_duration=180, omega_threshold=0.75),
        }

        self._cross_scale_signals: list[CrossScaleSignal] = []
        self._revolt_cascades: list[dict[str, Any]] = []
        self._remember_constraints: dict[str, float] = {}

    def step_all(
        self,
        disturbances: dict[ScaleLevel, float] | None = None,
        innovation_rates: dict[ScaleLevel, float] | None = None,
    ) -> dict[ScaleLevel, Any]:
        """Step all four adaptive cycles and process cross-scale signals."""
        disturbances = disturbances or {}
        innovation_rates = innovation_rates or {}

        # Step each cycle
        states: dict[ScaleLevel, Any] = {}
        for scale in ScaleLevel:
            dist = disturbances.get(scale, 0.0)
            innov = innovation_rates.get(scale, 0.01)
            states[scale] = self._cycles[scale].step(dist, innov).__dict__

        # Process Revolt (upward cascade)
        self._process_revolt()

        # Process Remember (downward constraint)
        self._process_remember()

        return states

    def _process_revolt(self) -> None:
        """Check for Revolt cascades: small fast → triggers larger collapse.

        Revolt happens when a lower scale is in Ω (release) phase and
        the connectedness of the higher scale is high enough for cascade.
        """
        scales = [ScaleLevel.SIGNAL, ScaleLevel.STRATEGY, ScaleLevel.AGENT, ScaleLevel.SYSTEM]

        for i in range(len(scales) - 1):
            lower = scales[i]
            higher = scales[i + 1]
            lower_cycle = self._cycles[lower]
            higher_cycle = self._cycles[higher]

            if lower_cycle.phase == CyclePhase.OMEGA:
                cascade_prob = higher_cycle.stats["connectedness"] * self._revolt_t
                if cascade_prob > self._revolt_t:
                    signal = CrossScaleSignal(
                        direction="revolt",
                        from_scale=lower,
                        to_scale=higher,
                        intensity=cascade_prob,
                        trigger_event=f"{lower.value}_collapse_cascading_to_{higher.value}",
                    )
                    self._cross_scale_signals.append(signal)

                    # Apply revolt effect: push higher scale toward Ω
                    self._revolt_cascades.append({
                        "from": lower.value,
                        "to": higher.value,
                        "intensity": cascade_prob,
                        "timestamp": time.time(),
                    })

    def _process_remember(self) -> None:
        """Apply Remember constraints: higher scales constrain lower scale recovery.

        Remember happens when a higher scale is in K (conservation) phase —
        its accumulated memory constrains how lower scales can reorganize.
        """
        scales = [ScaleLevel.SIGNAL, ScaleLevel.STRATEGY, ScaleLevel.AGENT, ScaleLevel.SYSTEM]

        for i in range(len(scales) - 1, 0, -1):
            higher = scales[i]
            lower = scales[i - 1]
            higher_cycle = self._cycles[higher]

            if higher_cycle.phase in (CyclePhase.K, CyclePhase.ALPHA):
                constraint = higher_cycle.stats["connectedness"] * self._remember
                self._remember_constraints[f"{higher.value}→{lower.value}"] = constraint

                self._cross_scale_signals.append(CrossScaleSignal(
                    direction="remember",
                    from_scale=higher,
                    to_scale=lower,
                    intensity=constraint,
                    trigger_event=f"{higher.value}_constrains_{lower.value}_recovery",
                ))

    def apply_intermediate_disturbance(self) -> dict[ScaleLevel, float]:
        """Apply optimal intermediate disturbance to maximize diversity.

        Intermediate Disturbance Hypothesis: moderate disturbance maximizes
        diversity by preventing both K-phase rigidity and perpetual α chaos.
        """
        disturbances: dict[ScaleLevel, float] = {}
        for scale in ScaleLevel:
            cycle = self._cycles[scale]
            if cycle.phase == CyclePhase.K:
                disturbances[scale] = self._optimal_disturbance
            elif cycle.phase == CyclePhase.OMEGA:
                disturbances[scale] = self._optimal_disturbance * 0.3  # Less in Ω
            else:
                disturbances[scale] = self._optimal_disturbance * 0.5
        return disturbances

    def get_phase_coherence(self) -> float:
        """Measure how aligned the four scales are in their cycle phases.

        High coherence = all scales in sync → dangerously fragile.
        Low coherence = scales out of sync → more resilient.
        """
        phases = [c.phase for c in self._cycles.values()]
        unique = len(set(phases))
        return 1.0 - (unique - 1) / 3.0  # 1 if all same, 0 if all different

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "scale_phases": {s.value: c.phase.value for s, c in self._cycles.items()},
            "phase_coherence": self.get_phase_coherence(),
            "revolt_signals": len([s for s in self._cross_scale_signals if s.direction == "revolt"]),
            "remember_signals": len([s for s in self._cross_scale_signals if s.direction == "remember"]),
            "active_constraints": len(self._remember_constraints),
            "cascades": len(self._revolt_cascades),
            "optimal_disturbance": self._optimal_disturbance,
        }
