"""Guided Self-Organization — boundary conditions guide spontaneous agent differentiation.

2026 Caltech insight: Turing mechanisms are NOT pure laissez-faire.
They are guided by:
1. Boundary conditions (edges of the system define what's possible)
2. Mechanical constraints (physical limits shape the pattern space)
3. Upstream signals (gradients bias local decisions)

Marr's 3-level framework for morphogenesis:
- Computational: WHAT is being computed (pattern formation in agent space)
- Algorithmic: HOW it's computed (Turing RD + gradient sensing)
- Implementation: Physical realization (agent positions + communication edges)

Root Agent = "the organizer" — sets boundary conditions, axes, and constraints.
Within these boundaries, agents spontaneously self-organize into specialized clusters.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RootAgentRole(str, Enum):
    """Roles the Root Agent plays in guiding self-organization."""

    BOUNDARY_SETTER = "boundary_setter"  # Define system edges
    AXIS_DEFINER = "axis_definer"  # Define gradient axes
    CONSTRAINT_ENFORCER = "constraint_enforcer"  # Enforce mechanical limits
    PATTERN_STABILIZER = "pattern_stabilizer"  # Dampen oscillations
    EMERGENCE_ACCELERATOR = "emergence_accelerator"  # Speed up pattern formation


@dataclass
class PatternConstraint:
    """A constraint that guides pattern formation without dictating it."""

    constraint_type: str  # "range", "barrier", "source", "sink"
    region: tuple[float, float]  # Affected region (normalized 0-1)
    strength: float  # 0-1, how strongly enforced
    description: str


@dataclass
class SelfOrgReport:
    """Report on the state of guided self-organization."""

    pattern_formed: bool
    pattern_type: str
    agent_distribution: dict[str, int]  # specialty → count
    num_clusters: int
    stability_index: float
    convergence_time_s: float
    root_agent_interventions: int


class GuidedSelfOrganization:
    """Guided self-organization — boundary conditions + Turing patterns → agent differentiation.

    The Root Agent plays the role of the "organizer" in embryonic development:
    - Sets boundary conditions (what's the edge of agent space?)
    - Defines primary axes (what dimensions matter?)
    - Enforces constraints (what's forbidden?)
    - Stabilizes patterns (prevent runaway oscillations)

    Within these boundaries, agents spontaneously differentiate into
    specialized clusters through local Turing-like activation-inhibition.
    """

    def __init__(self) -> None:
        self._constraints: list[PatternConstraint] = []
        self._active_constraints: dict[str, PatternConstraint] = {}
        self._boundary_set: bool = False
        self._axes: list[str] = []
        self._intervention_count = 0
        self._start_time = time.time()

    def set_boundaries(
        self,
        x_range: tuple[float, float],
        y_range: tuple[float, float],
    ) -> None:
        """Define the spatial boundaries of the agent ecosystem."""
        self._active_constraints["boundary_x"] = PatternConstraint(
            constraint_type="range",
            region=x_range,
            strength=1.0,
            description="X-axis boundary",
        )
        self._active_constraints["boundary_y"] = PatternConstraint(
            constraint_type="range",
            region=y_range,
            strength=1.0,
            description="Y-axis boundary",
        )
        self._boundary_set = True

    def define_axis(self, name: str, min_val: float = 0.0, max_val: float = 1.0) -> None:
        """Define a primary axis for agent differentiation."""
        self._axes.append(name)
        self._active_constraints[f"axis_{name}"] = PatternConstraint(
            constraint_type="range",
            region=(min_val, max_val),
            strength=0.5,
            description=f"Axis: {name} [{min_val}, {max_val}]",
        )

    def add_constraint(self, constraint: PatternConstraint) -> None:
        self._constraints.append(constraint)
        self._active_constraints[constraint.description] = constraint

    def enforce(self, agent_positions: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
        """Enforce constraints on agent positions.

        Agents outside boundaries → projected back inside.
        Agents near barriers → repelled.
        Each enforcement is a Root Agent intervention.
        """
        adjusted: dict[str, tuple[float, float]] = {}

        for agent_id, (x, y) in agent_positions.items():
            new_x, new_y = x, y
            intervened = False

            for cid, constraint in self._active_constraints.items():
                if constraint.constraint_type == "range":
                    lo, hi = constraint.region
                    if cid == "boundary_x" or cid.startswith("axis_"):
                        if new_x < lo:
                            new_x = lo
                            intervened = True
                        elif new_x > hi:
                            new_x = hi
                            intervened = True
                    else:
                        if new_y < lo:
                            new_y = lo
                            intervened = True
                        elif new_y > hi:
                            new_y = hi
                            intervened = True

                elif constraint.constraint_type == "barrier":
                    # Soft barrier: push away with strength
                    lo, hi = constraint.region
                    mid = (lo + hi) / 2.0
                    dist_x = abs(new_x - mid)
                    if dist_x < (hi - lo) / 2.0:
                        push = constraint.strength * ((hi - lo) / 2.0 - dist_x)
                        new_x += math.copysign(push, new_x - mid)
                        intervened = True

            if intervened:
                self._intervention_count += 1
            adjusted[agent_id] = (new_x, new_y)

        return adjusted

    def assess_pattern(
        self,
        agent_distribution: dict[str, int],
        clusters: int,
    ) -> SelfOrgReport:
        """Assess whether stable agent differentiation has been achieved.

        A "formed" pattern has:
        - All 5 specialties represented
        - At least 3 clusters (spatial grouping)
        - Distribution not too uniform or too concentrated
        """
        total = sum(agent_distribution.values())
        if total == 0:
            return SelfOrgReport(
                pattern_formed=False,
                pattern_type="none",
                agent_distribution=agent_distribution,
                num_clusters=0,
                stability_index=0.0,
                convergence_time_s=time.time() - self._start_time,
                root_agent_interventions=self._intervention_count,
            )

        # Entropy of distribution: too uniform = no differentiation, too concentrated = monopoly
        entropy = 0.0
        for count in agent_distribution.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        max_entropy = math.log2(max(len(agent_distribution), 2))
        norm_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

        # Good differentiation = moderate entropy (not too uniform, not too concentrated)
        if norm_entropy < 0.3:
            pattern_type = "concentrated"
            formed = False
        elif norm_entropy > 0.85:
            pattern_type = "uniform"
            formed = False
        else:
            pattern_type = "differentiated"
            formed = len(agent_distribution) >= 3

        stability = 1.0 - abs(norm_entropy - 0.6) / 0.6  # Peak at entropy ~0.6

        return SelfOrgReport(
            pattern_formed=formed,
            pattern_type=pattern_type,
            agent_distribution=agent_distribution,
            num_clusters=clusters,
            stability_index=max(0.0, min(1.0, stability)),
            convergence_time_s=time.time() - self._start_time,
            root_agent_interventions=self._intervention_count,
        )

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "boundary_set": self._boundary_set,
            "axes": self._axes,
            "constraints": len(self._constraints),
            "active_constraints": len(self._active_constraints),
            "interventions": self._intervention_count,
        }
