"""⑫ Panarchy Resilience — nested adaptive cycles with cross-scale connections.

Inspired by Holling & Gunderson's Panarchy theory:
- Adaptive cycle: r(exploitation) → K(conservation) → Ω(release) → α(reorganization)
- Nested across timescales: signal(min) → strategy(day) → agent(week) → system(month)
- Revolt: small fast perturbation → cascades up → triggers larger-scale collapse
- Remember: large-scale memory → constrains smaller-scale recovery
- Ecological resilience ≠ engineering resilience — stability can mean fragility

Key insight: intermediate disturbance maximizes diversity.
Too little disturbance → K-phase rigidity → catastrophic Ω collapse.
Too much disturbance → can't build structure → perpetual α chaos.
"""

from src.panarchy.adaptive_cycle import AdaptiveCycle, CyclePhase, CycleState
from src.panarchy.panarchy_controller import PanarchyController, CrossScaleSignal, ScaleLevel
from src.panarchy.resilience_metrics import ResilienceMetrics, ResilienceProfile

__all__ = [
    "AdaptiveCycle",
    "CyclePhase",
    "CycleState",
    "PanarchyController",
    "CrossScaleSignal",
    "ScaleLevel",
    "ResilienceMetrics",
    "ResilienceProfile",
]
