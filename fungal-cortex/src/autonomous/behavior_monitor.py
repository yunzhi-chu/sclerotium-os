"""L4 M6b: BehaviorMonitor — "内感受网络"(Interoception Network) 行为监控器.

Biological Metaphor:
  脑岛(Insula)和前扣带回(ACC)——大脑的"内感受网络":
  持续监测心跳/呼吸/胃肠蠕动/膀胱充盈/体温。
  异常→产生"感觉"→引起注意→驱动行为纠正。
  (你不需要看手表就知道自己饿了/渴了/需要上厕所)

  三类告警(对应三种"感觉"):
    param_drift(20周期滚动std>0.05) = 眩晕(vestibular)
    signal_extreme(极端信号>50%) = 剧痛(nociceptive)
    model_abuse(单模块>500次调用) = 心悸(palpitation)

  指标缓冲区:
    param_history = 血糖曲线(连续监测)
    signal_history = 心电图(ECG)
    skill_calls = 呼吸频率计

Reference: Insula+ACC interoception theory (Craig 2002, Barrett 2017)
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class AnomalyLevel(str, Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BehaviorProfile:
    """Learned normal behavior — like physiological baseline."""

    profile_id: str
    metric_name: str
    mean: float = 0.0
    std: float = 0.0
    count: int = 0
    last_updated: float = field(default_factory=time.time)

    def z_score(self, value: float) -> float:
        return (value - self.mean) / max(self.std, 0.001)


@dataclass
class AnomalyAlert:
    """A detected anomaly — like an interoceptive sensation."""

    alert_id: str
    alert_type: str  # "param_drift", "signal_extreme", "model_abuse"
    metric_name: str
    value: float
    z_score: float = 0.0
    level: AnomalyLevel = AnomalyLevel.NORMAL
    description: str = ""
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False


class BehaviorMonitor:
    """Insula+ACC interoception — detects drift, extremes, and overuse.

    Config:
      - drift_window: rolling window size for drift detection
      - drift_threshold: std threshold for param_drift
      - extreme_threshold: fraction threshold for signal_extreme
      - abuse_threshold: call count threshold for model_abuse
    """

    def __init__(
        self, drift_window: int = 20, drift_threshold: float = 0.05,
        extreme_threshold: float = 0.5, abuse_threshold: int = 500,
    ) -> None:
        self._drift_window = drift_window
        self._drift_threshold = drift_threshold
        self._extreme_threshold = extreme_threshold
        self._abuse_threshold = abuse_threshold

        self._profiles: dict[str, BehaviorProfile] = {}
        self._param_history: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=drift_window))
        self._signal_history: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=100))
        self._skill_calls: dict[str, int] = defaultdict(int)
        self._alerts: list[AnomalyAlert] = []
        self._logger = CortexLogger("behavior_monitor")

    def observe_param(self, param_name: str, value: float) -> AnomalyAlert | None:
        """Observe a parameter — like blood glucose reading."""
        self._param_history[param_name].append(value)
        profile = self._get_profile(param_name)
        self._update_profile(profile, value)

        if profile.count < self._drift_window:
            return None

        # Drift detection
        recent = list(self._param_history[param_name])
        recent_std = math.sqrt(
            sum((v - profile.mean) ** 2 for v in recent) / len(recent)
        ) if len(recent) > 1 else 0.0

        if recent_std > self._drift_threshold and profile.std > 0:
            return self._create_alert(
                "param_drift", param_name, recent_std,
                f"Param '{param_name}' rolling std={recent_std:.4f} > {self._drift_threshold}",
            )
        return None

    def observe_signal(self, signal_name: str, value: float) -> AnomalyAlert | None:
        """Observe a signal — checking for extremes."""
        self._signal_history[signal_name].append(value)
        if abs(value) > self._extreme_threshold:
            return self._create_alert(
                "signal_extreme", signal_name, value,
                f"Signal '{signal_name}' = {value:.3f} (extreme > {self._extreme_threshold})",
            )
        return None

    def observe_skill_call(self, skill_name: str, module_id: str) -> AnomalyAlert | None:
        """Record a skill call — detect model abuse."""
        self._skill_calls[module_id] += 1
        count = self._skill_calls[module_id]
        if count > self._abuse_threshold:
            return self._create_alert(
                "model_abuse", module_id, count,
                f"Module '{module_id}' called {count} times (threshold={self._abuse_threshold})",
            )
        return None

    def snapshot(self) -> dict[str, Any]:
        """Take a complete interoceptive snapshot."""
        alerts_active = [a for a in self._alerts if not a.acknowledged]
        return {
            "profiles": len(self._profiles),
            "active_alerts": len(alerts_active),
            "alert_breakdown": {
                t: sum(1 for a in alerts_active if a.alert_type == t)
                for t in ("param_drift", "signal_extreme", "model_abuse")
            },
            "skill_call_leaders": sorted(
                self._skill_calls.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    def acknowledge(self, alert_id: str) -> bool:
        for a in self._alerts:
            if a.alert_id == alert_id:
                a.acknowledged = True
                return True
        return False

    def _get_profile(self, name: str) -> BehaviorProfile:
        if name not in self._profiles:
            self._profiles[name] = BehaviorProfile(profile_id=self._gen_id(name), metric_name=name)
        return self._profiles[name]

    def _update_profile(self, profile: BehaviorProfile, value: float) -> None:
        old_mean = profile.mean
        profile.count += 1
        profile.mean += (value - old_mean) / profile.count
        if profile.count > 1:
            profile.std = math.sqrt(
                ((profile.count - 2) * profile.std ** 2 + (value - old_mean) * (value - profile.mean))
                / (profile.count - 1)
            )
        profile.last_updated = time.time()

    def _create_alert(self, alert_type: str, metric_name: str,
                      value: float, description: str) -> AnomalyAlert:
        profile = self._profiles.get(metric_name)
        z = profile.z_score(value) if profile and profile.std > 0 else 0.0
        abs_z = abs(z)
        level = AnomalyLevel.CRITICAL if abs_z > 5 else (
            AnomalyLevel.HIGH if abs_z > 4 else (
                AnomalyLevel.ELEVATED if abs_z > 3 else AnomalyLevel.NORMAL
            )
        )
        alert = AnomalyAlert(
            alert_id=self._gen_id(alert_type),
            alert_type=alert_type, metric_name=metric_name,
            value=value, z_score=z, level=level, description=description,
        )
        self._alerts.append(alert)
        if len(self._alerts) > 1000:
            self._alerts = self._alerts[-1000:]
        return alert

    @staticmethod
    def _gen_id(prefix: str) -> str:
        return hashlib.md5(f"{prefix}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "profiles": len(self._profiles),
            "alerts": len(self._alerts),
            "unacknowledged": sum(1 for a in self._alerts if not a.acknowledged),
        }
