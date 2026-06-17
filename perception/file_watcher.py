"""File Watcher — monitors filesystem changes.

Publishes events:
  file.created    — a new file was created
  file.modified   — a file was modified
  file.deleted    — a file was deleted
  file.moved      — a file was moved/renamed
"""

from __future__ import annotations

import threading
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kernel.event_bus import EventBus

logger = logging.getLogger("sclerotium.perception.file")

# watchdog is optional — watcher gracefully degrades without it
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False


@dataclass(frozen=True)
class FileEvent:
    """Immutable snapshot of a filesystem event."""
    path: str
    event_type: str  # created / modified / deleted / moved
    is_directory: bool
    size: int = 0
    suffix: str = ""
    src_path: str = ""  # For move events
    timestamp: float = field(default_factory=time.time)


class FileWatcher:
    """Watches directories for filesystem changes and publishes to EventBus.

    Usage:
        bus = EventBus()
        watcher = FileWatcher(event_bus=bus, paths=["~/projects"])
        watcher.start()
    """

    TOPIC_CREATED = "file.created"
    TOPIC_MODIFIED = "file.modified"
    TOPIC_DELETED = "file.deleted"
    TOPIC_MOVED = "file.moved"

    # Event type → topic mapping
    EVENT_TOPICS = {
        "created": TOPIC_CREATED,
        "modified": TOPIC_MODIFIED,
        "deleted": TOPIC_DELETED,
        "moved": TOPIC_MOVED,
    }

    def __init__(
        self,
        event_bus: EventBus,
        paths: list[str | Path] | None = None,
        patterns: list[str] | None = None,
        recursive: bool = True,
        ignore_hidden: bool = True,
        debounce_seconds: float = 0.5,
    ) -> None:
        self._bus = event_bus
        self._watch_paths = [Path(p).expanduser().resolve() for p in (paths or ["."])]
        self._patterns = patterns or ["*"]
        self._recursive = recursive
        self._ignore_hidden = ignore_hidden
        self._debounce = debounce_seconds

        self._observer: Any = None
        self._running: bool = False
        self._recent_events: list[FileEvent] = []
        self._events_lock = threading.Lock()

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def start(self) -> None:
        """Start watching filesystem changes."""
        if self._running:
            return

        self._running = True

        if HAS_WATCHDOG:
            self._observer = Observer()
            handler = _WatchdogHandler(self)
            for watch_path in self._watch_paths:
                if watch_path.exists():
                    self._observer.schedule(
                        handler,
                        str(watch_path),
                        recursive=self._recursive,
                    )
                    logger.info("Watching: %s", watch_path)
                else:
                    logger.warning("Path not found, skipping: %s", watch_path)
            self._observer.start()
            logger.info(
                "File watcher started — %d paths, recursive=%s",
                len(self._watch_paths), self._recursive,
            )
        else:
            logger.warning(
                "watchdog not installed. File watching is disabled. "
                "Install with: pip install watchdog"
            )

    def stop(self) -> None:
        """Stop watching."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None
        logger.info("File watcher stopped")

    def get_recent_events(self, event_type: str | None = None,
                          limit: int = 50) -> list[FileEvent]:
        """Get recent file events, optionally filtered by type."""
        with self._events_lock:
            events = list(self._recent_events)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def inject_event(self, event: FileEvent) -> None:
        """Manually inject a file event (for testing or programmatic use)."""
        self._on_file_event(event)

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def watch_paths(self) -> list[Path]:
        return list(self._watch_paths)

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored."""
        if self._ignore_hidden:
            parts = Path(path).parts
            for part in parts:
                if part.startswith('.'):
                    return True
        return False

    def _on_file_event(self, event: FileEvent) -> None:
        """Handle a filesystem event."""
        # Debounce: skip duplicate events within debounce window
        with self._events_lock:
            # Check for recent duplicate
            cutoff = time.time() - self._debounce
            for recent in reversed(self._recent_events):
                if recent.timestamp < cutoff:
                    break
                if (recent.path == event.path and
                        recent.event_type == event.event_type):
                    return  # Duplicate, skip

            self._recent_events.append(event)
            if len(self._recent_events) > 200:
                self._recent_events = self._recent_events[-200:]

        # Publish to EventBus
        topic = self.EVENT_TOPICS.get(event.event_type, "file.changed")
        self._bus.publish(
            topic,
            data={
                "path": event.path,
                "is_directory": event.is_directory,
                "size": event.size,
                "suffix": event.suffix,
                "src_path": event.src_path,
            },
            source="FileWatcher",
        )


# ═══════════════════════════════════════════════════════════
# Watchdog Handler
# ═══════════════════════════════════════════════════════════

if HAS_WATCHDOG:

    class _WatchdogHandler(FileSystemEventHandler):
        """Bridge from watchdog events to our FileWatcher."""

        def __init__(self, watcher: FileWatcher) -> None:
            super().__init__()
            self._watcher = watcher

        def _to_file_event(self, event: FileSystemEvent, event_type: str) -> FileEvent | None:
            """Convert a watchdog event to our FileEvent."""
            src_path = getattr(event, 'src_path', '')
            path = src_path if event_type == "moved" else event.src_path

            if self._watcher._should_ignore(path):
                return None

            size = 0
            suffix = ""
            is_dir = event.is_directory

            if not is_dir and event_type != "deleted":
                try:
                    p = Path(path)
                    if p.exists():
                        size = p.stat().st_size
                    suffix = p.suffix
                except Exception:
                    pass

            return FileEvent(
                path=path,
                event_type=event_type,
                is_directory=is_dir,
                size=size,
                suffix=suffix,
                src_path=getattr(event, 'dest_path', ''),
            )

        def on_created(self, event: FileSystemEvent) -> None:
            fe = self._to_file_event(event, "created")
            if fe:
                self._watcher._on_file_event(fe)

        def on_modified(self, event: FileSystemEvent) -> None:
            fe = self._to_file_event(event, "modified")
            if fe:
                self._watcher._on_file_event(fe)

        def on_deleted(self, event: FileSystemEvent) -> None:
            fe = self._to_file_event(event, "deleted")
            if fe:
                self._watcher._on_file_event(fe)

        def on_moved(self, event: FileSystemEvent) -> None:
            fe = self._to_file_event(event, "moved")
            if fe:
                self._watcher._on_file_event(fe)
