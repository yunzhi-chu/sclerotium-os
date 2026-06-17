"""L0-L5 UnifiedEventBus — "全身循环系统" 统一事件总线.

Biological Metaphor:
  循环系统(心血管+淋巴)——连接全身37万亿个细胞:
    血液: 运输氧气/营养/激素/免疫细胞/废物
    淋巴: 回收组织液+免疫监视
    没有一个细胞距离最近的毛细血管超过50μm

  我们映射:
    动脉 = 高优先级事件(CRITICAL), 如同主动脉直接供应大脑/心脏
    静脉 = 正常优先级事件(NORMAL), 常规回流
    毛细血管 = 低优先级事件(LOW), 弥漫到每个细胞
    淋巴管 = 事件历史持久化(SQLite), 如同淋巴回收+免疫监视
    骨髓 = SQLite backlog(防失血过多/造血干细胞储备)

  新增全局事件类型:
    L0.regime_change: 体制切换(如同肾上腺素激增的广播)
    L3.claim_resolved: 辩论解决(如同免疫应答完成信号)
    L4.task_completed: 任务完成(如同运动完成→肌肉放松)
    L5.agent_apoptosed: Agent凋亡(如同细胞凋亡信号)

  全局trace_id: 从用户查询→最终决策(如同血液循环追踪一个分子)
  优先级队列: CRITICAL>HIGH>NORMAL>LOW(如同血液优先供应脑/心脏)

Reference:
  Guyton & Hall (2020), "Textbook of Medical Physiology", Chapter 14-25;
  Event-driven architecture patterns (RabbitMQ/Kafka design)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable

from src.utils.logging import CortexLogger

EventHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


# ── Event Priority ────────────────────────────────────────────────────

class EventPriority(int, Enum):
    """Priority levels — like blood flow priority to organs."""
    CRITICAL = 0  # Brain/heart — must deliver immediately
    HIGH = 1      # Liver/kidneys — important
    NORMAL = 2    # Skeletal muscles — standard
    LOW = 3      # Adipose tissue — can wait


# ── Standard Cross-Layer Event Types ─────────────────────────────────

class StandardEventType(str, Enum):
    """Standard cross-layer event types — like hormone/neurotransmitter types."""
    # L0: Peripheral sensing + endocrine
    REGIME_CHANGE = "L0.regime_change"
    DRIFT_DETECTED = "L0.drift_detected"
    HORMONE_SIGNAL = "L0.hormone_signal"
    CIRCUIT_BREAKER_TRIP = "L0.circuit_breaker_trip"

    # L3: Immune debate
    CLAIM_RESOLVED = "L3.claim_resolved"
    DEBATE_COMPLETE = "L3.debate_complete"
    IMMUNE_MEMORY_STORED = "L3.immune_memory_stored"

    # L4: Autonomous middleware
    TASK_COMPLETED = "L4.task_completed"
    DAG_EXECUTED = "L4.dag_executed"
    AUDIT_RECORDED = "L4.audit_recorded"
    EVOLUTION_STEP = "L4.evolution_step"

    # L5: Cluster ecosystem
    AGENT_APOPTOSED = "L5.agent_apoptosed"
    AGENT_SPAWNED = "L5.agent_spawned"
    CONSENSUS_REACHED = "L5.consensus_reached"
    KNOWLEDGE_SYNCED = "L5.knowledge_synced"


# ── Data Classes ──────────────────────────────────────────────────────

@dataclass
class UnifiedEvent:
    """A cross-layer event — like a molecule in the bloodstream."""

    event_id: str
    topic: str
    data: dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    source_layer: str = ""  # L0/L3/L4/L5
    source_agent_id: str = ""
    trace_id: str = ""  # Global trace chain — follows from query to decision
    parent_event_id: str = ""  # For causal chain tracking
    timestamp: float = field(default_factory=time.time)
    ttl: int = 0  # Time-to-live in seconds, 0 = no expiry

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "topic": self.topic,
            "data": self.data,
            "priority": self.priority.name,
            "source_layer": self.source_layer,
            "source_agent_id": self.source_agent_id,
            "trace_id": self.trace_id,
            "parent_event_id": self.parent_event_id,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "UnifiedEvent":
        priority_raw = d.get("priority", "NORMAL")
        if isinstance(priority_raw, str):
            priority = EventPriority[priority_raw]
        else:
            priority = EventPriority(priority_raw)
        return cls(
            event_id=d["event_id"],
            topic=d["topic"],
            data=d.get("data", {}),
            priority=priority,
            source_layer=d.get("source_layer", ""),
            source_agent_id=d.get("source_agent_id", ""),
            trace_id=d.get("trace_id", ""),
            parent_event_id=d.get("parent_event_id", ""),
            timestamp=d.get("timestamp", time.time()),
            ttl=d.get("ttl", 0),
        )


# ── SQLite Backlog ────────────────────────────────────────────────────

class EventBacklogStore:
    """SQLite-backed event persistence — like bone marrow storing hematopoietic stem cells.

    Provides durable event storage that survives process restarts.
    """

    _instance: "EventBacklogStore | None" = None
    _lock = threading.Lock()

    def __init__(self, db_path: str = "data/event_backlog.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._initialized = False

    def _ensure_init(self) -> None:
        if self._initialized and self._conn:
            return
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                topic TEXT NOT NULL,
                data_json TEXT DEFAULT '{}',
                priority TEXT DEFAULT 'NORMAL',
                source_layer TEXT DEFAULT '',
                source_agent_id TEXT DEFAULT '',
                trace_id TEXT DEFAULT '',
                parent_event_id TEXT DEFAULT '',
                timestamp REAL NOT NULL,
                ttl INTEGER DEFAULT 0
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_trace ON events(trace_id)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_topic ON events(topic)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp)
        """)
        self._conn.commit()
        self._initialized = True

    def insert(self, event: UnifiedEvent) -> bool:
        self._ensure_init()
        try:
            assert self._conn is not None
            self._conn.execute(
                """INSERT OR IGNORE INTO events
                   (event_id, topic, data_json, priority, source_layer,
                    source_agent_id, trace_id, parent_event_id, timestamp, ttl)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id, event.topic,
                    json.dumps(event.data, ensure_ascii=False),
                    event.priority.name, event.source_layer,
                    event.source_agent_id, event.trace_id,
                    event.parent_event_id, event.timestamp, event.ttl,
                ),
            )
            self._conn.commit()
            return True
        except Exception:
            return False

    def query(self, limit: int = 100, trace_id: str = "",
              topic: str = "") -> list[dict[str, Any]]:
        self._ensure_init()
        assert self._conn is not None
        conditions: list[str] = []
        params: list[Any] = []
        if trace_id:
            conditions.append("trace_id = ?")
            params.append(trace_id)
        if topic:
            conditions.append("topic = ?")
            params.append(topic)
        where = " AND ".join(conditions) if conditions else "1=1"
        rows = self._conn.execute(
            f"SELECT * FROM events WHERE {where} ORDER BY timestamp DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        cols = ["id", "event_id", "topic", "data_json", "priority",
                "source_layer", "source_agent_id", "trace_id",
                "parent_event_id", "timestamp", "ttl"]
        results: list[dict[str, Any]] = []
        for row in rows:
            d = dict(zip(cols, row))
            d["data"] = json.loads(d.pop("data_json", "{}"))
            results.append(d)
        return results

    def get_trace_chain(self, trace_id: str) -> list[dict[str, Any]]:
        """Reconstruct the complete event chain for a trace_id."""
        self._ensure_init()
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT * FROM events WHERE trace_id = ? ORDER BY timestamp ASC",
            (trace_id,),
        ).fetchall()
        cols = ["id", "event_id", "topic", "data_json", "priority",
                "source_layer", "source_agent_id", "trace_id",
                "parent_event_id", "timestamp", "ttl"]
        results: list[dict[str, Any]] = []
        for row in rows:
            d = dict(zip(cols, row))
            d["data"] = json.loads(d.pop("data_json", "{}"))
            results.append(d)
        return results

    def count(self) -> int:
        self._ensure_init()
        assert self._conn is not None
        return self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def vacuum(self, before_timestamp: float) -> int:
        self._ensure_init()
        assert self._conn is not None
        cur = self._conn.execute(
            "DELETE FROM events WHERE timestamp < ?", (before_timestamp,)
        )
        self._conn.commit()
        return cur.rowcount

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


# ── Unified Event Bus ─────────────────────────────────────────────────

class UnifiedEventBus:
    """L0-L5 cross-layer event bus — the circulatory system of Fungal Cortex.

    Features over base EventBus:
      - Priority-based dispatch (CRITICAL first)
      - Standardized cross-layer event types (L0/L3/L4/L5)
      - Global trace_id for end-to-end causality tracking
      - SQLite persistent backlog (bone marrow analog)
      - TTL-based event expiry
      - Layer-specific subscription patterns
    """

    _DEFAULT_PRIORITY_MAP: dict[str, EventPriority] = {
        "L0.circuit_breaker_trip": EventPriority.CRITICAL,
        "L0.regime_change": EventPriority.HIGH,
        "L3.claim_resolved": EventPriority.HIGH,
        "L4.task_completed": EventPriority.NORMAL,
        "L5.agent_apoptosed": EventPriority.LOW,
    }

    def __init__(
        self,
        db_path: str = "data/event_backlog.db",
        max_queue: int = 20000,
        enable_persistence: bool = True,
        vacuum_interval: float = 86400.0,  # 24h
    ) -> None:
        # Priority queues — one per level
        self._queues: dict[EventPriority, asyncio.Queue[UnifiedEvent]] = {
            p: asyncio.Queue(maxsize=max_queue // 4) for p in EventPriority
        }
        self._max_queue = max_queue

        # Subscriptions: topic_pattern → [handlers]
        self._subscriptions: dict[str, list[EventHandler]] = defaultdict(list)

        # Persistence
        self._enable_persistence = enable_persistence
        self._backlog = EventBacklogStore(db_path) if enable_persistence else None
        self._vacuum_interval = vacuum_interval
        self._last_vacuum = time.time()

        # Runtime state
        self._running = False
        self._dispatch_task: asyncio.Task[None] | None = None
        self._event_count: dict[str, int] = defaultdict(int)
        self._dropped_count = 0
        self._in_memory_history: list[dict[str, Any]] = []
        self._max_history = 10000

        # Trace tracking
        self._active_traces: dict[str, list[str]] = defaultdict(list)  # trace_id → [event_ids]

        self._logger = CortexLogger("unified_event_bus")

    # ── Subscription Management ──────────────────────────────────────

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribe to a topic. Supports wildcard: 'L0.*', 'L4.*'."""
        self._subscriptions[topic].append(handler)

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        handlers = self._subscriptions.get(topic, [])
        if handler in handlers:
            handlers.remove(handler)

    def subscribe_layer(self, layer: str, handler: EventHandler) -> None:
        """Subscribe to all events from a specific layer (L0/L3/L4/L5)."""
        self._subscriptions[f"{layer}.*"].append(handler)

    # ── Publishing ────────────────────────────────────────────────────

    async def publish(self, event: UnifiedEvent) -> bool:
        """Publish a unified event with priority routing.

        Like the heart pumping blood into the appropriate artery.
        """
        # Auto-assign priority from topic if not explicitly set
        if event.priority == EventPriority.NORMAL:
            event.priority = self._DEFAULT_PRIORITY_MAP.get(event.topic, EventPriority.NORMAL)

        # Auto-derive source layer from topic
        if not event.source_layer:
            event.source_layer = event.topic.split(".")[0] if "." in event.topic else ""

        # Track trace
        if event.trace_id:
            self._active_traces[event.trace_id].append(event.event_id)

        queue = self._queues[event.priority]
        try:
            queue.put_nowait(event)
            self._event_count[event.priority.name] += 1

            # Persist to backlog
            if self._enable_persistence and self._backlog:
                self._backlog.insert(event)

            return True
        except asyncio.QueueFull:
            self._dropped_count += 1
            self._logger.warn(
                "event_dropped",
                topic=event.topic,
                priority=event.priority.name,
                total_dropped=self._dropped_count,
            )
            return False

    async def publish_quick(
        self,
        topic: str,
        data: dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "",
        trace_id: str = "",
        parent_id: str = "",
    ) -> bool:
        """Convenience method — publish without constructing event manually."""
        event = UnifiedEvent(
            event_id=_gen_event_id(topic),
            topic=topic,
            data=data,
            priority=priority,
            source_agent_id=source,
            trace_id=trace_id or _gen_trace_id(),
            parent_event_id=parent_id,
        )
        return await self.publish(event)

    async def publish_regime_change(
        self,
        from_regime: str,
        to_regime: str,
        confidence: float,
        source: str = "",
    ) -> bool:
        """Publish an L0 regime change event (like adrenaline surge)."""
        trace_id = _gen_trace_id()
        return await self.publish_quick(
            topic=StandardEventType.REGIME_CHANGE.value,
            data={
                "from_regime": from_regime,
                "to_regime": to_regime,
                "confidence": confidence,
            },
            priority=EventPriority.HIGH,
            source=source,
            trace_id=trace_id,
        )

    async def publish_claim_resolved(
        self,
        claim_id: str,
        verdict: str,
        net_price: float,
        trace_id: str = "",
    ) -> bool:
        """Publish an L3 claim resolution event."""
        return await self.publish_quick(
            topic=StandardEventType.CLAIM_RESOLVED.value,
            data={
                "claim_id": claim_id,
                "verdict": verdict,
                "net_price": net_price,
            },
            priority=EventPriority.HIGH,
            source="immune_debate",
            trace_id=trace_id,
        )

    async def publish_task_completed(
        self,
        task_id: str,
        dag_id: str,
        success: bool,
        trace_id: str = "",
    ) -> bool:
        """Publish an L4 task completion event."""
        return await self.publish_quick(
            topic=StandardEventType.TASK_COMPLETED.value,
            data={
                "task_id": task_id,
                "dag_id": dag_id,
                "success": success,
            },
            priority=EventPriority.NORMAL,
            source="autonomous",
            trace_id=trace_id,
        )

    async def publish_agent_apoptosed(
        self,
        agent_id: str,
        reason: str,
        trace_id: str = "",
    ) -> bool:
        """Publish an L5 agent apoptosis event."""
        return await self.publish_quick(
            topic=StandardEventType.AGENT_APOPTOSED.value,
            data={
                "agent_id": agent_id,
                "reason": reason,
            },
            priority=EventPriority.LOW,
            source="cluster",
            trace_id=trace_id,
        )

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the dispatch loop — the heart begins beating."""
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        self._logger.info("unified_event_bus_started", queues=len(self._queues), persistence=self._enable_persistence)

    async def stop(self) -> None:
        """Stop the dispatch loop gracefully."""
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        if self._backlog:
            self._backlog.close()
        self._logger.info(
            "unified_event_bus_stopped",
            total_events=sum(self._event_count.values()),
            dropped=self._dropped_count,
        )

    async def _dispatch_loop(self) -> None:
        """Priority-aware dispatch loop.

        CRITICAL events are dispatched before HIGH, then NORMAL, then LOW.
        Like blood preferentially flowing to the brain and heart.
        """
        while self._running:
            dispatched = False
            # Process in priority order
            for priority in EventPriority:
                queue = self._queues[priority]
                while not queue.empty():
                    try:
                        event = queue.get_nowait()
                        await self._dispatch_one(event)
                        dispatched = True
                    except asyncio.QueueEmpty:
                        break

            if not dispatched:
                await asyncio.sleep(0.01)

            # Periodic vacuum
            if self._enable_persistence and self._backlog:
                now = time.time()
                if now - self._last_vacuum > self._vacuum_interval:
                    cutoff = now - 7 * 86400  # Keep 7 days
                    removed = self._backlog.vacuum(cutoff)
                    self._last_vacuum = now
                    if removed:
                        self._logger.info("backlog_vacuumed", removed=removed)

    async def _dispatch_one(self, event: UnifiedEvent) -> None:
        """Dispatch a single event to all matching handlers."""
        # TTL check
        if event.ttl > 0 and time.time() - event.timestamp > event.ttl:
            return

        # In-memory history
        record = event.to_dict()
        self._in_memory_history.append(record)
        if len(self._in_memory_history) > self._max_history:
            self._in_memory_history = self._in_memory_history[-self._max_history:]

        # Find matching handlers
        matched = self._matching_handlers(event.topic)
        if matched:
            tasks = [handler(event.topic, event.data) for handler in matched]
            await asyncio.gather(*tasks, return_exceptions=True)

    def _matching_handlers(self, topic: str) -> list[EventHandler]:
        """Find all handlers matching the topic, including wildcards."""
        handlers: list[EventHandler] = []
        topic_parts = topic.split(".")

        for pattern, h_list in self._subscriptions.items():
            pattern_parts = pattern.split(".")

            if pattern == topic:
                handlers.extend(h_list)
            elif pattern.endswith("*"):
                prefix = pattern_parts[:-1]
                if topic_parts[:len(prefix)] == prefix:
                    handlers.extend(h_list)

        return handlers

    # ── Query Interface ───────────────────────────────────────────────

    def get_history(
        self, limit: int = 100, topic: str = "", layer: str = "",
    ) -> list[dict[str, Any]]:
        """Get recent event history, with optional filters."""
        results = self._in_memory_history
        if topic:
            results = [r for r in results if r.get("topic") == topic]
        if layer:
            results = [r for r in results if r.get("source_layer") == layer]
        return results[-limit:]

    def get_causal_trace(self, trace_id: str) -> list[dict[str, Any]]:
        """Reconstruct an end-to-end causal trace for a given trace_id.

        Like following a tagged molecule through the circulatory system.
        """
        # Check in-memory first
        memory_trace = [
            r for r in self._in_memory_history
            if r.get("trace_id") == trace_id
        ]
        memory_trace.sort(key=lambda r: r.get("timestamp", 0))

        # Supplement with SQLite backlog
        if self._backlog:
            db_trace = self._backlog.get_trace_chain(trace_id)
            # Merge, preferring memory (newer)
            mem_ids = {r.get("event_id") for r in memory_trace}
            for d in db_trace:
                if d.get("event_id") not in mem_ids:
                    memory_trace.append(d)
            memory_trace.sort(key=lambda r: r.get("timestamp", 0))

        return memory_trace

    def get_active_traces(self) -> list[str]:
        """Get currently active trace IDs."""
        return list(self._active_traces.keys())

    def get_layer_stats(self) -> dict[str, int]:
        """Get event counts by layer."""
        layer_counts: dict[str, int] = defaultdict(int)
        for r in self._in_memory_history[-1000:]:
            layer_counts[r.get("source_layer", "unknown")] += 1
        return dict(layer_counts)

    # ── Static Helpers ────────────────────────────────────────────────

    @staticmethod
    def generate_trace_id() -> str:
        """Generate a new global trace ID for end-to-end tracking."""
        return _gen_trace_id()


# ── Module-level helpers ──────────────────────────────────────────────

def _gen_event_id(topic: str) -> str:
    return hashlib.md5(f"{topic}|{time.time()}|{id(topic)}".encode()).hexdigest()[:16]


def _gen_trace_id() -> str:
    return f"trace-{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}"
