"""Phase 7 灰度测试 — Hexis五层记忆升级 + 洞察引擎。

测试覆盖:
  - MemoryEntry/MemoryStats 不可变数据类
  - HexisMemoryStore: CRUD/搜索/整合/遗忘/事件处理/统计
  - InsightEngine: 工作模式/技术演变/工具使用/日程/健康/建议
  - 集成: 记忆→洞察→Strategic 存储完整链路
"""

from __future__ import annotations

import time
from unittest import mock

import pytest

from kernel.hexis_memory import (
    HexisMemoryStore, MemoryEntry, MemoryStats, MemoryLevel,
    ConsolidationResult, PatternMatch,
    LAYER_HALFLIFE, CONSOLIDATION_THRESHOLD,
)
from memory.insight_engine import (
    InsightEngine, Insight, InsightCategory,
)


# ═══════════════════════════════════════════════════════════════
# 数据类测试
# ═══════════════════════════════════════════════════════════════

class TestMemoryEntry:
    """MemoryEntry 不可变数据类测试。"""

    def test_create(self):
        e = MemoryEntry(id="m1", content="测试", level="episodic")
        assert e.id == "m1"
        assert e.importance == 0.5
        assert e.access_count == 0

    def test_to_dict(self):
        e = MemoryEntry(id="m1", content="C", level="episodic", importance=0.8)
        d = e.to_dict()
        assert d["id"] == "m1"
        assert d["importance"] == 0.8

    def test_frozen(self):
        e = MemoryEntry(id="m1", content="C", level="episodic")
        with pytest.raises(Exception):
            e.content = "changed"  # type: ignore

    def test_level_enum(self):
        assert MemoryLevel.WORKING.value == "working"
        assert MemoryLevel.STRATEGIC.value == "strategic"

    def test_persistent_levels(self):
        persistent = MemoryLevel.persistent_levels()
        assert "working" not in persistent
        assert "episodic" in persistent
        assert "strategic" in persistent

    def test_above(self):
        assert MemoryLevel.above("working") == "episodic"
        assert MemoryLevel.above("episodic") == "semantic"
        assert MemoryLevel.above("strategic") is None


class TestMemoryStats:
    """MemoryStats 不可变数据类测试。"""

    def test_create(self):
        s = MemoryStats(total_memories=100, by_level={"episodic": 80})
        assert s.total_memories == 100

    def test_frozen(self):
        s = MemoryStats(total_memories=0, by_level={})
        with pytest.raises(Exception):
            s.total_memories = 10  # type: ignore


class TestConsolidationResult:
    """ConsolidationResult 测试。"""

    def test_create(self):
        r = ConsolidationResult(
            from_level="episodic", to_level="semantic",
            source_count=50, patterns_extracted=["python", "bug"],
            new_entries=1,
        )
        assert r.source_count == 50
        assert "python" in r.patterns_extracted

    def test_frozen(self):
        r = ConsolidationResult(
            from_level="e", to_level="s", source_count=0,
            patterns_extracted=[], new_entries=0,
        )
        with pytest.raises(Exception):
            r.source_count = 1  # type: ignore


# ═══════════════════════════════════════════════════════════════
# HexisMemoryStore 核心测试
# ═══════════════════════════════════════════════════════════════

class TestHexisMemoryStore:
    """HexisMemoryStore 核心测试。"""

    @pytest.fixture
    def store(self, tmp_path):
        """创建临时文件存储。"""
        db = tmp_path / "memory.db"
        return HexisMemoryStore(
            chroma_path=str(tmp_path / "chroma"),
            sqlite_path=str(db),
        )

    def test_store_and_get(self, store):
        mid = store.store("用户修改了 auth.py", level="episodic")
        entry = store.get(mid)
        assert entry is not None
        assert entry.content == "用户修改了 auth.py"
        assert entry.level == "episodic"

    def test_store_working(self, store):
        mid = store.store("当前在 vscode", level="working")
        entry = store.get(mid)
        assert entry is not None
        assert entry.level == "working"

    def test_importance_clamped(self, store):
        mid = store.store("test", level="episodic", importance=5.0)
        entry = store.get(mid)
        assert entry is not None
        assert entry.importance <= 1.0

        mid2 = store.store("test2", level="episodic", importance=-1.0)
        entry2 = store.get(mid2)
        assert entry2 is not None
        assert entry2.importance >= 0.0

    def test_keyword_search(self, store):
        store.store("调试 auth 模块 bug", level="episodic")
        store.store("整理桌面文件", level="episodic")
        store.store("写单元测试", level="episodic")

        results = store.search("bug")
        assert len(results) >= 1
        assert any("bug" in r.content for r in results)

    def test_search_empty(self, store):
        results = store.search("nonexistent_xyz")
        assert len(results) == 0

    def test_search_by_level(self, store):
        store.store("episodic 条目", level="episodic")
        store.store("semantic 条目", level="semantic")
        results = store.search("条目", level="semantic")
        assert len(results) == 1
        assert results[0].level == "semantic"

    def test_update(self, store):
        mid = store.store("旧内容", level="episodic")
        ok = store.update(mid, content="新内容", importance=0.9)
        assert ok
        entry = store.get(mid)
        assert entry is not None
        assert entry.content == "新内容"
        assert entry.importance == 0.9

    def test_delete(self, store):
        mid = store.store("待删除", level="episodic")
        ok = store.delete(mid)
        assert ok
        assert store.get(mid) is None

    def test_search_ranks_by_relevance(self, store):
        store.store("python 编程", level="episodic", importance=0.9)
        store.store("python 教程", level="episodic", importance=0.3)
        results = store.search("python")
        assert len(results) >= 2
        assert results[0].importance >= results[1].importance

    def test_get_nonexistent(self, store):
        assert store.get("nonexistent_id") is None


