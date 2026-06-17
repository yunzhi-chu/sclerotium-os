"""Adaptive Cycle — r → K → Ω → α phase transitions.

The fundamental unit of Panarchy theory. Every complex adaptive system
cycles through four phases:

r (Exploitation/Growth): Rapid growth, low connectedness, high resilience.
  Agents proliferate, strategies multiply, resources are abundant.
K (Conservation): Slow accumulation, high connectedness, low resilience.
  System becomes rigid, interconnected, and efficient — but fragile.
Ω (Release/Collapse): Sudden breakdown, connectedness plummets.
  A small trigger can cascade through the hyper-connected system.
α (Reorganization): Renewal, high potential for novelty.
  Resources released from Ω become available for new configurations.

Key metrics that drive phase transitions:
- Potential: accumulated capital (wealth, strategies, agents)
- Connectedness: interdependency between components
- Resilience: capacity to absorb disturbance while maintaining function
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CyclePhase(str, Enum):
    R = "r"  # Exploitation / Growth
    K = "k"  # Conservation
    OMEGA = "omega"  # Release / Collapse
    ALPHA = "alpha"  # Reorganization / Renewal


@dataclass
class CycleState:
    """Current state within the adaptive cycle."""

    phase: CyclePhase
    potential: float  # 0-1: accumulated resources/capital
    connectedness: float  # 0-1: interdependency between components
    resilience: float  # 0-1: capacity to absorb disturbance
    phase_duration: float  # Time spent in current phase
    transition_probability: float  # Probability of phase transition
    timestamp: float = field(default_factory=time.time)


class AdaptiveCycle:
    """A single adaptive cycle at one scale level.

    The cycle advances naturally through r→K→Ω→α driven by the
    accumulation of potential and connectedness.
    """

    def __init__(
        self,
        scale_name: str,
        r_duration: float = 30.0,
        k_duration: float = 90.0,
        omega_threshold: float = 0.7,
        seed: int | None = None,
    ) -> None:
        self._name = scale_name
        self._r_duration = r_duration
        self._k_duration = k_duration
        self._omega_t = omega_threshold

        self._potential = 0.1  # Start low in r phase
        self._connectedness = 0.1
        self._resilience = 0.9  # High resilience early
        self._phase = CyclePhase.R
        self._phase_start = time.time()
        self._phase_history: list[CycleState] = []
        self._cycle_count = 0

        import random
        self._rng = random.Random(seed)

    def step(
        self,
        external_disturbance: float = 0.0,
        innovation_rate: float = 0.01,
    ) -> CycleState:
        """Advance the adaptive cycle by one timestep.

        Args:
            external_disturbance: 0-1 external shock level
            innovation_rate: rate of novel solutions emerging
        """
        phase_dur = time.time() - self._phase_start
        transition = False

        if self._phase == CyclePhase.R:
            # Growth: accumulate potential, low connectedness growth
            self._potential = min(1.0, self._potential + 0.02 * (1.0 - self._potential))
            self._connectedness = min(1.0, self._connectedness + 0.005)
            self._resilience = max(0.1, self._resilience - 0.002)  # Slowly erodes

            # Transition to K when potential and connectedness reach threshold
            if self._potential > 0.6 and self._connectedness > 0.4:
                transition = True

        elif self._phase == CyclePhase.K:
            # Conservation: high potential, high connectedness, very fragile
            self._potential = min(1.0, self._potential + 0.005)
            self._connectedness = min(1.0, self._connectedness + 0.01)
            self._resilience = max(0.0, self._resilience - 0.005)  # Rigidity trap

            # Ω trigger: disturbance or internal fragility
            fragility = self._connectedness * (1.0 - self._resilience)
            if fragility > self._omega_t or external_disturbance > 0.5:
                transition = True

        elif self._phase == CyclePhase.OMEGA:
            # Release: rapid breakdown, connectedness plummets
            self._potential = max(0.05, self._potential - 0.1)
            self._connectedness = max(0.05, self._connectedness - 0.08)
            self._resilience = min(1.0, self._resilience + 0.02)  # Resilience returns

            # Transition to α when connectedness drops enough
            if self._connectedness < 0.2:
                transition = True

        elif self._phase == CyclePhase.ALPHA:
            # Reorganization: high potential for novelty, low connectedness
            self._potential = self._potential + innovation_rate * (1.0 - self._potential)
            self._connectedness = min(1.0, self._connectedness + 0.01)
            self._resilience = max(0.3, self._resilience - 0.003)

            # Transition to r when reorganized enough
            if self._connectedness > 0.2 and self._potential > 0.2:
                transition = True
                self._cycle_count += 1

        if transition:
            self._advance_phase()

        state = CycleState(
            phase=self._phase,
            potential=self._potential,
            connectedness=self._connectedness,
            resilience=self._resilience,
            phase_duration=phase_dur,
            transition_probability=self._compute_transition_probability(external_disturbance),
        )
        self._phase_history.append(state)
        if len(self._phase_history) > 1000:
            self._phase_history = self._phase_history[-1000:]
        return state

    def _advance_phase(self) -> None:
        phases = [CyclePhase.R, CyclePhase.K, CyclePhase.OMEGA, CyclePhase.ALPHA]
        idx = phases.index(self._phase)
        self._phase = phases[(idx + 1) % len(phases)]
        self._phase_start = time.time()

    def _compute_transition_probability(self, disturbance: float) -> float:
        if self._phase == CyclePhase.K:
            fragility = self._connectedness * (1.0 - self._resilience)
            return min(1.0, fragility + disturbance)
        if self._phase == CyclePhase.OMEGA:
            return max(0.0, 1.0 - self._connectedness * 3.0)
        return 0.3

    @property
    def phase(self) -> CyclePhase:
        return self._phase

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "phase": self._phase.value,
            "potential": self._potential,
            "connectedness": self._connectedness,
            "resilience": self._resilience,
            "cycle_count": self._cycle_count,
            "phase_duration": time.time() - self._phase_start,
        }
