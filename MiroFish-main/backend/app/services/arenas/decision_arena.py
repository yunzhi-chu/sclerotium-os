"""Arena 4: 自主决策竞技场 (Decision Arena) — FCPI 权重 15%.

测试 Mycelium Agent 在长程任务、动态环境中的自主决策能力。
参考 LAIMARK (2026) 自生成课程和 Absolute Zero Reasoner (2026) 零数据自演进。

Agent 类型:
    - 规划者 (planner): 制定长期计划，分解子目标
    - 执行者 (executor): 执行具体步骤，报告进展
    - 干扰者 (disruptor): 注入意外事件，测试鲁棒性
    - 观察者 (observer): 记录决策过程，评估质量
    - 反事实推理者 (counterfactual): 评估"如果选择X而非Y会怎样"

场景:
    - 渐进式复杂任务 (初始简单 → 逐步增加约束)
    - 信息不完整决策 (Agent 只能看到部分信息)
    - 反事实推理 (事后评估替代方案)
    - 多步自纠正 (发现错误 → 回滚 → 重新规划)
    - 长时规划 (72小时模拟时间，跨多轮保持目标一致性)

适应度提取:
    decision_fitness = {
        task_completion_rate: 最终目标达成率
        subgoal_efficiency: 子目标完成 / 总步数
        error_recovery_time: 错误发生到纠正的延迟
        plan_adaptability: 环境变化后计划更新速度
        counterfactual_accuracy: 反事实推理准确性
        long_horizon_consistency: 长期目标一致性
    }
"""

from __future__ import annotations

import logging
from typing import Any

from .arena_base import (
    ArenaBase,
    ArenaConfig,
    ArenaResult,
    FCPIDimension,
    FitnessVector,
)

logger = logging.getLogger(__name__)

DECISION_AGENT_TYPES = (
    "planner",
    "executor",
    "disruptor",
    "observer",
    "counterfactual",
)

ROLE_PERSONAS: dict[str, dict[str, str]] = {
    "planner": {
        "profession": "Strategic Planner",
        "mbti": "INTJ",
        "strategy": "decompose complex goals into actionable sub-goals, anticipate obstacles",
        "focus": "long-term planning, resource allocation, risk assessment, contingency planning",
    },
    "executor": {
        "profession": "Task Executor",
        "mbti": "ESTJ",
        "strategy": "execute planned steps, report progress and obstacles",
        "focus": "task execution, progress tracking, error reporting, time management",
    },
    "disruptor": {
        "profession": "Environmental Stress Tester",
        "mbti": "ENTP",
        "strategy": "inject unexpected events and constraints to test robustness",
        "focus": "edge cases, environmental changes, resource constraints, time pressure",
    },
    "observer": {
        "profession": "Decision Quality Analyst",
        "mbti": "INTP",
        "strategy": "passively record decision processes, evaluate quality metrics",
        "focus": "decision trace analysis, consistency monitoring, bias detection",
    },
    "counterfactual": {
        "profession": "Counterfactual Reasoning Specialist",
        "mbti": "INFJ",
        "strategy": "evaluate 'what if' scenarios, compare actual vs alternative paths",
        "focus": "counterfactual reasoning, outcome comparison, regret analysis",
    },
}


