"""Cognitive depth scheduler — adaptive L1-L6 depth selection based on task complexity."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.model_router import CognitiveDepth


class TaskCategory(Enum):
    """Task categories mapped to minimum cognitive depth."""

    DATA_ACCESS = "data_access"           # L1: fetch/read data
    SIGNAL_CHECK = "signal_check"          # L2: threshold comparison
    DEBATE = "debate"                      # L3: multi-perspective
    RESEARCH = "research"                  # L4: deep analysis
    PLANNING = "planning"                  # L5: strategy planning
    META = "meta"                          # L6: self-reflection


# Mapping from task category to minimum cognitive depth
CATEGORY_MIN_DEPTH: dict[TaskCategory, CognitiveDepth] = {
    TaskCategory.DATA_ACCESS: CognitiveDepth.L1_FAST,
    TaskCategory.SIGNAL_CHECK: CognitiveDepth.L2_DECIDE,
    TaskCategory.DEBATE: CognitiveDepth.L3_DEBATE,
    TaskCategory.RESEARCH: CognitiveDepth.L4_RESEARCH,
    TaskCategory.PLANNING: CognitiveDepth.L5_PLAN,
    TaskCategory.META: CognitiveDepth.L6_META,
}


@dataclass
class ScheduleEntry:
    """A single scheduled cognitive task."""

    task_id: str
    category: TaskCategory
    system_prompt: str
    user_prompt: str
    context: dict[str, Any] = field(default_factory=dict)
    scheduled_at: float = field(default_factory=time.time)
    priority: int = 5  # 1 (highest) to 10 (lowest)
    depth: CognitiveDepth | None = None  # None = auto-select

    def __post_init__(self) -> None:
        if self.depth is None:
            self.depth = CATEGORY_MIN_DEPTH[self.category]


class CognitiveScheduler:
    """Adaptive cognitive depth scheduler.

    Selects the appropriate depth (L1-L6) based on task category and
    dynamically escalates when confidence is low or anomalies are detected.
    """

    def __init__(self, default_depth: CognitiveDepth = CognitiveDepth.L3_DEBATE) -> None:
        self.default_depth = default_depth
        self._pending: list[ScheduleEntry] = []
        self._history: list[ScheduleEntry] = []
        self._escalation_triggers: dict[str, int] = {}  # task_id → escalation count

    def schedule(self, task_id: str, category: TaskCategory, system: str, user: str, context: dict[str, Any] | None = None, priority: int = 5) -> ScheduleEntry:
        """Enqueue a cognitive task. Returns the scheduled entry."""
        entry = ScheduleEntry(
            task_id=task_id,
            category=category,
            system_prompt=system,
            user_prompt=user,
            context=context or {},
            priority=priority,
        )
        self._pending.append(entry)
        self._pending.sort(key=lambda e: e.priority)
        return entry

    def next(self) -> ScheduleEntry | None:
        """Pop the highest-priority pending task."""
        if not self._pending:
            return None
        entry = self._pending.pop(0)
        self._history.append(entry)
        return entry

    def escalate(self, task_id: str) -> CognitiveDepth:
        """Escalate a task to the next deeper cognitive level. Returns new depth."""
        current = self._escalation_triggers.get(task_id, 0)
        current += 1
        self._escalation_triggers[task_id] = current

        all_depths = list(CognitiveDepth)
        escalated_idx = min(5, current)  # cap at L6
        return all_depths[escalated_idx]

    def should_escalate(self, confidence: float, depth: CognitiveDepth) -> bool:
        """Determine if current depth should be escalated based on confidence."""
        thresholds = {
            CognitiveDepth.L1_FAST: 0.95,
            CognitiveDepth.L2_DECIDE: 0.90,
            CognitiveDepth.L3_DEBATE: 0.80,
            CognitiveDepth.L4_RESEARCH: 0.70,
            CognitiveDepth.L5_PLAN: 0.60,
            CognitiveDepth.L6_META: 0.50,  # L6 always tries, but can still trigger re-scan
        }
        return confidence < thresholds.get(depth, 0.70)

    def get_depth_for_category(self, category: TaskCategory) -> CognitiveDepth:
        """Get the recommended cognitive depth for a task category."""
        return CATEGORY_MIN_DEPTH.get(category, self.default_depth)

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def history_count(self) -> int:
        return len(self._history)

    def snapshot(self) -> dict[str, Any]:
        return {
            "pending_count": self.pending_count,
            "history_count": self.history_count,
            "escalations": dict(self._escalation_triggers),
        }
