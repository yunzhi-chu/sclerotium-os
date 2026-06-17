"""Lightweight EventBus — the organism's nervous system.

A minimal pub/sub event bus for perception events and organ communication.
Can be swapped with fungal-cortex's full EventBus later via the same interface.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Event:
    """An immutable event that flows through the nervous system."""
    topic: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Lightweight thread-safe publish/subscribe event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)
        self._lock = threading.RLock()
        self._event_count: int = 0
        self._recent_events: list[Event] = []  # Ring buffer of last 200

    def subscribe(self, topic: str, callback: Callable[[Event], None]) -> str:
        """Subscribe to a topic. Returns a subscription ID for later unsubscribe."""
        sub_id = f"{topic}:{id(callback)}"
        with self._lock:
            self._subscribers[topic].append(callback)
        return sub_id

    def unsubscribe(self, sub_id: str) -> bool:
        """Unsubscribe using the ID returned by subscribe()."""
        topic = sub_id.rsplit(":", 1)[0]
        with self._lock:
            if topic in self._subscribers:
                before = len(self._subscribers[topic])
                self._subscribers[topic] = [
                    cb for cb in self._subscribers[topic]
                    if f"{topic}:{id(cb)}" != sub_id
                ]
                return len(self._subscribers[topic]) < before
        return False

    def publish(self, topic: str, data: dict[str, Any] | None = None,
                source: str = "") -> int:
        """Publish an event to all subscribers of the topic. Returns handler count."""
        event = Event(topic=topic, data=data or {}, source=source)
        self._event_count += 1

        # Ring buffer: keep last 200 events
        self._recent_events.append(event)
        if len(self._recent_events) > 200:
            self._recent_events = self._recent_events[-200:]

        handlers = []
        with self._lock:
            handlers = list(self._subscribers.get(topic, []))

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass  # One bad subscriber shouldn't break the bus

        return len(handlers)

    def get_recent_events(self, topic: str | None = None, limit: int = 50) -> list[Event]:
        """Get recent events, optionally filtered by topic."""
        events = self._recent_events
        if topic:
            events = [e for e in events if e.topic == topic]
        return events[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get bus statistics."""
        with self._lock:
            return {
                "total_events": self._event_count,
                "topic_count": len(self._subscribers),
                "active_topics": {
                    topic: len(handlers)
                    for topic, handlers in self._subscribers.items()
                    if handlers
                },
                "recent_events": len(self._recent_events),
            }

    def clear(self) -> None:
        """Clear all subscribers, events, and counter (for testing)."""
        with self._lock:
            self._subscribers.clear()
            self._recent_events.clear()
            self._event_count = 0
