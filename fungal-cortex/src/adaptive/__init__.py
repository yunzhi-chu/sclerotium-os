"""L0 Adaptive Engine + L3 Immune Debate Engine — 周围神经+内分泌+免疫系统.

Biological Metaphor:
  - Peripheral Nervous System: Sensory neurons → spinal cord → brain sensory pathway
  - Endocrine System: HPA axis (Hypothalamus-Pituitary-Adrenal) cascading hormone regulation
  - Adaptive Immune System: Antigen presentation → T cell activation → clonal selection → immune memory
  - Synaptic Plasticity: LTP (long-term potentiation) = strategy reinforcement, LTD = weakening
  - Homeostatic Plasticity: Synaptic scaling = global parameter auto-calibration

一句话: L0感知市场状态+L3验证交易信号 = 系统的"感官+激素+免疫"

Sub-layers:
  L1: Three-channel Market Sensing (HMM + CUSUM + GTH-Net + BOCD + BMA orchestrator)
  L2: HyperNetwork Dynamic Generation (HyperNetwork + Strategy + Indicator + Safety adapters)
  L3a: Adaptive Meta-Learning (TemporalSampler + MetaLearner + SelfEvolution)
  L3b: Immune Debate Engine (MarketOfClaims + AISImmuneValidator + DebateConsensusEngine)
  L6: Circuit Breaker + Memory Bridge (HPA negative feedback + immune memory)

References (2025-2026):
  - Zhu et al. (2025), "Adaptive BOCD for Financial Market Surveillance", 统计研究
  - Tsaknaki et al. (2025), "Score-Driven BOCPD for Order Flow", Quantitative Finance
  - Chen & Ding (2026), "GTH-Net", Applied Sciences 16(7):3294
  - Daviu et al. (2026), "Homeostatic scaling ensures behavioural stability", Mol Psychiatry
  - Zinjad et al. (2026), "FOMAML+Reptile ensemble for adaptive k-shot", IJISA 18(2):27-43
  - Schuler et al. (2026), "Energy Allocation System", IJMS 27(3):1345
  - Maury (2025), "Amyloid world hypothesis", FEBS Letters 599:2693-2705
  - Singh & Arora (2025), "HAIS-IDS", 波兰科学院技术科学通报
  - MoCA-Agent (arXiv 2606.11537, 2026) — Market of Claims
  - Grimm (AAAI 2025) — AIS for defense
  - Inverse-Wisdom Law (arXiv 2604.27274, 2026)
"""

from __future__ import annotations

# ── L1: Three-channel Market Sensing ──────────────────────────────────
from src.adaptive.hmm_detector import HMMRegimeDetector
from src.adaptive.cusum_detector import CUSUMRegimeDetector
from src.adaptive.gthnet_detector import GTHNetRegimeDetector
from src.adaptive.drift_detector import AdaptiveDriftDetector
from src.adaptive.regime_orchestrator import BayesianRegimeOrchestrator

# ── L2: HyperNetwork Dynamic Generation ──────────────────────────────
from src.adaptive.hypernetwork import AdaptiveHyperNetwork
from src.adaptive.strategy_adapter import StrategyAdapter
from src.adaptive.indicator_adapter import IndicatorAdapter
from src.adaptive.safety_gate import SafetyGateAdapter

# ── L3: Adaptive Meta-Learning ───────────────────────────────────────
from src.adaptive.temporal_sampler import MultiDistributionTemporalSampler
from src.adaptive.meta_learner import AdaptiveMetaLearner
from src.adaptive.self_evolution import SelfEvolutionLoop

# ── L3b: Immune Debate Engine ───────────────────────────────────────
from src.adaptive.market_of_claims import MarketOfClaims
from src.adaptive.immune_validator import AISImmuneValidator
from src.adaptive.debate_consensus import DebateConsensusEngine

# ── L6: Circuit Breaker + Memory Bridge ──────────────────────────────
from src.adaptive.circuit_breaker import CircuitBreaker, CircuitState
from src.adaptive.memory_bridge import MemoryFeedbackBridge

# ── Phase 5: Cross-Layer Bridge ──────────────────────────────────────
from src.adaptive.debate_adaptive_bridge import (
    AdaptiveDebateBridge,
    DebateParams,
    ImmuneState,
    RegimeImmuneMapping,
)

__all__ = [
    # L1: Sensing
    "HMMRegimeDetector",
    "CUSUMRegimeDetector",
    "GTHNetRegimeDetector",
    "AdaptiveDriftDetector",
    "BayesianRegimeOrchestrator",
    # L2: HyperNetwork
    "AdaptiveHyperNetwork",
    "StrategyAdapter",
    "IndicatorAdapter",
    "SafetyGateAdapter",
    # L3a: Meta-Learning
    "MultiDistributionTemporalSampler",
    "AdaptiveMetaLearner",
    "SelfEvolutionLoop",
    # L3b: Immune Debate Engine
    "MarketOfClaims",
    "AISImmuneValidator",
    "DebateConsensusEngine",
    # L6: Protection
    "CircuitBreaker",
    "CircuitState",
    "MemoryFeedbackBridge",
    # Phase 5: Cross-Layer Bridges
    "AdaptiveDebateBridge",
    "DebateParams",
    "ImmuneState",
    "RegimeImmuneMapping",
]
