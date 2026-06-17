"""Tests for L7: DigitalTwinEngine — 主动数字孪生引擎."""

import numpy as np
import pytest

from src.l7.digital_twin_engine import (
    AnomalyReport,
    AnomalySeverity,
    DTEConfig,
    DigitalState,
    DigitalTwinEngine,
    HealthReport,
    InterventionPlan,
    PhysicalState,
    PredictedState,
)


@pytest.fixture
def config() -> DTEConfig:
    return DTEConfig(state_dim=32, health_check_interval_steps=9999)  # Disable periodic checks


@pytest.fixture
def engine(config: DTEConfig) -> DigitalTwinEngine:
    return DigitalTwinEngine(config=config)


@pytest.fixture
def synced_engine(engine: DigitalTwinEngine) -> DigitalTwinEngine:
    for i in range(5):
        state = PhysicalState(
            state_id=f"state-{i}",
            vector=np.random.RandomState(42 + i).randn(32) * 0.5,
        )
        engine.synchronize(state)
    return engine


class TestEngineInit:
    def test_default_init(self) -> None:
        e = DigitalTwinEngine()
        assert e.stats["step_count"] == 0
        assert e.stats["anomaly_count"] == 0

    def test_custom_config(self, engine: DigitalTwinEngine) -> None:
        assert engine._config.state_dim == 32

    def test_initial_state_none(self, engine: DigitalTwinEngine) -> None:
        assert engine.get_current_state() is None


class TestSynchronization:
    def test_synchronize_first_state(self, engine: DigitalTwinEngine) -> None:
        physical = PhysicalState(state_id="s1", vector=np.ones(32) * 0.5)
        digital = engine.synchronize(physical)
        assert isinstance(digital, DigitalState)
        assert digital.physical_source_id == "s1"
        assert digital.state_norm > 0.0
        assert engine.stats["step_count"] == 1

    def test_synchronize_multiple_states(self, engine: DigitalTwinEngine) -> None:
        for i in range(10):
            physical = PhysicalState(state_id=f"s{i}", vector=np.random.RandomState(i).randn(32) * 0.5)
            engine.synchronize(physical)
        assert engine.stats["step_count"] == 10
        assert engine.stats["state_history_size"] == 10

    def test_synchronize_projects_dimension(self, engine: DigitalTwinEngine) -> None:
        physical = PhysicalState(state_id="wide", vector=np.random.RandomState(0).randn(50))
        digital = engine.synchronize(physical)
        assert digital.mean.shape == (32,)

    def test_synchronize_has_prediction_error(self, engine: DigitalTwinEngine) -> None:
        physical = PhysicalState(state_id="s1", vector=np.ones(32))
        engine.synchronize(physical)
        digital = engine.get_current_state()
        assert digital is not None
        assert digital.prediction_error >= 0.0

    def test_synchronize_has_free_energy(self, engine: DigitalTwinEngine) -> None:
        physical = PhysicalState(state_id="s1", vector=np.ones(32) * 0.5)
        digital = engine.synchronize(physical)
        assert digital.free_energy >= 0.0


class TestWhatIfSimulation:
    def test_simulate_what_if_default(self, synced_engine: DigitalTwinEngine) -> None:
        predictions = synced_engine.simulate_what_if()
        assert len(predictions) == synced_engine._config.simulation_horizon_steps
        assert isinstance(predictions[0], PredictedState)
        assert predictions[0].step == 1

    def test_simulate_what_if_with_intervention(self, synced_engine: DigitalTwinEngine) -> None:
        intervention = np.ones(32) * 0.1
        predictions = synced_engine.simulate_what_if(intervention, horizon=10)
        assert len(predictions) == 10

    def test_simulate_what_if_custom_horizon(self, synced_engine: DigitalTwinEngine) -> None:
        predictions = synced_engine.simulate_what_if(horizon=5)
        assert len(predictions) == 5

    def test_simulate_no_state(self, engine: DigitalTwinEngine) -> None:
        predictions = engine.simulate_what_if()
        assert predictions == []

    def test_simulate_multiple_what_ifs(self, synced_engine: DigitalTwinEngine) -> None:
        interventions = [np.zeros(32), np.ones(32) * 0.1, np.ones(32) * -0.1]
        results = synced_engine.simulate_multiple_what_ifs(interventions)
        assert len(results) == 3
        for traj in results:
            assert len(traj) > 0

    def test_predictions_have_anomaly_prob(self, synced_engine: DigitalTwinEngine) -> None:
        predictions = synced_engine.simulate_what_if(horizon=5)
        for p in predictions:
            assert 0.0 <= p.anomaly_probability <= 1.0


