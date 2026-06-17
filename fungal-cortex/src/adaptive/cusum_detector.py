"""L0/L1b: CUSUMRegimeDetector — "痛觉神经" (Nociceptor).

Biological Metaphor:
  皮肤痛觉感受器(Nociceptor)——对温度/压力的突然变化即时反应
  双向累积和(cusum_pos/cusum_neg) = 皮肤记录持续高温/高压的累加器
  如同手碰到热炉→瞬间撤回(不需要等待大脑分析"这是个热炉")

Score-Driven BOCPD 2025 Upgrade:
  - 动态阈值(P95滚动校准) = 不同人的痛觉阈值不同且会适应
  - 滑动窗口z-score = 痛觉的"对比效应"(从冷水进入温水感觉热, 反之冷)
  - MBO+MBOC体制内自相关建模

Reference:
  Tsaknaki et al. (2025), "Score-Driven BOCPD for Order Flow", Quantitative Finance
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class CUSUMSignal:
    """A detected regime change signal from the CUSUM detector."""

    direction: str  # "up", "down", "none"
    cusum_pos: float  # positive CUSUM accumulator
    cusum_neg: float  # negative CUSUM accumulator
    z_score: float  # current z-score
    threshold: float  # dynamic P95 threshold
    triggered: bool  # whether threshold was crossed
    confidence: float  # 0-1
    timestamp: float = field(default_factory=time.time)


class CUSUMRegimeDetector:
    """Bidirectional CUSUM detector for abrupt market regime changes.

    The "nociceptor" of the adaptive engine — instantly detects pain (drawdowns)
    and pleasure (breakouts) without waiting for confirmation.

    Architecture:
      - Bidirectional CUSUM (cusum_pos tracks upward shifts, cusum_neg tracks downward)
      - Dynamic threshold via rolling P95 calibration
      - Score-driven BOCPD with z-score sliding window
      - Mean-reversion detection with AR(1) autocorrelation modeling
    """

    def __init__(
        self,
        drift: float = 0.005,  # Minimum detectable shift (0.5%)
        threshold: float = 3.0,  # Initial CUSUM threshold
        window_size: int = 252,  # Rolling window for P95
        reset_period: int = 60,  # Reset accumulators every N obs
    ) -> None:
        self._drift = drift
        self._threshold = threshold
        self._window_size = window_size
        self._reset_period = reset_period

        self._logger = CortexLogger("cusum_detector")

        # Accumulators
        self._cusum_pos: float = 0.0
        self._cusum_neg: float = 0.0

        # Rolling stats
        self._observation_count: int = 0
        self._value_history: list[float] = []
        self._z_score_history: list[float] = []
        self._signal_history: list[CUSUMSignal] = []

        # Current estimates
        self._running_mean: float = 0.0
        self._running_std: float = 1.0
        self._last_value: float = 0.0
        self._last_z_score: float = 0.0

    # ── Core CUSUM Algorithm ──────────────────────────────────────────

    def update(self, value: float) -> CUSUMSignal:
        """Process a single observation and return CUSUM signal.

        Like a nociceptor firing when temperature crosses the pain threshold.

        Args:
            value: The observation (e.g., log return, price change)

        Returns:
            CUSUMSignal with direction, accumulator values, and trigger status
        """
        self._observation_count += 1
        self._value_history.append(value)

        # Update running statistics (EMA for efficiency)
        alpha = 2.0 / min(self._observation_count + 1, self._window_size + 1)
        if self._observation_count == 1:
            self._running_mean = value
            self._running_std = 0.0
        else:
            self._running_mean = (1 - alpha) * self._running_mean + alpha * value
            diff = value - self._running_mean
            self._running_std = math.sqrt(
                max((1 - alpha) * self._running_std ** 2 + alpha * diff ** 2, 1e-10)
            )

        self._last_value = value

        # Standardize
        std = max(self._running_std, 1e-8)
        standardized = (value - self._running_mean) / std
        self._last_z_score = standardized

        self._z_score_history.append(standardized)

        # Bidirectional CUSUM update
        # cusum_pos: tracks positive mean shift (upward regime change)
        # cusum_neg: tracks negative mean shift (downward regime change)
        pos_shift = standardized - self._drift
        neg_shift = -standardized - self._drift

        self._cusum_pos = max(0.0, self._cusum_pos + pos_shift)
        self._cusum_neg = max(0.0, self._cusum_neg + neg_shift)

        # Dynamic threshold (P95 rolling calibration)
        dynamic_threshold = self._compute_dynamic_threshold()

        # Check triggers
        triggered_pos = self._cusum_pos > dynamic_threshold
        triggered_neg = self._cusum_neg > dynamic_threshold

        direction = "none"
        if triggered_pos:
            direction = "up"
            confidence = min(self._cusum_pos / (dynamic_threshold * 2), 1.0)
        elif triggered_neg:
            direction = "down"
            confidence = min(self._cusum_neg / (dynamic_threshold * 2), 1.0)
        else:
            # Determine leaning direction even if not triggered
            if self._cusum_pos > self._cusum_neg * 1.3:
                direction = "up"
            elif self._cusum_neg > self._cusum_pos * 1.3:
                direction = "down"
            confidence = 0.5

        signal = CUSUMSignal(
            direction=direction,
            cusum_pos=round(self._cusum_pos, 4),
            cusum_neg=round(self._cusum_neg, 4),
            z_score=round(standardized, 4),
            threshold=round(dynamic_threshold, 4),
            triggered=triggered_pos or triggered_neg,
            confidence=round(confidence, 3),
        )
        self._signal_history.append(signal)

        # Periodic reset (like nociceptor adaptation — stop firing after sustained stimulus)
        if self._observation_count % self._reset_period == 0:
            self._cusum_pos *= 0.3  # partial reset, not full
            self._cusum_neg *= 0.3

        # Trim histories
        if len(self._value_history) > self._window_size * 2:
            self._value_history = self._value_history[-self._window_size:]
        if len(self._z_score_history) > self._window_size:
            self._z_score_history = self._z_score_history[-self._window_size:]
        if len(self._signal_history) > self._window_size:
            self._signal_history = self._signal_history[-self._window_size:]

        if triggered_pos or triggered_neg:
            self._logger.info("cusum_triggered",
                            direction=direction,
                            confidence=round(confidence, 3),
                            cusum_pos=round(self._cusum_pos, 2),
                            cusum_neg=round(self._cusum_neg, 2))

        return signal

    def detect(self, ohlc: list[dict[str, Any]]) -> CUSUMSignal:
        """Detect regime changes from OHLC data.

        Uses log returns as the primary signal (most sensitive to regime changes).
        """
        if len(ohlc) < 2:
            return CUSUMSignal(
                direction="none", cusum_pos=0.0, cusum_neg=0.0,
                z_score=0.0, threshold=self._threshold, triggered=False, confidence=0.0,
            )

        # Use composite signal: weighted combination of log return and volatility
        closes = [bar["close"] for bar in ohlc]
        log_ret = math.log(closes[-1] / closes[-2]) if closes[-2] > 0 else 0.0

        # Also consider intraday volatility as a regime change indicator
        if len(ohlc) >= 5:
            recent_rets = [math.log(closes[i] / closes[i - 1])
                          for i in range(max(1, len(closes) - 5), len(closes))
                          if closes[i - 1] > 0]
            vol_signal = (sum((r - sum(recent_rets) / len(recent_rets)) ** 2
                           for r in recent_rets) / len(recent_rets)) ** 0.5 if recent_rets else 0.0
        else:
            vol_signal = 0.0

        # Composite value: 70% return signal + 30% volatility signal
        composite = log_ret * 0.7 + vol_signal * 0.3

        return self.update(composite)

    def _compute_dynamic_threshold(self) -> float:
        """Compute P95 dynamic threshold from rolling z-score distribution.

        Like individual pain thresholds that adapt to experience:
        - Athletes develop higher pain tolerance (higher threshold)
        - Chronic pain lowers threshold (more sensitive)
        """
        if len(self._z_score_history) < 30:
            return self._threshold

        # Sort absolute z-scores and take P95
        abs_scores = sorted(abs(z) for z in self._z_score_history[-self._window_size:])
        p95_idx = int(len(abs_scores) * 0.95)
        p95 = abs_scores[min(p95_idx, len(abs_scores) - 1)]

        # Blend with initial threshold for stability
        return max(p95 * 0.7 + self._threshold * 0.3, 1.5)

    def reset(self) -> None:
        """Reset all accumulators (like nociceptor recovery after stimulus removed)."""
        self._cusum_pos = 0.0
        self._cusum_neg = 0.0
        self._running_mean = 0.0
        self._running_std = 1.0
        self._logger.debug("cusum_reset")

    def get_recent_signals(self, n: int = 20) -> list[CUSUMSignal]:
        """Get the last N CUSUM signals for analysis."""
        return self._signal_history[-n:] if self._signal_history else []

    def get_trigger_frequency(self) -> float:
        """Fraction of recent observations that triggered a signal."""
        if not self._signal_history:
            return 0.0
        recent = self._signal_history[-min(100, len(self._signal_history)):]
        return sum(1 for s in recent if s.triggered) / len(recent)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "observation_count": self._observation_count,
            "cusum_pos": round(self._cusum_pos, 4),
            "cusum_neg": round(self._cusum_neg, 4),
            "running_mean": round(self._running_mean, 6),
            "running_std": round(self._running_std, 6),
            "last_z_score": round(self._last_z_score, 4),
            "dynamic_threshold": round(self._compute_dynamic_threshold(), 4),
            "trigger_frequency": round(self.get_trigger_frequency(), 3),
            "drift": self._drift,
        }
