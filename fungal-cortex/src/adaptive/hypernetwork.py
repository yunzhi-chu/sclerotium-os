"""L0/L2a: AdaptiveHyperNetwork — "垂体腺" (Pituitary Gland).

Biological Metaphor:
  垂体腺(Pituitary Gland)——豌豆大小的"主腺体", 接收下丘脑信号,
  分泌TSH/ACTH/FSH/LH/GH等激素, 调控下游所有内分泌器官

  HPA轴: 下丘脑(体制感知)→垂体(HyperNetwork)→肾上腺/甲状腺/性腺(策略/指标/安全门)
  一个信号引发三级激素释放，精确调控全身每个细胞的代谢状态

  输入: 6维体制分布(下丘脑信号)
  H-embedding任务关系编码(残差0.3) = 垂体"记住"上一次的激素水平,
    避免剧烈波动(内环境稳态)
  三路输出 = 垂体分泌三种"激素":
    1. strategy_head→8类策略Softmax权重 = TSH→甲状腺→代谢速率
    2. indicator_head→24维指标Sigmoid缩放 = ACTH→肾上腺→应激反应
    3. safety_head→5道安全门Softplus阈值 = ADH→肾脏→水分/压力调控

Reference:
  Chen & Ding (2026), GTH-Net;
  Schuler et al. (2026), "Energy Allocation System", IJMS 27(3):1345
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class HyperNetworkOutput:
    """Three-channel output of the HyperNetwork (the "pituitary hormones")."""

    strategy_weights: list[float]  # 8-dim strategy softmax weights (TSH-like)
    indicator_scales: list[float]  # 24-dim indicator sigmoid scales (ACTH-like)
    safety_thresholds: list[float]  # 5-dim safety softplus thresholds (ADH-like)
    h_embedding: list[float]  # 32-dim hidden state (for residual connection)
    timestamp: float = field(default_factory=time.time)


class AdaptiveHyperNetwork:
    """HyperNetwork that generates weights for downstream adapters.

    The "pituitary gland" of the adaptive engine — receives regime context
    from L1 sensing, outputs hormone-like weight signals that modulate
    strategy, indicator, and safety gate adapters.

    Architecture:
      - Input: 6-dim regime distribution (from RegimeOrchestrator)
      - H-embedding: 32-dim task-relation encoding with 0.3 residual
      - Three output heads:
        * strategy_head: 6×8 matrix → 8-dim Softmax weights
        * indicator_head: 6×24 matrix → 24-dim Sigmoid scales
        * safety_head: 6×5 matrix → 5-dim Softplus thresholds
    """

    INPUT_DIM = 6  # regime distribution dimensions
    H_DIM = 32  # hidden embedding dimension
    STRATEGY_DIM = 8  # number of strategy types
    INDICATOR_DIM = 24  # number of indicator parameters
    SAFETY_DIM = 5  # number of safety gates
    RESIDUAL_RATIO = 0.3  # H-embedding residual connection strength

    def __init__(self) -> None:
        self._logger = CortexLogger("hypernetwork")

        # Previous H-embedding (for residual connection — "hormone homeostasis")
        self._prev_h: list[float] = [0.0] * self.H_DIM

        # Regime → H-embedding weights (32→6 mapping, stored as 32×6)
        self._W_h: list[list[float]] = self._init_weights(self.H_DIM, self.INPUT_DIM)
        self._b_h: list[float] = [0.0] * self.H_DIM

        # Strategy head: H(32)→8 (8×32 weight matrix × 32-dim hidden = 8-dim output)
        self._W_strategy: list[list[float]] = self._init_weights(self.STRATEGY_DIM, self.H_DIM)
        self._b_strategy: list[float] = [0.0] * self.STRATEGY_DIM

        # Indicator head: H(32)→24 (24×32 weight matrix)
        self._W_indicator: list[list[float]] = self._init_weights(self.INDICATOR_DIM, self.H_DIM)
        self._b_indicator: list[float] = [0.0] * self.INDICATOR_DIM

        # Safety head: H(32)→5 (5×32 weight matrix)
        self._W_safety: list[list[float]] = self._init_weights(self.SAFETY_DIM, self.H_DIM)
        self._b_safety: list[float] = [0.0] * self.SAFETY_DIM

        # State
        self._last_output: HyperNetworkOutput | None = None
        self._call_count: int = 0

        # Phase 7.1a: TorchScript compilation (spinal reflex arc)
        self._compiled: bool = False
        self._torch_available: bool = self._check_torch()

    @staticmethod
    def _init_weights(rows: int, cols: int) -> list[list[float]]:
        """Xavier initialization."""
        scale = math.sqrt(2.0 / (rows + cols))
        return [[(2.0 * _pseudo_random(i * cols + j) - 1.0) * scale
                 for j in range(cols)] for i in range(rows)]

    # ── Forward Pass ──────────────────────────────────────────────────

    def forward(self, regime_distribution: list[float]) -> HyperNetworkOutput:
        """Generate 3-channel hormone output from regime context.

        Args:
            regime_distribution: 6-dim regime probability distribution
              [trending_up, trending_down, high_vol, low_vol, sideways, transition]

        Returns:
            HyperNetworkOutput with strategy weights, indicator scales, safety thresholds
        """
        self._call_count += 1

        # Ensure 6-dim input
        r = list(regime_distribution[:self.INPUT_DIM])
        while len(r) < self.INPUT_DIM:
            r.append(0.0)

        # 1. Compute H-embedding with residual connection (hormone homeostasis)
        h_new = [0.0] * self.H_DIM
        for i in range(self.H_DIM):
            s = self._b_h[i]
            for j in range(self.INPUT_DIM):
                s += self._W_h[i][j] * r[j]
            # Residual connection: keep 30% of previous state
            h_new[i] = s + self.RESIDUAL_RATIO * self._prev_h[i]

        # 2. Strategy head → 8-dim Softmax (TSH → thyroid)
        strategy_logits = [0.0] * self.STRATEGY_DIM
        for i in range(self.STRATEGY_DIM):
            s = self._b_strategy[i]
            for j in range(self.H_DIM):
                s += self._W_strategy[i][j] * h_new[j]
            strategy_logits[i] = s
        strategy_weights = self._softmax(strategy_logits)

        # 3. Indicator head → 24-dim Sigmoid (ACTH → adrenal)
        indicator_raw = [0.0] * self.INDICATOR_DIM
        for i in range(self.INDICATOR_DIM):
            s = self._b_indicator[i]
            for j in range(self.H_DIM):
                s += self._W_indicator[i][j] * h_new[j]
            indicator_raw[i] = s
        indicator_scales = [self._sigmoid(v) for v in indicator_raw]

        # 4. Safety head → 5-dim Softplus (ADH → kidney)
        safety_raw = [0.0] * self.SAFETY_DIM
        for i in range(self.SAFETY_DIM):
            s = self._b_safety[i]
            for j in range(self.H_DIM):
                s += self._W_safety[i][j] * h_new[j]
            safety_raw[i] = s
        safety_thresholds = [self._softplus(v) for v in safety_raw]

        # Update H-embedding memory
        self._prev_h = h_new

        output = HyperNetworkOutput(
            strategy_weights=[round(w, 4) for w in strategy_weights],
            indicator_scales=[round(s, 4) for s in indicator_scales],
            safety_thresholds=[round(t, 4) for t in safety_thresholds],
            h_embedding=[round(v, 4) for v in h_new],
        )
        self._last_output = output

        self._logger.debug("hypernetwork_forward",
                          dominant_strategy=max(range(self.STRATEGY_DIM), key=lambda i: strategy_weights[i]),
                          max_indicator_scale=round(max(indicator_scales), 3),
                          active_gates=sum(1 for t in safety_thresholds if t > 0.05))

        return output

    # ── Weight Update (for online adaptation) ─────────────────────────

    def update_weights(
        self,
        regime_distribution: list[float],
        target_strategy: list[float] | None = None,
        target_indicator: list[float] | None = None,
        target_safety: list[float] | None = None,
        learning_rate: float = 0.001,
    ) -> dict[str, float]:
        """Online weight update using gradient-like feedback.

        Like the pituitary adjusting hormone secretion based on feedback
        from downstream organs (negative feedback loop).

        Returns:
            Dict of {"strategy_loss": ..., "indicator_loss": ..., "safety_loss": ...}
        """
        output = self.forward(regime_distribution)
        losses: dict[str, float] = {}

        r = list(regime_distribution[:self.INPUT_DIM])
        while len(r) < self.INPUT_DIM:
            r.append(0.0)

        # Strategy gradient
        if target_strategy is not None:
            loss = sum((output.strategy_weights[i] - target_strategy[i]) ** 2
                      for i in range(min(len(target_strategy), self.STRATEGY_DIM)))
            losses["strategy_loss"] = round(loss, 6)
            # Update strategy head weights (simplified SGD)
            for i in range(self.STRATEGY_DIM):
                err = output.strategy_weights[i] - target_strategy[i]
                for j in range(self.H_DIM):
                    self._W_strategy[i][j] -= learning_rate * err * self._prev_h[j]

        # Indicator gradient
        if target_indicator is not None:
            loss = sum((output.indicator_scales[i] - target_indicator[i]) ** 2
                      for i in range(min(len(target_indicator), self.INDICATOR_DIM)))
            losses["indicator_loss"] = round(loss, 6)
            for i in range(self.INDICATOR_DIM):
                err = output.indicator_scales[i] - target_indicator[i]
                for j in range(self.H_DIM):
                    self._W_indicator[i][j] -= learning_rate * err * self._prev_h[j]

        # Safety gradient
        if target_safety is not None:
            loss = sum((output.safety_thresholds[i] - target_safety[i]) ** 2
                      for i in range(min(len(target_safety), self.SAFETY_DIM)))
            losses["safety_loss"] = round(loss, 6)
            for i in range(self.SAFETY_DIM):
                err = output.safety_thresholds[i] - target_safety[i]
                for j in range(self.H_DIM):
                    self._W_safety[i][j] -= learning_rate * err * self._prev_h[j]

        self._logger.debug("hypernetwork_updated", **losses)
        return losses

    # ── Activation Functions ──────────────────────────────────────────

    @staticmethod
    def _softmax(logits: list[float]) -> list[float]:
        max_val = max(logits)
        exps = [math.exp(v - max_val) for v in logits]
        total = sum(exps)
        return [e / max(total, 1e-10) for e in exps]

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    @staticmethod
    def _softplus(x: float) -> float:
        """Softplus: smooth approximation of ReLU, always positive."""
        if x > 20:
            return x
        return math.log(1.0 + math.exp(x))

    # ── Phase 7.1a: TorchScript Compilation (Spinal Reflex Arc) ─────

    @staticmethod
    def _check_torch() -> bool:
        """Check if PyTorch is available for TorchScript compilation."""
        try:
            import torch  # noqa: F401
            return True
        except ImportError:
            return False

    def compile(self) -> bool:
        """TorchScript JIT compilation — <5ms spinal reflex arc.

        Like the spinal cord bypassing the brain for faster reflexes,
        TorchScript compiles the forward pass to optimized C++.

        Returns True if compilation succeeded, False if torch is unavailable.
        """
        if not self._torch_available:
            self._logger.info("torchscript_unavailable", reason="PyTorch not installed")
            return False

        try:
            import torch

            # Convert weights to torch tensors
            self._W_h_t = torch.tensor(self._W_h, dtype=torch.float32)
            self._b_h_t = torch.tensor(self._b_h, dtype=torch.float32)
            self._W_strategy_t = torch.tensor(self._W_strategy, dtype=torch.float32)
            self._b_strategy_t = torch.tensor(self._b_strategy, dtype=torch.float32)
            self._W_indicator_t = torch.tensor(self._W_indicator, dtype=torch.float32)
            self._b_indicator_t = torch.tensor(self._b_indicator, dtype=torch.float32)
            self._W_safety_t = torch.tensor(self._W_safety, dtype=torch.float32)
            self._b_safety_t = torch.tensor(self._b_safety, dtype=torch.float32)
            self._prev_h_t = torch.tensor(self._prev_h, dtype=torch.float32)
            self._residual_t = torch.tensor(self.RESIDUAL_RATIO, dtype=torch.float32)

            # Define TorchScript forward method
            def _compiled_forward(regime_tensor: torch.Tensor) -> tuple:
                h_new = torch.matmul(self._W_h_t, regime_tensor) + self._b_h_t
                h_new = h_new + self._residual_t * self._prev_h_t

                strategy_logits = torch.matmul(self._W_strategy_t, h_new) + self._b_strategy_t
                strategy_weights = torch.softmax(strategy_logits, dim=0)

                indicator_raw = torch.matmul(self._W_indicator_t, h_new) + self._b_indicator_t
                indicator_scales = torch.sigmoid(indicator_raw)

                safety_raw = torch.matmul(self._W_safety_t, h_new) + self._b_safety_t
                safety_thresholds = torch.nn.functional.softplus(safety_raw)

                return h_new, strategy_weights, indicator_scales, safety_thresholds

            self._compiled_forward = _compiled_forward
            self._compiled = True
            self._logger.info("torchscript_compiled", method="JIT trace")
            return True
        except Exception as exc:
            self._logger.warn("torchscript_compilation_failed", error=str(exc))
            return False

    def forward_compiled(self, regime_distribution: list[float]) -> HyperNetworkOutput:
        """Execute forward pass using TorchScript-compiled path.

        Falls back to pure Python if not compiled. Like choosing the
        spinal reflex arc (fast) over the cortical path (flexible).
        """
        if not self._compiled or not self._torch_available:
            return self.forward(regime_distribution)

        import torch

        self._call_count += 1
        r = list(regime_distribution[:self.INPUT_DIM])
        while len(r) < self.INPUT_DIM:
            r.append(0.0)

        regime_t = torch.tensor(r, dtype=torch.float32)
        with torch.no_grad():
            h_new, strategy_w, indicator_s, safety_t = self._compiled_forward(regime_t)

        self._prev_h = h_new.tolist()
        output = HyperNetworkOutput(
            strategy_weights=[round(float(v), 4) for v in strategy_w.tolist()],
            indicator_scales=[round(float(v), 4) for v in indicator_s.tolist()],
            safety_thresholds=[round(float(v), 4) for v in safety_t.tolist()],
            h_embedding=[round(float(v), 4) for v in self._prev_h],
        )
        self._last_output = output
        return output

    @property
    def stats(self) -> dict[str, Any]:
        last = self._last_output
        return {
            "call_count": self._call_count,
            "input_dim": self.INPUT_DIM,
            "hidden_dim": self.H_DIM,
            "strategy_dim": self.STRATEGY_DIM,
            "indicator_dim": self.INDICATOR_DIM,
            "safety_dim": self.SAFETY_DIM,
            "residual_ratio": self.RESIDUAL_RATIO,
            "last_output": {
                "strategy": last.strategy_weights if last else None,
                "indicator": last.indicator_scales[:8] if last else None,  # first 8
                "safety": last.safety_thresholds if last else None,
            } if last else None,
        }


def _pseudo_random(seed: int) -> float:
    x = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    return (x % 1000000) / 1000000.0
