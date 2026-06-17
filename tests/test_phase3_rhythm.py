"""Phase 3 Gray-Box Tests — STG Rhythm System.

Comprehensive tests covering:
  - RhythmEngine: pyloric/gastric loops, mode switching, callbacks
  - NudgeEngine: decision logic, cooldowns, mode policies
  - DailyDigest: event accumulation, digest generation, suggestions
  - Integration: rhythm → nudge → digest pipeline
"""

from __future__ import annotations

import time
import threading
from unittest import mock

import pytest

from kernel.event_bus import EventBus, Event
from kernel.stg.neuromodulator import Neuromodulator, Profile


# ═══════════════════════════════════════════════════════════════
# 1. RhythmEngine
# ═══════════════════════════════════════════════════════════════

class TestRhythmEngine:
    """Test the hierarchical rhythm generator."""

    def test_starts_and_stops(self):
        """Engine should start and stop cleanly."""
        bus = EventBus()
        from rhythm.rhythm_engine import RhythmEngine

        engine = RhythmEngine(event_bus=bus, pyloric_interval=0.1, gastric_interval=10.0)
        assert not engine.is_running

        engine.start()
        assert engine.is_running

        engine.stop()
        assert not engine.is_running

    def test_pyloric_ticks_accumulate(self):
        """Pyloric ticks should increment over time."""
        bus = EventBus()
        from rhythm.rhythm_engine import RhythmEngine

        engine = RhythmEngine(event_bus=bus, pyloric_interval=0.05, gastric_interval=60.0)
        engine.start()
        time.sleep(0.3)
        engine.stop()

        state = engine.get_state()
        assert state.pyloric_ticks >= 3, f"Expected >=3 pyloric ticks, got {state.pyloric_ticks}"
        assert state.total_ticks >= 3

    def test_pyloric_publishes_to_bus(self):
        """Each pyloric tick should publish to EventBus."""
        bus = EventBus()
        events = []
        bus.subscribe("rhythm.pyloric", lambda e: events.append(e))

        from rhythm.rhythm_engine import RhythmEngine

        engine = RhythmEngine(event_bus=bus, pyloric_interval=0.05, gastric_interval=60.0)
        engine.start()
        time.sleep(0.25)
        engine.stop()

        assert len(events) >= 2, f"Expected >=2 pyloric events, got {len(events)}"
        assert all(e.data["tick"] > 0 for e in events)

    def test_manual_pyloric_trigger(self):
        """Triggering pyloric manually should work."""
        bus = EventBus()
        from rhythm.rhythm_engine import RhythmEngine, RhythmLayer

        engine = RhythmEngine(event_bus=bus)
        tick = engine.trigger_pyloric_manually()

        assert tick.layer == RhythmLayer.PYLORIC
        assert tick.tick_number == 1

        tick2 = engine.trigger_pyloric_manually()
        assert tick2.tick_number == 2

    def test_manual_gastric_trigger(self):
        """Triggering gastric manually should work."""
        bus = EventBus()
        from rhythm.rhythm_engine import RhythmEngine, RhythmLayer

        engine = RhythmEngine(event_bus=bus)
        tick = engine.trigger_gastric_manually()

        assert tick.layer == RhythmLayer.GASTRIC
        assert tick.tick_number == 1

    def test_mode_switch(self):
        """Switching mode should update neuromodulator and publish event."""
        bus = EventBus()
        mode_events = []
        bus.subscribe("rhythm.mode_change", lambda e: mode_events.append(e))

        from rhythm.rhythm_engine import RhythmEngine

        engine = RhythmEngine(event_bus=bus)

        result = engine.switch_mode("sleep")
        assert result["active_profile"] == "sleep"
        assert len(mode_events) == 1
        assert mode_events[0].data["old"] == "work"
        assert mode_events[0].data["new"] == "sleep"

        result = engine.switch_mode("creative")
        assert result["active_profile"] == "creative"

        # Invalid mode
        result = engine.switch_mode("invalid")
        assert "error" in result

    def test_mode_change_callbacks(self):
        """Mode change callbacks should fire."""
        bus = EventBus()
        from rhythm.rhythm_engine import RhythmEngine

        engine = RhythmEngine(event_bus=bus)
        changes = []

        engine.on_mode_change(lambda old, new: changes.append((old, new)))
        engine.switch_mode("game")

        assert len(changes) == 1
        assert changes[0] == ("work", "game")

    def test_pyloric_callbacks(self):
        """Pyloric callbacks should fire on each tick."""
        bus = EventBus()
        from rhythm.rhythm_engine import RhythmEngine

        engine = RhythmEngine(event_bus=bus)
        ticks = []

        engine.on_pyloric(lambda t: ticks.append(t))
        engine.trigger_pyloric_manually()
        engine.trigger_pyloric_manually()

        assert len(ticks) == 2

    def test_gastric_callbacks(self):
        """Gastric callbacks should fire on each tick."""
        bus = EventBus()
        from rhythm.rhythm_engine import RhythmEngine

        engine = RhythmEngine(event_bus=bus)
        ticks = []

        engine.on_gastric(lambda t: ticks.append(t))
        engine.trigger_gastric_manually()

        assert len(ticks) == 1

    def test_get_state_snapshot(self):
        """State snapshot should reflect current engine state."""
        bus = EventBus()
        from rhythm.rhythm_engine import RhythmEngine

        engine = RhythmEngine(event_bus=bus, pyloric_interval=0.1, gastric_interval=60)

        state = engine.get_state()
        assert state.active_profile == "work"
        assert state.pyloric_ticks == 0
        assert state.gastric_ticks == 0
        assert state.uptime_seconds == 0.0

    def test_state_tick_counters(self):
        """After triggers, state should reflect tick counts."""
        bus = EventBus()
        from rhythm.rhythm_engine import RhythmEngine

        engine = RhythmEngine(event_bus=bus)
        engine.trigger_pyloric_manually()
        engine.trigger_pyloric_manually()
        engine.trigger_gastric_manually()

        state = engine.get_state()
        assert state.pyloric_ticks == 2
        assert state.gastric_ticks == 1
        assert state.total_ticks == 3

    def test_rhythm_tick_is_immutable(self):
        """RhythmTick should be frozen."""
        from rhythm.rhythm_engine import RhythmTick, RhythmLayer
        tick = RhythmTick(layer=RhythmLayer.PYLORIC, tick_number=1)
        with pytest.raises(Exception):
            tick.layer = RhythmLayer.GASTRIC  # type: ignore[misc]

    def test_rhythm_state_is_immutable(self):
        """RhythmState should be frozen."""
        from rhythm.rhythm_engine import RhythmState
        state = RhythmState(
            active_profile="work", pyloric_ticks=0,
            gastric_ticks=0, metabolic_ticks=0,
            total_ticks=0, uptime_seconds=0.0,
            pyloric_interval=30.0, gastric_interval=3600.0,
        )
        with pytest.raises(Exception):
            state.active_profile = "sleep"  # type: ignore[misc]

    def test_properties(self):
        """Properties should expose current state."""
        bus = EventBus()
        from rhythm.rhythm_engine import RhythmEngine

        engine = RhythmEngine(event_bus=bus)
        assert engine.profile == "work"
        assert engine.is_running is False
        assert isinstance(engine.neuromodulator, Neuromodulator)


