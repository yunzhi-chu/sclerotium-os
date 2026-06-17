"""Core layer — event bus, skill registry, unified event bus, emergence, healing, governance.

Phase 5: UnifiedEventBus (Circulatory System)
Phase 6: CrossLayerEmergence + SelfHealing + AutonomousGovernance (Consciousness + Healing)
"""

from __future__ import annotations

# Phase 5: Event Infrastructure
from src.core.event_bus import EventBus, Event
from src.core.unified_event_bus import (
    UnifiedEventBus,
    UnifiedEvent,
    EventPriority,
    StandardEventType,
    EventBacklogStore,
    EventHandler,
)

# Phase 6: Emergence + Self-Healing + Governance
from src.core.cross_layer_emergence import (
    CrossLayerEmergence,
    EmergenceLevel,
    ShiftType,
    EmergenceEvent,
    LayerSignal,
    EcotypeProfile,
)
from src.core.self_healing import (
    SelfHealingOrchestrator,
    HealingPhase,
    WoundSeverity,
    WoundType,
    Wound,
    HealthReport,
    HealingCycle,
)
from src.core.autonomous_governance import (
    AutonomousGovernance,
    ChangeType,
    GovernanceDecision,
    GateResult,
    ChangeProposal,
    GateVerdict,
)

__all__ = [
    # Phase 5: Event Infrastructure
    "EventBus",
    "Event",
    "UnifiedEventBus",
    "UnifiedEvent",
    "EventPriority",
    "StandardEventType",
    "EventBacklogStore",
    "EventHandler",
    # Phase 6.1: Cross-Layer Emergence
    "CrossLayerEmergence",
    "EmergenceLevel",
    "ShiftType",
    "EmergenceEvent",
    "LayerSignal",
    "EcotypeProfile",
    # Phase 6.2: Self-Healing
    "SelfHealingOrchestrator",
    "HealingPhase",
    "WoundSeverity",
    "WoundType",
    "Wound",
    "HealthReport",
    "HealingCycle",
    # Phase 6.3: Autonomous Governance
    "AutonomousGovernance",
    "ChangeType",
    "GovernanceDecision",
    "GateResult",
    "ChangeProposal",
    "GateVerdict",
]
