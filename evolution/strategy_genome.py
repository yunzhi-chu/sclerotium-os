"""Strategy Genome — 可进化策略参数基因组。

基因组编码了系统所有可调参数，进化循环通过变异这些参数
来优化 FCPI 适应度。

基因组结构:
  genes = {
      "nudge_threshold_work": 0.5,     # 工作模式通知阈值
      "nudge_threshold_sleep": 0.9,    # 睡眠模式通知阈值
      "pyloric_interval": 30.0,        # 幽门节律间隔 (秒)
      "gastric_interval": 3600.0,      # 胃磨节律间隔 (秒)
      "consolidation_threshold": 20,   # 整合阈值
      "forget_days_episodic": 90,      # 情景记忆保留天数
      "ema_learning_rate": 0.05,       # EMA 学习率
      "search_top_k": 10,              # 搜索返回数
  }

变异操作:
  - Gaussian: 添加高斯噪声 (连续参数)
  - Flip: 翻转离散参数
  - Scaling: 缩放参数 (×0.5–×2.0)
  - Crossover: 与另一基因组交换片段

参考:
  - MiroFish DGM (5种变异)
  - fungal-cortex l6/darwinian_godel_machine
"""

from __future__ import annotations

import copy
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class GeneType(Enum):
    """基因参数类型。"""
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"


@dataclass(frozen=True)
class GeneSpec:
    """基因规格定义 (不可变)。"""
    name: str
    gene_type: GeneType
    default: Any
    min_val: Any = None
    max_val: Any = None
    mutation_rate: float = 0.1      # 变异概率
    mutation_strength: float = 0.1  # 变异强度 (float 参数的标准差比例)


@dataclass(frozen=True)
class GenomeConfig:
    """基因组配置 (不可变)。"""
    genes: tuple[GeneSpec, ...]
    version: int = 1
    description: str = ""


@dataclass(frozen=True)
class MutationRecord:
    """变异记录 (不可变)。"""
    gene_name: str
    old_value: Any
    new_value: Any
    mutation_type: str  # "gaussian"/"flip"/"scaling"/"crossover"
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# 默认基因组定义
# ═══════════════════════════════════════════════════════════════

DEFAULT_GENES = (
    GeneSpec("nudge_threshold_work", GeneType.FLOAT, 0.5, 0.1, 0.9, 0.1, 0.1),
    GeneSpec("nudge_threshold_sleep", GeneType.FLOAT, 0.9, 0.5, 1.0, 0.05, 0.05),
    GeneSpec("nudge_threshold_game", GeneType.FLOAT, 0.85, 0.5, 1.0, 0.05, 0.05),
    GeneSpec("pyloric_interval", GeneType.FLOAT, 30.0, 5.0, 300.0, 0.1, 0.15),
    GeneSpec("gastric_interval", GeneType.FLOAT, 3600.0, 600.0, 21600.0, 0.05, 0.1),
    GeneSpec("consolidation_threshold_working", GeneType.INT, 20, 5, 100, 0.1, 0.2),
    GeneSpec("consolidation_threshold_episodic", GeneType.INT, 50, 10, 200, 0.1, 0.2),
    GeneSpec("forget_days_episodic", GeneType.INT, 90, 30, 365, 0.05, 0.1),
    GeneSpec("forget_days_semantic", GeneType.INT, 180, 60, 730, 0.05, 0.1),
    GeneSpec("ema_learning_rate", GeneType.FLOAT, 0.05, 0.01, 0.3, 0.1, 0.2),
    GeneSpec("search_top_k", GeneType.INT, 10, 3, 50, 0.1, 0.15),
    GeneSpec("nudge_cooldown_work", GeneType.FLOAT, 300.0, 60.0, 1800.0, 0.1, 0.15),
    GeneSpec("notify_max_per_hour", GeneType.INT, 8, 1, 30, 0.1, 0.15),
    GeneSpec("tray_blink_interval", GeneType.FLOAT, 1.0, 0.3, 3.0, 0.1, 0.1),
    GeneSpec("daily_digest_hour", GeneType.INT, 21, 18, 23, 0.05, 0.05),
    GeneSpec("insight_min_confidence", GeneType.FLOAT, 0.3, 0.1, 0.8, 0.1, 0.15),
)


DEFAULT_CONFIG = GenomeConfig(
    genes=DEFAULT_GENES,
    version=1,
    description="Sclerotium OS v4.0 默认基因组 — 16 个可进化参数",
)


# ═══════════════════════════════════════════════════════════════
# StrategyGenome
# ═══════════════════════════════════════════════════════════════

