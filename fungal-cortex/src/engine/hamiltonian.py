"""Hamiltonian Flow — reversible, energy-conserving dynamics.

L(x)·∇E(x): The Poisson (skew-symmetric) operator applied to the energy gradient
produces conservative dynamics that preserve the symplectic structure.

In finance: this represents deterministic strategy execution — known rules,
no randomness, energy conserved across the system's phase space.

Degeneracy condition: L(x)·∇S(x) = 0 (reversible flow does not produce entropy).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ConservativeForce:
    """A conservative (potential-based) force field."""

    name: str
    potential: Callable[[float], float]  # V(x): potential energy function
    gradient: Callable[[float], float]  # -dV/dx: conservative force
    description: str = ""


class HamiltonianFlow:
    """Reversible Hamiltonian dynamics — symplectic integrator.

    Hamilton's equations:
        dq/dt = ∂H/∂p  (position update from momentum)
        dp/dt = -∂H/∂q  (momentum update from position)

    Energy H(p,q) is exactly conserved in the continuous limit.
    Symplectic Euler integrator preserves the symplectic 2-form.
    """

    def __init__(self, mass: float = 1.0, damping: float = 0.0) -> None:
        self._mass = mass
        self._damping = damping  # 0 = purely conservative
        self._position = 0.0
        self._momentum = 0.0
        self._forces: list[ConservativeForce] = []
        self._energy = 0.0
        self._step_count = 0

    def add_force(self, force: ConservativeForce) -> None:
        self._forces.append(force)

    def total_force(self, position: float) -> float:
        """Sum all conservative forces at given position."""
        return sum(f.gradient(position) for f in self._forces)

    def total_potential(self, position: float) -> float:
        """Sum all potential energies at given position."""
        return sum(f.potential(position) for f in self._forces)

    def step(self, dt: float = 0.01) -> dict[str, float]:
        """Symplectic Euler step (explicit in momentum, implicit in position).

        p_{n+1} = p_n - dt * ∂H/∂q(p_n, q_n)  (momentum update)
        q_{n+1} = q_n + dt * ∂H/∂p(p_{n+1}, q_n)  (position update)
        """
        self._step_count += 1

        # Compute force at current position
        force = self.total_force(self._position)

        # Momentum half-step
        self._momentum += 0.5 * dt * force

        # Optional damping (breaks exact energy conservation)
        if self._damping > 0:
            self._momentum *= math.exp(-self._damping * dt)

        # Position update
        self._position += dt * self._momentum / self._mass

        # Compute force at new position
        force_new = self.total_force(self._position)

        # Momentum half-step
        self._momentum += 0.5 * dt * force_new

        # Compute energy: H = T(p) + V(q)
        kinetic = 0.5 * self._momentum ** 2 / self._mass
        potential = self.total_potential(self._position)
        self._energy = kinetic + potential

        return {
            "position": self._position,
            "momentum": self._momentum,
            "kinetic_energy": kinetic,
            "potential_energy": potential,
            "total_energy": self._energy,
        }

    def set_state(self, position: float, momentum: float = 0.0) -> None:
        self._position = position
        self._momentum = momentum

    @property
    def state(self) -> dict[str, float]:
        return {
            "position": self._position,
            "momentum": self._momentum,
            "energy": self._energy,
        }

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "position": self._position,
            "momentum": self._momentum,
            "energy": self._energy,
            "mass": self._mass,
            "damping": self._damping,
            "forces": len(self._forces),
            "step_count": self._step_count,
        }
