"""L4: RL Conductor + Causal Debug Engine — RL编排+因果调试 (Phase 3 v4.0).

Biological Metaphor:
  Cerebellum — coordinates hundreds of muscles, each with precise sequence,
  timing, and force. Cerebellar neurons outnumber cortical neurons, yet each
  is simple. Similarly, a small 7B RL-trained model can orchestrate GPT-5+
  Claude+Gemini, discovering strategies no human engineer would conceive.

  Prefrontal Cortex — counterfactual thinking: "What if I had done X instead
  of Y?" Causal-Agent-Replay builds Structural Causal Models of agent
  trajectories, using Pearl's do-calculus to precisely attribute failure
  to specific steps, not just correlations.

Key Innovation (v4.0):
  RLConductor (Sakana Fugu pattern): 7B model RL-trained → orchestrates
  frontier models, discovers novel orchestration strategies, cross-domain
  transfer. 93.3% AIME25, 87.5% GPQA-Diamond.
  CausalDebugEngine (CAR): SCM + do-calculus → exact step-level failure
  attribution, Shapley value decomposition, automatic fix suggestions.
  AdaptOrchTopologyRouter: O(|V|+|E|) DAG→topology optimization, runtime
  adaptation based on worker performance.

Sub-modules:
  - RLConductorOrchestrator: RL-trained multi-model orchestration
  - CausalDebugEngine: CAR causal attribution + automatic fix suggestions
  - AdaptOrchTopologyRouter: DAG topology optimization + runtime adaptation

References (2025-2026):
  - Sakana AI (2026): RL Conductor, 93.3% AIME25
  - Causal-Agent-Replay (GitHub 2025): SCM + do-calculus for agent debugging
  - AdaptOrch (Feb 2026): Topology optimization O(|V|+|E|)
"""

from __future__ import annotations

from src.l4.rl_conductor_orchestrator import (
    RLConductorOrchestrator,
    OrchestrationAction,
    ExecutionPlan,
    OrchestrationStrategy,
    RLOrchestratorConfig,
)
from src.l4.causal_debug_engine import (
    CausalDebugEngine,
    StructuralCausalModel,
    AgentTrajectory,
    CausalAttribution,
    DebugConfig,
    InterventionType,
)
from src.l4.adapt_orch_topology_router import (
    AdaptOrchTopologyRouter,
    TaskDAG,
    DAGNode,
    OrchestrationTopology,
    TopologyType,
    TopologyConstraint,
    TopologyRouterConfig,
)

__all__ = [
    # RL Conductor Orchestrator
    "RLConductorOrchestrator",
    "OrchestrationAction",
    "ExecutionPlan",
    "OrchestrationStrategy",
    "RLOrchestratorConfig",
    # Causal Debug Engine
    "CausalDebugEngine",
    "StructuralCausalModel",
    "AgentTrajectory",
    "CausalAttribution",
    "DebugConfig",
    "InterventionType",
    # AdaptOrch Topology Router
    "AdaptOrchTopologyRouter",
    "TaskDAG",
    "DAGNode",
    "OrchestrationTopology",
    "TopologyType",
    "TopologyConstraint",
    "TopologyRouterConfig",
]
