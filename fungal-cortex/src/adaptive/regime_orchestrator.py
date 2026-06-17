"""L0/L1e: BayesianRegimeOrchestrator — "前额叶整合皮层" (Prefrontal Integration Cortex).

Biological Metaphor:
  前额叶皮层——整合来自视觉/听觉/触觉/内感受的所有信号,
  形成统一的"局势判断", 并在信息不足时主动降低置信度

  BMA贝叶斯模型平均 = 三位专家(HMM/CUSUM/GTH-Net)各自给出意见+置信度
  → 根据历史准确率动态加权 → 贝叶斯融合为统一概率分布
  (如同陪审团中三位法官的投票权重根据历史判案准确率动态调整)

  熵不确定性量化 = 如果三位专家意见分歧极大(熵>1.5)
  → fallback静态基线 = "我们都不确定, 暂不行动"

  5日延迟验证窗口 = 回过头看5天前的判断是否正确，反向修正专家权重

  连续分歧降级: 3次无法达成共识 → 切回equilibrium + 25%置信度
  = 危险理论(Danger Theory): 当免疫系统无法判断是否为病原体时,
  采取保守策略(不攻击自身组织)

Reference:
  Bayesian Model Averaging (Hoeting et al. 1999) +
  Danger Theory (Matzinger 2002)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class ExpertOpinion:
    """A single expert's regime assessment."""

    expert_name: str
    regime_label: str
    confidence: float  # 0-1
    regime_probs: list[float]  # probability distribution over regimes
    weight: float  # current BMA weight
    last_accuracy: float  # historical prediction accuracy


@dataclass
class UnifiedRegimeReport:
    """Unified regime assessment from BMA fusion."""

    regime_label: str
    regime_index: int
    confidence: float
    entropy: float
    expert_opinions: dict[str, ExpertOpinion]
    consensus_reached: bool
    fallback_active: bool  # True if entropy too high, using baseline
    consecutive_disagreements: int
    bma_weights: dict[str, float]
    regime_probs: list[float]  # fused probability distribution
    timestamp: float = field(default_factory=time.time)


