"""
业务服务模块 — MiroFish × Mycelium AGI v4.0 六维进化引擎
"""

from .ontology_generator import OntologyGenerator
from .graph_builder import GraphBuilderService
from .text_processor import TextProcessor
from .zep_entity_reader import ZepEntityReader, EntityNode, FilteredEntities
from .oasis_profile_generator import OasisProfileGenerator, OasisAgentProfile
from .simulation_manager import SimulationManager, SimulationState, SimulationStatus
from .simulation_config_generator import (
    SimulationConfigGenerator,
    SimulationParameters,
    AgentActivityConfig,
    TimeSimulationConfig,
    EventConfig,
    PlatformConfig
)
from .simulation_runner import (
    SimulationRunner,
    SimulationRunState,
    RunnerStatus,
    AgentAction,
    RoundSummary
)
from .zep_graph_memory_updater import (
    ZepGraphMemoryUpdater,
    ZepGraphMemoryManager,
    AgentActivity
)
from .simulation_ipc import (
    SimulationIPCClient,
    SimulationIPCServer,
    IPCCommand,
    IPCResponse,
    CommandType,
    CommandStatus
)

# Phase 1: Six-Arena Evolution Engine
from .arenas import (
    ArenaBase,
    ArenaConfig,
    ArenaResult,
    FitnessVector,
    CodingArena,
    CoordinationArena,
    SafetyArena,
    DecisionArena,
    EmergenceArena,
    PerformanceArena,
)
from .arenas.arena_base import FCPIDimension
from .evolution_generation_manager import (
    EvolutionGenerationManager,
    EvolutionConfig,
    EvolutionPhase,
    PanarchyPhase,
    GenerationSnapshot,
)
from .fitness_extractor import (
    EmergentFitnessExtractor,
    FCPIVector,
    ExtractionResult,
)

__all__ = [
    # 原有服务
    'OntologyGenerator',
    'GraphBuilderService',
    'TextProcessor',
    'ZepEntityReader',
    'EntityNode',
    'FilteredEntities',
    'OasisProfileGenerator',
    'OasisAgentProfile',
    'SimulationManager',
    'SimulationState',
    'SimulationStatus',
    'SimulationConfigGenerator',
    'SimulationParameters',
    'AgentActivityConfig',
    'TimeSimulationConfig',
    'EventConfig',
    'PlatformConfig',
    'SimulationRunner',
    'SimulationRunState',
    'RunnerStatus',
    'AgentAction',
    'RoundSummary',
    'ZepGraphMemoryUpdater',
    'ZepGraphMemoryManager',
    'AgentActivity',
    'SimulationIPCClient',
    'SimulationIPCServer',
    'IPCCommand',
    'IPCResponse',
    'CommandType',
    'CommandStatus',
    # Phase 1: 六维进化引擎
    'FCPIDimension',
    'ArenaBase',
    'ArenaConfig',
    'ArenaResult',
    'FitnessVector',
    'CodingArena',
    'CoordinationArena',
    'SafetyArena',
    'DecisionArena',
    'EmergenceArena',
    'PerformanceArena',
    'EvolutionGenerationManager',
    'EvolutionConfig',
    'EvolutionPhase',
    'PanarchyPhase',
    'GenerationSnapshot',
    'EmergentFitnessExtractor',
    'FCPIVector',
    'ExtractionResult',
]