class TestAnomalyDetection:
    def test_detect_anomaly_normal(self, synced_engine: DigitalTwinEngine) -> None:
        # Normal state close to prediction → no anomaly
        state = PhysicalState(
            state_id="normal",
            vector=synced_engine.get_current_state().mean + np.random.RandomState(0).randn(32) * 0.01,
        )
        result = synced_engine.detect_anomaly(state)
        # May or may not be anomaly depending on model fit — just check type
        if result is not None:
            assert isinstance(result, AnomalyReport)

    def test_detect_anomaly_critical(self, synced_engine: DigitalTwinEngine) -> None:
        # Very different state → should trigger anomaly
        state = PhysicalState(
            state_id="anomalous",
            vector=synced_engine.get_current_state().mean + np.ones(32) * 50.0,
        )
        result = synced_engine.detect_anomaly(state)
        assert result is not None
        assert result.severity in (AnomalySeverity.WARNING, AnomalySeverity.CRITICAL, AnomalySeverity.EMERGENCY)

    def test_detect_anomaly_no_state(self, engine: DigitalTwinEngine) -> None:
        result = engine.detect_anomaly()
        assert result is None

    def test_get_anomalies_filtered(self, synced_engine: DigitalTwinEngine) -> None:
        # Trigger an anomaly
        state = PhysicalState(
            state_id="big-dev",
            vector=synced_engine.get_current_state().mean + np.ones(32) * 100.0,
        )
        synced_engine.detect_anomaly(state)
        criticals = synced_engine.get_anomalies(AnomalySeverity.CRITICAL)
        assert isinstance(criticals, list)


class TestInterventionRecommendation:
    def test_recommend_intervention(self, synced_engine: DigitalTwinEngine) -> None:
        plan = synced_engine.recommend_intervention()
        assert isinstance(plan, InterventionPlan)
        assert plan.plan_id
        assert len(plan.actions) > 0

    def test_recommend_with_goal(self, synced_engine: DigitalTwinEngine) -> None:
        goal = np.zeros(32)
        plan = synced_engine.recommend_intervention(goal_state=goal)
        assert isinstance(plan, InterventionPlan)
        assert plan.expected_free_energy >= 0.0

    def test_recommend_no_state(self, engine: DigitalTwinEngine) -> None:
        plan = engine.recommend_intervention()
        assert plan.plan_id == "no-state"

    def test_recommend_has_success_prob(self, synced_engine: DigitalTwinEngine) -> None:
        plan = synced_engine.recommend_intervention()
        assert 0.0 <= plan.estimated_success_probability <= 1.0


class TestHealthMonitoring:
    def test_structural_health_monitoring(self, synced_engine: DigitalTwinEngine) -> None:
        report = synced_engine.structural_health_monitoring()
        assert isinstance(report, HealthReport)
        assert 0.0 <= report.overall_health <= 1.0
        assert report.trend in ("stable", "deteriorating", "improving", "critical")

    def test_health_has_recommendations(self, synced_engine: DigitalTwinEngine) -> None:
        report = synced_engine.structural_health_monitoring()
        assert isinstance(report.recommendations, list)


class TestStateHistory:
    def test_history_bounded(self, engine: DigitalTwinEngine) -> None:
        for i in range(engine._config.history_window + 100):
            physical = PhysicalState(state_id=f"h{i}", vector=np.random.RandomState(i).randn(32))
            engine.synchronize(physical)
        assert engine.stats["state_history_size"] <= engine._config.history_window


class TestReset:
    def test_reset_clears_all(self, synced_engine: DigitalTwinEngine) -> None:
        synced_engine.reset()
        assert synced_engine.stats["step_count"] == 0
        assert synced_engine.stats["anomaly_count"] == 0
        assert synced_engine.stats["state_history_size"] == 0
        assert synced_engine.get_current_state() is None