class BayesianRegimeOrchestrator:
    """Bayesian Model Averaging orchestrator for fusing 3 regime detectors.

    The "prefrontal cortex" of the adaptive engine — integrates signals from
    HMM (visual cortex), CUSUM (nociceptor), and GTH-Net (vestibular system)
    into a unified regime assessment.

    Architecture:
      - BMA: weighted average of 3 expert probability distributions
      - Dynamic weight updating based on 5-day delayed validation
      - Entropy threshold (1.5) for fallback to static baseline
      - Danger Theory: 3 consecutive disagreements → conservative stance
      - Expert weight tracking with historical accuracy
    """

    REGIME_LABELS = [
        "trending_up", "trending_down", "high_volatility",
        "low_volatility", "sideways", "transition",
    ]
    N_REGIMES = len(REGIME_LABELS)

    ENTROPY_THRESHOLD = 1.5  # Max entropy before fallback (in nats)
    CONSENSUS_DISAGREEMENT_MAX = 3  # Consecutive disagreements before danger mode
    VALIDATION_DELAY = 5  # Days to wait before validating prediction
    BASE_WEIGHT = 1.0 / 3  # Equal initial weight for all experts

    def __init__(self) -> None:
        self._logger = CortexLogger("regime_orchestrator")
        self._observation_count = 0

        # Expert tracking
        self._experts: dict[str, ExpertOpinion] = {}
        self._bma_weights: dict[str, float] = {}

        # Validation queue: (timestamp, predicted_regime, expert_opinions)
        self._validation_queue: list[dict[str, Any]] = []

        # Disagreement tracking
        self._consecutive_disagreements: int = 0
        self._consensus_history: list[bool] = []

        # Historical accuracy per expert
        self._accuracy_tracker: dict[str, list[float]] = {}

        # State
        self._last_unified: UnifiedRegimeReport | None = None
        self._fallback_active: bool = False

    # ── BMA Core ──────────────────────────────────────────────────────

    def fuse(
        self,
        hmm_probs: list[float] | None = None,
        cusum_signal: dict[str, Any] | None = None,
        gthnet_probs: list[float] | None = None,
        expert_confidences: dict[str, float] | None = None,
    ) -> UnifiedRegimeReport:
        """Fuse 3 expert opinions using Bayesian Model Averaging.

        Args:
            hmm_probs: 6-element regime probability from HMM
            cusum_signal: CUSUM signal dict with direction, confidence, z_score
            gthnet_probs: 6-element regime probability from GTH-Net
            expert_confidences: {"hmm": 0.8, "cusum": 0.6, "gthnet": 0.7}

        Returns:
            UnifiedRegimeReport with fused regime assessment
        """
        self._observation_count += 1

        # Default uniform probabilities
        uniform = [1.0 / self.N_REGIMES] * self.N_REGIMES

        # 1. Normalize each expert's regime probabilities
        hmm = self._normalize_probs(hmm_probs) if hmm_probs else uniform[:]
        gn_probs = self._normalize_probs(gthnet_probs) if gthnet_probs else uniform[:]

        # CUSUM → regime mapping
        cusum_regime = self._cusum_to_regime_probs(cusum_signal)

        # 2. Apply expert confidences as precision weights
        confs = expert_confidences or {}
        hmm_conf = confs.get("hmm", 0.5)
        cusum_conf = confs.get("cusum", 0.5)
        gth_conf = confs.get("gthnet", 0.5)

        # Bayesian precision weighting: weight = precision = 1/variance
        # Higher confidence → higher precision → higher weight
        hmm_precision = hmm_conf / max(1 - hmm_conf, 0.01)
        cusum_precision = cusum_conf / max(1 - cusum_conf, 0.01)
        gth_precision = gth_conf / max(1 - gth_conf, 0.01)

        # Normalize to BMA weights
        total_precision = hmm_precision + cusum_precision + gth_precision
        if total_precision > 0:
            w_hmm = hmm_precision / total_precision
            w_cusum = cusum_precision / total_precision
            w_gth = gth_precision / total_precision
        else:
            w_hmm = w_cusum = w_gth = self.BASE_WEIGHT

        # Apply historical accuracy adjustment
        if self._accuracy_tracker:
            w_hmm, w_cusum, w_gth = self._adjust_weights_by_accuracy(
                w_hmm, w_cusum, w_gth
            )

        self._bma_weights = {"hmm": w_hmm, "cusum": w_cusum, "gthnet": w_gth}

        # 3. BMA fusion: weighted sum of probability distributions
        fused_probs = [0.0] * self.N_REGIMES
        for i in range(self.N_REGIMES):
            fused_probs[i] = (
                w_hmm * hmm[i]
                + w_cusum * cusum_regime[i]
                + w_gth * gn_probs[i]
            )

        # Normalize
        total = sum(fused_probs)
        if total > 0:
            fused_probs = [p / total for p in fused_probs]

        # 4. Dominant regime and confidence
        dominant_idx = max(range(self.N_REGIMES), key=lambda i: fused_probs[i])
        confidence = fused_probs[dominant_idx]

        # 5. Entropy check
        entropy = self._compute_entropy(fused_probs)

        # 6. Consensus check
        consensus_reached = self._check_consensus(
            [hmm, cusum_regime, gn_probs], [w_hmm, w_cusum, w_gth]
        )

        # 7. Fallback decision (Danger Theory)
        fallback = False
        if entropy > self.ENTROPY_THRESHOLD:
            # High uncertainty → use uniform distribution
            fused_probs = uniform[:]
            confidence = 0.25  # capped confidence in fallback
            fallback = True
            self._consecutive_disagreements += 1
            self._logger.warn("regime_fallback_activated",
                            entropy=round(entropy, 3),
                            disagreements=self._consecutive_disagreements)
        elif not consensus_reached:
            self._consecutive_disagreements += 1
            if self._consecutive_disagreements >= self.CONSENSUS_DISAGREEMENT_MAX:
                # Danger Theory triggered: 3 strikes → conservative
                fused_probs = uniform[:]
                confidence = 0.25
                fallback = True
                self._logger.warn("danger_theory_triggered",
                                consecutive=self._consecutive_disagreements)
        else:
            self._consecutive_disagreements = 0

        self._fallback_active = fallback
        self._consensus_history.append(consensus_reached)

        # 8. Build expert opinions
        opinions = {
            "hmm": ExpertOpinion(
                expert_name="hmm",
                regime_label=self.REGIME_LABELS[max(range(self.N_REGIMES), key=lambda i: hmm[i])],
                confidence=hmm_conf,
                regime_probs=[round(p, 4) for p in hmm],
                weight=round(w_hmm, 4),
                last_accuracy=self._get_accuracy("hmm"),
            ),
            "cusum": ExpertOpinion(
                expert_name="cusum",
                regime_label=cusum_signal.get("direction", "none") if cusum_signal else "none",
                confidence=cusum_conf,
                regime_probs=[round(p, 4) for p in cusum_regime],
                weight=round(w_cusum, 4),
                last_accuracy=self._get_accuracy("cusum"),
            ),
            "gthnet": ExpertOpinion(
                expert_name="gthnet",
                regime_label=self.REGIME_LABELS[max(range(self.N_REGIMES), key=lambda i: gn_probs[i])],
                confidence=gth_conf,
                regime_probs=[round(p, 4) for p in gn_probs],
                weight=round(w_gth, 4),
                last_accuracy=self._get_accuracy("gthnet"),
            ),
        }

        # 9. Store for delayed validation
        # Queue must hold at least VALIDATION_DELAY days × 24 hourly calls = 120 entries
        # We use 500 to be safe for higher-frequency callers
        self._validation_queue.append({
            "timestamp": time.time(),
            "predicted_regime": self.REGIME_LABELS[dominant_idx],
            "confidence": confidence,
            "entropy": entropy,
            "expert_weights": dict(self._bma_weights),
        })
        # Keep enough history for >5-day lookback at hourly granularity
        _MAX_QUEUE = max(self.VALIDATION_DELAY * 24, 120)
        if len(self._validation_queue) > _MAX_QUEUE:
            self._validation_queue = self._validation_queue[-_MAX_QUEUE:]

        report = UnifiedRegimeReport(
            regime_label=self.REGIME_LABELS[dominant_idx] if not fallback else "equilibrium",
            regime_index=dominant_idx,
            confidence=round(confidence, 3),
            entropy=round(entropy, 3),
            expert_opinions=opinions,
            consensus_reached=consensus_reached,
            fallback_active=fallback,
            consecutive_disagreements=self._consecutive_disagreements,
            bma_weights={k: round(v, 4) for k, v in self._bma_weights.items()},
            regime_probs=[round(p, 4) for p in fused_probs],
        )
        self._last_unified = report

        self._logger.info("regime_fused",
                         regime=report.regime_label,
                         confidence=round(confidence, 3),
                         entropy=round(entropy, 3),
                         consensus=consensus_reached,
                         fallback=fallback)

        return report

    # ── Delayed Validation ────────────────────────────────────────────

    def validate(self, actual_regime: str, days_ago: int = 5) -> dict[str, float]:
        """5-day delayed validation: check if past prediction was correct.

        Like looking back at a decision 5 days later to see if it was right,
        then adjusting expert weights accordingly.

        Returns:
            Dict of expert_name → new_accuracy
        """
        # Find the prediction from days_ago
        target_ts = time.time() - days_ago * 86400
        best_match = None
        best_diff = float("inf")

        for entry in self._validation_queue:
            diff = abs(entry["timestamp"] - target_ts)
            if diff < best_diff:
                best_diff = diff
                best_match = entry

        if best_match is None:
            return {}

        predicted = best_match["predicted_regime"]
        is_correct = predicted == actual_regime

        # Update accuracy trackers
        for expert_name in ["hmm", "cusum", "gthnet"]:
            if expert_name not in self._accuracy_tracker:
                self._accuracy_tracker[expert_name] = []
            self._accuracy_tracker[expert_name].append(1.0 if is_correct else 0.0)
            # Keep last 100
            if len(self._accuracy_tracker[expert_name]) > 100:
                self._accuracy_tracker[expert_name] = self._accuracy_tracker[expert_name][-100:]

        self._logger.info("regime_validated",
                         predicted=predicted,
                         actual=actual_regime,
                         correct=is_correct)

        return {name: self._get_accuracy(name) for name in ["hmm", "cusum", "gthnet"]}

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _normalize_probs(probs: list[float]) -> list[float]:
        """Normalize probabilities to sum to 1."""
        total = sum(probs)
        if total > 0:
            return [p / total for p in probs]
        return [1.0 / len(probs)] * len(probs)

    def _cusum_to_regime_probs(self, cusum_signal: dict[str, Any] | None) -> list[float]:
        """Convert CUSUM signal to 6-regime probability distribution.

        CUSUM gives direction (up/down) + confidence, we spread that across regimes.
        """
        probs = [0.0] * self.N_REGIMES
        if cusum_signal is None:
            return [1.0 / self.N_REGIMES] * self.N_REGIMES

        direction = cusum_signal.get("direction", "none")
        confidence = cusum_signal.get("confidence", 0.5)

        if direction == "up":
            probs[0] = 0.5 * confidence  # trending_up
            probs[4] = 0.3 * (1 - confidence)  # sideways
            probs[3] = 0.2 * (1 - confidence)  # low_volatility
        elif direction == "down":
            probs[1] = 0.5 * confidence  # trending_down
            probs[2] = 0.3 * confidence  # high_volatility
            probs[5] = 0.2 * (1 - confidence)  # transition
        else:
            probs[3] = 0.3  # low_volatility
            probs[4] = 0.4  # sideways
            probs[5] = 0.3  # transition

        return self._normalize_probs(probs)

    def _compute_entropy(self, probs: list[float]) -> float:
        """Compute Shannon entropy of probability distribution in nats."""
        return -sum(p * math.log(max(p, 1e-10)) for p in probs)

    def _check_consensus(
        self, expert_probs: list[list[float]], weights: list[float]
    ) -> bool:
        """Check if experts reach consensus (at least 2/3 agree on dominant regime)."""
        dominant_per_expert = [
            max(range(len(p)), key=lambda i: p[i]) for p in expert_probs
        ]
        # Weighted vote
        votes: dict[int, float] = {}
        for dom, w in zip(dominant_per_expert, weights):
            votes[dom] = votes.get(dom, 0.0) + w

        max_votes = max(votes.values()) if votes else 0.0
        return max_votes > 0.5  # >50% weighted agreement

    def _adjust_weights_by_accuracy(
        self, w_hmm: float, w_cusum: float, w_gth: float
    ) -> tuple[float, float, float]:
        """Adjust BMA weights by historical accuracy.

        Experts with higher historical accuracy get higher weights.
        """
        accuracies = {
            "hmm": self._get_accuracy("hmm"),
            "cusum": self._get_accuracy("cusum"),
            "gthnet": self._get_accuracy("gthnet"),
        }

        # Blend: 60% confidence-based + 40% accuracy-based
        blend = 0.4
        total_acc = sum(accuracies.values())
        if total_acc > 0:
            w_hmm = w_hmm * (1 - blend) + (accuracies["hmm"] / total_acc) * blend
            w_cusum = w_cusum * (1 - blend) + (accuracies["cusum"] / total_acc) * blend
            w_gth = w_gth * (1 - blend) + (accuracies["gthnet"] / total_acc) * blend

        # Normalize
        total = w_hmm + w_cusum + w_gth
        if total > 0:
            return w_hmm / total, w_cusum / total, w_gth / total
        return self.BASE_WEIGHT, self.BASE_WEIGHT, self.BASE_WEIGHT

    def _get_accuracy(self, expert_name: str) -> float:
        """Get historical accuracy for an expert."""
        history = self._accuracy_tracker.get(expert_name, [])
        if not history:
            return 0.5  # Default: neutral
        return sum(history) / len(history)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "observation_count": self._observation_count,
            "bma_weights": {k: round(v, 4) for k, v in self._bma_weights.items()},
            "expert_accuracies": {k: round(self._get_accuracy(k), 3) for k in ["hmm", "cusum", "gthnet"]},
            "consecutive_disagreements": self._consecutive_disagreements,
            "fallback_active": self._fallback_active,
            "consensus_rate": sum(self._consensus_history[-100:]) / max(len(self._consensus_history[-100:]), 1),
            "last_regime": self._last_unified.regime_label if self._last_unified else "unknown",
            "entropy_threshold": self.ENTROPY_THRESHOLD,
        }
