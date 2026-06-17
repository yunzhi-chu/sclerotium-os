"""Agent state machine with immutable state transitions.

Every state change produces a NEW AgentState — never mutates existing one.
This is the foundational pattern for the entire framework per coding-style.md.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any


class Lifecycle(Enum):
    """Agent lifecycle states."""

    SPAWNING = "spawning"
    ACTIVE = "active"
    IDLE = "idle"
    APOPTOSING = "apoptosing"
    DEAD = "dead"
    PROMOTING = "promoting"


class Specialty(Enum):
    """Agent professional specialties (5 QuantMind cluster types)."""

    INSTITUTION = "institution"     # 体制研究
    STRATEGY = "strategy"           # 策略挖掘
    INDICATOR = "indicator"         # 指标编译
    TACTICAL = "tactical"           # 本土战法
    RISK = "risk"                   # 风控压力
    ROOT = "root"                   # Root Agent
    GENERAL = "general"             # 通用代理


@dataclass(frozen=True)  # IMMUTABLE — the new state is returned on each transition
class AgentState:
    """Complete snapshot of agent state at a point in time.

    FROZEN dataclass — all state transitions return a new AgentState.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "agent"
    lifecycle: Lifecycle = Lifecycle.SPAWNING
    specialty: Specialty = Specialty.GENERAL
    position: tuple[int, int] = (128, 128)
    nutrition: float = 0.5
    activity: float = 0.0
    generation: int = 0
    skills: tuple[str, ...] = ()  # tuple for immutability
    performance: dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def activate(self) -> AgentState:
        """Transition to ACTIVE state."""
        return replace(self, lifecycle=Lifecycle.ACTIVE, last_active=time.time())

    def idle(self) -> AgentState:
        """Transition to IDLE state."""
        return replace(self, lifecycle=Lifecycle.IDLE)

    def apoptose(self) -> AgentState:
        """Transition to APOPTOSING (programmed cell death)."""
        return replace(self, lifecycle=Lifecycle.APOPTOSING)

    def die(self) -> AgentState:
        """Transition to DEAD (terminal)."""
        return replace(self, lifecycle=Lifecycle.DEAD)

    def move(self, i: int, j: int) -> AgentState:
        """Return new state with updated position."""
        return replace(self, position=(i, j), last_active=time.time())

    def feed(self, amount: float) -> AgentState:
        """Consume nutrients, updating nutrition level."""
        new_nutrition = max(0.0, min(1.0, self.nutrition + amount))
        return replace(self, nutrition=new_nutrition)

    def starve(self, amount: float) -> AgentState:
        """Lose nutrition over time."""
        new_nutrition = max(0.0, min(1.0, self.nutrition - amount))
        return replace(self, nutrition=new_nutrition)

    def update_activity(self, value: float) -> AgentState:
        """Set current activity level."""
        return replace(self, activity=value)

    def promote(self, specialty: Specialty) -> AgentState:
        """Promote to a new specialty."""
        return replace(self, specialty=specialty, lifecycle=Lifecycle.PROMOTING)

    def add_skill(self, skill_name: str) -> AgentState:
        """Add a skill (returns new state, tuple is immutable)."""
        if skill_name in self.skills:
            return self
        return replace(self, skills=self.skills + (skill_name,))

    def remove_skill(self, skill_name: str) -> AgentState:
        """Remove a skill."""
        return replace(self, skills=tuple(s for s in self.skills if s != skill_name))

    @property
    def is_alive(self) -> bool:
        return self.lifecycle not in (Lifecycle.DEAD,)

    @property
    def position_float(self) -> tuple[float, float]:
        return float(self.position[0]), float(self.position[1])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "lifecycle": self.lifecycle.value,
            "specialty": self.specialty.value,
            "position": list(self.position),
            "nutrition": self.nutrition,
            "activity": self.activity,
            "generation": self.generation,
            "skills": list(self.skills),
        }


class AgentStateTracker:
    """Tracks state history for a single agent (immutable log)."""

    def __init__(self, max_history: int = 1000) -> None:
        self._history: list[AgentState] = []
        self._max_history = max_history

    def push(self, state: AgentState) -> None:
        self._history.append(state)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    @property
    def current(self) -> AgentState | None:
        return self._history[-1] if self._history else None

    @property
    def history(self) -> list[AgentState]:
        return list(self._history)
