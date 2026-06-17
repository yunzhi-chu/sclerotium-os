"""Bridge layer — Fungal Cortex ↔ QuantMind OS integration.

Phase 1 (v4.0): Phase1LiquidBridge for L1→L2 liquid processing pipeline.
Phase 2 (v4.0): Phase2MycorrhizalBridge for L3 debate → L5 stigmergy field.
Phase 3 (v4.0): Phase3CausalOrchestrationBridge for L4 RL conductor + causal debug.
Phase 4 (v4.0): Phase4GenomeTwinBridge for L6 genome evolution + L7 world model.
Phase 5 (v4.0): QuantumBridge (L9↔L3) + ConsciousBridge (L10↔L6).
"""

from src.bridge.l0_l7_pipeline import L0L7Pipeline, LayerState, LayerLevel
from src.bridge.skill_adapter import SkillAdapter, AdaptedSkill
from src.bridge.strategy_dna_loader import StrategyDNALoader, StrategyDNA
from src.bridge.indicator_compiler_bridge import IndicatorCompilerBridge, CompilationResult
from src.bridge.ktd_fin_bridge import KTDFinBridge, BarraAttribution
from src.bridge.final_bench_bridge import FINALBenchBridge, MAERScore
from src.bridge.claim_debate_bridge import ClaimDebateBridge, DebatePosition
from src.bridge.phase1_liquid_bridge import (
    Phase1LiquidBridge,
    Phase1Result,
    ProcessingPath,
)
from src.bridge.phase2_mycorrhizal_bridge import (
    Phase2MycorrhizalBridge,
    Phase2Result,
    DebatePath,
)
from src.bridge.phase3_causal_orch_bridge import (
    Phase3CausalOrchestrationBridge,
    Phase3Result,
    OrchestrationPath,
)
from src.bridge.phase4_genome_twin_bridge import (
    Phase4GenomeTwinBridge,
    Phase4Result,
    EvolutionPath,
)
from src.bridge.quantum_bridge import (
    QuantumBridge,
    QuantumOptimizationResult,
    IsingModel,
)
from src.bridge.conscious_bridge import (
    ConsciousBridge,
    MetaControlParams,
    MetaControlLevel,
    OverrideResult,
)
from src.bridge.skill_agent_compiler import (
    SkillAgentCompiler,
    CompilationReport,
    CompilationStage,
    SkillMetadata,
    AgentSpec,
    DomainManifest,
)

__all__ = [
    "L0L7Pipeline", "LayerState", "LayerLevel",
    "SkillAdapter", "AdaptedSkill",
    "StrategyDNALoader", "StrategyDNA",
    "IndicatorCompilerBridge", "CompilationResult",
    "KTDFinBridge", "BarraAttribution",
    "FINALBenchBridge", "MAERScore",
    "ClaimDebateBridge", "DebatePosition",
    # Phase 1 v4.0
    "Phase1LiquidBridge",
    "Phase1Result",
    "ProcessingPath",
    # Phase 2 v4.0
    "Phase2MycorrhizalBridge",
    "Phase2Result",
    "DebatePath",
    # Phase 3 v4.0
    "Phase3CausalOrchestrationBridge",
    "Phase3Result",
    "OrchestrationPath",
    # Phase 4 v4.0
    "Phase4GenomeTwinBridge",
    "Phase4Result",
    "EvolutionPath",
    # Phase 5 v4.0 — Quantum Bridge (L9↔L3)
    "QuantumBridge",
    "QuantumOptimizationResult",
    "IsingModel",
    # Phase 5 v4.0 — Conscious Bridge (L10↔L6)
    "ConsciousBridge",
    "MetaControlParams",
    "MetaControlLevel",
    "OverrideResult",
    # Phase 6 v4.0 — Skill→Agent Compilation Pipeline
    "SkillAgentCompiler",
    "CompilationReport",
    "CompilationStage",
    "SkillMetadata",
    "AgentSpec",
    "DomainManifest",
]
