"""Phase 2 Gray-Box Tests — Perception System.

Comprehensive tests covering:
  - EventBus: pub/sub, thread safety, ring buffer
  - WindowWatcher: polling, change detection, idle detection
  - ClipboardWatcher: content categorization, hash-based dedup
  - FileWatcher: event injection, debounce, path filtering
  - ActivityTracker: state transitions, session tracking, daily reset
  - UserModel: serialization, EMA updates, language/app detection
  - Integration: sensor data → UserModel pipeline
"""

from __future__ import annotations

import time
import json
import threading
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from kernel.event_bus import EventBus, Event


# ═══════════════════════════════════════════════════════════════
# 1. EventBus
# ═══════════════════════════════════════════════════════════════

class TestEventBus:
    """Test the lightweight EventBus."""

    def test_subscribe_and_publish(self):
        """Subscriber should receive published events."""
        bus = EventBus()
        received = []

        bus.subscribe("test.topic", lambda e: received.append(e))
        bus.publish("test.topic", {"key": "value"}, source="test")

        assert len(received) == 1
        assert received[0].topic == "test.topic"
        assert received[0].data == {"key": "value"}
        assert received[0].source == "test"

    def test_multiple_subscribers(self):
        """All subscribers should receive the event."""
        bus = EventBus()
        count = [0, 0, 0]

        for i in range(3):
            def cb(e, idx=i):
                count[idx] += 1
            bus.subscribe("topic", cb)

        handlers = bus.publish("topic")
        assert handlers == 3
        assert count == [1, 1, 1]

    def test_topic_isolation(self):
        """Subscribers only receive events for their topic."""
        bus = EventBus()
        topic_a = []
        topic_b = []

        bus.subscribe("a", lambda e: topic_a.append(e))
        bus.subscribe("b", lambda e: topic_b.append(e))

        bus.publish("a")
        bus.publish("a")

        assert len(topic_a) == 2
        assert len(topic_b) == 0

    def test_unsubscribe(self):
        """Unsubscribe should stop receiving events."""
        bus = EventBus()
        received = []

        sub_id = bus.subscribe("topic", lambda e: received.append(e))
        bus.publish("topic")
        assert len(received) == 1

        bus.unsubscribe(sub_id)
        bus.publish("topic")
        assert len(received) == 1  # Still 1

    def test_subscriber_exception_does_not_break_bus(self):
        """A crashing subscriber should not affect other subscribers."""
        bus = EventBus()
        good = []

        def crash(e):
            raise RuntimeError("boom")

        bus.subscribe("topic", crash)
        bus.subscribe("topic", lambda e: good.append(e))

        # Should not raise
        handlers = bus.publish("topic")
        assert handlers == 2
        assert len(good) == 1

    def test_recent_events_ring_buffer(self):
        """Recent events should be accessible."""
        bus = EventBus()
        for i in range(10):
            bus.publish("test", {"n": i})

        recent = bus.get_recent_events("test", limit=5)
        assert len(recent) == 5
        assert recent[-1].data["n"] == 9

    def test_recent_events_filtered_by_topic(self):
        """get_recent_events should filter by topic."""
        bus = EventBus()
        bus.publish("a", {"x": 1})
        bus.publish("b", {"x": 2})
        bus.publish("a", {"x": 3})

        a_events = bus.get_recent_events("a")
        assert len(a_events) == 2
        assert all(e.topic == "a" for e in a_events)

    def test_get_stats(self):
        """Stats should report topic and event counts."""
        bus = EventBus()
        bus.subscribe("alpha", lambda e: None)
        bus.subscribe("alpha", lambda e: None)
        bus.subscribe("beta", lambda e: None)
        bus.publish("alpha")
        bus.publish("alpha")
        bus.publish("beta")

        stats = bus.get_stats()
        assert stats["total_events"] == 3
        assert stats["topic_count"] == 2
        assert stats["active_topics"]["alpha"] == 2
        assert stats["active_topics"]["beta"] == 1

    def test_thread_safety(self):
        """EventBus should handle concurrent publish from multiple threads."""
        bus = EventBus()
        received = []
        bus.subscribe("t", lambda e: received.append(e))

        def publish_many(n):
            for i in range(n):
                bus.publish("t", {"thread": threading.get_ident()})

        threads = [threading.Thread(target=publish_many, args=(50,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(received) == 200

    def test_event_immutability(self):
        """Event should be frozen."""
        e = Event(topic="x", data={"a": 1})
        with pytest.raises(Exception):
            e.topic = "y"  # type: ignore[misc]

    def test_clear_resets_everything(self):
        """clear() should remove all subscribers and events."""
        bus = EventBus()
        received = []
        bus.subscribe("t", lambda e: received.append(e))
        bus.publish("t")
        assert len(received) == 1
        assert bus.get_stats()["total_events"] == 1

        bus.clear()
        # After clear: no subscribers, empty recent events
        assert bus.get_stats()["total_events"] == 0
        assert len(bus.get_recent_events()) == 0

        # Publish after clear — no subscribers, event count increments
        bus.publish("t")
        assert len(received) == 1  # Still 1 — no subscriber to receive it
        assert bus.get_stats()["total_events"] == 1  # One new event


# ═══════════════════════════════════════════════════════════════
# 2. WindowWatcher
# ═══════════════════════════════════════════════════════════════

class TestWindowWatcher:
    """Test the window polling and change detection."""

    def test_starts_and_stops(self):
        """Watcher should start and stop cleanly."""
        bus = EventBus()
        from perception.window_watcher import WindowWatcher

        w = WindowWatcher(event_bus=bus, interval=0.1)
        assert not w.is_running

        w.start()
        assert w.is_running

        w.stop()
        assert not w.is_running

    def test_publishes_on_window_change(self):
        """Should publish window.changed when window changes."""
        bus = EventBus()
        events = []
        bus.subscribe("window.changed", lambda e: events.append(e))

        from perception.window_watcher import WindowWatcher

        # Use mocked get_active_window to simulate window changes
        windows = [
            {"title": "app.py — Project", "process_name": "Code.exe", "hwnd": 1},
            {"title": "app.py — Project", "process_name": "Code.exe", "hwnd": 1},  # Same
            {"title": "Chrome — GitHub", "process_name": "chrome.exe", "hwnd": 2},
        ]
        call_count = [0]

        original = WindowWatcher.get_active_window
        def mock_get(self):
            if call_count[0] >= len(windows):
                self.stop()
                return None
            from perception.window_watcher import WindowInfo
            w = windows[call_count[0]]
            call_count[0] += 1
            return WindowInfo(**w)

        with mock.patch.object(WindowWatcher, 'get_active_window', mock_get):
            w = WindowWatcher(event_bus=bus, interval=0.05)
            w.start()
            time.sleep(0.3)
            w.stop()

        # First poll (hwnd=1) → change from None → publish
        # Second poll (hwnd=1) → no change → no publish
        # Third poll (hwnd=2) → change → publish
        assert len(events) >= 2, f"Expected at least 2 changes, got {len(events)}"

    def test_idle_detection(self):
        """Should publish window.idle after idle_threshold without changes."""
        bus = EventBus()
        idle_events = []
        bus.subscribe("window.idle", lambda e: idle_events.append(e))

        from perception.window_watcher import WindowWatcher, WindowInfo

        # Mock get_active_window to always return the SAME window
        fixed_window = WindowInfo(title="same", process_name="same.exe", hwnd=1)
        def mock_get(self):
            return fixed_window

        with mock.patch.object(WindowWatcher, 'get_active_window', mock_get):
            w = WindowWatcher(event_bus=bus, interval=0.05, idle_threshold=0.15)
            # Backdate last change so idle_threshold is exceeded immediately
            w._last_change_time = time.time() - 0.5
            w._last_window = fixed_window
            w._idle_published = False
            w.start()
            time.sleep(0.4)
            w.stop()

        assert len(idle_events) >= 1, f"Expected idle events, got {len(idle_events)}"

    def test_get_active_window_returns_none_without_win32(self):
        """get_active_window should return None when win32 unavailable."""
        from perception.window_watcher import WindowWatcher, HAS_WIN32

        bus = EventBus()
        w = WindowWatcher(event_bus=bus)

        if not HAS_WIN32:
            assert w.get_active_window() is None

    def test_window_to_dict_none(self):
        """_window_to_dict should return None for None input."""
        from perception.window_watcher import _window_to_dict
        assert _window_to_dict(None) is None

    def test_window_info_is_frozen(self):
        """WindowInfo should be immutable."""
        from perception.window_watcher import WindowInfo
        info = WindowInfo(title="Test", process_name="test.exe")
        with pytest.raises(Exception):
            info.title = "Changed"  # type: ignore[misc]

    def test_idle_seconds_increases(self):
        """idle_seconds should increase when window doesn't change."""
        bus = EventBus()
        from perception.window_watcher import WindowWatcher

        w = WindowWatcher(event_bus=bus)
        w._last_change_time = time.time() - 5.0
        assert w.idle_seconds >= 4.5


# ═══════════════════════════════════════════════════════════════
# 3. ClipboardWatcher
# ═══════════════════════════════════════════════════════════════

class TestClipboardWatcher:
    """Test clipboard polling and content categorization."""

    def test_starts_and_stops(self):
        """Watcher should start and stop cleanly."""
        bus = EventBus()
        from perception.clipboard_watcher import ClipboardWatcher

        cw = ClipboardWatcher(event_bus=bus, interval=0.1)
        cw.start()
        assert cw.is_running
        cw.stop()
        assert not cw.is_running

    def test_categorize_url(self):
        """URL detection."""
        from perception.clipboard_watcher import ClipboardWatcher, ClipboardCategory
        assert ClipboardWatcher.categorize("https://github.com") == ClipboardCategory.URL

    def test_categorize_email(self):
        """Email detection."""
        from perception.clipboard_watcher import ClipboardWatcher, ClipboardCategory
        assert ClipboardWatcher.categorize("user@example.com") == ClipboardCategory.EMAIL

    def test_categorize_path(self):
        """Path detection."""
        from perception.clipboard_watcher import ClipboardWatcher, ClipboardCategory
        assert ClipboardWatcher.categorize("C:\\Users\\test\\file.txt") == ClipboardCategory.PATH
        assert ClipboardWatcher.categorize("/home/user/file.txt") == ClipboardCategory.PATH

    def test_categorize_json(self):
        """JSON detection."""
        from perception.clipboard_watcher import ClipboardWatcher, ClipboardCategory
        assert ClipboardWatcher.categorize('{"key": "value"}') == ClipboardCategory.JSON
        assert ClipboardWatcher.categorize('[1, 2, 3]') == ClipboardCategory.JSON

    def test_categorize_number(self):
        """Number detection."""
        from perception.clipboard_watcher import ClipboardWatcher, ClipboardCategory
        assert ClipboardWatcher.categorize("12345.67") == ClipboardCategory.NUMBER
        assert ClipboardWatcher.categorize("-100") == ClipboardCategory.NUMBER

    def test_categorize_code(self):
        """Code detection."""
        from perception.clipboard_watcher import ClipboardWatcher, ClipboardCategory
        code = "def hello():\n    print('world')\n    return True"
        assert ClipboardWatcher.categorize(code) == ClipboardCategory.CODE

    def test_categorize_plain_text(self):
        """Plain text detection."""
        from perception.clipboard_watcher import ClipboardWatcher, ClipboardCategory
        assert ClipboardWatcher.categorize("Hello, how are you?") == ClipboardCategory.TEXT

    def test_categorize_empty(self):
        """Empty/whitespace should be UNKNOWN."""
        from perception.clipboard_watcher import ClipboardWatcher, ClipboardCategory
        assert ClipboardWatcher.categorize("") == ClipboardCategory.UNKNOWN
        assert ClipboardWatcher.categorize("   ") == ClipboardCategory.UNKNOWN

    def test_hash_based_dedup(self):
        """Same content hash should not re-publish."""
        bus = EventBus()
        events = []
        bus.subscribe("clipboard.changed", lambda e: events.append(e))

        from perception.clipboard_watcher import ClipboardWatcher

        cw = ClipboardWatcher(event_bus=bus, interval=0.1)
        # Simulate same content
        cw._last_hash = hash("same text")
        cw._poll_once()  # With no real clipboard, get_text returns None → no publish

        # Direct event injection test: same hash → skip
        cw._last_hash = hash("text A")
        # Mock get_text
        calls = ["text A", "text A", "text B"]
        call_idx = [0]

        original = cw.get_text
        def mock_get_text():
            if call_idx[0] < len(calls):
                val = calls[call_idx[0]]
                call_idx[0] += 1
                return val
            return None

        with mock.patch.object(cw, 'get_text', mock_get_text):
            cw._poll_once()  # text A → publish
            cw._poll_once()  # text A → skip (same hash)
            cw._poll_once()  # text B → publish

        assert len(events) == 2

    def test_clipboard_snapshot_is_frozen(self):
        """ClipboardSnapshot should be immutable."""
        from perception.clipboard_watcher import ClipboardSnapshot, ClipboardCategory
        snap = ClipboardSnapshot(
            text="test", text_hash=123, length=4,
            category=ClipboardCategory.TEXT, has_newlines=False,
        )
        with pytest.raises(Exception):
            snap.text = "changed"  # type: ignore[misc]

    def test_get_history_returns_recent(self):
        """get_history should return recent snapshots."""
        bus = EventBus()
        from perception.clipboard_watcher import ClipboardWatcher

        cw = ClipboardWatcher(event_bus=bus)
        # Set _last_hash to something that won't match
        cw._last_hash = -1
        for i in range(5):
            with mock.patch.object(cw, 'get_text', return_value=f"text_{i}"):
                cw._poll_once()

        history = cw.get_history(limit=3)
        assert len(history) == 3, f"Expected 3 items in history, got {len(history)}"


# ═══════════════════════════════════════════════════════════════
# 4. FileWatcher
# ═══════════════════════════════════════════════════════════════

class TestFileWatcher:
    """Test filesystem event processing."""

    def test_starts_and_stops(self):
        """Watcher should start and stop cleanly."""
        bus = EventBus()
        from perception.file_watcher import FileWatcher

        fw = FileWatcher(event_bus=bus, paths=["."])
        fw.start()
        assert fw.is_running
        fw.stop()
        assert not fw.is_running

    def test_inject_event_publishes_to_bus(self):
        """Injecting an event should publish to EventBus."""
        bus = EventBus()
        events = []
        bus.subscribe("file.created", lambda e: events.append(e))

        from perception.file_watcher import FileWatcher, FileEvent

        fw = FileWatcher(event_bus=bus, paths=["."])
        fe = FileEvent(
            path="/tmp/test.py", event_type="created",
            is_directory=False, size=100, suffix=".py",
        )
        fw.inject_event(fe)
        assert len(events) == 1
        assert events[0].data["path"] == "/tmp/test.py"
        assert events[0].data["suffix"] == ".py"

    def test_debounce_duplicate_events(self):
        """Duplicate events within debounce window should be suppressed."""
        bus = EventBus()
        events = []
        bus.subscribe("file.modified", lambda e: events.append(e))

        from perception.file_watcher import FileWatcher, FileEvent

        fw = FileWatcher(event_bus=bus, paths=["."], debounce_seconds=1.0)
        fe = FileEvent(path="/tmp/x.py", event_type="modified", is_directory=False)

        fw.inject_event(fe)
        fw.inject_event(fe)  # Same within debounce → suppressed

        assert len(events) == 1

    def test_hidden_files_ignored(self):
        """Hidden files should be ignored by default."""
        bus = EventBus()
        from perception.file_watcher import FileWatcher

        fw = FileWatcher(event_bus=bus, paths=["."], ignore_hidden=True)
        assert fw._should_ignore("/tmp/.git/config") is True
        assert fw._should_ignore("/tmp/.hidden_file") is True
        assert fw._should_ignore("/tmp/normal/file.py") is False

    def test_hidden_files_not_ignored_when_disabled(self):
        """Hidden files should be included when ignore_hidden=False."""
        bus = EventBus()
        from perception.file_watcher import FileWatcher

        fw = FileWatcher(event_bus=bus, paths=["."], ignore_hidden=False)
        assert fw._should_ignore("/tmp/.git/config") is False

    def test_get_recent_events_filtered(self):
        """get_recent_events should filter by event type."""
        from perception.file_watcher import FileWatcher, FileEvent

        bus = EventBus()
        fw = FileWatcher(event_bus=bus, paths=["."])

        fw.inject_event(FileEvent(path="/a", event_type="created", is_directory=False))
        fw.inject_event(FileEvent(path="/b", event_type="modified", is_directory=False))
        fw.inject_event(FileEvent(path="/c", event_type="deleted", is_directory=False))

        created = fw.get_recent_events(event_type="created")
        assert len(created) == 1
        assert created[0].path == "/a"

    def test_watch_paths_property(self):
        """watch_paths should return configured paths."""
        bus = EventBus()
        from perception.file_watcher import FileWatcher

        fw = FileWatcher(event_bus=bus, paths=["/a", "/b"])
        paths = fw.watch_paths
        assert len(paths) == 2

    def test_file_event_is_frozen(self):
        """FileEvent should be immutable."""
        from perception.file_watcher import FileEvent
        fe = FileEvent(path="/tmp", event_type="created", is_directory=True)
        with pytest.raises(Exception):
            fe.path = "changed"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════
# 5. ActivityTracker
# ═══════════════════════════════════════════════════════════════

class TestActivityTracker:
    """Test activity state tracking."""

    def test_starts_and_stops(self):
        """Tracker should start and stop cleanly."""
        bus = EventBus()
        from perception.activity_tracker import ActivityTracker

        at = ActivityTracker(event_bus=bus)
        at.start()
        assert at.is_running
        at.stop()
        assert not at.is_running

    def test_initial_state_is_active(self):
        """Initial state should be ACTIVE."""
        bus = EventBus()
        from perception.activity_tracker import ActivityTracker, ActivityState

        at = ActivityTracker(event_bus=bus)
        assert at.state == ActivityState.ACTIVE
        assert at.idle_seconds >= 0

    def test_record_window_change(self):
        """Recording window changes should update stats."""
        bus = EventBus()
        from perception.activity_tracker import ActivityTracker

        at = ActivityTracker(event_bus=bus)
        at.record_window_change("Code.exe")
        at.record_window_change("Code.exe")
        at.record_window_change("chrome.exe")

        top = at.get_top_apps(limit=2)
        assert top[0][0] == "Code.exe"
        assert top[0][1] == 2.0
        assert top[1][0] == "chrome.exe"

    def test_get_state_snapshot(self):
        """get_state should return current activity snapshot."""
        bus = EventBus()
        from perception.activity_tracker import ActivityTracker, ActivityState

        at = ActivityTracker(event_bus=bus)
        snap = at.get_state()
        assert snap.state == ActivityState.ACTIVE
        assert snap.sessions_today == 0

    def test_state_transitions_with_mocked_idle(self):
        """Simulated idle should trigger state transitions."""
        bus = EventBus()
        active_events = []
        idle_events = []
        bus.subscribe("activity.active", lambda e: active_events.append(e))
        bus.subscribe("activity.idle", lambda e: idle_events.append(e))

        from perception.activity_tracker import ActivityTracker, ActivityState

        at = ActivityTracker(
            event_bus=bus,
            idle_threshold=1.0,       # Very short for testing
            away_threshold=30.0,      # Far away
            pulse_interval=0.1,
        )

        # Patch idle_seconds to simulate going idle
        idle_values = [0.0, 0.0, 1.5, 1.5, 0.5]
        idle_idx = [0]
        original = type(at).idle_seconds
        def mock_idle(self):
            if idle_idx[0] < len(idle_values):
                val = idle_values[idle_idx[0]]
                idle_idx[0] += 1
                return val
            return 0.0

        with mock.patch.object(ActivityTracker, 'idle_seconds', property(mock_idle)):
            at.start()
            time.sleep(0.8)
            at.stop()

        assert len(idle_events) >= 1  # Should have detected idle

    def test_get_top_apps_empty(self):
        """get_top_apps should return empty list when no data."""
        bus = EventBus()
        from perception.activity_tracker import ActivityTracker

        at = ActivityTracker(event_bus=bus)
        assert at.get_top_apps() == []

    def test_activity_snapshot_is_frozen(self):
        """ActivitySnapshot should be immutable."""
        from perception.activity_tracker import ActivitySnapshot, ActivityState
        snap = ActivitySnapshot(
            state=ActivityState.ACTIVE, active_seconds=10.0,
            idle_seconds=0.0, total_active_today=3600.0, sessions_today=3,
        )
        with pytest.raises(Exception):
            snap.state = ActivityState.IDLE  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════
# 6. UserModel
# ═══════════════════════════════════════════════════════════════

class TestUserModel:
    """Test the user mental model."""

    def test_default_model(self):
        """Default model should have sensible defaults."""
        from perception.user_model import UserModel
        m = UserModel()
        assert m.work_start_hour == 9.0
        assert m.work_end_hour == 18.0
        assert m.confidence == 0.1
        assert m.total_observations == 0
        assert len(m.languages) == 0

    def test_serialization_roundtrip(self):
        """Model should survive to_dict → from_dict roundtrip."""
        from perception.user_model import UserModel
        m = UserModel(
            primary_language="python",
            languages=("python", "typescript"),
            primary_editor="vscode",
            context_switch_frequency=12.5,
            confidence=0.45,
            total_observations=200,
        )
        d = m.to_dict()
        m2 = UserModel.from_dict(d)
        assert m2.primary_language == "python"
        assert m2.languages == ("python", "typescript")
        assert m2.primary_editor == "vscode"
        assert m2.confidence == 0.45
        assert m2.total_observations == 200

    def test_save_and_load_from_disk(self):
        """Model should persist to and load from JSON."""
        from perception.user_model import UserModel, UserModelUpdater
        bus = EventBus()
        updater = UserModelUpdater(event_bus=bus)

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "user_model.json"
            updater.save_to_disk(path)
            assert path.exists()

            # Load into a new updater
            updater2 = UserModelUpdater(event_bus=EventBus())
            ok = updater2.load_from_disk(path)
            assert ok
            assert updater2.get_model().work_start_hour == 9.0

    def test_load_nonexistent_returns_false(self):
        """Loading a nonexistent file should return False."""
        from perception.user_model import UserModelUpdater
        bus = EventBus()
        updater = UserModelUpdater(event_bus=bus)
        assert updater.load_from_disk(Path("/nonexistent/path.json")) is False

    def test_reset_clears_model(self):
        """Reset should return model to defaults."""
        from perception.user_model import UserModelUpdater
        bus = EventBus()
        updater = UserModelUpdater(event_bus=bus)

        # Update model through events
        updater._language_detections["python"] = 10
        updater._model = updater._model.__class__(
            **{**updater._model.__dict__,
               "primary_language": "python",
               "confidence": 0.8,
               "total_observations": 100,
            }
        )

        updater.reset()
        m = updater.get_model()
        assert m.confidence == 0.1
        assert m.total_observations == 0
        assert m.primary_language == ""

    def test_model_is_immutable(self):
        """UserModel should be frozen."""
        from perception.user_model import UserModel
        m = UserModel()
        with pytest.raises(Exception):
            m.primary_language = "python"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════
# 7. UserModelUpdater — Event-Driven Updates
# ═══════════════════════════════════════════════════════════════

class TestUserModelUpdater:
    """Test the updater responds correctly to events."""

    def test_starts_and_stops(self):
        """Updater should subscribe and unsubscribe cleanly."""
        bus = EventBus()
        from perception.user_model import UserModelUpdater

        updater = UserModelUpdater(event_bus=bus)
        updater.start()
        stats = bus.get_stats()
        assert stats["topic_count"] >= 4  # Subscribed to multiple topics
        updater.stop()
        stats2 = bus.get_stats()
        # After unsubscribe, active topics should be 0
        assert sum(stats2.get("active_topics", {}).values()) == 0

    def test_window_change_updates_model(self):
        """Window change events should update app usage and context switch rate."""
        bus = EventBus()
        from perception.user_model import UserModelUpdater

        updater = UserModelUpdater(event_bus=bus, learning_rate=0.5)
        updater.start()

        # Simulate window changes
        bus.publish("window.changed", {
            "current": {"title": "app.py — MyProject", "process_name": "Code.exe"},
            "previous": None,
        })
        bus.publish("window.changed", {
            "current": {"title": "Chrome", "process_name": "chrome.exe"},
            "previous": {"title": "app.py — MyProject", "process_name": "Code.exe"},
        })
        bus.publish("window.changed", {
            "current": {"title": "test.py — MyProject", "process_name": "Code.exe"},
            "previous": {"title": "Chrome", "process_name": "chrome.exe"},
        })

        model = updater.get_model()
        assert model.total_observations >= 3
        assert model.primary_editor == "vscode"
        assert "vscode" in [app for app, _ in model.top_apps] or \
               model.top_apps  # At least some app data
        updater.stop()

    def test_detects_language_from_clipboard_code(self):
        """Clipboard code should trigger language detection."""
        bus = EventBus()
        from perception.user_model import UserModelUpdater

        updater = UserModelUpdater(event_bus=bus, learning_rate=1.0)
        updater.start()

        # Simulate copying Python code
        python_code = """
        def hello_world():
            import os
            class MyClass:
                def __init__(self):
                    self.name = "test"
        """
        bus.publish("clipboard.text", {
            "text": python_code,
            "length": len(python_code),
            "category": "code",
        })

        model = updater.get_model()
        assert "python" in model.languages, f"Expected python in {model.languages}"
        updater.stop()

    def test_detects_language_from_file_suffix(self):
        """File modification events should trigger language detection by suffix."""
        bus = EventBus()
        from perception.user_model import UserModelUpdater

        updater = UserModelUpdater(event_bus=bus, learning_rate=1.0)
        updater.start()

        bus.publish("file.modified", {
            "path": "/project/main.rs",
            "suffix": ".rs",
        })
        bus.publish("file.modified", {
            "path": "/project/main.rs",
            "suffix": ".rs",
        })

        model = updater.get_model()
        assert "rust" in model.languages, f"Expected rust in {model.languages}"
        updater.stop()

    def test_ema_update_smoothing(self):
        """EMA should smooth updates rather than jump to extremes."""
        from perception.user_model import UserModelUpdater
        bus = EventBus()
        updater = UserModelUpdater(event_bus=bus, learning_rate=0.1)

        # Direct EMA computation test
        result = updater._ema_update(old=0.0, new=100.0, rate=0.1)
        assert 0 < result < 100, f"EMA should smooth: {result}"
        assert abs(result - 10.0) < 0.01, f"EMA(0, 100, 0.1) should be 10.0, got {result}"

        # Test that EMA approaches target over multiple iterations
        val = 0.0
        for _ in range(50):
            val = updater._ema_update(val, 100.0, rate=0.1)
        assert val > 99.0, f"After 50 iterations, should approach 100, got {val}"

        updater.stop()

    def test_suffix_to_language_mapping(self):
        """File suffix to language mapping should be correct."""
        from perception.user_model import _suffix_to_language

        assert _suffix_to_language(".py") == "python"
        assert _suffix_to_language(".ts") == "typescript"
        assert _suffix_to_language(".rs") == "rust"
        assert _suffix_to_language(".go") == "go"
        assert _suffix_to_language(".js") == "javascript"
        assert _suffix_to_language(".java") == "java"
        assert _suffix_to_language(".cpp") == "cpp"
        assert _suffix_to_language(".sql") == "sql"
        assert _suffix_to_language(".unknown") is None

    def test_language_detection_from_text(self):
        """Should detect programming language from code text."""
        from perception.user_model import UserModelUpdater

        bus = EventBus()
        updater = UserModelUpdater(event_bus=bus)

        assert updater._detect_language("def foo():\n    import os\n    class Bar:") == "python"
        assert updater._detect_language("function foo() {\n    const x = 1;\n    let y = 2;\n}") == "javascript"
        assert updater._detect_language("fn main() {\n    let mut x = 1;\n    impl Foo {\n}") == "rust"

        # Not enough markers
        assert updater._detect_language("hello world") is None


# ═══════════════════════════════════════════════════════════════
# 8. Integration — Sensor → UserModel Pipeline
# ═══════════════════════════════════════════════════════════════

class TestPerceptionIntegration:
    """End-to-end: perception events flowing through to user model."""

    def test_window_to_user_model_pipeline(self):
        """WindowWatcher events → EventBus → UserModelUpdater → model update."""
        bus = EventBus()

        from perception.user_model import UserModelUpdater
        from perception.activity_tracker import ActivityTracker

        updater = UserModelUpdater(event_bus=bus, learning_rate=0.5)
        tracker = ActivityTracker(event_bus=bus)

        updater.start()
        tracker.start()

        # Simulate a work session: VS Code → browser → VS Code
        for i in range(5):
            bus.publish("window.changed", {
                "current": {"title": f"file{i}.py — Project", "process_name": "Code.exe"},
                "previous": None,
            })

        bus.publish("window.changed", {
            "current": {"title": "GitHub — Chrome", "process_name": "chrome.exe"},
            "previous": {"title": "file4.py — Project", "process_name": "Code.exe"},
        })

        model = updater.get_model()
        assert model.total_observations > 0
        assert model.primary_editor == "vscode"
        # top_apps uses raw process names, not normalized editor names
        top_app_names = [app for app, _ in model.top_apps]
        assert "Code.exe" in top_app_names, f"Expected Code.exe in {top_app_names}"

        tracker.stop()
        updater.stop()

    def test_file_events_detect_project(self):
        """File modifications should populate active projects."""
        bus = EventBus()
        from perception.user_model import UserModelUpdater

        updater = UserModelUpdater(event_bus=bus, learning_rate=1.0)
        updater.start()

        # Simulate file edits
        bus.publish("file.modified", {
            "path": "C:/projects/myapp/src/main.py",
            "suffix": ".py",
        })
        bus.publish("file.modified", {
            "path": "C:/projects/myapp/tests/test_main.py",
            "suffix": ".py",
        })

        model = updater.get_model()
        assert "python" in model.languages
        updater.stop()

    def test_concurrent_perception_modules(self):
        """All perception modules should coexist without conflicts."""
        bus = EventBus()

        from perception.window_watcher import WindowWatcher
        from perception.clipboard_watcher import ClipboardWatcher
        from perception.file_watcher import FileWatcher
        from perception.activity_tracker import ActivityTracker
        from perception.user_model import UserModelUpdater

        # Create all modules
        ww = WindowWatcher(event_bus=bus, interval=0.5)
        cw = ClipboardWatcher(event_bus=bus, interval=0.5)
        fw = FileWatcher(event_bus=bus, paths=["."])
        at = ActivityTracker(event_bus=bus)
        up = UserModelUpdater(event_bus=bus)

        # Start all
        ww.start()
        cw.start()
        fw.start()
        at.start()
        up.start()

        time.sleep(0.5)  # Let them run briefly

        # All should be running
        assert ww.is_running
        assert cw.is_running
        assert fw.is_running
        assert at.is_running

        # Inject a file event to ensure pipeline works
        from perception.file_watcher import FileEvent
        fw.inject_event(FileEvent(
            path="/test/file.py", event_type="created",
            is_directory=False, suffix=".py",
        ))

        # Stop all
        ww.stop()
        cw.stop()
        fw.stop()
        at.stop()
        up.stop()

        # All should have stopped
        assert not ww.is_running
        assert not cw.is_running
        assert not fw.is_running
        assert not at.is_running

    def test_sensor_data_accumulates_in_model(self):
        """After N observations, model confidence should increase."""
        bus = EventBus()
        from perception.user_model import UserModelUpdater

        updater = UserModelUpdater(event_bus=bus, learning_rate=0.5)
        updater.start()

        initial_confidence = updater.get_model().confidence

        # 20 window change events
        for i in range(20):
            bus.publish("window.changed", {
                "current": {"title": f"File{i}.py — Proj", "process_name": "Code.exe"},
                "previous": None,
            })

        model = updater.get_model()
        assert model.confidence > initial_confidence
        assert model.total_observations >= 20
        updater.stop()

    def test_user_model_save_load_end_to_end(self):
        """Full cycle: build model → save → load → verify."""
        bus = EventBus()
        from perception.user_model import UserModelUpdater

        updater = UserModelUpdater(event_bus=bus, learning_rate=1.0)
        updater.start()

        # Build some model data
        for i in range(10):
            bus.publish("window.changed", {
                "current": {"title": f"code{i}.py", "process_name": "Code.exe"},
                "previous": None,
            })

        bus.publish("clipboard.text", {
            "text": "def foo():\n    import sys\n    class Bar:\n        pass",
            "length": 50, "category": "code",
        })

        model_before = updater.get_model()
        updater.stop()

        # Save
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "model.json"
            updater.save_to_disk(path)

            # Load into new updater
            updater2 = UserModelUpdater(event_bus=EventBus())
            ok = updater2.load_from_disk(path)
            assert ok

            model_after = updater2.get_model()
            assert model_after.primary_editor == model_before.primary_editor
            assert model_after.total_observations == model_before.total_observations
            assert len(model_after.languages) == len(model_before.languages)
