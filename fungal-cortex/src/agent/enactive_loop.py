"""Mechanism ⑪: Enactive Inference — perception↔prediction↔action continuous coupling.

The enactive inference loop replaces the traditional perceive→reason→act pipeline.
Agents do not "reason about" the market — they "couple with" the market.

Core principle (Friston/FEP): Agents minimize free energy by continuously
updating predictions to match sensory input, and acting to make sensory
input match predictions. The agent IS the model — no separate world model.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.agent.agent_state import AgentState
from src.core.event_bus import EventBus
from src.utils.logging import CortexLogger


@dataclass
class EnactiveState:
    """The agent's current enactive coupling state.

    prediction: what the agent expects to sense next
    prediction_error: difference between expected and actual sensory input
    free_energy: variational free energy (surprisal + divergence)
    action_readiness: preparedness to act (0=passive, 1=fully engaged)
    """

    prediction: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    prediction_error: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    free_energy: float = 0.0
    action_readiness: float = 0.5
    precision: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.float64))


class EnactiveLoop:
    """The core enactive inference loop for a single agent.

    Instead of: sense → plan → act
    It is:      predict ⇄ sense ⇄ act  (continuous, bidirectional coupling)

    Two modes:
    - Perception: update internal predictions to better match sensory input
    - Action: act on the world to make sensory input match predictions

    The balance between these is governed by free energy minimization.
    """

    def __init__(
        self,
        agent_state: AgentState,
        event_bus: EventBus | None = None,
        temperature: float = 1.0,
        prediction_horizon: int = 10,
    ) -> None:
        self.agent_state = agent_state
        self.enactive = EnactiveState()
        self._event_bus = event_bus
        self._temperature = temperature
        self._horizon = prediction_horizon
        self._logger = CortexLogger("enactive_loop", agent_state.id[:8])
        self._sensory_history: list[np.ndarray] = []
        self._action_history: list[str] = []
        self._free_energy_history: list[float] = []

    def perceive(self, sensory_input: tuple[float, float, float]) -> None:
        """Update predictions based on sensory input (perception phase).

        This is the 'bottom-up' flow: sensation → prediction update.
        Prediction error = sensed - predicted
        Free energy ∝ |prediction error|² / precision
        """
        sensed = np.array(sensory_input, dtype=np.float64)

        # 1. Compute prediction error
        self.enactive.prediction_error = sensed - self.enactive.prediction

        # 2. Compute variational free energy
        #    F = -ln p(s|pred) + KL(q(state)|p(state))
        #    Approximated as: F = 0.5 * Σ (prediction_error² / precision) + 0.5 * Σ ln(precision)
        precision = np.maximum(self.enactive.precision, 1e-6)
        self.enactive.free_energy = float(
            0.5 * np.sum(self.enactive.prediction_error**2 / precision)
            + 0.5 * np.sum(np.log(precision))
        )

        # 3. Update prediction (gradient descent on free energy)
        #    pred_new = pred_old + α * prediction_error * precision
        learning_rate = 0.1
        self.enactive.prediction = self.enactive.prediction + learning_rate * self.enactive.prediction_error

        # 4. Update precision (inverse variance of prediction errors)
        self._sensory_history.append(sensed)
        if len(self._sensory_history) > 20:
            self._sensory_history = self._sensory_history[-20:]
            errors = np.array([s - p for s, p in zip(self._sensory_history, [self.enactive.prediction] * len(self._sensory_history))])
            self.enactive.precision = 1.0 / np.maximum(np.var(errors, axis=0), 1e-4)

        self._free_energy_history.append(self.enactive.free_energy)
        if len(self._free_energy_history) > 100:
            self._free_energy_history = self._free_energy_history[-100:]

    def act(self) -> str:
        """Select an action to bring sensory input closer to predictions.

        This is the 'top-down' flow: prediction → action → world change.

        Actions are selected by:
        1. If prediction error is low: EXPLOIT (follow the signal)
        2. If prediction error is high: EXPLORE (random action, reduce uncertainty)
        3. Temperature modulates the explore/exploit balance
        """
        fe = self.enactive.free_energy
        r = random.random()

        # Action readiness updates based on free energy trend
        if len(self._free_energy_history) >= 5:
            fe_trend = self._free_energy_history[-1] - self._free_energy_history[-5]
            if fe_trend > 0:  # Free energy increasing → more exploration needed
                self.enactive.action_readiness = min(1.0, self.enactive.action_readiness + 0.1)
            else:  # Free energy decreasing → exploitation working
                self.enactive.action_readiness = max(0.1, self.enactive.action_readiness - 0.05)

        # Action selection
        threshold = 0.5 * self._temperature
        if r < threshold or fe < 0.1:
            # EXPLOIT: move toward predicted signal
            if self.enactive.prediction[0] > 0.3:
                action = "move_toward_signal"
            elif self.enactive.prediction[2] > 0.5:
                action = "avoid_damage"
            else:
                action = "exploit_local"
        elif r < threshold + 0.3:
            # EXPLORE: random movement to reduce uncertainty
            actions = ["explore_random", "branch_probe", "reverse_direction", "pause_and_sample"]
            action = random.choice(actions)
        else:
            # COMMUNICATE: deposit signal for stigmergic coordination
            action = "deposit_signal"

        self._action_history.append(action)
        if len(self._action_history) > 50:
            self._action_history = self._action_history[-50:]

        return action

    async def cycle(self, sensory_input: tuple[float, float, float]) -> dict[str, Any]:
        """Execute one full enactive cycle: perceive → act → broadcast.

        Returns a dict describing what happened, suitable for event bus publishing.
        """
        t0 = time.perf_counter()

        # Perception phase
        self.perceive(sensory_input)

        # Action phase
        action = self.act()

        # Broadcast the cycle to the event bus (for emergence detection)
        cycle_data = {
            "agent_id": self.agent_state.id,
            "action": action,
            "free_energy": self.enactive.free_energy,
            "prediction_error": float(np.linalg.norm(self.enactive.prediction_error)),
            "action_readiness": self.enactive.action_readiness,
            "latency_ms": (time.perf_counter() - t0) * 1000,
        }

        if self._event_bus:
            await self._event_bus.publish_nowait("agent.enactive_cycle", cycle_data, source=self.agent_state.id)

        return cycle_data

    @property
    def is_surprised(self) -> bool:
        """Agent is 'surprised' if free energy exceeds threshold."""
        return self.enactive.free_energy > 2.0

    @property
    def explore_exploit_ratio(self) -> float:
        """Estimate current explore/exploit balance from action history."""
        if not self._action_history:
            return 0.5
        exploit_actions = sum(1 for a in self._action_history[-20:] if "move" in a or "exploit" in a)
        return exploit_actions / min(20, len(self._action_history))