# ═══════════════════════════════════════════════════════════════
# 2. NudgeEngine
# ═══════════════════════════════════════════════════════════════

class TestNudgeEngine:
    """Test the nudge decision engine."""

    def test_default_work_mode_policy(self):
        """Work mode should allow moderate notifications."""
        from rhythm.nudge_engine import NudgeEngine, NudgeLevel, NudgeCategory

        engine = NudgeEngine(mode="work")

        # Low importance → silent
        d = engine.decide(
            NudgeCategory.HEALTH, "Test", "Low importance", importance=0.1,
        )
        assert d.level == NudgeLevel.SILENT

        # Medium → tray
        d = engine.decide(
            NudgeCategory.INSIGHT, "Test", "Medium", importance=0.4,
        )
        assert d.level == NudgeLevel.TRAY

        # High → notify
        d = engine.decide(
            NudgeCategory.HEALTH, "Test", "High", importance=0.7,
        )
        assert d.level == NudgeLevel.NOTIFY

        # Critical → alert
        d = engine.decide(
            NudgeCategory.SECURITY, "Test", "Critical", importance=0.95,
        )
        assert d.level == NudgeLevel.ALERT

    def test_sleep_mode_suppresses_most(self):
        """Sleep mode should suppress almost everything."""
        from rhythm.nudge_engine import NudgeEngine, NudgeLevel, NudgeCategory

        engine = NudgeEngine(mode="sleep")

        d = engine.decide(
            NudgeCategory.HEALTH, "Test", "Normal", importance=0.6,
        )
        assert d.level == NudgeLevel.SILENT  # Below sleep tray threshold (0.7)

        d = engine.decide(
            NudgeCategory.SECURITY, "Test", "Security", importance=0.99,
        )
        assert d.level == NudgeLevel.ALERT  # Security always gets through

    def test_game_mode_partial_suppression(self):
        """Game mode should allow only important notifications."""
        from rhythm.nudge_engine import NudgeEngine, NudgeLevel, NudgeCategory

        engine = NudgeEngine(mode="game")

        d = engine.decide(
            NudgeCategory.HEALTH, "Test", "Break", importance=0.5,
        )
        assert d.level == NudgeLevel.SILENT  # Below game threshold

        d = engine.decide(
            NudgeCategory.HEALTH, "Test", "Important", importance=0.9,
        )
        assert d.level == NudgeLevel.NOTIFY

    def test_security_always_alerts(self):
        """Security category should always produce ALERT regardless of mode."""
        from rhythm.nudge_engine import NudgeEngine, NudgeLevel, NudgeCategory

        for mode in ["work", "sleep", "game", "meeting", "creative"]:
            engine = NudgeEngine(mode=mode)
            d = engine.decide(
                NudgeCategory.SECURITY, "⚠ Alert", "Danger", importance=0.5,
            )
            assert d.level == NudgeLevel.ALERT, f"Security should alert in {mode}"

    def test_force_bypasses_all_checks(self):
        """force=True should bypass all checks."""
        from rhythm.nudge_engine import NudgeEngine, NudgeLevel, NudgeCategory

        engine = NudgeEngine(mode="sleep")  # Most restrictive
        d = engine.decide(
            NudgeCategory.INFO, "Forced", "Message", importance=0.01, force=True,
        )
        assert d.level == NudgeLevel.ALERT

    def test_cooldown_respected(self):
        """After a notification, cooldown should block subsequent ones."""
        from rhythm.nudge_engine import NudgeEngine, NudgeLevel, NudgeCategory

        engine = NudgeEngine(mode="work")  # cooldown = 300s

        # First notification goes through
        d1 = engine.decide(
            NudgeCategory.HEALTH, "First", "Message", importance=0.8,
        )
        assert d1.level == NudgeLevel.NOTIFY

        # Second immediately after → cooldown
        d2 = engine.decide(
            NudgeCategory.HEALTH, "Second", "Message", importance=0.9,
        )
        assert d2.level == NudgeLevel.SILENT
        assert "Cooldown" in d2.reason

    def test_hourly_cap_respected(self):
        """After max notifications per hour, further ones are silent."""
        from rhythm.nudge_engine import NudgeEngine, NudgeLevel, NudgeCategory

        engine = NudgeEngine(mode="work")  # max 8/hour

        # Force many notifications (bypass cooldown by resetting time)
        engine._last_notification_time = 0.0
        for i in range(engine._policy.max_notifications_per_hour):
            d = engine.decide(
                NudgeCategory.INFO, f"Nudge {i}", "Msg", importance=0.8,
            )
            engine._last_notification_time = 0.0  # Reset cooldown after each

        # One more — should be capped
        engine._last_notification_time = 0.0
        d = engine.decide(
            NudgeCategory.INFO, "Over cap", "Msg", importance=0.9,
        )
        assert d.level == NudgeLevel.SILENT
        assert "Hourly cap" in d.reason

    def test_fullscreen_suppression(self):
        """Fullscreen should suppress non-critical notifications."""
        from rhythm.nudge_engine import NudgeEngine, NudgeLevel, NudgeCategory

        engine = NudgeEngine(mode="work")
        engine.set_fullscreen(True)

        d = engine.decide(
            NudgeCategory.HEALTH, "Break", "Time for break", importance=0.8,
        )
        assert d.level == NudgeLevel.SILENT
        assert "fullscreen" in d.reason.lower()

        # Critical should still get through
        d = engine.decide(
            NudgeCategory.SECURITY, "Alert", "Danger", importance=0.95,
        )
        assert d.level == NudgeLevel.ALERT

    def test_set_mode_updates_policy(self):
        """Changing mode should update the nudge policy."""
        from rhythm.nudge_engine import NudgeEngine

        engine = NudgeEngine(mode="work")
        assert engine.mode == "work"
        assert engine.policy.cooldown_seconds == 300

        engine.set_mode("sleep")
        assert engine.mode == "sleep"
        assert engine.policy.cooldown_seconds == 3600

    def test_get_stats(self):
        """Stats should reflect decision history."""
        from rhythm.nudge_engine import NudgeEngine, NudgeCategory

        engine = NudgeEngine(mode="work")
        engine.decide(NudgeCategory.HEALTH, "1", "", importance=0.1)
        engine.decide(NudgeCategory.HEALTH, "2", "", importance=0.8)
        engine.decide(NudgeCategory.INFO, "3", "", importance=0.6)

        stats = engine.get_stats()
        assert stats["mode"] == "work"
        assert stats["total_decisions"] == 3

    def test_get_history(self):
        """History should return recent decisions."""
        from rhythm.nudge_engine import NudgeEngine, NudgeCategory

        engine = NudgeEngine(mode="work")
        for i in range(5):
            engine.decide(NudgeCategory.INFO, f"Test {i}", "", importance=0.1)

        history = engine.get_history(limit=3)
        assert len(history) == 3

    def test_nudge_decision_is_immutable(self):
        """NudgeDecision should be frozen."""
        from rhythm.nudge_engine import NudgeDecision, NudgeLevel, NudgeCategory
        d = NudgeDecision(
            level=NudgeLevel.SILENT, category=NudgeCategory.INFO,
            title="", message="", importance=0.0,
        )
        with pytest.raises(Exception):
            d.level = NudgeLevel.ALERT  # type: ignore[misc]

    def test_all_modes_have_policies(self):
        """Every valid mode should have a defined policy."""
        from rhythm.nudge_engine import MODE_POLICIES
        for mode in ["work", "sleep", "game", "meeting", "creative"]:
            assert mode in MODE_POLICIES, f"Missing policy for {mode}"


