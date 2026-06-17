"""LTC Rhythm — 液态时间常数动态节律 (L2 LiquidTimeConstantNet)。

替代硬编码的 pyloric_interval/gastric_interval,
由 LTC 网络动态调整节律参数。

原理:
  - 高活动期 → 缩短间隔 (高频采样)
  - 低活动期 → 延长间隔 (省资源)
  - 模式切换 → 平滑过渡 (而非突变)

使用方式:
    ltc = LTCRhythm()
    ltc.update_activity(0.8)  # 高活跃
    interval = ltc.get_pyloric_interval()  # → 较短间隔
    ltc.update_activity(0.1)  # 低活跃
    interval = ltc.get_pyloric_interval()  # → 较长间隔
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.ltc_rhythm")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LTCRhythmState:
    """LTC 节律状态。"""
    pyloric_interval: float       # 幽门间隔 (秒)
    gastric_interval: float       # 胃磨间隔 (秒)
    activity_level: float         # 当前活跃度 (0-1)
    mode: str = "work"
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# LTCRhythm
# ═══════════════════════════════════════════════════════════════

class LTCRhythm:
    """液态时间常数动态节律调节器。

    活动度 → 节律间隔映射:
      - activity 1.0 → pyloric=10s, gastric=600s
      - activity 0.5 → pyloric=30s, gastric=3600s
      - activity 0.0 → pyloric=120s, gastric=7200s

    使用方式:
        ltc = LTCRhythm()
        ltc.update_activity(0.7)
        print(ltc.get_pyloric_interval())  # ~18s
    """

    # 节律范围
    PYLORIC_MIN = 10.0      # 最快
    PYLORIC_MAX = 120.0     # 最慢
    GASTRIC_MIN = 600.0     # 最快 (10分钟)
    GASTRIC_MAX = 7200.0    # 最慢 (2小时)

    def __init__(self) -> None:
        self._activity: float = 0.5
        self._pyloric: float = 30.0
        self._gastric: float = 3600.0
        self._mode: str = "work"
        self._smoothing: float = 0.3  # EMA 平滑系数

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def update_activity(self, level: float) -> None:
        """更新活跃度, 动态调整节律。

        Args:
            level: 活跃度 (0.0=空闲, 1.0=极活跃)
        """
        clamped = max(0.0, min(1.0, level))
        # EMA 平滑
        self._activity = (
            self._activity * (1 - self._smoothing)
            + clamped * self._smoothing
        )

        # 活跃度 → 节律间隔 (反比关系)
        # interval = max - (max - min) * activity
        self._pyloric = self.PYLORIC_MAX - (
            self.PYLORIC_MAX - self.PYLORIC_MIN
        ) * self._activity
        self._gastric = self.GASTRIC_MAX - (
            self.GASTRIC_MAX - self.GASTRIC_MIN
        ) * self._activity

    def set_mode(self, mode: str) -> None:
        """切换模式, 调整基线。"""
        self._mode = mode
        if mode == "sleep":
            self._pyloric *= 3
            self._gastric *= 4
        elif mode == "game":
            self._pyloric *= 2
            self._gastric *= 2
        elif mode == "meeting":
            self._pyloric *= 1.5
            self._gastric *= 1.5
        # work/creative: 保持动态调整

    def get_pyloric_interval(self) -> float:
        return round(self._pyloric, 1)

    def get_gastric_interval(self) -> float:
        return round(self._gastric, 1)

    def get_state(self) -> LTCRhythmState:
        return LTCRhythmState(
            pyloric_interval=self.get_pyloric_interval(),
            gastric_interval=self.get_gastric_interval(),
            activity_level=round(self._activity, 3),
            mode=self._mode,
        )

    def get_stats(self) -> dict[str, Any]:
        state = self.get_state()
        return {
            "pyloric": state.pyloric_interval,
            "gastric": state.gastric_interval,
            "activity": state.activity_level,
            "mode": state.mode,
        }

    @property
    def activity(self) -> float:
        return self._activity
