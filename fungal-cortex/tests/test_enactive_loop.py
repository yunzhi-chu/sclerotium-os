"""Tests for Mechanism ⑪: Enactive Inference loop."""

import numpy as np
import pytest

from src.agent.agent_state import AgentState
from src.agent.enactive_loop import EnactiveLoop, EnactiveState
from src.core.event_bus import EventBus


@pytest.fixture
def enactive() -> EnactiveLoop:
    state = AgentState(name="test-enactive")
    return EnactiveLoop(agent_state=state, temperature=1.0, prediction_horizon=10)


class TestEnactiveLoop:
    def test_initial_state(self, enactive: EnactiveLoop) -> None:
        """EnactiveLoop starts with zero prediction and default readiness."""
        assert np.all(enactive.enactive.prediction == 0.0)
        assert enactive.enactive.action_readiness == 0.5
        assert enactive.enactive.free_energy == 0.0

    def test_perceive_updates_prediction(self, enactive: EnactiveLoop) -> None:
        """After perceiving, prediction should move toward sensory input."""
        old_pred = enactive.enactive.prediction.copy()
        enactive.perceive((0.8, 0.5, 0.1))
        # Prediction should have moved from zero toward the input
        assert enactive.enactive.prediction[0] > old_pred[0]

    def test_perceive_computes_free_energy(self, enactive: EnactiveLoop) -> None:
        """Free energy should be computed after perception."""
        enactive.perceive((0.9, 0.5, 0.1))
        assert enactive.enactive.free_energy > 0.0

    def test_action_returns_valid_string(self, enactive: EnactiveLoop) -> None:
        """Act should return a recognized action type."""
        enactive.perceive((0.3, 0.6, 0.4))
        action = enactive.act()
        assert isinstance(action, str)
        assert len(action) > 0

    def test_multiple_cycles_converge(self, enactive: EnactiveLoop) -> None:
        """Repeated perception of the same input should converge prediction."""
        for _ in range(20):
            enactive.perceive((0.7, 0.5, 0.2))
        # After convergence, prediction should be close to input
        assert abs(enactive.enactive.prediction[0] - 0.7) < 0.5

    def test_surprise_detection(self, enactive: EnactiveLoop) -> None:
        """A sudden large change should trigger surprise."""
        # First, train on a stable pattern
        for _ in range(10):
            enactive.perceive((0.5, 0.5, 0.1))
        # Then, present a sudden anomalous input
        enactive.perceive((0.99, 0.01, 0.99))
        assert enactive.is_surprised or enactive.enactive.free_energy > enactive._free_energy_history[0]

    def test_explore_exploit_ratio(self, enactive: EnactiveLoop) -> None:
        """Explore/exploit ratio should be computable."""
        ratio = enactive.explore_exploit_ratio
        assert 0.0 <= ratio <= 1.0

    async def test_cycle_emits_event(self) -> None:
        """A cycle should produce cycle data for event bus."""
        bus = EventBus()
        await bus.start()
        state = AgentState(name="test-cycle")
        loop = EnactiveLoop(agent_state=state, event_bus=bus)
        result = await loop.cycle((0.6, 0.5, 0.2))
        assert "action" in result
        assert "free_energy" in result
        assert result["agent_id"] == state.id
        await bus.stop()