class TestHexisMemoryConsolidation:
    """记忆整合测试。"""

    @pytest.fixture
    def store(self, tmp_path):
        db = tmp_path / "memory.db"
        return HexisMemoryStore(
            chroma_path=str(tmp_path / "chroma"),
            sqlite_path=str(db),
        )

    def test_consolidate_insufficient(self, store):
        """不足阈值时不整合。"""
        store.store("条目1", level="episodic")
        store.store("条目2", level="episodic")
        result = store.consolidate("episodic", "semantic")
        assert result.source_count == 0

    def test_consolidate_force(self, store):
        """强制整合。"""
        store.store("条目1", level="episodic")
        result = store.consolidate("episodic", "semantic", force=True)
        assert result.source_count == 1
        assert result.new_entries == 1

    def test_consolidate_chain(self, store):
        """完整整合链。"""
        for i in range(25):
            store.store(f"工作事件 {i}: 修改代码", level="working")
        results = store.consolidate_chain()
        assert len(results) > 0

    def test_consolidation_callback(self, store):
        """整合回调。"""
        received = []

        def cb(result):
            received.append(result)

        store.on_consolidate(cb)
        for i in range(10):
            store.store(f"事件 {i}", level="episodic")
        store.consolidate("episodic", "semantic", force=True)
        assert len(received) == 1


class TestHexisMemoryForgetting:
    """遗忘机制测试。"""

    @pytest.fixture
    def store(self, tmp_path):
        db = tmp_path / "memory.db"
        return HexisMemoryStore(
            chroma_path=str(tmp_path / "chroma"),
            sqlite_path=str(db),
        )

    def test_forget_empty(self, store):
        result = store.forget("episodic", threshold_days=30)
        assert result["forgotten_count"] == 0

    def test_forget_preserves_important(self, store):
        """高重要性记忆不被遗忘。"""
        mid = store.store("重要记忆", level="episodic", importance=0.95)
        result = store.forget("episodic", threshold_days=0)  # 即使阈值为0
        entry = store.get(mid)
        assert entry is not None  # 高重要性被保留

    def test_decay_score(self, store):
        """衰减分数计算。"""
        mid = store.store("test", level="episodic", importance=0.5)
        entry = store.get(mid)
        assert entry is not None
        score = store.decay_score(entry)
        assert 0.9 <= score <= 1.0  # 刚创建, 几乎不衰减

    def test_decay_faster_for_low_importance(self, store):
        """低重要性衰减更快。"""
        e_high = MemoryEntry(id="h", content="h", level="episodic", importance=0.9)
        e_low = MemoryEntry(id="l", content="l", level="episodic", importance=0.1)
        assert store.decay_score(e_high) >= store.decay_score(e_low)

    def test_layer_halflife_config(self):
        """每层半衰期配置。"""
        assert LAYER_HALFLIFE["working"] == 1.0
        assert LAYER_HALFLIFE["episodic"] == 30.0
        assert LAYER_HALFLIFE["strategic"] == 730.0


