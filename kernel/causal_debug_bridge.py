"""Causal Debug Bridge — SCM 故障根因追溯 (L4 CausalDebugEngine)。

生命体的"诊断能力" — 当系统出错时, 不只看"什么错了",
而是追溯"为什么会错"。

功能:
  - 构建因果图 (哪些器官依赖哪些器官)
  - 故障注入: "如果当时 X 是正常的, Y 还会出错吗?"
  - 根因候选排序 (按可能性)
  - 自动生成修复建议

使用方式:
    causal = CausalDebugBridge()
    causal.add_dependency("nudge_engine", "rhythm_engine")
    causal.add_dependency("nudge_engine", "user_model")
    root_causes = causal.diagnose("nudge_engine", symptom="频繁误报")
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.causal_debug")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CausalLink:
    """因果依赖关系。"""
    source: str          # 原因
    target: str          # 结果
    strength: float = 0.5  # 因果强度 (0-1)
    description: str = ""


@dataclass(frozen=True)
class RootCause:
    """根因候选。"""
    organ: str
    probability: float        # 0.0–1.0 成为根因的概率
    evidence: tuple[str, ...]  # 支持证据
    suggestion: str = ""


@dataclass(frozen=True)
class CausalDiagnosis:
    """因果诊断结果。"""
    symptom_organ: str
    symptom: str
    root_causes: tuple[RootCause, ...]
    total_candidates: int
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# CausalDebugBridge
# ═══════════════════════════════════════════════════════════════

class CausalDebugBridge:
    """SCM 因果故障归因引擎。

    使用方式:
        causal = CausalDebugBridge()
        causal.add_dependency("rhythm_engine", "nudge_engine", strength=0.8)
        diagnosis = causal.diagnose("nudge_engine", symptom="通知延迟")
        for rc in diagnosis.root_causes:
            print(f"根因候选: {rc.organ} (概率={rc.probability})")
    """

    def __init__(self) -> None:
        self._dependencies: dict[str, list[CausalLink]] = defaultdict(list)
        self._reverse_deps: dict[str, list[CausalLink]] = defaultdict(list)
        self._organ_status: dict[str, str] = {}  # organ → healthy/degraded
        self._diagnoses: list[CausalDiagnosis] = []

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def add_dependency(
        self, source: str, target: str,
        strength: float = 0.5, description: str = "",
    ) -> None:
        """添加因果依赖: source → target (source 影响 target)。

        Args:
            source: 原因器官
            target: 结果器官
            strength: 因果强度
            description: 描述
        """
        link = CausalLink(source=source, target=target,
                         strength=strength, description=description)
        self._dependencies[target].append(link)
        self._reverse_deps[source].append(link)

    def update_status(self, organ: str, status: str) -> None:
        """更新器官状态 (用于诊断)。"""
        self._organ_status[organ] = status

    def diagnose(self, organ: str, symptom: str = "") -> CausalDiagnosis:
        """诊断指定器官的故障根因。

        Args:
            organ: 症状器官
            symptom: 症状描述

        Returns:
            CausalDiagnosis
        """
        # 找到所有可能的原因 (反向因果链)
        candidates: list[RootCause] = []
        visited: set[str] = set()

        def _trace(current: str, depth: int = 0, prob: float = 1.0) -> None:
            if depth > 5 or current in visited:
                return
            visited.add(current)

            deps = self._dependencies.get(current, [])
            for link in deps:
                source_status = self._organ_status.get(link.source, "unknown")
                # 如果源器官状态异常, 提高它是根因的概率
                boost = 0.5 if source_status == "degraded" else 0.3
                if source_status == "failing":
                    boost = 0.8

                root_prob = prob * link.strength * boost
                if root_prob > 0.1:
                    candidates.append(RootCause(
                        organ=link.source,
                        probability=round(root_prob, 3),
                        evidence=(f"{link.source} → {current} (强度={link.strength})",
                                 f"{link.source} 状态={source_status}"),
                        suggestion=f"检查 {link.source} 的健康状态并尝试修复",
                    ))
                _trace(link.source, depth + 1, root_prob)

        _trace(organ)

        # 按概率排序
        candidates.sort(key=lambda x: x.probability, reverse=True)

        diagnosis = CausalDiagnosis(
            symptom_organ=organ,
            symptom=symptom,
            root_causes=tuple(candidates[:5]),
            total_candidates=len(candidates),
        )
        self._diagnoses.append(diagnosis)
        if len(self._diagnoses) > 100:
            self._diagnoses = self._diagnoses[-100:]
        return diagnosis

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """获取因果依赖图 (用于可视化)。"""
        graph: dict[str, list[str]] = {}
        for target, links in self._dependencies.items():
            graph[target] = [l.source for l in links]
        return graph

    def get_stats(self) -> dict[str, Any]:
        return {
            "dependencies": sum(len(v) for v in self._dependencies.values()),
            "organs_tracked": len(self._organ_status),
            "diagnoses": len(self._diagnoses),
        }

    def clear(self) -> None:
        self._dependencies.clear()
        self._reverse_deps.clear()
        self._organ_status.clear()
        self._diagnoses.clear()
