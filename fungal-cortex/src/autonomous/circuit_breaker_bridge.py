"""L4 M2b: CircuitBreakerBridge — "HPA→ANS桥接" 熔断桥接器.

Biological Metaphor:
  HPA轴(内分泌)与自主神经系统(神经)的交汇点: 下丘脑室旁核(PVN)
  PVN同时接收: 体液信号(皮质醇/血糖) + 神经信号(孤束核→PVN)
  整合后→控制交感/副交感的输出强度

  桥接L0 CircuitBreaker到L4 Autonomous:
    监控L0断路器状态→传播到L4任务执行→协调响应
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class BreakerState(str, Enum):
    CLOSED = "closed"      # normal
    HALF_OPEN = "half_open"
    OPEN = "open"          # fully blocked


@dataclass
class BreakerStatus:
    name: str
    state: BreakerState = BreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = field(default_factory=time.time)
    tripped_count: int = 0


class CircuitBreakerBridge:
    """HPA→ANS integration — bridges L0 circuit breaker to L4 autonomous tasks.

    Config:
      - failure_threshold: consecutive failures to trip
      - timeout: seconds before half-open attempt
      - cascade: propagate state to downstream modules
    """

    def __init__(
        self, failure_threshold: int = 5, timeout: float = 60.0, cascade: bool = True
    ) -> None:
        self._threshold = failure_threshold
        self._timeout = timeout
        self._cascade = cascade
        self._breakers: dict[str, BreakerStatus] = {}
        self._downstream: dict[str, list[str]] = {}  # {breaker: [module_names]}
        self._logger = CortexLogger("circuit_breaker_bridge")

    def register(self, name: str, downstream_modules: list[str] | None = None) -> BreakerStatus:
        status = BreakerStatus(name=name)
        self._breakers[name] = status
        if downstream_modules:
            self._downstream[name] = downstream_modules
        return status

    def report_failure(self, name: str) -> BreakerStatus | None:
        """Report failure → may trigger OPEN (cortisol surge)."""
        status = self._breakers.get(name)
        if status is None or status.state == BreakerState.OPEN:
            return status

        status.failure_count += 1
        status.last_failure_time = time.time()

        if status.failure_count >= self._threshold:
            status.state = BreakerState.OPEN
            status.last_state_change = time.time()
            status.tripped_count += 1
            self._logger.warn("breaker_tripped", name=name, failures=status.failure_count)

            if self._cascade and name in self._downstream:
                self._logger.warn("cascade", modules=self._downstream[name])

        return status

    def report_success(self, name: str) -> BreakerStatus | None:
        """Report success → may allow reset."""
        status = self._breakers.get(name)
        if status is None:
            return None

        status.success_count += 1
        if status.state == BreakerState.HALF_OPEN and status.success_count >= max(1, self._threshold // 2):
            status.state = BreakerState.CLOSED
            status.failure_count = 0
            status.last_state_change = time.time()
            self._logger.info("breaker_reset", name=name)

        return status

    def check_timeout(self, name: str) -> BreakerStatus | None:
        """Check if OPEN → HALF_OPEN transition is due (probation)."""
        status = self._breakers.get(name)
        if status and status.state == BreakerState.OPEN:
            if time.time() - status.last_state_change >= self._timeout:
                status.state = BreakerState.HALF_OPEN
                status.failure_count = 0
                status.last_state_change = time.time()
        return status

    def is_allowed(self, module_name: str) -> bool:
        """Check if a downstream module is allowed to operate."""
        for name, modules in self._downstream.items():
            if module_name in modules:
                return self._breakers.get(name, BreakerStatus(name="")).state != BreakerState.OPEN
        return True

    def check_all(self) -> dict[str, BreakerStatus]:
        for name in list(self._breakers):
            self.check_timeout(name)
        return dict(self._breakers)

    @staticmethod
    def _gen_id(prefix: str) -> str:
        return hashlib.md5(f"{prefix}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            name: {"state": s.state.value, "failures": s.failure_count, "tripped": s.tripped_count}
            for name, s in self._breakers.items()
        }
