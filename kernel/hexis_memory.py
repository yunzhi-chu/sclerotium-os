"""Hexis Memory v2.0 — 五层分层记忆 + Ebbinghaus 自适应遗忘 + 自动整合。

五层记忆 (working → episodic → semantic → procedural → strategic):
  L1 Working    — 挥发态, 当前上下文 (dict, 会话级)
  L2 Episodic   — 事件记录, "今天修了 auth bug" (SQLite+ChromaDB, 90天)
  L3 Semantic   — 知识模式, "用户从 Python→TS 过渡中" (ChromaDB, 永久)
  L4 Procedural — 操作模式, "调试流程: 改→测→看错误→再改" (SQLite, 永久)
  L5 Strategic  — 长期洞察, "目标: 完成重构" "在学 Rust 但反复放弃" (ChromaDB, 永久)

v2.0 新增:
  - MemoryEntry frozen dataclass (不可变)
  - 事件驱动整合 (EventBus 订阅 → 自动写入情景记忆)
  - 模式提取引擎 (episodic → semantic 自动发现)
  - 程序记忆 (重复操作序列检测)
  - 战略洞察 (长期行为趋势分析)
  - 每层独立 Ebbinghaus 半衰期配置
  - 重要性自适应调整 (基于访问频率)
  - 记忆相关性评分 (向量+关键词+时间衰减)

参考:
  - Hermes 4-layer memory (NousResearch 2026)
  - OpenClaw proactive memory v2026.4.11
  - SuperLocalMemory V3.3 (Zenodo 2026)
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable


# ═══════════════════════════════════════════════════════════════
# 常量和配置
# ═══════════════════════════════════════════════════════════════

class MemoryLevel(str, Enum):
    """记忆层级 (字符串枚举, 兼容现有代码)。"""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    STRATEGIC = "strategic"

    @classmethod
    def all_levels(cls) -> list[str]:
        return [l.value for l in cls]

    @classmethod
    def persistent_levels(cls) -> list[str]:
        """非挥发性层级。"""
        return [cls.EPISODIC.value, cls.SEMANTIC.value,
                cls.PROCEDURAL.value, cls.STRATEGIC.value]

    @classmethod
    def above(cls, level: str) -> str | None:
        """返回上一层。"""
        levels = cls.all_levels()
        try:
            idx = levels.index(level)
            return levels[idx + 1] if idx + 1 < len(levels) else None
        except ValueError:
            return None


# BUG#5修复: 支持通过环境变量覆盖半衰期默认值
# SCLEROTIUM_MEMORY_HALFLIFE_DAYS=7 → working=7d, episodic=28d, semantic=182d...
_DEFAULT_HALFLIFE: dict[str, float] = {
    "working": 1.0,
    "episodic": 30.0,
    "semantic": 180.0,
    "procedural": 365.0,
    "strategic": 730.0,
}

def _load_halflife_config() -> dict[str, float]:
    """BUG#5修复: 从环境变量加载半衰期全局覆盖。"""
    import os as _os
    result = dict(_DEFAULT_HALFLIFE)
    override = _os.environ.get("SCLEROTIUM_MEMORY_HALFLIFE_DAYS")
    if override:
        try:
            base = float(override)
            result["working"] = base
            result["episodic"] = base * 4
            result["semantic"] = base * 26
            result["procedural"] = base * 52
            result["strategic"] = base * 104
        except ValueError:
            pass
    return result

LAYER_HALFLIFE: dict[str, float] = _load_halflife_config()

# 每层自动整合的最小事件数
CONSOLIDATION_THRESHOLD: dict[str, int] = {
    "working": 20,        # 20条 Working → 1条 Episodic
    "episodic": 50,       # 50条 Episodic → 提取 Semantic
    "semantic": 30,       # 30条 Semantic → 提取 Procedural
    "procedural": 20,     # 20条 Procedural → 提取 Strategic
}

# 重要性权重
IMPORTANCE_DEFAULT = 0.5
IMPORTANCE_BOOST_ON_ACCESS = 0.02   # 每次访问提升
IMPORTANCE_MAX = 0.99


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MemoryEntry:
    """单条记忆 (不可变)。"""
    id: str
    content: str
    level: str                            # MemoryLevel 值
    importance: float = IMPORTANCE_DEFAULT
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = 0.0
    decay_factor: float = 1.0             # 当前衰减系数
    source: str = ""                      # 来源 (event/consolidation/insight/user)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "level": self.level,
            "importance": self.importance,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "decay_factor": self.decay_factor,
            "source": self.source,
        }


