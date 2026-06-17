"""Tests for L7: ActiveInferenceAgent — 自由能原理主动推理Agent."""

import numpy as np
import pytest

from src.l7.active_inference_agent import (
    Action,
    ActiveInferenceAgent,
    ActiveInferenceConfig,
    Belief,
    GenerativeModel,
    Observation,
    Policy,
    PolicyType,
    Trajectory,
)


@pytest.fixture
def config() -> ActiveInferenceConfig:
    return ActiveInferenceConfig(
        hidden_state_dim=32,
        observation_dim=16,
        action_dim=4,
        policy_horizon=3,
        num_policies=4,
        learning_rate=0.02,
        belief_update_steps=5,
    )


@pytest.fixture
def agent(config: ActiveInferenceConfig) -> ActiveInferenceAgent:
    return ActiveInferenceAgent(config=config)


@pytest.fixture
def observation() -> Observation:
    return Observation(data=np.random.RandomState(42).randn(16) * 0.5, modality="sensor")


class TestAgentInit:
    def test_default_init(self) -> None:
        a = ActiveInferenceAgent()
        assert a.stats["action_count"] == 0
        assert a.stats["trajectory_count"] == 0

    def test_custom_config(self, agent: ActiveInferenceAgent) -> None:
        assert agent._config.hidden_state_dim == 32
        assert agent._config.observation_dim == 16
        assert agent._config.num_policies == 4

    def test_initial_belief(self, agent: ActiveInferenceAgent) -> None:
        belief = agent.belief
        assert isinstance(belief, Belief)
        assert belief.mean.shape == (32,)
        assert belief.free_energy >= 0.0

    def test_generative_model_initialized(self, agent: ActiveInferenceAgent) -> None:
        model = agent.model
        assert isinstance(model, GenerativeModel)
        assert model.A.shape == (32, 32)
        assert model.B.shape == (32, 4)
        assert model.C.shape == (16, 32)


class TestGenerativeModel:
    def test_predict_next_state(self, agent: ActiveInferenceAgent) -> None:
        state = np.zeros(32)
        action = np.zeros(4)
        mean, cov = agent.model.predict_next_state(state, action)
        assert mean.shape == (32,)
        assert cov.shape == (32,)
        assert np.all(cov >= 0)

    def test_predict_observation(self, agent: ActiveInferenceAgent) -> None:
        state = np.ones(32) * 0.5
        mean, cov = agent.model.predict_observation(state)
        assert mean.shape == (16,)
        assert cov.shape == (16,)

    def test_compute_free_energy(self, agent: ActiveInferenceAgent) -> None:
        obs = np.zeros(16)
        state = np.zeros(32)
        fe = agent.model.compute_free_energy(obs, state)
        assert fe >= 0.0

    def test_model_dimensions(self, agent: ActiveInferenceAgent) -> None:
        m = agent.model
        assert m.state_dim == 32
        assert m.action_dim == 4
        assert m.obs_dim == 16


class TestPerception:
    def test_perceive_updates_belief(self, agent: ActiveInferenceAgent, observation: Observation) -> None:
        old_fe = agent.belief.free_energy
        belief = agent.perceive(observation)
        assert isinstance(belief, Belief)
        # Free energy should change after observation
        assert belief.free_energy != 0.0

    def test_perceive_different_modality(self, agent: ActiveInferenceAgent) -> None:
        obs = Observation(data=np.random.RandomState(99).randn(16), modality="price")
        belief = agent.perceive(obs)
        assert isinstance(belief, Belief)

    def test_perceive_projects_different_dim(self, agent: ActiveInferenceAgent) -> None:
        obs = Observation(data=np.random.RandomState(7).randn(10), modality="text")
        belief = agent.perceive(obs)
        assert belief.mean.shape == (32,)  # Should project 10→16 internally


