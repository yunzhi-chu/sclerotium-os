"""Arena 1: 编码自主性竞技场 (Coding Arena) — FCPI 权重 25%.

将 DarwinianGodelMachine 生成的代码变体投入代码评审 Agent 社会，
通过社会涌现共识评估代码质量，而非运行固定测试套件。

Agent 类型:
    - 资深工程师 (senior_engineer): 审查架构/可维护性
    - 安全专家 (security_expert): 审查安全漏洞
    - 性能分析师 (performance_analyst): 审查效率
    - 初级开发者 (junior_dev): 审查可读性/学习曲线
    - QA 测试员 (qa_tester): 审查边界情况/测试覆盖

动作类型:
    - REVIEW: 发表代码评审 (包含评分和建议)
    - FORK: 分叉代码并修改
    - MERGE: 合并他人修改
    - APPROVE: 认可代码
    - REJECT: 拒绝代码
    - COMMENT: 讨论具体实现细节

适应度提取:
    coding_fitness = {
        review_approval_rate: 正评 / 总评
        fork_adoption_rate: 被采纳分叉 / 总分叉
        bug_discovery_speed: 首次 bug 发现轮次
        refactoring_quality: 重构后评分提升幅度
        code_survival_duration: 代码被持续引用的轮数
        controversy_index: 评审分歧度
    }
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .arena_base import (
    ArenaBase,
    ArenaConfig,
    ArenaResult,
    FCPIDimension,
    FitnessVector,
)

logger = logging.getLogger(__name__)

# ── Agent 角色定义 ─────────────────────────────────────────────────────────

CODING_AGENT_TYPES = (
    "senior_engineer",
    "security_expert",
    "performance_analyst",
    "junior_dev",
    "qa_tester",
)

CODING_ACTION_TYPES = (
    "REVIEW",
    "FORK",
    "MERGE",
    "APPROVE",
    "REJECT",
    "COMMENT",
)

# 角色人格模板
ROLE_PERSONAS: dict[str, dict[str, str]] = {
    "senior_engineer": {
        "profession": "Senior Software Engineer",
        "mbti": "INTJ",
        "focus": "architecture, maintainability, design patterns, scalability",
        "review_style": "thorough and constructive, emphasizes long-term maintainability",
    },
    "security_expert": {
        "profession": "Application Security Engineer",
        "mbti": "ISTJ",
        "focus": "OWASP Top 10, injection attacks, authentication, data leaks, sandbox escapes",
        "review_style": "adversarial and meticulous, thinks like an attacker",
    },
    "performance_analyst": {
        "profession": "Performance Engineer",
        "mbti": "ISTP",
        "focus": "algorithmic complexity, memory usage, I/O patterns, caching, concurrency",
        "review_style": "data-driven, uses benchmarks and profiling results",
    },
    "junior_dev": {
        "profession": "Junior Developer",
        "mbti": "ENFP",
        "focus": "readability, documentation, learning curve, onboarding experience",
        "review_style": "curious and questioning, represents new team members",
    },
    "qa_tester": {
        "profession": "QA Test Engineer",
        "mbti": "ESTJ",
        "focus": "edge cases, boundary conditions, error handling, test coverage, regression",
        "review_style": "systematic and exhaustive, thinks about what could go wrong",
    },
}


class CodingArena(ArenaBase):
    """编码自主性竞技场.

    模拟开源社区的代码评审过程，通过 Agent 社会共识
    评估由 Mycelium 基因组生成的代码质量。
    """

    def __init__(
        self,
        config: ArenaConfig | None = None,
        work_dir: Any = None,
    ) -> None:
        if config is None:
            config = ArenaConfig(
                arena_id=f"coding_{id(self):x}",
                dimension=FCPIDimension.CODING,
                max_rounds=30,
                min_agents=5,
                max_agents=25,
                agent_types=CODING_AGENT_TYPES,
                platform_types=("reddit",),  # Reddit 风格深度评审
                temperature=0.4,  # 代码评审需要精确
                extra={
                    "review_rounds_min": 3,
                    "fork_threshold": 0.6,
                    "merge_threshold": 0.7,
                },
            )
        super().__init__(config, work_dir)

    # ── 抽象方法实现 ────────────────────────────────────────────────────

    def build_agent_profiles(
        self, genome_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """构建代码评审 Agent Profile 列表.

        每个代码片段生成 3-5 个评审 Agent，角色循环分配。
        如果提供了外部 profile_generator，优先使用。
        """
        if self._profile_generator:
            return self._profile_generator.generate_profiles(self.config, genome_context)

        code_snippets = genome_context.get("code_snippets", [{"id": "default", "source": "N/A"}])
        profiles: list[dict[str, Any]] = []
        user_id = 1000

        for snippet in code_snippets:
            for role_type in self.config.agent_types:
                persona = ROLE_PERSONAS.get(role_type, ROLE_PERSONAS["senior_engineer"])
                profile = {
                    "user_id": user_id,
                    "user_name": f"{role_type}_{user_id}",
                    "name": f"{persona['profession']} #{user_id}",
                    "bio": (
                        f"{persona['profession']} specializing in {persona['focus']}. "
                        f"MBTI: {persona['mbti']}. "
                        f"Review style: {persona['review_style']}."
                    ),
                    "persona": self._build_code_reviewer_persona(role_type, persona, snippet),
                    "karma": 500 + user_id,
                    "age": 25 + (user_id % 20),
                    "gender": "non-binary",
                    "mbti": persona["mbti"],
                    "country": "Global",
                    "profession": persona["profession"],
                    "interested_topics": [
                        persona["focus"].split(",")[0].strip(),
                        "code review",
                        "software engineering",
                        snippet.get("language", "Python"),
                    ],
                    "source_entity_type": "CodeReviewer",
                    "role_type": role_type,
                }
                profiles.append(profile)
                user_id += 1

        logger.info(
            "CodingArena: built %d reviewer profiles for %d snippets",
            len(profiles), len(code_snippets),
        )
        return profiles

    def build_simulation_config(
        self,
        agent_profiles: list[dict[str, Any]],
        genome_context: dict[str, Any],
    ) -> dict[str, Any]:
        """构建代码评审仿真配置.

        仿真结构:
            1. 代码片段 Agent"发布"代码 (初始帖)
            2. 评审 Agent 发现、分析、评论
            3. FORK/MERGE 动作模拟代码修改
            4. 共识形成: APPROVE/REJECT 动作
        """
        code_snippets = genome_context.get("code_snippets", [])
        event_config = {
            "initial_posts": [],
            "review_focus_areas": [
                "correctness",
                "security",
                "performance",
                "readability",
                "test_coverage",
            ],
            "code_snippets": code_snippets,
        }

        # 为每个代码片段创建初始"发布帖"
        for i, snippet in enumerate(code_snippets):
            event_config["initial_posts"].append({
                "poster_agent_id": f"code_author_{i}",
                "title": f"Code Review Request: {snippet.get('name', f'Snippet #{i}')}",
                "content": (
                    f"```{snippet.get('language', 'python')}\n"
                    f"{snippet.get('source', '# No code provided')}\n"
                    f"```\n\n"
                    f"Context: {snippet.get('context', 'No context provided')}\n"
                    f"Please review for: correctness, security, performance, readability, test coverage."
                ),
                "tags": ["code-review", snippet.get("language", "python"), "evolution"],
            })

        return {
            "arena_type": "coding",
            "time_config": {
                "total_hours": 48,
                "minutes_per_round": 60,
                "peak_hours": [9, 10, 11, 14, 15, 16],
                "off_peak_multiplier": 0.3,
            },
            "agent_configs": [
                {
                    "agent_id": p["user_id"],
                    "activity_level": 0.8,
                    "posts_per_hour": 1.5,
                    "comments_per_hour": 4.0,
                    "active_hours": [9, 10, 11, 14, 15, 16, 17],
                    "response_delay": 5.0,
                    "sentiment_bias": "constructive",
                    "stance": "neutral",
                    "influence_weight": 1.0,
                    "role_type": p.get("role_type", "senior_engineer"),
                }
                for p in agent_profiles
            ],
            "event_config": event_config,
            "platform_configs": {
                "reddit": {
                    "recency_weight": 0.3,
                    "popularity_weight": 0.2,
                    "relevance_weight": 0.5,
                    "viral_threshold": 5,
                    "echo_chamber_strength": 0.1,
                    "allowed_actions": list(CODING_ACTION_TYPES),
                },
            },
        }

    def extract_fitness(
        self,
        action_logs: list[dict[str, Any]],
        agent_profiles: list[dict[str, Any]],
        genome_context: dict[str, Any],
    ) -> FitnessVector:
        """从代码评审日志中提取适应度向量.

        核心逻辑:
            - REVIEW 动作包含评分 → approval_rate
            - FORK 动作 → 代码被修改的频率
            - MERGE 动作 → 修改被采纳的频率
            - APPROVE/REJECT → 最终共识
        """
        # 优先使用LLM评估分数 (LiveAgentSimulator)
        eval_scores = self._extract_eval_scores(action_logs)
        if eval_scores:
            sub_scores = {
                "review_approval_rate": round(eval_scores.get("code_correctness", 5) / 10, 4),
                "fork_adoption_rate": round(eval_scores.get("collaboration_quality", 5) / 10, 4),
                "bug_discovery_speed": round(eval_scores.get("security_awareness", 5) / 10, 4),
                "refactoring_quality": round(eval_scores.get("innovation_in_fixes", 5) / 10, 4),
                "code_survival_duration": 0.5,
                "controversy_index": 0.3,
            }
            primary = sum(sub_scores.values()) / len(sub_scores)
            return FitnessVector(
                dimension=FCPIDimension.CODING, primary_score=round(primary, 4),
                sub_scores=sub_scores, confidence=0.7,
                generation=self._generation, genome_id=genome_context.get("genome_id", "unknown"),
                arena_id=self.config.arena_id,
            )

        reviews = [a for a in action_logs if a.get("action_type") == "REVIEW"]
        forks = [a for a in action_logs if a.get("action_type") == "FORK"]
        merges = [a for a in action_logs if a.get("action_type") == "MERGE"]
        approves = [a for a in action_logs if a.get("action_type") == "APPROVE"]
        rejects = [a for a in action_logs if a.get("action_type") == "REJECT"]

        total_reviews = len(reviews)
        total_forks = len(forks)
        total_actions = len(action_logs)

        # 评审通过率: APPROVE / (APPROVE + REJECT)
        total_decisions = len(approves) + len(rejects)
        approval_rate = len(approves) / total_decisions if total_decisions > 0 else 0.5

        # 分叉采纳率: MERGE / FORK
        fork_adoption = len(merges) / total_forks if total_forks > 0 else 0.5

        # Bug 发现速度: 第一个安全相关 REVIEW 出现的轮次
        bug_rounds = [
            a.get("round_num", 999)
            for a in reviews
            if any(
                kw in str(a.get("content", "")).lower()
                for kw in ["bug", "vulnerability", "issue", "error", "security", "缺陷", "漏洞"]
            )
        ]
        bug_discovery_speed = (
            min(bug_rounds) / self.config.max_rounds if bug_rounds else 1.0
        )

        # 重构质量: 分叉后评分是否提升 (FORK 前后 REVIEW 分数比较)
        refactoring_quality = self._compute_refactoring_quality(action_logs)

        # 代码存活: 代码被引用/讨论的轮数跨度
        active_rounds = {a.get("round_num", 0) for a in action_logs if a.get("action_type") != "DO_NOTHING"}
        survival_duration = len(active_rounds) / self.config.max_rounds if active_rounds else 0.0

        # 争议指数: 评审分歧度 (高方差 = 有意义的争论)
        controversy = self._compute_controversy(reviews)

        sub_scores = {
            "review_approval_rate": round(approval_rate, 4),
            "fork_adoption_rate": round(fork_adoption, 4),
            "bug_discovery_speed": round(bug_discovery_speed, 4),
            "refactoring_quality": round(refactoring_quality, 4),
            "code_survival_duration": round(survival_duration, 4),
            "controversy_index": round(controversy, 4),
        }

        # 主分数: 加权合成 (权重来自计划文档)
        primary = (
            0.30 * approval_rate
            + 0.20 * fork_adoption
            + 0.15 * (1.0 - bug_discovery_speed)  # 更快发现 = 更高质量意识
            + 0.15 * refactoring_quality
            + 0.10 * survival_duration
            + 0.10 * controversy
        )

        # PAC 置信度
        confidence = self._compute_pac_confidence(
            sample_size=total_reviews + total_forks,
            observed_accuracy=approval_rate,
        )

        return FitnessVector(
            dimension=FCPIDimension.CODING,
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
        """检测代码评审中的涌现模式."""
        patterns: list[str] = []
        historical_patterns: set[str] = {
            p for r in history for p in r.emergent_patterns
        }

        # 模式 1: 评审共识快速形成 (所有评审者快速达成一致)
        approves = [a for a in action_logs if a.get("action_type") == "APPROVE"]
        rejects = [a for a in action_logs if a.get("action_type") == "REJECT"]
        if approves and not rejects and len(approves) >= 3:
            p = "rapid_consensus: unanimous approval without dissent"
            if p not in historical_patterns:
                patterns.append(p)

        # 模式 2: 安全专家发现隐藏漏洞
        security_reviews = [
            a for a in action_logs
            if a.get("action_type") == "REVIEW"
            and "security" in str(a.get("tags", [])).lower()
        ]
        if len(security_reviews) > len(action_logs) * 0.1:
            p = "security_focus: heightened security awareness in reviews"
            if p not in historical_patterns:
                patterns.append(p)

        # 模式 3: 跨角色协作 (不同角色互补评审)
        role_types_in_merges = {
            a.get("role_type") for a in action_logs if a.get("action_type") == "MERGE"
        }
        if len(role_types_in_merges) >= 3:
            p = f"cross_role_collaboration: {len(role_types_in_merges)} roles contributed merges"
            if p not in historical_patterns:
                patterns.append(p)

        # 模式 4: 代码自修复涌现 (FORK→MERGE 链)
        fork_merge_chains = self._detect_fork_merge_chains(action_logs)
        if fork_merge_chains >= 3:
            p = f"self_repair_chains: {fork_merge_chains} fork→merge repair chains detected"
            if p not in historical_patterns:
                patterns.append(p)

        return patterns

    # ── 私有方法 ────────────────────────────────────────────────────────

    def _build_code_reviewer_persona(
        self, role_type: str, persona: dict[str, str], snippet: dict[str, Any]
    ) -> str:
        """构建代码评审者的详细人格描述."""
        return (
            f"You are a {persona['profession']} with {persona['review_style']}. "
            f"Your expertise covers {persona['focus']}. "
            f"You are reviewing code in {snippet.get('language', 'Python')}. "
            f"Provide detailed, actionable feedback. "
            f"Rate code on a scale of 1-10 for: correctness, security, "
            f"performance, readability, and testability. "
            f"Be {persona['review_style']} in your approach."
        )

    @staticmethod
    def _compute_refactoring_quality(action_logs: list[dict[str, Any]]) -> float:
        """计算重构质量: FORK 前后评分变化."""
        forks = [a for a in action_logs if a.get("action_type") == "FORK"]
        if not forks:
            return 0.5

        improvements = 0
        for fork in forks:
            fork_round = fork.get("round_num", 0)
            # 查找 FORK 前后的 REVIEW 分数
            pre_reviews = [
                a for a in action_logs
                if a.get("action_type") == "REVIEW"
                and a.get("round_num", 0) < fork_round
            ]
            post_reviews = [
                a for a in action_logs
                if a.get("action_type") == "REVIEW"
                and a.get("round_num", 0) > fork_round
            ]
            # 简单启发式: 如果 FORK 后好评增多，视为改进
            pre_approve = sum(1 for r in pre_reviews if "approve" in str(r).lower())
            post_approve = sum(1 for r in post_reviews if "approve" in str(r).lower())
            if post_approve > pre_approve:
                improvements += 1

        return improvements / len(forks) if forks else 0.5

    @staticmethod
    def _compute_controversy(reviews: list[dict[str, Any]]) -> float:
        """计算争议指数 — 健康的争论表明深度审查."""
        if len(reviews) < 2:
            return 0.0
        # 简化: 评审中不同观点越多，争议指数越高
        # 通过角色类型多样性来近似
        role_types = {r.get("role_type", "unknown") for r in reviews}
        diversity = len(role_types) / len(CODING_AGENT_TYPES)
        return min(diversity * 1.5, 1.0)  # 上限 1.0

    @staticmethod
    def _detect_fork_merge_chains(action_logs: list[dict[str, Any]]) -> int:
        """检测 FORK→MERGE 的修复链数量."""
        chains = 0
        sorted_actions = sorted(action_logs, key=lambda a: a.get("round_num", 0))
        for i, action in enumerate(sorted_actions):
            if action.get("action_type") == "FORK":
                # 查找后续的 MERGE
                for later in sorted_actions[i + 1 :]:
                    if later.get("action_type") == "MERGE":
                        chains += 1
                        break
                    # 如果中间有新的 FORK，链断裂
                    if later.get("action_type") == "FORK":
                        break
        return chains
