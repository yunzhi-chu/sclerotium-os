"""Active Inference Agent — 自由能原理行动选择 (L7)。

生命体的"决策大脑" — 不是规则引擎, 是最小化预期自由能(EFE)。

核心概念:
  - 预期自由能 (Expected Free Energy, EFE):
    EFE = Pragmatic(实现目标) + Epistemic(减少不确定)
  - 行动选择: 选择最小化 EFE 的下一步行动
  - 自然收敛: 当 EFE 低于阈值时停止, 不需要硬编码停止规则

替代 AgentLoop 的 "30轮硬停止":
  - 不再需要 max_rounds
  - 当所有行动的 EFE > 当前状态价值 → 自然停止
  - 当 pragmatic_value 足够低 → 目标已达成

使用方式:
    agent = ActiveInferenceAgent()
    agent.add_action("file_read", pragmatic=0.8, epistemic=0.2)
    agent.add_action("file_write", pragmatic=0.6, epistemic=0.5)
    policy = agent.select_action()
    if policy.should_stop:
        return  # 自然停止
"""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.active_inference")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ActionOption:
    """可选行动。"""
    name: str
    pragmatic_value: float = 0.5    # 实现目标的预期价值 (0-1)
    epistemic_value: float = 0.3   # 减少不确定性的价值 (0-1)
    risk: float = 0.0              # 风险惩罚
    cost: float = 0.1              # 执行成本


@dataclass(frozen=True)
class ActionPolicy:
    """行动策略 (不可变)。"""
    action: str
    efe: float                     # 预期自由能 (越低越好)
    should_stop: bool = False
    confidence: float = 0.5
    reasoning: str = ""


@dataclass(frozen=True)
class AIState:
    """主动推理状态。"""
    total_actions: int
    stop_count: int
    avg_efe: float
    stop_rate: float


# ═══════════════════════════════════════════════════════════════
# ActiveInferenceAgent
# ═══════════════════════════════════════════════════════════════

class ActiveInferenceAgent:
    """基于自由能原理的行动选择器。

    使用方式:
        agent = ActiveInferenceAgent(stop_threshold=0.15)
        agent.add_action("file_read", pragmatic=0.8, epistemic=0.1, risk=0.0)
        agent.add_action("file_write", pragmatic=0.5, epistemic=0.4, risk=0.2)
        policy = agent.select_action()
        if policy.should_stop:
            print("目标已达成, 自然停止")
        else:
            execute(policy.action)
    """

    def __init__(self, stop_threshold: float = 0.15) -> None:
        self._stop_threshold = stop_threshold
        self._actions: list[ActionOption] = []
        self._lock = threading.RLock()
        self._total_actions: int = 0
        self._stop_decisions: int = 0
        self._efe_history: list[float] = []

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def add_action(
        self,
        name: str,
        pragmatic: float = 0.5,
        epistemic: float = 0.3,
        risk: float = 0.0,
        cost: float = 0.1,
    ) -> None:
        """注册一个可选行动。

        Args:
            name: 行动名称
            pragmatic: 实现目标的预期价值
            epistemic: 减少不确定性的价值 (探索价值)
            risk: 风险惩罚
            cost: 执行成本
        """
        with self._lock:
            self._actions.append(ActionOption(
                name=name, pragmatic_value=pragmatic,
                epistemic_value=epistemic, risk=risk, cost=cost,
            ))

    def select_action(self) -> ActionPolicy:
        """选择最小化 EFE 的下一步行动。

        如果所有行动的 EFE 都高于阈值, 返回 should_stop=True。
        """
        self._total_actions += 1

        with self._lock:
            if not self._actions:
                self._stop_decisions += 1
                return ActionPolicy(
                    action="", efe=0.0, should_stop=True,
                    confidence=0.0, reasoning="无可选行动",
                )

            # 计算每个行动的 EFE
            best: ActionOption | None = None
            best_efe = float("inf")

            for action in self._actions:
                # EFE = -(pragmatic + epistemic) + risk + cost
                efe = (
                    -(action.pragmatic_value + action.epistemic_value)
                    + action.risk
                    + action.cost
                )
                if efe < best_efe:
                    best_efe = efe
                    best = action

            if best is None:
                self._stop_decisions += 1
                return ActionPolicy(
                    action="", efe=0.0, should_stop=True,
                    confidence=0.0, reasoning="无有效行动",
                )

            # 判断是否应该停止
            # 当最佳行动的 EFE > -阈值 时 (即 pragmatic+epistemic 不够高)
            should_stop = best_efe > -self._stop_threshold

            if should_stop:
                self._stop_decisions += 1
                reasoning = (
                    f"所有行动的预期自由能过高 (min_EFE={best_efe:.3f}), "
                    f"当前状态已达到目标, 自然停止"
                )
            else:
                reasoning = (
                    f"选择 '{best.name}': EFE={best_efe:.3f} "
                    f"(pragmatic={best.pragmatic_value}, "
                    f"epistemic={best.epistemic_value})"
                )

            self._efe_history.append(best_efe)
            if len(self._efe_history) > 200:
                self._efe_history = self._efe_history[-200:]

            return ActionPolicy(
                action=best.name,
                efe=round(best_efe, 4),
                should_stop=should_stop,
                confidence=round(1.0 / (1.0 + abs(best_efe)), 3),
                reasoning=reasoning,
            )

    def clear_actions(self) -> None:
        with self._lock:
            self._actions.clear()

    def get_state(self) -> AIState:
        with self._lock:
            avg = (
                sum(self._efe_history[-50:]) / max(len(self._efe_history[-50:]), 1)
                if self._efe_history else 0.0
            )
        return AIState(
            total_actions=self._total_actions,
            stop_count=self._stop_decisions,
            avg_efe=round(avg, 4),
            stop_rate=round(
                self._stop_decisions / max(self._total_actions, 1), 3
            ),
        )

    def reset(self) -> None:
        with self._lock:
            self._actions.clear()
            self._total_actions = 0
            self._stop_decisions = 0
            self._efe_history.clear()
