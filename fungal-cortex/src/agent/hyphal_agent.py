"""Mechanism ②: Hyphal Agent — fungus-inspired agent with Branch/Fuse/Apoptose/Myelinate.

Core lifecycle operations inspired by fungal mycelium:
- Branch: create new agents from high-gradient regions
- Fuse: merge two agents' skill sets (anastomosis)
- Apoptose: programmed death of underperforming agents
- Myelinate: reinforce high-traffic communication paths
"""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

from src.agent.agent_state import AgentState, Lifecycle, Specialty
from src.utils.logging import CortexLogger

if TYPE_CHECKING:
    from src.field.stigmergy_field import StigmergyField


class HyphalAgent:
    """Base agent class operating on the Stigmergy Field.

    Each agent:
    - Senses local field gradients (signal, nutrient, damage)
    - Moves up the signal gradient (chemotaxis)
    - Branches when nutrients are abundant
    - Apoptoses when nutrition falls below threshold
    - Myelinates high-traffic connections to other agents
    """

    def __init__(
        self,
        state: AgentState | None = None,
        field: "StigmergyField | None" = None,
        branch_prob: float = 0.05,
        apoptose_threshold: float = 0.1,
        myelinate_threshold: int = 100,
    ) -> None:
        self.state = state or AgentState()
        self.field = field
        self.branch_prob = branch_prob
        self.apoptose_threshold = apoptose_threshold
        self.myelinate_threshold = myelinate_threshold
        self._logger = CortexLogger("hyphal_agent", self.state.id[:8])
        self._message_counts: dict[str, int] = {}  # neighbor_id → message count
        self._children: list[str] = []

    def sense(self) -> tuple[float, float, float]:
        """Read local field values at current position."""
        if self.field is None:
            return 0.0, 0.5, 0.0
        i, j = self.state.position
        return self.field.sense(i, j)

    def decide_direction(self) -> tuple[int, int]:
        """Choose movement direction based on signal gradient.

        Combines:
        - Signal gradient (chemotaxis — move toward high signal)
        - Damage avoidance (move away from high damage)
        - Random exploration (noise proportional to inverse nutrient)
        """
        if self.field is None:
            return 0, 0

        i, j = self.state.position
        s, n, d = self.sense()
        gx, gy = self.field.gradient_at(i, j)

        # Damage avoidance: steer away from damage
        # Compute damage gradient similarly
        d_right = self.field.D[min(i + 1, self.field.geom.width - 1), j]
        d_left = self.field.D[max(i - 1, 0), j]
        d_down = self.field.D[i, min(j + 1, self.field.geom.height - 1)]
        d_up = self.field.D[i, max(j - 1, 0)]
        dgx = (d_right - d_left) / (2 * self.field.geom.dx)
        dgy = (d_down - d_up) / (2 * self.field.geom.dy)

        # Combined direction: signal gradient - damage gradient + noise
        dir_x = gx - 0.3 * dgx + random.uniform(-0.1, 0.1) * (1.0 - n)
        dir_y = gy - 0.3 * dgy + random.uniform(-0.1, 0.1) * (1.0 - n)

        # Discretize to grid movement (±1, 0)
        dx = 1 if dir_x > 0.01 else (-1 if dir_x < -0.01 else 0)
        dy = 1 if dir_y > 0.01 else (-1 if dir_y < -0.01 else 0)

        return dx, dy

    def should_branch(self) -> bool:
        """Decide whether to branch (create child agent).

        Branch probability ∝ local_nutrient × global_branch_prob.
        Higher nutrients = more branching.
        """
        s, n, d = self.sense()
        return random.random() < self.branch_prob * n * 2

    def should_apoptose(self) -> bool:
        """Decide whether to apoptose (programmed death)."""
        s, n, d = self.sense()
        if n < self.apoptose_threshold:
            return True
        if self.state.nutrition < self.apoptose_threshold:
            return True
        return False

    def should_myelinate(self, target_id: str) -> bool:
        """Decide whether to myelinate (reinforce) a connection."""
        count = self._message_counts.get(target_id, 0)
        return count >= self.myelinate_threshold

    async def step(self) -> AgentState:
        """Execute one agent step: sense → decide → act → update state."""
        if not self.state.is_alive:
            return self.state

        # 1. Sense
        s, n, d = self.sense()

        # 2. Move (chemotaxis)
        dx, dy = self.decide_direction()
        i, j = self.state.position
        new_i = max(0, min(self.field.geom.width - 1, i + dx)) if self.field else i
        new_j = max(0, min(self.field.geom.height - 1, j + dy)) if self.field else j
        self.state = self.state.move(new_i, new_j)

        # 3. Deposit signal (pheromone) at new position
        if self.field:
            self.field.deposit_signal(new_i, new_j, amount=0.05 * self.state.activity)

        # 4. Consume nutrients
        basal_cost = 0.001
        activity_cost = 0.01 * self.state.activity
        self.state = self.state.starve(basal_cost + activity_cost)
        if self.field:
            self.field.consume_nutrient(new_i, new_j, amount=basal_cost)

        # 5. Check apoptosis
        if self.should_apoptose():
            self.state = self.state.apoptose()
            self._logger.info("agent_apoptosing", agent_id=self.state.id[:8], nutrition=self.state.nutrition)

        # 6. Update activity (decay toward zero)
        new_activity = self.state.activity * 0.95
        self.state = self.state.update_activity(new_activity)

        return self.state

    def branch_offspring_state(self, child_name: str) -> AgentState:
        """Create an initial state for a child (branched) agent."""
        return AgentState(
            name=child_name,
            lifecycle=Lifecycle.SPAWNING,
            specialty=self.state.specialty,
            position=self.state.position,
            nutrition=self.state.nutrition * 0.5,
            generation=self.state.generation + 1,
            skills=self.state.skills,
        )

    def record_message(self, target_id: str) -> None:
        """Record a message to another agent (for myelination tracking)."""
        self._message_counts[target_id] = self._message_counts.get(target_id, 0) + 1

    @property
    def is_alive(self) -> bool:
        return self.state.is_alive

    @property
    def connection_strength(self) -> dict[str, int]:
        """Return current connection strengths to all neighbors."""
        return dict(self._message_counts)