# ═══════════════════════════════════════════════════════════════
# 3. DailyDigest
# ═══════════════════════════════════════════════════════════════

class TestDailyDigest:
    """Test the daily digest generation."""

    def test_starts_and_stops(self):
        """Digest should start and stop cleanly."""
        bus = EventBus()
        from rhythm.daily_digest import DailyDigest

        digest = DailyDigest(event_bus=bus)
        digest.start()
        assert digest.is_started
        digest.stop()
        assert not digest.is_started

    def test_accumulates_window_events(self):
        """Window change events should accumulate."""
        bus = EventBus()
        from rhythm.daily_digest import DailyDigest

        digest = DailyDigest(event_bus=bus)
        digest.start()

        # Simulate window changes
        for i in range(5):
            bus.publish("window.changed", {
                "current": {
                    "title": f"File{i}.py — MyProject",
                    "process_name": "Code.exe",
                },
                "previous": None,
            })

        digest.stop()

        # Should have accumulated event data
        result = digest.generate()
        assert result.activity.windows_switched > 0, (
            f"Expected window switches > 0, got {result.activity.windows_switched}"
        )

    def test_accumulates_file_events(self):
        """File events should be counted."""
        bus = EventBus()
        from rhythm.daily_digest import DailyDigest

        digest = DailyDigest(event_bus=bus)
        digest.start()

        bus.publish("file.created", {"path": "/proj/a.py", "suffix": ".py"})
        bus.publish("file.created", {"path": "/proj/b.ts", "suffix": ".ts"})
        bus.publish("file.modified", {"path": "/proj/a.py", "suffix": ".py"})

        digest.stop()

        result = digest.generate()
        assert result.files_created == 2
        assert result.files_modified == 1

    def test_inject_event_works(self):
        """Manual event injection should work."""
        bus = EventBus()
        from rhythm.daily_digest import DailyDigest

        digest = DailyDigest(event_bus=bus)
        digest.inject_event(Event(topic="test", data={"x": 1}))
        digest.inject_event(Event(topic="test", data={"x": 2}))

        assert digest.event_count == 2

    def test_reset_daily(self):
        """Reset should clear all accumulators."""
        bus = EventBus()
        from rhythm.daily_digest import DailyDigest

        digest = DailyDigest(event_bus=bus)
        digest.start()

        bus.publish("file.created", {"path": "/a.py", "suffix": ".py"})
        digest.stop()

        result = digest.generate()
        assert result.files_created == 1

        digest.reset_daily()
        result2 = digest.generate()
        assert result2.files_created == 0
        assert digest.event_count == 0

    def test_generates_summary_string(self):
        """to_summary should produce readable text."""
        bus = EventBus()
        from rhythm.daily_digest import DailyDigest

        digest = DailyDigest(event_bus=bus)
        digest.start()

        bus.publish("file.created", {"path": "/p/main.py", "suffix": ".py"})
        bus.publish("window.changed", {
            "current": {"title": "main.py — MyProject", "process_name": "Code.exe"},
            "previous": None,
        })

        digest.stop()

        result = digest.generate()
        summary = result.to_summary()
        assert "Activity" in summary
        assert result.date in summary

    def test_digest_result_is_immutable(self):
        """DailyDigestResult should be frozen."""
        from rhythm.daily_digest import DailyDigestResult, ActivityMetrics

        metrics = ActivityMetrics(total_active_seconds=3600)
        result = DailyDigestResult(
            date="2026-06-15", day_of_week="Monday",
            activity=metrics,
        )
        with pytest.raises(Exception):
            result.date = "changed"  # type: ignore[misc]

    def test_suggestions_for_long_day(self):
        """Should generate suggestions for long work days."""
        from rhythm.daily_digest import DailyDigest, ActivityMetrics, DailyDigestResult

        digest = DailyDigest(event_bus=EventBus())
        activity = ActivityMetrics(
            total_active_seconds=36000,  # 10 hours
            sessions_count=5,
        )
        suggestions = digest._generate_suggestions(activity)
        assert any("8 hours" in s for s in suggestions)

    def test_suggestions_for_short_day(self):
        """Should generate suggestions for short days."""
        from rhythm.daily_digest import DailyDigest, ActivityMetrics

        digest = DailyDigest(event_bus=EventBus())
        activity = ActivityMetrics(
            total_active_seconds=1800,  # 0.5 hours
            sessions_count=2,
        )
        suggestions = digest._generate_suggestions(activity)
        assert any("Light" in s for s in suggestions)

    def test_suggestions_for_many_sessions(self):
        """Many sessions should trigger batching suggestion."""
        from rhythm.daily_digest import DailyDigest, ActivityMetrics

        digest = DailyDigest(event_bus=EventBus())
        activity = ActivityMetrics(
            total_active_seconds=36000,
            sessions_count=15,
        )
        suggestions = digest._generate_suggestions(activity)
        assert any("batching" in s.lower() for s in suggestions)

    def test_suggestions_for_high_idle(self):
        """High idle ratio should trigger distraction suggestion."""
        from rhythm.daily_digest import DailyDigest, ActivityMetrics

        digest = DailyDigest(event_bus=EventBus())
        activity = ActivityMetrics(
            total_active_seconds=3600,
            total_idle_seconds=2000,
            sessions_count=3,
        )
        suggestions = digest._generate_suggestions(activity)
        assert any("idle" in s.lower() or "distraction" in s.lower() for s in suggestions)

    def test_event_count_property(self):
        """Event count should reflect injected events."""
        bus = EventBus()
        from rhythm.daily_digest import DailyDigest

        digest = DailyDigest(event_bus=bus)
        digest.start()

        for i in range(10):
            bus.publish("window.changed", {
                "current": {"title": f"f{i}", "process_name": "test.exe"},
                "previous": None,
            })

        digest.stop()
        assert digest.event_count >= 10

    def test_activity_metrics_to_dict(self):
        """ActivityMetrics.to_dict should produce correct structure."""
        from rhythm.daily_digest import ActivityMetrics
        metrics = ActivityMetrics(
            total_active_seconds=7200,
            total_idle_seconds=600,
            sessions_count=4,
            top_apps=(("Code.exe", 0.6), ("chrome.exe", 0.4)),
            windows_switched=50,
            avg_focus_minutes=30.0,
            peak_hour=14,
            languages_detected=("Python", "TypeScript"),
        )
        d = metrics.to_dict()
        assert d["total_active_hours"] == 2.0
        assert d["total_idle_minutes"] == 10.0
        assert d["sessions_count"] == 4
        assert d["peak_hour"] == 14
        assert "Python" in d["languages"]


