"""Phase 3 Causal Orchestration Bridge — L4 RL Conductor + Causal Debug.

This bridge is the "cerebellar-prefrontal axis" connecting v4.0 L4 causal
debugging and RL orchestration to the existing pipeline:
  - RLConductorOrchestrator → optimizes multi-model execution plans
  - CausalDebugEngine → attributes failures to specific steps
  - AdaptOrchTopologyRouter → selects optimal execution topology

Architecture:
  Task → L4 RL Conductor (plan) → L4 Topology Router (topology)
       → L2 MultiModelRouter (execution) → L4 Causal Debug (attribution)
       → Feedback loop: attribution → conductor retraining

The bridge runs alongside the existing v3.0 autonomous orchestration
(TaskDAGBuilder, CounterfactualEngine, AuditTrail) without replacing them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from src.config import L4Config, get_config
from src.l4.rl_conductor_orchestrator import (
    ExecutionPlan,
    OrchestrationAction,
    OrchestrationStrategy,
    RLConductorOrchestrator,
    RLOrchestratorConfig,
    StrategyCategory,
)
from src.l4.causal_debug_engine import (
    AgentTrajectory,
    CausalAttribution,
    CausalDebugEngine,
    DebugConfig,
    InterventionType,
    StructuralCausalModel,
)
from src.l4.adapt_orch_topology_router import (
    AdaptOrchTopologyRouter,
    DAGNode,
    OrchestrationTopology,
    TaskDAG,
    TopologyConstraint,
    TopologyRouterConfig,
    TopologyType,
)
from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class OrchestrationPath(Enum):
    """Which orchestration path was used."""
    V3_AUTONOMOUS = "v3_autonomous"    # Old TaskDAGBuilder/IntentParser
    V4_RL_CONDUCTOR = "v4_rl_conductor"  # New RL-trained orchestration
    HYBRID = "hybrid"                    # Both paths fused


@dataclass
class Phase3Result:
    """Complete Phase 3 processing result — plan + topology + attribution."""

    task_description: str
    execution_plan: ExecutionPlan | None = None
    topology: OrchestrationTopology | None = None
    attribution: CausalAttribution | None = None
    strategy: OrchestrationStrategy | None = None
    orchestration_path: OrchestrationPath = OrchestrationPath.V4_RL_CONDUCTOR
    plan_quality: float = 0.0
    estimated_cost_usd: float = 0.0
    estimated_latency_ms: float = 0.0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════════
# Core Bridge
# ═══════════════════════════════════════════════════════════════════════


class Phase3CausalOrchestrationBridge:
    """Bridge connecting v4.0 L4 causal orchestration to the pipeline.

    This is the primary integration point for Phase 3. It:
      - Plans task execution via RLConductorOrchestrator
      - Maps plans to topologies via AdaptOrchTopologyRouter
      - Builds SCMs from execution trajectories via CausalDebugEngine
      - Attributes failures to specific steps
      - Feeds attributions back to the conductor for continuous improvement

    Usage::

        bridge = Phase3CausalOrchestrationBridge()
        await bridge.initialize()

        result = await bridge.plan_and_execute(
            "Analyze Q3 earnings and predict Q4 outlook",
            complexity=0.7,
        )

        if result.attribution:
            fixes = bridge.suggest_fixes(result.attribution)

        await bridge.shutdown()
    """

    def __init__(
        self,
        l4_config: L4Config | None = None,
        enable_conductor: bool = True,
        enable_debug: bool = True,
        enable_topology: bool = True,
    ) -> None:
        self._logger = CortexLogger("phase3_bridge")

        app_config = get_config()
        l4_cfg = l4_config or app_config.l4

        self._enable_conductor = enable_conductor
        self._enable_debug = enable_debug
        self._enable_topology = enable_topology

        # --- L4: RL Conductor Orchestrator ---
        self._conductor = RLConductorOrchestrator(RLOrchestratorConfig(
            training_episodes=l4_cfg.rl_training_episodes,
            learning_rate=l4_cfg.rl_learning_rate,
            discount_factor=l4_cfg.rl_discount_factor,
            exploration_epsilon=l4_cfg.rl_exploration_epsilon,
            state_dim=l4_cfg.rl_state_dim,
            action_pool_size=l4_cfg.rl_action_pool_size,
            reward_quality_weight=l4_cfg.rl_reward_quality_weight,
            reward_cost_weight=l4_cfg.rl_reward_cost_weight,
            reward_latency_weight=l4_cfg.rl_reward_latency_weight,
        )) if enable_conductor else None

        # --- L4: Causal Debug Engine ---
        self._debug_engine = CausalDebugEngine(DebugConfig(
            max_scm_nodes=l4_cfg.cde_max_scm_nodes,
            do_resample_count=l4_cfg.cde_do_resample_count,
            shapley_samples=l4_cfg.cde_shapley_samples,
            attribution_confidence=l4_cfg.cde_attribution_confidence,
            min_effect_size=l4_cfg.cde_min_effect_size,
        )) if enable_debug else None

        # --- L4: AdaptOrch Topology Router ---
        self._topology_router = AdaptOrchTopologyRouter(TopologyRouterConfig(
            topology_types=list(l4_cfg.aot_topology_types),
            default_timeout_ms=l4_cfg.aot_default_timeout_ms,
            max_parallel_workers=l4_cfg.aot_max_parallel_workers,
            adaptive_threshold=l4_cfg.aot_adaptive_threshold,
        )) if enable_topology else None

        # --- State ---
        self._initialized: bool = False
        self._process_count: int = 0
        self._results: list[Phase3Result] = []
        self._trajectories: dict[str, AgentTrajectory] = {}

        self._logger.info("phase3_bridge_created",
                          enable_conductor=enable_conductor,
                          enable_debug=enable_debug,
                          enable_topology=enable_topology)

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize the Phase 3 bridge with default training."""
        self._initialized = True

        if self._conductor is not None:
            # Quick bootstrap training on common task patterns
            bootstrap_tasks = [
                "analyze financial data and identify trends",
                "review code for bugs and suggest fixes",
                "summarize research papers and extract key findings",
                "evaluate security vulnerabilities and prioritize risks",
                "generate creative solutions to engineering problems",
                "compare multiple investment strategies",
                "audit compliance with regulatory requirements",
                "diagnose system failures from log data",
            ]
            self._conductor.train_orchestrator(bootstrap_tasks)

        self._logger.info("phase3_bridge_initialized",
                          trained=self._conductor.is_trained if self._conductor else False)

    async def shutdown(self) -> None:
        """Gracefully shutdown the Phase 3 bridge."""
        self._initialized = False
        self._logger.info("phase3_bridge_shutdown",
                          total_processed=self._process_count)

    # ── Main Planning Pipeline ────────────────────────────────────────

    async def plan_and_execute(
        self,
        task_description: str,
        complexity: float = 0.5,
        budget_usd: float = 1.0,
        deadline_ms: float = 30000.0,
    ) -> Phase3Result:
        """Plan and execute a task through the L4 orchestration pipeline.

        Full pipeline:
          1. RL Conductor → generates execution plan
          2. Topology Router → maps plan to topology
          3. (Execution happens externally)
          4. Causal Debug → attributes outcome to steps

        Args:
            task_description: What needs to be done
            complexity: Estimated task complexity (0-1)
            budget_usd: Budget constraint
            deadline_ms: Time constraint

        Returns:
            Phase3Result with plan, topology, and (if available) attribution
        """
        t_start = time.time()
        self._process_count += 1

        context = {"complexity": complexity, "budget_usd": budget_usd, "deadline_ms": deadline_ms}

        # Step 1: RL Conductor → Execution Plan
        plan = None
        strategy = None
        if self._conductor is not None:
            plan = self._conductor.orchestrate(task_description, context)
            strategy = self._conductor.discover_strategy(task_description[:30])

        # Step 2: Build DAG from plan actions
        topology = None
        if self._topology_router is not None and plan is not None:
            dag = self._plan_to_dag(plan)
            topology = self._topology_router.map_dag_to_topology(dag)

            # Optimize based on constraints
            if complexity > 0.7:
                topology = self._topology_router.optimize_for_constraint(
                    topology, TopologyConstraint.MAX_QUALITY,
                )
            elif deadline_ms < 10000:
                topology = self._topology_router.optimize_for_constraint(
                    topology, TopologyConstraint.MIN_LATENCY,
                )
            elif budget_usd < 0.5:
                topology = self._topology_router.optimize_for_constraint(
                    topology, TopologyConstraint.MIN_COST,
                )

        # Build result
        latency = (time.time() - t_start) * 1000.0

        result = Phase3Result(
            task_description=task_description,
            execution_plan=plan,
            topology=topology,
            strategy=strategy,
            orchestration_path=OrchestrationPath.V4_RL_CONDUCTOR,
            plan_quality=plan.expected_quality if plan else 0.5,
            estimated_cost_usd=plan.estimated_cost_usd if plan else 0.0,
            estimated_latency_ms=plan.estimated_latency_ms if plan else 0.0,
            latency_ms=round(latency, 2),
            metadata=context,
        )

        self._results.append(result)
        self._logger.debug("phase3_planned",
                           task=task_description[:50],
                           plan_actions=plan.action_count if plan else 0,
                           topology=topology.topology_type.value if topology else "none",
                           latency_ms=round(latency, 2))

        return result

    # ── Failure Attribution ───────────────────────────────────────────

    async def attribute_failure(
        self,
        task_description: str,
        steps: list[dict[str, Any]],
        outcome_score: float,
        final_outcome: str = "failure",
    ) -> CausalAttribution | None:
        """Attribute a task failure to specific steps.

        Builds an SCM from the trajectory and uses Shapley decomposition
        to identify which step(s) caused the failure.

        Args:
            task_description: The original task
            steps: Ordered list of step records
            outcome_score: 0-1 quality score
            final_outcome: "success", "failure", or "partial"

        Returns:
            CausalAttribution with per-step effects, or None if debug disabled
        """
        if self._debug_engine is None:
            return None

        trajectory = AgentTrajectory(
            trajectory_id=f"traj-{self._process_count:04d}",
            task_description=task_description,
            steps=steps,
            final_outcome=final_outcome,
            outcome_score=outcome_score,
        )

        self._trajectories[trajectory.trajectory_id] = trajectory
        return self._debug_engine.attribute_failure(trajectory)

    async def analyze_trajectory(
        self,
        trajectory: AgentTrajectory,
    ) -> tuple[StructuralCausalModel, CausalAttribution]:
        """Build SCM and attribute failure for a trajectory."""
        if self._debug_engine is None:
            raise RuntimeError("CausalDebugEngine not enabled")

        scm = self._debug_engine.build_scm(trajectory)
        attribution = self._debug_engine.attribute_failure(trajectory, scm)
        return scm, attribution

    # ── Fix Suggestions ───────────────────────────────────────────────

    def suggest_fixes(self, attribution: CausalAttribution) -> list[dict[str, Any]]:
        """Get fix suggestions from a causal attribution."""
        if self._debug_engine is None:
            return []
        return self._debug_engine.suggest_fix(attribution)

    # ── Do-Intervention ───────────────────────────────────────────────

    def test_intervention(
        self,
        trajectory: AgentTrajectory,
        step_index: int,
        intervention_type: InterventionType,
    ) -> dict[str, Any] | None:
        """Test a causal intervention on a trajectory step."""
        if self._debug_engine is None:
            return None

        scm = self._debug_engine.build_scm(trajectory)
        node_id = f"step-{step_index:03d}"

        return self._debug_engine.do_intervention(
            scm, node_id, intervention_type,
        )

    # ── Topology Adaptation ───────────────────────────────────────────

    def adapt_topology(
        self,
        topology: OrchestrationTopology,
        feedback: dict[str, Any],
    ) -> OrchestrationTopology | None:
        """Adapt topology at runtime based on execution feedback."""
        if self._topology_router is None:
            return None
        return self._topology_router.adapt_at_runtime(topology, feedback)

    # ── Helper Methods ────────────────────────────────────────────────

    def _plan_to_dag(self, plan: ExecutionPlan) -> TaskDAG:
        """Convert an ExecutionPlan into a TaskDAG for topology routing."""
        dag = TaskDAG(dag_id=f"dag-{plan.plan_id}")

        for i, action in enumerate(plan.actions):
            node_id = f"action-{i:03d}"
            node = DAGNode(
                node_id=node_id,
                task_description=f"{action.action_type.value}:{action.model_id}",
                estimated_complexity=0.5,
                estimated_cost_usd=plan.estimated_cost_usd / max(plan.action_count, 1),
                estimated_latency_ms=plan.estimated_latency_ms / max(plan.action_count, 1),
            )
            dag.add_node(node)

            # Sequential dependencies by default
            if i > 0:
                dag.add_edge(f"action-{i-1:03d}", node_id)

        dag.update_entry_exit()
        return dag

    def create_trajectory_from_result(
        self,
        result: Phase3Result,
        steps: list[dict[str, Any]],
        outcome_score: float,
    ) -> AgentTrajectory:
        """Create an AgentTrajectory from a Phase3Result for debugging."""
        return AgentTrajectory(
            trajectory_id=f"traj-{result.timestamp:.0f}",
            task_description=result.task_description,
            steps=steps,
            final_outcome="success" if outcome_score > 0.7 else "failure",
            outcome_score=outcome_score,
            total_cost_usd=result.estimated_cost_usd,
            total_latency_ms=result.estimated_latency_ms,
            metadata={"plan_id": result.execution_plan.plan_id if result.execution_plan else ""},
        )

    # ── Model Registration ────────────────────────────────────────────

    def register_model(self, model_id: str, quality: float, cost: float, latency_ms: float) -> None:
        """Register a model with the RL conductor."""
        if self._conductor is not None:
            self._conductor.register_model(model_id, quality, cost, latency_ms)

    # ── Legacy Compatibility ──────────────────────────────────────────

    def to_legacy_plan(self, result: Phase3Result) -> dict[str, Any]:
        """Convert Phase 3 result to v3.0 TaskDAGBuilder-compatible format."""
        plan = result.execution_plan
        topology = result.topology

        return {
            "plan_id": plan.plan_id if plan else "",
            "task": result.task_description,
            "nodes": [
                {
                    "node_id": a.model_id or f"step-{i}",
                    "action_type": a.action_type.value,
                    "dependencies": [],
                }
                for i, a in enumerate(plan.actions)
            ] if plan else [],
            "topology": topology.topology_type.value if topology else "sequential",
            "estimated_latency_ms": result.estimated_latency_ms,
            "estimated_cost_usd": result.estimated_cost_usd,
        }

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def conductor(self) -> RLConductorOrchestrator | None:
        return self._conductor

    @property
    def debug_engine(self) -> CausalDebugEngine | None:
        return self._debug_engine

    @property
    def topology_router(self) -> AdaptOrchTopologyRouter | None:
        return self._topology_router

    @property
    def stats(self) -> dict[str, Any]:
        """Bridge-level statistics aggregating all Phase 3 components."""
        stats: dict[str, Any] = {
            "initialized": self._initialized,
            "process_count": self._process_count,
            "enable_conductor": self._enable_conductor,
            "enable_debug": self._enable_debug,
            "enable_topology": self._enable_topology,
        }
        if self._conductor is not None:
            stats["l4_conductor"] = self._conductor.stats
        if self._debug_engine is not None:
            stats["l4_debug"] = self._debug_engine.stats
        if self._topology_router is not None:
            stats["l4_topology"] = self._topology_router.stats
        if self._results:
            last = self._results[-1]
            stats["last_result"] = {
                "task": last.task_description[:80],
                "plan_quality": round(last.plan_quality, 3),
                "topology": last.topology.topology_type.value if last.topology else "none",
                "latency_ms": last.latency_ms,
            }
        return stats

    def reset(self) -> None:
        """Reset all Phase 3 components."""
        if self._conductor is not None:
            self._conductor.reset()
        if self._debug_engine is not None:
            self._debug_engine.reset()
        if self._topology_router is not None:
            self._topology_router.reset()
        self._process_count = 0
        self._results.clear()
        self._trajectories.clear()
        self._logger.debug("phase3_bridge_reset")
