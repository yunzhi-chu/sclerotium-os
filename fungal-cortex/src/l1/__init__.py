"""L1: Liquid Perception Layer — 液态通用感知.

Biological Metaphor:
  神经元膜电位 — 连续时间积分，自适应放电阈值
  Retinal ganglion cells — 光强度→脉冲频率编码

Key Innovation (v4.0):
  LNN continuous-time perception replaces discrete HMM/CUSUM sensing.
  SNN spike encoding enables neuromorphic hardware acceleration.

Sub-modules:
  - LiquidPerceptor: ODE-driven continuous-time perception with adaptive τ
  - SNNSpikingEncoder: Rate/temporal/population spike encoding for neuromorphic chips

References (2025-2026):
  - Hasani et al. (2026), "Liquid Foundation Model 2.5", MIT/Liquid AI
  - Nature Comms (2026), "Multi-core SNN on-chip training", 1.05 TFLOPS/W @ 28nm
  - Zhu et al. (2025), "Adaptive BOCD for Financial Market Surveillance", 统计研究
"""

from __future__ import annotations

from src.l1.liquid_perceptor import (
    LiquidPerceptor,
    Percept,
    LiquidState,
    ModalityType,
    DataPoint,
    LiquidPerceptorConfig,
)
from src.l1.snn_spiking_encoder import (
    SNNSpikingEncoder,
    SpikeTrain,
    Spike,
    EncodingMethod,
    SpikeEncoderConfig,
)

__all__ = [
    # Liquid Perceptor
    "LiquidPerceptor",
    "Percept",
    "LiquidState",
    "ModalityType",
    "DataPoint",
    "LiquidPerceptorConfig",
    # SNN Encoder
    "SNNSpikingEncoder",
    "SpikeTrain",
    "Spike",
    "EncodingMethod",
    "SpikeEncoderConfig",
]
