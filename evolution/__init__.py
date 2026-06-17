"""Sclerotium OS — 进化引擎 (黏菌探索场)。

基于真实用户行为数据的 FCPI 六维进化系统:
  - FCPITracker: 六维适应度实时追踪
  - StrategyGenome: 可进化策略参数基因组
  - EvolutionLoop: 评估→变异→选择进化闭环
"""

from evolution.fcpi_tracker import FCPITracker, FCPIVector, FCPIDimension
from evolution.strategy_genome import StrategyGenome, GenomeConfig
from evolution.evolution_loop import EvolutionLoop, EvolutionState

__all__ = [
    "FCPITracker", "FCPIVector", "FCPIDimension",
    "StrategyGenome", "GenomeConfig",
    "EvolutionLoop", "EvolutionState",
]
