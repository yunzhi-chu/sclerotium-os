"""L0/L3a: MultiDistributionTemporalSampler v4.0 — "时序记忆巩固" (Temporal Memory Consolidation).

Biological Metaphor:
  海马体记忆巩固——睡眠中重放白天的经历(sharp-wave ripples),
  但不是等权重重放——情绪强烈的事件被优先巩固

  三分布混合:
    1. 高斯核(近期聚焦) = 最近的学习材料记得最清(近因效应)
    2. 指数衰减核(长期记忆) = 童年的记忆随时间衰减但永不消失
    3. 均匀核(全局搜索) = 偶尔翻看旧笔记, 防知识过时

  反遗忘正则(8%远期强制保留) = 最小保留机制,
  如同大脑不会完全忘记母语(即使多年不说)

  短期偏误检测(最近10%>60%→自动修正)
  = 防止"考试前只复习最后一章"的偏差

Reference:
  Averbeck & Brunel (2025), "Synaptic pruning, myelination and emergence of
  dominant attractors", NIMH;
  Zinjad et al. (2026), "FOMAML+Reptile ensemble", IJISA 18(2):27-43
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class SampleBatch:
    """A batch of temporally-weighted samples for training."""

    indices: list[int]  # indices into the experience buffer
    weights: list[float]  # importance weight per sample
    distribution_name: str  # which distribution generated this batch
    recency_bias: float  # measured recency bias (0-1)
    timestamp: float = field(default_factory=time.time)


@dataclass
class SamplerState:
    """State of the temporal sampler for diagnostics."""

    buffer_size: int
    recent_fraction: float  # fraction of samples in recent window
    distribution_weights: dict[str, float]  # current mix ratios
    anti_forgetting_active: bool
    recency_bias_detected: bool


class MultiDistributionTemporalSampler:
    """Three-distribution temporal sampler with anti-forgetting regularization.

    The "hippocampal memory consolidation" system — decides which past
    experiences to replay for learning, with emotional (profit/loss) weighting.

    Architecture:
      - Gaussian kernel: weighted toward recent samples (recency effect)
      - Exponential decay kernel: long-term memory with slow decay
      - Uniform kernel: exploration to prevent knowledge obsolescence
      - Anti-forgetting regularization: 8% forced long-term retention
      - Recency bias detection and auto-correction
    """

    GAUSSIAN_WEIGHT = 0.50  # 50% recent focus
    EXPONENTIAL_WEIGHT = 0.30  # 30% long-term memory
    UNIFORM_WEIGHT = 0.20  # 20% global exploration
    ANTI_FORGETTING_RATIO = 0.08  # 8% minimum long-term retention
    RECENCY_BIAS_THRESHOLD = 0.60  # >60% recent = bias detected

    def __init__(self, buffer_size: int = 1000) -> None:
        self._buffer_size = buffer_size
        self._logger = CortexLogger("temporal_sampler")
        self._call_count = 0

        # Experience buffer: list of (importance_score, timestep)
        self._buffer: list[tuple[float, int]] = []
        self._total_steps: int = 0

        # Distribution weights (adaptable)
        self._dist_weights = {
            "gaussian": self.GAUSSIAN_WEIGHT,
            "exponential": self.EXPONENTIAL_WEIGHT,
            "uniform": self.UNIFORM_WEIGHT,
        }

        # For anti-forgetting: track which indices were sampled
        self._sample_counts: dict[int, int] = {}
        self._forgotten_threshold: int = 3  # min samples before considered "forgotten"

        # Recent bias tracking
        self._recent_sampling_history: list[float] = []

    # ── Buffer Management ─────────────────────────────────────────────

    def add_experience(self, importance: float, timestep: int | None = None) -> None:
        """Add an experience to the memory buffer.

        Like encoding a new episodic memory in the hippocampus.
        Higher importance = emotionally salient event = more likely to be consolidated.
        """
        if timestep is None:
            self._total_steps += 1
            timestep = self._total_steps

        self._buffer.append((importance, timestep))

        # Maintain buffer size (oldest memories fade first, like normal forgetting)
        if len(self._buffer) > self._buffer_size:
            removed_idx = len(self._buffer) - self._buffer_size
            self._buffer = self._buffer[-self._buffer_size:]
            # Clean up sample counts for removed entries
            self._sample_counts = {
                k - removed_idx: v
                for k, v in self._sample_counts.items()
                if k - removed_idx >= 0
            }

    # ── Sampling Kernels ──────────────────────────────────────────────

    def _gaussian_kernel(self, n_samples: int) -> SampleBatch:
        """Gaussian kernel: focus on recent experiences (recency effect).

        Like sharp-wave ripples preferentially replaying recent events.
        """
        n = len(self._buffer)
        if n == 0:
            return SampleBatch(indices=[], weights=[], distribution_name="gaussian", recency_bias=0.0)

        # Gaussian centered at the most recent index
        center = n - 1  # most recent
        sigma = max(n * 0.15, 5.0)  # std proportional to buffer size

        indices: list[int] = []
        weights: list[float] = []
        for _ in range(min(n_samples, n)):
            # Sample index using Gaussian CDF inversion
            z = _pseudo_random(self._call_count * 1000 + len(indices))
            idx = int(center + sigma * math.sqrt(2) * _erfinv(2 * z - 1))
            idx = max(0, min(n - 1, idx))
            indices.append(idx)
            # Weight by importance
            imp, _ = self._buffer[idx]
            weights.append(imp)

        # Normalize weights
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        return SampleBatch(
            indices=indices,
            weights=weights,
            distribution_name="gaussian",
            recency_bias=self._measure_recency(indices),
        )

    def _exponential_kernel(self, n_samples: int) -> SampleBatch:
        """Exponential decay kernel: long-term memory (slow decay).

        Like childhood memories — fade with time but never completely gone.
        """
        n = len(self._buffer)
        if n == 0:
            return SampleBatch(indices=[], weights=[], distribution_name="exponential", recency_bias=0.0)

        # Decay factor: newer = higher probability
        decay = 0.995  # slow decay per step
        sample_weights = [0.0] * n
        for i in range(n):
            age = n - 1 - i  # distance from most recent
            sample_weights[i] = decay ** age

        total_sw = sum(sample_weights)
        if total_sw > 0:
            probs = [w / total_sw for w in sample_weights]
        else:
            probs = [1.0 / n] * n

        # Weighted random sampling
        indices: list[int] = []
        weights: list[float] = []
        for _ in range(min(n_samples, n)):
            idx = self._weighted_sample(probs)
            indices.append(idx)
            imp, _ = self._buffer[idx]
            weights.append(imp)

        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        return SampleBatch(
            indices=indices,
            weights=weights,
            distribution_name="exponential",
            recency_bias=self._measure_recency(indices),
        )

    def _uniform_kernel(self, n_samples: int) -> SampleBatch:
        """Uniform kernel: global exploration (prevent knowledge obsolescence).

        Like occasionally reviewing old textbooks to prevent knowledge decay.
        """
        n = len(self._buffer)
        if n == 0:
            return SampleBatch(indices=[], weights=[], distribution_name="uniform", recency_bias=0.0)

        # Uniform random sampling
        indices: list[int] = []
        weights: list[float] = []
        for _ in range(min(n_samples, n)):
            idx = int(_pseudo_random(self._call_count * 2000 + len(indices)) * n)
            idx = min(idx, n - 1)
            indices.append(idx)
            imp, _ = self._buffer[idx]
            weights.append(imp)

        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        return SampleBatch(
            indices=indices,
            weights=weights,
            distribution_name="uniform",
            recency_bias=self._measure_recency(indices),
        )

    # ── Main Sampling ─────────────────────────────────────────────────

    def sample(self, n_samples: int = 32) -> SampleBatch:
        """Sample from the three-distribution mixture.

        The mix ratio is:
          - 50% Gaussian (recent focus)
          - 30% Exponential (long-term memory)
          - 20% Uniform (global exploration)

        With anti-forgetting correction applied post-hoc.

        Returns:
            SampleBatch with indices, weights, and diagnostics
        """
        self._call_count += 1

        if not self._buffer:
            return SampleBatch(indices=[], weights=[], distribution_name="empty", recency_bias=0.0)

        # Allocate samples per distribution
        n_gauss = max(1, int(n_samples * self._dist_weights["gaussian"]))
        n_exp = max(1, int(n_samples * self._dist_weights["exponential"]))
        n_unif = max(1, n_samples - n_gauss - n_exp)

        # Sample from each distribution
        gauss_batch = self._gaussian_kernel(n_gauss)
        exp_batch = self._exponential_kernel(n_exp)
        unif_batch = self._uniform_kernel(n_unif)

        # Merge
        all_indices = gauss_batch.indices + exp_batch.indices + unif_batch.indices
        all_weights = gauss_batch.weights + exp_batch.weights + unif_batch.weights

        # Anti-forgetting correction: ensure 8% of samples are from "forgotten" regions
        all_indices, all_weights = self._apply_anti_forgetting(all_indices, all_weights)

        # Update sample counts
        for idx in all_indices:
            self._sample_counts[idx] = self._sample_counts.get(idx, 0) + 1

        # Detect and correct recency bias
        recency_bias = self._measure_recency(all_indices)
        self._recent_sampling_history.append(recency_bias)
        if len(self._recent_sampling_history) > 100:
            self._recent_sampling_history = self._recent_sampling_history[-100:]

        if recency_bias > self.RECENCY_BIAS_THRESHOLD:
            self._logger.warn("recency_bias_detected",
                            bias=round(recency_bias, 3),
                            correction="increasing_uniform_weight")
            # Auto-correct: increase uniform weight
            self._dist_weights["uniform"] = min(0.40, self._dist_weights["uniform"] + 0.05)
            self._dist_weights["gaussian"] = max(0.30, self._dist_weights["gaussian"] - 0.05)
        elif recency_bias < 0.30 and self._dist_weights["uniform"] > self.UNIFORM_WEIGHT:
            # Gradually restore default mix
            self._dist_weights["uniform"] = max(self.UNIFORM_WEIGHT, self._dist_weights["uniform"] - 0.02)
            self._dist_weights["gaussian"] = min(self.GAUSSIAN_WEIGHT, self._dist_weights["gaussian"] + 0.02)

        return SampleBatch(
            indices=all_indices,
            weights=all_weights,
            distribution_name="mixture",
            recency_bias=round(recency_bias, 3),
        )

    # ── Anti-Forgetting ───────────────────────────────────────────────

    def _apply_anti_forgetting(
        self, indices: list[int], weights: list[float]
    ) -> tuple[list[int], list[float]]:
        """Ensure 8% of samples come from rarely-sampled (potentially forgotten) regions.

        Like the brain's mechanism for preserving childhood memories —
        even rarely-accessed memories get periodic reinforcement.
        """
        n = len(self._buffer)
        if n == 0:
            return indices, weights

        # Identify "forgotten" indices (sampled below threshold)
        forgotten = [
            i for i in range(n)
            if self._sample_counts.get(i, 0) < self._forgotten_threshold
        ]

        if not forgotten:
            return indices, weights

        # Replace 8% of samples with forgotten ones
        n_replace = max(1, int(len(indices) * self.ANTI_FORGETTING_RATIO))

        for k in range(min(n_replace, len(forgotten))):
            if k < len(indices):
                idx = forgotten[int(_pseudo_random(k * 7777) * len(forgotten)) % len(forgotten)]
                indices[k] = idx
                imp, _ = self._buffer[idx]
                weights[k] = imp

        # Re-normalize
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        return indices, weights

    def _measure_recency(self, indices: list[int]) -> float:
        """Measure what fraction of samples are from the recent 10% of buffer."""
        if not self._buffer or not indices:
            return 0.0
        n = len(self._buffer)
        recent_cutoff = int(n * 0.9)  # top 10%
        recent_count = sum(1 for i in indices if i >= recent_cutoff)
        return recent_count / len(indices)

    @staticmethod
    def _weighted_sample(probs: list[float]) -> int:
        """Sample an index according to probability distribution."""
        r = _pseudo_random(int(time.time() * 1000000) % 1000000)
        cumsum = 0.0
        for i, p in enumerate(probs):
            cumsum += p
            if r <= cumsum:
                return i
        return len(probs) - 1

    def get_state(self) -> SamplerState:
        """Get diagnostic state of the sampler."""
        n = len(self._buffer)
        if n > 0:
            recent_cutoff = int(n * 0.9)
            recent_count = self._sample_counts.get(0, 0)  # simplified
            for i in range(recent_cutoff, n):
                recent_count += self._sample_counts.get(i, 0)
            total_samples = sum(self._sample_counts.values()) + 1
            recent_fraction = recent_count / total_samples
        else:
            recent_fraction = 0.0

        return SamplerState(
            buffer_size=n,
            recent_fraction=round(recent_fraction, 3),
            distribution_weights={k: round(v, 3) for k, v in self._dist_weights.items()},
            anti_forgetting_active=True,
            recency_bias_detected=(
                self._recent_sampling_history[-1] > self.RECENCY_BIAS_THRESHOLD
                if self._recent_sampling_history else False
            ),
        )

    @property
    def stats(self) -> dict[str, Any]:
        state = self.get_state()
        return {
            "call_count": self._call_count,
            "buffer_size": state.buffer_size,
            "distribution_weights": state.distribution_weights,
            "recent_fraction": state.recent_fraction,
            "recency_bias_detected": state.recency_bias_detected,
            "anti_forgetting_ratio": self.ANTI_FORGETTING_RATIO,
        }


# ── Math Helpers ──────────────────────────────────────────────────────

def _pseudo_random(seed: int) -> float:
    x = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    return (x % 1000000) / 1000000.0


def _erfinv(x: float) -> float:
    """Approximate inverse error function."""
    a = 0.147
    y = math.log(1 - x * x) if abs(x) < 1 else 0.0
    sign = 1 if x >= 0 else -1
    return sign * math.sqrt(
        max(0, (2 / (math.pi * a) + y / 2) ** 2 - y / a) - (2 / (math.pi * a) + y / 2)
    )
