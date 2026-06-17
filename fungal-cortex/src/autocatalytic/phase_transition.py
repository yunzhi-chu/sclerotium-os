"""Phase Transition Detection — autocatalytic phase change monitoring.

In sufficiently diverse chemical mixtures, autocatalytic sets emerge as a
first-order phase transition — analogous to the giant component emergence
in ER random graphs when p > 1/N.

For Fungal Cortex, the phase transition is:
- Below N_crit: Skills are individually invoked (passive mode)
- Above N_crit: The system enters autopoietic self-maintenance (active mode)
  - Skills catalyze each other spontaneously
  - New skills emerge without explicit instruction
  - The system "comes alive"

The transition is detected by monitoring:
1. Catalytic ring count in the skill catalysis graph
2. Constraint closure achievement
3. Emergence crystallization rate
4. Cross-domain catalytic edge density
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class TransitionState(Enum):
    """The phase state of the autocatalytic system."""

    PRE_CRITICAL = "pre_critical"  # Below N_crit: passive invocation
    CRITICAL = "critical"  # At N_crit: phase transition in progress
    SUPERCRITICAL = "supercritical"  # Above N_crit: autopoietic self-maintenance
    DEGENERATE = "degenerate"  # System reverted below critical threshold


@dataclass
class PhaseMetrics:
    """Metrics for phase transition detection."""

    catalytic_ring_count: int = 0
    constraint_closure_loops: int = 0
    emergence_rate: float = 0.0  # New crystallizations per hour
    cross_domain_edge_density: float = 0.0  # Edges between different skill domains
    skill_activation_rate: float = 0.0  # Fraction of skills active in last hour
    auto_generated_skills: int = 0  # Skills created without explicit instruction
    timestamp: float = field(default_factory=time.time)

    @property
    def is_critical(self) -> bool:
        """Quick check if the system appears near critical point."""
        return (
            self.catalytic_ring_count >= 5
            and self.constraint_closure_loops >= 1
            and self.emergence_rate > 0
        )


class PhaseTransition:
    """Monitors and detects the autocatalytic phase transition.

    The phase transition follows a percolation-like model:
    - As skill nodes increase, random catalytic edges connect them
    - At N_crit, a giant autocatalytic component emerges
    - The system transitions from "passive toolbox" to "active ecosystem"

    N_crit is estimated as: N_crit ≈ 1 / p_catalysis
    where p_catalysis = fraction of skill pairs that catalyze each other.
    """

    def __init__(self, n_crit: int = 10) -> None:
        self._n_crit = n_crit
        self._state = TransitionState.PRE_CRITICAL
        self._metrics_history: list[PhaseMetrics] = []
        self._transition_count = 0
        self._last_transition_time: float = 0.0
        self._logger = CortexLogger("phase_transition")

    def evaluate(
        self,
        catalytic_ring_count: int,
        constraint_closure_loops: int,
        emergence_rate: float,
        cross_domain_edge_density: float,
        skill_activation_rate: float = 0.0,
        auto_generated_skills: int = 0,
    ) -> TransitionState:
        """Evaluate the current phase state from system metrics.

        Transition criteria:
        - PRE_CRITICAL → CRITICAL: ring_count >= N_crit/2
        - CRITICAL → SUPERCRITICAL: ring_count >= N_crit AND closure_loops >= 1
        - SUPERCRITICAL → DEGENERATE: ring_count < N_crit/2
        - DEGENERATE → PRE_CRITICAL: sustained low metrics
        """
        metrics = PhaseMetrics(
            catalytic_ring_count=catalytic_ring_count,
            constraint_closure_loops=constraint_closure_loops,
            emergence_rate=emergence_rate,
            cross_domain_edge_density=cross_domain_edge_density,
            skill_activation_rate=skill_activation_rate,
            auto_generated_skills=auto_generated_skills,
        )
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > 200:
            self._metrics_history = self._metrics_history[-200:]

        previous_state = self._state

        if self._state == TransitionState.PRE_CRITICAL:
            if catalytic_ring_count >= self._n_crit / 2:
                self._state = TransitionState.CRITICAL
        elif self._state == TransitionState.CRITICAL:
            if catalytic_ring_count >= self._n_crit and constraint_closure_loops >= 1:
                self._state = TransitionState.SUPERCRITICAL
            elif catalytic_ring_count < self._n_crit / 2:
                self._state = TransitionState.PRE_CRITICAL
        elif self._state == TransitionState.SUPERCRITICAL:
            if catalytic_ring_count < self._n_crit / 2 and constraint_closure_loops == 0:
                self._state = TransitionState.DEGENERATE
        elif self._state == TransitionState.DEGENERATE:
            if catalytic_ring_count >= self._n_crit / 2:
                self._state = TransitionState.CRITICAL

        if self._state != previous_state:
            self._transition_count += 1
            self._last_transition_time = time.time()
            self._logger.info("phase_transition", from_state=previous_state.value, to_state=self._state.value)

        return self._state

    def distance_to_critical(self, catalytic_ring_count: int) -> float:
        """How far are we from the critical threshold? (0=at threshold, 1=far)"""
        if catalytic_ring_count >= self._n_crit:
            return 0.0
        return 1.0 - (catalytic_ring_count / self._n_crit)

    def is_autopoietic(self) -> bool:
        """Is the system in autopoietic self-maintenance mode?"""
        return self._state == TransitionState.SUPERCRITICAL

    @property
    def state(self) -> TransitionState:
        return self._state

    @property
    def n_crit(self) -> int:
        return self._n_crit

    @property
    def stats(self) -> dict[str, Any]:
        latest = self._metrics_history[-1] if self._metrics_history else PhaseMetrics()
        return {
            "state": self._state.value,
            "n_crit": self._n_crit,
            "distance_to_critical": self.distance_to_critical(latest.catalytic_ring_count),
            "transition_count": self._transition_count,
            "is_autopoietic": self.is_autopoietic(),
            "latest_metrics": {
                "catalytic_rings": latest.catalytic_ring_count,
                "closure_loops": latest.constraint_closure_loops,
                "emergence_rate": round(latest.emergence_rate, 4),
                "cross_domain_density": round(latest.cross_domain_edge_density, 3),
            },
        }
