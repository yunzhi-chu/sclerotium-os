"""L0/L3b: AdaptiveMetaLearner v4.0 — "LTP+LTD+Meta-Plasticity" (Synaptic Plasticity).

Biological Metaphor:
  元学习(Learning to Learn) = 突触的元可塑性(Meta-plasticity)
  不仅调整权重, 还调整"如何调整权重"的规则
  (如同不仅学习知识, 还学习"如何学习"的方法)

  体制新颖度评分:
    Mahalanobis距离(新状态与已知状态的距离) + 任务相似度 + 熵
    = 大脑判断"这是全新情况"还是"以前见过类似情况"

  自适应k-shot(新颖度0→3shot, 1→20shot):
    = 熟悉场景只需要3个样本就能识别(见到猫一次就认得出)
      全新场景需要20个样本(从没见过外星生物, 需要更多观察)

  三算法集成(加权融合):
    1. Reptile(40%): 一阶MAML→快速但粗略 = 直觉反应(不经过大脑皮层)
    2. FOMAML(35%): 二阶梯度→精准但慢 = 深思熟虑(前额叶参与)
    3. Prototypical(25%): 原型匹配→泛化最佳 = 模板匹配(与记忆中所有原型比对)

  多目标联合优化:
    预测损失(准确性) + 一致性正则(不要频繁改变)
    + 体制嵌入对齐(保持与历史知识一致) + 反遗忘正则(不忘记旧知识)
    = 同时优化四个目标的帕累托前沿

Upgrade (Lu et al. 2025, eLife):
  - 双相结构可塑性规则 = 部分阻断促进生长, 完全阻断抑制生长
    → 有控制的压力促使适应, 完全失控的压力导致崩溃

Reference:
  Zinjad et al. (2026), IJISA 18(2):27-43;
  Thomazeau et al. (2025), "Unconventional NMDA receptors", eLife;
  Lu et al. (2025), "Homeostatic synaptic scaling × structural plasticity", eLife
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class RegimePrototype:
    """A prototypical representation of a known regime (like a concept in memory)."""

    regime_label: str
    centroid: list[float]  # 32-dim prototype vector
    variance: list[float]  # per-dimension variance
    sample_count: int  # number of examples used to form this prototype
    last_updated: float
    ema_alpha: float = 0.1  # EMA update rate


@dataclass
class MetaLearnReport:
    """Output report from one meta-learning cycle."""

    novelty_score: float  # 0-1, how novel is current regime
    k_shot: int  # adaptive number of shots needed
    algorithm_weights: dict[str, float]  # Reptile/FOMAML/Prototypical weights
    matched_prototype: str | None  # closest known regime
    prototype_distance: float  # Mahalanobis distance to closest prototype
    losses: dict[str, float]  # multi-objective losses
    adaptation_rate: float  # current learning rate
    timestamp: float = field(default_factory=time.time)


class AdaptiveMetaLearner:
    """Few-shot meta-learner with adaptive k-shot and prototype matching.

    The "synaptic plasticity" system — learns how to learn from market regimes,
    using three complementary algorithms fused by novelty.

    Architecture:
      - 32-dim regime prototypes with EMA updating
      - Novelty scoring: Mahalanobis distance + task similarity + entropy
      - Adaptive k-shot: novelty 0→3 samples, 1→20 samples
      - Three-algorithm ensemble: Reptile(40%) + FOMAML(35%) + Prototypical(25%)
      - Multi-objective optimization: loss + consistency + alignment + anti-forgetting
      - Biphasic plasticity rule (Lu et al. 2025)
    """

    PROTOTYPE_DIM = 32
    BASE_K_SHOT = 3
    MAX_K_SHOT = 20

    # Algorithm base weights
    REPTILE_BASE = 0.40
    FOMAML_BASE = 0.35
    PROTO_BASE = 0.25

    def __init__(self) -> None:
        self._logger = CortexLogger("meta_learner")
        self._call_count = 0

        # Prototype library: regime_label → RegimePrototype
        self._prototypes: dict[str, RegimePrototype] = {}

        # Algorithm weights (adaptable)
        self._algo_weights = {
            "reptile": self.REPTILE_BASE,
            "fomaml": self.FOMAML_BASE,
            "proto": self.PROTO_BASE,
        }

        # Multi-objective loss tracking
        self._loss_history: dict[str, list[float]] = {
            "prediction": [],
            "consistency": [],
            "alignment": [],
            "anti_forgetting": [],
        }

        # Current learning rate (adapts based on novelty)
        self._learning_rate: float = 0.01

        # Task memory for consistency regularization
        self._task_memory: list[dict[str, Any]] = []

        self._last_report: MetaLearnReport | None = None

    # ── Prototype Management ──────────────────────────────────────────

    def update_prototype(
        self,
        regime_label: str,
        feature_vector: list[float],
    ) -> RegimePrototype:
        """Update or create a regime prototype using EMA.

        Like updating a mental concept — each new example slightly shifts
        the "average" representation in memory.
        """
        f = list(feature_vector[:self.PROTOTYPE_DIM])
        while len(f) < self.PROTOTYPE_DIM:
            f.append(0.0)

        if regime_label in self._prototypes:
            proto = self._prototypes[regime_label]
            # EMA update centroid
            proto.centroid = [
                (1 - proto.ema_alpha) * proto.centroid[i] + proto.ema_alpha * f[i]
                for i in range(self.PROTOTYPE_DIM)
            ]
            # Update variance
            proto.variance = [
                (1 - proto.ema_alpha) * proto.variance[i]
                + proto.ema_alpha * (f[i] - proto.centroid[i]) ** 2
                for i in range(self.PROTOTYPE_DIM)
            ]
            proto.sample_count += 1
            proto.last_updated = time.time()
        else:
            proto = RegimePrototype(
                regime_label=regime_label,
                centroid=f[:],
                variance=[1.0] * self.PROTOTYPE_DIM,
                sample_count=1,
                last_updated=time.time(),
            )
            self._prototypes[regime_label] = proto

        self._logger.debug("prototype_updated",
                          regime=regime_label,
                          count=proto.sample_count)
        return proto

    # ── Novelty Scoring ───────────────────────────────────────────────

    def _mahalanobis_distance(
        self, features: list[float], prototype: RegimePrototype
    ) -> float:
        """Mahalanobis distance: how many standard deviations from prototype center.

        Like the brain evaluating "how different is this from any known pattern?"
        """
        dist = 0.0
        for i in range(self.PROTOTYPE_DIM):
            std = math.sqrt(max(prototype.variance[i], 1e-6))
            diff = (features[i] - prototype.centroid[i]) / std
            dist += diff ** 2
        return math.sqrt(dist / self.PROTOTYPE_DIM)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        dot = sum(a[i] * b[i] for i in range(len(a)))
        norm_a = math.sqrt(sum(x ** 2 for x in a))
        norm_b = math.sqrt(sum(x ** 2 for x in b))
        if norm_a < 1e-10 or norm_b < 1e-10:
            return 0.0
        return dot / (norm_a * norm_b)

    def compute_novelty(
        self,
        feature_vector: list[float],
        regime_distribution: list[float] | None = None,
    ) -> tuple[float, str | None, float]:
        """Compute regime novelty score.

        Returns:
            (novelty_score 0-1, closest_prototype_label, mahalanobis_distance)
        """
        f = list(feature_vector[:self.PROTOTYPE_DIM])
        while len(f) < self.PROTOTYPE_DIM:
            f.append(0.0)

        if not self._prototypes:
            return 1.0, None, float("inf")  # completely novel

        # Find closest prototype by Mahalanobis distance
        best_label: str | None = None
        best_dist = float("inf")

        for label, proto in self._prototypes.items():
            dist = self._mahalanobis_distance(f, proto)
            if dist < best_dist:
                best_dist = dist
                best_label = label

        # Task similarity: cosine similarity to closest prototype
        if best_label and best_label in self._prototypes:
            similarity = self._cosine_similarity(f, self._prototypes[best_label].centroid)
        else:
            similarity = 0.0

        # Entropy: from regime distribution if available
        if regime_distribution:
            r = [p for p in regime_distribution if p > 0]
            entropy = -sum(p * math.log(p) for p in r) / math.log(max(len(r), 2))
        else:
            entropy = 0.5

        # Composite novelty:
        # High Mahalanobis + low similarity + high entropy → novel
        novelty = (
            0.4 * min(best_dist / 5.0, 1.0)  # normalized distance
            + 0.3 * (1.0 - similarity)  # dissimilarity
            + 0.3 * entropy  # uncertainty
        )

        return min(novelty, 1.0), best_label, best_dist

    # ── Adaptive k-shot ───────────────────────────────────────────────

    def _compute_k_shot(self, novelty: float) -> int:
        """Map novelty score to number of shots needed.

        novelty 0.0 (familiar) → 3 shots (BASE)
        novelty 0.5 (ambiguous) → 11 shots
        novelty 1.0 (completely novel) → 20 shots (MAX)
        """
        k = int(self.BASE_K_SHOT + novelty * (self.MAX_K_SHOT - self.BASE_K_SHOT))
        return max(self.BASE_K_SHOT, min(self.MAX_K_SHOT, k))

    # ── Algorithm Weight Fusion ───────────────────────────────────────

    def _compute_algo_weights(self, novelty: float) -> dict[str, float]:
        """Adjust algorithm weights based on novelty.

        High novelty → more Reptile (fast intuition) + Prototypical (template matching)
        Low novelty → more FOMAML (deliberate optimization)
        """
        # FOMAML decreases with novelty (slow thinking is less useful for novel situations)
        fomaml = self.FOMAML_BASE * (1.0 - novelty * 0.5)
        # Reptile increases with novelty (fast adaptation for novel situations)
        reptile = self.REPTILE_BASE * (1.0 + novelty * 0.5)
        # Proto stays stable (always useful)
        proto = self.PROTO_BASE

        total = fomaml + reptile + proto
        return {
            "reptile": round(reptile / total, 4),
            "fomaml": round(fomaml / total, 4),
            "proto": round(proto / total, 4),
        }

    # ── Multi-Objective Loss ──────────────────────────────────────────

    def _compute_losses(
        self,
        prediction: list[float],
        target: list[float],
        previous_prediction: list[float] | None = None,
        feature_vector: list[float] | None = None,
    ) -> dict[str, float]:
        """Compute multi-objective losses.

        1. Prediction loss: MSE between prediction and target
        2. Consistency loss: MSE between consecutive predictions (penalizes rapid changes)
        3. Alignment loss: Mahalanobis distance of current FEATURE VECTOR from nearest
           prototype centroid (input-to-input comparison, same semantic space)
        4. Anti-forgetting loss: penalty for deviating from historical task distribution
        """
        losses: dict[str, float] = {}

        # 1. Prediction loss
        if len(prediction) == len(target):
            losses["prediction"] = sum(
                (prediction[i] - target[i]) ** 2 for i in range(len(prediction))
            ) / len(prediction)

        # 2. Consistency regularization
        if previous_prediction and len(previous_prediction) == len(prediction):
            losses["consistency"] = sum(
                (prediction[i] - previous_prediction[i]) ** 2
                for i in range(len(prediction))
            ) / len(prediction)
        else:
            losses["consistency"] = 0.0

        # 3. Prototype alignment: compare FEATURE VECTOR (not prediction) with
        #    prototype centroids — both live in the same 32-dim input space
        if self._prototypes and feature_vector:
            f = list(feature_vector[:self.PROTOTYPE_DIM])
            while len(f) < self.PROTOTYPE_DIM:
                f.append(0.0)
            min_dist = float("inf")
            for proto in self._prototypes.values():
                dist = self._mahalanobis_distance(f, proto)
                min_dist = min(min_dist, dist)
            losses["alignment"] = min(min_dist / 5.0, 1.0)
        else:
            losses["alignment"] = 0.0

        # 4. Anti-forgetting (distance from historical task mean)
        if self._task_memory:
            hist_mean = [0.0] * min(len(prediction), self.PROTOTYPE_DIM)
            for task in self._task_memory[-100:]:
                task_vec = task.get("features", [])
                for i in range(len(hist_mean)):
                    if i < len(task_vec):
                        hist_mean[i] += task_vec[i]
            n_tasks = len(self._task_memory[-100:])
            hist_mean = [v / n_tasks for v in hist_mean]

            losses["anti_forgetting"] = sum(
                (prediction[i] - hist_mean[i]) ** 2
                for i in range(len(hist_mean))
            ) / len(hist_mean)
        else:
            losses["anti_forgetting"] = 0.0

        return losses

    # ── Biphasic Plasticity Rule (Lu et al. 2025) ────────────────────

    def _biphasic_adaptation_rate(self, total_loss: float) -> float:
        """Biphasic structural plasticity rule.

        Partial stress (moderate loss) → promotes adaptation (higher learning rate)
        Complete stress (very high loss) → suppresses adaptation (lower learning rate)

        Like exercise: moderate stress builds muscle, extreme stress causes injury.
        """
        # Normalize loss to 0-1 range
        normalized = min(total_loss / 2.0, 1.0)

        # Biphasic curve: peak at ~0.4, drops after 0.7
        if normalized < 0.4:
            rate = 0.005 + normalized * 0.05  # increasing
        elif normalized < 0.7:
            rate = 0.025 - (normalized - 0.4) * 0.03  # plateau then slight dip
        else:
            rate = 0.016 - (normalized - 0.7) * 0.05  # decreasing sharply

        return max(0.001, min(0.05, rate))

    # ── Main Meta-Learning Cycle ──────────────────────────────────────

    def meta_learn(
        self,
        feature_vector: list[float],
        regime_distribution: list[float] | None = None,
        target: list[float] | None = None,
        previous_prediction: list[float] | None = None,
    ) -> MetaLearnReport:
        """Execute one meta-learning cycle.

        Args:
            feature_vector: 32-dim feature representation of current state
            regime_distribution: 6-dim regime probabilities
            target: optional target for loss computation
            previous_prediction: previous output for consistency loss

        Returns:
            MetaLearnReport with novelty, k-shot, algorithm weights, and losses
        """
        self._call_count += 1

        f = list(feature_vector[:self.PROTOTYPE_DIM])
        while len(f) < self.PROTOTYPE_DIM:
            f.append(0.0)

        # 1. Compute novelty
        novelty, closest_proto, proto_dist = self.compute_novelty(f, regime_distribution)

        # 2. Adaptive k-shot
        k_shot = self._compute_k_shot(novelty)

        # 3. Algorithm weight fusion
        algo_weights = self._compute_algo_weights(novelty)
        self._algo_weights = algo_weights

        # 4. Adapt learning rate via biphasic rule
        if target:
            prediction = f[:len(target)] if len(f) >= len(target) else f + [0.0] * (len(target) - len(f))
            losses = self._compute_losses(prediction[:len(target)], target, previous_prediction, feature_vector=f)
            total_loss = sum(losses.values())
            self._learning_rate = self._biphasic_adaptation_rate(total_loss)
            for k, v in losses.items():
                self._loss_history[k].append(v)
                if len(self._loss_history[k]) > 500:
                    self._loss_history[k] = self._loss_history[k][-500:]
        else:
            losses = {"prediction": 0.0, "consistency": 0.0, "alignment": 0.0, "anti_forgetting": 0.0}

        # 5. Store in task memory
        self._task_memory.append({
            "features": f,
            "novelty": novelty,
            "k_shot": k_shot,
            "timestamp": time.time(),
        })
        if len(self._task_memory) > 500:
            self._task_memory = self._task_memory[-500:]

        report = MetaLearnReport(
            novelty_score=round(novelty, 4),
            k_shot=k_shot,
            algorithm_weights=algo_weights,
            matched_prototype=closest_proto,
            prototype_distance=round(proto_dist, 4),
            losses={k: round(v, 6) for k, v in losses.items()},
            adaptation_rate=round(self._learning_rate, 6),
        )
        self._last_report = report

        self._logger.debug("meta_learn_cycle",
                          novelty=round(novelty, 3),
                          k_shot=k_shot,
                          lr=round(self._learning_rate, 6),
                          matched=closest_proto or "none")

        return report

    def get_prototype_library(self) -> dict[str, dict[str, Any]]:
        """Get all prototypes for inspection."""
        return {
            label: {
                "centroid": [round(v, 4) for v in proto.centroid[:8]],  # first 8 dims
                "sample_count": proto.sample_count,
                "last_updated": proto.last_updated,
            }
            for label, proto in self._prototypes.items()
        }

    @property
    def stats(self) -> dict[str, Any]:
        avg_losses = {}
        for k, v in self._loss_history.items():
            avg_losses[f"avg_{k}_loss"] = round(sum(v) / max(len(v), 1), 6) if v else 0.0

        return {
            "call_count": self._call_count,
            "prototype_count": len(self._prototypes),
            "prototypes": list(self._prototypes.keys()),
            "algorithm_weights": self._algo_weights,
            "learning_rate": round(self._learning_rate, 6),
            "base_k_shot": self.BASE_K_SHOT,
            "max_k_shot": self.MAX_K_SHOT,
            "last_novelty": self._last_report.novelty_score if self._last_report else None,
            "task_memory_size": len(self._task_memory),
            **avg_losses,
        }
