"""Tests for event_bus module — async pub/sub with backpressure."""

from __future__ import annotations

import asyncio

import pytest

from src.core.event_bus import Event, EventBus


class TestEvent:
    def test_creation_defaults(self):
        evt = Event(topic="test.topic", data={"key": "val"})
        assert evt.topic == "test.topic"
        assert evt.data == {"key": "val"}
        assert evt.source_agent_id == ""
        assert evt.id != ""

    def test_creation_full(self):
        evt = Event(topic="a.b", data={"x": 1}, source_agent_id="agent-1")
        assert evt.source_agent_id == "agent-1"
        assert evt.timestamp > 0


class TestEventBus:
    @pytest.fixture
    def bus(self):
        return EventBus(max_backlog=100)

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, bus):
        received = []

        async def handler(topic, data):
            received.append((topic, data))

        bus.subscribe("test.topic", handler)
        await bus.start()
        await bus.publish_nowait("test.topic", {"msg": "hello"})
        await asyncio.sleep(0.15)
        await bus.stop()

        assert len(received) >= 1
        assert received[0][0] == "test.topic"
        assert received[0][1] == {"msg": "hello"}

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        received = []

        async def handler(topic, data):
            received.append(data)

        bus.subscribe("test.topic", handler)
        bus.unsubscribe("test.topic", handler)
        await bus.start()
        await bus.publish_nowait("test.topic", {"msg": "hello"})
        await asyncio.sleep(0.15)
        await bus.stop()

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_topic(self, bus):
        async def handler(topic, data):
            pass
        bus.unsubscribe("nonexistent", handler)  # Should not raise

    @pytest.mark.asyncio
    async def test_publish_direct(self, bus):
        evt = Event(topic="direct.topic", data={"x": 1})
        await bus.start()
        result = await bus.publish(evt)
        assert result is True

    @pytest.mark.asyncio
    async def test_publish_backpressure(self, bus):
        small_bus = EventBus(max_backlog=1)
        await small_bus.start()
        # Fill the queue
        await small_bus.publish(Event(topic="a", data={}))
        # Next publish should be dropped
        result = await small_bus.publish(Event(topic="b", data={}))
        assert result is False

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, bus):
        received = []

        async def handler(topic, data):
            received.append(topic)

        bus.subscribe("l6.*", handler)
        await bus.start()
        await bus.publish_nowait("l6.scan.complete", {})
        await bus.publish_nowait("l6.crystallized", {})
        await asyncio.sleep(0.15)
        await bus.stop()

        assert "l6.scan.complete" in received
        assert "l6.crystallized" in received

    @pytest.mark.asyncio
    async def test_exact_match_subscription(self, bus):
        received = []

        async def handler(topic, data):
            received.append(topic)

        bus.subscribe("exact.match", handler)
        await bus.start()
        await bus.publish_nowait("exact.match", {})
        await bus.publish_nowait("other.match", {})
        await asyncio.sleep(0.15)
        await bus.stop()

        assert received == ["exact.match"]

    @pytest.mark.asyncio
    async def test_stats(self, bus):
        await bus.start()
        await bus.publish_nowait("test", {"x": 1})
        await asyncio.sleep(0.15)
        s = bus.stats
        await bus.stop()

        assert s["event_count"] >= 1
        assert s["queue_size"] == 0

    @pytest.mark.asyncio
    async def test_multiple_handlers_same_topic(self, bus):
        received_a = []
        received_b = []

        async def handler_a(topic, data):
            received_a.append(data)

        async def handler_b(topic, data):
            received_b.append(data)

        bus.subscribe("shared.topic", handler_a)
        bus.subscribe("shared.topic", handler_b)
        await bus.start()
        await bus.publish_nowait("shared.topic", {"v": 1})
        await asyncio.sleep(0.15)
        await bus.stop()

        assert len(received_a) == 1
        assert len(received_b) == 1

    @pytest.mark.asyncio
    async def test_dispatch_handler_exception(self, bus):
        async def bad_handler(topic, data):
            raise RuntimeError("handler crash")

        bus.subscribe("crash.topic", bad_handler)
        await bus.start()
        await bus.publish_nowait("crash.topic", {})
        await asyncio.sleep(0.2)
        await bus.stop()
        # Should not crash the bus

    @pytest.mark.asyncio
    async def test_stop_without_start(self, bus):
        await bus.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_stop_clears_running(self, bus):
        await bus.start()
        assert bus._running is True
        await bus.stop()
        assert bus._running is False

    @pytest.mark.asyncio
    async def test_wildcard_mismatch_too_long(self, bus):
        """Wildcard pattern longer than topic+1 should not match."""
        received = []

        async def handler(topic, data):
            received.append(topic)

        # Subscribe with "a.b.c.*" — pattern has 4 parts
        bus.subscribe("a.b.c.*", handler)
        await bus.start()
        # Publish to "a.b" — only 2 parts, pattern is more than len(parts)+1
        await bus.publish_nowait("a.b", {"x": 1})
        await asyncio.sleep(0.15)
        await bus.stop()
        assert len(received) == 0  # Should NOT match

    @pytest.mark.asyncio
    async def test_wildcard_partial_match(self, bus):
        """Wildcard pattern with matching prefix should match."""
        received = []

        async def handler(topic, data):
            received.append(topic)

        bus.subscribe("l6.*", handler)
        await bus.start()
        await bus.publish_nowait("l6.scan", {"x": 1})
        await bus.publish_nowait("l5.scan", {"x": 2})  # different prefix
        await asyncio.sleep(0.15)
        await bus.stop()
        assert "l6.scan" in received
        assert "l5.scan" not in received
