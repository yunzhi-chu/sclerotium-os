"""Self Awareness — 系统自我状态感知。

生命体的"内感知" — 知道自己每个器官的健康状态。

监测内容:
  - 器官健康检查 (心跳/响应/错误率)
  - 系统资源 (CPU/内存)
  - EventBus 吞吐量
  - 记忆系统状态
  - 进化状态
  - 异常自检测

使用方式:
    awareness = SelfAwareness()
    awareness.report_organ_health("perception/window_watcher", healthy=True)
    awareness.report_error("perception/file_watcher", "watchdog timeout")

    health = awareness.get_health_report()
    if health.overall_status == "degraded":
        trigger_self_healing()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("sclerotium.self_aware")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class OrganStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class OverallStatus(str, Enum):
    HEALTHY = "healthy"       # 所有器官正常
    DEGRADED = "degraded"     # 部分器官异常
    CRITICAL = "critical"     # 关键器官故障
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OrganHealth:
    """单个器官健康状态 (不可变)。"""
    organ_name: str
    status: OrganStatus
    last_heartbeat: float = 0.0
    error_count: int = 0
    last_error: str = ""
    uptime_seconds: float = 0.0


@dataclass(frozen=True)
class HealthReport:
    """系统健康报告 (不可变)。"""
    overall_status: OverallStatus
    organs: tuple[OrganHealth, ...]
    total_organs: int
    healthy_count: int
    degraded_count: int
    failing_count: int
    recent_errors: tuple[str, ...]
    timestamp: float = field(default_factory=time.time)

    @property
    def health_ratio(self) -> float:
        """健康器官比例。"""
        return self.healthy_count / max(self.total_organs, 1)


# ═══════════════════════════════════════════════════════════════
# SelfAwareness
# ═══════════════════════════════════════════════════════════════

class SelfAwareness:
    """系统自我状态感知与健康监控。

    使用方式:
        awareness = SelfAwareness()
        awareness.register_organ("perception/window_watcher")
        awareness.report_heartbeat("perception/window_watcher")
        awareness.report_error("automation/uia_controller", "pywinauto crash")
        report = awareness.get_health_report()
    """

    # 心跳超时 (秒)
    HEARTBEAT_TIMEOUT = 30.0

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._organs: dict[str, OrganHealth] = {}
        self._recent_errors: list[str] = []
        self._started_at: float = time.time()
        self._error_count_total: int = 0

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def register_organ(self, name: str) -> None:
        """注册一个器官。"""
        with self._lock:
            if name not in self._organs:
                self._organs[name] = OrganHealth(
                    organ_name=name,
                    status=OrganStatus.UNKNOWN,
                    uptime_seconds=0.0,
                )

    def report_heartbeat(self, name: str) -> None:
        """器官心跳上报。"""
        with self._lock:
            if name not in self._organs:
                self._organs[name] = OrganHealth(
                    organ_name=name, status=OrganStatus.HEALTHY,
                    last_heartbeat=time.time(), uptime_seconds=0.0,
                )
            else:
                oh = self._organs[name]
                self._organs[name] = OrganHealth(
                    organ_name=name,
                    status=OrganStatus.HEALTHY,
                    last_heartbeat=time.time(),
                    error_count=oh.error_count,
                    uptime_seconds=time.time() - self._started_at,
                )

    def report_error(self, name: str, error: str) -> None:
        """器官错误上报。"""
        self._error_count_total += 1
        with self._lock:
            if name not in self._organs:
                self._organs[name] = OrganHealth(
                    organ_name=name, status=OrganStatus.FAILING,
                    error_count=1, last_error=error,
                )
            else:
                oh = self._organs[name]
                new_count = oh.error_count + 1
                new_status = OrganStatus.FAILING if new_count > 3 else OrganStatus.DEGRADED
                self._organs[name] = OrganHealth(
                    organ_name=name,
                    status=new_status,
                    last_heartbeat=oh.last_heartbeat,
                    error_count=new_count,
                    last_error=error,
                    uptime_seconds=oh.uptime_seconds,
                )
            self._recent_errors.append(f"{name}: {error}")
            if len(self._recent_errors) > 50:
                self._recent_errors = self._recent_errors[-50:]

    def report_offline(self, name: str) -> None:
        """器官离线上报。"""
        with self._lock:
            if name in self._organs:
                oh = self._organs[name]
                self._organs[name] = OrganHealth(
                    organ_name=name, status=OrganStatus.OFFLINE,
                    last_heartbeat=oh.last_heartbeat,
                    error_count=oh.error_count,
                )

    def check_timeouts(self) -> list[str]:
        """检查超时的器官, 返回超时器官名列表。"""
        now = time.time()
        timeout_organs = []
        with self._lock:
            for name, oh in self._organs.items():
                if oh.last_heartbeat > 0:
                    if now - oh.last_heartbeat > self.HEARTBEAT_TIMEOUT:
                        timeout_organs.append(name)
                        self._organs[name] = OrganHealth(
                            organ_name=name, status=OrganStatus.FAILING,
                            last_heartbeat=oh.last_heartbeat,
                            error_count=oh.error_count,
                            uptime_seconds=oh.uptime_seconds,
                        )
        return timeout_organs

    def get_health_report(self) -> HealthReport:
        """获取系统健康报告。"""
        self.check_timeouts()
        with self._lock:
            organs = tuple(self._organs.values())
            total = len(organs)
            healthy = sum(
                1 for o in organs if o.status == OrganStatus.HEALTHY
            )
            degraded = sum(
                1 for o in organs if o.status == OrganStatus.DEGRADED
            )
            failing = sum(
                1 for o in organs
                if o.status in (OrganStatus.FAILING, OrganStatus.OFFLINE)
            )

            if failing > 0:
                overall = OverallStatus.CRITICAL
            elif degraded > 0:
                overall = OverallStatus.DEGRADED
            else:
                overall = OverallStatus.HEALTHY

            return HealthReport(
                overall_status=overall,
                organs=organs,
                total_organs=total,
                healthy_count=healthy,
                degraded_count=degraded,
                failing_count=failing,
                recent_errors=tuple(self._recent_errors[-10:]),
            )

    def get_organ(self, name: str) -> OrganHealth | None:
        """获取单个器官状态。"""
        with self._lock:
            return self._organs.get(name)

    def get_stats(self) -> dict[str, Any]:
        report = self.get_health_report()
        return {
            "overall": report.overall_status.value,
            "organs": report.total_organs,
            "healthy": report.healthy_count,
            "degraded": report.degraded_count,
            "failing": report.failing_count,
            "health_ratio": round(report.health_ratio, 3),
            "total_errors": self._error_count_total,
            "recent_errors": list(report.recent_errors[-5:]),
        }

    def clear(self) -> None:
        with self._lock:
            self._organs.clear()
            self._recent_errors.clear()
            self._error_count_total = 0