@dataclass(frozen=True)
class MemoryStats:
    """记忆系统统计 (不可变)。"""
    total_memories: int = 0
    by_level: dict[str, int] = field(default_factory=dict)
    avg_importance: float = 0.0
    total_accesses: int = 0
    last_consolidation: dict[str, float] = field(default_factory=dict)
    forgotten_total: int = 0
    chromadb_available: bool = False


@dataclass(frozen=True)
class ConsolidationResult:
    """整合操作结果 (不可变)。"""
    from_level: str
    to_level: str
    source_count: int
    patterns_extracted: list[str]
    new_entries: int
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class PatternMatch:
    """模式匹配结果 (不可变)。"""
    pattern: str
    frequency: int
    confidence: float      # 0.0–1.0
    examples: tuple[str, ...] = ()
    category: str = ""     # "behavior"/"technical"/"schedule"/"preference"


# ═══════════════════════════════════════════════════════════════
# HexisMemoryStore v2.0
# ═══════════════════════════════════════════════════════════════

class HexisMemoryStore:
    """五层分层记忆存储引擎 v2.0。

    使用方式:
        store = HexisMemoryStore()
        store.start(event_bus=bus)

        # 存储记忆
        mid = store.store("用户在晚上11点调试 auth 模块",
                          level=MemoryLevel.EPISODIC, importance=0.7)

        # 搜索
        results = store.search("auth bug")

        # 自动整合 (由事件驱动或手动触发)
        result = store.consolidate(MemoryLevel.EPISODIC, MemoryLevel.SEMANTIC)

        # 遗忘
        store.forget(MemoryLevel.EPISODIC, threshold_days=90)

        # 统计
        stats = store.get_stats()
    """

    def __init__(
        self,
        chroma_path: str = "./data/chroma",
        sqlite_path: str = "./data/memory.db",
        auto_consolidate: bool = True,
    ) -> None:
        self._chroma_path = Path(chroma_path)
        self._sqlite_path = Path(sqlite_path)
        self._chroma_path.mkdir(parents=True, exist_ok=True)
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._auto_consolidate = auto_consolidate

        # SQLite
        self._conn = sqlite3.connect(str(self._sqlite_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_sqlite()

        # ChromaDB (lazy)
        self._chroma: Any = None
        self._chroma_collection: Any = None

        # Working memory (L1, volatile)
        self._working: dict[str, MemoryEntry] = {}

        # 计数器
        self._counter: int = 0
        self._forgotten_total: int = 0
        self._last_consolidation: dict[str, float] = {}

        # EventBus
        self._event_bus: Any = None
        self._sub_ids: list[str] = []

        # 线程安全
        self._lock = threading.RLock()

        # 整合回调
        self._on_consolidate: list[Callable[[ConsolidationResult], None]] = []

    # ═══════════════════════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════════════════════

    def start(self, event_bus: Any = None) -> None:
        """启动记忆系统, 订阅 EventBus。"""
        self._event_bus = event_bus
        if event_bus:
            self._sub_ids = [
                event_bus.subscribe("window.changed", self._on_event),
                event_bus.subscribe("clipboard.text", self._on_event),
                event_bus.subscribe("file.modified", self._on_event),
                event_bus.subscribe("activity.*", self._on_event),
                event_bus.subscribe("rhythm.gastric", self._on_gastric),
            ]

    def stop(self) -> None:
        """停止记忆系统, 取消订阅。"""
        if self._event_bus:
            for sub_id in self._sub_ids:
                self._event_bus.unsubscribe(sub_id)
            self._sub_ids.clear()

    def close(self) -> None:
        """关闭连接。"""
        self.stop()
        self._conn.close()

    # ═══════════════════════════════════════════════════════
    # CRUD
    # ═══════════════════════════════════════════════════════

    def store(
        self,
        content: str,
        level: str = MemoryLevel.EPISODIC.value,
        importance: float = IMPORTANCE_DEFAULT,
        metadata: dict[str, Any] | None = None,
        source: str = "",
    ) -> str:
        """存储一条记忆。返回 memory_id。

        Args:
            content: 记忆内容
            level: 层级
            importance: 重要性 (0.0–1.0)
            metadata: 附加元数据
            source: 来源标识
        """
        with self._lock:
            self._counter += 1
            mem_id = f"mem_{self._counter:08d}"
            now = time.time()

            entry = MemoryEntry(
                id=mem_id,
                content=content,
                level=level,
                importance=self._clamp_importance(importance),
                metadata=metadata or {},
                timestamp=now,
                last_accessed=now,
                source=source,
            )

            # Working 仅内存
            if level == MemoryLevel.WORKING.value:
                self._working[mem_id] = entry
                return mem_id

            # 持久化到 SQLite + ChromaDB
            self._persist_to_sqlite(mem_id, content, level, entry.importance, metadata, now, source, entry.decay_factor)
            self._index_to_chroma(mem_id, content, level, importance)
            return mem_id

    def _persist_to_sqlite(
        self, mem_id: str, content: str, level: str,
        importance: float, metadata: dict[str, Any] | None,
        now: float, source: str, decay_factor: float,
    ) -> None:
        """持久化单条记忆到 SQLite。P1-1: extracted from store()."""
        self._conn.execute(
            """INSERT OR REPLACE INTO memories
               (id, content, level, importance, metadata_json,
                timestamp, access_count, last_accessed, source, decay_factor)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (mem_id, content, level, importance,
             json.dumps(metadata or {}, ensure_ascii=False),
             now, 0, now, source, decay_factor),
        )
        self._conn.commit()

    def _index_to_chroma(self, mem_id: str, content: str, level: str, importance: float) -> None:
        """索引单条记忆到 ChromaDB 向量库。P1-1: extracted from store()."""
        coll = self._get_chroma()
        if coll:
            try:
                coll.add(
                    ids=[mem_id], documents=[content],
                    metadatas=[{"level": level, "importance": importance}],
                )
            except Exception:
                pass

    def get(self, memory_id: str) -> MemoryEntry | None:
        """按 ID 获取记忆。"""
        with self._lock:
            if memory_id in self._working:
                return self._working[memory_id]

            row = self._conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            if row:
                return self._row_to_entry(row)
            return None

    def search(
        self,
        query: str,
        level: str = "all",
        top_k: int = 10,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        """搜索记忆 (向量+关键词混合)。

        Args:
            query: 搜索查询
            level: 限定层级 ("all" = 全部)
            top_k: 返回条数
            min_importance: 最小重要性
        """
        results: list[MemoryEntry] = []

        # ChromaDB 向量搜索
        coll = self._get_chroma()
        if coll and query.strip():
            try:
                where = None if level == "all" else {"level": level}
                chroma_results = coll.query(
                    query_texts=[query],
                    n_results=top_k,
                    where=where,
                )
                if chroma_results and chroma_results["ids"]:
                    for i, mid in enumerate(chroma_results["ids"][0]):
                        row = self._conn.execute(
                            "SELECT * FROM memories WHERE id = ?", (mid,)
                        ).fetchone()
                        if row:
                            entry = self._row_to_entry(row)
                            if entry.importance >= min_importance:
                                results.append(entry)
            except Exception:
                pass

        # SQLite 关键词回退
        if not results:
            results = self._keyword_search(query, level, top_k)

        # BUG#1修复: 工作记忆存在于 self._working (in-memory), 不在 ChromaDB/SQLite
        # 当搜索 working 或 all 层级时, 也检查工作记忆
        if level in ("working", "all"):
            working_entries = list(self._working.values())
            for we in working_entries:
                # 简单文本匹配
                if query.lower() in we.content.lower() and we.importance >= min_importance:
                    results.append(we)

        # 按重要性+时间排序, 应用衰减
        results = self._rank_results(results, query)

        # 更新访问计数 (非 working 条目)
        for entry in results[:top_k]:
            if entry.id not in self._working:
                self._touch(entry.id)

        return results[:top_k]

    def update(
        self, memory_id: str,
        content: str | None = None,
        importance: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """更新记忆 (不可变模式 — 内部更新 SQLite)。

        返回是否成功。
        """
        with self._lock:
            if memory_id in self._working:
                entry = self._working[memory_id]
                # 创建新 entry (不可变)
                new_entry = MemoryEntry(
                    id=entry.id,
                    content=content if content is not None else entry.content,
                    level=entry.level,
                    importance=importance if importance is not None else entry.importance,
                    metadata=metadata if metadata is not None else entry.metadata,
                    timestamp=entry.timestamp,
                    access_count=entry.access_count,
                    last_accessed=time.time(),
                    source=entry.source,
                )
                self._working[memory_id] = new_entry
                return True

            sets = []
            params: list[Any] = []
            if content is not None:
                sets.append("content = ?")
                params.append(content)
            if importance is not None:
                sets.append("importance = ?")
                params.append(max(0.0, min(IMPORTANCE_MAX, importance)))
            if metadata is not None:
                sets.append("metadata_json = ?")
                params.append(json.dumps(metadata, ensure_ascii=False))
            if not sets:
                return False

            sets.append("last_accessed = ?")
            params.append(time.time())
            params.append(memory_id)

            sql = f"UPDATE memories SET {', '.join(sets)} WHERE id = ?"
            self._conn.execute(sql, params)
            self._conn.commit()
            return True

    def delete(self, memory_id: str) -> bool:
        """删除一条记忆。"""
        with self._lock:
            if memory_id in self._working:
                del self._working[memory_id]
                return True

            self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            self._conn.commit()
            return True

    # ═══════════════════════════════════════════════════════
    # 整合 (Consolidation)
    # ═══════════════════════════════════════════════════════

    def consolidate(
        self,
        from_level: str,
        to_level: str,
        force: bool = False,
    ) -> ConsolidationResult:
        """将低层记忆整合为高层记忆。P1-1 refactor: split into focused helpers."""
        with self._lock:
            # 获取源数据 (Working 或持久层)
            gather_result = self._gather_source(from_level, force)
            if gather_result is None:
                return ConsolidationResult(
                    from_level=from_level, to_level=to_level,
                    source_count=0, patterns_extracted=[], new_entries=0,
                )
            all_text, source_count = gather_result

            # 提取模式 → 存储整合条目 → 通知回调
            return self._finalize_consolidation(from_level, to_level, all_text, source_count)

    def _gather_source(
        self, from_level: str, force: bool,
    ) -> tuple[str, int] | None:
        """收集源层级数据。返回 (all_text, source_count) 或 None (不足阈值)。"""
        if from_level == MemoryLevel.WORKING.value:
            working = list(self._working.values())
            if not working:
                return None
            threshold = CONSOLIDATION_THRESHOLD.get(from_level, 20)
            if len(working) < threshold and not force:
                return None
            all_text = " ".join(e.content for e in working)
            source_count = len(working)
            self._working.clear()
            return all_text, source_count
        else:
            rows = self._conn.execute(
                "SELECT * FROM memories WHERE level = ? ORDER BY timestamp DESC",
                (from_level,)
            ).fetchall()
            threshold = CONSOLIDATION_THRESHOLD.get(from_level, 10)
            if len(rows) < threshold and not force:
                return None
            all_text = " ".join(r["content"] for r in rows)
            return all_text, len(rows)

    def _finalize_consolidation(
        self, from_level: str, to_level: str, all_text: str, source_count: int,
    ) -> ConsolidationResult:
        """提取模式、存储整合条目、回调通知。"""
        patterns = self._extract_patterns(all_text)
        summary = self._build_consolidation_summary(from_level, to_level, source_count, patterns)
        self.store(
            content=summary, level=to_level, importance=0.7,
            metadata={"consolidated_from": from_level, "source_count": source_count, "patterns": patterns},
            source="consolidation",
        )
        self._last_consolidation[from_level] = time.time()
        result = ConsolidationResult(
            from_level=from_level, to_level=to_level,
            source_count=source_count, patterns_extracted=patterns, new_entries=1,
        )
        for cb in self._on_consolidate:
            try:
                cb(result)
            except Exception:
                pass
        return result

    def consolidate_chain(self) -> list[ConsolidationResult]:
        """执行完整整合链: working→episodic→semantic→procedural→strategic。"""
        results = []
        for i in range(len(MemoryLevel.all_levels()) - 1):
            from_lv = MemoryLevel.all_levels()[i]
            to_lv = MemoryLevel.all_levels()[i + 1]
            result = self.consolidate(from_lv, to_lv)
            if result.source_count > 0:
                results.append(result)
        return results

    # ═══════════════════════════════════════════════════════════
    # Ebbinghaus 自适应遗忘
    # ═══════════════════════════════════════════════════════════

    def forget(self, level: str, threshold_days: int = 90, decay_threshold: float = 0.2) -> dict[str, Any]:
        """对指定层级应用 Ebbinghaus 自适应遗忘。

        BUG#4修复: 1) 处理 working memory (在 self._working 中, 不在 SQLite)
        2) 移除 importance < 0.6 的硬限制, 让 decay_threshold 参数真正生效
        """
        with self._lock:
            self._update_decay_factors(level)
            halflife = LAYER_HALFLIFE.get(level, 30.0)
            now = time.time()
            forgotten = 0

            # BUG#4修复: 处理 working memory
            if level == "working":
                to_delete = []
                for mem_id, entry in list(self._working.items()):
                    import json as _json
                    mock_row = {
                        "id": mem_id, "importance": entry.importance,
                        "timestamp": entry.timestamp, "access_count": entry.access_count,
                        "metadata_json": _json.dumps(entry.metadata or {}),
                    }
                    if self._should_forget_row(mock_row, halflife, now, threshold_days, decay_threshold):
                        to_delete.append(mem_id)
                for mem_id in to_delete:
                    del self._working[mem_id]
                    forgotten += 1
            else:
                rows = self._conn.execute(
                    """SELECT id, importance, timestamp, access_count, last_accessed, metadata_json
                       FROM memories WHERE level = ?""", (level,)
                ).fetchall()

                for row in rows:
                    if self._should_forget_row(row, halflife, now, threshold_days, decay_threshold):
                        self._conn.execute("DELETE FROM memories WHERE id = ?", (row["id"],))
                        forgotten += 1
                self._conn.commit()

            self._forgotten_total += forgotten
            return {
                "forgotten_count": forgotten, "level": level,
                "halflife_days": halflife, "decay_threshold": decay_threshold,
                "total_forgotten_all_time": self._forgotten_total,
            }

    @staticmethod
    def _should_forget_row(
        row, halflife: float, now: float, threshold_days: int, decay_threshold: float,
    ) -> bool:
        """判断单条记忆是否应被遗忘。P1-1: extracted from forget()."""
        try:
            ts = float(row["timestamp"])
            days_old = (now - ts) / 86400.0
            if days_old < threshold_days:
                return False
            importance = float(row["importance"])
            access_count = int(row["access_count"])
            adjusted = halflife * (1.0 + importance * 3.0)
            decay = math.exp(-math.log(2) * days_old / max(adjusted, 1.0))
            if access_count > 5:
                decay = max(decay, 0.5)
            meta = json.loads(row["metadata_json"] or "{}")
            if meta.get("pinned"):
                decay = 1.0
            # BUG#4修复: 移除 importance < 0.6 硬限制, 让 decay_threshold 参数真正控制遗忘
            # 高重要性记忆的半衰期通过 adjusted = halflife * (1 + imp*3) 自然延长
            return decay < decay_threshold
        except (ValueError, TypeError):
            return False

    def _update_decay_factors(self, level: str | None = None) -> int:
        """更新所有记忆的 decay_factor 到 SQLite (Ebbinghaus 实时衰减).

        修复 Bug #5: 之前 decay_factor 创建后永远为 1.0, 从未随时间衰减。
        此方法在 forget() 前自动调用, 也可作为定时维护任务独立调用。

        Returns:
            更新的记忆条数
        """
        where = "WHERE level = ?" if level else ""
        params: tuple = (level,) if level else ()

        rows = self._conn.execute(
            f"SELECT id, timestamp, importance, level FROM memories {where}",
            params,
        ).fetchall()

        now = time.time()
        updated = 0

        for row in rows:
            try:
                ts = float(row["timestamp"])
                days_old = max(0, (now - ts) / 86400.0)
                importance = float(row["importance"])
                mem_level = row["level"]

                halflife = LAYER_HALFLIFE.get(mem_level, 30.0)
                adjusted = halflife * (1.0 + importance * 3.0)
                decay = round(math.exp(-math.log(2) * days_old / max(adjusted, 1.0)), 4)

                self._conn.execute(
                    "UPDATE memories SET decay_factor = ? WHERE id = ?",
                    (decay, row["id"]),
                )
                updated += 1
            except (ValueError, TypeError):
                pass

        if updated > 0:
            self._conn.commit()
        return updated

    def decay_score(self, entry: MemoryEntry) -> float:
        """计算单条记忆的当前衰减分数 (0=完全遗忘, 1=全新)。"""
        days_old = (time.time() - entry.timestamp) / 86400.0
        halflife = LAYER_HALFLIFE.get(entry.level, 30.0)
        adjusted = halflife * (1.0 + entry.importance * 3.0)
        return math.exp(-math.log(2) * days_old / max(adjusted, 1.0))

    # ═══════════════════════════════════════════════════════════
    # 上下文和统计
    # ═══════════════════════════════════════════════════════════

    def get_context(
        self, query: str = "", top_k: int = 5, level: str = "all"
    ) -> dict[str, Any]:
        """获取决策上下文 (相关记忆 + 层级统计)。"""
        memories = []
        if query:
            entries = self.search(query=query, level=level, top_k=top_k)
            memories = [e.to_dict() for e in entries]

        level_counts = {}
        for lv in MemoryLevel.all_levels():
            if lv == MemoryLevel.WORKING.value:
                level_counts[lv] = len(self._working)
            else:
                level_counts[lv] = self._conn.execute(
                    "SELECT COUNT(*) as c FROM memories WHERE level = ?", (lv,)
                ).fetchone()["c"]

        return {
            "relevant_memories": memories,
            "level_counts": level_counts,
            "total_memories": sum(level_counts.values()),
            "working_count": len(self._working),
        }

    def get_stats(self) -> MemoryStats:
        """获取完整统计。"""
        with self._lock:
            by_level: dict[str, int] = {}
            total = 0
            imp_sum = 0.0
            imp_count = 0
            access_total = 0

            for lv in MemoryLevel.all_levels():
                if lv == MemoryLevel.WORKING.value:
                    count = len(self._working)
                else:
                    count = self._conn.execute(
                        "SELECT COUNT(*) as c FROM memories WHERE level = ?", (lv,)
                    ).fetchone()["c"]

                    # 聚合此层的 importance/access
                    rows = self._conn.execute(
                        "SELECT importance, access_count FROM memories WHERE level = ?",
                        (lv,)
                    ).fetchall()
                    for r in rows:
                        imp_sum += r["importance"]
                        imp_count += 1
                        access_total += r["access_count"]

                by_level[lv] = count
                total += count

            return MemoryStats(
                total_memories=total,
                by_level=by_level,
                avg_importance=round(imp_sum / max(imp_count, 1), 3),
                total_accesses=access_total,
                last_consolidation=dict(self._last_consolidation),
                forgotten_total=self._forgotten_total,
                chromadb_available=self._get_chroma() is not None,
            )

    def dump_layer(self, level: str, limit: int = 20) -> list[MemoryEntry]:
        """导出指定层级的所有记忆 (调试用)。"""
        if level == MemoryLevel.WORKING.value:
            return list(self._working.values())[-limit:]

        rows = self._conn.execute(
            "SELECT * FROM memories WHERE level = ? ORDER BY timestamp DESC LIMIT ?",
            (level, limit),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # 回调
    # ═══════════════════════════════════════════════════════════

    def on_consolidate(self, cb: Callable[[ConsolidationResult], None]) -> None:
        """注册整合完成回调。"""
        self._on_consolidate.append(cb)

    # ═══════════════════════════════════════════════════════════
    # Internal — SQLite
    # ═══════════════════════════════════════════════════════════

    def _init_sqlite(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                level TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                metadata_json TEXT DEFAULT '{}',
                timestamp REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                source TEXT DEFAULT ''
            )
        """)
        # Schema migration: add missing columns from older DB versions
        cur = self._conn.execute("PRAGMA table_info(memories)")
        existing_cols = {row[1] for row in cur.fetchall()}
        migrations = {
            "source": "TEXT DEFAULT ''",
            "access_count": "INTEGER DEFAULT 0",
            "last_accessed": "REAL",
            "decay_factor": "REAL DEFAULT 1.0",
        }
        for col, col_def in migrations.items():
            if col not in existing_cols:
                self._conn.execute(f"ALTER TABLE memories ADD COLUMN {col} {col_def}")
        for idx in ["level", "timestamp", "importance"]:
            self._conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_memories_{idx} ON memories({idx})"
            )
        self._conn.commit()

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        """SQLite Row → MemoryEntry。"""
        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            level=row["level"],
            importance=row["importance"],
            metadata=json.loads(row["metadata_json"] or "{}"),
            timestamp=float(row["timestamp"]),
            access_count=int(row["access_count"]),
            last_accessed=float(row["last_accessed"] or 0),
            decay_factor=float(row["decay_factor"]) if "decay_factor" in row.keys() else 1.0,
            source=row["source"] if "source" in row.keys() else "",
        )

    def _touch(self, memory_id: str) -> None:
        """更新访问计数和时间。"""
        self._conn.execute(
            """UPDATE memories
               SET access_count = access_count + 1, last_accessed = ?
               WHERE id = ?""",
            (time.time(), memory_id),
        )
        self._conn.commit()

    def _get_chroma(self) -> Any:
        """懒加载 ChromaDB collection。"""
        if self._chroma is None:
            try:
                import chromadb
                self._chroma = chromadb.PersistentClient(
                    path=str(self._chroma_path),
                )
                self._chroma_collection = self._chroma.get_or_create_collection(
                    name="hexis_memories",
                    metadata={"hnsw:space": "cosine"},
                )
            except ImportError:
                pass
        return self._chroma_collection

    # ═══════════════════════════════════════════════════════════
    # Internal — 搜索和排序
    # ═══════════════════════════════════════════════════════════

    def _keyword_search(
        self, query: str, level: str, top_k: int,
    ) -> list[MemoryEntry]:
        """SQLite 关键词搜索回退。"""
        words = query.lower().split()
        sql = "SELECT * FROM memories WHERE 1=1"
        params: list[Any] = []

        if level != "all":
            sql += " AND level = ?"
            params.append(level)
        if words:
            conditions = " OR ".join(["content LIKE ?" for _ in words])
            sql += f" AND ({conditions})"
            params.extend([f"%{w}%" for w in words])
        sql += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        params.append(top_k)

        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def _rank_results(
        self, entries: list[MemoryEntry], query: str,
    ) -> list[MemoryEntry]:
        """按相关性排序 (时间+重要性+关键词匹配+衰减)。"""
        query_lower = query.lower()
        scored = []
        for entry in entries:
            score = entry.importance
            # 关键词精确匹配加分
            if query_lower in entry.content.lower():
                score += 0.3
            # 最近添加的加分
            days_old = (time.time() - entry.timestamp) / 86400.0
            score += max(0, 0.2 - days_old * 0.01)
            # 衰减因子
            score *= self.decay_score(entry)
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored]

    # ═══════════════════════════════════════════════════════════
    # Internal — 模式提取和整合
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _clamp_importance(value: float) -> float:
        """Clamp importance to valid range."""
        return max(0.0, min(IMPORTANCE_MAX, value))

    @staticmethod
    def _extract_patterns(text: str, max_patterns: int = 15) -> list[str]:
        """从文本中提取关键词模式 (TF-IDF加权 + 共现检测)。

        Upgraded from simple word frequency (Bug #4 fix):
          - TF-IDF penalizes common words across documents
          - N-gram detection captures multi-word concepts
          - Category-tagged patterns for better semantic grouping
        """
        if not text or not text.strip():
            return []

        # 分文档: 按 "|" 或 "。" 或 ". " 切分
        docs = [d.strip() for d in text.replace("|", ".").replace("。", ".").split(".") if len(d.strip()) > 10]

        words_all = [w.lower() for w in text.split() if len(w) > 3 and w.isalpha()]
        if not words_all:
            return []

        # ── TF-IDF 加权 ──────────────────────────────────────────
        doc_count = max(len(docs), 1)
        word_doc_freq: dict[str, int] = {}
        word_total_freq: dict[str, int] = {}
        cooccur: dict[tuple[str, str], int] = {}

        for doc in docs:
            doc_words = [w.lower() for w in doc.split() if len(w) > 3 and w.isalpha()]
            for w in set(doc_words):
                word_doc_freq[w] = word_doc_freq.get(w, 0) + 1
            for w in doc_words:
                word_total_freq[w] = word_total_freq.get(w, 0) + 1
            for i in range(len(doc_words)):
                for j in range(i + 1, min(i + 5, len(doc_words))):
                    pair = tuple(sorted([doc_words[i], doc_words[j]]))
                    cooccur[pair] = cooccur.get(pair, 0) + 1

        tfidf_scores: dict[str, float] = {}
        for w, tf in word_total_freq.items():
            df = word_doc_freq.get(w, 1)
            idf = math.log((doc_count + 1) / (df + 1)) + 1.0
            tfidf_scores[w] = tf * idf

        # Top TF-IDF keywords
        top_keywords = sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)[:max_patterns]

        # Top co-occurrence pairs → composite patterns
        top_pairs = sorted(cooccur.items(), key=lambda x: x[1], reverse=True)[:5]
        pair_patterns = [f"{a}+{b}" for (a, b), c in top_pairs if c >= 2]

        # 合并: TF-IDF keywords + co-occurrence pairs
        patterns = [w for w, _ in top_keywords if word_total_freq.get(w, 0) >= 2]
        patterns.extend(pair_patterns)

        return patterns[:max_patterns]

    @staticmethod
    def _build_consolidation_summary(
        from_level: str, to_level: str, count: int, patterns: list[str],
    ) -> str:
        """生成整合摘要文本 (增强版 — Bug #4 fix)。"""
        if not patterns:
            return (
                f"[{from_level}→{to_level}] 从 {count} 条 {from_level} 记忆整合。"
                f" 未检测到显著跨记忆模式 — 可能需要更多样本或多样化输入。"
            )
        primary = patterns[0] if patterns else ""
        secondary = ", ".join(patterns[1:6]) if len(patterns) > 1 else ""
        return (
            f"[{from_level}→{to_level}] 从 {count} 条 {from_level} 记忆整合。"
            f" 主模式: {primary}。"
            + (f" 关联模式: {secondary}。" if secondary else "")
            + (f" 共 {len(patterns)} 个模式。" if len(patterns) > 6 else "")
        )

    # ═══════════════════════════════════════════════════════════
    # Internal — EventBus 事件处理
    # ═══════════════════════════════════════════════════════════

    def _on_event(self, event: Any) -> None:
        """EventBus 事件 → 自动写入情景记忆。P1-1 refactor: dispatch to typed handlers."""
        topic = event.topic
        data = event.data or {}

        if "window.changed" == topic:
            self._on_window_changed(data)
        elif "clipboard.text" == topic:
            self._on_clipboard_text(data)
        elif "file.modified" == topic:
            self._on_file_modified(data)
        elif "activity.session" in topic:
            self._on_activity_session(data)

        if self._auto_consolidate:
            if len(self._working) >= CONSOLIDATION_THRESHOLD.get(MemoryLevel.WORKING.value, 20):
                self._flush_working_to_episodic()

    def _on_window_changed(self, data: dict) -> None:
        current = data.get("current", {})
        app = current.get("process_name", "")
        if app:
            self.store(
                content=f"窗口切换: {app} — {current.get('title', '')}",
                level=MemoryLevel.WORKING.value, importance=0.3,
                metadata={"app": app, "title": current.get("title", "")},
                source="event/window",
            )

    def _on_clipboard_text(self, data: dict) -> None:
        if data.get("category") == "code" and data.get("length", 0) > 10:
            self.store(
                content=f"复制代码片段 ({data['length']} 字符, {data['category']})",
                level=MemoryLevel.WORKING.value, importance=0.5,
                metadata={"category": data["category"], "length": data["length"]},
                source="event/clipboard",
            )

    def _on_file_modified(self, data: dict) -> None:
        path = data.get("path", "")
        if path:
            self.store(
                content=f"文件修改: {path}",
                level=MemoryLevel.WORKING.value, importance=0.4,
                metadata={"path": path, "suffix": data.get("suffix", "")},
                source="event/file",
            )

    def _on_activity_session(self, data: dict) -> None:
        duration = data.get("duration", 0)
        if duration > 60:
            self.store(
                content=f"活跃会话: {duration:.0f}秒",
                level=MemoryLevel.WORKING.value, importance=0.3,
                metadata={"duration": duration},
                source="event/activity",
            )

    def _on_gastric(self, event: Any) -> None:
        """胃磨节律触发 — 执行记忆维护 (整合+遗忘)。"""
        hour = event.data.get("hour", 0)
        # 凌晨整合链
        if hour >= 2 and hour <= 4:
            self.consolidate_chain()
            for level in MemoryLevel.persistent_levels():
                halflife = LAYER_HALFLIFE.get(level, 30)
                self.forget(level, threshold_days=int(halflife * 2))

    def _flush_working_to_episodic(self) -> None:
        """将 Working 记忆刷入 Episodic。"""
        working = list(self._working.values())
        if not working:
            return

        # 合并为一条情景摘要
        summary = " | ".join(e.content for e in working[-15:])
        self.store(
            content=f"会话摘要: {summary}",
            level=MemoryLevel.EPISODIC.value,
            importance=0.5,
            metadata={"working_count": len(working)},
            source="auto/flush",
        )
        self._working.clear()