class StrategyGenome:
    """可进化策略基因组。

    使用方式:
        genome = StrategyGenome()
        genome.set("nudge_threshold_work", 0.6)
        mutant = genome.mutate()  # 随机变异
        child = genome.crossover(other_genome)  # 交叉
        params = genome.to_dict()  # 导出为字典供其他模块使用
    """

    def __init__(
        self,
        config: GenomeConfig | None = None,
        seed: int | None = None,
    ) -> None:
        self._config = config or DEFAULT_CONFIG
        self._values: dict[str, Any] = {}
        self._specs: dict[str, GeneSpec] = {}

        for spec in self._config.genes:
            self._specs[spec.name] = spec
            self._values[spec.name] = spec.default

        self._mutation_history: list[MutationRecord] = []
        self._generation: int = 0
        self._fitness: float = 0.5
        self._rng = random.Random(seed)

    # ═══════════════════════════════════════════════════════
    # 基因读写
    # ═══════════════════════════════════════════════════════

    def get(self, name: str) -> Any | None:
        """获取基因值。"""
        return self._values.get(name)

    def set(self, name: str, value: Any) -> bool:
        """设置基因值 (自动清洗)。"""
        spec = self._specs.get(name)
        if spec is None:
            return False
        self._values[name] = self._clamp(value, spec)
        return True

    def to_dict(self) -> dict[str, Any]:
        """导出为字典。"""
        return dict(self._values)

    def gene_names(self) -> list[str]:
        """所有基因名称。"""
        return list(self._values.keys())

    # ═══════════════════════════════════════════════════════
    # 变异
    # ═══════════════════════════════════════════════════════

    def mutate(
        self, num_mutations: int | None = None, strength: float = 1.0,
    ) -> StrategyGenome:
        """创建变异后的新基因组 (不可变模式)。

        Args:
            num_mutations: 变异基因数 (None=随机1-3个)
            strength: 全局变异强度乘数

        Returns:
            新的 StrategyGenome 实例
        """
        mutant = self._clone()
        mutant._generation = self._generation + 1

        genes = list(self._specs.values())
        if num_mutations is None:
            num_mutations = self._rng.randint(1, min(3, len(genes)))

        targets = self._rng.sample(genes, min(num_mutations, len(genes)))

        for spec in targets:
            if self._rng.random() < spec.mutation_rate * strength:
                old_val = mutant._values[spec.name]
                new_val = self._apply_mutation(spec, old_val, strength)
                mutant._values[spec.name] = new_val
                mutant._mutation_history.append(MutationRecord(
                    gene_name=spec.name,
                    old_value=old_val,
                    new_value=new_val,
                    mutation_type=self._choose_mutation_type(spec),
                ))

        return mutant

    def crossover(self, other: StrategyGenome) -> StrategyGenome:
        """与另一个基因组交叉, 产生子代。

        随机选择每个基因来自父方或母方。
        """
        child = self._clone()
        child._generation = max(self._generation, other._generation) + 1

        for name in self._values:
            if self._rng.random() < 0.5:
                other_val = other._values.get(name)
                if other_val is not None:
                    child._values[name] = other_val

        child._fitness = 0.5  # 子代初始适应度未知
        return child

    def copy(self) -> StrategyGenome:
        """深拷贝。"""
        return self._clone()

    # ═══════════════════════════════════════════════════════
    # Fitness
    # ═══════════════════════════════════════════════════════

    @property
    def fitness(self) -> float:
        return self._fitness

    def set_fitness(self, score: float) -> None:
        """设置适应度分数 (由 EvolutionLoop 调用)。"""
        self._fitness = max(0.0, min(1.0, score))

    @property
    def generation(self) -> int:
        return self._generation

    def get_mutation_history(self, limit: int = 20) -> list[MutationRecord]:
        """获取变异历史。"""
        return self._mutation_history[-limit:]

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _clone(self) -> StrategyGenome:
        """深拷贝。"""
        clone = StrategyGenome.__new__(StrategyGenome)
        clone._config = self._config
        clone._specs = self._specs
        clone._values = dict(self._values)
        clone._mutation_history = list(self._mutation_history)
        clone._generation = self._generation
        clone._fitness = self._fitness
        clone._rng = random.Random()
        return clone

    def _apply_mutation(
        self, spec: GeneSpec, current: Any, strength: float,
    ) -> Any:
        """对单个基因应用变异。"""
        mtype = self._choose_mutation_type(spec)

        if spec.gene_type == GeneType.BOOL:
            return not current

        elif spec.gene_type == GeneType.INT:
            if mtype == "scaling":
                factor = self._rng.uniform(0.5, 2.0) * strength
                new_val = int(round(current * factor))
            else:  # gaussian
                std = max(1, current * spec.mutation_strength * strength)
                new_val = int(round(self._rng.gauss(current, std)))
            return self._clamp(new_val, spec)

        else:  # FLOAT
            if mtype == "scaling":
                factor = self._rng.uniform(0.5, 2.0) * strength
                new_val = current * factor
            else:  # gaussian
                std = current * spec.mutation_strength * strength
                new_val = self._rng.gauss(current, max(std, 0.001))
            return self._clamp(new_val, spec)

    def _choose_mutation_type(self, spec: GeneSpec) -> str:
        """随机选择变异类型。"""
        if spec.gene_type == GeneType.BOOL:
            return "flip"
        return self._rng.choice(["gaussian", "gaussian", "scaling"])

    @staticmethod
    def _clamp(value: Any, spec: GeneSpec) -> Any:
        """将值钳制在有效范围。"""
        if spec.gene_type == GeneType.BOOL:
            return bool(value)
        if spec.min_val is not None and value < spec.min_val:
            value = spec.min_val
        if spec.max_val is not None and value > spec.max_val:
            value = spec.max_val
        if spec.gene_type == GeneType.INT:
            value = int(value)
        elif spec.gene_type == GeneType.FLOAT:
            value = float(value)
        return value
