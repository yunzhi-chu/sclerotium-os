"""FCPI Tracker — 六维适应度实时追踪。

FCPI = Functional-Coding-Coordination-Performance-Intelligence
六维适应度评分, 每维 0.0–1.0, 基于真实用户行为数据计算:

  Coding:        代码质量 (测试通过率、代码复杂度)
  Coordination:  多工具协调效率 (工具链成功率、步骤数)
  Safety:        操作安全性 (误操作率、权限拒绝率)
  Decision:      决策质量 (主动建议采纳率)
  Emergence:     涌现行为 (新模式发现频率)
  Performance:   系统性能 (响应延迟、资源消耗)

使用方式:
    tracker = FCPITracker()
    tracker.record_coding(test_pass=True, complexity=0.3)
    tracker.record_coordination(tool_chain_success=True, steps=3)
    vector = tracker.get_vector()  # FCPIVector
    print(vector.total_score)
"""

from __future__ import annotations

import time
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class FCPIDimension(Enum):
    """六维适应度维度。"""
    CODING = "coding"              # 代码质量
    COORDINATION = "coordination"  # 多工具协调
    SAFETY = "safety"              # 操作安全
    DECISION = "decision"          # 决策质量
    EMERGENCE = "emergence"        # 涌现行为
    PERFORMANCE = "performance"    # 系统性能


# 每维权重 (总和=1.0)
DEFAULT_WEIGHTS: dict[str, float] = {
    "coding": 0.20,
    "coordination": 0.15,
    "safety": 0.25,        # 安全权重最高
    "decision": 0.20,
    "emergence": 0.10,
    "performance": 0.10,
}


@dataclass(frozen=True)
class FCPIVector:
    """六维 FCPI 适应度向量 (不可变)。"""
    coding: float = 0.5
    coordination: float = 0.5
    safety: float = 0.5
    decision: float = 0.5
    emergence: float = 0.5
    performance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    generation: int = 0

    @property
    def total_score(self) -> float:
        """加权总分 (0.0–1.0)。"""
        return round(
            self.coding * DEFAULT_WEIGHTS["coding"]
            + self.coordination * DEFAULT_WEIGHTS["coordination"]
            + self.safety * DEFAULT_WEIGHTS["safety"]
            + self.decision * DEFAULT_WEIGHTS["decision"]
            + self.emergence * DEFAULT_WEIGHTS["emergence"]
            + self.performance * DEFAULT_WEIGHTS["performance"],
            4,
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "coding": self.coding,
            "coordination": self.coordination,
            "safety": self.safety,
            "decision": self.decision,
            "emergence": self.emergence,
            "performance": self.performance,
            "total": self.total_score,
        }

    def weak_dimensions(self, threshold: float = 0.4) -> list[str]:
        """返回低于阈值的维度名。"""
        dims = []
        for dim in FCPIDimension:
            val = getattr(self, dim.value)
            if val < threshold:
                dims.append(dim.value)
        return dims

    def dominant_dimension(self) -> str:
        """返回最高分维度。"""
        best = ""
        best_val = -1.0
        for dim in FCPIDimension:
            val = getattr(self, dim.value)
            if val > best_val:
                best_val = val
                best = dim.value
        return best


# ═══════════════════════════════════════════════════════════════
# FCPITracker
# ═══════════════════════════════════════════════════════════════

