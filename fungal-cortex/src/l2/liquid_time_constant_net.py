"""L2a: LiquidTimeConstantNet — "液态垂体" (Liquid Pituitary).

Biological Metaphor:
  垂体腺(Pituitary Gland) → 升级为"液态垂体"
  原HyperNetwork: 6→32→{8,24,5} 三路静态输出 (TSH/ACTH/ADH)
  升级: 64→64→{τ, W_strategy, W_indicator, W_safety} 四路动态输出

  关键升级:
  1. 输入从6维市场体制→64维通用状态嵌入(液态感知器输出)
  2. 隐藏层维持32维但增加液态残差连接(自适应比例)
  3. 新增τ输出通道: 控制L1感知器的时间常数
     τ ∈ (0,1] where τ→0 = 快速衰减(直觉), τ→1 = 慢速衰减(深思)
  4. 策略/指标/安全头维度扩展以支持通用域

  动态 τ 适应:
    τ_new = τ_old × (1 + α·surprise - β·confidence)
    高意外 + 低置信 → τ↑ (慢处理，深思熟虑)
    低意外 + 高置信 → τ↓ (快处理，直觉反应)

  HyperNetwork输出的物理意义:
    τ → 控制L1 LiquidPerceptor的积分速度 (时间常数)
    strategy_weights → 下游策略选择概率分布 (Softmax)
    indicator_scales → 指标参数缩放因子 (Sigmoid)
    safety_thresholds → 安全门槛高度 (Softplus)

Reference:
  Hasani et al. (2026), "LFM 2.5", MIT/Liquid AI
  Chen & Ding (2026), "GTH-Net", Applied Sciences 16(7):3294
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class LiquidHyperState:
    """The internal state of the Liquid Time Constant network.

    Maintains hidden embedding with liquid residual connection.
    """

    h_embedding: np.ndarray        # Current hidden state (H_DIM,)
    tau_output: float              # Last τ output
    tau_history: list[float]       # Recent τ values (for stability analysis)
    last_update: float = field(default_factory=time.time)


@dataclass
class HyperParameters:
    """Four-channel output of the Liquid Time Constant Network.

    These are the "liquid hormones" that modulate downstream processing.
    """

    tau: float                        # Time constant for L1 LiquidPerceptor (0, 1]
    strategy_weights: np.ndarray      # Strategy selection weights (n_strategies,)
    indicator_scales: np.ndarray      # Indicator parameter scales (n_indicators,)
    safety_thresholds: np.ndarray     # Safety gate thresholds (n_safety_gates,)
    h_embedding: np.ndarray           # Hidden state for residual connection
    timestamp: float = field(default_factory=time.time)

    def as_dict(self) -> dict[str, Any]:
        return {
            "tau": round(self.tau, 4),
            "strategy_weights": [round(float(w), 4) for w in self.strategy_weights],
            "indicator_scales": [round(float(s), 4) for s in self.indicator_scales[:8]],
            "safety_thresholds": [round(float(t), 4) for t in self.safety_thresholds],
            "timestamp": self.timestamp,
        }


@dataclass
class TimeConstantConfig:
    """Configuration for the Liquid Time Constant Network."""

    input_dim: int = 64             # Input dimension (from LiquidPerceptor)
    hidden_dim: int = 64            # Hidden embedding dimension (upgraded from 32)
    n_strategies: int = 12          # Number of strategy types (upgraded from 8)
    n_indicators: int = 32          # Number of indicator params (upgraded from 24)
    n_safety_gates: int = 8         # Number of safety gates (upgraded from 5)

    # Residual connection
    residual_ratio: float = 0.3     # Base residual strength
    residual_adaptive: bool = True  # Enable adaptive residual ratio

    # τ adaptation
    tau_default: float = 0.5        # Default time constant
    tau_min: float = 0.05           # Fastest response
    tau_max: float = 1.0            # Deepest processing
    alpha_surprise: float = 0.3     # Surprise sensitivity
    beta_confidence: float = 0.15   # Confidence sensitivity

    # Stability
    tau_ema_alpha: float = 0.1      # EMA smoothing for τ (prevents oscillation)

    # TorchScript compilation
    jit_enabled: bool = True


# ═══════════════════════════════════════════════════════════════════════
# Core Implementation
# ═══════════════════════════════════════════════════════════════════════


class LiquidTimeConstantNet:
    """Liquid Time Constant HyperNetwork — generates dynamic processing parameters.

    The "liquid pituitary" of the AGI system. Upgrades the v3.0 AdaptiveHyperNetwork
    from static 3-channel output to dynamic 4-channel output with adaptive τ.

    Architecture:
      Input (64-dim percept) → H-embedding (64-dim with liquid residual)
        → τ channel: scalar time constant
        → Strategy channel: n_strategies-dim Softmax
        → Indicator channel: n_indicators-dim Sigmoid
        → Safety channel: n_safety_gates-dim Softplus

    Key innovation over v3.0:
      - Adaptive residual ratio: residual_weight adapts based on regime stability
      - τ feedback loop: τ controls L1 integration speed, L1 surprise controls τ
      - 4-channel output: adds explicit time constant as first-class output

    Usage::

        ltn = LiquidTimeConstantNet()
        percept_vec = np.array([...])  # 64-dim from LiquidPerceptor
        params = ltn.forward(percept_vec, surprise=0.3, confidence=0.8)
        # params.tau → feeds back to L1 LiquidPerceptor.tau
        # params.strategy_weights → feeds to strategy selection
    """

    def __init__(self, config: TimeConstantConfig | None = None) -> None:
        self._config = config or TimeConstantConfig()
        self._logger = CortexLogger("liquid_time_constant_net")
        c = self._config
        rng = np.random.RandomState(42)

        # --- Hidden embedding weights: input(64) → hidden(64) ---
        self._W_h: np.ndarray = rng.randn(c.hidden_dim, c.input_dim) * math.sqrt(
            2.0 / (c.hidden_dim + c.input_dim)
        )
        self._b_h: np.ndarray = np.zeros(c.hidden_dim)

        # --- τ channel: hidden(64) → 1 (scalar) ---
        self._W_tau: np.ndarray = rng.randn(1, c.hidden_dim) * 0.01
        self._b_tau: float = 0.0

        # --- Strategy channel: hidden(64) → n_strategies(12) ---
        self._W_strategy: np.ndarray = rng.randn(
            c.n_strategies, c.hidden_dim
        ) * math.sqrt(2.0 / (c.n_strategies + c.hidden_dim))
        self._b_strategy: np.ndarray = np.zeros(c.n_strategies)

        # --- Indicator channel: hidden(64) → n_indicators(32) ---
        self._W_indicator: np.ndarray = rng.randn(
            c.n_indicators, c.hidden_dim
        ) * math.sqrt(2.0 / (c.n_indicators + c.hidden_dim))
        self._b_indicator: np.ndarray = np.zeros(c.n_indicators)

        # --- Safety channel: hidden(64) → n_safety_gates(8) ---
        self._W_safety: np.ndarray = rng.randn(
            c.n_safety_gates, c.hidden_dim
        ) * math.sqrt(2.0 / (c.n_safety_gates + c.hidden_dim))
        self._b_safety: np.ndarray = np.zeros(c.n_safety_gates)

        # --- State ---
        self._state = LiquidHyperState(
            h_embedding=np.zeros(c.hidden_dim),
            tau_output=c.tau_default,
            tau_history=[],
        )
        self._last_output: HyperParameters | None = None
        self._call_count: int = 0

        # --- TorchScript compilation ---
        self._compiled: bool = False
        self._torch_available: bool = self._check_torch()

        self._logger.info("liquid_time_constant_net_initialized",
                          input_dim=c.input_dim,
                          hidden_dim=c.hidden_dim,
                          n_strategies=c.n_strategies,
                          n_indicators=c.n_indicators,
                          n_safety_gates=c.n_safety_gates,
                          tau_default=c.tau_default)

    # ── Forward Pass ──────────────────────────────────────────────────

    def forward(
        self,
        percept_vector: np.ndarray,
        surprise: float = 0.0,
        confidence: float = 0.5,
    ) -> HyperParameters:
        """Generate 4-channel hyper-parameters from percept embedding.

        Args:
            percept_vector: 64-dim embedding from L1 LiquidPerceptor
            surprise: Current surprise level (from LiquidPerceptor)
            confidence: Current confidence level (from LiquidPerceptor)

        Returns:
            HyperParameters with τ, strategy weights, indicator scales, safety thresholds
        """
        self._call_count += 1
        c = self._config

        # Ensure input dimensionality
        x = self._preprocess_input(percept_vector)
        x = x.astype(np.float64)

        # 1. Compute H-embedding with adaptive liquid residual
        h_raw = self._W_h @ x + self._b_h

        # Adaptive residual ratio: more residual when confident (stable regime)
        if c.residual_adaptive:
            residual_weight = c.residual_ratio * (0.5 + 0.5 * confidence)
        else:
            residual_weight = c.residual_ratio

        h_new = h_raw + residual_weight * self._state.h_embedding

        # 2. τ channel: hidden → scalar (Sigmoid → [0,1])
        tau_raw = float((self._W_tau @ h_new)[0] + self._b_tau)
        tau_base = self._sigmoid(tau_raw)  # [0, 1]

        # Adapt τ based on surprise/confidence
        tau = self._adapt_tau(tau_base, surprise, confidence)

        # 3. Strategy channel: hidden → Softmax weights
        strategy_logits = self._W_strategy @ h_new + self._b_strategy
        strategy_weights = self._softmax(strategy_logits)

        # 4. Indicator channel: hidden → Sigmoid scales
        indicator_raw = self._W_indicator @ h_new + self._b_indicator
        indicator_scales = self._sigmoid_vec(indicator_raw)

        # 5. Safety channel: hidden → Softplus thresholds (always positive)
        safety_raw = self._W_safety @ h_new + self._b_safety
        safety_thresholds = self._softplus_vec(safety_raw)

        # 6. Update state
        self._state.h_embedding = h_new
        self._state.tau_output = tau
        self._state.tau_history.append(tau)
        if len(self._state.tau_history) > 100:
            self._state.tau_history = self._state.tau_history[-50:]
        self._state.last_update = time.time()

        output = HyperParameters(
            tau=round(tau, 4),
            strategy_weights=strategy_weights,
            indicator_scales=indicator_scales,
            safety_thresholds=safety_thresholds,
            h_embedding=h_new,
        )
        self._last_output = output

        self._logger.debug("ltn_forward",
                           tau=round(tau, 3),
                           dominant_strategy=int(np.argmax(strategy_weights)),
                           active_gates=int(np.sum(safety_thresholds > 0.1)),
                           residual_weight=round(residual_weight, 3))

        return output

    def forward_with_embedding(
        self, percept_vector: np.ndarray, surprise: float = 0.0, confidence: float = 0.5,
    ) -> tuple[HyperParameters, np.ndarray]:
        """Forward pass that also returns the raw H-embedding.

        Useful when downstream modules need the embedding for additional computation.
        """
        params = self.forward(percept_vector, surprise, confidence)
        return params, self._state.h_embedding.copy()

    # ── Adaptive τ ────────────────────────────────────────────────────

    def _adapt_tau(self, tau_base: float, surprise: float, confidence: float) -> float:
        """Adapt the time constant based on cognitive state.

        This is the KEY innovation: τ is not just a hyperparameter — it's
        a dynamic state variable that controls how much "thinking time"
        each input gets.

        Formula:
          τ_new = τ_base × (1 + α·surprise - β·confidence)

        The EMA-smoothing prevents τ oscillation:
          τ_final = (1 - γ)·τ_old + γ·τ_new
        """
        c = self._config
        alpha = c.alpha_surprise
        beta = c.beta_confidence

        adjustment = 1.0 + alpha * surprise - beta * confidence
        tau_new = tau_base * adjustment

        # Clamp to valid range
        tau_new = max(c.tau_min, min(c.tau_max, tau_new))

        # EMA smoothing to prevent oscillation
        tau_old = self._state.tau_output
        tau_smooth = (1.0 - c.tau_ema_alpha) * tau_old + c.tau_ema_alpha * tau_new

        return tau_smooth

    # ── Weight Update (Online Adaptation) ──────────────────────────────

    def update_weights(
        self,
        percept_vector: np.ndarray,
        surprise: float = 0.0,
        confidence: float = 0.5,
        target_strategy: np.ndarray | None = None,
        target_indicator: np.ndarray | None = None,
        target_safety: np.ndarray | None = None,
        target_tau: float | None = None,
        learning_rate: float = 0.001,
    ) -> dict[str, float]:
        """Online weight update via gradient feedback.

        Like the pituitary adjusting hormone secretion based on negative
        feedback from downstream organs.

        Returns:
            Dict of per-channel losses.
        """
        output = self.forward(percept_vector, surprise, confidence)
        losses: dict[str, float] = {}
        h = self._state.h_embedding

        if target_tau is not None:
            err = output.tau - target_tau
            losses["tau_loss"] = round(err ** 2, 6)
            for j in range(self._config.hidden_dim):
                self._W_tau[0, j] -= learning_rate * err * h[j]

        if target_strategy is not None:
            loss = float(np.mean((output.strategy_weights - target_strategy) ** 2))
            losses["strategy_loss"] = round(loss, 6)
            for i in range(self._config.n_strategies):
                err = output.strategy_weights[i] - target_strategy[i]
                self._W_strategy[i] -= learning_rate * err * h
                self._b_strategy[i] -= learning_rate * err

        if target_indicator is not None:
            loss = float(np.mean((output.indicator_scales - target_indicator) ** 2))
            losses["indicator_loss"] = round(loss, 6)
            for i in range(self._config.n_indicators):
                err = output.indicator_scales[i] - target_indicator[i]
                self._W_indicator[i] -= learning_rate * err * h
                self._b_indicator[i] -= learning_rate * err

        if target_safety is not None:
            loss = float(np.mean((output.safety_thresholds - target_safety) ** 2))
            losses["safety_loss"] = round(loss, 6)
            for i in range(self._config.n_safety_gates):
                err = output.safety_thresholds[i] - target_safety[i]
                self._W_safety[i] -= learning_rate * err * h
                self._b_safety[i] -= learning_rate * err

        if losses:
            self._logger.debug("ltn_weights_updated", **losses)

        return losses

    # ── TorchScript JIT Compilation ────────────────────────────────────

    @staticmethod
    def _check_torch() -> bool:
        try:
            import torch  # noqa: F401
            return True
        except ImportError:
            return False

    def compile_jit(self) -> bool:
        """JIT compile the forward pass for <5ms inference.

        Like the spinal reflex arc bypassing the brain for faster reflexes.
        """
        if not self._torch_available:
            self._logger.info("torch_unavailable")
            return False

        try:
            import torch

            # Convert weights to tensors
            self._W_h_t = torch.tensor(self._W_h, dtype=torch.float32)
            self._b_h_t = torch.tensor(self._b_h, dtype=torch.float32)
            self._W_tau_t = torch.tensor(self._W_tau, dtype=torch.float32)
            self._b_tau_t = torch.tensor(self._b_tau, dtype=torch.float32)
            self._W_strategy_t = torch.tensor(self._W_strategy, dtype=torch.float32)
            self._b_strategy_t = torch.tensor(self._b_strategy, dtype=torch.float32)
            self._W_indicator_t = torch.tensor(self._W_indicator, dtype=torch.float32)
            self._b_indicator_t = torch.tensor(self._b_indicator, dtype=torch.float32)
            self._W_safety_t = torch.tensor(self._W_safety, dtype=torch.float32)
            self._b_safety_t = torch.tensor(self._b_safety, dtype=torch.float32)

            self._compiled = True
            self._logger.info("jit_compiled")
            return True
        except Exception as exc:
            self._logger.warn("jit_compilation_failed", error=str(exc))
            return False

    def forward_compiled(
        self, percept_vector: np.ndarray, surprise: float = 0.0, confidence: float = 0.5,
    ) -> HyperParameters:
        """Execute forward pass via JIT-compiled path.

        Falls back to pure NumPy if compilation failed.
        """
        if not self._compiled or not self._torch_available:
            return self.forward(percept_vector, surprise, confidence)

        import torch

        self._call_count += 1
        c = self._config

        x = torch.tensor(self._preprocess_input(percept_vector), dtype=torch.float32)
        h_prev = torch.tensor(self._state.h_embedding, dtype=torch.float32)
        residual = c.residual_ratio * (0.5 + 0.5 * confidence) if c.residual_adaptive else c.residual_ratio

        with torch.no_grad():
            h_new = torch.matmul(self._W_h_t, x) + self._b_h_t + residual * h_prev

            tau_raw = float(torch.sigmoid(torch.matmul(self._W_tau_t, h_new) + self._b_tau_t))
            tau = self._adapt_tau(tau_raw, surprise, confidence)

            strategy_w = torch.softmax(
                torch.matmul(self._W_strategy_t, h_new) + self._b_strategy_t, dim=0
            )
            indicator_s = torch.sigmoid(
                torch.matmul(self._W_indicator_t, h_new) + self._b_indicator_t
            )
            safety_t = torch.nn.functional.softplus(
                torch.matmul(self._W_safety_t, h_new) + self._b_safety_t
            )

        self._state.h_embedding = h_new.numpy()
        self._state.tau_output = tau
        self._state.last_update = time.time()

        output = HyperParameters(
            tau=round(tau, 4),
            strategy_weights=strategy_w.numpy(),
            indicator_scales=indicator_s.numpy(),
            safety_thresholds=safety_t.numpy(),
            h_embedding=self._state.h_embedding.copy(),
        )
        self._last_output = output
        return output

    # ── Helpers ───────────────────────────────────────────────────────

    def _preprocess_input(self, percept_vector: np.ndarray) -> np.ndarray:
        """Ensure input matches expected dimensionality."""
        c = self._config
        vec = percept_vector.astype(np.float64).flatten()

        if len(vec) > c.input_dim:
            vec = vec[:c.input_dim]
        elif len(vec) < c.input_dim:
            padded = np.zeros(c.input_dim)
            padded[:len(vec)] = vec
            vec = padded

        return vec

    @staticmethod
    def _sigmoid(x: float) -> float:
        if x > 20:
            return 1.0
        if x < -20:
            return 0.0
        return 1.0 / (1.0 + math.exp(-x))

    @staticmethod
    def _sigmoid_vec(x: np.ndarray) -> np.ndarray:
        result = np.zeros_like(x)
        for i in range(len(x)):
            val = x[i]
            if val > 20:
                result[i] = 1.0
            elif val < -20:
                result[i] = 0.0
            else:
                result[i] = 1.0 / (1.0 + math.exp(-val))
        return result

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        max_val = np.max(logits)
        exps = np.exp(logits - max_val)
        total = np.sum(exps)
        return exps / max(total, 1e-10)

    @staticmethod
    def _softplus_vec(x: np.ndarray) -> np.ndarray:
        result = np.zeros_like(x)
        for i in range(len(x)):
            val = x[i]
            if val > 20:
                result[i] = val
            else:
                result[i] = math.log(1.0 + math.exp(val))
        return result

    # ── Properties ────────────────────────────────────────────────────

    @property
    def state(self) -> LiquidHyperState:
        return self._state

    @property
    def stats(self) -> dict[str, Any]:
        last = self._last_output
        c = self._config
        return {
            "call_count": self._call_count,
            "input_dim": c.input_dim,
            "hidden_dim": c.hidden_dim,
            "n_strategies": c.n_strategies,
            "n_indicators": c.n_indicators,
            "n_safety_gates": c.n_safety_gates,
            "current_tau": round(self._state.tau_output, 4),
            "tau_history_mean": round(
                float(np.mean(self._state.tau_history)), 4
            ) if self._state.tau_history else None,
            "last_output": last.as_dict() if last else None,
            "compiled": self._compiled,
        }

    def reset(self) -> None:
        """Reset network state for testing."""
        c = self._config
        self._state = LiquidHyperState(
            h_embedding=np.zeros(c.hidden_dim),
            tau_output=c.tau_default,
            tau_history=[],
        )
        self._last_output = None
        self._call_count = 0
        self._logger.debug("ltn_reset")
