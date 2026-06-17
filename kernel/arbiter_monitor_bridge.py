"""ArbiterMonitor Bridge — 基于用户历史的个性化Nudge策略 (L6 M8)。

替代简单的 NudgeEngine 规则式决策, 升级为:
  - 学习用户对过去通知的反应 (是否点击/是否采纳)
  - 自适应调整通知阈值 (个人化的 importance threshold)
  - 主动反思: "我上次的建议对吗?"
  - 上下文感知: 同样 importance=0.6, 在 coding 时可以打断, 在 meeting 时不行

使用方式:
    monitor = ArbiterMonitorBridge()
    monitor.record_nudge(decision_id, user_clicked=True)
    monitor.record_nudge(decision_id, user_clicked=False)

    # 替代 nudge_engine.decide():
    decision = monitor.decide(category, title, message, importance)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("sclerotium.arbiter_monitor")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class NudgeAction(int, Enum):
    SILENT = 0
    TRAY = 1
    NOTIFY = 2
    ALERT = 3


@dataclass(frozen=True)
class NudgeRecord:
    """单次Nudge记录 (不可变)。"""
    nudge_id: str
    category: str
    importance: float
    action: NudgeAction
    user_clicked: bool = False
    user_accepted: bool = False
    context: str = ""              # 当时上下文 (time/app/mode)
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class UserNudgeProfile:
    """用户Nudge偏好画像 (不可变, 持续学习)。"""
    acceptance_rate: float = 0.5
    avg_click_rate: float = 0.0
    preferred_categories: tuple[str, ...] = ()
    suppressed_categories: tuple[str, ...] = ()
    best_hours: tuple[int, ...] = ()         # 最佳通知时段
    worst_hours: tuple[int, ...] = ()        # 最差通知时段
    total_nudges: int = 0
    last_updated: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# ArbiterMonitorBridge
# ═══════════════════════════════════════════════════════════════

class ArbiterMonitorBridge:
    """个性化Nudge策略引擎 — 替代 NudgeEngine。

    核心区别:
      - 不是硬编码阈值, 是学出来的
      - 记录每次Nudge的用户反馈
      - 持续调整每个人的阈值
      - 主动反思建议质量
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: list[NudgeRecord] = []
        self._profile = UserNudgeProfile()
        self._hourly_acceptance: dict[int, list[bool]] = {}
        self._category_acceptance: dict[str, list[bool]] = {}
        self._importance_threshold: dict[str, float] = {
            "health": 0.6, "security": 0.3, "insight": 0.5,
            "maintenance": 0.4, "rhythm": 0.5, "info": 0.6,
        }
        self._total_decisions: int = 0

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def decide(
        self,
        category: str,
        title: str,
        message: str,
        importance: float,
        force: bool = False,
    ) -> NudgeAction:
        """决定是否/如何打断用户 (基于学习到的偏好)。"""
        self._total_decisions += 1

        if force or category == "security":
            return NudgeAction.ALERT

        # 获取该类别的个性化阈值
        threshold = self._importance_threshold.get(category, 0.5)

        # 根据时段调整
        hour = int(time.strftime("%H"))
        hour_accept = self._hourly_acceptance.get(hour, [])
        if hour_accept:
            accept_rate = sum(hour_accept) / len(hour_accept)
            threshold += (0.5 - accept_rate) * 0.2  # 低接受率 → 提高阈值

        # 决策
        if importance >= 0.9:
            return NudgeAction.NOTIFY
        elif importance >= threshold + 0.2:
            return NudgeAction.NOTIFY
        elif importance >= threshold:
            return NudgeAction.TRAY
        else:
            return NudgeAction.SILENT

    def record_nudge(
        self,
        nudge_id: str,
        category: str,
        importance: float,
        action: NudgeAction,
        user_clicked: bool = False,
        user_accepted: bool = False,
        context: str = "",
    ) -> None:
        """记录一次Nudge的用户反馈 (学习信号)。"""
        rec = NudgeRecord(
            nudge_id=nudge_id, category=category,
            importance=importance, action=action,
            user_clicked=user_clicked, user_accepted=user_accepted,
            context=context,
        )
        with self._lock:
            self._records.append(rec)
            if len(self._records) > 500:
                self._records = self._records[-500:]

            # 更新时段统计
            hour = int(time.strftime("%H", time.localtime(rec.timestamp)))
            if hour not in self._hourly_acceptance:
                self._hourly_acceptance[hour] = []
            self._hourly_acceptance[hour].append(user_accepted)
            if len(self._hourly_acceptance[hour]) > 100:
                self._hourly_acceptance[hour] = \
                    self._hourly_acceptance[hour][-100:]

            # 更新类别统计
            if category not in self._category_acceptance:
                self._category_acceptance[category] = []
            self._category_acceptance[category].append(user_accepted)
            if len(self._category_acceptance[category]) > 100:
                self._category_acceptance[category] = \
                    self._category_acceptance[category][-100:]

            # 更新阈值
            cat_accepts = self._category_acceptance.get(category, [])
            if len(cat_accepts) >= 5:
                acc_rate = sum(cat_accepts) / len(cat_accepts)
                old = self._importance_threshold.get(category, 0.5)
                # 接受率高 → 降低阈值 (更积极), 接受率低 → 提高阈值 (更保守)
                new = old - 0.05 if acc_rate > 0.6 else old + 0.05
                self._importance_threshold[category] = max(0.1, min(0.9, new))

    def get_profile(self) -> UserNudgeProfile:
        """获取当前用户Nudge画像。"""
        with self._lock:
            total = len(self._records)
            if total == 0:
                return self._profile

            accepted = sum(1 for r in self._records if r.user_accepted)
            clicked = sum(1 for r in self._records if r.user_clicked)

            # 分析偏好类别
            cat_scores = {}
            for cat, accepts in self._category_acceptance.items():
                if accepts:
                    cat_scores[cat] = sum(accepts) / len(accepts)
            sorted_cats = sorted(cat_scores.items(), key=lambda x: x[1],
                                reverse=True)

            # 分析最佳/最差时段
            hour_scores = {}
            for h, accepts in self._hourly_acceptance.items():
                if accepts:
                    hour_scores[h] = sum(accepts) / len(accepts)
            sorted_hours = sorted(hour_scores.items(), key=lambda x: x[1],
                                 reverse=True)

            return UserNudgeProfile(
                acceptance_rate=round(accepted / total, 3),
                avg_click_rate=round(clicked / total, 3),
                preferred_categories=tuple(c for c, _ in sorted_cats[:3]),
                suppressed_categories=tuple(c for c, _ in sorted_cats[-2:]),
                best_hours=tuple(h for h, _ in sorted_hours[:3]),
                worst_hours=tuple(h for h, _ in sorted_hours[-2:]),
                total_nudges=total,
            )

    def get_thresholds(self) -> dict[str, float]:
        return dict(self._importance_threshold)

    def get_stats(self) -> dict[str, Any]:
        profile = self.get_profile()
        return {
            "total_nudges": profile.total_nudges,
            "acceptance_rate": profile.acceptance_rate,
            "click_rate": profile.avg_click_rate,
            "preferred_categories": list(profile.preferred_categories),
            "thresholds": self.get_thresholds(),
        }

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._importance_threshold = {
                "health": 0.6, "security": 0.3, "insight": 0.5,
                "maintenance": 0.4, "rhythm": 0.5, "info": 0.6,
            }
            self._hourly_acceptance.clear()
            self._category_acceptance.clear()
