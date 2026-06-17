"""⑦ Immune Layer — artificial immune system for Fungal Cortex.

Inspired by the adaptive immune system:
- Self/Non-self discrimination (negative selection)
- Dendritic cell danger theory (PAMP + DAMP + co-stimulation)
- Clonal selection (successful detectors proliferate)
- Immune memory (secondary response < 1/10 of primary)

2026 frontier: ImmuneMesh (IEEE), RL-DCA (AAAI 2026), immune-neural hybrid (ASTM 2026).
"""

from src.immune.self_set import SelfSet
from src.immune.negative_selector import NegativeSelector
from src.immune.dendritic_cell import DendriticCell, DCSignal, DCMaturationState
from src.immune.clonal_selector import ClonalSelector
from src.immune.immune_memory import ImmuneMemory, MemoryCell

__all__ = [
    "SelfSet",
    "NegativeSelector",
    "DendriticCell",
    "DCSignal",
    "DCMaturationState",
    "ClonalSelector",
    "ImmuneMemory",
    "MemoryCell",
]
