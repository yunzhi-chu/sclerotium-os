"""Activity Tracker — monitors user activity and idle time.

Publishes events:
  activity.active     — user is actively using the computer
  activity.idle       — user has been idle for a threshold
  activity.returned   — user returned after idle period
  activity.session    — session summary (when going idle or shutdown)
"""

from __future__ import annotations

import threading
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from kernel.event_bus import EventBus

logger = logging.getLogger("sclerotium.perception.activity")

# Try Windows API for last input time
try:
    import ctypes
    from ctypes import wintypes

    def _get_last_input_seconds() -> float:
        """Get seconds since last user input (keyboard/mouse)."""
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [
                ('cbSize', wintypes.UINT),
                ('dwTime', wintypes.DWORD),
            ]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        tick_count = ctypes.windll.kernel32.GetTickCount()
        return (tick_count - lii.dwTime) / 1000.0

    HAS_LASTINPUT = True
except Exception:
    HAS_LASTINPUT = False
    def _get_last_input_seconds() -> float:
        return 0.0


class ActivityState(Enum):
    """User activity states."""
    ACTIVE = "active"
    IDLE = "idle"
    AWAY = "away"  # Long idle
    RETURNED = "returned"


@dataclass(frozen=True)
class ActivitySession:
    """Immutable summary of an activity session."""
    started_at: float
    ended_at: float
    duration_seconds: float
    idle_count: int
    total_idle_seconds: float
    active_apps: tuple[str, ...]  # Top apps used
    windows_switched: int


@dataclass(frozen=True)
class ActivitySnapshot:
    """Immutable snapshot of current activity state."""
    state: ActivityState
    active_seconds: float  # Seconds since last state change
    idle_seconds: float    # Current idle time (0 if active)
    total_active_today: float
    sessions_today: int


