"""Integration tests for Phase 3: L4 RL Conductor + Causal Debug + Topology Router."""

import asyncio

import numpy as np
import pytest

from src.bridge.phase3_causal_orch_bridge import (
    OrchestrationPath,
    Phase3CausalOrchestrationBridge,
    Phase3Result,
)
from src.l4.adapt_orch_topology_router import DAGNode, TaskDAG, TopologyConstraint, TopologyType
from src.l4.causal_debug_engine import AgentTrajectory, InterventionType
from src.l4.rl_conductor_orchestrator import ExecutionPlan, OrchestrationStrategy


@pytest.fixture
def bridge() -> Phase3CausalOrchestrationBridge:
    return Phase3CausalOrchestrationBridge(enable_conductor=True, enable_debug=True, enable_topology=True)


@pytest.fixture
def bridge_minimal() -> Phase3CausalOrchestrationBridge:
    return Phase3CausalOrchestrationBridge(enable_conductor=False, enable_debug=False, enable_topology=False)


class TestBridgeLifecycle:
    def test_initial_state(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        assert not bridge.is_initialized
        assert bridge.stats["process_count"] == 0

    @pytest.mark.asyncio
    async def test_initialize_trains_conductor(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        assert bridge.is_initialized
        assert bridge.conductor.is_trained

    @pytest.mark.asyncio
    async def test_shutdown(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        await bridge.shutdown()
        assert not bridge.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_minimal(self, bridge_minimal: Phase3CausalOrchestrationBridge) -> None:
        await bridge_minimal.initialize()
        assert bridge_minimal.is_initialized


class TestPlanAndExecute:
    @pytest.mark.asyncio
    async def test_plan_task(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        result = await bridge.plan_and_execute("Analyze Q3 earnings report")
        assert isinstance(result, Phase3Result)
        assert result.execution_plan is not None
        assert result.execution_plan.action_count > 0

    @pytest.mark.asyncio
    async def test_plan_with_complexity(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        result = await bridge.plan_and_execute(
            "Audit security vulnerabilities",
            complexity=0.9,
            budget_usd=2.0,
            deadline_ms=60000,
        )
        assert result.plan_quality > 0.0

    @pytest.mark.asyncio
    async def test_plan_returns_topology(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        result = await bridge.plan_and_execute("Generate trading signals")
        assert result.topology is not None
        assert result.topology.topology_type in (
            TopologyType.SEQUENTIAL, TopologyType.PARALLEL,
            TopologyType.HIERARCHICAL, TopologyType.HYBRID,
        )

    @pytest.mark.asyncio
    async def test_plan_increments_count(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        await bridge.plan_and_execute("Task 1")
        assert bridge.stats["process_count"] == 1

    @pytest.mark.asyncio
    async def test_plan_without_conductor(self, bridge_minimal: Phase3CausalOrchestrationBridge) -> None:
        await bridge_minimal.initialize()
        result = await bridge_minimal.plan_and_execute("Task")
        assert result.execution_plan is None
        assert result.topology is None


class TestFailureAttribution:
    @pytest.mark.asyncio
    async def test_attribute_failure(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        steps = [
            {"action_type": "model_call", "input": "data", "output": "analysis", "success": True},
            {"action_type": "tool_use", "input": "analysis", "output": "error", "success": False},
            {"action_type": "model_call", "input": "error", "output": "wrong conclusion", "success": False},
        ]
        attribution = await bridge.attribute_failure(
            "Debug crash", steps, outcome_score=0.15, final_outcome="failure",
        )
        assert attribution is not None
        assert len(attribution.attributions) > 0

    @pytest.mark.asyncio
    async def test_attribute_failure_disabled(self, bridge_minimal: Phase3CausalOrchestrationBridge) -> None:
        await bridge_minimal.initialize()
        attribution = await bridge_minimal.attribute_failure("test", [], 0.5)
        assert attribution is None

    @pytest.mark.asyncio
    async def test_suggest_fixes(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        steps = [{"action_type": "model_call", "input": "x", "output": "bad", "success": False}]
        attribution = await bridge.attribute_failure("test", steps, outcome_score=0.1)
        if attribution:
            fixes = bridge.suggest_fixes(attribution)
            assert isinstance(fixes, list)


class TestDoIntervention:
    @pytest.mark.asyncio
    async def test_test_intervention(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        trajectory = AgentTrajectory(
            trajectory_id="int-test",
            task_description="Test intervention",
            steps=[
                {"action_type": "model_call", "input": "in", "output": "out", "success": True},
            ],
            final_outcome="success",
            outcome_score=0.8,
        )
        result = bridge.test_intervention(trajectory, 0, InterventionType.DO_ACTION)
        assert result is not None
        assert "improvement" in result


class TestTopologyAdaptation:
    @pytest.mark.asyncio
    async def test_adapt_topology(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        result = await bridge.plan_and_execute("Test task")
        if result.topology:
            adapted = bridge.adapt_topology(result.topology, {"worker_slow": "model-x"})
            assert adapted is not None

    @pytest.mark.asyncio
    async def test_adapt_disabled(self, bridge_minimal: Phase3CausalOrchestrationBridge) -> None:
        await bridge_minimal.initialize()
        assert bridge_minimal.adapt_topology(None, {}) is None


class TestLegacyCompatibility:
    @pytest.mark.asyncio
    async def test_to_legacy_plan(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        result = await bridge.plan_and_execute("Analyze data")
        legacy = bridge.to_legacy_plan(result)
        assert "plan_id" in legacy
        assert "task" in legacy
        assert "nodes" in legacy
        assert "topology" in legacy


class TestModelRegistration:
    def test_register_model(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        bridge.register_model("test-model", 0.85, 0.02, 800)
        assert "test-model" in bridge.conductor.list_models()


class TestBridgeStats:
    def test_stats_initial(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        stats = bridge.stats
        assert "l4_conductor" in stats
        assert "l4_debug" in stats
        assert "l4_topology" in stats

    @pytest.mark.asyncio
    async def test_stats_after_processing(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        await bridge.plan_and_execute("Test task")
        stats = bridge.stats
        assert stats["process_count"] == 1
        assert stats["last_result"] is not None


class TestBridgeReset:
    @pytest.mark.asyncio
    async def test_reset(self, bridge: Phase3CausalOrchestrationBridge) -> None:
        await bridge.initialize()
        await bridge.plan_and_execute("Task")
        bridge.reset()
        assert bridge.stats["process_count"] == 0


# ═══════════════════════════════════════════════════════════════════════
# Cross-Phase Integration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestFullPhase3Pipeline:
    @pytest.mark.asyncio
    async def test_end_to_end_flow(self) -> None:
        """Full Phase 3 pipeline: plan → attribute → fix."""
        bridge = Phase3CausalOrchestrationBridge()
        await bridge.initialize()

        # Plan
        result = await bridge.plan_and_execute(
            "Analyze portfolio risk and suggest rebalancing",
            complexity=0.6,
        )
        assert result.execution_plan is not None
        assert result.topology is not None

        # Simulate execution failure
        steps = [
            {"action_type": a.action_type.value, "input": a.model_id, "output": "result",
             "success": i != 2}  # Step 2 fails
            for i, a in enumerate(result.execution_plan.actions)
        ]

        # Attribute
        attribution = await bridge.attribute_failure(
            result.task_description, steps,
            outcome_score=0.3, final_outcome="failure",
        )

        if attribution and attribution.suggested_fixes:
            fixes = bridge.suggest_fixes(attribution)
            assert len(fixes) > 0

    @pytest.mark.asyncio
    async def test_parallel_phase1_phase2_phase3(self) -> None:
        """All three phases can coexist."""
        from src.bridge.phase1_liquid_bridge import Phase1LiquidBridge
        from src.bridge.phase2_mycorrhizal_bridge import Phase2MycorrhizalBridge
        from src.l1.liquid_perceptor import DataPoint, ModalityType

        p1 = Phase1LiquidBridge(enable_snn=False, enable_routing=False)
        await p1.initialize()

        p2 = Phase2MycorrhizalBridge(enable_validator=False, enable_swarm=False)
        await p2.initialize()

        p3 = Phase3CausalOrchestrationBridge()
        await p3.initialize()

        # All three initialized
        assert p1.is_initialized and p2.is_initialized and p3.is_initialized

        # Process through all three
        p1_result = await p1.process(DataPoint(
            modality=ModalityType.TIME_SERIES,
            vector=np.random.RandomState(42).randn(20).astype(np.float64),
        ))
        assert p1_result.percept is not None

        p2_result = await p2.process_claim("Market is bullish", agent_id="a1")
        assert p2_result.trace is not None

        p3_result = await p3.plan_and_execute("Analyze data")
        assert p3_result.execution_plan is not None
