"""L2: Liquid Routing + Multi-Model Orchestration — 液态路由+多模型编排.

Biological Metaphor:
  Pituitary Gland → upgraded to "Liquid Pituitary" with dynamic time constants
  Basal Ganglia action selection — competitive pathways through inhibition/disinhibition

Key Innovation (v4.0):
  HyperNetwork generates dynamic weights + adaptive time constants.
  RouteMoA query-embedding routing eliminates pre-inference cost (89.8% reduction).
  AdaptOrch topology optimization for multi-model orchestration.

Sub-modules:
  - LiquidTimeConstantNet: Dynamic τ adaptation + 4-channel hyper-parameter output
  - MultiModelRouter: Query-embedding model routing + topology optimization

References (2025-2026):
  - RouteMoA (ACL 2026): Pre-inference query-embedding routing
  - AdaptOrch (Feb 2026): Topology optimization O(|V|+|E|)
  - Sakana AI (2026): RL Conductor, 93.3% AIME25
  - JiSi (ICML 2026): Intelligent model scheduling
"""

from __future__ import annotations

from src.l2.liquid_time_constant_net import (
    LiquidTimeConstantNet,
    HyperParameters,
    LiquidHyperState,
    TimeConstantConfig,
)
from src.l2.multi_model_router import (
    MultiModelRouter,
    ModelProfile,
    RoutingDecision,
    OrchestrationTopology,
    FusedAnswer,
    RouterConfig,
    TopologyType,
    ModelTier,
    create_default_model_pool,
)

__all__ = [
    # Liquid Time Constant Net
    "LiquidTimeConstantNet",
    "HyperParameters",
    "LiquidHyperState",
    "TimeConstantConfig",
    # Multi-Model Router
    "MultiModelRouter",
    "ModelProfile",
    "RoutingDecision",
    "OrchestrationTopology",
    "FusedAnswer",
    "RouterConfig",
    "TopologyType",
    "ModelTier",
    "create_default_model_pool",
]
