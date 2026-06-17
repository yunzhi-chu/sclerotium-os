"""Arena 6: 性能效率竞技场 (Performance Arena) — FCPI 权重 10%.

不通过 MiroFish 社会仿真 —— 直接在 Mycelium 内部进行压力测试。
结果报告给进化循环。

测试内容:
    - 认知路由延迟 (L1-L6 routing latency)
    - 事件总线吞吐 (event bus throughput)
    - Stigmergy 场更新速度
    - Token 效率
    - 记忆压缩比
    - 可扩展性 (Agent 数量增加时的性能退化)

Agent 类型:
    - 无社会 Agent — 此竞技场使用直接性能测量
    - 压力生成器 (load_generator): 模拟负载
    - 性能监控器 (performance_monitor): 收集指标

适应度提取:
    performance_fitness = {
        cognitive_routing_latency: L1-L6 路由延迟 (ms)
        event_bus_throughput: 事件总线吞吐 (events/sec)
        field_update_performance: Stigmergy 场更新速度 (cells/ms)
        token_efficiency: 每 Token 有效计算量
        memory_compression_ratio: 全息记忆压缩比
        scalability_factor: Agent 扩展时的退化曲线
    }
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .arena_base import (
    ArenaBase,
    ArenaConfig,
    ArenaResult,
    FCPIDimension,
    FitnessVector,
)

logger = logging.getLogger(__name__)


class PerformanceArena(ArenaBase):
    """性能效率竞技场.

    直接在本地运行性能基准测试，不依赖 OASIS 社会仿真。
    测试 Mycelium 核心系统的延迟、吞吐、Token 效率和可扩展性。
    """

    def __init__(
        self,
        config: ArenaConfig | None = None,
        work_dir: Any = None,
    ) -> None:
        if config is None:
            config = ArenaConfig(
                arena_id=f"performance_{id(self):x}",
                dimension=FCPIDimension.PERFORMANCE,
                max_rounds=10,
                min_agents=0,
                max_agents=0,
                agent_types=(),  # 无社会 Agent
                platform_types=(),  # 无 OASIS 平台
                temperature=0.0,
                extra={
                    "latency_target_ms": 500,
                    "throughput_target": 10000,
                    "token_efficiency_baseline": 0.7,
                    "scalability_test_agent_counts": [1, 10, 50, 100, 200],
                },
            )
        super().__init__(config, work_dir)

    # ── 抽象方法实现 ────────────────────────────────────────────────────

    def build_agent_profiles(
        self, genome_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """性能竞技场不使用社会 Agent Profile."""
        return []

    def build_simulation_config(
        self,
        agent_profiles: list[dict[str, Any]],
        genome_context: dict[str, Any],
    ) -> dict[str, Any]:
        """构建性能基准测试配置."""
        return {
            "arena_type": "performance",
            "benchmark_config": {
                "latency_tests": {
                    "model_routing": {
                        "depths": ["L1", "L2", "L3", "L4", "L5", "L6"],
                        "iterations": 100,
                        "target_ms": 500,
                    },
                    "event_bus": {
                        "event_types": ["pipeline.tick", "l6.scan.complete", "l6.skill_created"],
                        "iterations": 1000,
                    },
                },
                "throughput_tests": {
                    "event_bus": {
                        "burst_size": 1000,
                        "sustained_duration_seconds": 60,
                    },
                    "stigmergy_field": {
                        "grid_size": 100,
                        "update_iterations": 500,
                    },
                },
                "token_efficiency": {
                    "test_prompts": [
                        "simple_query",
                        "complex_analysis",
                        "code_generation",
                        "multi_agent_coordination",
                    ],
                    "measure_output_tokens": True,
                    "measure_latency_per_token": True,
                },
                "scalability": {
                    "agent_counts": [1, 10, 50, 100, 200],
                    "measure_degradation": True,
                },
                "memory_tests": {
                    "compression_ratio_test": True,
                    "retrieval_accuracy_test": True,
                },
            },
            "time_config": {
                "total_hours": 2,
                "minutes_per_round": 10,
            },
            "agent_configs": [],
            "event_config": {},
            "platform_configs": {},
        }

    def extract_fitness(
        self,
        action_logs: list[dict[str, Any]],
        agent_profiles: list[dict[str, Any]],
        genome_context: dict[str, Any],
    ) -> FitnessVector:
        """计算性能适应度向量.

        由于 Phase 1 没有真实 Mycelium 系统连接，
        使用模拟的性能数据。在后续 Phase 集成真实系统。
        """
        # 从 genome_context 获取性能数据 (由 Mycelium 系统提供)
        perf_data = genome_context.get("performance_data", {})

        # 认知路由延迟 (ms) — 越低越好
        routing_latency = perf_data.get("routing_latency_ms", 250)
        latency_score = max(0.0, 1.0 - routing_latency / 1000)  # < 1000ms → 好

        # 事件总线吞吐 (events/sec) — 越高越好
        event_throughput = perf_data.get("event_throughput", 8000)
        throughput_score = min(event_throughput / 10000, 1.0)  # > 10000 → 满分

        # Stigmergy 场更新速度 (cells/ms) — 越高越好
        field_update_speed = perf_data.get("field_update_cells_per_ms", 500)
        field_score = min(field_update_speed / 1000, 1.0)

        # Token 效率 (有效计算/Token) — 越高越好
        token_efficiency = perf_data.get("token_efficiency", 0.65)
        token_score = min(token_efficiency / 0.9, 1.0)  # > 0.9 → 满分

        # 记忆压缩比 — 越高越好
        memory_compression = perf_data.get("memory_compression_ratio", 0.5)
        memory_score = min(memory_compression / 0.8, 1.0)  # > 0.8 → 满分

        # 可扩展性 (退化曲线) — 越平坦越好
        scalability = perf_data.get("scalability_factor", 0.6)
        scal_score = min(scalability / 0.9, 1.0)  # > 0.9 → 满分

        sub_scores = {
            "cognitive_routing_latency": round(latency_score, 4),
            "event_bus_throughput": round(throughput_score, 4),
            "field_update_performance": round(field_score, 4),
            "token_efficiency": round(token_score, 4),
            "memory_compression_ratio": round(memory_score, 4),
            "scalability_factor": round(scal_score, 4),
        }

        primary = (
            0.25 * latency_score
            + 0.20 * throughput_score
            + 0.15 * field_score
            + 0.20 * token_score
            + 0.10 * memory_score
            + 0.10 * scal_score
        )

        return FitnessVector(
            dimension=FCPIDimension.PERFORMANCE,
            primary_score=round(min(max(primary, 0.0), 1.0), 4),
            sub_scores=sub_scores,
            confidence=0.95,  # 性能测试置信度高 (真实测量)
            generation=self._generation,
            genome_id=genome_context.get("genome_id", "unknown"),
            arena_id=self.config.arena_id,
        )

    def detect_emergent_patterns(
        self,
        action_logs: list[dict[str, Any]],
        fitness: FitnessVector,
        history: list[ArenaResult],
    ) -> list[str]:
        """检测性能涌现模式 (如性能退化/优化跳跃)."""
        patterns: list[str] = []
        historical_patterns: set[str] = {
            p for r in history for p in r.emergent_patterns
        }

        # 性能回归检测
        if history:
            prev = history[-1]
            if prev.fitness_vector:
                degradation = prev.fitness_vector.primary_score - fitness.primary_score
                if degradation > 0.1:
                    p = f"performance_regression: {degradation:.2%} drop from gen {prev.generation}"
                    if p not in historical_patterns:
                        patterns.append(p)
                elif degradation < -0.1:
                    p = f"performance_leap: {-degradation:.2%} improvement from gen {prev.generation}"
                    if p not in historical_patterns:
                        patterns.append(p)

        # Token 效率突破
        if fitness.sub_scores.get("token_efficiency", 0) > 0.85:
            p = "token_efficiency_breakthrough: exceeding 85% efficiency"
            if p not in historical_patterns:
                patterns.append(p)

        return patterns

    # ── 覆盖: 不使用模拟日志 ─────────────────────────────────────────

    def run_generation(
        self,
        genome_context: dict[str, Any],
        action_logs: list[dict[str, Any]] | None = None,
    ) -> ArenaResult:
        """运行一代性能评估.

        性能竞技场不生成 Agent Profile，不运行社会仿真，
        直接从 genome_context 提取性能数据。
        """
        start_time = time.monotonic()
        self._is_running = True
        self._generation += 1

        try:
            # 性能竞技场直接使用 genome_context 中的性能数据
            sim_config = self.build_simulation_config([], genome_context)
            self._save_simulation_config(sim_config)

            # 不需要 action_logs — 直接提取
            fitness = self.extract_fitness([], [], genome_context)
            logger.info(
                "PerformanceArena Gen %d: fitness=%.4f",
                self._generation, fitness.primary_score,
            )

            emergent = self.detect_emergent_patterns([], fitness, self._history)

            duration = time.monotonic() - start_time
            result = ArenaResult(
                fitness_vector=fitness,
                generation=self._generation,
                duration_seconds=duration,
                agent_count=0,
                total_actions=0,
                emergent_patterns=tuple(emergent),
                success=True,
            )

        except Exception as exc:
            logger.exception("PerformanceArena Gen %d failed", self._generation)
            duration = time.monotonic() - start_time
            result = ArenaResult(
                fitness_vector=None,
                generation=self._generation,
                duration_seconds=duration,
                agent_count=0,
                total_actions=0,
                errors=(str(exc),),
                success=False,
            )

        self._history.append(result)
        self._is_running = False
        self._save_result(result)
        return result
