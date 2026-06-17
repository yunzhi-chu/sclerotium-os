"""Tests for L9: HybridQuantumAgent — 混合量子-经典Agent."""

import numpy as np
import pytest

from src.l9.hybrid_quantum_agent import (
    AnnealingSolution,
    ClassicalCritic,
    HybridQuantumAgent,
    HybridQuantumConfig,
    QuantumActor,
    QuantumTrainingResult,
)


@pytest.fixture
def config() -> HybridQuantumConfig:
    return HybridQuantumConfig(qubits=6, vqc_layers=2, anneal_reads=100)


@pytest.fixture
def agent(config: HybridQuantumConfig) -> HybridQuantumAgent:
    return HybridQuantumAgent(config=config)


class TestAgentInit:
    def test_default_init(self) -> None:
        a = HybridQuantumAgent()
        assert a.stats["qubits"] == 8
        assert a.stats["vqc_layers"] == 4

    def test_custom_config(self, agent: HybridQuantumAgent) -> None:
        assert agent._config.qubits == 6
        assert agent._config.vqc_layers == 2


class TestQuantumActor:
    def test_encode_state(self) -> None:
        actor = QuantumActor(num_qubits=4, num_layers=2)
        state = np.array([0.5, -0.3, 0.8, 0.1])
        psi = actor.encode_state(state)
        assert psi.shape == (16,)  # 2^4
        assert np.iscomplexobj(psi)

    def test_encode_state_larger_than_qubits(self) -> None:
        actor = QuantumActor(num_qubits=4, num_layers=2)
        state = np.arange(10)
        psi = actor.encode_state(state)
        assert psi.shape == (16,)

    def test_apply_variational_layers(self) -> None:
        actor = QuantumActor(num_qubits=4, num_layers=2)
        psi = np.ones(16, dtype=np.complex128) / 4.0
        psi = actor.apply_variational_layers(psi)
        assert psi.shape == (16,)
        # State should be modified
        assert not np.allclose(psi, np.ones(16, dtype=np.complex128) / 4.0)

    def test_measure_policy(self) -> None:
        actor = QuantumActor(num_qubits=4, num_layers=2)
        psi = np.ones(16, dtype=np.complex128) / 4.0
        dist = actor.measure_policy(psi, action_dim=4)
        assert dist.probabilities.shape == (4,)
        assert abs(np.sum(dist.probabilities) - 1.0) < 0.01
        assert dist.entropy > 0.0


class TestClassicalCritic:
    def test_evaluate(self) -> None:
        critic = ClassicalCritic(state_dim=8, hidden_dim=32)
        state = np.ones(8) * 0.5
        value = critic.evaluate(state)
        assert isinstance(value, float)

    def test_evaluate_different_dim(self) -> None:
        critic = ClassicalCritic(state_dim=8, hidden_dim=32)
        value = critic.evaluate(np.ones(10))
        assert isinstance(value, float)


class TestActionSelection:
    def test_select_action(self, agent: HybridQuantumAgent) -> None:
        state = np.random.RandomState(42).randn(64)
        action, dist = agent.select_action(state)
        assert 0 <= action < 4
        assert dist.probabilities.shape == (4,)

    def test_evaluate_state(self, agent: HybridQuantumAgent) -> None:
        value = agent.evaluate_state(np.ones(64))
        assert isinstance(value, float)


class TestHybridTraining:
    def test_train_hybrid(self, agent: HybridQuantumAgent) -> None:
        result = agent.train_hybrid(episodes=20)
        assert isinstance(result, QuantumTrainingResult)
        assert result.episodes == 20
        assert result.avg_reward != 0.0

    def test_training_records_history(self, agent: HybridQuantumAgent) -> None:
        agent.train_hybrid(episodes=10)
        assert agent.stats["training_runs"] == 1


class TestQuantumAnnealing:
    def test_quantum_anneal_optimize(self, agent: HybridQuantumAgent) -> None:
        solution = agent.quantum_anneal_optimize(param_dim=8)
        assert isinstance(solution, AnnealingSolution)
        assert solution.solution_vector.shape == (8,)
        assert solution.reads == 100

    def test_annealing_multiple_runs(self, agent: HybridQuantumAgent) -> None:
        s1 = agent.quantum_anneal_optimize(param_dim=6)
        s2 = agent.quantum_anneal_optimize(param_dim=6)
        # Solutions may differ due to stochasticity
        assert s1.energy != float("inf")


class TestReset:
    def test_reset_clears_history(self, agent: HybridQuantumAgent) -> None:
        agent.train_hybrid(episodes=5)
        agent.reset()
        assert agent.stats["training_runs"] == 0
