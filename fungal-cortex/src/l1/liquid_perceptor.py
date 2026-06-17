"""L1a: LiquidPerceptor — "液态视网膜" (Liquid Retina).

Biological Metaphor:
  神经元膜电位 — 连续时间积分，自适应放电阈值
  视网膜神经节细胞 — 光强度→脉冲频率编码，ON/OFF双通道

  LNN 替代传统 HMM:
  - HMM: 离散状态转移，固定时间步 (离散时间马尔可夫链)
  - LNN: ODE连续时间动力系统，自适应计算时间 (NODEs家族)

  核心优势:
  1. 参数效率: 数十神经元 vs 数百万参数 (HCFC验证)
  2. 持续适应: 隐藏状态隐式适应分布偏移，无需重训练
  3. 因果性: ODE保证时间连续性，消除离散跃迁伪影
  4. 计算自适应: τ学习控制信息吸收速率
     - 高意外输入 → τ↑ (慢衰减，更多处理)
     - 熟悉输入 → τ↓ (快衰减，快速通过)

  ODE形式:
    ẋ(t) = -(1/τ)·x(t) + g(Wx·x(t) + Wu·u(t) + b)

    where:
      x(t) ∈ ℝⁿ  — 隐藏状态向量 (n=N_HIDDEN)
      u(t) ∈ ℝᵐ  — 输入信号 (m取决于模态)
      τ ∈ ℝ₊     — 液态时间常数 (控制衰减速率)
      g(·)       — 非线性激活 (tanh)
      Wx, Wu, b  — 可学习参数

Reference:
  Hasani et al. (2026), "Liquid Foundation Model 2.5", MIT/Liquid AI
  Zhu et al. (Apr 2025), "LNNs maintain performance under moderate distribution shift"
  Lechner et al. (2020), "Neural ODEs for Irregularly Sampled Time Series", NeurIPS
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Optional

import numpy as np

from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class ModalityType(Enum):
    """Supported input modalities for the LiquidPerceptor."""

    TIME_SERIES = "time_series"   # Price/volume/volatility sequences
    TEXT = "text"                 # News/announcements/social media
    IMAGE = "image"               # Satellite/chart/technical pattern
    AUDIO = "audio"               # Earnings calls/central bank speeches
    BIOELECTRIC = "bioelectric"   # Mycelium spike trains


@dataclass
class DataPoint:
    """A single multimodal data point entering the perception stream.

    Like a single photon hitting a retinal ganglion cell.
    """

    modality: ModalityType
    vector: np.ndarray          # Embedded feature vector (modality-dependent dim)
    timestamp: float = field(default_factory=time.time)
    weight: float = 1.0         # Importance weight (0-1), like synaptic strength
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LiquidState:
    """The hidden state of the Liquid Time Constant ODE.

    This is the "membrane potential" of the liquid perceptron.
    """

    x: np.ndarray               # Hidden state vector
    tau: float                  # Current time constant (adaptive)
    surprise: float             # Recent surprise level (prediction error EMA)
    confidence: float           # Recent confidence level (inverse uncertainty)
    last_update: float = field(default_factory=time.time)


@dataclass
class Percept:
    """Processed perception output — what the liquid retina "sees".

    This is passed to L2 (LiquidTimeConstantNet) for hyper-parameter generation.
    """

    vector: np.ndarray              # Percept embedding (N_HIDDEN-dim)
    modality: ModalityType
    surprise: float                 # How unexpected this percept is (0-1)
    confidence: float               # How confident the model is (0-1)
    tau_used: float                 # The time constant used for processing
    computation_steps: int          # ODE solver steps taken (adaptive cost)
    regime_hint: str = "unknown"    # Quick regime guess for downstream routing
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LiquidPerceptorConfig:
    """Configuration for the LiquidPerceptor.

    All parameters have sensible defaults derived from the LFM2.5 paper.
    """

    n_hidden: int = 64                 # Hidden state dimension
    n_input_time_series: int = 20      # Input dim for time-series modality
    n_input_text: int = 768            # Input dim for text (embedding size)
    n_input_image: int = 512           # Input dim for image
    n_input_audio: int = 256           # Input dim for audio
    n_input_bioelectric: int = 16      # Input dim for mycelium data

    tau_min: float = 0.1              # Minimum time constant (fastest response)
    tau_max: float = 5.0              # Maximum time constant (deepest processing)
    tau_default: float = 1.0          # Default time constant

    surprise_ema_alpha: float = 0.1   # EMA smoothing for surprise tracking
    confidence_ema_alpha: float = 0.05  # EMA smoothing for confidence tracking

    ode_solver_steps_min: int = 4     # Minimum ODE solver steps
    ode_solver_steps_max: int = 64    # Maximum ODE solver steps
    ode_rtol: float = 1e-3            # ODE relative tolerance
    ode_atol: float = 1e-5            # ODE absolute tolerance

    adaptation_window: int = 100      # Window for distribution shift detection
    adaptation_threshold: float = 0.15  # KL divergence threshold for adaptation

    # Derived from LFM2.5 paper: LNNs maintain performance under moderate
    # distribution shift without retraining (Zhu et al., Apr 2025)


# ═══════════════════════════════════════════════════════════════════════
# Core Implementation
# ═══════════════════════════════════════════════════════════════════════


class LiquidPerceptor:
    """ODE-driven continuous-time perception engine.

    The "liquid retina" of the AGI system — perceives any modality through
    the lens of a continuous-time dynamical system. Unlike discrete HMMs,
    the LNN formulation allows:
      - Variable computation time per input (τ adaptation)
      - Smooth handling of irregularly-sampled data
      - Implicit distribution shift adaptation
      - Causal temporal consistency guaranteed by ODE integration

    Architecture:
      Input u(t) → ODE Layer (Wx, Wu, b, τ) → Hidden state x(t) → Readout → Percept

    Usage::

        perceptor = LiquidPerceptor()
        async for data_point in data_stream:
            percept = await perceptor.perceive(data_point)
            # percept flows to L2 LiquidTimeConstantNet
    """

    def __init__(self, config: LiquidPerceptorConfig | None = None) -> None:
        self._config = config or LiquidPerceptorConfig()
        self._logger = CortexLogger("liquid_perceptor")

        # --- Weight initialization (Xavier uniform) ---
        c = self._config
        rng = np.random.RandomState(42)

        # We initialize weights for ALL modalities at once.
        # The max input dim determines the Wu matrix shape; smaller modalities
        # use a slice of the weight matrix.
        self._max_input_dim = max(
            c.n_input_time_series,
            c.n_input_text,
            c.n_input_image,
            c.n_input_audio,
            c.n_input_bioelectric,
        )

        # Wx: recurrent weights (n_hidden × n_hidden)
        self._Wx: np.ndarray = rng.randn(c.n_hidden, c.n_hidden) * math.sqrt(
            2.0 / (c.n_hidden + c.n_hidden)
        )
        # Wu: input weights (n_hidden × max_input_dim)
        self._Wu: np.ndarray = rng.randn(c.n_hidden, self._max_input_dim) * math.sqrt(
            2.0 / (c.n_hidden + self._max_input_dim)
        )
        # b: bias
        self._b: np.ndarray = np.zeros(c.n_hidden)

        # --- State ---
        self._state = LiquidState(
            x=np.zeros(c.n_hidden),
            tau=c.tau_default,
            surprise=0.0,
            confidence=0.5,
        )

        # --- Adaptation tracking ---
        self._recent_outputs: deque[np.ndarray] = deque(maxlen=c.adaptation_window)
        self._recent_surprises: deque[float] = deque(maxlen=c.adaptation_window)
        self._call_count: int = 0
        self._total_steps: int = 0  # Total ODE solver steps (efficiency metric)

        self._logger.info("liquid_perceptor_initialized",
                          n_hidden=c.n_hidden,
                          tau_default=c.tau_default,
                          max_input_dim=self._max_input_dim)

    # ── Public API ────────────────────────────────────────────────────

    async def perceive(self, data: DataPoint) -> Percept:
        """Process a single data point through the liquid ODE.

        This is the main entry point. Each call:
        1. Embeds the input into the appropriate dimensional space
        2. Runs the ODE forward for adaptive number of steps
        3. Reads out the percept from the hidden state
        4. Updates surprise/confidence tracking
        5. Adapts τ based on prediction quality

        Args:
            data: A multimodal DataPoint with embedded feature vector.

        Returns:
            Percept with the processed perception, ready for L2 routing.
        """
        self._call_count += 1

        # 1. Embed input to match Wu dimensions
        u = self._embed_input(data)

        # 2. Run ODE forward pass
        hidden, steps = self._liquid_forward(u)

        # 3. Readout: compute percept vector + surprise
        percept_vec = self._readout(hidden)
        surprise = self._compute_surprise(percept_vec)
        confidence = self._compute_confidence()

        # 4. Adaptive τ update (core LNN innovation)
        self._adapt_tau(surprise, confidence)

        # 5. Update state
        self._state.x = hidden
        self._state.surprise = surprise
        self._state.confidence = confidence
        self._state.last_update = time.time()
        self._total_steps += steps

        # 6. Track for distribution shift detection
        self._recent_outputs.append(percept_vec.copy())
        self._recent_surprises.append(surprise)

        # 7. Quick regime classification
        regime_hint = self._classify_regime(percept_vec, surprise)

        return Percept(
            vector=percept_vec,
            modality=data.modality,
            surprise=round(surprise, 4),
            confidence=round(confidence, 4),
            tau_used=self._state.tau,
            computation_steps=steps,
            regime_hint=regime_hint,
            metadata=data.metadata,
        )

    async def perceive_stream(
        self, stream: AsyncIterator[DataPoint],
    ) -> AsyncIterator[Percept]:
        """Process a continuous stream of data points.

        Like the retina processing a continuous stream of photons.
        Maintains temporal context across stream elements.

        Usage::

            async for percept in perceptor.perceive_stream(data_stream):
                yield percept
        """
        async for data_point in stream:
            yield await self.perceive(data_point)

    def perceive_batch(self, batch: list[DataPoint]) -> list[Percept]:
        """Synchronous batch processing for non-async contexts.

        Each item is processed sequentially to maintain ODE temporal continuity.
        """
        results: list[Percept] = []
        for data_point in batch:
            # Synchronous version of perceive()
            self._call_count += 1
            u = self._embed_input(data_point)
            hidden, steps = self._liquid_forward(u)
            percept_vec = self._readout(hidden)
            surprise = self._compute_surprise(percept_vec)
            confidence = self._compute_confidence()
            self._adapt_tau(surprise, confidence)

            self._state.x = hidden
            self._state.surprise = surprise
            self._state.confidence = confidence
            self._state.last_update = time.time()
            self._total_steps += steps
            self._recent_outputs.append(percept_vec.copy())
            self._recent_surprises.append(surprise)

            results.append(Percept(
                vector=percept_vec,
                modality=data_point.modality,
                surprise=round(surprise, 4),
                confidence=round(confidence, 4),
                tau_used=self._state.tau,
                computation_steps=steps,
                regime_hint=self._classify_regime(percept_vec, surprise),
                metadata=data_point.metadata,
            ))
        return results

    # ── Core ODE Mechanics ────────────────────────────────────────────

    def _liquid_forward(self, u: np.ndarray) -> tuple[np.ndarray, int]:
        """ODE forward propagation: ẋ = -(1/τ)·x + tanh(Wx·x + Wu·u + b)

        Uses adaptive-step RK4 (Runge-Kutta 4th order) for stable integration.
        The number of steps adapts to the current τ: larger τ → more steps
        (slower decay, deeper processing).

        Args:
            u: Input vector (max_input_dim, zero-padded for unused dims)

        Returns:
            (final_hidden_state, solver_steps_taken)
        """
        c = self._config
        tau = self._state.tau
        x = self._state.x.copy()

        # Adaptive step count: larger τ → more steps (deeper processing)
        # τ maps to [ode_solver_steps_min, ode_solver_steps_max] logarithmically
        tau_ratio = (math.log(tau) - math.log(c.tau_min)) / (
            math.log(c.tau_max) - math.log(c.tau_min) + 1e-8
        )
        tau_ratio = max(0.0, min(1.0, tau_ratio))
        n_steps = int(c.ode_solver_steps_min + tau_ratio * (
            c.ode_solver_steps_max - c.ode_solver_steps_min
        ))

        dt = 1.0 / n_steps

        # ODE right-hand side: dx/dt
        def ode_rhs(xv: np.ndarray) -> np.ndarray:
            # tanh(Wx·x + Wu·u + b)
            preact = self._Wx @ xv + self._Wu @ u + self._b
            activation = np.tanh(preact)
            # ẋ = -(1/τ)·x + activation
            return -(1.0 / tau) * xv + activation

        # RK4 integration
        for _ in range(n_steps):
            k1 = ode_rhs(x)
            k2 = ode_rhs(x + 0.5 * dt * k1)
            k3 = ode_rhs(x + 0.5 * dt * k2)
            k4 = ode_rhs(x + dt * k3)
            x = x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

            # Stability clamp
            x = np.clip(x, -10.0, 10.0)

        return x, n_steps

    def _embed_input(self, data: DataPoint) -> np.ndarray:
        """Embed a data point into the fixed max_input_dim space.

        Different modalities use different slices of the Wu weight matrix.
        Zero-padding ensures consistent dimensionality.
        """
        c = self._config
        vec = data.vector.astype(np.float64)

        # Determine target dim based on modality
        dim_map = {
            ModalityType.TIME_SERIES: c.n_input_time_series,
            ModalityType.TEXT: c.n_input_text,
            ModalityType.IMAGE: c.n_input_image,
            ModalityType.AUDIO: c.n_input_audio,
            ModalityType.BIOELECTRIC: c.n_input_bioelectric,
        }
        target_dim = dim_map.get(data.modality, c.n_input_time_series)

        # Pad or truncate to target_dim
        if len(vec) < target_dim:
            padded = np.zeros(target_dim)
            padded[:len(vec)] = vec
            vec = padded
        elif len(vec) > target_dim:
            vec = vec[:target_dim]

        # Pad to max_input_dim (zero-fill unused dimensions)
        result = np.zeros(self._max_input_dim)
        result[:target_dim] = vec

        # Apply importance weight
        result *= data.weight

        return result

    def _readout(self, hidden: np.ndarray) -> np.ndarray:
        """Read out the percept vector from the hidden state.

        The readout is the hidden state itself (linear readout),
        which preserves the full representational content for downstream layers.
        """
        return hidden.copy()

    # ── Surprise & Confidence Tracking ─────────────────────────────────

    def _compute_surprise(self, percept: np.ndarray) -> float:
        """Compute surprise as normalized prediction error.

        Compares current percept to EMA of recent percepts.
        Large deviation → high surprise → triggers τ increase (deeper processing).
        """
        if len(self._recent_outputs) < 2:
            return 0.0

        # EMA prediction: expected = EMA of recent outputs
        recent = np.array(self._recent_outputs)
        ema = recent[-1].copy() if len(recent) == 1 else np.mean(recent[-10:], axis=0)

        # Normalized L2 error
        err = np.linalg.norm(percept - ema)
        norm = np.linalg.norm(ema) + 1e-8

        return float(np.clip(err / norm, 0.0, 1.0))

    def _compute_confidence(self) -> float:
        """Compute confidence as inverse of recent surprise variance.

        High variance in recent surprises → low confidence.
        Low variance → high confidence (stable environment).
        """
        if len(self._recent_surprises) < 5:
            return 0.5

        recent = list(self._recent_surprises)[-20:]
        mean_surprise = sum(recent) / len(recent)
        variance = sum((s - mean_surprise) ** 2 for s in recent) / len(recent)

        # Confidence = 1 / (1 + variance), normalized to [0, 1]
        return float(1.0 / (1.0 + variance * 5.0))

    # ── Adaptive Time Constant ─────────────────────────────────────────

    def _adapt_tau(self, surprise: float, confidence: float) -> None:
        """Adapt the liquid time constant based on surprise and confidence.

        The core LNN innovation — τ controls how fast information decays:
          τ_new = τ_old × (1 + α·surprise - β·confidence)

        - High surprise + low confidence → τ↑ (slow decay, deep processing)
        - Low surprise + high confidence → τ↓ (fast decay, reflexive action)

        This is analogous to:
          - Neural attention: surprising stimuli → more processing time
          - Pupil dilation: novel scenes → more light intake
          - Mycelium growth: nutrient gradient → slower, more careful exploration

        References:
          Hasani et al. (2026), "LFM 2.5": adaptive computation time via τ
          Ha et al. (2022), "Liquid Structural State-Space Models" (NeurIPS)
        """
        c = self._config
        alpha = 0.3   # Surprise sensitivity (how much surprise slows processing)
        beta = 0.15   # Confidence sensitivity (how much confidence speeds processing)

        tau_old = self._state.tau
        adjustment = 1.0 + alpha * surprise - beta * confidence
        tau_new = tau_old * adjustment

        # Clamp to valid range
        tau_new = max(c.tau_min, min(c.tau_max, tau_new))

        self._state.tau = tau_new

        if abs(tau_new - tau_old) / (tau_old + 1e-8) > 0.1:
            self._logger.debug("tau_adapted",
                               old_tau=round(tau_old, 3),
                               new_tau=round(tau_new, 3),
                               surprise=round(surprise, 3),
                               confidence=round(confidence, 3))

    # ── Regime Classification ──────────────────────────────────────────

    def _classify_regime(self, percept: np.ndarray, surprise: float) -> str:
        """Quick heuristic regime classification from percept statistics.

        Provides a hint for downstream routing without full regime inference.
        """
        mean_val = float(np.mean(percept))
        std_val = float(np.std(percept))

        if surprise > 0.7:
            return "transition"
        elif std_val > 1.5:
            return "high_volatility"
        elif mean_val > 0.5:
            return "trending_up"
        elif mean_val < -0.5:
            return "trending_down"
        elif std_val < 0.3:
            return "calm"
        else:
            return "sideways"

    # ── Distribution Shift Adaptation ──────────────────────────────────

    def adapt_to_distribution_shift(self, new_data: np.ndarray) -> dict[str, float]:
        """Detect and adapt to distribution shift without retraining.

        Uses KL-divergence approximation on percept statistics.
        If shift detected, resets surprise EMA to prevent over-correction.

        This is the key LNN advantage over HMMs:
          "LNNs maintain performance under moderate distribution shift
           without retraining" — Zhu et al. (Apr 2025)

        Args:
            new_data: Batch of new observations (n_samples × n_features)

        Returns:
            Dict with shift metrics: {"shift_detected": bool, "magnitude": float}
        """
        if len(self._recent_outputs) < self._config.adaptation_window:
            return {"shift_detected": False, "magnitude": 0.0}

        # Compute statistics on recent outputs
        recent = np.array(self._recent_outputs)
        recent_mean = np.mean(recent, axis=0)
        recent_std = np.std(recent, axis=0) + 1e-8

        # Process new data through the perceptor to get percept-space stats
        new_percepts = []
        for i in range(min(len(new_data), 50)):
            dp = DataPoint(
                modality=ModalityType.TIME_SERIES,
                vector=new_data[i] if new_data.ndim > 1 else new_data,
            )
            u = self._embed_input(dp)
            hidden, _ = self._liquid_forward(u)
            new_percepts.append(self._readout(hidden))

        if not new_percepts:
            return {"shift_detected": False, "magnitude": 0.0}

        new_arr = np.array(new_percepts)
        new_mean = np.mean(new_arr, axis=0)
        new_std = np.std(new_arr, axis=0) + 1e-8

        # Approximate KL divergence between two Gaussians
        var_ratio = (recent_std ** 2) / (new_std ** 2)
        mean_diff_sq = ((recent_mean - new_mean) ** 2) / (new_std ** 2)
        kl = 0.5 * float(np.mean(var_ratio + mean_diff_sq - 1.0 - np.log(var_ratio + 1e-8)))

        shift_detected = kl > self._config.adaptation_threshold
        if shift_detected:
            # Reset surprise tracking to adapt to new distribution
            self._recent_surprises.clear()
            self._logger.info("distribution_shift_detected",
                              kl_divergence=round(kl, 4),
                              threshold=self._config.adaptation_threshold)

        return {
            "shift_detected": shift_detected,
            "magnitude": round(kl, 4),
            "kl_divergence": round(kl, 4),
        }

    # ── Edge Compilation ──────────────────────────────────────────────

    def compile_to_edge(self) -> dict[str, Any]:
        """Prepare model for edge deployment.

        LFM2.5 achieves 82 tok/s on phone NPU with only 800MB memory.
        This method serializes weights for edge inference.

        Returns:
            Dict with serialized model weights and metadata.
        """
        return {
            "Wx": self._Wx.tolist(),
            "Wu": self._Wu.tolist(),
            "b": self._b.tolist(),
            "n_hidden": self._config.n_hidden,
            "max_input_dim": self._max_input_dim,
            "tau_current": self._state.tau,
            "ode_rtol": self._config.ode_rtol,
            "ode_atol": self._config.ode_atol,
            "format": "liquid_perceptor_v1",
            "timestamp": time.time(),
        }

    def load_from_edge(self, compiled: dict[str, Any]) -> None:
        """Load serialized weights from edge compilation.

        Args:
            compiled: Dict from compile_to_edge() output.
        """
        self._Wx = np.array(compiled["Wx"])
        self._Wu = np.array(compiled["Wu"])
        self._b = np.array(compiled["b"])
        self._state.tau = compiled.get("tau_current", self._config.tau_default)
        self._logger.info("edge_weights_loaded",
                          n_hidden=compiled["n_hidden"],
                          tau=self._state.tau)

    # ── Properties ────────────────────────────────────────────────────

    @property
    def state(self) -> LiquidState:
        """Current liquid ODE state (read-only view)."""
        return self._state

    @property
    def stats(self) -> dict[str, Any]:
        """Runtime statistics for monitoring and debugging."""
        return {
            "call_count": self._call_count,
            "total_ode_steps": self._total_steps,
            "avg_steps_per_call": (
                self._total_steps / max(self._call_count, 1)
            ),
            "current_tau": round(self._state.tau, 4),
            "current_surprise": round(self._state.surprise, 4),
            "current_confidence": round(self._state.confidence, 4),
            "n_hidden": self._config.n_hidden,
            "max_input_dim": self._max_input_dim,
            "adaptation_window_filled": len(self._recent_outputs),
        }

    def reset(self) -> None:
        """Reset the perceptor state for testing/debugging."""
        self._state = LiquidState(
            x=np.zeros(self._config.n_hidden),
            tau=self._config.tau_default,
            surprise=0.0,
            confidence=0.5,
        )
        self._recent_outputs.clear()
        self._recent_surprises.clear()
        self._call_count = 0
        self._total_steps = 0
        self._logger.debug("liquid_perceptor_reset")
