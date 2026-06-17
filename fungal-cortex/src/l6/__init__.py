"""L6: MetaCognition + Genome Evolution Layer.

v3.0: MetaCognitionEngine, AbilityCreationFactory, EmergenceCapture, etc.
v4.0 Phase 4: DarwinianGodelMachine + MAS2ArchitectureCustomizer
"""

# v3.0 exports (existing)
from src.l6.meta_cognition import MetaCognitionEngine, HealthReport as MetaHealthReport
from src.l6.ability_factory import AbilityCreationFactory
from src.l6.emergence_capture import EmergenceCapture
from src.l6.crystallizer import EmergenceCrystallizer
from src.l6.security_gateway import CrossEcoSecurityGateway
from src.l6.rule_evolution import DynamicRuleEvolutionEngine
from src.l6.goal_expander import GlobalGoalExpander
from src.l6.cluster_organizer import ClusterSelfOrganizer
from src.l6.architecture_scanner import ArchitectureScanner, ArchitectureIssue, IssueSeverity
from src.l6.auto_refactor import AutoRefactorEngine, RefactorStatus
from src.l6.sandbox_pipeline import SandboxVerificationPipeline

# v4.0 Phase 4 exports
from src.l6.darwinian_godel_machine import (
    AgentGenome,
    DGMConfig,
    DarwinianGodelMachine,
    Gene,
    ImprovedStrategy,
    Mutation,
    MutationType,
    TransferredAgent,
    ValidationResult,
)
from src.l6.mas2_architecture_customizer import (
    AgentRole,
    ArchitectureBenchmark,
    CustomArchitecture,
    MAS2ArchitectureCustomizer,
    MAS2Config,
    TaskProfile,
)

__all__ = [
    # v3.0
    "MetaCognitionEngine", "MetaHealthReport",
    "AbilityCreationFactory",
    "EmergenceCapture",
    "EmergenceCrystallizer",
    "CrossEcoSecurityGateway",
    "DynamicRuleEvolutionEngine",
    "GlobalGoalExpander",
    "ClusterSelfOrganizer",
    "ArchitectureScanner", "ArchitectureIssue", "IssueSeverity",
    "AutoRefactorEngine", "RefactorStatus",
    "SandboxVerificationPipeline",
    # v4.0 Phase 4
    "DarwinianGodelMachine",
    "DGMConfig",
    "AgentGenome",
    "Gene",
    "Mutation",
    "MutationType",
    "ValidationResult",
    "ImprovedStrategy",
    "TransferredAgent",
    "MAS2ArchitectureCustomizer",
    "MAS2Config",
    "TaskProfile",
    "AgentRole",
    "CustomArchitecture",
    "ArchitectureBenchmark",
]
