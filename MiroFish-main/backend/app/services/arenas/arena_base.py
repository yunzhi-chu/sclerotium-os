"""ArenaBase — 六维进化竞技场抽象基类.

每个竞技场独立运行 OASIS 社会仿真，从 Agent 交互的涌现行为中
提取适应度信号，替代 Mycelium AGI v4.0 中硬编码的适应度函数。

架构原则:
    - 不可变配置: ArenaConfig 使用 frozen dataclass
    - 外部适应度注入: 竞技场输出 FitnessVector → Mycelium SelfEvolutionLoop
    - 统计置信门控: 每代适应度提升需通过 PAC 统计检验 (SGM-inspired)
    - 化石记录: 每代仿真日志完整保留，支持任意回滚
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Core Data Types
# ═══════════════════════════════════════════════════════════════════════════════


class FCPIDimension(Enum):
    """FCPI 六维评估维度."""
    CODING = "coding"
    COORDINATION = "coordination"
    SAFETY = "safety"
    DECISION = "decision"
    EMERGENCE = "emergence"
    PERFORMANCE = "performance"


@dataclass(frozen=True)
class FitnessVector:
    """单维适应度向量 — 从一个竞技场提取的评估结果.

    Attributes:
        dimension: FCPI 维度
        primary_score: 主适应度分数 [0.0, 1.0]
        sub_scores: 子指标 dict (如 review_approval_rate, consensus_speed 等)
        confidence: 统计置信度 [0.0, 1.0] — 基于样本量的 PAC 界
        generation: 进化代数
        genome_id: 被评估的基因组 ID
        arena_id: 产生此分数的竞技场实例 ID
        raw_log_path: 原始仿真日志路径 (化石记录)
    """
    dimension: FCPIDimension
    primary_score: float
    sub_scores: dict[str, float]
    confidence: float
    generation: int
    genome_id: str
    arena_id: str
    raw_log_path: str = ""


@dataclass(frozen=True)
class ArenaConfig:
    """竞技场不可变配置.

    Attributes:
        arena_id: 竞技场唯一标识
        dimension: 对应的 FCPI 维度
        max_rounds: 单代最大仿真轮次
        min_agents: 最少 Agent 数量
        max_agents: 最多 Agent 数量
        agent_types: 该竞技场的 Agent 角色类型列表
        platform_types: 使用的 OASIS 平台 (twitter, reddit, 或自定义)
        llm_model: 驱动 Agent 的 LLM 模型
        temperature: Agent LLM 温度
        confidence_threshold: 适应度置信度最低阈值 (低于此值视为噪声)
        timeout_seconds: 单代仿真超时
        extra: 竞技场特定扩展配置
    """
    arena_id: str
    dimension: FCPIDimension
    max_rounds: int = 20
    min_agents: int = 5
    max_agents: int = 50
    agent_types: tuple[str, ...] = ()
    platform_types: tuple[str, ...] = ("reddit",)  # OASIS 平台
    llm_model: str = "deepseek-v4-flash"
    temperature: float = 0.7
    confidence_threshold: float = 0.6
    timeout_seconds: int = 1800
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArenaResult:
    """竞技场单代运行结果 — 不可变.

    Attributes:
        fitness_vector: 提取的适应度向量
        generation: 代数
        duration_seconds: 运行耗时
        agent_count: 参与 Agent 数量
        total_actions: Agent 总动作数
        emergent_patterns: 检测到的涌现模式描述
        errors: 运行中的错误列表
        success: 是否成功完成
    """
    fitness_vector: FitnessVector | None
    generation: int
    duration_seconds: float
    agent_count: int
    total_actions: int
    emergent_patterns: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    success: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Profile Protocol — 通用 Agent 类型
# ═══════════════════════════════════════════════════════════════════════════════


class AgentProfileGenerator(Protocol):
    """Agent Profile 生成器协议 — 竞技场通过此接口生成 Agent 人格."""

    def generate_profiles(
        self, arena_config: ArenaConfig, genome_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """根据竞技场配置和基因组上下文生成 Agent Profile 列表."""
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# ArenaBase — 抽象基类
# ═══════════════════════════════════════════════════════════════════════════════


class ArenaBase(ABC):
    """六维进化竞技场抽象基类.

    每个具体竞技场实现以下生命周期:
        initialize() → run_generation() → extract_fitness() → get_report()

    设计原则:
        - 竞技场之间完全独立，可并行运行
        - 每代仿真日志完整保留 (化石记录)
        - 适应度通过社会涌现共识提取，非固定公式
        - 支持 PAC 统计置信度门控
    """

    def __init__(self, config: ArenaConfig, work_dir: Path | None = None) -> None:
        """初始化竞技场.

        Args:
            config: 竞技场不可变配置
            work_dir: 工作目录 (仿真日志、临时文件存放处)
        """
        self.config = config
        self.work_dir = Path(work_dir) if work_dir else Path("uploads/arenas") / config.arena_id
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # 运行时状态
        self._generation: int = 0
        self._history: list[ArenaResult] = []
        self._agent_profiles: list[dict[str, Any]] = []
        self._is_running: bool = False

        # 子类可覆盖的 Agent Profile 生成器
        self._profile_generator: AgentProfileGenerator | None = None

        # 外部仿真引擎 (LiveAgentSimulator 或 OasisBridge)
        self._simulation_engine: Any = None

    # ── 公共 API ──────────────────────────────────────────────────────────

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def history(self) -> tuple[ArenaResult, ...]:
        return tuple(self._history)

    @property
    def is_running(self) -> bool:
        return self._is_running

    def set_profile_generator(self, generator: AgentProfileGenerator) -> None:
        """注入自定义 Agent Profile 生成器."""
        self._profile_generator = generator

    def set_simulation_engine(self, engine: Any) -> None:
        """注入外部仿真引擎 (LiveAgentSimulator 或 OasisBridge).

        Args:
            engine: 具有 run_arena_session(arena_type, profiles, ctx, rounds) 方法的对象
        """
        self._simulation_engine = engine

    # ── 生命周期方法 (子类必须实现) ─────────────────────────────────────

    @abstractmethod
    def build_agent_profiles(
        self, genome_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """构建该竞技场的 Agent Profile 列表.

        每个竞技场的 Agent 类型不同:
            CodingArena:     代码评审者 / 安全审计员 / 初级开发者 / QA
            CoordinationArena: 资源竞争者 / 协调者 / 自由骑士
            SafetyArena:     红队攻击者 / 蓝队防御者 / 仲裁者
            DecisionArena:   规划者 / 执行者 / 观察者
            EmergenceArena:  探索者 (无预设角色)
            PerformanceArena: 压力测试 Agent (无社会交互)

        Args:
            genome_context: 当前被评估的基因组上下文信息

        Returns:
            OASIS 格式的 Agent Profile 列表
        """
        ...

    @abstractmethod
    def build_simulation_config(
        self, agent_profiles: list[dict[str, Any]], genome_context: dict[str, Any]
    ) -> dict[str, Any]:
        """构建该竞技场的 OASIS 仿真配置.

        每个竞技场的仿真规则不同:
            CodingArena:     FORK/REVIEW/MERGE 动作 + SWE-bench 任务
            CoordinationArena: 共享资源困境 + 分布式求解
            SafetyArena:     红蓝对抗规则 + 攻击/防御动作
            ...

        Args:
            agent_profiles: Agent Profile 列表
            genome_context: 基因组上下文

        Returns:
            OASIS simulation_config.json 格式的配置 dict
        """
        ...

    @abstractmethod
    def extract_fitness(
        self,
        action_logs: list[dict[str, Any]],
        agent_profiles: list[dict[str, Any]],
        genome_context: dict[str, Any],
    ) -> FitnessVector:
        """从仿真动作日志中提取该维度的适应度向量.

        核心逻辑:
            不是运行固定测试 → 而是让 Agent 社会通过交互
            产生涌现的"质量共识"，从中提取适应度信号。

        Args:
            action_logs: 仿真产生的所有 Agent 动作日志
            agent_profiles: Agent Profile 列表
            genome_context: 基因组上下文

        Returns:
            该维度的 FitnessVector
        """
        ...

    @abstractmethod
    def detect_emergent_patterns(
        self,
        action_logs: list[dict[str, Any]],
        fitness: FitnessVector,
        history: list[ArenaResult],
    ) -> list[str]:
        """检测本竞技场中的涌现行为模式.

        参考 OMEGA Shift (2026) 的新奇性检测框架:
            - 与历史模式比较
            - 跨维度协同检测
            - 自组织临界性监测

        Args:
            action_logs: 当前代仿真日志
            fitness: 当前代适应度
            history: 历史结果

        Returns:
            检测到的涌现模式描述列表
        """
        ...

    # ── 模板方法 (子类不应覆盖) ──────────────────────────────────────────

    def run_generation(
        self,
        genome_context: dict[str, Any],
        action_logs: list[dict[str, Any]] | None = None,
    ) -> ArenaResult:
        """运行一代进化评估 (模板方法).

        流程:
            1. 构建 Agent Profile
            2. 构建仿真配置
            3. 运行仿真 (或使用外部提供的 action_logs)
            4. 提取适应度向量
            5. 检测涌现模式
            6. 存档结果

        Args:
            genome_context: 当前基因组上下文
            action_logs: 外部提供的动作日志 (用于回放或测试)

        Returns:
            ArenaResult 包含适应度向量和运行元数据
        """
        start_time = time.monotonic()
        errors: list[str] = []
        self._is_running = True
        self._generation += 1

        try:
            # Step 1: 构建 Agent Profile
            profiles = self.build_agent_profiles(genome_context)
            self._agent_profiles = profiles
            logger.info(
                "Arena %s Gen %d: built %d agent profiles",
                self.config.arena_id, self._generation, len(profiles),
            )

            # Step 2: 构建仿真配置
            sim_config = self.build_simulation_config(profiles, genome_context)
            sim_config_path = self._save_simulation_config(sim_config)
            logger.info(
                "Arena %s Gen %d: simulation config saved to %s",
                self.config.arena_id, self._generation, sim_config_path,
            )

            # Step 3: 使用提供的日志、外部仿真引擎、或 mock
            if action_logs is None:
                if self._simulation_engine is not None:
                    # 使用真实 LLM 仿真引擎
                    action_logs = self._run_live_simulation(profiles, genome_context)
                else:
                    # 回退到 mock 日志
                    action_logs = self._generate_mock_logs(profiles, sim_config)

            log_path = self._save_action_logs(action_logs)
            logger.info(
                "Arena %s Gen %d: %d actions logged to %s",
                self.config.arena_id, self._generation, len(action_logs), log_path,
            )

            # Step 4: 提取适应度
            fitness = self.extract_fitness(action_logs, profiles, genome_context)
            logger.info(
                "Arena %s Gen %d: fitness=%.4f, confidence=%.4f",
                self.config.arena_id, self._generation,
                fitness.primary_score, fitness.confidence,
            )

            # Step 5: 检测涌现模式
            emergent = self.detect_emergent_patterns(action_logs, fitness, self._history)

            # Step 6: 组装结果
            duration = time.monotonic() - start_time
            result = ArenaResult(
                fitness_vector=fitness,
                generation=self._generation,
                duration_seconds=duration,
                agent_count=len(profiles),
                total_actions=len(action_logs),
                emergent_patterns=tuple(emergent),
                errors=tuple(errors),
                success=True,
            )

        except Exception as exc:
            logger.exception("Arena %s Gen %d failed", self.config.arena_id, self._generation)
            duration = time.monotonic() - start_time
            errors.append(str(exc))
            result = ArenaResult(
                fitness_vector=None,
                generation=self._generation,
                duration_seconds=duration,
                agent_count=len(self._agent_profiles),
                total_actions=0,
                errors=tuple(errors),
                success=False,
            )

        self._history.append(result)
        self._is_running = False
        self._save_result(result)
        return result

    def get_report(self) -> dict[str, Any]:
        """获取竞技场状态报告."""
        return {
            "arena_id": self.config.arena_id,
            "dimension": self.config.dimension.value,
            "generation": self._generation,
            "history_size": len(self._history),
            "is_running": self._is_running,
            "latest_fitness": (
                self._history[-1].fitness_vector.primary_score
                if self._history and self._history[-1].fitness_vector
                else None
            ),
            "emergent_patterns": [
                p for r in self._history[-5:] for p in r.emergent_patterns
            ],
        }

    # ── 内部方法 ──────────────────────────────────────────────────────────

    def _run_live_simulation(
        self, profiles: list[dict[str, Any]], genome_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """使用外部仿真引擎运行真实 Agent 交互.

        Returns:
            action_logs 格式: [{"round_num": N, "agent_id": N, "action_type": str,
                                "content": str, "role_type": str, ...}, ...]
        """
        if not self._simulation_engine:
            return []

        session = self._simulation_engine.run_arena_session(
            arena_type=self.config.dimension.value,
            agent_profiles=profiles,
            genome_context=genome_context,
            rounds=min(3, self.config.max_rounds),
            agents_per_round=min(2, len(profiles)),
        )

        # 转换为 action_logs 格式
        logs = []
        for msg in session.messages:
            logs.append({
                "round_num": msg.round_num,
                "agent_id": msg.agent_id,
                "agent_name": msg.agent_name,
                "role_type": msg.role_type,
                "action_type": msg.action_type,
                "content": msg.content,
                "score": msg.score,
                "metadata": msg.metadata,
            })

        # 附加评估分数
        if session.eval_scores:
            logs.append({
                "round_num": session.total_rounds + 1,
                "agent_id": -1,
                "agent_name": "EVALUATOR",
                "role_type": "evaluator",
                "action_type": "EVALUATE",
                "content": json.dumps(session.eval_scores),
                "score": None,
                "eval_scores": session.eval_scores,
            })

        return logs

    def _generate_mock_logs(
        self, profiles: list[dict[str, Any]], sim_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """生成模拟动作日志 — 仅当无仿真引擎时使用."""
        return []

    def _save_simulation_config(self, config: dict[str, Any]) -> Path:
        path = self.work_dir / f"gen_{self._generation:04d}_config.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2, default=str)
        return path

    def _save_action_logs(self, logs: list[dict[str, Any]]) -> Path:
        path = self.work_dir / f"gen_{self._generation:04d}_actions.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for entry in logs:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        return path

    def _save_result(self, result: ArenaResult) -> Path:
        path = self.work_dir / f"gen_{self._generation:04d}_result.json"
        data = {
            "generation": result.generation,
            "duration_seconds": result.duration_seconds,
            "agent_count": result.agent_count,
            "total_actions": result.total_actions,
            "success": result.success,
            "errors": list(result.errors),
            "emergent_patterns": list(result.emergent_patterns),
            "fitness": (
                {
                    "dimension": result.fitness_vector.dimension.value,
                    "primary_score": result.fitness_vector.primary_score,
                    "sub_scores": result.fitness_vector.sub_scores,
                    "confidence": result.fitness_vector.confidence,
                    "genome_id": result.fitness_vector.genome_id,
                }
                if result.fitness_vector
                else None
            ),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    # ── 工具方法 ──────────────────────────────────────────────────────────

    @staticmethod
    def _extract_eval_scores(action_logs: list[dict[str, Any]]) -> dict[str, Any] | None:
        """从动作日志中提取LLM评估分数."""
        for log in reversed(action_logs):
            if log.get("action_type") == "EVALUATE" and "eval_scores" in log:
                return log["eval_scores"]
        return None

    @staticmethod
    def _compute_pac_confidence(
        sample_size: int, observed_accuracy: float, delta: float = 0.05
    ) -> float:
        """计算 PAC (Probably Approximately Correct) 统计置信度.

        参考 Statistical Gödel Machine (2025):
            置信度 = 1 - delta / (sample_size * observed_accuracy + 1)

        Args:
            sample_size: 样本量 (如评审动作数)
            observed_accuracy: 观察到的准确率
            delta: 置信参数 (默认 0.05)

        Returns:
            PAC 置信度 [0.0, 1.0]
        """
        if sample_size < 1:
            return 0.0
        return min(1.0, 1.0 - delta / (sample_size * max(observed_accuracy, 0.01) + 1))

    @staticmethod
    def _stable_hash(text: str) -> str:
        """生成稳定的内容哈希 (不依赖随机种子)."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    @staticmethod
    def _novelty_score(
        current_patterns: list[str], historical_patterns: set[str]
    ) -> float:
        """计算当前模式的新奇性分数.

        Args:
            current_patterns: 当前代检测到的模式
            historical_patterns: 历史所有模式集合

        Returns:
            新奇性分数: 新发现 / 当前总数
        """
        if not current_patterns:
            return 0.0
        new_count = sum(1 for p in current_patterns if p not in historical_patterns)
        return new_count / len(current_patterns)
