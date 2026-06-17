"""Tests for cognitive_scheduler module — adaptive L1-L6 depth selection."""

from __future__ import annotations

import pytest

from src.core.cognitive_scheduler import (
    CATEGORY_MIN_DEPTH,
    CognitiveScheduler,
    ScheduleEntry,
    TaskCategory,
)
from src.core.model_router import CognitiveDepth


class TestTaskCategory:
    def test_all_categories_exist(self):
        assert TaskCategory.DATA_ACCESS.value == "data_access"
        assert TaskCategory.SIGNAL_CHECK.value == "signal_check"
        assert TaskCategory.DEBATE.value == "debate"
        assert TaskCategory.RESEARCH.value == "research"
        assert TaskCategory.PLANNING.value == "planning"
        assert TaskCategory.META.value == "meta"

    def test_category_min_depth_mapping(self):
        assert CATEGORY_MIN_DEPTH[TaskCategory.DATA_ACCESS] == CognitiveDepth.L1_FAST
        assert CATEGORY_MIN_DEPTH[TaskCategory.SIGNAL_CHECK] == CognitiveDepth.L2_DECIDE
        assert CATEGORY_MIN_DEPTH[TaskCategory.DEBATE] == CognitiveDepth.L3_DEBATE
        assert CATEGORY_MIN_DEPTH[TaskCategory.RESEARCH] == CognitiveDepth.L4_RESEARCH
        assert CATEGORY_MIN_DEPTH[TaskCategory.PLANNING] == CognitiveDepth.L5_PLAN
        assert CATEGORY_MIN_DEPTH[TaskCategory.META] == CognitiveDepth.L6_META


class TestScheduleEntry:
    def test_creation_with_auto_depth(self):
        entry = ScheduleEntry(
            task_id="task-1",
            category=TaskCategory.DATA_ACCESS,
            system_prompt="sys",
            user_prompt="user",
        )
        assert entry.task_id == "task-1"
        assert entry.depth == CognitiveDepth.L1_FAST
        assert entry.priority == 5
        assert entry.context == {}

    def test_creation_with_explicit_depth(self):
        entry = ScheduleEntry(
            task_id="task-2",
            category=TaskCategory.META,
            system_prompt="sys",
            user_prompt="user",
            depth=CognitiveDepth.L3_DEBATE,
            priority=3,
            context={"key": "val"},
        )
        assert entry.depth == CognitiveDepth.L3_DEBATE
        assert entry.priority == 3
        assert entry.context == {"key": "val"}

    def test_post_init_sets_meta_depth(self):
        entry = ScheduleEntry(
            task_id="t", category=TaskCategory.META, system_prompt="s", user_prompt="u"
        )
        assert entry.depth == CognitiveDepth.L6_META


class TestCognitiveScheduler:
    @pytest.fixture
    def sched(self):
        return CognitiveScheduler()

    def test_default_depth(self, sched):
        assert sched.default_depth == CognitiveDepth.L3_DEBATE

    def test_schedule_returns_entry(self, sched):
        entry = sched.schedule("t1", TaskCategory.DATA_ACCESS, "sys", "user")
        assert isinstance(entry, ScheduleEntry)
        assert entry.task_id == "t1"

    def test_schedule_sorts_by_priority(self, sched):
        sched.schedule("low", TaskCategory.DATA_ACCESS, "s", "u", priority=8)
        sched.schedule("high", TaskCategory.DATA_ACCESS, "s", "u", priority=2)
        sched.schedule("mid", TaskCategory.DATA_ACCESS, "s", "u", priority=5)
        nxt = sched.next()
        assert nxt.task_id == "high"  # Lowest priority number first

    def test_next_returns_none_when_empty(self, sched):
        assert sched.next() is None

    def test_next_moves_to_history(self, sched):
        sched.schedule("t1", TaskCategory.DATA_ACCESS, "s", "u")
        assert sched.pending_count == 1
        sched.next()
        assert sched.pending_count == 0
        assert sched.history_count == 1

    def test_escalate_deepens_level(self, sched):
        depth = sched.escalate("task-1")
        assert depth == CognitiveDepth.L2_DECIDE

    def test_escalate_twice(self, sched):
        sched.escalate("task-1")
        depth = sched.escalate("task-1")
        assert depth == CognitiveDepth.L3_DEBATE

    def test_escalate_caps_at_l6(self, sched):
        for _ in range(10):
            sched.escalate("task-1")
        depth = sched.escalate("task-1")
        assert depth == CognitiveDepth.L6_META

    def test_should_escalate_l1_low_confidence(self, sched):
        assert sched.should_escalate(0.90, CognitiveDepth.L1_FAST) is True

    def test_should_escalate_l1_high_confidence(self, sched):
        assert sched.should_escalate(0.96, CognitiveDepth.L1_FAST) is False

    def test_should_escalate_l6_always_checks(self, sched):
        assert sched.should_escalate(0.40, CognitiveDepth.L6_META) is True

    def test_should_escalate_unknown_depth(self, sched):
        # Unknown depth uses default threshold 0.70
        should = sched.should_escalate(0.60, CognitiveDepth.L3_DEBATE)
        assert should is True

    def test_get_depth_for_category(self, sched):
        assert sched.get_depth_for_category(TaskCategory.DATA_ACCESS) == CognitiveDepth.L1_FAST
        assert sched.get_depth_for_category(TaskCategory.META) == CognitiveDepth.L6_META

    def test_pending_count(self, sched):
        assert sched.pending_count == 0
        sched.schedule("a", TaskCategory.DATA_ACCESS, "s", "u")
        sched.schedule("b", TaskCategory.DATA_ACCESS, "s", "u")
        assert sched.pending_count == 2

    def test_history_count(self, sched):
        assert sched.history_count == 0
        sched.schedule("a", TaskCategory.DATA_ACCESS, "s", "u")
        sched.next()
        assert sched.history_count == 1

    def test_snapshot(self, sched):
        sched.schedule("t1", TaskCategory.META, "sys", "user")
        sched.escalate("t1")
        snap = sched.snapshot()
        assert snap["pending_count"] == 1
        assert snap["history_count"] == 0
        assert "t1" in snap["escalations"]

    def test_schedule_with_context(self, sched):
        ctx = {"model": "deepseek", "temperature": 0.5}
        entry = sched.schedule("ctx-task", TaskCategory.RESEARCH, "sys", "user", context=ctx)
        assert entry.context == ctx

    def test_multiple_nexts_in_priority_order(self, sched):
        sched.schedule("p9", TaskCategory.DATA_ACCESS, "s", "u", priority=9)
        sched.schedule("p1", TaskCategory.DATA_ACCESS, "s", "u", priority=1)
        sched.schedule("p5", TaskCategory.DATA_ACCESS, "s", "u", priority=5)
        assert sched.next().task_id == "p1"
        assert sched.next().task_id == "p5"
        assert sched.next().task_id == "p9"