class ActivityTracker:
    """Tracks user activity patterns and publishes state changes to EventBus.

    Usage:
        bus = EventBus()
        tracker = ActivityTracker(event_bus=bus)
        tracker.start()
    """

    TOPIC_ACTIVE = "activity.active"
    TOPIC_IDLE = "activity.idle"
    TOPIC_RETURNED = "activity.returned"
    TOPIC_SESSION = "activity.session"

    def __init__(
        self,
        event_bus: EventBus,
        idle_threshold: float = 120.0,     # 2 minutes → idle
        away_threshold: float = 900.0,      # 15 minutes → away
        pulse_interval: float = 5.0,        # Check every 5 seconds
    ) -> None:
        self._bus = event_bus
        self._idle_threshold = idle_threshold
        self._away_threshold = away_threshold
        self._pulse_interval = pulse_interval

        self._thread: threading.Thread | None = None
        self._running: bool = False

        # State
        self._state: ActivityState = ActivityState.ACTIVE
        self._state_changed_at: float = time.time()
        self._session_start: float = time.time()
        self._idle_count: int = 0
        self._total_idle_seconds: float = 0.0
        self._windows_switched: int = 0
        self._idle_start: float = 0.0
        self._active_apps: dict[str, float] = {}  # app_name → total_seconds

        # Daily stats
        self._total_active_today: float = 0.0
        self._sessions_today: int = 0
        self._daily_reset_time: float = time.time()

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def start(self) -> None:
        """Start tracking in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._pulse_loop,
            name="sclerotium-activity-tracker",
            daemon=True,
        )
        self._thread.start()
        logger.info("Activity tracker started")

    def stop(self) -> None:
        """Stop tracking."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._pulse_interval * 2)
        logger.info("Activity tracker stopped")

    def record_window_change(self, app_name: str) -> None:
        """Record that the user switched to a new window."""
        self._windows_switched += 1
        self._active_apps[app_name] = self._active_apps.get(app_name, 0) + 1

    def get_state(self) -> ActivitySnapshot:
        """Get current activity state."""
        return ActivitySnapshot(
            state=self._state,
            active_seconds=time.time() - self._state_changed_at,
            idle_seconds=self.idle_seconds,
            total_active_today=self._total_active_today,
            sessions_today=self._sessions_today,
        )

    def get_top_apps(self, limit: int = 10) -> list[tuple[str, float]]:
        """Get the most-used applications."""
        sorted_apps = sorted(
            self._active_apps.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_apps[:limit]

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def state(self) -> ActivityState:
        return self._state

    @property
    def idle_seconds(self) -> float:
        """Current idle time. Uses real system idle time when available."""
        if HAS_LASTINPUT:
            return _get_last_input_seconds()
        return time.time() - self._state_changed_at

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _pulse_loop(self) -> None:
        """Main pulse loop."""
        while self._running:
            try:
                self._pulse_once()
            except Exception as e:
                logger.warning("Activity pulse error: %s", e)
            time.sleep(self._pulse_interval)

    def _pulse_once(self) -> None:
        """Single pulse iteration."""
        # Reset daily counters at midnight
        self._maybe_reset_daily()

        idle = self.idle_seconds
        prev_state = self._state

        if idle >= self._away_threshold and self._state != ActivityState.AWAY:
            self._transition_to(ActivityState.AWAY, idle)
        elif idle >= self._idle_threshold and self._state == ActivityState.ACTIVE:
            self._transition_to(ActivityState.IDLE, idle)
        elif idle < self._idle_threshold and self._state in (
            ActivityState.IDLE, ActivityState.AWAY, ActivityState.RETURNED
        ):
            self._transition_to(ActivityState.ACTIVE, idle)

    def _transition_to(self, new_state: ActivityState, idle: float) -> None:
        """Transition to a new activity state."""
        old_state = self._state
        now = time.time()
        duration = now - self._state_changed_at

        # Track idle stats
        if old_state in (ActivityState.IDLE, ActivityState.AWAY):
            self._total_idle_seconds += duration

        if old_state == ActivityState.ACTIVE:
            self._total_active_today += duration

        self._state = new_state
        self._state_changed_at = now

        # Publish events
        if new_state == ActivityState.ACTIVE and old_state != ActivityState.ACTIVE:
            self._bus.publish(
                self.TOPIC_ACTIVE,
                data={"idle_duration": duration},
                source="ActivityTracker",
            )
            if old_state in (ActivityState.IDLE, ActivityState.AWAY):
                self._bus.publish(
                    self.TOPIC_RETURNED,
                    data={"away_duration": duration, "from_state": old_state.value},
                    source="ActivityTracker",
                )

        elif new_state == ActivityState.IDLE:
            self._idle_start = now
            self._idle_count += 1
            self._bus.publish(
                self.TOPIC_IDLE,
                data={"idle_seconds": idle},
                source="ActivityTracker",
            )

        elif new_state == ActivityState.AWAY:
            # End of session
            session = self._end_session(now)
            self._bus.publish(
                self.TOPIC_SESSION,
                data={
                    "duration": session.duration_seconds,
                    "idle_count": session.idle_count,
                    "windows_switched": session.windows_switched,
                },
                source="ActivityTracker",
            )

        logger.debug("Activity: %s → %s (idle=%.0fs)", old_state.value, new_state.value, idle)

    def _end_session(self, now: float) -> ActivitySession:
        """End the current activity session and start a new one."""
        top_apps = tuple(
            app for app, _ in sorted(
                self._active_apps.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5]
        )
        session = ActivitySession(
            started_at=self._session_start,
            ended_at=now,
            duration_seconds=now - self._session_start,
            idle_count=self._idle_count,
            total_idle_seconds=self._total_idle_seconds,
            active_apps=top_apps,
            windows_switched=self._windows_switched,
        )
        # Reset for new session
        self._session_start = now
        self._idle_count = 0
        self._total_idle_seconds = 0.0
        self._windows_switched = 0
        self._sessions_today += 1
        return session

    def _maybe_reset_daily(self) -> None:
        """Reset daily counters if a new day has started."""
        now = time.time()
        # Check if it's been more than 24 hours since last reset
        if now - self._daily_reset_time > 86400:
            self._total_active_today = 0.0
            self._sessions_today = 0
            self._daily_reset_time = now
