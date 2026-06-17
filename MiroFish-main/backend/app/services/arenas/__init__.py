"""Six-Arena Evolution Engine — MiroFish × Mycelium AGI v4.0 Integration.

Each arena evaluates one FCPI dimension of the Mycelium genome through
OASIS social simulation, replacing hardcoded fitness functions with
emergent social consensus.

Arenas:
    CodingArena (25%):      代码评审 Agent 社会 → coding_fitness
    CoordinationArena (25%): 多 Agent 协作困境 → coordination_fitness
    SafetyArena (15%):      红蓝对抗 + 免疫军备竞赛 → safety_fitness
    DecisionArena (15%):    长程任务 + 反事实推理 → decision_fitness
    EmergenceArena (10%):   开放环境 + 新奇性驱动 → emergence_fitness
    PerformanceArena (10%): 延迟/吞吐/Token 效率压测 → performance_fitness
"""

from .arena_base import ArenaBase, ArenaConfig, ArenaResult, FitnessVector
from .coding_arena import CodingArena
from .coordination_arena import CoordinationArena
from .safety_arena import SafetyArena
from .decision_arena import DecisionArena
from .emergence_arena import EmergenceArena
from .performance_arena import PerformanceArena

__all__ = [
    "ArenaBase",
    "ArenaConfig",
    "ArenaResult",
    "FitnessVector",
    "CodingArena",
    "CoordinationArena",
    "SafetyArena",
    "DecisionArena",
    "EmergenceArena",
    "PerformanceArena",
]
