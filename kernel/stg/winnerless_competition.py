"""STG Winnerless Competition — ordered state transitions.

In the lobster STG, WLC dynamics produce sequential firing patterns
where neurons take turns being active without a single "winner." This
maps to Panarchy adaptive cycles and ordered state transitions.

Panarchy phases mapped to WLC states:
  r (growth)        → high exploration, low connectedness
  K (conservation)  → high connectedness, high efficiency
  Ω (creative destruction) → collapse, purge, reset
  α (reorganization)→ low connectedness, novelty injection

Reference: Lin & Liu (2020/2025), "Circuit dynamics in lobster STG
based on winnerless competition network."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PanarchyPhase(Enum):
    R = "r"           # Growth / exploitation
    K = "K"           # Conservation
    OMEGA = "OMEGA"   # Creative destruction / release
    ALPHA = "ALPHA"   # Reorganization


@dataclass
class WLCState:
    """Single WLC node state — one Panarchy phase."""
    phase: PanarchyPhase
    activity: float = 0.0         # [0, 1] current activation
    threshold: float = 0.5        # activation threshold
    inhibition: float = 0.0       # received inhibition from other nodes
    duration: float = 0.0         # time spent in this phase


class WinnerlessCompetition:
    """WLC-driven Panarchy state machine.

    Four nodes (r, K, ω, α) mutually inhibit each other. When one
    node's activity drops below threshold, the next in sequence
    activates — producing ordered cyclic transitions without
    any single "winner."
    """

    def __init__(self) -> None:
        self._states: dict[PanarchyPhase, WLCState] = {
            PanarchyPhase.R: WLCState(phase=PanarchyPhase.R),
            PanarchyPhase.K: WLCState(phase=PanarchyPhase.K),
            PanarchyPhase.OMEGA: WLCState(phase=PanarchyPhase.OMEGA),
            PanarchyPhase.ALPHA: WLCState(phase=PanarchyPhase.ALPHA),
        }
        self._current: PanarchyPhase = PanarchyPhase.R
        self._states[self._current].activity = 0.8
        self._history: list[tuple[str, float]] = []  # (phase, timestamp)

    # ── State machine ─────────────────────────────────────────────────

    @property
    def current_phase(self) -> PanarchyPhase:
        return self._current

    @property
    def connectedness(self) -> float:
        """Connectedness rises during r→K, drops during Ω→α."""
        state = self._states[self._current]
        if self._current == PanarchyPhase.R:
            return 0.3 + state.duration * 0.01  # rising
        elif self._current == PanarchyPhase.K:
            return 0.7 + state.duration * 0.005  # high
        elif self._current == PanarchyPhase.OMEGA:
            return 0.8 - state.duration * 0.05  # crashing
        else:
            return 0.2 + state.duration * 0.01  # rebuilding

    @property
    def resilience(self) -> float:
        """Resilience is highest during growth, lowest during omega."""
        if self._current == PanarchyPhase.OMEGA:
            return max(0.05, 0.3 - self._states[self._current].duration * 0.02)
        elif self._current == PanarchyPhase.ALPHA:
            return 0.3 + self._states[self._current].duration * 0.02
        elif self._current == PanarchyPhase.K:
            return max(0.1, 0.6 - self._states[self._current].duration * 0.01)
        else:
            return 0.5 + self._states[self._current].duration * 0.01

    # ── Transition logic ──────────────────────────────────────────────

    _TRANSITIONS: dict[PanarchyPhase, PanarchyPhase] = {
        PanarchyPhase.R: PanarchyPhase.K,
        PanarchyPhase.K: PanarchyPhase.OMEGA,
        PanarchyPhase.OMEGA: PanarchyPhase.ALPHA,
        PanarchyPhase.ALPHA: PanarchyPhase.R,
    }

    def tick(self, dt: float = 1.0) -> PanarchyPhase | None:
        """Advance the WLC by dt seconds. Returns new phase if transition occurred."""
        state = self._states[self._current]
        state.duration += dt

        # Check transition conditions
        should_transition = False

        if self._current == PanarchyPhase.R:
            # r→K when connectedness > 0.7
            should_transition = self.connectedness > 0.7 and state.duration > 10
        elif self._current == PanarchyPhase.K:
            # K→Ω when connectedness > 0.8 AND resilience < 0.2
            should_transition = (
                self.connectedness > 0.8
                and self.resilience < 0.2
                and state.duration > 20
            )
        elif self._current == PanarchyPhase.OMEGA:
            # Ω→α after sufficient destruction
            should_transition = state.duration > 5 and self.resilience < 0.1
        elif self._current == PanarchyPhase.ALPHA:
            # α→r when resilience rebuilds
            should_transition = self.resilience > 0.5 and state.duration > 8

        if should_transition:
            return self._transition()
        return None

    def _transition(self) -> PanarchyPhase:
        """Execute phase transition."""
        import time

        # Inhibit current node
        self._states[self._current].activity = 0.1
        self._states[self._current].duration = 0.0

        # Activate next node
        next_phase = self._TRANSITIONS[self._current]
        self._states[next_phase].activity = 0.8
        self._current = next_phase
        self._history.append((self._current.value, time.time()))

        return self._current

    def force_transition(self, target: PanarchyPhase) -> PanarchyPhase:
        """Force a specific phase transition (e.g., from external trigger)."""
        self._states[self._current].activity = 0.0
        self._states[target].activity = 1.0
        self._states[target].duration = 0.0
        self._current = target
        return self._current

    def get_status(self) -> dict[str, Any]:
        return {
            "current_phase": self._current.value,
            "connectedness": round(self.connectedness, 4),
            "resilience": round(self.resilience, 4),
            "phase_duration": round(self._states[self._current].duration, 1),
            "states": {
                p.value: {
                    "activity": round(s.activity, 3),
                    "duration": round(s.duration, 1),
                }
                for p, s in self._states.items()
            },
        }
