"""L8: Self-Referential Evolution Compiler (Phase 5 v4.0).

Biological Metaphor:
  Gödel's Incompleteness — any sufficiently powerful system must transcend
  itself to improve. The Self-Referential Compiler recursively rewrites the
  system's own code, verified by safety invariants.
"""

from src.l8.self_referential_compiler import (
    CyclePhase,
    FileChromosome,
    ImprovementReport,
    SafetyVerdict,
    SelfReferentialCompiler,
    SRCConfig,
    SystemGenome,
)

__all__ = [
    "SelfReferentialCompiler",
    "SRCConfig",
    "SystemGenome",
    "FileChromosome",
    "SafetyVerdict",
    "ImprovementReport",
    "CyclePhase",
]
