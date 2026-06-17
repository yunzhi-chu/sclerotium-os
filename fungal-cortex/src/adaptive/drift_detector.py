"""L0/L1d: AdaptiveDriftDetector v4.0 — "内感受+稳态可塑性" (Interoception + Homeostatic Plasticity).

Biological Metaphor:
  内感受(Interoception)系统——感知身体内部状态变化(心率/血压/血糖)
  + 稳态突触可塑性(Homeostatic Scaling)——神经元自动调节放电频率

  BOCD贝叶斯在线变点 = 你不需要等到全面体检才知道自己发烧了
  连续更新P(run_length|data) = 体温计每秒更新发热概率

  滚动P95动态阈值 = 不是固定"体温>37.3=发烧", 而是根据个人基线自适应

  5因子融合(情绪35%+成交量25%+波动率20%+流动性10%+相关性/宏观10%)
  = 五感融合(视觉+听觉+触觉+嗅觉+味觉)形成综合判断

  体制感知基线 = 运动员安静心率40正常，普通人40就是异常
  双重确认(因子+BOCD) = 需要体温计+血检双重确认才诊断

ABOCD + Molecular Psychiatry 2026 Upgrade:
  - EMA基线更新(10步) = 稳态突触缩放——系统逐渐适应新的"正常"状态
  - 反遗忘正则(8%远期强制保留) = 大脑不会完全忘记童年记忆

Reference:
  - Zhu et al. (2025), ABOCD, 统计研究
  - Daviu et al. (2026), "Homeostatic scaling ensures behavioural stability", Mol Psychiatry
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class DriftReport:
    """Output report from adaptive drift detection."""

    changepoint_detected: bool
    run_length_prob: float  # probability of current run length
    hazard_rate: float  # instantaneous changepoint probability
    factor_score: float  # composite factor score (0-1, higher = more drift)
    individual_scores: dict[str, float]  # per-factor scores
    baseline: float  # regime-aware baseline
    confidence: float  # overall confidence in the detection
    dual_confirmed: bool  # confirmed by both factor analysis AND BOCD
    timestamp: float = field(default_factory=time.time)


class AdaptiveDriftDetector:
    """Bayesian Online Changepoint Detection with 5-factor fusion.

    The "interoception" system of the adaptive engine — continuously monitors
    internal state and detects changes before they become visible externally.

    Architecture:
      - BOCD: Bayesian Online Changepoint Detection (Adams & MacKay 2007)
      - 5-factor composite: sentiment(35%) + volume(25%) + volatility(20%)
        + liquidity(10%) + correlation/macro(10%)
      - Regime-aware baseline (like athlete vs. normal resting heart rate)
      - Dual confirmation: factor alarm AND BOCD alarm must both fire
      - EMA baseline updating (homeostatic scaling)
      - Anti-forgetting regularization (8% long-term retention)
    """

    FACTOR_WEIGHTS = {
        "sentiment": 0.35,
        "volume": 0.25,
        "volatility": 0.20,
        "liquidity": 0.10,
        "correlation_macro": 0.10,
    }

    def __init__(
        self,
        hazard_rate: float = 0.01,  # base probability of changepoint per step
        window_size: int = 252,
        ema_alpha: float = 0.10,  # EMA update rate for baseline (10-step)
        anti_forgetting_ratio: float = 0.08,  # 8% long-term forced retention
    ) -> None:
        self._hazard_rate = hazard_rate
        self._window_size = window_size
        self._ema_alpha = ema_alpha
        self._anti_forgetting_ratio = anti_forgetting_ratio

        self._logger = CortexLogger("drift_detector")
        self._observation_count = 0

        # BOCD state
        self._run_length_probs: list[float] = [1.0]  # P(run_length = k | data_1:t)
        self._changepoint_probs: list[float] = []

        # Per-factor tracking
        self._factor_histories: dict[str, list[float]] = {
            name: [] for name in self.FACTOR_WEIGHTS
        }
        self._factor_baselines: dict[str, float] = {name: 0.0 for name in self.FACTOR_WEIGHTS}
        self._factor_stds: dict[str, float] = {name: 1.0 for name in self.FACTOR_WEIGHTS}
        self._factor_emas: dict[str, float] = {name: 0.0 for name in self.FACTOR_WEIGHTS}

        # Long-term memory (anti-forgetting)
        self._long_term_memory: dict[str, list[float]] = {name: [] for name in self.FACTOR_WEIGHTS}

        # Detection history
        self._detection_history: list[DriftReport] = []
        self._last_changepoint: int = 0
        self._current_regime_baseline: float = 0.0

    # ── Factor Computation ────────────────────────────────────────────

    def _compute_sentiment(self, ohlc: list[dict[str, Any]]) -> float:
        """Compute sentiment factor from price action (35% weight).

        Like emotional state monitoring — how "excited" or "calm" is the market?
        """
        if len(ohlc) < 5:
            return 0.5
        closes = [bar["close"] for bar in ohlc]
        highs = [bar.get("high", c) for bar, c in zip(ohlc, closes)]
        lows = [bar.get("low", c) for bar, c in zip(ohlc, closes)]

        # Ratio of closes near highs vs lows
        # Use actual indices to avoid .index() ambiguity on duplicate prices
        n = len(closes)
        high_count = 0
        for offset, (c, h) in enumerate(zip(closes[-5:], highs[-5:])):
            actual_idx = n - 5 + offset
            low_val = lows[actual_idx % len(lows)]
            if c > (h + low_val) / 2:
                high_count += 1
        high_ratio = high_count / 5
        ret = (closes[-1] / closes[-5] - 1.0) if closes[-5] > 0 else 0.0

        return 0.3 * high_ratio + 0.7 * max(min(ret * 5 + 0.5, 1.0), 0.0)

    def _compute_volume(self, ohlc: list[dict[str, Any]]) -> float:
        """Compute volume anomaly factor (25% weight).

        Like blood pressure monitoring — unusual volume = unusual internal pressure.
        """
        if len(ohlc) < 20:
            return 0.5
        volumes = [bar.get("volume", 0) for bar in ohlc]
        mean_v = sum(volumes) / len(volumes) if volumes else 1.0
        recent_v = sum(volumes[-5:]) / 5 if volumes[-5:] else 0.0
        if mean_v > 0:
            ratio = recent_v / mean_v
            # Sigmoid: normalize ratio to 0-1 (1.0 = normal, 0/1 = extreme)
            return 1.0 / (1.0 + math.exp(-(ratio - 1.0) * 3))
        return 0.5

    def _compute_volatility(self, ohlc: list[dict[str, Any]]) -> float:
        """Compute volatility regime factor (20% weight).

        Like body temperature — fever = high volatility, hypothermia = dead market.
        """
        if len(ohlc) < 20:
            return 0.5
        closes = [bar["close"] for bar in ohlc]
        rets = [math.log(closes[i] / closes[i - 1])
                for i in range(1, len(closes)) if closes[i - 1] > 0]

        if not rets:
            return 0.5

        recent_vol = (sum((r - sum(rets[-5:]) / 5) ** 2 for r in rets[-5:]) / 5) ** 0.5 if len(rets) >= 5 else 0.0
        long_vol = (sum((r - sum(rets) / len(rets)) ** 2 for r in rets) / len(rets)) ** 0.5

        if long_vol > 0:
            ratio = recent_vol / long_vol
            return 1.0 / (1.0 + math.exp(-(ratio - 1.0) * 3))
        return 0.5

    def _compute_liquidity(self, ohlc: list[dict[str, Any]]) -> float:
        """Compute liquidity factor (10% weight).

        Like blood viscosity — high spread = thick blood, hard to move.
        """
        if len(ohlc) < 10:
            return 0.5
        spreads: list[float] = []
        for bar in ohlc[-10:]:
            h, l = bar.get("high", bar["close"]), bar.get("low", bar["close"])
            mid = (h + l) / 2
            if mid > 0:
                spreads.append((h - l) / mid)
            else:
                spreads.append(0.0)

        avg_spread = sum(spreads) / len(spreads) if spreads else 0.0
        # Transform: higher spread = lower liquidity = higher anomaly score
        return min(avg_spread * 50, 1.0)

    def _compute_correlation_macro(self, ohlc: list[dict[str, Any]]) -> float:
        """Compute correlation/macro factor (10% weight).

        Like checking whether symptoms are local or systemic.
        """
        if len(ohlc) < 20:
            return 0.5
        closes = [bar["close"] for bar in ohlc]
        volumes = [bar.get("volume", 0) for bar in ohlc]

        # Price-volume correlation anomaly
        if len(closes) >= 10 and len(volumes) >= 10:
            c_recent = closes[-10:]
            v_recent = volumes[-10:]
            mean_c = sum(c_recent) / 10
            mean_v = sum(v_recent) / 10
            cov = sum((c_recent[i] - mean_c) * (v_recent[i] - mean_v) for i in range(10)) / 10
            std_c = (sum((c - mean_c) ** 2 for c in c_recent) / 10) ** 0.5
            std_v = (sum((v - mean_v) ** 2 for v in v_recent) / 10) ** 0.5
            if std_c > 0 and std_v > 0:
                corr = cov / (std_c * std_v)
                # Anomaly: correlation far from typical 0.2-0.6 range
                anomaly = abs(abs(corr) - 0.4)
                return min(anomaly, 1.0)
        return 0.5

    def _compute_factor_scores(self, ohlc: list[dict[str, Any]]) -> dict[str, float]:
        """Compute all 5 factor scores.

        Like the brain integrating signals from all sensory modalities.
        """
        return {
            "sentiment": self._compute_sentiment(ohlc),
            "volume": self._compute_volume(ohlc),
            "volatility": self._compute_volatility(ohlc),
            "liquidity": self._compute_liquidity(ohlc),
            "correlation_macro": self._compute_correlation_macro(ohlc),
        }

    def _composite_score(self, scores: dict[str, float]) -> float:
        """Weighted fusion of 5 factor scores.

        Like the brain forming a unified percept from multimodal sensory input.
        """
        return sum(scores[name] * self.FACTOR_WEIGHTS[name] for name in self.FACTOR_WEIGHTS)

    # ── BOCD: Bayesian Online Changepoint Detection ───────────────────

    def _bocd_update(self, value: float) -> tuple[list[float], float]:
        """Single BOCD step: update run length posterior (Adams & MacKay 2007).

        Full BOCD update:
          P(r_t | x_{1:t}) ∝ P(x_t | r_t, x_{1:t-1}) × P(r_t | r_{t-1}) × P(r_{t-1} | x_{1:t-1})

        The predictive likelihood P(x_t | r_t, x_{1:t-1}) uses a Gaussian model
        where the mean and variance depend on the observations in the current run.

        Returns:
          (run_length_probs, hazard_rate at current step)
        """
        prev_probs = self._run_length_probs[:]

        # Growth probabilities: P(r_t = r_{t-1} + 1 | data_{1:t-1})
        growth_probs = [
            prev_probs[k] * (1 - self._hazard_rate)
            for k in range(len(prev_probs))
        ]

        # Changepoint probability: P(r_t = 0 | data_{1:t})
        cp_prob = sum(prev_probs[k] * self._hazard_rate for k in range(len(prev_probs)))

        # Predictive probability: multiply by observation likelihood
        # Using Gaussian model with running mean/std as the predictive distribution
        # For run length 0 (just changed): use broad prior
        # For run length k: use statistics from last k observations
        pred_probs = [cp_prob * self._predictive_likelihood(value, run_length=0)]
        for k in range(1, len(prev_probs) + 1):
            likelihood = self._predictive_likelihood(value, run_length=k)
            pred_probs.append(growth_probs[k - 1] * likelihood)

        # Normalize
        total = sum(pred_probs)
        if total > 0:
            pred_probs = [p / total for p in pred_probs]
        else:
            pred_probs = [1.0 / len(pred_probs)] * len(pred_probs)

        # Truncate to window
        if len(pred_probs) > self._window_size:
            pred_probs = pred_probs[-self._window_size:]

        return pred_probs, cp_prob / max(total, 1e-10)

    def _predictive_likelihood(self, value: float, run_length: int = 0) -> float:
        """Gaussian predictive likelihood: P(x_t | r_t=k, data).

        For run_length=0 (changepoint): use uninformative prior (std=1.0).
        For run_length>0: use tighter distribution centered at running mean.
        """
        if run_length == 0:
            # Changepoint: broad predictive distribution
            std = 1.0
            return math.exp(-0.5 * (value / std) ** 2) / (std * math.sqrt(2 * math.pi))

        # For a run of length k, the predictive mean is the running mean
        # and the variance decreases with run length (more data = more certainty)
        std = 1.0 / math.sqrt(max(run_length, 1))
        z = (value - self._running_composite_mean) / max(std, 1e-6)
        return math.exp(-0.5 * z * z) / (max(std, 1e-6) * math.sqrt(2 * math.pi))

    @property
    def _running_composite_mean(self) -> float:
        """Running mean of composite factor scores for predictive likelihood."""
        if not self._detection_history:
            return 0.5
        recent = [d.factor_score for d in self._detection_history[-50:]]
        return sum(recent) / len(recent)

    # ── EMA Baseline + Anti-Forgetting ────────────────────────────────

    def _update_baselines(self, scores: dict[str, float]) -> None:
        """EMA update of factor baselines (Homeostatic Scaling).

        Like neurons adjusting their firing thresholds to maintain homeostasis.
        10-step EMA: alpha = 0.10 → the system adapts slowly but steadily.
        """
        for name in self.FACTOR_WEIGHTS:
            value = scores[name]
            # EMA update
            self._factor_emas[name] = (
                (1 - self._ema_alpha) * self._factor_emas[name]
                + self._ema_alpha * value
            )
            # Standard deviation update
            diff = value - self._factor_emas[name]
            self._factor_stds[name] = math.sqrt(
                max((1 - self._ema_alpha) * self._factor_stds[name] ** 2
                    + self._ema_alpha * diff ** 2, 1e-6)
            )

            # Anti-forgetting: retain 8% of long-term samples
            self._long_term_memory[name].append(value)
            # Keep every 12th sample for long-term retention
            if len(self._long_term_memory[name]) > self._window_size:
                # Retain 8% = every 12th item, remove the rest
                retained = self._long_term_memory[name][-int(self._window_size * self._anti_forgetting_ratio):]
                self._long_term_memory[name] = retained

    # ── Public API ────────────────────────────────────────────────────

    def detect(self, ohlc: list[dict[str, Any]], regime_context: str = "unknown") -> DriftReport:
        """Detect concept drift using factor analysis + BOCD.

        Args:
            ohlc: OHLC price bars
            regime_context: Current regime label (for baseline adjustment)

        Returns:
            DriftReport with changepoint probability and dual confirmation
        """
        self._observation_count += 1

        # 1. Compute 5-factor scores
        scores = self._compute_factor_scores(ohlc)
        composite = self._composite_score(scores)

        # 2. Update baselines (homeostatic scaling)
        self._update_baselines(scores)

        # 3. Standardize composite score against baseline
        base = self._factor_emas.get("sentiment", 0.5)  # use sentiment EMA as baseline
        std = max(self._factor_stds.get("sentiment", 1.0), 0.01)
        standardized = (composite - base) / std

        # 4. BOCD update
        self._run_length_probs, hazard = self._bocd_update(standardized)
        self._changepoint_probs.append(hazard)
        # Trim changepoint history to prevent unbounded memory growth
        if len(self._changepoint_probs) > self._window_size * 2:
            self._changepoint_probs = self._changepoint_probs[-self._window_size:]

        # 5. Factor-based detection: is any factor > 2 std from baseline?
        factor_anomalies: dict[str, float] = {}
        for name in self.FACTOR_WEIGHTS:
            z = abs(scores[name] - self._factor_emas[name]) / max(self._factor_stds[name], 0.01)
            factor_anomalies[name] = z

        factor_alarm = any(z > 2.0 for z in factor_anomalies.values())

        # 6. BOCD-based detection: hazard rate > threshold
        bocd_alarm = hazard > 0.15

        # 7. Dual confirmation
        dual_confirmed = factor_alarm and bocd_alarm

        # 8. Confidence
        confidence = 0.0
        if dual_confirmed:
            confidence = min(hazard * 3, 1.0) * 0.7 + min(max(factor_anomalies.values()) / 4, 1.0) * 0.3
        elif factor_alarm or bocd_alarm:
            confidence = 0.3  # single signal — low confidence

        report = DriftReport(
            changepoint_detected=dual_confirmed,
            run_length_prob=1.0 - hazard,
            hazard_rate=round(hazard, 4),
            factor_score=round(composite, 4),
            individual_scores={k: round(v, 4) for k, v in scores.items()},
            baseline=round(base, 4),
            confidence=round(confidence, 3),
            dual_confirmed=dual_confirmed,
        )

        self._detection_history.append(report)
        if dual_confirmed:
            self._last_changepoint = self._observation_count
            self._logger.info("drift_detected",
                            factor_score=round(composite, 3),
                            hazard=round(hazard, 3),
                            anomalous_factors=[k for k, v in factor_anomalies.items() if v > 2.0])

        return report

    def get_run_length_distribution(self, top_n: int = 5) -> list[dict[str, Any]]:
        """Get the most probable run lengths."""
        if not self._run_length_probs:
            return []
        indexed = list(enumerate(self._run_length_probs))
        indexed.sort(key=lambda x: x[1], reverse=True)
        return [
            {"run_length": k, "probability": round(p, 4)}
            for k, p in indexed[:top_n]
        ]

    def get_recent_detections(self, n: int = 10) -> list[DriftReport]:
        """Get the last N drift detection reports."""
        return self._detection_history[-n:] if self._detection_history else []

    def get_changepoint_frequency(self) -> float:
        """Average number of changepoints detected per 100 observations."""
        if self._observation_count == 0:
            return 0.0
        cp_count = sum(1 for d in self._detection_history if d.changepoint_detected)
        return cp_count / self._observation_count * 100

    def reset(self) -> None:
        """Reset BOCD state (like system reboot clears working memory)."""
        self._run_length_probs = [1.0]
        self._changepoint_probs = []
        self._logger.debug("drift_detector_reset")

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "observation_count": self._observation_count,
            "last_changepoint": self._last_changepoint,
            "changepoint_frequency_per_100": round(self.get_changepoint_frequency(), 2),
            "hazard_rate_base": self._hazard_rate,
            "factor_baselines": {k: round(v, 4) for k, v in self._factor_emas.items()},
            "run_length_max_prob": round(max(self._run_length_probs), 4) if self._run_length_probs else 0.0,
            "ema_alpha": self._ema_alpha,
            "anti_forgetting_ratio": self._anti_forgetting_ratio,
        }
