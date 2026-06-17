"""④ Thermodynamic Engine — non-equilibrium thermodynamics for strategy optimization.

Inspired by 2026 breakthroughs:
- LBNL thermodynamic neurons (Nature Comm 2026): physical variables in 4th-order potential wells
- GENERIC-FNO (2026): Function-space embedding of GENERIC structure, degenerate conditions to machine precision
- NGD-T (Nature Sci Rep 2026): Natural gradient descent minimizes irreversible dissipation
- Spintronic Bayesian hardware (Adv Sci 2026): Magnetic tunnel junction thermal fluctuations
"""

from src.engine.thermodynamic import ThermodynamicEngine, ThermoState
from src.engine.hamiltonian import HamiltonianFlow, ConservativeForce
from src.engine.dissipative import DissipativeFlow, LangevinNoise

__all__ = [
    "ThermodynamicEngine",
    "ThermoState",
    "HamiltonianFlow",
    "ConservativeForce",
    "DissipativeFlow",
    "LangevinNoise",
]
