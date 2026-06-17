"""L5: Stigmergy Field v2.0 + Swarm Self-Organization — 共生集群 (Phase 2 v4.0).

Biological Metaphor:
  Ant colony pheromone field → upgraded to "Photormone + Citation Graph +
  Behavioral Trust" triune system. Harvard RAnts exbodied intelligence —
  two parameters (cooperation_strength × deposition_rate) control the entire
  swarm from construction to dismantling without blueprints or central control.

Key Innovation (v4.0):
  Stigmergy solved 32× more problems than hierarchy in 70-day experiment.
  Network tolerated 45% bad actors with <3% output loss.
  Behavioral trust identified ALL problematic agents before human flagging.
  Norms propagated spontaneously without enforcement or central authority.

Sub-modules:
  - StigmergyFieldV2: Append-only trace grid + citation coordination + behavioral trust
  - SwarmSelfOrganizer: Two-parameter phase portrait + nucleation + phase switching

References (2025-2026):
  - Mycel Network (Zenodo 2026): 70-day 18-agent Stigmergy experiment
  - Harvard RAnts (PRX Life 2026): Exbodied Intelligence, photormone control
  - SwarmHarness (May 2026): SwarmCredit incentive protocol
"""

from __future__ import annotations

from src.l5.stigmergy_field_v2 import (
    StigmergyFieldV2,
    TraceEntry,
    CitationEdge,
    NicheMap,
    TrustScore,
    ResilienceReport,
    NormSpreadReport,
    StigmergyV2Config,
)
from src.l5.swarm_self_organizer import (
    SwarmSelfOrganizer,
    SwarmPhase,
    PhasePortrait,
    NucleationSite,
    PhotormoneField,
    SwarmOrganizerConfig,
)

__all__ = [
    # Stigmergy Field V2
    "StigmergyFieldV2",
    "TraceEntry",
    "CitationEdge",
    "NicheMap",
    "TrustScore",
    "ResilienceReport",
    "NormSpreadReport",
    "StigmergyV2Config",
    # Swarm Self-Organizer
    "SwarmSelfOrganizer",
    "SwarmPhase",
    "PhasePortrait",
    "NucleationSite",
    "PhotormoneField",
    "SwarmOrganizerConfig",
]