# ═══════════════════════════════════════════════════════════════
# 4. Neuromodulator (existing kernel/stg/)
# ═══════════════════════════════════════════════════════════════

class TestNeuromodulator:
    """Test the existing neuromodulator module."""

    def test_default_profile_is_work(self):
        """Default profile should be WORK."""
        neuro = Neuromodulator()
        assert neuro.active_profile == Profile.WORK

    def test_switch_valid_profiles(self):
        """All 5 profiles should be switchable."""
        neuro = Neuromodulator()
        for profile in ["work", "sleep", "game", "meeting", "creative"]:
            result = neuro.switch(profile)
            assert "error" not in result
            assert result["active_profile"] == profile

    def test_switch_invalid_profile(self):
        """Invalid profile should return error."""
        neuro = Neuromodulator()
        result = neuro.switch("invalid")
        assert "error" in result

    def test_get_profile_returns_state(self):
        """get_profile should return current profile data."""
        neuro = Neuromodulator()
        profile = neuro.get_profile()
        assert profile["profile"] == "work"
        assert "notification_level" in profile
        assert "evolution_enabled" in profile

    def test_sleep_disables_evolution(self):
        """Sleep mode should disable evolution."""
        neuro = Neuromodulator()
        neuro.switch("sleep")
        state = neuro.state
        assert state.evolution_enabled is False
        assert state.notification_level == "none"

    def test_creative_enables_best_llm(self):
        """Creative mode should use best LLM routing."""
        neuro = Neuromodulator()
        neuro.switch("creative")
        state = neuro.state
        assert state.llm_routing == "best"
        assert state.evolution_enabled is True

    def test_state_is_mutable_dataclass(self):
        """ModulationState should be a regular (not frozen) dataclass."""
        neuro = Neuromodulator()
        state = neuro.state
        state.notification_level = "test"  # Should not raise
        assert state.notification_level == "test"


