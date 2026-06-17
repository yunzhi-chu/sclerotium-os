"""L0/L4a: CircuitBreaker — "HPA轴负反馈 + 炎症反射弧" (HPA Negative Feedback + Inflammatory Reflex).

Biological Metaphor:
  HPA轴的负反馈(negative feedback) + 炎症反射弧(inflammatory reflex)

  三级状态:
    CLOSED(正常) = 健康人静息状态——皮质醇正常分泌, 负反馈完好
    HALF_OPEN(半开) = 亚健康——皮质醇轻度升高, 部分负反馈受损
    OPEN(完全断开) = 库欣综合征——皮质醇极高, 负反馈完全丧失,
      必须外部干预(人工确认)

  触发条件(与HPA轴精确对应):
    连续失败≥3次→HALF_OPEN = 连续应激→下丘脑CRH分泌增加
    连续失败≥5次 OR 单次PnL<-5%→OPEN = HPA轴过度激活→外源性糖皮质激素

  Panarchy Ω相共振:
    当Connectedness>0.8 AND Resilience<0.2 → 系统高度互联但极其脆弱
    主动进入Ω释放(如同森林大火清除过度积累的易燃物质)

  恢复机制(Daviu et al. 2026):
    沙箱验证通过+24h无异常→CLOSED
    = 稳态突触缩放——即使皮质醇仍高,
    谷氨酸突触上调用以恢复行为功能(行为韧性的神经基础)

Reference:
  Daviu et al. (2026), "Homeostatic scaling ensures behavioural stability
  during corticosterone negative feedback", Molecular Psychiatry
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class CircuitState(Enum):
    """Three-level circuit breaker state (like HPA axis feedback states)."""

    CLOSED = "closed"  # Normal operation — healthy HPA negative feedback
    HALF_OPEN = "half_open"  # Degraded — partial cortisol elevation
    OPEN = "open"  # Emergency stop — Cushing's syndrome, external intervention needed


@dataclass
class CircuitBreakerConfig:
    """Configuration thresholds for the circuit breaker."""

    consecutive_failures_half_open: int = 3  # → HALF_OPEN
    consecutive_failures_open: int = 5  # → OPEN
    single_pnl_threshold: float = -0.05  # -5% single loss → OPEN
    recovery_sandbox_passes: int = 2  # sandbox validations needed for recovery
    recovery_cooldown_hours: float = 24.0  # cooldown before recovery attempt
    panarchy_connectedness_threshold: float = 0.8  # → Ω resonance
    panarchy_resilience_threshold: float = 0.2  # → Ω resonance


@dataclass
class CircuitBreakerReport:
    """Output report from circuit breaker evaluation."""

    state: CircuitState
    consecutive_failures: int
    total_failures: int
    last_failure_time: float | None
    last_failure_reason: str
    recovery_attempts: int
    cooldown_remaining_hours: float
    panarchy_resonance: bool  # Ω phase resonance detected
    forced_open: bool  # manually forced open
    timestamp: float = field(default_factory=time.time)


class CircuitBreaker:
    """Three-level circuit breaker with HPA axis negative feedback dynamics.

    The "HPA axis + inflammatory reflex" of the system — prevents runaway
    damage by progressively restricting operation as stress accumulates.

    Architecture:
      - CLOSED → HALF_OPEN → OPEN escalation path
      - Consecutive failure counting with decay
      - Panarchy Ω phase resonance detection
      - Sandbox-verified recovery with cooldown
      - Manual override capability for emergency intervention
    """

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._logger = CortexLogger("circuit_breaker")

        self._state: CircuitState = CircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._total_failures: int = 0
        self._total_successes: int = 0
        self._last_failure_time: float | None = None
        self._last_failure_reason: str = ""
        self._recovery_attempts: int = 0
        self._last_recovery_attempt: float | None = None
        self._forced_open: bool = False
        self._state_history: list[tuple[CircuitState, float]] = [(CircuitState.CLOSED, time.time())]

        # Failure memory (decays over time — like cortisol half-life)
        self._failure_memory: list[dict[str, Any]] = []

    # ── State Transitions ─────────────────────────────────────────────

    def record_success(self) -> CircuitState:
        """Record a successful operation.

        Like a healthy stress response resolving — cortisol returns to baseline.
        """
        self._total_successes += 1

        if self._state == CircuitState.HALF_OPEN:
            # Partial recovery: decrement failure counter
            self._consecutive_failures = max(0, self._consecutive_failures - 1)
            if self._consecutive_failures == 0:
                self._transition_to(CircuitState.CLOSED, "consecutive_failures_reset")
                self._logger.info("circuit_closed", reason="failures_reset")

        return self._state

    def record_failure(self, reason: str = "", pnl_pct: float = 0.0) -> tuple[CircuitState, str]:
        """Record a failed operation.

        Like a stressor activating the HPA axis — CRH → ACTH → cortisol cascade.

        Args:
            reason: Description of the failure
            pnl_pct: PnL impact as a fraction (negative = loss)

        Returns:
            (new_state, action_description)
        """
        self._consecutive_failures += 1
        self._total_failures += 1
        self._last_failure_time = time.time()
        self._last_failure_reason = reason

        self._failure_memory.append({
            "reason": reason,
            "pnl_pct": pnl_pct,
            "consecutive": self._consecutive_failures,
            "timestamp": time.time(),
        })
        if len(self._failure_memory) > 100:
            self._failure_memory = self._failure_memory[-100:]

        prev_state = self._state

        # OPEN trigger: single catastrophic loss (>5%)
        if pnl_pct <= self._config.single_pnl_threshold:
            self._transition_to(CircuitState.OPEN, f"catastrophic_loss_{pnl_pct:.1%}")
            self._logger.error("circuit_opened_catastrophic",
                             pnl_pct=round(pnl_pct, 4),
                             reason=reason)
            return self._state, "EMERGENCY_STOP: catastrophic loss threshold breached"

        # OPEN trigger: consecutive failures >= 5
        if self._consecutive_failures >= self._config.consecutive_failures_open:
            self._transition_to(CircuitState.OPEN, "consecutive_failures_threshold")
            self._logger.error("circuit_opened_consecutive",
                             failures=self._consecutive_failures,
                             reason=reason)
            return self._state, "CIRCUIT_OPEN: too many consecutive failures"

        # HALF_OPEN trigger: consecutive failures >= 3
        if self._consecutive_failures >= self._config.consecutive_failures_half_open and \
           self._state == CircuitState.CLOSED:
            self._transition_to(CircuitState.HALF_OPEN, "consecutive_failures_warning")
            self._logger.warn("circuit_half_open",
                            failures=self._consecutive_failures,
                            reason=reason)
            return self._state, "WARNING: entering degraded mode"

        return self._state, "recorded"

    def _transition_to(self, new_state: CircuitState, reason: str) -> None:
        """Transition to a new state with logging."""
        old_state = self._state
        self._state = new_state
        self._state_history.append((new_state, time.time()))
        if len(self._state_history) > 200:
            self._state_history = self._state_history[-200:]

    # ── Panarchy Ω Resonance ──────────────────────────────────────────

    def check_panarchy_resonance(self, connectedness: float, resilience: float) -> bool:
        """Check if system is in Panarchy Ω phase (brittle + highly connected).

        When Connectedness > 0.8 AND Resilience < 0.2:
        The system is like a forest with too much accumulated dry biomass —
        a single spark can cause catastrophic fire. Proactive Ω release
        clears the accumulation.

        Returns:
            True if Ω resonance is detected (circuit should open)
        """
        if connectedness > self._config.panarchy_connectedness_threshold and \
           resilience < self._config.panarchy_resilience_threshold:
            if self._state != CircuitState.OPEN:
                self._transition_to(CircuitState.OPEN, "panarchy_omega_resonance")
                self._logger.warn("panarchy_omega_resonance_detected",
                                connectedness=round(connectedness, 3),
                                resilience=round(resilience, 3))
            return True
        return False

    # ── Recovery Mechanism (Daviu et al. 2026) ────────────────────────

    def attempt_recovery(self, sandbox_passed: bool = False) -> tuple[bool, str]:
        """Attempt to recover from OPEN/HALF_OPEN state.

        Like the homeostatic scaling mechanism restoring behavioral function
        even when cortisol remains elevated (Daviu et al. 2026).

        Recovery requires:
          1. Sandbox validation passes
          2. Cooldown period elapsed (24h)
          3. Sufficient successful sandbox passes

        Returns:
            (recovered, status_message)
        """
        if self._state == CircuitState.CLOSED:
            return True, "already_closed"

        now = time.time()

        # Check cooldown
        if self._last_failure_time:
            cooldown_elapsed = (now - self._last_failure_time) / 3600  # hours
            if cooldown_elapsed < self._config.recovery_cooldown_hours:
                remaining = self._config.recovery_cooldown_hours - cooldown_elapsed
                return False, f"cooldown_remaining: {remaining:.1f}h"

        # Sandbox validation
        if sandbox_passed:
            self._recovery_attempts += 1
            self._last_recovery_attempt = now

            if self._recovery_attempts >= self._config.recovery_sandbox_passes:
                self._transition_to(CircuitState.CLOSED, "recovery_sandbox_passed")
                self._consecutive_failures = 0
                self._recovery_attempts = 0
                self._forced_open = False
                self._logger.info("circuit_recovered",
                                recovery_attempts=self._recovery_attempts)
                return True, "FULLY_RECOVERED"
            else:
                # Partial recovery: move to HALF_OPEN
                if self._state == CircuitState.OPEN:
                    self._transition_to(CircuitState.HALF_OPEN, "partial_recovery")
                return False, f"partial_recovery: {self._recovery_attempts}/{self._config.recovery_sandbox_passes}"
        else:
            self._recovery_attempts = max(0, self._recovery_attempts - 1)
            return False, "sandbox_failed"

    # ── Manual Override ───────────────────────────────────────────────

    def force_open(self, reason: str = "manual_override") -> None:
        """Force circuit OPEN (emergency intervention).

        Like administering exogenous corticosteroids when the HPA axis
        is completely dysregulated.
        """
        self._forced_open = True
        self._transition_to(CircuitState.OPEN, reason)
        self._logger.warn("circuit_forced_open", reason=reason)

    def force_close(self, reason: str = "manual_override") -> None:
        """Force circuit CLOSED (manual reset after verification).

        Like surgically removing an adrenal tumor that caused
        Cushing's syndrome — restoring normal HPA function.
        """
        self._forced_open = False
        self._consecutive_failures = 0
        self._recovery_attempts = 0
        self._transition_to(CircuitState.CLOSED, reason)
        self._logger.info("circuit_forced_closed", reason=reason)

    # ── Query ─────────────────────────────────────────────────────────

    def evaluate(self) -> CircuitBreakerReport:
        """Get current circuit breaker status.

        Returns:
            CircuitBreakerReport with full state diagnostics
        """
        now = time.time()
        cooldown_remaining = 0.0
        if self._last_failure_time and self._state != CircuitState.CLOSED:
            elapsed = (now - self._last_failure_time) / 3600
            cooldown_remaining = max(0.0, self._config.recovery_cooldown_hours - elapsed)

        return CircuitBreakerReport(
            state=self._state,
            consecutive_failures=self._consecutive_failures,
            total_failures=self._total_failures,
            last_failure_time=self._last_failure_time,
            last_failure_reason=self._last_failure_reason,
            recovery_attempts=self._recovery_attempts,
            cooldown_remaining_hours=round(cooldown_remaining, 1),
            panarchy_resonance=False,  # set externally via check_panarchy_resonance
            forced_open=self._forced_open,
        )

    def is_available(self) -> bool:
        """Check if the system can accept new operations."""
        return self._state == CircuitState.CLOSED or (
            self._state == CircuitState.HALF_OPEN and not self._forced_open
        )

    def is_emergency(self) -> bool:
        """Check if the system is in emergency (OPEN) state."""
        return self._state == CircuitState.OPEN

    def get_state_duration(self) -> float:
        """How long (in seconds) has the system been in current state?"""
        if not self._state_history:
            return 0.0
        _, last_change = self._state_history[-1]
        return time.time() - last_change

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def stats(self) -> dict[str, Any]:
        report = self.evaluate()
        return {
            "state": report.state.value,
            "consecutive_failures": report.consecutive_failures,
            "total_failures": report.total_failures,
            "total_successes": self._total_successes,
            "failure_rate": round(
                self._total_failures / max(self._total_failures + self._total_successes, 1), 3
            ),
            "recovery_attempts": report.recovery_attempts,
            "cooldown_remaining_hours": report.cooldown_remaining_hours,
            "forced_open": report.forced_open,
            "state_duration_seconds": round(self.get_state_duration(), 0),
            "available": self.is_available(),
        }
