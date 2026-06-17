"""Liquid Perceptor — LNN ODE 连续时间感知 (L1)。

替代 WindowWatcher 的离散轮询, 升级为连续时间状态追踪。

核心: 使用简单的 ODE (常微分方程) 追踪用户活动状态
  - 窗口切换 → 状态变量更新
  - 时间流逝 → 状态自然衰减
  - 输出: 连续的活跃度曲线, 而非离散事件

使用方式:
    lp = LiquidPerceptor(tau=30.0)  # 30秒时间常数
    lp.update("code.exe", 0.8)       # 切换到 VS Code
    lp.update("chrome.exe", 0.4)     # 切换到 Chrome
    time.sleep(5)
    state = lp.get_state()           # 连续时间状态
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.liquid_perceptor")


@dataclass(frozen=True)
class LiquidState:
    """连续时间感知状态。"""
    current_app: str = ""
    activity_level: float = 0.5       # 0.0–1.0 当前活跃度
    switching_frequency: float = 0.0   # 切换频率 (次/分钟)
    focus_depth: float = 0.5           # 专注深度 (连续在同一应用的时间)
    idle_probability: float = 0.0      # 空闲概率
    timestamp: float = field(default_factory=time.time)


class LiquidPerceptor:
    """连续时间窗口感知器 (LNN ODE 简化版)。

    使用 ODE dx/dt = -(x - u)/tau 追踪应用状态:
      - x: 内部状态 (连续)
      - u: 输入信号 (离散)
      - tau: 时间常数 (越大越平滑)

    使用方式:
        lp = LiquidPerceptor(tau=30.0)
        lp.update("code.exe", 0.8)
        state = lp.get_state()
    """

    def __init__(self, tau: float = 30.0) -> None:
        self._tau = tau                  # 时间常数 (秒)
        self._state: float = 0.5         # 内部状态
        self._current_app: str = ""
        self._last_update: float = time.time()
        self._last_app: str = ""
        self._switch_times: list[float] = []
        self._app_durations: dict[str, float] = {}
        self._app_start: float = time.time()

    def update(self, app_name: str, intensity: float = 0.5) -> float:
        """输入新信号, 更新内部状态。

        Args:
            app_name: 应用名
            intensity: 信号强度 (0.0–1.0)

        Returns:
            更新后的内部状态值
        """
        now = time.time()
        dt = now - self._last_update

        # ODE: dx/dt = -(x - u)/tau
        # 离散化: x_new = x + dt * (u - x) / tau
        if dt > 0 and dt < 300:  # 忽略 >5分钟的间隔
            decay = math.exp(-dt / self._tau)
            self._state = self._state * decay + intensity * (1 - decay)
        else:
            self._state = intensity

        # 切换检测
        if app_name != self._last_app and self._last_app:
            self._switch_times.append(now)
            # 记录上一个应用的使用时长
            duration = now - self._app_start
            self._app_durations[self._last_app] = (
                self._app_durations.get(self._last_app, 0) + duration
            )

        self._current_app = app_name
        self._last_app = app_name
        self._app_start = now
        self._last_update = now

        return self._state

    def get_state(self) -> LiquidState:
        """获取当前连续状态。"""
        now = time.time()

        # 切换频率 (最近60秒)
        recent_switches = [
            t for t in self._switch_times if now - t < 60
        ]
        switch_freq = len(recent_switches)

        # 专注深度 (当前应用持续时间 / 时间常数)
        current_duration = now - self._app_start if self._app_start > 0 else 0
        focus_depth = min(1.0, current_duration / (self._tau * 2))

        # 空闲概率 (低活跃度)
        idle_prob = max(0.0, 1.0 - self._state * 2)

        return LiquidState(
            current_app=self._current_app,
            activity_level=round(self._state, 3),
            switching_frequency=round(switch_freq, 3),
            focus_depth=round(focus_depth, 3),
            idle_probability=round(idle_prob, 3),
        )

    def get_app_usage(self, top_n: int = 5) -> dict[str, float]:
        """获取应用使用时长排名。"""
        total = sum(self._app_durations.values()) or 1
        sorted_apps = sorted(
            self._app_durations.items(),
            key=lambda x: x[1], reverse=True,
        )
        return {
            app: round(duration / total, 3)
            for app, duration in sorted_apps[:top_n]
        }

    def reset(self) -> None:
        self._state = 0.5
        self._current_app = ""
        self._last_update = time.time()
        self._last_app = ""
        self._switch_times.clear()
        self._app_durations.clear()
        self._app_start = time.time()
