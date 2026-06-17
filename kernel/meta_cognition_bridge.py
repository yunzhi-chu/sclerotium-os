"""MetaCognition Bridge — 监控→诊断→修复循环 (L6 M1)。

生命体的"前额叶皮层" — 持续监控所有器官健康, 自动诊断问题, 尝试修复。

三阶段循环:
  1. MONITOR: 扫描所有注册器官, 收集健康数据
  2. DIAGNOSE: 分析异常模式, 识别根因
  3. REPAIR: 执行修复动作 (重启/重载/降级/通知)

使用方式:
    meta = MetaCognitionBridge(awareness=SelfAwareness())
    meta.register_monitor("perception/window_watcher", check_fn)
    meta.register_repair("perception/window_watcher", restart_fn)

    # 每次 pyloric tick 调用:
    report = meta.run_cycle()
    if report.actions_taken:
        print(f"Auto-repaired: {report.summary()}")
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("sclerotium.metacognition")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class DiagnosisLevel(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class OrganDiagnosis:
    """单个器官诊断结果。"""
    organ_name: str
    level: DiagnosisLevel
    message: str = ""
    suggestions: tuple[str, ...] = ()
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class CycleReport:
    """一次监控循环的报告。"""
    cycle: int
    diagnoses: tuple[OrganDiagnosis, ...]
    actions_taken: tuple[str, ...]
    healthy_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    timestamp: float = field(default_factory=time.time)

    def summary(self) -> str:
        return (
            f"Cycle #{self.cycle}: {self.healthy_count}✓ "
            f"{self.warning_count}⚠ {self.error_count}✗ "
            f"Actions: {len(self.actions_taken)}"
        )


# ═══════════════════════════════════════════════════════════════
# MetaCognitionBridge
# ═══════════════════════════════════════════════════════════════

class MetaCognitionBridge:
    """元认知监控→诊断→修复引擎。

    使用方式:
        meta = MetaCognitionBridge()
        meta.register_organ("perception/window_watcher",
                           check=lambda: True,
                           repair=lambda: restart_watcher())
        report = meta.run_cycle()
    """

    def __init__(self, awareness: Any = None) -> None:
        self._awareness = awareness
        self._monitors: dict[str, Callable[[], bool]] = {}
        self._repairers: dict[str, Callable[[], bool]] = {}
        self._check_fns: dict[str, Callable[[], tuple[bool, str]]] = {}
        self._lock = threading.RLock()
        self._cycle: int = 0
        self._history: list[CycleReport] = []
        self._total_repairs: int = 0

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def register_organ(
        self,
        name: str,
        check: Callable[[], bool] | None = None,
        repair: Callable[[], bool] | None = None,
        check_fn: Callable[[], tuple[bool, str]] | None = None,
    ) -> None:
        """注册一个器官的监控和修复回调。

        Args:
            name: 器官名
            check: 快速健康检查 (返回 True=健康)
            repair: 修复回调 (返回 True=修复成功)
            check_fn: 详细检查 (返回 (健康?, 消息))
        """
        if check:
            self._monitors[name] = check
        if repair:
            self._repairers[name] = repair
        if check_fn:
            self._check_fns[name] = check_fn
        if self._awareness:
            self._awareness.register_organ(name)

    def run_cycle(self) -> CycleReport:
        """执行一次完整的监控→诊断→修复循环。"""
        self._cycle += 1
        diagnoses: list[OrganDiagnosis] = []
        actions: list[str] = []

        # Phase 1: MONITOR
        organ_names = set(
            list(self._monitors.keys()) + list(self._check_fns.keys())
        )
        for name in organ_names:
            diag = self._diagnose_one(name)
            diagnoses.append(diag)

            # 心跳上报
            if self._awareness:
                try:
                    self._awareness.report_heartbeat(name)
                except Exception:
                    pass

        # Phase 2: DIAGNOSE + REPAIR
        for diag in diagnoses:
            if diag.level in (DiagnosisLevel.ERROR, DiagnosisLevel.CRITICAL):
                if name := diag.organ_name:
                    action = self._attempt_repair(name)
                    if action:
                        actions.append(action)
                        self._total_repairs += 1

        healthy = sum(1 for d in diagnoses if d.level == DiagnosisLevel.HEALTHY)
        warning = sum(1 for d in diagnoses if d.level == DiagnosisLevel.WARNING)
        error = sum(1 for d in diagnoses if d.level in
                    (DiagnosisLevel.ERROR, DiagnosisLevel.CRITICAL))

        report = CycleReport(
            cycle=self._cycle,
            diagnoses=tuple(diagnoses),
            actions_taken=tuple(actions),
            healthy_count=healthy,
            warning_count=warning,
            error_count=error,
        )
        self._history.append(report)
        if len(self._history) > 200:
            self._history = self._history[-200:]

        if error > 0:
            logger.warning("MetaCognition: %s", report.summary())

        return report

    def get_history(self, limit: int = 20) -> list[CycleReport]:
        return self._history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        if self._history:
            last = self._history[-1]
        else:
            last = CycleReport(cycle=0, diagnoses=(), actions_taken=())
        return {
            "cycle": self._cycle,
            "total_repairs": self._total_repairs,
            "monitored_organs": len(self._monitors) + len(self._check_fns),
            "last_healthy": last.healthy_count,
            "last_warning": last.warning_count,
            "last_error": last.error_count,
        }

    def clear(self) -> None:
        self._cycle = 0
        self._history.clear()
        self._total_repairs = 0

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _diagnose_one(self, name: str) -> OrganDiagnosis:
        cf = self._check_fns.get(name)
        if cf:
            try:
                ok, msg = cf()
                if ok:
                    return OrganDiagnosis(name, DiagnosisLevel.HEALTHY, msg)
                else:
                    return OrganDiagnosis(name, DiagnosisLevel.ERROR, msg)
            except Exception as e:
                return OrganDiagnosis(name, DiagnosisLevel.CRITICAL, str(e))

        check = self._monitors.get(name)
        if check:
            try:
                ok = check()
                if ok:
                    return OrganDiagnosis(name, DiagnosisLevel.HEALTHY)
                else:
                    return OrganDiagnosis(name, DiagnosisLevel.ERROR,
                                          f"{name} 健康检查失败")
            except Exception as e:
                return OrganDiagnosis(name, DiagnosisLevel.CRITICAL, str(e))

        return OrganDiagnosis(name, DiagnosisLevel.WARNING, "无监控器")

    def _attempt_repair(self, name: str) -> str:
        repair = self._repairers.get(name)
        if not repair:
            return ""
        try:
            ok = repair()
            if ok:
                return f"修复成功: {name}"
            else:
                return f"修复失败: {name}"
        except Exception as e:
            return f"修复异常: {name} — {e}"
