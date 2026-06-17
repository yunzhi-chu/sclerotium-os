"""L0/L1a: HMMRegimeDetector — "视觉皮层" (Visual Cortex V1).

Biological Metaphor:
  大脑视觉皮层V1——从原始像素(价格序列)中提取边缘/纹理/形状(体制特征)

  Baum-Welch无监督学习 = 婴儿通过观察世界自动学会区分白天/黑夜/室内/室外
  不需要标签，系统自己发现市场有几种"状态"（如同婴儿不需要被教"这是白天"）

ABOCD 2025 Upgrade:
  - 滑动窗口重估计超参数 = 人眼根据环境光暗自动调节瞳孔大小(不是固定光圈)
  - 7维观测特征(开高低收量+对数收益+波动率)
  - 6隐藏状态自动标注(通过状态统计特征)

Reference:
  Zhu et al. (2025), "Adaptive BOCD for Financial Market Surveillance", 统计研究
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class HMMState:
    """A single hidden regime state discovered by the HMM.

    Like a visual "shape" that V1 neurons learn to recognize.
    """

    state_id: int
    label: str = "unknown"  # auto-labeled: trending_up, volatile, calm, etc.
    prior: float = 1.0 / 6  # initial state probability
    transition_probs: list[float] = field(default_factory=lambda: [1.0 / 6] * 6)
    emission_mean: list[float] = field(default_factory=lambda: [0.0] * 7)
    emission_std: list[float] = field(default_factory=lambda: [1.0] * 7)
    observation_count: int = 0
    last_seen: float = 0.0


@dataclass
class HMMRegimeReport:
    """Output report from a single HMM detection cycle."""

    dominant_state: int
    state_probs: list[float]  # posterior probability of each state
    confidence: float  # 0-1, how confident the model is
    entropy: float  # uncertainty measure
    regime_label: str
    transition_alert: bool  # True if regime transition detected
    timestamp: float = field(default_factory=time.time)


class HMMRegimeDetector:
    """Baum-Welch Hidden Markov Model for unsupervised regime detection.

    The "visual cortex" of the adaptive engine — learns to see market states
    without being told what they look like.

    Architecture:
      7 observation features (OHLCV + log_return + volatility)
      6 hidden states (auto-labeled by statistical profile)
      Baum-Welch EM algorithm for unsupervised training
      ABOCD sliding window for adaptive hyperparameter recalibration
    """

    N_STATES = 6
    N_FEATURES = 7
    # Feature indices
    F_OPEN = 0
    F_HIGH = 1
    F_LOW = 2
    F_CLOSE = 3
    F_VOLUME = 4
    F_LOG_RETURN = 5
    F_VOLATILITY = 6

    STATE_LABELS = [
        "trending_up",       # 上升趋势 — like bright daylight
        "trending_down",     # 下降趋势 — like nighttime
        "high_volatility",   # 高波动 — like flickering strobe light
        "low_volatility",    # 低波动 — like steady ambient light
        "reversal",          # 反转 — like sudden shadow/light shift
        "sideways",          # 横盘 — like twilight/dusk
    ]

    def __init__(self, window_size: int = 252, recalibrate_every: int = 60) -> None:
        """
        Args:
            window_size: Rolling window for training (default 252 ≈ 1 trading year)
            recalibrate_every: Re-estimate hyperparams every N observations
        """
        self._window_size = window_size
        self._recalibrate_every = recalibrate_every
        self._logger = CortexLogger("hmm_detector")
        self._observation_count = 0

        # Initialize 6 states with uniform priors
        self._states: list[HMMState] = [
            HMMState(state_id=i, prior=1.0 / self.N_STATES) for i in range(self.N_STATES)
        ]

        # Transition matrix: 6×6 (uniform to start — "infant sees random noise")
        self._transition_matrix: list[list[float]] = [
            [1.0 / self.N_STATES] * self.N_STATES for _ in range(self.N_STATES)
        ]

        # Emission parameters (mean, std per state per feature)
        self._emission_means: list[list[float]] = [
            [0.0] * self.N_FEATURES for _ in range(self.N_STATES)
        ]
        self._emission_stds: list[list[float]] = [
            [1.0] * self.N_FEATURES for _ in range(self.N_STATES)
        ]

        # Observation buffer
        self._observations: list[list[float]] = []

        # Last posterior
        self._last_posterior: list[float] = [1.0 / self.N_STATES] * self.N_STATES

    # ── Feature Extraction ────────────────────────────────────────────

    def _extract_features(self, ohlc: list[dict[str, Any]]) -> list[list[float]]:
        """Extract 7-dimensional feature vectors from OHLC bars.

        Features (like V1 extracting edges/orientation/motion):
          0: open price (normalized)
          1: high price (normalized)
          2: low price (normalized)
          3: close price (normalized)
          4: volume (log-normalized)
          5: log return
          6: rolling volatility (20-period std of returns)
        """
        if len(ohlc) < 21:
            return []

        features: list[list[float]] = []
        # Normalize prices by running mean
        closes = [bar["close"] for bar in ohlc]
        mean_close = sum(closes) / len(closes) if closes else 1.0

        for i, bar in enumerate(ohlc):
            c = bar["close"]
            log_ret = math.log(c / ohlc[i - 1]["close"]) if i > 0 and ohlc[i - 1]["close"] > 0 else 0.0

            # Rolling 20-period volatility
            if i >= 20:
                rets = [math.log(ohlc[j]["close"] / ohlc[j - 1]["close"])
                        for j in range(i - 19, i + 1) if ohlc[j - 1]["close"] > 0]
                vol = (sum((r - sum(rets) / len(rets)) ** 2 for r in rets) / len(rets)) ** 0.5 if rets else 0.0
            else:
                vol = 0.0

            features.append([
                bar.get("open", c) / mean_close,
                bar.get("high", c) / mean_close,
                bar.get("low", c) / mean_close,
                c / mean_close,
                math.log(max(bar.get("volume", 1), 1)),
                log_ret,
                vol,
            ])

        return features

    # ── Baum-Welch EM Algorithm ──────────────────────────────────────

    def _forward(self, obs_seq: list[list[float]]) -> tuple[list[list[float]], list[float]]:
        """Forward pass: compute α[t][i] = P(o_1...o_t, state_t=i | λ)."""
        T = len(obs_seq)
        N = self.N_STATES
        alpha: list[list[float]] = [[0.0] * N for _ in range(T)]
        scales: list[float] = [0.0] * T

        # Initialize: α[0][i] = π_i * b_i(o_0)
        for i in range(N):
            alpha[0][i] = self._states[i].prior * self._emission_prob(obs_seq[0], i)
        scales[0] = sum(alpha[0])
        if scales[0] > 0:
            for i in range(N):
                alpha[0][i] /= scales[0]

        # Recursion
        for t in range(1, T):
            for j in range(N):
                prob = 0.0
                for i in range(N):
                    prob += alpha[t - 1][i] * self._transition_matrix[i][j]
                alpha[t][j] = prob * self._emission_prob(obs_seq[t], j)
            scales[t] = sum(alpha[t])
            if scales[t] > 0:
                for j in range(N):
                    alpha[t][j] /= scales[t]

        return alpha, scales

    def _backward(self, obs_seq: list[list[float]], scales: list[float]) -> list[list[float]]:
        """Backward pass: compute β[t][i] = P(o_{t+1}...o_T | state_t=i, λ)."""
        T = len(obs_seq)
        N = self.N_STATES
        beta: list[list[float]] = [[0.0] * N for _ in range(T)]

        # Initialize
        for i in range(N):
            beta[T - 1][i] = 1.0 / max(scales[T - 1], 1e-10)

        # Recursion
        for t in range(T - 2, -1, -1):
            for i in range(N):
                prob = 0.0
                for j in range(N):
                    prob += (self._transition_matrix[i][j]
                             * self._emission_prob(obs_seq[t + 1], j)
                             * beta[t + 1][j])
                beta[t][i] = prob / max(scales[t], 1e-10)

        return beta

    def _baum_welch_step(self, obs_seq: list[list[float]]) -> float:
        """Single Baum-Welch EM iteration. Returns log-likelihood."""
        T = len(obs_seq)
        N = self.N_STATES
        F = self.N_FEATURES

        alpha, scales = self._forward(obs_seq)
        beta = self._backward(obs_seq, scales)

        # Log-likelihood
        log_lik = sum(math.log(max(s, 1e-10)) for s in scales)

        # E-step: compute ξ[t][i][j] = P(state_t=i, state_{t+1}=j | O, λ)
        xi: list[list[list[float]]] = [[[0.0] * N for _ in range(N)] for _ in range(T - 1)]
        gamma: list[list[float]] = [[0.0] * N for _ in range(T)]

        for t in range(T - 1):
            denom = 0.0
            for i in range(N):
                for j in range(N):
                    xi[t][i][j] = (alpha[t][i]
                                   * self._transition_matrix[i][j]
                                   * self._emission_prob(obs_seq[t + 1], j)
                                   * beta[t + 1][j])
                    denom += xi[t][i][j]
            if denom > 0:
                for i in range(N):
                    for j in range(N):
                        xi[t][i][j] /= denom

        for t in range(T):
            for i in range(N):
                gamma[t][i] = alpha[t][i] * beta[t][i]
            s = sum(gamma[t])
            if s > 0:
                for i in range(N):
                    gamma[t][i] /= s

        # M-step: update parameters
        for i in range(N):
            gamma_sum = sum(gamma[t][i] for t in range(T))

            # Update prior
            self._states[i].prior = gamma[0][i]

            # Update transition matrix
            for j in range(N):
                xi_sum = sum(xi[t][i][j] for t in range(T - 1))
                denom = sum(sum(xi[t][i][k] for k in range(N)) for t in range(T - 1))
                self._transition_matrix[i][j] = xi_sum / max(denom, 1e-10)

            # Update emission means
            if gamma_sum > 1e-10:
                for f in range(F):
                    self._emission_means[i][f] = (
                        sum(gamma[t][i] * obs_seq[t][f] for t in range(T)) / gamma_sum
                    )

                # Update emission stds
                for f in range(F):
                    sse = sum(gamma[t][i] * (obs_seq[t][f] - self._emission_means[i][f]) ** 2
                             for t in range(T))
                    self._emission_stds[i][f] = math.sqrt(max(sse / gamma_sum, 1e-6))

        return log_lik

    def _emission_prob(self, obs: list[float], state: int) -> float:
        """Gaussian emission probability: P(o | state)."""
        prob = 1.0
        for f in range(self.N_FEATURES):
            std = max(self._emission_stds[state][f], 1e-6)
            diff = (obs[f] - self._emission_means[state][f]) / std
            prob *= math.exp(-0.5 * diff * diff) / (std * math.sqrt(2 * math.pi))
        return prob

    # ── ABOCD Sliding Window Recalibration ───────────────────────────

    def _auto_label_states(self) -> None:
        """Auto-label hidden states by statistical profile (ABOCD 2025).

        Like a child learning to name visual categories:
        - State with highest mean return → "trending_up"
        - State with lowest mean return → "trending_down"
        - State with highest volatility → "high_volatility"
        - etc.
        """
        profile: list[tuple[int, float, float]] = []
        for i in range(self.N_STATES):
            mean_ret = self._emission_means[i][self.F_LOG_RETURN]
            std_vol = self._emission_stds[i][self.F_VOLATILITY]
            profile.append((i, mean_ret, std_vol))

        # Sort by mean return
        by_return = sorted(profile, key=lambda x: x[1])
        if len(by_return) >= 6:
            self._states[by_return[0][0]].label = "trending_down"
            self._states[by_return[1][0]].label = "reversal"
            self._states[by_return[2][0]].label = "sideways"
            self._states[by_return[3][0]].label = "low_volatility"
            self._states[by_return[4][0]].label = "high_volatility"
            self._states[by_return[5][0]].label = "trending_up"

    def _recalibrate_hyperparams(self) -> None:
        """ABOCD-style sliding window recalibration.

        Like the pupil adjusting its aperture based on ambient light:
        - If recent observations are more volatile → increase emission stds
        - If market has been calm → tighten stds for higher sensitivity
        """
        if not self._observations:
            return

        recent = self._observations[-min(self._recalibrate_every, len(self._observations)):]

        # Compute global volatility scaling factor
        total_var = 0.0
        for obs in recent:
            total_var += sum(o ** 2 for o in obs)
        avg_var = total_var / max(len(recent), 1)

        # Scale emission stds proportional to recent volatility
        scale = math.sqrt(max(avg_var, 0.01))
        for state in range(self.N_STATES):
            for f in range(self.N_FEATURES):
                self._emission_stds[state][f] = max(
                    self._emission_stds[state][f] * 0.8 + scale * 0.2,
                    1e-6,
                )

    # ── Public API ────────────────────────────────────────────────────

    def fit(self, ohlc: list[dict[str, Any]], iterations: int = 20) -> float:
        """Train HMM on OHLC data using Baum-Welch EM.

        Args:
            ohlc: List of OHLC bars with close/open/high/low/volume
            iterations: Maximum EM iterations

        Returns:
            Final log-likelihood
        """
        features = self._extract_features(ohlc)
        if len(features) < 30:
            self._logger.warn("hmm_insufficient_data", count=len(features))
            return float("-inf")

        self._observations = features

        # Baum-Welch iteration
        prev_ll = float("-inf")
        for it in range(iterations):
            ll = self._baum_welch_step(features)
            if abs(ll - prev_ll) < 1e-4:
                self._logger.debug("hmm_converged", iteration=it, log_lik=round(ll, 2))
                break
            prev_ll = ll
            self._observation_count += 1

        # Auto-label after training
        self._auto_label_states()

        # Recalibrate hyperparams
        if self._observation_count % self._recalibrate_every == 0:
            self._recalibrate_hyperparams()

        self._logger.info("hmm_trained", states=self._get_state_labels(), log_lik=round(prev_ll, 2))
        return prev_ll

    def detect(self, ohlc: list[dict[str, Any]]) -> HMMRegimeReport:
        """Detect current regime from OHLC data.

        Args:
            ohlc: Recent OHLC bars (should be consistent with training data)

        Returns:
            HMMRegimeReport with dominant state, probabilities, and confidence
        """
        features = self._extract_features(ohlc)
        if not features:
            return HMMRegimeReport(
                dominant_state=-1,
                state_probs=self._last_posterior,
                confidence=0.0,
                entropy=0.0,
                regime_label="unknown",
            )

        # Compute posterior for the last observation (Viterbi-like forward pass)
        alpha, _ = self._forward(features)
        posterior = alpha[-1][:]  # last timestep posterior

        # Normalize
        total = sum(posterior)
        if total > 0:
            posterior = [p / total for p in posterior]

        self._last_posterior = posterior

        # Dominant state
        dominant = max(range(self.N_STATES), key=lambda i: posterior[i])
        confidence = posterior[dominant]

        # Entropy (uncertainty)
        entropy = -sum(p * math.log(max(p, 1e-10)) for p in posterior) / math.log(self.N_STATES)

        # Transition alert: dominant state changed from previous
        prev_dominant = max(range(self.N_STATES),
                           key=lambda i: self._states[i].last_seen) if self._observation_count > 0 else -1
        transition_alert = dominant != prev_dominant and self._observation_count > 0

        # Update state metadata
        for i in range(self.N_STATES):
            self._states[i].last_seen = posterior[i]

        self._logger.debug("hmm_detected",
                          regime=self._states[dominant].label,
                          confidence=round(confidence, 3),
                          entropy=round(entropy, 3))

        return HMMRegimeReport(
            dominant_state=dominant,
            state_probs=posterior,
            confidence=confidence,
            entropy=entropy,
            regime_label=self._states[dominant].label,
            transition_alert=transition_alert,
        )

    def get_state_profile(self, state_id: int) -> dict[str, Any]:
        """Get the statistical profile of a discovered regime state."""
        if state_id < 0 or state_id >= self.N_STATES:
            return {}
        state = self._states[state_id]
        return {
            "state_id": state_id,
            "label": state.label,
            "prior": state.prior,
            "transition_to": [round(p, 4) for p in self._transition_matrix[state_id]],
            "emission_mean": [round(m, 6) for m in self._emission_means[state_id]],
            "emission_std": [round(s, 6) for s in self._emission_stds[state_id]],
            "observation_count": state.observation_count,
        }

    def _get_state_labels(self) -> dict[int, str]:
        return {i: s.label for i, s in enumerate(self._states)}

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "n_states": self.N_STATES,
            "n_features": self.N_FEATURES,
            "observation_count": self._observation_count,
            "state_labels": self._get_state_labels(),
            "last_posterior": [round(p, 4) for p in self._last_posterior],
            "window_size": self._window_size,
        }
