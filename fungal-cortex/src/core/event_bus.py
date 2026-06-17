"""Async event bus with topic-based pub/sub and backpressure protection."""

from __future__ import annotations

import asyncio
import time as _time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from src.utils.logging import CortexLogger

EventHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class Event:
    """A single event on the bus."""

    topic: str
    data: dict[str, Any]
    source_agent_id: str = ""
    timestamp: float = field(default_factory=lambda: __import__("time").time())
    id: str = field(default_factory=lambda: str(__import__("uuid").uuid4()))


class EventBus:
    """Asynchronous topic-based publish/subscribe event bus.

    Supports wildcard subscriptions (e.g., 'l6.*' matches 'l6.scan.complete').
    Backpressure is handled by bounded queues that drop oldest events on overflow.
    """

    def __init__(self, max_backlog: int = 10000) -> None:
        self._subscriptions: dict[str, list[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max_backlog)
        self._max_backlog = max_backlog
        self._logger = CortexLogger("event_bus")
        self._running = False
        self._dispatch_task: asyncio.Task[None] | None = None
        self._event_count = 0
        self._dropped_count = 0
        self._history: list[dict[str, Any]] = []
        self._max_history = 5000

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Register a handler for a topic. Supports wildcard '*' suffix."""
        self._subscriptions[topic].append(handler)

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """Remove a specific handler from a topic."""
        handlers = self._subscriptions.get(topic, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: Event) -> bool:
        """Publish an event. Returns False if dropped due to backpressure."""
        try:
            self._queue.put_nowait(event)
            self._event_count += 1
            return True
        except asyncio.QueueFull:
            self._dropped_count += 1
            self._logger.warn("event_dropped", topic=event.topic, total_dropped=self._dropped_count)
            return False

    async def publish_nowait(self, topic: str, data: dict[str, Any], source: str = "") -> bool:
        """Convenience method to publish without constructing Event manually."""
        return await self.publish(Event(topic=topic, data=data, source_agent_id=source))

    async def start(self) -> None:
        """Start the dispatch loop."""
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        self._logger.info("event_bus_started", max_backlog=self._max_backlog)

    async def stop(self) -> None:
        """Stop the dispatch loop gracefully."""
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        self._logger.info("event_bus_stopped", total_events=self._event_count, dropped=self._dropped_count)

    async def _dispatch_loop(self) -> None:
        """Main dispatch loop — routes events to matching subscribers."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                # Store in history for audit
                record = {
                    "id": event.id,
                    "topic": event.topic,
                    "data": event.data,
                    "source": event.source_agent_id,
                    "timestamp": event.timestamp,
                    "parent_id": event.data.get("parent_id", ""),
                }
                self._history.append(record)
                if len(self._history) > self._max_history:
                    self._history = self._history[-self._max_history:]
                matched = self._matching_handlers(event.topic)
                tasks = [handler(event.topic, event.data) for handler in matched]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            except asyncio.TimeoutError:
                continue
            except Exception:
                self._logger.error("dispatch_error", topic=event.topic if "event" in dir() else "unknown")

    def _matching_handlers(self, topic: str) -> list[EventHandler]:
        """Return all handlers matching the topic (exact or wildcard)."""
        handlers: list[EventHandler] = []
        parts = topic.split(".")
        for pattern, h_list in self._subscriptions.items():
            pattern_parts = pattern.split(".")
            if len(pattern_parts) > len(parts) + 1:
                continue
            if pattern.endswith("*"):
                prefix = pattern_parts[:-1]
                if parts[:len(prefix)] == prefix:
                    handlers.extend(h_list)
            elif pattern == topic:
                handlers.extend(h_list)
        return handlers

    def get_history(
        self, limit: int = 100, filters: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        """Return filtered event history for audit purposes."""
        results = self._history
        if filters:
            filtered = []
            for record in results:
                match = True
                for key, val in filters.items():
                    if record.get(key) != val:
                        match = False
                        break
                if match:
                    filtered.append(record)
            results = filtered
        return results[-limit:]

    def get_causal_trace(self, event_id: str) -> list[dict[str, Any]]:
        """Build a causal trace chain for a given event ID."""
        trace = []
        current_id = event_id
        seen: set[str] = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            for record in self._history:
                if record.get("id") == current_id:
                    trace.append(record)
                    current_id = record.get("parent_id", "")
                    break
            else:
                break
        return trace

    @property
    def stats(self) -> dict[str, int]:
        return {"event_count": self._event_count, "subscriptions": len(self._subscriptions), "dropped": self._dropped_count, "queue_size": self._queue.qsize()}
