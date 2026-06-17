"""⑥ Quantum-Classical Dual-Mode — self-referential switching between quantum exploration and classical execution.

Inspired by:
- Orch-OR theory: microtubule superradiance (0.2ps) > thermal decoherence (10ps)
- Floquet time crystals: THz resonance sustains quantum coherence
- Speed 2026: Recurrence condition — must revisit possibility space after collapse
- Self-referential processing = biological switch between quantum↔classical function

Decision rule:
- Low confidence → Quantum mode (parallel hypothesis exploration)
- High confidence → Classical mode (deterministic execution)
- Self-referential DMN monitoring controls the switch
"""

from src.quantum.dual_mode_engine import DualModeEngine, QuantumState, ClassicalState, ModeType
from src.quantum.self_referential_switch import SelfReferentialSwitch, SwitchReason

__all__ = [
    "DualModeEngine",
    "QuantumState",
    "ClassicalState",
    "ModeType",
    "SelfReferentialSwitch",
    "SwitchReason",
]
