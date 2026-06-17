"""Clipboard Watcher — monitors clipboard content changes.

Publishes events:
  clipboard.changed  — clipboard content has changed
  clipboard.text     — new text content (with category detection)
"""

from __future__ import annotations

import threading
import time
import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from kernel.event_bus import EventBus

logger = logging.getLogger("sclerotium.perception.clipboard")

# Try Windows clipboard API
try:
    import win32clipboard
    HAS_WIN32_CLIPBOARD = True
except ImportError:
    HAS_WIN32_CLIPBOARD = False


class ClipboardCategory(Enum):
    """Detected content category of clipboard text."""
    CODE = "code"
    URL = "url"
    EMAIL = "email"
    PATH = "path"
    JSON = "json"
    NUMBER = "number"
    TEXT = "text"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ClipboardSnapshot:
    """Immutable snapshot of clipboard content."""
    text: str
    text_hash: int
    length: int
    category: ClipboardCategory
    has_newlines: bool
    timestamp: float = field(default_factory=time.time)


class ClipboardWatcher:
    """Polls the clipboard and publishes changes to EventBus.

    Usage:
        bus = EventBus()
        watcher = ClipboardWatcher(event_bus=bus, interval=1.0)
        watcher.start()
    """

    TOPIC_CHANGED = "clipboard.changed"
    TOPIC_TEXT = "clipboard.text"

    # Content category detection patterns
    CATEGORY_PATTERNS: dict[ClipboardCategory, re.Pattern] = {
        ClipboardCategory.URL: re.compile(r'^https?://', re.IGNORECASE),
        ClipboardCategory.EMAIL: re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        ClipboardCategory.PATH: re.compile(r'^[A-Z]:\\|^~?/[a-zA-Z]|^\.{1,2}/'),
        ClipboardCategory.JSON: re.compile(r'^\s*[\{\[]'),
        ClipboardCategory.NUMBER: re.compile(r'^[\d.,\-+]+$'),
        ClipboardCategory.CODE: re.compile(
            r'(def |class |import |from |function |const |let |var |'
            r'#include|package |<?php|public class)',
            re.MULTILINE,
        ),
    }

    def __init__(
        self,
        event_bus: EventBus,
        interval: float = 1.0,
        max_text_length: int = 10000,
    ) -> None:
        self._bus = event_bus
        self._interval = interval
        self._max_text_length = max_text_length
        self._thread: threading.Thread | None = None
        self._running: bool = False
        self._last_hash: int = 0
        self._last_snapshot: ClipboardSnapshot | None = None
        self._snapshots: list[ClipboardSnapshot] = []  # Ring buffer

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
            name="sclerotium-clipboard-watcher",
            daemon=True,
        )
        self._thread.start()
        logger.info("Clipboard watcher started (interval=%.1fs)", self._interval)

    def stop(self) -> None:
        """Stop the watcher thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._interval * 2)
        logger.info("Clipboard watcher stopped")

    def get_text(self) -> str | None:
        """Get current clipboard text. Returns None if unavailable."""
        if not HAS_WIN32_CLIPBOARD:
            return None
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    return data[:self._max_text_length] if data else None
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            logger.debug("Clipboard read failed: %s", e)
        return None

    def get_history(self, limit: int = 20) -> list[ClipboardSnapshot]:
        """Get recent clipboard snapshots."""
        return self._snapshots[-limit:]

    # ═══════════════════════════════════════════════════════
    # Content Detection
    # ═══════════════════════════════════════════════════════

    @classmethod
    def categorize(cls, text: str) -> ClipboardCategory:
        """Detect the category of clipboard text."""
        if not text or not text.strip():
            return ClipboardCategory.UNKNOWN

        text_stripped = text.strip()

        # Check each pattern
        for category, pattern in cls.CATEGORY_PATTERNS.items():
            if pattern.search(text_stripped):
                return category

        # Heuristic: long text with punctuation → likely code
        if len(text_stripped) > 200 and _has_code_indicators(text_stripped):
            return ClipboardCategory.CODE

        return ClipboardCategory.TEXT

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_snapshot(self) -> ClipboardSnapshot | None:
        return self._last_snapshot

    @property
    def history_length(self) -> int:
        return len(self._snapshots)

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                self._poll_once()
            except Exception as e:
                logger.warning("Clipboard poll error: %s", e)
            time.sleep(self._interval)

    def _poll_once(self) -> None:
        """Single poll iteration."""
        text = self.get_text()
        if text is None:
            return

        text_hash = hash(text)
        if text_hash == self._last_hash:
            return  # No change

        self._last_hash = text_hash
        category = self.categorize(text)
        snapshot = ClipboardSnapshot(
            text=text,
            text_hash=text_hash,
            length=len(text),
            category=category,
            has_newlines="\n" in text,
        )
        self._last_snapshot = snapshot

        # Ring buffer
        self._snapshots.append(snapshot)
        if len(self._snapshots) > 100:
            self._snapshots = self._snapshots[-100:]

        # Publish events
        self._bus.publish(
            self.TOPIC_CHANGED,
            data={"length": len(text), "category": category.value},
            source="ClipboardWatcher",
        )
        self._bus.publish(
            self.TOPIC_TEXT,
            data={
                "text": text[:500],  # Truncate for event payload
                "length": len(text),
                "category": category.value,
                "is_truncated": len(text) > 500,
            },
            source="ClipboardWatcher",
        )


def _has_code_indicators(text: str) -> bool:
    """Check if text has common code indicators."""
    indicators = [
        ('{' in text and '}' in text),
        (';' in text and '\n' in text),
        ('def ' in text or 'function ' in text or 'class ' in text),
        ('import ' in text or 'from ' in text or 'require(' in text),
        ('=' in text and ('==' in text or '!=' in text)),
    ]
    return sum(indicators) >= 2