class TestEnactiveLoopExtended:
    """Extended tests for EnactiveLoop covering edge cases and uncovered lines."""

    def test_multiple_perceive_builds_sensory_history(self, enactive: EnactiveLoop) -> None:
        for _ in range(25):
            enactive.perceive((0.5, 0.5, 0.1))
        assert len(enactive._sensory_history) <= 20

    def test_perceive_updates_precision_after_20_calls(self, enactive: EnactiveLoop) -> None:
        old_precision = enactive.enactive.precision.copy()
        for _ in range(22):
            enactive.perceive((0.5, 0.5, 0.1))
        assert not np.array_equal(enactive.enactive.precision, old_precision)

    def test_act_explores_when_free_energy_high(self, enactive: EnactiveLoop, monkeypatch: pytest.MonkeyPatch) -> None:
        enactive.enactive.free_energy = 5.0
        monkeypatch.setattr("random.random", lambda: 0.6)
        action = enactive.act()
        assert action in ("explore_random", "branch_probe", "reverse_direction", "pause_and_sample")

    def test_act_communicates_when_free_energy_high_and_random_high(self, enactive: EnactiveLoop, monkeypatch: pytest.MonkeyPatch) -> None:
        enactive.enactive.free_energy = 5.0
        monkeypatch.setattr("random.random", lambda: 0.9)
        action = enactive.act()
        assert action == "deposit_signal"

    def test_act_move_toward_signal_when_fe_low(self, enactive: EnactiveLoop) -> None:
        enactive.enactive.prediction[0] = 0.5
        enactive.enactive.free_energy = 0.05
        action = enactive.act()
        assert action == "move_toward_signal"

    def test_act_avoid_damage_when_damage_high(self, enactive: EnactiveLoop) -> None:
        enactive.enactive.prediction[0] = 0.2
        enactive.enactive.prediction[2] = 0.7
        enactive.enactive.free_energy = 0.05
        action = enactive.act()
        assert action == "avoid_damage"

    def test_act_exploit_local_when_both_low(self, enactive: EnactiveLoop) -> None:
        enactive.enactive.prediction[0] = 0.2
        enactive.enactive.prediction[2] = 0.3
        enactive.enactive.free_energy = 0.05
        action = enactive.act()
        assert action == "exploit_local"

    def test_multiple_cycles_converge_free_energy(self, enactive: EnactiveLoop) -> None:
        for _ in range(20):
            enactive.perceive((0.7, 0.5, 0.2))
        assert enactive.enactive.free_energy < enactive._free_energy_history[0]

    def test_is_surprised_when_free_energy_above_two(self, enactive: EnactiveLoop) -> None:
        enactive.enactive.free_energy = 3.0
        assert enactive.is_surprised
        enactive.enactive.free_energy = 1.0
        assert not enactive.is_surprised

    def test_action_readiness_increases_with_rising_free_energy(self, enactive: EnactiveLoop) -> None:
        for _ in range(5):
            enactive.perceive((0.5, 0.5, 0.1))
        old_readiness = enactive.enactive.action_readiness
        enactive.perceive((0.9, 0.9, 0.9))
        enactive.act()
        assert enactive.enactive.action_readiness > old_readiness

    def test_explore_exploit_ratio(self, enactive: EnactiveLoop) -> None:
        enactive._action_history = ["move_toward_signal", "exploit_local", "explore_random", "deposit_signal"]
        ratio = enactive.explore_exploit_ratio
        assert ratio == 0.5

    def test_explore_exploit_ratio_empty_history(self, enactive: EnactiveLoop) -> None:
        enactive._action_history = []
        assert enactive.explore_exploit_ratio == 0.5

    def test_action_history_truncates_at_50(self, enactive: EnactiveLoop) -> None:
        for _ in range(60):
            enactive.act()
        assert len(enactive._action_history) == 50

    async def test_cycle_without_event_bus(self) -> None:
        state = AgentState(name="test-cycle-no-bus")
        loop = EnactiveLoop(agent_state=state)
        result = await loop.cycle((0.6, 0.5, 0.2))
        assert "action" in result
        assert "free_energy" in result
        assert "latency_ms" in result

    def test_free_energy_history_truncates_at_100(self, enactive: EnactiveLoop) -> None:
        for _ in range(110):
            enactive.perceive((0.5, 0.5, 0.1))
        assert len(enactive._free_energy_history) == 100

    def test_action_readiness_decreases_with_falling_free_energy(self, enactive: EnactiveLoop) -> None:
        for _ in range(5):
            enactive.perceive((0.5, 0.5, 0.1))
        old_readiness = enactive.enactive.action_readiness
        enactive.perceive((0.5, 0.5, 0.1))
        enactive.act()
        assert enactive.enactive.action_readiness < old_readiness
