"""Stigmergy Field V2 — 踪迹网格+引文图+信任 (L5 StigmergyFieldV2)。

v2.0 升级:
  - 踪迹网格 (Trail Grid): 多层信息素 (短期/中期/长期)
  - 引文图 (Citation Graph): 记忆→记忆的引用关系
  - 信任权重 (Trust): 基于验证次数的信息素质量

使用方式:
    v2 = StigmergyFieldV2()
    v2.deposit_trail("memory/strategic", "auth_bug_fix", trust=0.9)
    v2.cite("memory/strategic/auth_bug_fix", "memory/episodic/debug_session")
    hotspots = v2.get_hotspots(threshold=0.5)
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.stigmergy_v2")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TrailEntry:
    """踪迹条目。"""
    trail_id: str
    content: str
    layer: str = ""            # short/medium/long
    trust: float = 0.5         # 信任权重
    citations: int = 0         # 被引用次数
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class Citation:
    """引文关系。"""
    source: str
    target: str
    weight: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class TrailState:
    """踪迹状态。"""
    total_trails: int
    total_citations: int
    avg_trust: float
    most_cited: str = ""
    layer_counts: dict[str, int] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# StigmergyFieldV2
# ═══════════════════════════════════════════════════════════════

class StigmergyFieldV2:
    """信息素场 v2.0 — 踪迹+引文+信任。

    使用方式:
        v2 = StigmergyFieldV2()
        v2.deposit_trail("strategic", "用户迁移到TS", trust=0.8)
        v2.cite("trail_001", "trail_002")
        state = v2.get_state()
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._trails: dict[str, TrailEntry] = {}
        self._citations: list[Citation] = []
        self._counter: int = 0

        # 多层网格 (短期/中期/长期)
        self._layers: dict[str, dict[str, float]] = {
            "short": {},    # 最近1小时
            "medium": {},   # 最近24小时
            "long": {},     # >24小时
        }

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def deposit_trail(
        self, layer: str, content: str,
        trust: float = 0.5, trail_id: str = "",
    ) -> TrailEntry:
        """沉积一条信息素踪迹。

        Args:
            layer: 层级 (short/medium/long)
            content: 内容
            trust: 信任权重
            trail_id: 踪迹ID (自动生成)
        """
        self._counter += 1
        tid = trail_id or f"trail_{self._counter:04d}"

        entry = TrailEntry(
            trail_id=tid, content=content,
            layer=layer, trust=max(0.0, min(1.0, trust)),
        )
        with self._lock:
            self._trails[tid] = entry
            if layer in self._layers:
                self._layers[layer][tid] = trust

        return entry

    def cite(self, source_id: str, target_id: str,
             weight: float = 0.5) -> Citation | None:
        """创建引文关系: source 引用 target。

        Args:
            source_id: 引用源
            target_id: 被引用目标
            weight: 引用权重
        """
        if source_id not in self._trails or target_id not in self._trails:
            return None

        cit = Citation(source=source_id, target=target_id,
                      weight=weight)
        with self._lock:
            self._citations.append(cit)

            # 更新被引次数
            target = self._trails[target_id]
            self._trails[target_id] = TrailEntry(
                trail_id=target.trail_id,
                content=target.content,
                layer=target.layer,
                trust=target.trust,
                citations=target.citations + 1,
            )

        return cit

    def boost_trust(self, trail_id: str, amount: float = 0.1) -> bool:
        """提升踪迹的信任权重 (验证通过时调用)。"""
        if trail_id not in self._trails:
            return False
        with self._lock:
            t = self._trails[trail_id]
            self._trails[trail_id] = TrailEntry(
                trail_id=t.trail_id, content=t.content,
                layer=t.layer,
                trust=min(1.0, t.trust + amount),
                citations=t.citations,
            )
        return True

    def get_hotspots(self, threshold: float = 0.5,
                     layer: str = "all") -> list[TrailEntry]:
        """获取高信任/高引用的热点踪迹。"""
        with self._lock:
            entries = list(self._trails.values())

        result = []
        for e in entries:
            if layer != "all" and e.layer != layer:
                continue
            score = e.trust * 0.6 + min(1.0, e.citations / 5) * 0.4
            if score >= threshold:
                result.append((score, e))
        result.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in result[:10]]

    def get_citation_graph(self) -> dict[str, list[str]]:
        """获取引文图 (用于可视化)。"""
        graph: dict[str, list[str]] = defaultdict(list)
        with self._lock:
            for cit in self._citations:
                graph[cit.source].append(cit.target)
        return dict(graph)

    def get_state(self) -> TrailState:
        """获取踪迹状态。"""
        with self._lock:
            total = len(self._trails)
            total_cit = len(self._citations)
            avg_trust = (
                sum(t.trust for t in self._trails.values()) / max(total, 1)
            )
            most_cited = max(
                self._trails.values(),
                key=lambda t: t.citations,
            ).trail_id if self._trails else ""

            layer_counts = {
                k: len(v) for k, v in self._layers.items()
            }

        return TrailState(
            total_trails=total, total_citations=total_cit,
            avg_trust=round(avg_trust, 3), most_cited=most_cited,
            layer_counts=layer_counts,
        )

    def get_stats(self) -> dict[str, Any]:
        state = self.get_state()
        return {
            "total_trails": state.total_trails,
            "total_citations": state.total_citations,
            "avg_trust": state.avg_trust,
            "most_cited": state.most_cited,
            "layer_counts": state.layer_counts,
        }