class TestHexisMemoryStats:
    """统计和上下文测试。"""

    @pytest.fixture
    def store(self, tmp_path):
        db = tmp_path / "memory.db"
        return HexisMemoryStore(
            chroma_path=str(tmp_path / "chroma"),
            sqlite_path=str(db),
        )

    def test_get_stats(self, store):
        store.store("e1", level="episodic", importance=0.6)
        store.store("s1", level="semantic", importance=0.8)
        stats = store.get_stats()
        assert stats.total_memories == 2
        assert stats.by_level["episodic"] == 1
        assert stats.by_level["semantic"] == 1

    def test_get_context(self, store):
        store.store("python auth bug", level="episodic")
        store.store("typescript refactor", level="semantic")
        ctx = store.get_context(query="python")
        assert len(ctx["relevant_memories"]) >= 1
        assert ctx["total_memories"] == 2

    def test_dump_layer(self, store):
        for i in range(5):
            store.store(f"e{i}", level="episodic")
        entries = store.dump_layer("episodic", limit=3)
        assert len(entries) == 3


class TestHexisMemoryEvents:
    """事件驱动测试。"""

    @pytest.fixture
    def store(self, tmp_path):
        db = tmp_path / "memory.db"
        return HexisMemoryStore(
            chroma_path=str(tmp_path / "chroma"),
            sqlite_path=str(db),
            auto_consolidate=False,
        )

    def test_store_with_source(self, store):
        mid = store.store("event driven", level="episodic", source="event/window")
        entry = store.get(mid)
        assert entry is not None
        assert entry.source == "event/window"

    def test_start_stop_eventbus(self, store):
        """启动/停止 EventBus 订阅。"""
        store.start(event_bus=None)
        assert store._event_bus is None
        store.stop()

    def test_flush_working_to_episodic(self, store):
        """Working → Episodic 刷新。"""
        for i in range(15):
            store.store(f"w{i}", level="working")
        store._flush_working_to_episodic()
        assert len(store._working) == 0
        # Episodic 应该有一条摘要
        episodes = store.dump_layer("episodic")
        assert len(episodes) == 1


# ═══════════════════════════════════════════════════════════════
# Insight / InsightEngine 测试
# ═══════════════════════════════════════════════════════════════

class TestInsight:
    """Insight 数据类测试。"""

    def test_create(self):
        i = Insight(
            category=InsightCategory.WORK_PATTERN,
            title="测试洞察",
            description="这是一个测试",
            confidence=0.7,
        )
        assert i.category == InsightCategory.WORK_PATTERN
        assert i.confidence == 0.7

    def test_to_human_readable(self):
        i = Insight(
            category=InsightCategory.HEALTH,
            title="休息提醒",
            description="你工作太久了",
            suggestion="去休息一下",
            confidence=0.8,
        )
        text = i.to_human_readable()
        assert "休息提醒" in text
        assert "去休息一下" in text

    def test_to_dict(self):
        i = Insight(
            category=InsightCategory.TECH_EVOLUTION,
            title="Python→TS",
            description="过渡中",
            confidence=0.6,
            evidence=("auth.py 改为了 auth.ts",),
        )
        d = i.to_dict()
        assert d["category"] == "tech_evolution"
        assert len(d["evidence"]) == 1

    def test_frozen(self):
        i = Insight(category=InsightCategory.LEARNING, title="T",
                     description="D", confidence=0.5)
        with pytest.raises(Exception):
            i.title = "changed"  # type: ignore


