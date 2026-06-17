"""Full-Body Genome — 菌核全维度自我进化基因组。

每一个可进化参数都是基因，编码在基因组中:
  - Tool Genes:     191 个工具的使用权重 (哪些工具更适合当前任务)
  - Prompt Genes:   系统提示词各模块的权重 (DNA 模块化进化)
  - Personality Genes: 9 个人格的适应度评分 (哪个更匹配用户)
  - Memory Genes:   五层记忆的保留策略参数 (Ebbinghaus 半衰期)
  - Provider Genes: 5 个 LLM 提供商的选择权重 (成本/质量/速度)
  - Skill Genes:    已加载技能的激活权重 (哪些技能更有用)
  - Organ Genes:    238 个器官的健康权重 (哪些器官更活跃)
  - Arbiter Genes:  7 个审批模式的使用频率 (安全 vs 效率)
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("sclerotium.genome")


@dataclass(frozen=True)
class GeneLocus:
    """单个基因位点 (不可变快照)。"""
    name: str
    value: float
    min_val: float = 0.0
    max_val: float = 1.0
    mutation_rate: float = 0.1
    last_mutated: float = 0.0
    fitness_contribution: float = 0.0


@dataclass(frozen=True)
class GenomeSnapshot:
    """基因组完整快照 (不可变)。"""
    generation: int
    timestamp: float
    genes: tuple[GeneLocus, ...]
    total_fitness: float
    dimensions: dict[str, float]


class FullBodyGenome:
    """菌核全维度基因组 — 自我进化的DNA。

    基因组编码了菌核的所有可进化参数，每个参数都是一个基因位点。
    通过记录真实的工具使用数据，自动调整基因权重，
    实现"用进废退"的自然选择。

    Usage:
        genome = FullBodyGenome()
        genome.record_tool_usage("desktop_open", success=True)
        genome.record_personality_match("jarvis", score=0.9)
        genome.evolve()  # 突变+选择
        best_tools = genome.get_top_tools(10)  # 最适工具 Top 10
    """

    # 突变参数
    MUTATION_RATE = 0.15
    CROSSOVER_RATE = 0.3
    ELITE_RATE = 0.2
    POPULATION_SIZE = 50

    def __init__(self, data_path: str = "./data/genome.json") -> None:
        self._data_path = Path(data_path)
        self._generation = 0
        self._total_mutations = 0
        self._improvements = 0

        # ── 工具基因 (191 tools × weight) ──
        self._tool_genes: dict[str, float] = {}      # tool_name → weight (0-1)
        self._tool_usage: dict[str, int] = {}         # tool_name → call count
        self._tool_success: dict[str, int] = {}       # tool_name → success count

        # ── 提示词基因 (DNA 模块权重) ──
        self._prompt_genes: dict[str, float] = {
            "tool_instructions": 0.8,    # 工具使用说明
            "personality_traits": 0.6,   # 性格特征
            "safety_rules": 0.9,         # 安全规则
            "memory_context": 0.5,       # 记忆上下文注入
            "skill_context": 0.4,        # 技能上下文注入
            "system_info": 0.7,          # 系统信息
        }

        # ── 人格基因 (9 personalities × fitness) ──
        self._personality_genes: dict[str, float] = {}
        self._personality_usage: dict[str, int] = {}

        # ── 记忆基因 (Ebbinghaus 参数) ──
        self._memory_genes: dict[str, float] = {
            "working_halflife_hours": 24.0,
            "episodic_halflife_days": 7.0,
            "semantic_halflife_days": 30.0,
            "procedural_halflife_days": 90.0,
            "strategic_halflife_days": 180.0,
            "consolidation_threshold": 0.6,
            "importance_boost": 0.3,
        }

        # ── 提供商基因 (5 providers × weight) ──
        self._provider_genes: dict[str, float] = {}

        # ── 技能基因 (skill × activation weight) ──
        self._skill_genes: dict[str, float] = {}
        self._skill_usage: dict[str, int] = {}

        # ── 器官基因 (organ category × health) ──
        self._organ_genes: dict[str, float] = {}

        # ── 裁决基因 (arbiter mode × frequency) ──
        self._arbiter_genes: dict[str, float] = {
            "PLAN": 0.1, "DEFAULT": 0.6, "ACCEPT_EDITS": 0.3,
            "AUTO": 0.2, "DONT_ASK": 0.05, "BYPASS": 0.02, "BUBBLE": 0.5,
        }

        self._evolution_history: list[GenomeSnapshot] = []
        self._load()

    # ═══════════════════════════════════════════════════════════════
    # Recording (用进废退 — 真实数据驱动)
    # ═══════════════════════════════════════════════════════════════

    def record_tool_usage(self, tool_name: str, success: bool) -> None:
        """记录工具使用 → EMA 更新权重，避免快速饱和到 1.0。

        用进废退：成功率高的工具自然权重高，失败的权重低。
        使用指数移动平均避免几次成功就冲到 1.0。
        """
        self._tool_genes.setdefault(tool_name, 0.5)
        self._tool_usage[tool_name] = self._tool_usage.get(tool_name, 0) + 1
        if success:
            self._tool_success[tool_name] = self._tool_success.get(tool_name, 0) + 1
        # EMA: new_weight = old * 0.95 + reward * 0.05
        # 成功→reward=1.0, 失败→reward=0.0
        reward = 1.0 if success else 0.0
        old = self._tool_genes[tool_name]
        self._tool_genes[tool_name] = old * 0.95 + reward * 0.05

    def record_personality_match(self, name: str, score: float) -> None:
        """记录人格匹配度 → 用户满意度高的人格获得更高适应度。"""
        self._personality_genes.setdefault(name, 0.5)
        self._personality_usage[name] = self._personality_usage.get(name, 0) + 1
        # 指数移动平均
        old = self._personality_genes[name]
        self._personality_genes[name] = old * 0.8 + score * 0.2

    def record_provider_performance(self, name: str, latency_ms: float, success: bool) -> None:
        """记录提供商表现 → 速度快+成功率高的提供商获得更高权重。"""
        self._provider_genes.setdefault(name, 0.5)
        speed_score = max(0.0, 1.0 - latency_ms / 5000.0)  # 5s = 0, 0ms = 1
        success_score = 1.0 if success else 0.0
        combined = speed_score * 0.4 + success_score * 0.6
        old = self._provider_genes[name]
        self._provider_genes[name] = old * 0.85 + combined * 0.15

    def record_skill_effectiveness(self, skill_name: str, used: bool, task_success: bool) -> None:
        """记录技能有效性 → 使用后任务成功率高的技能获得更高激活权重。"""
        self._skill_genes.setdefault(skill_name, 0.3)
        self._skill_usage[skill_name] = self._skill_usage.get(skill_name, 0) + 1
        if used and task_success:
            self._skill_genes[skill_name] = min(1.0, self._skill_genes[skill_name] + 0.03)
        elif used:
            self._skill_genes[skill_name] = max(0.0, self._skill_genes[skill_name] - 0.02)
        elif task_success:
            # 没用技能也成功了 → 技能可能不需要
            self._skill_genes[skill_name] = max(0.0, self._skill_genes[skill_name] - 0.005)

    def record_organ_activity(self, category: str, call_count: int) -> None:
        """记录器官活跃度。"""
        self._organ_genes.setdefault(category, 0.5)
        old = self._organ_genes[category]
        self._organ_genes[category] = old * 0.9 + min(1.0, call_count / 50.0) * 0.1

    # ═══════════════════════════════════════════════════════════════
    # Evolution (突变 + 选择)
    # ═══════════════════════════════════════════════════════════════

    def evolve(self) -> GenomeSnapshot:
        """执行一代进化: 评估适应度 → 变异 → 选择。"""
        self._generation += 1

        # 1. 突变: 随机微调所有基因
        mutations_this_gen = 0
        for gene_dict in [
            self._tool_genes, self._prompt_genes, self._personality_genes,
            self._memory_genes, self._provider_genes, self._skill_genes,
            self._organ_genes, self._arbiter_genes,
        ]:
            for name in list(gene_dict.keys()):
                if random.random() < self.MUTATION_RATE:
                    old_val = gene_dict[name]
                    # Gaussian mutation
                    delta = random.gauss(0, 0.05)
                    new_val = max(0.0, min(1.0, old_val + delta))
                    if new_val != old_val:
                        gene_dict[name] = new_val
                        mutations_this_gen += 1

        self._total_mutations += mutations_this_gen

        # 2. 计算适应度
        fitness = self._calculate_total_fitness()

        # 3. 选择: 淘汰低分基因，保留高分
        # 对工具基因: 去掉成功率 < 30% 且使用次数 > 5 的工具
        for name in list(self._tool_genes.keys()):
            usage = self._tool_usage.get(name, 0)
            success = self._tool_success.get(name, 0)
            if usage > 5 and success / usage < 0.3:
                self._tool_genes[name] = max(0.05, self._tool_genes[name] - 0.1)

        # 4. 记录快照
        snapshot = self.snapshot()
        self._evolution_history.append(snapshot)
        if len(self._evolution_history) > 100:
            self._evolution_history = self._evolution_history[-100:]

        # 5. 检查改进
        if len(self._evolution_history) >= 2:
            prev = self._evolution_history[-2].total_fitness
            if fitness > prev:
                self._improvements += 1

        self._save()
        logger.info("Generation %d: fitness=%.3f, mutations=%d, total_improvements=%d",
                     self._generation, fitness, mutations_this_gen, self._improvements)
        return snapshot

    def _calculate_total_fitness(self) -> float:
        """计算全基因组适应度 (0-1)。"""
        scores = []

        # 工具成功率
        if self._tool_genes:
            tool_success_rates = []
            for name, w in self._tool_genes.items():
                usage = self._tool_usage.get(name, 0)
                if usage > 0:
                    rate = self._tool_success.get(name, 0) / usage
                    tool_success_rates.append(rate * w)
            if tool_success_rates:
                scores.append(sum(tool_success_rates) / len(tool_success_rates))

        # 人格匹配度
        if self._personality_genes:
            scores.append(sum(self._personality_genes.values()) / len(self._personality_genes))

        # 提供商表现
        if self._provider_genes:
            scores.append(sum(self._provider_genes.values()) / len(self._provider_genes))

        # 技能有效性
        if self._skill_genes:
            scores.append(sum(self._skill_genes.values()) / len(self._skill_genes))

        # 器官活跃度
        if self._organ_genes:
            scores.append(sum(self._organ_genes.values()) / len(self._organ_genes))

        return sum(scores) / max(len(scores), 1)

    # ═══════════════════════════════════════════════════════════════
    # Query (获取进化结果)
    # ═══════════════════════════════════════════════════════════════

    def get_top_tools(self, n: int = 10) -> list[tuple[str, float]]:
        """获取权重最高的 N 个工具 (用进废退结果)。"""
        sorted_tools = sorted(self._tool_genes.items(), key=lambda x: x[1], reverse=True)
        return sorted_tools[:n]

    def get_best_personality(self) -> tuple[str, float]:
        """获取当前适应度最高的人格。"""
        if not self._personality_genes:
            return ("sclerotium", 0.5)
        return max(self._personality_genes.items(), key=lambda x: x[1])

    def get_best_provider(self) -> tuple[str, float]:
        """获取当前表现最好的 LLM 提供商。"""
        if not self._provider_genes:
            return ("deepseek", 0.5)
        return max(self._provider_genes.items(), key=lambda x: x[1])

    def get_top_skills(self, n: int = 10) -> list[tuple[str, float]]:
        """获取最有效的技能。"""
        sorted_skills = sorted(self._skill_genes.items(), key=lambda x: x[1], reverse=True)
        return sorted_skills[:n]

    def get_memory_params(self) -> dict[str, float]:
        """获取进化后的记忆参数。"""
        return dict(self._memory_genes)

    def get_arbiter_mode_distribution(self) -> dict[str, float]:
        """获取进化后的裁决模式分布。"""
        return dict(self._arbiter_genes)

    def get_organ_health(self) -> dict[str, float]:
        """获取器官活跃度分布。"""
        return dict(self._organ_genes)

    # ═══════════════════════════════════════════════════════════════
    # Snapshot & Persistence
    # ═══════════════════════════════════════════════════════════════

    def snapshot(self) -> GenomeSnapshot:
        """创建当前基因组的不可变快照。"""
        all_genes = []
        for name, val in self._tool_genes.items():
            all_genes.append(GeneLocus(name=f"tool:{name}", value=val))
        for name, val in self._prompt_genes.items():
            all_genes.append(GeneLocus(name=f"prompt:{name}", value=val))
        for name, val in self._personality_genes.items():
            all_genes.append(GeneLocus(name=f"personality:{name}", value=val))
        for name, val in self._memory_genes.items():
            all_genes.append(GeneLocus(name=f"memory:{name}", value=val))
        for name, val in self._provider_genes.items():
            all_genes.append(GeneLocus(name=f"provider:{name}", value=val))
        for name, val in self._skill_genes.items():
            all_genes.append(GeneLocus(name=f"skill:{name}", value=val))
        for name, val in self._organ_genes.items():
            all_genes.append(GeneLocus(name=f"organ:{name}", value=val))
        for name, val in self._arbiter_genes.items():
            all_genes.append(GeneLocus(name=f"arbiter:{name}", value=val))

        return GenomeSnapshot(
            generation=self._generation,
            timestamp=time.time(),
            genes=tuple(all_genes),
            total_fitness=self._calculate_total_fitness(),
            dimensions={
                "tools": len(self._tool_genes),
                "prompts": len(self._prompt_genes),
                "personalities": len(self._personality_genes),
                "memories": len(self._memory_genes),
                "providers": len(self._provider_genes),
                "skills": len(self._skill_genes),
                "organs": len(self._organ_genes),
                "arbiters": len(self._arbiter_genes),
            },
        )

    def copy(self) -> FullBodyGenome:
        """Return a deep copy for EvolutionLoop."""
        import copy
        return copy.deepcopy(self)

    def get(self, gene_name: str) -> float:
        """Get a gene value by name (e.g. 'tool:bash_execute')."""
        prefix, _, key = gene_name.partition(":")
        gene_map = {
            "tool": self._tool_genes,
            "prompt": self._prompt_genes,
            "personality": self._personality_genes,
            "memory": self._memory_genes,
            "provider": self._provider_genes,
            "skill": self._skill_genes,
            "organ": self._organ_genes,
            "arbiter": self._arbiter_genes,
        }
        return gene_map.get(prefix, {}).get(key, 0.5)

    def set(self, gene_name: str, value: float) -> None:
        """Set a gene value by name."""
        prefix, _, key = gene_name.partition(":")
        gene_map = {
            "tool": self._tool_genes,
            "prompt": self._prompt_genes,
            "personality": self._personality_genes,
            "memory": self._memory_genes,
            "provider": self._provider_genes,
            "skill": self._skill_genes,
            "organ": self._organ_genes,
            "arbiter": self._arbiter_genes,
        }
        if prefix in gene_map and key:
            gene_map[prefix][key] = max(0.01, min(1.0, value))

    def gene_names(self) -> list[str]:
        """Return all gene names for mutation targeting."""
        names = []
        names.extend(f"tool:{n}" for n in self._tool_genes)
        names.extend(f"prompt:{n}" for n in self._prompt_genes)
        names.extend(f"personality:{n}" for n in self._personality_genes)
        names.extend(f"memory:{n}" for n in self._memory_genes)
        names.extend(f"provider:{n}" for n in self._provider_genes)
        names.extend(f"skill:{n}" for n in self._skill_genes)
        names.extend(f"organ:{n}" for n in self._organ_genes)
        names.extend(f"arbiter:{n}" for n in self._arbiter_genes)
        return names

    def get_mutation_history(self) -> list[str]:
        """Return list of recently mutated gene names (for EvolutionLoop)."""
        return list(self._tool_genes.keys())[:3]  # Return some for evolution tracking

    @property
    def fitness(self) -> float:
        """Fitness score (used by EvolutionLoop for comparison)."""
        try:
            return self._total_fitness
        except AttributeError:
            return self._calculate_total_fitness()

    def get_fitness(self) -> float:
        """Return overall fitness score."""
        return self.fitness

    def mutate(self, num_mutations: int = 3, strength: float = 1.0) -> FullBodyGenome:
        """Create a mutated copy of this genome."""
        import copy, random
        c = copy.deepcopy(self)
        all_genes = [
            (c._tool_genes, "tool"),
            (c._prompt_genes, "prompt"),
            (c._personality_genes, "personality"),
            (c._memory_genes, "memory"),
            (c._provider_genes, "provider"),
            (c._skill_genes, "skill"),
            (c._organ_genes, "organ"),
            (c._arbiter_genes, "arbiter"),
        ]
        for _ in range(num_mutations):
            gene_dict, _ = random.choice([g for g in all_genes if g[0]])
            if gene_dict:
                key = random.choice(list(gene_dict.keys()))
                delta = (random.random() - 0.5) * 0.2 * strength
                gene_dict[key] = max(0.01, min(1.0, gene_dict[key] + delta))
        c._total_mutations += num_mutations
        # NOTE: _generation is NOT incremented here — the EvolutionLoop
        # manages generation count. Incrementing here would double-count.
        return c

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def total_mutations(self) -> int:
        return self._total_mutations

    @property
    def improvements(self) -> int:
        return self._improvements

    # ═══════════════════════════════════════════════════════════════
    # 持久化 (Checkpoint Save/Load)
    # ═══════════════════════════════════════════════════════════════

    def save_checkpoint(self) -> None:
        """保存进化检查点到磁盘 (重启后恢复用)。"""
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "generation": self._generation,
            "total_mutations": self._total_mutations,
            "improvements": self._improvements,
            "tool_genes": self._tool_genes,
            "prompt_genes": self._prompt_genes,
            "personality_genes": self._personality_genes,
            "memory_genes": self._memory_genes,
            "provider_genes": self._provider_genes,
            "skill_genes": self._skill_genes,
            "organ_genes": self._organ_genes,
            "arbiter_genes": self._arbiter_genes,
            "tool_usage": self._tool_usage,
            "tool_success": dict(self._tool_success),
        }
        with open(self._data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        logger.info("Checkpoint saved: gen %d → %s", self._generation, self._data_path)

    def load_checkpoint(self) -> None:
        """从磁盘恢复进化检查点。"""
        if not self._data_path.exists():
            logger.info("No checkpoint found at %s — starting fresh", self._data_path)
            return
        try:
            with open(self._data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._generation = data.get("generation", 0)
            self._total_mutations = data.get("total_mutations", 0)
            self._improvements = data.get("improvements", 0)
            self._tool_genes = data.get("tool_genes", {})
            self._prompt_genes = data.get("prompt_genes", self._prompt_genes)
            self._personality_genes = data.get("personality_genes", {})
            self._memory_genes = data.get("memory_genes", self._memory_genes)
            self._provider_genes = data.get("provider_genes", {})
            self._skill_genes = data.get("skill_genes", {})
            self._organ_genes = data.get("organ_genes", {})
            self._arbiter_genes = data.get("arbiter_genes", self._arbiter_genes)
            self._tool_usage = data.get("tool_usage", {})
            self._tool_success = data.get("tool_success", {})
            logger.info("Checkpoint loaded: gen %d, %d genes restored, %d mutations total",
                        self._generation, len(self._tool_genes), self._total_mutations)
        except Exception as e:
            logger.warning("Failed to load checkpoint: %s — starting fresh", e)

    # 兼容旧代码: 私有方法代理到公开方法
    def _save(self) -> None:
        self.save_checkpoint()

    def _load(self) -> None:
        self.load_checkpoint()
