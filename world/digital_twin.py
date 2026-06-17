"""Digital Twin Engine — 实时系统镜像 (L7)。

生命体的"自我镜像" — 持续维护系统的"数字孪生"。
不仅知道"现在是什么状态", 还能预测"如果执行X, 状态会变成Y"。

使用方式:
    twin = DigitalTwinEngine()
    twin.update_organ("perception/window_watcher", {"status": "healthy"})
    snapshot = twin.get_snapshot()
    prediction = twin.predict("关闭 VS Code", {"app": "code.exe"})
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.dtwin")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OrganMirror:
    """单个器官的镜像状态。"""
    name: str
    status: str = "unknown"
    params: dict[str, Any] = field(default_factory=dict)
    last_update: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SystemSnapshot:
    """系统快照 (数字孪生全貌)。"""
    organs: tuple[OrganMirror, ...]
    total_organs: int
    healthy_organs: int
    degraded_organs: int
    timestamp: float = field(default_factory=time.time)

    @property
    def health_ratio(self) -> float:
        return self.healthy_organs / max(self.total_organs, 1)


@dataclass(frozen=True)
class Prediction:
    """预测结果。"""
    action: str
    expected_outcome: str
    confidence: float
    affected_organs: tuple[str, ...] = ()
    risk_level: float = 0.0


# ═══════════════════════════════════════════════════════════════
# DigitalTwinEngine
# ═══════════════════════════════════════════════════════════════

class DigitalTwinEngine:
    """实时系统数字孪生。

    使用方式:
        twin = DigitalTwinEngine()
        twin.update_organ("window_watcher", {"status": "healthy"})
        snap = twin.get_snapshot()
        pred = twin.predict("restart window_watcher")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._organs: dict[str, OrganMirror] = {}
        self._snapshots: list[SystemSnapshot] = []
        self._predictions: list[Prediction] = []

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def update_organ(self, name: str, params: dict[str, Any]) -> None:
        """更新器官镜像状态。"""
        with self._lock:
            self._organs[name] = OrganMirror(
                name=name,
                status=params.get("status", "unknown"),
                params=params,
            )

    def get_snapshot(self) -> SystemSnapshot:
        """获取当前系统快照。"""
        with self._lock:
            organs = tuple(self._organs.values())
            total = len(organs)
            healthy = sum(1 for o in organs if o.status == "healthy")
            degraded = sum(1 for o in organs
                          if o.status in ("degraded", "failing", "offline"))

        snap = SystemSnapshot(
            organs=organs, total_organs=total,
            healthy_organs=healthy, degraded_organs=degraded,
        )
        self._snapshots.append(snap)
        if len(self._snapshots) > 100:
            self._snapshots = self._snapshots[-100:]
        return snap

    def predict(self, action: str, context: dict[str, Any] | None = None) -> Prediction:
        """预测操作对系统的影响。

        Args:
            action: 操作描述
            context: 额外上下文

        Returns:
            Prediction
        """
        context = context or {}
        snap = self.get_snapshot()

        # 分析受影响器官
        affected: list[str] = []
        risk = 0.0

        action_lower = action.lower()
        for org in snap.organs:
            if org.name.lower() in action_lower:
                affected.append(org.name)
                if org.status != "healthy":
                    risk += 0.3

        # 风险操作检测
        risky_kw = ["restart", "stop", "kill", "delete", "remove", "reset"]
        if any(k in action_lower for k in risky_kw):
            risk += 0.2

        confidence = max(0.3, 1.0 - risk)

        outcome = (
            f"执行 '{action}' 将影响 {len(affected)} 个器官, "
            f"当前系统健康度: {snap.health_ratio:.0%}"
        ) if affected else (
            f"执行 '{action}' 不会直接影响核心器官"
        )

        pred = Prediction(
            action=action,
            expected_outcome=outcome,
            confidence=round(confidence, 3),
            affected_organs=tuple(affected),
            risk_level=round(min(risk, 1.0), 3),
        )
        self._predictions.append(pred)
        if len(self._predictions) > 100:
            self._predictions = self._predictions[-100:]
        return pred

    def get_history(self, limit: int = 20) -> list[SystemSnapshot]:
        return self._snapshots[-limit:]

    def get_stats(self) -> dict[str, Any]:
        snap = self.get_snapshot()
        return {
            "total_organs": snap.total_organs,
            "healthy": snap.healthy_organs,
            "degraded": snap.degraded_organs,
            "health_ratio": round(snap.health_ratio, 3),
            "snapshots": len(self._snapshots),
            "predictions": len(self._predictions),
        }

    def clear(self) -> None:
        with self._lock:
            self._organs.clear()
            self._snapshots.clear()
            self._predictions.clear()