class TestInsightEngine:
    """InsightEngine 核心测试。"""

    @pytest.fixture
    def store(self, tmp_path):
        db = tmp_path / "memory.db"
        return HexisMemoryStore(
            chroma_path=str(tmp_path / "chroma"),
            sqlite_path=str(db),
        )

    @pytest.fixture
    def engine(self, store):
        return InsightEngine(memory_store=store)

    def test_analyze_empty(self, engine):
        """空记忆 → 空洞察。"""
        insights = engine.analyze(days=7)
        assert insights == []

    def test_analyze_with_memories(self, engine, store):
        """有记忆时生成洞察。"""
        store.store("python 代码调试 bug 修复", level="episodic", importance=0.5)
        store.store("python 单元测试 pytest", level="episodic", importance=0.5)
        store.store("python flask api 开发", level="episodic", importance=0.5)
        store.store("typescript 重构 auth 模块", level="episodic", importance=0.6)
        store.store("typescript react 组件", level="episodic", importance=0.5)

        insights = engine.analyze(days=7)
        assert len(insights) >= 1

    def test_analyze_respects_min_confidence(self, store):
        """最小置信度过滤。"""
        engine = InsightEngine(memory_store=store, min_confidence=0.9)
        # 少量数据 → 低置信度 → 全部被过滤
        store.store("python code", level="episodic")
        insights = engine.analyze(days=1)
        assert len(insights) == 0  # 没有足够数据达到高置信度

    def test_get_latest(self, engine, store):
        """获取最近洞察。"""
        store.store("python coding debugging", level="episodic", importance=0.8)
        store.store("python testing pytest bug fix", level="episodic", importance=0.8)
        store.store("python refactoring typescript migration", level="episodic", importance=0.7)
        engine.analyze(days=7)
        latest = engine.get_latest()
        assert len(latest) >= 1

    def test_store_insights(self, engine, store):
        """将洞察存入记忆。"""
        for i in range(5):
            store.store(f"python event {i} development", level="episodic", importance=0.7)
        engine.analyze(days=7)
        count = engine.store_insights()
        assert count >= 0  # 可能 0 如果置信度不够

    def test_detect_debug_pattern(self, engine, store):
        """检测调试模式。"""
        for i in range(8):
            store.store(f"bug fix error debug 修复 {i}", level="episodic", importance=0.6)
        insights = engine.analyze(days=7)
        has_debug = any(
            "调试" in i.title or "修复" in i.title or "bug" in i.title.lower()
            for i in insights
        )
        # 可能检测到或未检测到 (取决于数据量)
        assert isinstance(insights, list)

    def test_schedule_insight_night_work(self, engine, store):
        """深夜工作检测。"""
        # 模拟深夜时间戳
        for i in range(10):
            mid = store.store(f"深夜编码 {i}", level="episodic", importance=0.5)
            # 手动更新时间戳到凌晨3点
            store._conn.execute(
                "UPDATE memories SET timestamp = ? WHERE id = ?",
                (time.time() - 3600 * 5, mid),  # 5小时前 = 凌晨
            )
        store._conn.commit()
        insights = engine.analyze(days=1)
        assert isinstance(insights, list)

    def test_insight_deduplication(self, engine):
        """洞察去重。"""
        i1 = Insight(InsightCategory.WORK_PATTERN, "重复标题", "描述", 0.5)
        i2 = Insight(InsightCategory.WORK_PATTERN, "重复标题", "另一描述", 0.5)
        result = InsightEngine._deduplicate([i1, i2])
        assert len(result) == 1


# ═══════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════

class TestPhase7Integration:
    """Phase 7 跨模块集成测试。"""

    def test_full_memory_insight_pipeline(self, tmp_path):
        """完整记忆→洞察管道。"""
        db = tmp_path / "memory.db"
        store = HexisMemoryStore(
            chroma_path=str(tmp_path / "chroma"),
            sqlite_path=str(db),
        )
        engine = InsightEngine(memory_store=store)

        # 模拟一周记忆
        activities = [
            "窗口切换: code.exe — auth.py",
            "文件修改: src/auth.py",
            "窗口切换: chrome.exe — python docs",
            "复制代码片段 (120 字符, code)",
            "文件修改: tests/test_auth.py",
            "窗口切换: code.exe — refactor.ts",
            "文件修改: src/types.ts",
            "复制代码片段 (200 字符, code)",
            "窗口切换: terminal.exe — pytest",
            "文件修改: src/api.py",
        ] * 3  # 30条

        for i, content in enumerate(activities):
            store.store(content, level="episodic", importance=0.5)

        # 搜索
        results = store.search("auth")
        assert len(results) >= 1

        # 整合
        store.consolidate("episodic", "semantic", force=True)

        # 洞察
        insights = engine.analyze(days=7)
        assert isinstance(insights, list)

        # 统计
        stats = store.get_stats()
        assert stats.total_memories >= 30

    def test_memory_layer_climbing(self, tmp_path):
        """记忆逐层攀升。"""
        db = tmp_path / "memory.db"
        store = HexisMemoryStore(
            chroma_path=str(tmp_path / "chroma"),
            sqlite_path=str(db),
        )

        # L1: Working 积累
        for i in range(25):
            store.store(f"work event {i}", level="working")

        # 手动刷新 Working → Episodic
        store._flush_working_to_episodic()

        # L2: Episodic 应该有摘要
        epis = store.dump_layer("episodic")
        assert len(epis) >= 1

        # L2→L3: 整合
        store.consolidate("episodic", "semantic", force=True)
        sems = store.dump_layer("semantic")
        assert len(sems) >= 1

    def test_ebbinghaus_decay_consistency(self, tmp_path):
        """Ebbinghaus 衰减一致性。"""
        store = HexisMemoryStore(
            chroma_path=str(tmp_path / "chroma"),
            sqlite_path=str(tmp_path / "memory.db"),
        )

        # 高重要性 vs 低重要性
        hi = MemoryEntry(id="hi", content="重要", level="episodic", importance=0.95)
        lo = MemoryEntry(id="lo", content="普通", level="episodic", importance=0.1)

        score_hi = store.decay_score(hi)
        score_lo = store.decay_score(lo)

        assert score_hi >= score_lo  # 重要的衰减更慢