class TestActionSelection:
    def test_select_action(self, agent: ActiveInferenceAgent) -> None:
        action = agent.select_action()
        assert isinstance(action, Action)
        assert action.action_vector.shape == (4,)
        assert action.selected_policy is not None
        assert action.confidence > 0.0

    def test_select_action_with_belief(self, agent: ActiveInferenceAgent, observation: Observation) -> None:
        agent.perceive(observation)
        action = agent.select_action()
        assert isinstance(action, Action)

    def test_select_action_increments_count(self, agent: ActiveInferenceAgent) -> None:
        before = agent.stats["action_count"]
        agent.select_action()
        assert agent.stats["action_count"] == before + 1

    def test_select_action_with_custom_policies(self, agent: ActiveInferenceAgent) -> None:
        policies = [
            Policy(
                policy_id="custom-1", policy_type=PolicyType.EXPLORE,
                actions=[np.zeros(4) for _ in range(3)],
            ),
            Policy(
                policy_id="custom-2", policy_type=PolicyType.EXPLOIT,
                actions=[np.ones(4) * 0.5 for _ in range(3)],
            ),
        ]
        action = agent.select_action(policies=policies)
        assert action.selected_policy.policy_id in ("custom-1", "custom-2")

    def test_policies_have_types(self, agent: ActiveInferenceAgent) -> None:
        action = agent.select_action()
        assert action.selected_policy.policy_type in PolicyType


class TestGoalSetting:
    def test_set_goal(self, agent: ActiveInferenceAgent) -> None:
        goal = np.ones(16) * 0.8
        agent.set_goal(goal)
        assert agent.model.preferred_observation is not None
        assert agent.stats["has_goal"]

    def test_set_goal_projects_dimension(self, agent: ActiveInferenceAgent) -> None:
        goal = np.ones(20) * 0.5
        agent.set_goal(goal)
        assert agent.model.preferred_observation is not None
        assert len(agent.model.preferred_observation) == 16


class TestTrajectoryManagement:
    def test_start_trajectory(self, agent: ActiveInferenceAgent) -> None:
        traj_id = agent.start_trajectory()
        assert traj_id

    def test_end_trajectory(self, agent: ActiveInferenceAgent) -> None:
        agent.start_trajectory("test-traj")
        traj = agent.end_trajectory("success")
        assert traj is not None
        assert traj.trajectory_id == "test-traj"
        assert traj.final_outcome == "success"
        assert agent.stats["trajectory_count"] == 1

    def test_end_trajectory_without_start(self, agent: ActiveInferenceAgent) -> None:
        traj = agent.end_trajectory()
        assert traj is None

    def test_trajectory_records_data(self, agent: ActiveInferenceAgent, observation: Observation) -> None:
        agent.start_trajectory("full-traj")
        agent.perceive(observation)
        agent.select_action()
        traj = agent.end_trajectory("completed")
        assert traj is not None
        assert traj.length > 0


class TestLearning:
    def test_learn_from_experience(self, agent: ActiveInferenceAgent, observation: Observation) -> None:
        agent.start_trajectory("learn-traj")
        agent.perceive(observation)
        agent.select_action()
        agent.perceive(observation)
        traj = agent.end_trajectory()
        assert traj is not None

        updates = agent.learn_from_experience(traj)
        assert "dA" in updates
        assert "dB" in updates
        assert "dC" in updates
        # Updates should be non-zero (model changed)
        assert any(v != 0.0 for v in updates.values())

    def test_learn_short_trajectory(self, agent: ActiveInferenceAgent) -> None:
        traj = Trajectory(trajectory_id="short", length=1)
        updates = agent.learn_from_experience(traj)
        assert updates["dA"] == 0.0  # Not enough data
        assert updates["dB"] == 0.0


class TestPerceptionObservationProjection:
    def test_project_same_dim(self, agent: ActiveInferenceAgent) -> None:
        result = agent._project_observation(np.ones(16), 16)
        assert len(result) == 16
        assert result[0] == 1.0

    def test_project_smaller_dim(self, agent: ActiveInferenceAgent) -> None:
        result = agent._project_observation(np.ones(10), 16)
        assert len(result) == 16
        assert result[0] == 1.0
        assert result[10] == 0.0

    def test_project_larger_dim(self, agent: ActiveInferenceAgent) -> None:
        result = agent._project_observation(np.arange(20), 16)
        assert len(result) == 16


class TestPolicyGeneration:
    def test_generate_policies(self, agent: ActiveInferenceAgent) -> None:
        policies = agent._generate_policies(agent.belief)
        assert len(policies) == agent._config.num_policies
        for p in policies:
            assert len(p.actions) == agent._config.policy_horizon
            assert isinstance(p.policy_type, PolicyType)


class TestReset:
    def test_reset_clears_state(self, agent: ActiveInferenceAgent, observation: Observation) -> None:
        agent.perceive(observation)
        agent.select_action()
        agent.start_trajectory()
        agent.reset()
        assert agent.stats["action_count"] == 0
        assert agent.stats["trajectory_count"] == 0
        # Model parameters should be preserved (not reset)
        assert agent.stats["model_A_norm"] > 0.0
