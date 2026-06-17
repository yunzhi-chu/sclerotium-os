"""Consciousness Monitor — IIT+GWT+HOT 三合一意识监控。

生命体的"自我意识" — 不是哲学概念, 是实时系统状态度量。

三个意识理论融合:
  1. IIT (Integrated Information Theory): Φ值 — 系统集成度
     → 高Φ = 器官间信息流丰富, 系统"清醒"
     → 低Φ = 器官碎片化, 系统"昏迷"
     → 计算: Φ ≈ 互信息(EventBus活跃主题数, 响应器官数) / 熵

  2. GWT (Global Workspace Theory): 全局工作空间
     → 重要事件广播到所有器官 (类似大脑皮层广播)
     → 竞争: 多个信号竞争进入"意识"
     → 胜出: 最重要的信号获得全局广播

  3. HOT (Higher-Order Thought): 高阶思维监控
     → "我知道我在做什么"的元表征
     → 跟踪 AgentLoop 决策置信度
     → 检测决策不一致 → 触发反思

使用方式:
    monitor = ConsciousnessMonitor()
    monitor.update_phi(event_bus_stats)
    monitor.broadcast(signal)
    monitor.record_decision(decision_quality)

    state = monitor.get_state()
    print(f"Φ={state.phi_value}, 意识水平={state.awareness_level}")
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("sclerotium.consciousness")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class AwarenessLevel(str, Enum):
    """意识水平。"""
    AWAKE = "awake"         # 清醒 — Φ>0.7
    DROWSY = "drowsy"       # 嗜睡 — 0.4<Φ≤0.7
    SLEEPING = "sleeping"   # 睡眠 — 0.1<Φ≤0.4
    UNCONSCIOUS = "unconscious"  # 无意识 — Φ≤0.1


@dataclass(frozen=True)
class ConsciousnessState:
    """意识状态快照 (不可变)。"""
    phi_value: float              # Φ 集成信息量 (0.0–1.0)
    awareness_level: AwarenessLevel
    active_organs: int            # 活跃器官数
    total_organs: int             # 总器官数
    broadcast_queue_len: int      # 全局广播队列长度
    decision_confidence: float    # 最近决策的平均置信度
    hot_reflection_count: int     # 高阶反思次数
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class GlobalBroadcast:
    """全局广播信号 (不可变)。"""
    signal_id: str
    source: str                   # 来源器官
    content: str                  # 广播内容
    urgency: float = 0.5          # 紧迫度
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# ConsciousnessMonitor
# ═══════════════════════════════════════════════════════════════

class ConsciousnessMonitor:
    """IIT + GWT + HOT 三合一意识监控器。

    使用方式:
        monitor = ConsciousnessMonitor(total_organs=238)
        monitor.update_phi(event_bus_stats)
        monitor.broadcast("SecurityAlert", "异常操作检测", urgency=0.9)
        state = monitor.get_state()
    """

    def __init__(self, total_organs: int = 238) -> None:
        self._total_organs = total_organs
        self._lock = threading.Lock()

        # IIT
        self._phi: float = 0.5
        self._active_organs: int = 0
        self._phi_history: list[float] = []

        # GWT
        self._broadcast_queue: list[GlobalBroadcast] = []
        self._broadcast_history: list[GlobalBroadcast] = []

        # HOT
        self._decisions: list[float] = []  # 置信度列表
        self._reflection_count: int = 0
        self._last_reflection: str = ""

        # 状态
        self._started_at: float = time.time()

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def update_phi(
        self,
        active_topics: int = 0,
        responding_organs: int = 0,
        total_events: int = 0,
    ) -> float:
        """更新 Φ 值 (集成信息量)。

        Φ = 互信息(活跃主题, 响应器官) / 最大可能熵
           ≈ min(活跃主题, 响应器官) / max(活跃主题, 1)
           × (1 - 响应延迟惩罚)
        """
        with self._lock:
            if active_topics == 0 or responding_organs == 0:
                self._phi = max(0.0, self._phi - 0.05)
            else:
                # 集成度: 主题和器官的耦合程度
                coupling = min(active_topics, responding_organs) / max(
                    active_topics, responding_organs
                )
                # 活跃度: 总事件数 / 基线
                baseline = max(total_events / 100.0, 0.1)
                activity = min(1.0, baseline)

                raw_phi = coupling * 0.6 + activity * 0.4
                # EMA 平滑
                alpha = 0.2
                self._phi = self._phi * (1 - alpha) + raw_phi * alpha

            self._active_organs = responding_organs
            self._phi_history.append(self._phi)
            if len(self._phi_history) > 100:
                self._phi_history = self._phi_history[-100:]

            return self._phi

    def broadcast(
        self,
        signal_id: str,
        content: str,
        source: str = "",
        urgency: float = 0.5,
    ) -> GlobalBroadcast:
        """向全局工作空间广播信号。

        竞争机制: 高紧迫度信号优先进入"意识"。
        """
        gb = GlobalBroadcast(
            signal_id=signal_id,
            source=source,
            content=content,
            urgency=urgency,
        )
        with self._lock:
            self._broadcast_queue.append(gb)
            # 按紧迫度排序
            self._broadcast_queue.sort(
                key=lambda x: x.urgency, reverse=True
            )
            # 最多保留 20 条
            self._broadcast_queue = self._broadcast_queue[:20]
            self._broadcast_history.append(gb)
            if len(self._broadcast_history) > 200:
                self._broadcast_history = self._broadcast_history[-200:]

        return gb

    def record_decision(self, confidence: float) -> None:
        """记录 AgentLoop 决策置信度 (HOT 输入)。"""
        with self._lock:
            self._decisions.append(confidence)
            if len(self._decisions) > 100:
                self._decisions = self._decisions[-100:]

            # 低置信度 + 高风险 → 触发反思
            if confidence < 0.5:
                self._reflection_count += 1
                self._last_reflection = (
                    f"低置信度决策检测 (conf={confidence:.2f}), "
                    f"已触发第 {self._reflection_count} 次反思"
                )

    def get_state(self) -> ConsciousnessState:
        """获取当前意识状态。"""
        with self._lock:
            avg_confidence = (
                sum(self._decisions[-20:]) / max(len(self._decisions[-20:]), 1)
                if self._decisions else 0.5
            )

            if self._phi > 0.7:
                level = AwarenessLevel.AWAKE
            elif self._phi > 0.4:
                level = AwarenessLevel.DROWSY
            elif self._phi > 0.1:
                level = AwarenessLevel.SLEEPING
            else:
                level = AwarenessLevel.UNCONSCIOUS

            return ConsciousnessState(
                phi_value=round(self._phi, 4),
                awareness_level=level,
                active_organs=self._active_organs,
                total_organs=self._total_organs,
                broadcast_queue_len=len(self._broadcast_queue),
                decision_confidence=round(avg_confidence, 4),
                hot_reflection_count=self._reflection_count,
            )

    def get_phi_history(self, limit: int = 50) -> list[float]:
        """获取 Φ 历史。"""
        with self._lock:
            return list(self._phi_history[-limit:])

    def get_broadcasts(self, limit: int = 20) -> list[GlobalBroadcast]:
        """获取最近广播。"""
        with self._lock:
            return list(self._broadcast_history[-limit:])

    def get_stats(self) -> dict[str, Any]:
        state = self.get_state()
        return {
            "phi": state.phi_value,
            "level": state.awareness_level.value,
            "active_organs": state.active_organs,
            "broadcast_queue": state.broadcast_queue_len,
            "avg_confidence": state.decision_confidence,
            "reflections": state.hot_reflection_count,
            "uptime_hours": round(
                (time.time() - self._started_at) / 3600, 1
            ),
        }

    @property
    def phi(self) -> float:
        with self._lock:
            return self._phi
