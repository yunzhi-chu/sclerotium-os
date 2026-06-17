"""Window Watcher — monitors the active window and running processes.

Publishes events:
  window.changed  — user switched to a different window
  window.idle     — no window change for N seconds
"""

from __future__ import annotations

import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Any

from kernel.event_bus import EventBus

logger = logging.getLogger("sclerotium.perception.window")

# Try Windows API — graceful fallback for testing
try:
    import win32gui
    import win32process
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


@dataclass(frozen=True)
class WindowInfo:
    """Immutable snapshot of the active window."""
    title: str
    process_name: str
    exe_path: str = ""
    hwnd: int = 0
    timestamp: float = field(default_factory=time.time)


class WindowWatcher:
    """Periodically polls the active window and publishes changes to EventBus.

    Usage:
        bus = EventBus()
        watcher = WindowWatcher(event_bus=bus, interval=2.0)
        watcher.start()
        # ... later ...
        watcher.stop()
    """

    # Topics published by this watcher
    TOPIC_CHANGED = "window.changed"
    TOPIC_IDLE = "window.idle"

    def __init__(
        self,
        event_bus: EventBus,
        interval: float = 2.0,
        idle_threshold: float = 300.0,  # 5 minutes = idle
    ) -> None:
        self._bus = event_bus
        self._interval = interval
        self._idle_threshold = idle_threshold
        self._thread: threading.Thread | None = None
        self._running: bool = False
        self._last_window: WindowInfo | None = None
        self._last_change_time: float = time.time()
        self._idle_published: bool = False

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def start(self) -> None:
        """Start polling in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="sclerotium-window-watcher",
            daemon=True,
        )
        self._thread.start()
        logger.info("Window watcher started (interval=%.1fs)", self._interval)

    def stop(self) -> None:
        """Stop the watcher thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._interval * 2)
        logger.info("Window watcher stopped")

    def get_active_window(self) -> WindowInfo | None:
        """Get the current active window. Returns None if unavailable."""
        if not HAS_WIN32:
            return None
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
                exe_path = proc.exe()
            except Exception:
                proc_name = f"pid:{pid}"
                exe_path = ""
            return WindowInfo(
                title=title,
                process_name=proc_name,
                exe_path=exe_path,
                hwnd=hwnd,
            )
        except Exception as e:
            logger.debug("Failed to get active window: %s", e)
            return None

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_window(self) -> WindowInfo | None:
        return self._last_window

    @property
    def idle_seconds(self) -> float:
        """Seconds since the last window change."""
        return time.time() - self._last_change_time

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                self._poll_once()
            except Exception as e:
                logger.warning("Poll error: %s", e)
            time.sleep(self._interval)

    def _poll_once(self) -> None:
        """Single poll iteration."""
        current = self.get_active_window()
        if current is None:
            return

        # Check if window changed
        if self._last_window is None:
            self._last_window = current
            self._last_change_time = time.time()
            self._bus.publish(
                self.TOPIC_CHANGED,
                data={
                    "previous": None,
                    "current": _window_to_dict(current),
                },
                source="WindowWatcher",
            )
            return

        if self._window_did_change(self._last_window, current):
            previous = _window_to_dict(self._last_window)
            self._last_window = current
            self._last_change_time = time.time()
            self._idle_published = False
            self._bus.publish(
                self.TOPIC_CHANGED,
                data={
                    "previous": previous,
                    "current": _window_to_dict(current),
                },
                source="WindowWatcher",
            )
            return

        # Check idle
        idle = self.idle_seconds
        if idle >= self._idle_threshold and not self._idle_published:
            self._idle_published = True
            self._bus.publish(
                self.TOPIC_IDLE,
                data={
                    "idle_seconds": idle,
                    "last_window": _window_to_dict(self._last_window),
                },
                source="WindowWatcher",
            )

    @staticmethod
    def _window_did_change(prev: WindowInfo, curr: WindowInfo) -> bool:
        """Check if the meaningful window identity changed."""
        if prev.hwnd != curr.hwnd:
            return True
        # Same hwnd but title changed (e.g., switching tabs in browser)
        if prev.title != curr.title:
            return True
        return False


def _window_to_dict(w: WindowInfo | None) -> dict[str, Any] | None:
    """Convert WindowInfo to a JSON-serializable dict."""
    if w is None:
        return None
    return {
        "title": w.title,
        "process_name": w.process_name,
        "exe_path": w.exe_path,
        "hwnd": w.hwnd,
        "timestamp": w.timestamp,
    }
