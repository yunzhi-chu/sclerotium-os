"""⑩ Synaptive Multilevel Evolution — 3-tier co-evolution across timescales.

Inspired by:
- Major evolutionary transitions (Szathmáry): each transition creates a new "individuality" level
- Synaptation (Bielawski 2026): cross-level selection covariance produces adaptive complexity
  even without shared genetics (multi-species symbiosis)
- Watson & Szathmáry: one level's unsupervised learning "pre-trains" the next higher level
- Evo-Ego problem: individual-group interest misalignment → enforcement agent (second-level public good)

L1: Parameter Evolution (minutes) — genetic algorithm + Bayesian optimization
L2: Agent Evolution (days) — success→proliferate, failure→apoptose
L3: Architecture Evolution (weeks) — Synaptation-driven system-level restructuring
"""

from src.evolution.parameter_evolver import ParameterEvolver, EvolutionGeneration, Chromosome
from src.evolution.agent_evolver import AgentEvolver, AgentFitness, AgentGenome
from src.evolution.architecture_evolver import ArchitectureEvolver, ArchitectureGenome, SynaptationEvent
from src.evolution.enforcement_agent import EnforcementAgent, EgoDeviation, EnforcementAction

__all__ = [
    "ParameterEvolver",
    "EvolutionGeneration",
    "Chromosome",
    "AgentEvolver",
    "AgentFitness",
    "AgentGenome",
    "ArchitectureEvolver",
    "ArchitectureGenome",
    "SynaptationEvent",
    "EnforcementAgent",
    "EgoDeviation",
    "EnforcementAction",
]
