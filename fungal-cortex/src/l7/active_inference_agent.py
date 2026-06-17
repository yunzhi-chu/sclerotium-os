"""Active Inference Agent — 自由能原理驱动的主动推理Agent.

Biological Metaphor:
  The brain as a "prediction machine" — continuously predicting sensory input
  and updating beliefs via prediction error minimization. Karl Friston's Free
  Energy Principle: any self-organizing system must minimize its variational
  free energy. "Agents don't optimize reward — agents minimize surprise."

  Active Inference = Predictive Coding + Active Inference:
    - Perception: Bayesian belief updating (minimize variational free energy)
    - Action: Select actions to minimize expected free energy
      G(π) = -E_Q[ln P(o|C)] - E_Q[D_KL(Q(s|π) || P(s|π))]
           = Pragmatic value + Epistemic value

Key Innovation (v4.0):
  Full generative model: P(s', o | s, a) with LNN-based transition dynamics.
  Predictive coding perception through gradient descent on free energy.
  Policy selection via expected free energy balancing goal achievement
  (pragmatic) with uncertainty reduction (epistemic). Continuous learning
  updates the generative model parameters from experience.

References:
  - Active Digital Twin (PoliMi 2025-2026): POMDP + Active Inference
  - Active Inference for IoT (ACM 2025): Expected free energy for control
  - Friston (2010): The free-energy principle — a unified brain theory
  - Pretel et al. (ACM 2025): Free energy projection for agent simulation
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from src.config import L7WorldModelConfig, get_config
from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class PolicyType(Enum):
    """Types of policies the agent can evaluate."""
    EXPLORE = "explore"      # High epistemic value — gather information
    EXPLOIT = "exploit"      # High pragmatic value — achieve goal
    BALANCED = "balanced"    # Weighted mix of both
    CAUTIOUS = "cautious"    # Low risk, conservative actions
    AGGRESSIVE = "aggressive"  # High risk, high reward


@dataclass
class Belief:
    """Agent's current belief state — posterior over hidden states.

    Represented as a multivariate Gaussian with diagonal covariance.
    """

    mean: np.ndarray  # Shape: (state_dim,)
    covariance: np.ndarray  # Shape: (state_dim,) — diagonal of covariance matrix
    free_energy: float = 0.0
    precision: float = 1.0  # Inverse variance weight on sensory prediction errors
    timestamp: float = field(default_factory=time.time)

    @property
    def state_dim(self) -> int:
        return len(self.mean)

    def copy(self) -> Belief:
        return Belief(
            mean=self.mean.copy(),
            covariance=self.covariance.copy(),
            free_energy=self.free_energy,
            precision=self.precision,
        )


@dataclass
class Observation:
    """A sensory observation from the environment."""

    data: np.ndarray  # Shape: (observation_dim,)
    modality: str = "generic"  # e.g., "price", "text", "image", "sensor"
    noise_std: float = 0.1
    timestamp: float = field(default_factory=time.time)


@dataclass
class Policy:
    """A candidate action policy — sequence of actions over a horizon."""

    policy_id: str
    policy_type: PolicyType
    actions: list[np.ndarray]  # List of action vectors, length = horizon
    expected_free_energy: float = float("inf")
    pragmatic_value: float = 0.0
    epistemic_value: float = 0.0
    probability: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """A single action selected by the agent."""

    action_vector: np.ndarray  # Shape: (action_dim,)
    selected_policy: Policy
    expected_free_energy: float = 0.0
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class Trajectory:
    """A recorded trajectory of agent-environment interaction."""

    trajectory_id: str
    observations: list[Observation] = field(default_factory=list)
    beliefs: list[Belief] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    free_energies: list[float] = field(default_factory=list)
    final_outcome: str = "unknown"
    length: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class GenerativeModel:
    """The agent's internal world model: P(s', o | s, a).

    Components:
      - Transition model: P(s'|s,a) — predicts next hidden state (LNN-based)
      - Observation model: P(o|s) — predicts sensory data from state
      - Preference prior: P(o|C) — encodes goal states as prior over observations

    The model parameters are updated via gradient descent on free energy.
    """

    # Required: transition and observation matrices
    A: np.ndarray  # (state_dim, state_dim) — state transition matrix
    B: np.ndarray  # (state_dim, action_dim) — control input matrix
    C: np.ndarray  # (obs_dim, state_dim) — observation matrix

    # Optional: noise parameters and preferences
    transition_noise: float = 0.05
    observation_noise: float = 0.1
    preferred_observation: np.ndarray | None = None  # (obs_dim,) — goal state

    @property
    def state_dim(self) -> int:
        return self.A.shape[0]

    @property
    def action_dim(self) -> int:
        return self.B.shape[1]

    @property
    def obs_dim(self) -> int:
        return self.C.shape[0]

    def predict_next_state(self, state: np.ndarray, action: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Predict next state distribution: s' ~ N(A·s + B·a, Σ_trans)."""
        mean = self.A @ state + self.B @ action
        cov = np.full_like(mean, self.transition_noise ** 2)
        return mean, cov

    def predict_observation(self, state: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Predict observation distribution: o ~ N(C·s, Σ_obs)."""
        mean = self.C @ state
        cov = np.full(self.obs_dim, self.observation_noise ** 2)
        return mean, cov

    def compute_free_energy(self, observation: np.ndarray, state_mean: np.ndarray) -> float:
        """Compute variational free energy for a given observation and state belief.

        F = -ln P(o|s) - ln P(s) + ln Q(s)
          ≈ 0.5 * [ ||o - C·s||² / σ²_obs  +  ||s - A·s_prev - B·a||² / σ²_trans ]
        """
        pred_obs = self.C @ state_mean
        obs_error = np.sum(((observation - pred_obs) / self.observation_noise) ** 2)
        # Simplified: just the observation prediction error term
        return float(0.5 * obs_error)


# ═══════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ActiveInferenceConfig:
    """Runtime configuration for Active Inference Agent."""

    hidden_state_dim: int = 128
    observation_dim: int = 64
    action_dim: int = 16
    policy_horizon: int = 5
    epistemic_weight: float = 0.3
    pragmatic_weight: float = 0.7
    learning_rate: float = 0.01
    belief_update_steps: int = 10
    free_energy_tolerance: float = 0.001
    precision_default: float = 1.0
    num_policies: int = 8

    @classmethod
    def from_l7_config(cls, cfg: L7WorldModelConfig) -> ActiveInferenceConfig:
        return cls(
            hidden_state_dim=cfg.ai_hidden_state_dim,
            observation_dim=cfg.ai_observation_dim,
            action_dim=cfg.ai_hidden_state_dim // 8,
            policy_horizon=cfg.ai_policy_horizon,
            epistemic_weight=cfg.ai_epistemic_weight,
            pragmatic_weight=cfg.ai_pragmatic_weight,
            learning_rate=cfg.ai_learning_rate,
            belief_update_steps=cfg.ai_belief_update_steps,
            free_energy_tolerance=cfg.ai_free_energy_tolerance,
            precision_default=cfg.ai_precision_default,
        )


# ═══════════════════════════════════════════════════════════════════════
# Core Agent
# ═══════════════════════════════════════════════════════════════════════


class ActiveInferenceAgent:
    """Active Inference Agent — minimizes free energy through perception and action.

    Core loop:
      1. PERCEIVE: Update beliefs via gradient descent on variational free energy
      2. PLAN: Generate candidate policies and evaluate expected free energy
      3. ACT: Select the policy with minimum expected free energy
      4. LEARN: Update generative model parameters from experience

    The agent balances two drives:
      - Pragmatic: Achieve preferred observations (goals)
      - Epistemic: Reduce uncertainty about the world (explore)
    """

    def __init__(self, config: ActiveInferenceConfig | None = None) -> None:
        cfg = config or ActiveInferenceConfig.from_l7_config(get_config().l7)
        self._config = cfg
        self._logger = CortexLogger(module="l7_active_inference")

        # Initialize generative model with random matrices
        rng = np.random.RandomState(42)
        self._model = GenerativeModel(
            A=rng.randn(cfg.hidden_state_dim, cfg.hidden_state_dim) * 0.1,
            B=rng.randn(cfg.hidden_state_dim, cfg.action_dim) * 0.1,
            transition_noise=0.05,
            C=rng.randn(cfg.observation_dim, cfg.hidden_state_dim) * 0.1,
            observation_noise=0.1,
        )

        self._belief: Belief = Belief(
            mean=np.zeros(cfg.hidden_state_dim),
            covariance=np.ones(cfg.hidden_state_dim) * 0.5,
            precision=cfg.precision_default,
        )

        self._trajectories: list[Trajectory] = []
        self._current_trajectory: Trajectory | None = None
        self._action_count: int = 0
        self._rng = np.random.RandomState(42)

    # ═══════════════════════════════════════════════════════════════════
    # Perception — Bayesian Belief Updating via Predictive Coding
    # ═══════════════════════════════════════════════════════════════════

    def perceive(self, observation: Observation) -> Belief:
        """Update beliefs given a new observation.

        Implements predictive coding: gradient descent on variational free energy.
        The belief (posterior over hidden states) is updated to minimize the
        discrepancy between predicted and actual observations.

        Args:
            observation: New sensory observation

        Returns:
            Updated belief state
        """
        obs_array = observation.data

        # Ensure observation dimension matches
        if len(obs_array) != self._model.obs_dim:
            obs_array = self._project_observation(obs_array, self._model.obs_dim)

        # Gradient descent on free energy
        state = self._belief.mean.copy()
        free_energy = float("inf")

        for step in range(self._config.belief_update_steps):
            # Predicted observation from current state estimate
            pred_obs = self._model.C @ state

            # Prediction error (weighted by sensory precision)
            pred_error = (obs_array - pred_obs) * self._belief.precision

            # Gradient of free energy w.r.t. state
            # dF/ds = -C^T · (o - C·s) · precision + prior_term
            gradient = -self._model.C.T @ pred_error

            # Add prior gradient: s - s_prior (with transition noise)
            prior_precision = 1.0 / self._model.transition_noise ** 2
            gradient += prior_precision * state

            # Update state estimate (gradient descent)
            lr = self._config.learning_rate * (1.0 / (1.0 + 0.1 * step))
            state = state - lr * gradient

            # Compute free energy
            new_fe = self._model.compute_free_energy(obs_array, state)

            # Convergence check
            if abs(new_fe - free_energy) < self._config.free_energy_tolerance:
                free_energy = new_fe
                break
            free_energy = new_fe

        # Update belief
        self._belief = Belief(
            mean=state,
            covariance=np.ones_like(state) * self._model.observation_noise ** 2,
            free_energy=float(free_energy),
            precision=self._belief.precision,
        )

        # Record to current trajectory if active
        if self._current_trajectory is not None:
            self._current_trajectory.observations.append(observation)
            self._current_trajectory.beliefs.append(self._belief)
            self._current_trajectory.free_energies.append(float(free_energy))

        self._logger.info(
            "perceived",
            free_energy=round(self._belief.free_energy, 6),
            surprise=round(float(np.mean((obs_array - self._model.C @ state) ** 2)), 6),
        )
        return self._belief

    @staticmethod
    def _project_observation(obs: np.ndarray, target_dim: int) -> np.ndarray:
        """Project observation to target dimension (pad or truncate)."""
        if len(obs) == target_dim:
            return obs
        if len(obs) > target_dim:
            return obs[:target_dim]
        padded = np.zeros(target_dim)
        padded[:len(obs)] = obs
        return padded

    # ═══════════════════════════════════════════════════════════════════
    # Action Selection — Expected Free Energy Minimization
    # ═══════════════════════════════════════════════════════════════════

    def select_action(self, belief: Belief | None = None, policies: list[Policy] | None = None) -> Action:
        """Select the action that minimizes expected free energy.

        Evaluates each policy over the horizon:
          G(π) = -E_Q[ln P(o|C)] - E_Q[D_KL(Q(s|π) || P(s|π))]
               = Pragmatic (goal achievement) + Epistemic (uncertainty reduction)

        Args:
            belief: Current belief state (defaults to self._belief)
            policies: Candidate policies (auto-generated if None)

        Returns:
            Selected Action with policy and confidence
        """
        belief = belief or self._belief

        if policies is None:
            policies = self._generate_policies(belief)

        # Evaluate expected free energy for each policy
        evaluated: list[Policy] = []
        for policy in policies:
            g_pragmatic, g_epistemic = self._evaluate_policy(policy, belief)
            g_total = (
                self._config.pragmatic_weight * g_pragmatic
                + self._config.epistemic_weight * g_epistemic
            )
            evaluated.append(Policy(
                policy_id=policy.policy_id,
                policy_type=policy.policy_type,
                actions=list(policy.actions),
                expected_free_energy=g_total,
                pragmatic_value=g_pragmatic,
                epistemic_value=g_epistemic,
                metadata=policy.metadata,
            ))

        # Softmax over negative free energies to get probabilities
        energies = np.array([p.expected_free_energy for p in evaluated])
        min_energy = np.min(energies)
        shifted = -(energies - min_energy)  # negative → higher = better
        exp_scores = np.exp(shifted / max(abs(min_energy), 1e-8))
        probs = exp_scores / exp_scores.sum()

        for i, policy in enumerate(evaluated):
            policy.probability = float(probs[i])

        # Select best policy (or sample from softmax)
        best_idx = int(np.argmin(energies))
        best_policy = evaluated[best_idx]

        # First action in the policy sequence
        action_vector = best_policy.actions[0] if best_policy.actions else np.zeros(self._model.action_dim)

        confidence = best_policy.probability
        action = Action(
            action_vector=action_vector,
            selected_policy=best_policy,
            expected_free_energy=best_policy.expected_free_energy,
            confidence=round(confidence, 4),
        )

        self._action_count += 1

        # Record action to current trajectory if active
        if self._current_trajectory is not None:
            self._current_trajectory.actions.append(action)

        self._logger.info(
            "action_selected",
            policy=best_policy.policy_id,
            policy_type=best_policy.policy_type.value,
            g_total=round(best_policy.expected_free_energy, 4),
            pragmatic=round(best_policy.pragmatic_value, 4),
            epistemic=round(best_policy.epistemic_value, 4),
            confidence=round(confidence, 4),
        )
        return action

    def _generate_policies(self, belief: Belief) -> list[Policy]:
        """Generate diverse candidate policies from the current belief."""
        policies: list[Policy] = []
        dim = self._model.action_dim
        horizon = self._config.policy_horizon

        for i in range(self._config.num_policies):
            # Generate policy type cycling through options
            ptype = list(PolicyType)[i % len(PolicyType)]

            # Generate action sequence
            # Different policy types use different generation strategies
            if ptype == PolicyType.EXPLORE:
                # High-entropy random actions
                actions = [self._rng.randn(dim) * 0.5 for _ in range(horizon)]
            elif ptype == PolicyType.EXPLOIT:
                # Directed toward preferred state via action space
                if self._model.preferred_observation is not None:
                    # Compute action that moves state toward goal:
                    # a ≈ pinv(C·B) @ (preferred - C·A·s)
                    CB = self._model.C @ self._model.B  # (obs_dim, action_dim)
                    try:
                        CB_pinv = np.linalg.pinv(CB)  # (action_dim, obs_dim)
                        direction = CB_pinv @ self._model.preferred_observation
                        direction = direction / max(np.linalg.norm(direction), 1e-8) * 0.5
                    except np.linalg.LinAlgError:
                        direction = self._rng.randn(dim) * 0.2
                    actions = [direction * 0.5 / (t + 1) for t in range(horizon)]
                else:
                    actions = [self._rng.randn(dim) * 0.2 for _ in range(horizon)]
            elif ptype == PolicyType.CAUTIOUS:
                # Small, careful actions
                actions = [self._rng.randn(dim) * 0.1 for _ in range(horizon)]
            elif ptype == PolicyType.AGGRESSIVE:
                # Large actions
                actions = [self._rng.randn(dim) * 1.0 for _ in range(horizon)]
            else:  # BALANCED
                actions = [self._rng.randn(dim) * 0.3 for _ in range(horizon)]

            policies.append(Policy(
                policy_id=f"policy-{ptype.value}-{i}",
                policy_type=ptype,
                actions=actions,
            ))

        return policies

    def _evaluate_policy(self, policy: Policy, belief: Belief) -> tuple[float, float]:
        """Evaluate pragmatic and epistemic values for a policy.

        Simulates forward rollouts through the generative model.

        Returns:
            (pragmatic_value, epistemic_value) — both to be minimized
        """
        state = belief.mean.copy()
        pragmatic_total = 0.0
        epistemic_total = 0.0

        for action in policy.actions:
            # Predict next state
            next_mean, next_cov = self._model.predict_next_state(state, action)
            state = next_mean

            # Pragmatic: how close is predicted observation to preferred?
            if self._model.preferred_observation is not None:
                pred_obs = self._model.C @ state
                pragmatic_total += 0.5 * np.sum(
                    ((pred_obs - self._model.preferred_observation) / self._model.observation_noise) ** 2
                )

            # Epistemic: uncertainty in predicted observation (novelty bonus)
            obs_uncertainty = np.mean(next_cov) * np.trace(self._model.C @ self._model.C.T)
            epistemic_total += obs_uncertainty

        pragmatic = pragmatic_total / self._config.policy_horizon
        epistemic = epistemic_total / self._config.policy_horizon

        return float(pragmatic), float(epistemic)

    # ═══════════════════════════════════════════════════════════════════
    # Learning — Generative Model Parameter Updates
    # ═══════════════════════════════════════════════════════════════════

    def learn_from_experience(self, trajectory: Trajectory) -> dict[str, float]:
        """Update generative model parameters from an experience trajectory.

        Uses gradient descent on accumulated free energy to update:
          - A (transition matrix)
          - B (control matrix)
          - C (observation matrix)

        Args:
            trajectory: Complete agent-environment interaction trajectory

        Returns:
            Dict of parameter update magnitudes
        """
        updates: dict[str, float] = {"dA": 0.0, "dB": 0.0, "dC": 0.0}

        if trajectory.length < 2:
            return updates

        lr = self._config.learning_rate

        for t in range(trajectory.length - 1):
            s_t = trajectory.beliefs[t].mean
            s_next = trajectory.beliefs[t + 1].mean
            a_t = trajectory.actions[t].action_vector if t < len(trajectory.actions) else np.zeros(self._model.action_dim)

            # Update A: s' = A·s + B·a → dF/dA = (A·s + B·a - s')·s^T
            pred_next = self._model.A @ s_t + self._model.B @ a_t
            dA = np.outer(pred_next - s_next, s_t)
            self._model.A -= lr * dA
            updates["dA"] += float(np.mean(np.abs(dA)))

            # Update B: dF/dB = (A·s + B·a - s')·a^T
            dB = np.outer(pred_next - s_next, a_t)
            self._model.B -= lr * dB
            updates["dB"] += float(np.mean(np.abs(dB)))

            # Update C: o = C·s → dF/dC = (C·s - o)·s^T
            if t < len(trajectory.observations):
                obs = trajectory.observations[t].data
                if len(obs) != self._model.obs_dim:
                    obs = self._project_observation(obs, self._model.obs_dim)
                pred_obs = self._model.C @ s_t
                dC = np.outer(pred_obs - obs, s_t)
                self._model.C -= lr * dC
                updates["dC"] += float(np.mean(np.abs(dC)))

        # Normalize by trajectory length
        n = trajectory.length - 1
        updates = {k: round(v / max(n, 1), 6) for k, v in updates.items()}

        self._trajectories.append(trajectory)
        self._logger.info("learned_from_experience", **updates)
        return updates

    # ═══════════════════════════════════════════════════════════════════
    # Goal Setting
    # ═══════════════════════════════════════════════════════════════════

    def set_goal(self, preferred_observation: np.ndarray) -> None:
        """Set the agent's goal as a preferred observation.

        The agent will select actions to minimize the distance between
        predicted observations and this preferred state.

        Args:
            preferred_observation: Desired sensory observation vector
        """
        if len(preferred_observation) != self._model.obs_dim:
            preferred_observation = self._project_observation(preferred_observation, self._model.obs_dim)
        self._model.preferred_observation = preferred_observation
        self._logger.info("goal_set", obs_norm=round(float(np.linalg.norm(preferred_observation)), 4))

    # ═══════════════════════════════════════════════════════════════════
    # Trajectory Management
    # ═══════════════════════════════════════════════════════════════════

    def start_trajectory(self, task_id: str | None = None) -> str:
        """Begin recording a new interaction trajectory."""
        traj_id = task_id or self._hash_id(f"traj-{time.time()}")
        self._current_trajectory = Trajectory(trajectory_id=traj_id)
        return traj_id

    def end_trajectory(self, outcome: str = "completed") -> Trajectory | None:
        """End the current trajectory recording."""
        if self._current_trajectory is None:
            return None
        self._current_trajectory.final_outcome = outcome
        self._current_trajectory.length = len(self._current_trajectory.beliefs)
        self._trajectories.append(self._current_trajectory)
        traj = self._current_trajectory
        self._current_trajectory = None
        self._logger.info("trajectory_ended", trajectory_id=traj.trajectory_id, outcome=outcome, length=traj.length)
        return traj

    # ═══════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════

    @property
    def belief(self) -> Belief:
        return self._belief

    @property
    def model(self) -> GenerativeModel:
        return self._model

    @staticmethod
    def _hash_id(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        """Current agent statistics."""
        return {
            "action_count": self._action_count,
            "trajectory_count": len(self._trajectories),
            "current_free_energy": round(self._belief.free_energy, 6),
            "belief_norm": round(float(np.linalg.norm(self._belief.mean)), 4),
            "model_A_norm": round(float(np.linalg.norm(self._model.A)), 4),
            "model_B_norm": round(float(np.linalg.norm(self._model.B)), 4),
            "model_C_norm": round(float(np.linalg.norm(self._model.C)), 4),
            "has_goal": self._model.preferred_observation is not None,
        }

    def reset(self) -> None:
        """Reset agent state (preserves learned model parameters)."""
        self._belief = Belief(
            mean=np.zeros(self._config.hidden_state_dim),
            covariance=np.ones(self._config.hidden_state_dim) * 0.5,
            precision=self._config.precision_default,
        )
        self._trajectories.clear()
        self._current_trajectory = None
        self._action_count = 0
        self._logger.debug("ai_agent_reset")
