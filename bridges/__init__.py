"""Sclerotium OS — Integration Bridges.

Bridge adapters that unify the two existing projects behind clean interfaces:
  - FungalBridge    → fungal-cortex (EventBus, SkillRegistry, L6 DGM, Scanner, ...)
  - MiroFishBridge  → MiroFish Phase 1 (EvolutionManager, Arenas, FCPI, ...)
"""

from .fungal_bridge import FungalBridge
from .mirofish_bridge import MiroFishBridge

__all__ = ["FungalBridge", "MiroFishBridge"]
