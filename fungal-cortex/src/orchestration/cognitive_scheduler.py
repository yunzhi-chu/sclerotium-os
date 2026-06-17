"""Cognitive Scheduler — adaptive cognitive depth selection (L1~L6).

The scheduler maps incoming tasks to the appropriate cognitive depth based on:
- Task complexity (simple → L1 fast, complex → L6 meta)
- Time pressure (urgent → lower depth, leisurely → higher depth)
- Resource availability (low resources → conserve, abundant → explore)
- Novelty (known pattern → low depth, novel → high depth)

Cognitive depth levels (from AGENT.md / core/cognitive_scheduler.py):
- L1_FAST (~200ms): Quick lookup, cached response
- L2_BASIC (~500ms): Simple analysis, single-step reasoning
- L3_DEBATE (~2s): Multi-perspective analysis, BULL/BEAR compare
- L4_RESEARCH (~10s): Deep research, hypothesis generation
- L5_STRATEGIC (~30s): Multi-agent coordination, strategic planning
- L6_META (~continuous): Metacognitive reflection, self-improvement
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any

from src.utils.logging import CortexLogger


class CognitiveDepth(IntEnum):
    """Cognitive depth levels — higher = deeper processing."""

    L1_FAST = 1       # ~200ms
    L2_BASIC = 2      # ~500ms
    L3_DEBATE = 3     # ~2s
    L4_RESEARCH = 4   # ~10s
    L5_STRATEGIC = 5  # ~30s
    L6_META = 6       # Continuous

    @property
    def expected_latency_ms(self) -> float:
        return {
            CognitiveDepth.L1_FAST: 200,
            CognitiveDepth.L2_BASIC: 500,
            CognitiveDepth.L3_DEBATE: 2000,
            CognitiveDepth.L4_RESEARCH: 10000,
            CognitiveDepth.L5_STRATEGIC: 30000,
            CognitiveDepth.L6_META: float("inf"),
        }[self]


class TaskCategory(Enum):
    """Categories of tasks for scheduling."""

    QUICK_QUERY = "quick_query"
    DATA_FETCH = "data_fetch"
    SIMPLE_ANALYSIS = "simple_analysis"
    INDICATOR_COMPUTE = "indicator_compute"
    DEBATE_CLAIM = "debate_claim"
    STRATEGY_BACKTEST = "strategy_backtest"
    DEEP_RESEARCH = "deep_research"
    SYSTEM_SCAN = "system_scan"
    EMERGENCE_CAPTURE = "emergence_capture"
    META_REFLECTION = "meta_reflection"


@dataclass
class SchedulerDecision:
    """A scheduler decision for a task."""

    task_id: str
    category: TaskCategory
    assigned_depth: CognitiveDepth
    priority: int  # 1-10 (10 = highest)
    estimated_tokens: int = 500
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)


class CognitiveScheduler:
    """Maps tasks to cognitive depths based on context signals.

    The scheduler uses three signals (from ⑥ SelfReferentialSwitch DMN monitoring):
    1. time_pressure: Higher → lower depth (need fast response)
    2. novelty: Higher → higher depth (need exploration)
    3. resource_remaining: Lower → lower depth (conserve)
    """

    # Default depth assignment by task category
    CATEGORY_DEPTH: dict[TaskCategory, CognitiveDepth] = {
        TaskCategory.QUICK_QUERY: CognitiveDepth.L1_FAST,
        TaskCategory.DATA_FETCH: CognitiveDepth.L1_FAST,
        TaskCategory.SIMPLE_ANALYSIS: CognitiveDepth.L2_BASIC,
        TaskCategory.INDICATOR_COMPUTE: CognitiveDepth.L2_BASIC,
        TaskCategory.DEBATE_CLAIM: CognitiveDepth.L3_DEBATE,
        TaskCategory.STRATEGY_BACKTEST: CognitiveDepth.L4_RESEARCH,
        TaskCategory.DEEP_RESEARCH: CognitiveDepth.L4_RESEARCH,
        TaskCategory.SYSTEM_SCAN: CognitiveDepth.L5_STRATEGIC,
        TaskCategory.EMERGENCE_CAPTURE: CognitiveDepth.L5_STRATEGIC,
        TaskCategory.META_REFLECTION: CognitiveDepth.L6_META,
    }

    # Default priority by category
    CATEGORY_PRIORITY: dict[TaskCategory, int] = {
        TaskCategory.QUICK_QUERY: 3,
        TaskCategory.DATA_FETCH: 4,
        TaskCategory.SIMPLE_ANALYSIS: 5,
        TaskCategory.INDICATOR_COMPUTE: 5,
        TaskCategory.DEBATE_CLAIM: 6,
        TaskCategory.STRATEGY_BACKTEST: 7,
        TaskCategory.DEEP_RESEARCH: 8,
        TaskCategory.SYSTEM_SCAN: 9,
        TaskCategory.EMERGENCE_CAPTURE: 10,
        TaskCategory.META_REFLECTION: 10,
    }

    def __init__(self, default_depth: CognitiveDepth = CognitiveDepth.L2_BASIC) -> None:
        self._default_depth = default_depth
        self._logger = CortexLogger("cognitive_scheduler")
        self._decisions: list[SchedulerDecision] = []
        self._task_count = 0

    def schedule(
        self,
        task_id: str,
        category: TaskCategory,
        time_pressure: float = 0.0,
        novelty: float = 0.0,
        resource_remaining: float = 1.0,
    ) -> SchedulerDecision:
        """Schedule a task to the appropriate cognitive depth.

        Args:
            task_id: Unique task identifier
            category: What kind of task
            time_pressure: 0-1, how urgent (1 = very urgent)
            novelty: 0-1, how novel (1 = completely new)
            resource_remaining: 0-1, compute budget remaining
        """
        base_depth = self.CATEGORY_DEPTH.get(category, self._default_depth)
        depth = self._adjust_depth(base_depth, time_pressure, novelty, resource_remaining)
        priority = self._compute_priority(category, time_pressure, novelty)

        reasons: list[str] = []
        if time_pressure > 0.5:
            reasons.append(f"time_pressure={time_pressure:.1f}→depth_reduced")
        if novelty > 0.5:
            reasons.append(f"novelty={novelty:.1f}→depth_increased")

        decision = SchedulerDecision(
            task_id=task_id,
            category=category,
            assigned_depth=depth,
            priority=priority,
            estimated_tokens=self._estimate_tokens(depth),
            reasoning="; ".join(reasons) if reasons else "default_depth",
        )
        self._decisions.append(decision)
        self._task_count += 1

        if len(self._decisions) > 1000:
            self._decisions = self._decisions[-500:]

        self._logger.debug("task_scheduled", task_id=task_id, depth=depth.value, priority=priority)
        return decision

    def _adjust_depth(
        self,
        base: CognitiveDepth,
        time_pressure: float,
        novelty: float,
        resource_remaining: float,
    ) -> CognitiveDepth:
        """Adjust depth based on contextual signals."""
        adjustment = 0

        # Time pressure reduces depth
        if time_pressure > 0.7:
            adjustment -= 2
        elif time_pressure > 0.4:
            adjustment -= 1

        # Novelty increases depth
        if novelty > 0.7:
            adjustment += 2
        elif novelty > 0.4:
            adjustment += 1

        # Low resources reduce depth
        if resource_remaining < 0.2:
            adjustment -= 1

        new_depth = max(1, min(6, base.value + adjustment))
        return CognitiveDepth(new_depth)

    def _compute_priority(self, category: TaskCategory, time_pressure: float, novelty: float) -> int:
        """Compute task priority (1-10)."""
        base = self.CATEGORY_PRIORITY.get(category, 5)
        if time_pressure > 0.7:
            base = min(10, base + 2)
        if novelty > 0.7:
            base = min(10, base + 1)
        return base

    @staticmethod
    def _estimate_tokens(depth: CognitiveDepth) -> int:
        """Estimate token consumption for a given depth."""
        return {
            CognitiveDepth.L1_FAST: 200,
            CognitiveDepth.L2_BASIC: 500,
            CognitiveDepth.L3_DEBATE: 2000,
            CognitiveDepth.L4_RESEARCH: 10000,
            CognitiveDepth.L5_STRATEGIC: 30000,
            CognitiveDepth.L6_META: 100000,
        }.get(depth, 500)

    def get_pending_count(self, max_depth: CognitiveDepth | None = None) -> int:
        """Count pending tasks, optionally filtered by max depth."""
        if max_depth is None:
            return self._task_count
        return sum(1 for d in self._decisions if d.assigned_depth <= max_depth)

    @property
    def stats(self) -> dict[str, Any]:
        depth_counts = {d.value: 0 for d in CognitiveDepth}
        for dec in self._decisions[-100:]:
            depth_counts[dec.assigned_depth.value] = depth_counts.get(dec.assigned_depth.value, 0) + 1
        return {
            "total_scheduled": self._task_count,
            "recent_depth_distribution": depth_counts,
            "default_depth": self._default_depth.value,
        }