class FCPITracker:
    """六维适应度实时追踪器。

    每个维度使用 EMA (指数移动平均) 平滑更新,
    学习率可配, 越近的事件权重越高。

    使用方式:
        tracker = FCPITracker()
        tracker.record_coding(test_pass=True)
        tracker.record_safety(error=False)
        tracker.record_decision(suggestion_accepted=True)
        vector = tracker.get_vector()
        print(f"FCPI 总分: {vector.total_score}")
    """

    # EMA 学习率 — 越大越敏捷, 越小越平滑
    DEFAULT_ALPHA = 0.1

    def __init__(self, alpha: float = DEFAULT_ALPHA) -> None:
        self._alpha = alpha
        self._scores: dict[str, float] = {
            dim.value: 0.5 for dim in FCPIDimension
        }
        self._counts: dict[str, int] = {
            dim.value: 0 for dim in FCPIDimension
        }
        self._history: list[FCPIVector] = []
        self._generation: int = 0
        self._started_at: float = time.time()

    # ═══════════════════════════════════════════════════════
    # 记录事件
    # ═══════════════════════════════════════════════════════

    def record_coding(
        self,
        test_pass: bool = True,
        complexity: float = 0.3,
        lines_changed: int = 0,
    ) -> None:
        """记录编码事件。

        Args:
            test_pass: 测试是否通过
            complexity: 代码复杂度 (0=简单, 1=极复杂)
            lines_changed: 修改行数
        """
        # 测试通过 = 正向, 高复杂度 = 负向
        score = 0.7 if test_pass else 0.2
        if complexity > 0.7:
            score *= 0.7  # 高复杂度降低分数
        if lines_changed > 500:
            score *= 0.8  # 大批量修改有风险
        self._update("coding", score)

    def record_coordination(
        self,
        tool_chain_success: bool = True,
        steps: int = 1,
        tools_used: int = 1,
    ) -> None:
        """记录多工具协调事件。

        Args:
            tool_chain_success: 工具链是否全部成功
            steps: 步骤数
            tools_used: 使用工具数
        """
        score = 0.8 if tool_chain_success else 0.3
        # 多工具协调成功加分
        if tools_used >= 3 and tool_chain_success:
            score = min(1.0, score + 0.1)
        # 步骤太多降低分数
        if steps > 10:
            score *= 0.8
        self._update("coordination", score)

    def record_safety(
        self,
        error: bool = False,
        permission_denied: bool = False,
        risky_operation: bool = False,
    ) -> None:
        """记录安全事件。

        Args:
            error: 是否发生错误
            permission_denied: 权限是否被拒绝
            risky_operation: 是否尝试危险操作
        """
        if error or permission_denied:
            self._update("safety", 0.1)  # 严重扣分
        elif risky_operation:
            self._update("safety", 0.3)
        else:
            self._update("safety", 0.95)  # 安全操作

    def record_decision(
        self,
        suggestion_accepted: bool = False,
        suggestion_quality: float = 0.5,
    ) -> None:
        """记录决策事件。

        Args:
            suggestion_accepted: 建议被采纳
            suggestion_quality: 建议质量 (0–1)
        """
        if suggestion_accepted:
            score = 0.7 + suggestion_quality * 0.3
        else:
            score = suggestion_quality * 0.4
        self._update("decision", score)

    def record_emergence(
        self,
        new_pattern_detected: bool = False,
        pattern_significance: float = 0.3,
    ) -> None:
        """记录涌现事件。

        Args:
            new_pattern_detected: 是否发现新模式
            pattern_significance: 模式重要性
        """
        if new_pattern_detected:
            score = 0.5 + pattern_significance * 0.5
        else:
            score = 0.3  # 无涌现, 基线
        self._update("emergence", score)

    def record_performance(
        self,
        latency_ms: float = 100.0,
        memory_mb: float = 50.0,
    ) -> None:
        """记录性能事件。

        Args:
            latency_ms: 响应延迟 (毫秒)
            memory_mb: 内存占用 (MB)
        """
        # 延迟: <100ms 优秀, >2000ms 差
        latency_score = max(0.0, 1.0 - latency_ms / 2000.0)
        # 内存: <100MB 优秀, >1000MB 差
        memory_score = max(0.0, 1.0 - memory_mb / 1000.0)
        score = (latency_score + memory_score) / 2
        self._update("performance", score)

    # ═══════════════════════════════════════════════════════
    # 向量和统计
    # ═══════════════════════════════════════════════════════

    def snapshot(self) -> FCPIVector:
        """Alias for get_vector — used by EvolutionLoop."""
        return self.get_vector()

    def get_vector(self) -> FCPIVector:
        """获取当前 FCPI 向量。"""
        return FCPIVector(
            coding=round(self._scores["coding"], 4),
            coordination=round(self._scores["coordination"], 4),
            safety=round(self._scores["safety"], 4),
            decision=round(self._scores["decision"], 4),
            emergence=round(self._scores["emergence"], 4),
            performance=round(self._scores["performance"], 4),
            generation=self._generation,
        )

    def snapshot(self) -> FCPIVector:
        """快照当前分数并推入历史。"""
        vec = self.get_vector()
        self._history.append(vec)
        return vec

    def get_history(self, limit: int = 20) -> list[FCPIVector]:
        """获取历史向量。"""
        return self._history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """获取追踪器统计。"""
        vec = self.get_vector()
        return {
            "current": vec.to_dict(),
            "generation": self._generation,
            "total_records": sum(self._counts.values()),
            "records_by_dim": dict(self._counts),
            "weak_dimensions": vec.weak_dimensions(),
            "dominant": vec.dominant_dimension(),
            "history_length": len(self._history),
            "uptime_hours": round((time.time() - self._started_at) / 3600, 1),
        }

    def new_generation(self) -> FCPIVector:
        """开始新的一代, 快照当前分数。"""
        self._generation += 1
        return self.snapshot()

    def reset(self) -> None:
        """重置所有分数到初始值。"""
        self._scores = {dim.value: 0.5 for dim in FCPIDimension}
        self._counts = {dim.value: 0 for dim in FCPIDimension}
        self._history.clear()
        self._generation = 0

    # ═══════════════════════════════════════════════════════
    # Internal — EMA 更新
    # ═══════════════════════════════════════════════════════

    def _update(self, dimension: str, score: float) -> None:
        """EMA 更新维度分数。"""
        clamped = max(0.0, min(1.0, score))
        old = self._scores[dimension]
        new = old * (1 - self._alpha) + clamped * self._alpha
        self._scores[dimension] = new
        self._counts[dimension] += 1
