"""Tests for L4: RLConductorOrchestrator — RL训练的路由编排器."""

import numpy as np
import pytest

from src.l4.rl_conductor_orchestrator import (
    ExecutionPlan,
    OrchestrationAction,
    OrchestrationStrategy,
    RLConductorOrchestrator,
    RLOrchestratorConfig,
    StrategyCategory,
)


@pytest.fixture
def config() -> RLOrchestratorConfig:
    return RLOrchestratorConfig(training_episodes=50, state_dim=32)


@pytest.fixture
def conductor(config: RLOrchestratorConfig) -> RLConductorOrchestrator:
    return RLConductorOrchestrator(config=config)


@pytest.fixture
def trained_conductor(conductor: RLConductorOrchestrator) -> RLConductorOrchestrator:
    tasks = ["analyze stocks", "review code", "summarize text", "evaluate risk", "generate report"]
    conductor.train_orchestrator(tasks * 10)
    return conductor


class TestConductorInit:
    def test_default_init(self) -> None:
        c = RLConductorOrchestrator()
        assert not c.is_trained
        assert c.stats["episode_count"] == 0
        assert c.stats["plan_count"] == 0

    def test_custom_config(self, config: RLOrchestratorConfig) -> None:
        c = RLConductorOrchestrator(config=config)
        assert c._config.state_dim == 32
        assert c._config.training_episodes == 50

    def test_default_model_pool(self, conductor: RLConductorOrchestrator) -> None:
        models = conductor.list_models()
        assert len(models) >= 3
        assert "claude-opus" in models


class TestTraining:
    def test_train_orchestrator(self, conductor: RLConductorOrchestrator) -> None:
        tasks = ["task A", "task B", "task C"]
        metrics = conductor.train_orchestrator(tasks * 10)
        assert metrics["episodes"] > 0
        assert conductor.is_trained
        assert conductor.stats["q_table_size"] > 0

    def test_training_records_rewards(self, conductor: RLConductorOrchestrator) -> None:
        conductor.train_orchestrator(["task"] * 20)
        assert len(conductor._reward_history) > 0

    def test_training_empty_tasks(self, conductor: RLConductorOrchestrator) -> None:
        conductor.train_orchestrator([])
        assert not conductor.is_trained


class TestOrchestration:
    def test_orchestrate_returns_plan(self, trained_conductor: RLConductorOrchestrator) -> None:
        plan = trained_conductor.orchestrate("Analyze market trends")
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.actions) > 0
        assert plan.expected_quality > 0.0

    def test_orchestrate_with_context(self, trained_conductor: RLConductorOrchestrator) -> None:
        plan = trained_conductor.orchestrate("Review code", {"complexity": 0.9, "budget_usd": 0.5})
        assert isinstance(plan, ExecutionPlan)

    def test_orchestrate_increments_plan_count(self, trained_conductor: RLConductorOrchestrator) -> None:
        before = trained_conductor.stats["plan_count"]
        trained_conductor.orchestrate("Task")
        assert trained_conductor.stats["plan_count"] == before + 1

    def test_orchestrate_untrained(self, conductor: RLConductorOrchestrator) -> None:
        """Untrained conductor should still produce a plan (exploration)."""
        plan = conductor.orchestrate("Some task")
        assert isinstance(plan, ExecutionPlan)


class TestStrategyDiscovery:
    def test_discover_strategy(self, trained_conductor: RLConductorOrchestrator) -> None:
        strategy = trained_conductor.discover_strategy("financial_analysis")
        assert isinstance(strategy, OrchestrationStrategy)
        assert "financial_analysis" in strategy.strategy_id
        assert strategy.usage_count >= 1

    def test_discover_strategy_cached(self, trained_conductor: RLConductorOrchestrator) -> None:
        s1 = trained_conductor.discover_strategy("code_review")
        s2 = trained_conductor.discover_strategy("code_review")
        assert s1.strategy_id == s2.strategy_id
        assert s2.usage_count >= 1  # Same pattern returns cached strategy

    def test_transfer_to_domain(self, trained_conductor: RLConductorOrchestrator) -> None:
        trained_conductor.discover_strategy("finance")
        transferred = trained_conductor.transfer_to_domain("medical")
        assert isinstance(transferred, OrchestrationStrategy)
        assert "medical" in transferred.strategy_id

    def test_transfer_without_existing(self, conductor: RLConductorOrchestrator) -> None:
        strategy = conductor.transfer_to_domain("new_domain")
        assert isinstance(strategy, OrchestrationStrategy)


class TestModelManagement:
    def test_register_model(self, conductor: RLConductorOrchestrator) -> None:
        conductor.register_model("test-model", 0.9, 0.01, 500)
        assert "test-model" in conductor.list_models()

    def test_list_models(self, conductor: RLConductorOrchestrator) -> None:
        models = conductor.list_models()
        assert isinstance(models, list)
        assert len(models) > 0


class TestReset:
    def test_reset_clears_all(self, trained_conductor: RLConductorOrchestrator) -> None:
        trained_conductor.reset()
        assert not trained_conductor.is_trained
        assert trained_conductor.stats["plan_count"] == 0
        assert trained_conductor.stats["q_table_size"] == 0
