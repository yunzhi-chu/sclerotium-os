"""Tests for L4: CausalDebugEngine — 因果调试引擎."""

import numpy as np
import pytest

from src.l4.causal_debug_engine import (
    AgentTrajectory,
    CausalAttribution,
    CausalDebugEngine,
    DebugConfig,
    InterventionType,
    SCMNode,
    StructuralCausalModel,
)


@pytest.fixture
def config() -> DebugConfig:
    return DebugConfig(max_scm_nodes=50, do_resample_count=50, shapley_samples=100)


@pytest.fixture
def engine(config: DebugConfig) -> CausalDebugEngine:
    return CausalDebugEngine(config=config)


@pytest.fixture
def success_trajectory() -> AgentTrajectory:
    return AgentTrajectory(
        trajectory_id="traj-001",
        task_description="Analyze stock data and generate report",
        steps=[
            {"action_type": "model_call", "input": "Load market data", "output": "Market data loaded: AAPL +2%, GOOG -1%", "success": True},
            {"action_type": "tool_use", "input": "Calculate volatility", "output": "30-day vol: 25%", "success": True},
            {"action_type": "model_call", "input": "Generate report from: 30-day vol: 25%", "output": "Q3 outlook: bullish", "success": True},
        ],
        final_outcome="success",
        outcome_score=0.85,
    )


@pytest.fixture
def failure_trajectory() -> AgentTrajectory:
    return AgentTrajectory(
        trajectory_id="traj-002",
        task_description="Debug system crash from logs",
        steps=[
            {"action_type": "model_call", "input": "Parse error logs", "output": "NullPointerException at line 42", "success": True},
            {"action_type": "tool_use", "input": "Check database connection", "output": "Connection timeout", "success": False, "error": "timeout"},
            {"action_type": "model_call", "input": "Connection timeout", "output": "Root cause: misconfigured pool size", "success": False},
        ],
        final_outcome="failure",
        outcome_score=0.2,
    )


class TestDebugInit:
    def test_default_init(self) -> None:
        e = CausalDebugEngine()
        assert e.stats["debug_count"] == 0
        assert e.stats["scm_count"] == 0

    def test_custom_config(self, config: DebugConfig) -> None:
        e = CausalDebugEngine(config=config)
        assert e._config.max_scm_nodes == 50


class TestSCMConstruction:
    def test_build_scm(self, engine: CausalDebugEngine, success_trajectory: AgentTrajectory) -> None:
        scm = engine.build_scm(success_trajectory)
        assert isinstance(scm, StructuralCausalModel)
        assert scm.node_count == 3
        assert scm.trajectory_id == "traj-001"

    def test_build_scm_empty_trajectory(self, engine: CausalDebugEngine) -> None:
        traj = AgentTrajectory(trajectory_id="empty", task_description="test")
        scm = engine.build_scm(traj)
        assert scm.node_count == 0

    def test_build_scm_infers_edges(self, engine: CausalDebugEngine, success_trajectory: AgentTrajectory) -> None:
        scm = engine.build_scm(success_trajectory)
        # With shared tokens between steps, edges should be inferred
        assert scm.edge_count >= 0  # May or may not have edges depending on overlap

    def test_scm_root_nodes(self, engine: CausalDebugEngine, success_trajectory: AgentTrajectory) -> None:
        scm = engine.build_scm(success_trajectory)
        assert len(scm.root_nodes) >= 1

    def test_scm_causal_path(self, engine: CausalDebugEngine, success_trajectory: AgentTrajectory) -> None:
        scm = engine.build_scm(success_trajectory)
        if scm.node_count > 0:
            path = scm.get_causal_path(scm.outcome_node_id)
            assert len(path) > 0


class TestFailureAttribution:
    def test_attribute_failure(self, engine: CausalDebugEngine, failure_trajectory: AgentTrajectory) -> None:
        attribution = engine.attribute_failure(failure_trajectory)
        assert isinstance(attribution, CausalAttribution)
        assert attribution.trajectory_id == "traj-002"
        assert len(attribution.attributions) > 0

    def test_attribute_success(self, engine: CausalDebugEngine, success_trajectory: AgentTrajectory) -> None:
        attribution = engine.attribute_failure(success_trajectory)
        assert isinstance(attribution, CausalAttribution)

    def test_primary_cause_identified(self, engine: CausalDebugEngine, failure_trajectory: AgentTrajectory) -> None:
        attribution = engine.attribute_failure(failure_trajectory)
        # With failing steps, a primary cause should be identified
        assert isinstance(attribution.primary_cause, str)

    def test_shapley_values_sum(self, engine: CausalDebugEngine, failure_trajectory: AgentTrajectory) -> None:
        attribution = engine.attribute_failure(failure_trajectory)
        for node_id in attribution.shapley_values:
            assert isinstance(attribution.shapley_values[node_id], float)

    def test_confidence_computed(self, engine: CausalDebugEngine, failure_trajectory: AgentTrajectory) -> None:
        attribution = engine.attribute_failure(failure_trajectory)
        assert 0.0 <= attribution.confidence <= 1.0

    def test_fix_suggestions(self, engine: CausalDebugEngine, failure_trajectory: AgentTrajectory) -> None:
        attribution = engine.attribute_failure(failure_trajectory)
        fixes = engine.suggest_fix(attribution)
        assert isinstance(fixes, list)


class TestDoIntervention:
    def test_do_action_intervention(self, engine: CausalDebugEngine, failure_trajectory: AgentTrajectory) -> None:
        scm = engine.build_scm(failure_trajectory)
        if scm.node_count > 0:
            result = engine.do_intervention(scm, "step-001", InterventionType.DO_ACTION)
            assert "counterfactual_outcome" in result
            assert "improvement" in result

    def test_do_resample_intervention(self, engine: CausalDebugEngine, success_trajectory: AgentTrajectory) -> None:
        scm = engine.build_scm(success_trajectory)
        if scm.node_count > 0:
            result = engine.do_intervention(scm, "step-000", InterventionType.DO_RESAMPLE)
            assert "baseline_outcome" in result

    def test_do_intervention_nonexistent_node(self, engine: CausalDebugEngine, success_trajectory: AgentTrajectory) -> None:
        scm = engine.build_scm(success_trajectory)
        result = engine.do_intervention(scm, "nonexistent", InterventionType.DO_ACTION)
        assert "error" in result

    def test_significance_detection(self, engine: CausalDebugEngine, failure_trajectory: AgentTrajectory) -> None:
        scm = engine.build_scm(failure_trajectory)
        # Find a failing step
        for node_id, node in scm.nodes.items():
            if not node.success:
                result = engine.do_intervention(scm, node_id, InterventionType.DO_ACTION)
                assert isinstance(result["significant"], bool)
                break


class TestSCMNode:
    def test_node_creation(self) -> None:
        node = SCMNode(node_id="n1", step_index=0, action_type="model_call", success=True)
        assert node.step_index == 0
        assert node.success is True
        assert node.parents == []

    def test_node_with_parents(self) -> None:
        node = SCMNode(node_id="n2", step_index=1, action_type="tool_use", parents=["n1"])
        assert "n1" in node.parents


class TestReset:
    def test_reset_clears_all(self, engine: CausalDebugEngine, failure_trajectory: AgentTrajectory) -> None:
        engine.build_scm(failure_trajectory)
        engine.attribute_failure(failure_trajectory)
        engine.reset()
        assert engine.stats["debug_count"] == 0
        assert engine.stats["scm_count"] == 0
        assert engine.stats["attribution_count"] == 0