# ═══════════════════════════════════════════════════════════════
# 5. Integration Scenarios
# ═══════════════════════════════════════════════════════════════

class TestRhythmIntegration:
    """End-to-end: rhythm → nudge → digest pipeline."""

    def test_rhythm_ticks_publish_to_bus(self):
        """RhythmEngine ticks → EventBus → subscribers receive."""
        bus = EventBus()
        pyloric_events = []
        gastric_events = []
        bus.subscribe("rhythm.pyloric", lambda e: pyloric_events.append(e))
        bus.subscribe("rhythm.gastric", lambda e: gastric_events.append(e))

        from rhythm.rhythm_engine import RhythmEngine

        engine = RhythmEngine(event_bus=bus, pyloric_interval=0.05, gastric_interval=60.0)
        engine.start()
        time.sleep(0.3)
        engine.stop()

        assert len(pyloric_events) >= 3

    def test_mode_switch_affects_nudge_policy(self):
        """Switching mode should change nudge behavior."""
        from rhythm.nudge_engine import NudgeEngine, NudgeLevel, NudgeCategory

        engine = NudgeEngine(mode="work")

        # Work: importance 0.7 → NOTIFY
        d = engine.decide(NudgeCategory.HEALTH, "T", "", importance=0.7)
        assert d.level == NudgeLevel.NOTIFY

        # Switch to sleep
        engine.set_mode("sleep")

        # Sleep: same importance → SILENT
        d = engine.decide(NudgeCategory.HEALTH, "T", "", importance=0.7)
        assert d.level == NudgeLevel.SILENT

    def test_digest_integration_with_gastric(self):
        """Gastric ticks should trigger digest generation at end of day."""
        bus = EventBus()
        from rhythm.daily_digest import DailyDigest

        digest = DailyDigest(event_bus=bus)
        digest.start()

        # Inject some events
        bus.publish("file.created", {"path": "/x.py", "suffix": ".py"})
        bus.publish("file.created", {"path": "/y.ts", "suffix": ".ts"})
        bus.publish("window.changed", {
            "current": {"title": "test — TestProject", "process_name": "test.exe"},
            "previous": None,
        })

        # Generate BEFORE gastric tick reset
        result = digest.generate()
        assert result.files_created == 2

        # Simulate late-night gastric tick — should trigger auto-reset
        bus.publish("rhythm.gastric", {"tick": 1, "hour": 22, "weekday": 1})

        # After gastric reset, generate should produce empty fresh digest
        result2 = digest.generate()
        assert result2.files_created == 0  # Reset by gastric

        digest.stop()

    def test_full_pipeline(self):
        """Rhythm → Nudge → Digest — the complete cycle."""
        bus = EventBus()

        from rhythm.rhythm_engine import RhythmEngine
        from rhythm.nudge_engine import NudgeEngine
        from rhythm.daily_digest import DailyDigest

        engine = RhythmEngine(event_bus=bus, pyloric_interval=0.1, gastric_interval=60)
        nudge = NudgeEngine(mode="work")
        digest = DailyDigest(event_bus=bus)

        engine.start()
        digest.start()

        # Simulate a work session
        for _ in range(5):
            bus.publish("window.changed", {
                "current": {"title": "code.py — Project", "process_name": "Code.exe"},
                "previous": None,
            })

        # Check nudge at end of session
        from rhythm.nudge_engine import NudgeCategory
        decision = nudge.decide(
            category=NudgeCategory.HEALTH,
            title="Session end",
            message="Done coding",
            importance=0.6,
        )
        assert decision.level != "UNKNOWN"

        # Generate digest
        result = digest.generate()
        assert result.date  # Has a date string

        engine.stop()
        digest.stop()