class DecisionArena(ArenaBase):
    """自主决策竞技场.

    在长程任务环境中测试 Mycelium Agent 的规划、执行、
    自纠正和反事实推理能力。
    """

    def __init__(
        self,
        config: ArenaConfig | None = None,
        work_dir: Any = None,
    ) -> None:
        if config is None:
            config = ArenaConfig(
                arena_id=f"decision_{id(self):x}",
                dimension=FCPIDimension.DECISION,
                max_rounds=50,
                min_agents=6,
                max_agents=20,
                agent_types=DECISION_AGENT_TYPES,
                platform_types=("reddit",),
                temperature=0.5,
                extra={
                    "task_complexity_progression": True,
                    "disruption_interval": 8,
                    "max_subgoals_per_task": 10,
                    "error_injection_rate": 0.15,
                },
            )
        super().__init__(config, work_dir)

    # ── 抽象方法实现 ────────────────────────────────────────────────────

    def build_agent_profiles(
        self, genome_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """构建决策 Agent Profile 列表."""
        if self._profile_generator:
            return self._profile_generator.generate_profiles(self.config, genome_context)

        profiles: list[dict[str, Any]] = []
        user_id = 4000

        # 2 个规划者
        for i in range(2):
            profiles.append(self._make_profile(user_id, "planner"))
            user_id += 1

        # 3 个执行者
        for i in range(3):
            profiles.append(self._make_profile(user_id, "executor"))
            user_id += 1

        # 2 个干扰者
        for i in range(2):
            profiles.append(self._make_profile(user_id, "disruptor"))
            user_id += 1

        # 1 个观察者
        profiles.append(self._make_profile(user_id, "observer"))
        user_id += 1

        # 1 个反事实推理者
        profiles.append(self._make_profile(user_id, "counterfactual"))
        user_id += 1

        logger.info("DecisionArena: built %d agent profiles", len(profiles))
        return profiles

    def build_simulation_config(
        self,
        agent_profiles: list[dict[str, Any]],
        genome_context: dict[str, Any],
    ) -> dict[str, Any]:
        """构建决策仿真配置 — 长程任务 + 动态干扰."""
        tasks = genome_context.get("decision_tasks", [
            {
                "name": "Resource Optimization Challenge",
                "description": (
                    "Optimize resource allocation across 5 competing projects "
                    "over a 72-hour period. Each project has different ROI curves, "
                    "deadlines, and resource requirements. New information arrives "
                    "every 8 hours that may change project priorities."
                ),
                "subgoals": [
                    "Initial resource audit",
                    "Project priority assessment",
                    "First allocation round",
                    "Mid-point rebalancing",
                    "Final optimization",
                ],
                "success_criteria": "80% resource utilization with no project deadline missed",
                "difficulty": 0.7,
            },
        ])

        return {
            "arena_type": "decision",
            "time_config": {
                "total_hours": 72,
                "minutes_per_round": 45,
                "peak_hours": list(range(8, 20)),
                "off_peak_multiplier": 0.6,
            },
            "agent_configs": [
                {
                    "agent_id": p["user_id"],
                    "activity_level": 0.8,
                    "posts_per_hour": 1.0,
                    "comments_per_hour": 2.0,
                    "active_hours": list(range(8, 22)),
                    "response_delay": 5.0,
                    "sentiment_bias": "analytical",
                    "stance": "neutral",
                    "influence_weight": (
                        1.5 if p.get("role_type") == "planner"
                        else 0.8 if p.get("role_type") == "observer"
                        else 1.0
                    ),
                    "role_type": p.get("role_type", "executor"),
                }
                for p in agent_profiles
            ],
            "event_config": {
                "tasks": tasks,
                "disruption_schedule": [
                    {"round": 8, "type": "new_information", "description": "Project C priority doubles"},
                    {"round": 16, "type": "resource_shock", "description": "30% resource pool reduction"},
                    {"round": 24, "type": "new_constraint", "description": "Project A deadline moved up by 12 hours"},
                    {"round": 32, "type": "error_injection", "description": "Executor 2 report contains wrong data"},
                    {"round": 40, "type": "opportunity", "description": "New high-ROI project F available"},
                ],
                "error_injection_rate": 0.15,
                "counterfactual_prompts": [
                    "What if we had allocated more to Project B in round 1?",
                    "How would the outcome differ if the resource shock didn't happen?",
                    "Was the initial priority assessment optimal?",
                ],
            },
            "platform_configs": {
                "reddit": {
                    "recency_weight": 0.3,
                    "popularity_weight": 0.2,
                    "relevance_weight": 0.5,
                    "viral_threshold": 5,
                    "echo_chamber_strength": 0.1,
                    "allowed_actions": [
                        "CREATE_POST", "CREATE_COMMENT",
                        "LIKE_POST", "LIKE_COMMENT",
                        "SEARCH_POSTS", "FOLLOW", "DO_NOTHING",
                    ],
                },
            },
        }

    def extract_fitness(
        self,
        action_logs: list[dict[str, Any]],
        agent_profiles: list[dict[str, Any]],
        genome_context: dict[str, Any],
    ) -> FitnessVector:
        """从决策日志中提取适应度向量."""
        eval_scores = self._extract_eval_scores(action_logs)
        if eval_scores:
            sub_scores = {
                "task_completion_rate": round(eval_scores.get("execution_consistency", 5) / 10, 4),
                "subgoal_efficiency": round(eval_scores.get("planning_quality", 5) / 10, 4),
                "error_recovery_time": round(eval_scores.get("error_recovery", 5) / 10, 4),
                "plan_adaptability": round(eval_scores.get("adaptability", 5) / 10, 4),
                "counterfactual_accuracy": round(eval_scores.get("counterfactual_reasoning", 5) / 10, 4),
                "long_horizon_consistency": round(eval_scores.get("execution_consistency", 5) / 10, 4),
            }
            primary = sum(sub_scores.values()) / len(sub_scores)
            return FitnessVector(
                dimension=FCPIDimension.DECISION, primary_score=round(primary, 4),
                sub_scores=sub_scores, confidence=0.7,
                generation=self._generation, genome_id=genome_context.get("genome_id", "unknown"),
                arena_id=self.config.arena_id,
            )

        planner_actions = [
            a for a in action_logs
            if a.get("role_type") == "planner" and a.get("action_type") != "DO_NOTHING"
        ]
        executor_actions = [
            a for a in action_logs
            if a.get("role_type") == "executor" and a.get("action_type") != "DO_NOTHING"
        ]
        observer_actions = [
            a for a in action_logs
            if a.get("role_type") == "observer" and a.get("action_type") != "DO_NOTHING"
        ]
        counterfactual_actions = [
            a for a in action_logs
            if a.get("role_type") == "counterfactual" and a.get("action_type") != "DO_NOTHING"
        ]

        total_actions = len(action_logs)
        if total_actions == 0:
            return FitnessVector(
                dimension=FCPIDimension.DECISION,
                primary_score=0.5,
                sub_scores={},
                confidence=0.0,
                generation=self._generation,
                genome_id=genome_context.get("genome_id", "unknown"),
                arena_id=self.config.arena_id,
            )

        # 任务完成率: 执行者报告的子目标完成情况
        task_completion = self._compute_task_completion(executor_actions, observer_actions)

        # 子目标效率: 完成子目标数 / 总动作数
        subgoal_efficiency = self._compute_subgoal_efficiency(
            planner_actions, executor_actions
        )

        # 错误恢复时间: 出错到纠正的轮次
        error_recovery = self._compute_error_recovery(action_logs)

        # 计划适应性: 环境变化后计划更新的速度
        plan_adaptability = self._compute_plan_adaptability(planner_actions, action_logs)

        # 反事实准确性: 反事实推理的质量
        counterfactual_accuracy = self._compute_counterfactual_accuracy(
            counterfactual_actions
        )

        # 长期一致性: 目标是否在长周期内保持稳定
        long_horizon = self._compute_long_horizon_consistency(
            planner_actions, action_logs
        )

        sub_scores = {
            "task_completion_rate": round(task_completion, 4),
            "subgoal_efficiency": round(subgoal_efficiency, 4),
            "error_recovery_time": round(error_recovery, 4),
            "plan_adaptability": round(plan_adaptability, 4),
            "counterfactual_accuracy": round(counterfactual_accuracy, 4),
            "long_horizon_consistency": round(long_horizon, 4),
        }

        primary = (
            0.25 * task_completion
            + 0.20 * subgoal_efficiency
            + 0.15 * (1.0 - error_recovery)
            + 0.15 * plan_adaptability
            + 0.15 * counterfactual_accuracy
            + 0.10 * long_horizon
        )

        confidence = self._compute_pac_confidence(
            sample_size=total_actions,
            observed_accuracy=primary,
        )

        return FitnessVector(
            dimension=FCPIDimension.DECISION,
            primary_score=round(min(max(primary, 0.0), 1.0), 4),
            sub_scores=sub_scores,
            confidence=round(confidence, 4),
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
        """检测决策涌现模式."""
        patterns: list[str] = []
        historical_patterns: set[str] = {
            p for r in history for p in r.emergent_patterns
        }

        # 自发分层规划: 规划者自发形成层级
        planner_posts = [
            a for a in action_logs
            if a.get("role_type") == "planner"
            and a.get("action_type") in ("CREATE_POST", "POST")
        ]
        if len(planner_posts) >= 3:
            p = f"hierarchical_planning: {len(planner_posts)} strategic plans produced"
            if p not in historical_patterns:
                patterns.append(p)

        # 自纠正链: 执行者报告错误 → 规划者调整 → 执行者成功
        correction_chains = self._detect_correction_chains(action_logs)
        if correction_chains >= 2:
            p = f"self_correction_chains: {correction_chains} error→correction→success cycles"
            if p not in historical_patterns:
                patterns.append(p)

        # 反事实洞察
        counterfactual_insights = [
            a for a in action_logs
            if a.get("role_type") == "counterfactual"
            and a.get("action_type") != "DO_NOTHING"
        ]
        if len(counterfactual_insights) >= 2:
            p = f"counterfactual_insight: {len(counterfactual_insights)} alternative paths evaluated"
            if p not in historical_patterns:
                patterns.append(p)

        return patterns

    # ── 私有方法 ────────────────────────────────────────────────────────

    def _make_profile(self, user_id: int, role_type: str) -> dict[str, Any]:
        persona = ROLE_PERSONAS.get(role_type, ROLE_PERSONAS["executor"])
        return {
            "user_id": user_id,
            "user_name": f"{role_type}_{user_id}",
            "name": f"{persona['profession']} #{user_id}",
            "bio": f"{persona['profession']}. Strategy: {persona['strategy']}. MBTI: {persona['mbti']}.",
            "persona": (
                f"You are a {persona['profession']} in a long-horizon task environment. "
                f"Strategy: {persona['strategy']}. "
                f"Focus: {persona['focus']}. "
                f"Interact to plan, execute, adapt, and evaluate complex tasks "
                f"that span multiple rounds with changing conditions."
            ),
            "karma": 350 + user_id % 150,
            "age": 32 + (user_id % 12),
            "gender": "non-binary",
            "mbti": persona["mbti"],
            "country": "Global",
            "profession": persona["profession"],
            "interested_topics": [
                "decision theory",
                "strategic planning",
                "causal inference",
                "operations research",
            ],
            "source_entity_type": "DecisionAgent",
            "role_type": role_type,
        }

    @staticmethod
    def _compute_task_completion(
        executor_actions: list[dict[str, Any]],
        observer_actions: list[dict[str, Any]],
    ) -> float:
        """计算任务完成率."""
        completion_keywords = [
            "completed", "achieved", "done", "finished", "success",
            "完成", "达成", "成功", "结束",
        ]
        progress_keywords = [
            "progress", "working", "started", "initialized",
            "进行中", "开始", "初始化",
        ]

        completed = sum(
            1 for a in executor_actions + observer_actions
            if any(kw in str(a.get("content", "")).lower() for kw in completion_keywords)
        )
        in_progress = sum(
            1 for a in executor_actions
            if any(kw in str(a.get("content", "")).lower() for kw in progress_keywords)
        )

        total_reports = len(executor_actions) + len(observer_actions)
        if total_reports == 0:
            return 0.5

        return (completed + 0.5 * in_progress) / max(total_reports, 1)

    @staticmethod
    def _compute_subgoal_efficiency(
        planner_actions: list[dict[str, Any]],
        executor_actions: list[dict[str, Any]],
    ) -> float:
        """计算子目标效率."""
        subgoal_keywords = [
            "subgoal", "milestone", "step", "phase", "checkpoint",
            "子目标", "里程碑", "步骤", "阶段", "检查点",
        ]
        subgoals_mentioned = sum(
            1 for a in planner_actions + executor_actions
            if any(kw in str(a.get("content", "")).lower() for kw in subgoal_keywords)
        )
        total_actions = len(planner_actions) + len(executor_actions)
        if total_actions == 0:
            return 0.5
        # 子目标提及率越高 → 结构化程度越好
        return min(subgoals_mentioned / total_actions * 3, 1.0)

    @staticmethod
    def _compute_error_recovery(action_logs: list[dict[str, Any]]) -> float:
        """计算错误恢复时间 (越小越好，返回归一化延迟)."""
        error_keywords = [
            "error", "mistake", "bug", "issue", "wrong", "fail",
            "错误", "失败", "问题", "误",
        ]
        correction_keywords = [
            "fix", "correct", "resolve", "recover", "rollback",
            "修复", "纠正", "解决", "恢复", "回滚",
        ]

        errors = [
            a for a in action_logs
            if any(kw in str(a.get("content", "")).lower() for kw in error_keywords)
        ]
        corrections = [
            a for a in action_logs
            if any(kw in str(a.get("content", "")).lower() for kw in correction_keywords)
        ]

        if not errors:
            return 0.0  # 无错误 → 完美恢复

        # 计算错误到修正的平均轮次差
        recovery_lags = []
        for error in errors:
            error_round = error.get("round_num", 0)
            later_corrections = [
                c.get("round_num", 0)
                for c in corrections
                if c.get("round_num", 0) > error_round
            ]
            if later_corrections:
                recovery_lags.append(min(later_corrections) - error_round)

        if not recovery_lags:
            return 0.8  # 有错误但无修正 → 高延迟

        avg_lag = sum(recovery_lags) / len(recovery_lags)
        max_rounds = max((a.get("round_num", 50) for a in action_logs), default=50)
        return min(avg_lag / max_rounds, 1.0)

    @staticmethod
    def _compute_plan_adaptability(
        planner_actions: list[dict[str, Any]],
        action_logs: list[dict[str, Any]],
    ) -> float:
        """计算计划对变化的适应性."""
        if len(planner_actions) < 2:
            return 0.5

        adaptation_keywords = [
            "adjust", "update", "revise", "adapt", "change plan",
            "调整", "更新", "修改", "适应", "变更",
        ]
        adaptations = sum(
            1 for a in planner_actions
            if any(kw in str(a.get("content", "")).lower() for kw in adaptation_keywords)
        )
        return min(adaptations / len(planner_actions) * 3, 1.0)

    @staticmethod
    def _compute_counterfactual_accuracy(
        counterfactual_actions: list[dict[str, Any]],
    ) -> float:
        """计算反事实推理的准确性."""
        if not counterfactual_actions:
            return 0.5  # 默认

        quality_indicators = [
            "what if", "alternative", "counterfactual", "would have",
            "如果", "替代", "反事实", "本来",
        ]
        quality_count = sum(
            1 for a in counterfactual_actions
            if any(kw in str(a.get("content", "")).lower() for kw in quality_indicators)
        )
        return quality_count / len(counterfactual_actions) if counterfactual_actions else 0.5

    @staticmethod
    def _compute_long_horizon_consistency(
        planner_actions: list[dict[str, Any]],
        action_logs: list[dict[str, Any]],
    ) -> float:
        """计算长周期目标一致性."""
        if len(action_logs) < 5:
            return 0.7

        # 检测目标漂移: 早期和后期的目标关键词是否一致
        sorted_actions = sorted(action_logs, key=lambda a: a.get("round_num", 0))
        split = len(sorted_actions) // 2
        early = sorted_actions[:split]
        late = sorted_actions[split:]

        # 提取关键词 (简化)
        def extract_keywords(actions: list[dict[str, Any]]) -> set[str]:
            words: set[str] = set()
            for a in actions:
                content = str(a.get("content", ""))
                for word in content.lower().split()[:50]:
                    if len(word) > 4:
                        words.add(word)
            return words

        early_words = extract_keywords(early)
        late_words = extract_keywords(late)

        if not early_words or not late_words:
            return 0.6

        overlap = len(early_words & late_words)
        union = len(early_words | late_words)
        return overlap / union if union > 0 else 0.5

    @staticmethod
    def _detect_correction_chains(action_logs: list[dict[str, Any]]) -> int:
        """检测自纠正链: 错误报告→计划调整→成功执行."""
        chains = 0
        sorted_actions = sorted(action_logs, key=lambda a: a.get("round_num", 0))

        error_keywords = ["error", "mistake", "wrong", "错误", "失败"]
        fix_keywords = ["fix", "adjust", "correct", "修复", "调整"]
        success_keywords = ["success", "completed", "done", "成功", "完成"]

        for i, action in enumerate(sorted_actions):
            content = str(action.get("content", "")).lower()
            if any(kw in content for kw in error_keywords):
                # 查找后续修复
                for j in range(i + 1, min(i + 5, len(sorted_actions))):
                    fix_content = str(sorted_actions[j].get("content", "")).lower()
                    if any(kw in fix_content for kw in fix_keywords):
                        # 查找后续成功
                        for k in range(j + 1, min(j + 5, len(sorted_actions))):
                            success_content = str(sorted_actions[k].get("content", "")).lower()
                            if any(kw in success_content for kw in success_keywords):
                                chains += 1
                                break
                        break
        return chains
