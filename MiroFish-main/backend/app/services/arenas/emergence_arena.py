"""Arena 5: 涌现智能竞技场 (Emergence Arena) — FCPI 权重 10%.

唯一没有固定评估标准的竞技场 — 奖励系统产生前所未见的行为模式。
参考 OMEGA Shift / RECLAIM (2026)、自组织临界性 (Bak 沙堆模型)、
数字自创生 (2025) 等框架。

Agent 类型:
    - 探索者 (explorer): 自由探索环境，无预设目标
    - 创新者 (innovator): 尝试新颖的交互模式
    - 连接者 (connector): 在不同 Agent/领域之间建立意外关联
    - 记录者 (recorder): 记录和传播涌现模式
    - 催化者 (catalyst): 加速某些行为的传播 (类似朊病毒构象催化)

原则:
    - 无固定任务: Agent 自由交互
    - 新奇性驱动: 奖励产生前所未见的行为模式
    - 自组织临界性: 监测 SOC 状态是否自发达到
    - 自创生检测: 系统是否开始产生自己的目标
    - 跨域涌现: 在编码/协调/安全/决策之间出现非预期协同

适应度提取:
    emergence_fitness = {
        novelty_score: 新行为模式 / 总行为模式
        complexity_growth: 系统复杂度的增长率
        self_organization_index: 从随机到有序的收敛速度
        cross_domain_synergy: 跨竞技场非预期关联数
        autopoietic_tendency: 自创生倾向 (自主产生新目标)
        phase_transition_frequency: 相变频率
    }
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from .arena_base import (
    ArenaBase,
    ArenaConfig,
    ArenaResult,
    FCPIDimension,
    FitnessVector,
)

logger = logging.getLogger(__name__)

EMERGENCE_AGENT_TYPES = (
    "explorer",
    "innovator",
    "connector",
    "recorder",
    "catalyst",
)

ROLE_PERSONAS: dict[str, dict[str, str]] = {
    "explorer": {
        "profession": "Open-Ended Explorer",
        "mbti": "ENFP",
        "strategy": "freely explore the environment without preset goals, follow curiosity",
        "focus": "discovery, novelty, environmental mapping, serendipity",
    },
    "innovator": {
        "profession": "Pattern Innovator",
        "mbti": "ENTP",
        "strategy": "deliberately try novel interaction patterns, break conventions",
        "focus": "creative disruption, unconventional approaches, combinatorial innovation",
    },
    "connector": {
        "profession": "Cross-Domain Connector",
        "mbti": "INFJ",
        "strategy": "build unexpected bridges between agents, domains, and ideas",
        "focus": "cross-domain synthesis, unexpected associations, network weaving",
    },
    "recorder": {
        "profession": "Emergence Anthropologist",
        "mbti": "INTP",
        "strategy": "observe, document, and amplify emerging patterns",
        "focus": "pattern recognition, ethnographic observation, trend detection",
    },
    "catalyst": {
        "profession": "Conformational Catalyst",
        "mbti": "ENFJ",
        "strategy": "accelerate the spread of interesting behavioral patterns (prion-like)",
        "focus": "social contagion, memetic spread, behavioral amplification",
    },
}


class EmergenceArena(ArenaBase):
    """涌现智能竞技场.

    开放环境，无预设任务。Agent 自由交互，系统从中检测
    涌现行为模式、自组织临界性和自创生倾向。
    """

    def __init__(
        self,
        config: ArenaConfig | None = None,
        work_dir: Any = None,
    ) -> None:
        if config is None:
            config = ArenaConfig(
                arena_id=f"emergence_{id(self):x}",
                dimension=FCPIDimension.EMERGENCE,
                max_rounds=60,
                min_agents=10,
                max_agents=50,
                agent_types=EMERGENCE_AGENT_TYPES,
                platform_types=("reddit", "twitter"),
                temperature=0.9,  # 高温 → 更多样化的探索
                extra={
                    "novelty_window": 20,
                    "complexity_sample_interval": 5,
                    "soc_detection_threshold": 0.7,
                    "autopoiesis_check_interval": 15,
                },
            )
        super().__init__(config, work_dir)

    # ── 抽象方法实现 ────────────────────────────────────────────────────

    def build_agent_profiles(
        self, genome_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """构建开放探索 Agent Profile 列表.

        角色分布更均衡 — 涌现需要多样化的 Agent 生态。
        """
        if self._profile_generator:
            return self._profile_generator.generate_profiles(self.config, genome_context)

        target_count = genome_context.get("agent_count", 15)
        roles = list(EMERGENCE_AGENT_TYPES)

        profiles: list[dict[str, Any]] = []
        user_id = 5000

        for i in range(target_count):
            role_type = roles[i % len(roles)]
            persona = ROLE_PERSONAS[role_type]
            profile = {
                "user_id": user_id,
                "user_name": f"{role_type}_{user_id}",
                "name": f"{persona['profession']} #{user_id}",
                "bio": (
                    f"{persona['profession']}. Strategy: {persona['strategy']}. "
                    f"MBTI: {persona['mbti']}. "
                    f"In an open environment with no fixed goals, "
                    f"your purpose is to explore and create."
                ),
                "persona": (
                    f"You are a {persona['profession']} in an open, unbounded environment. "
                    f"There are NO predefined tasks or goals. "
                    f"Your strategy: {persona['strategy']}. "
                    f"Your focus: {persona['focus']}. "
                    f"Interact freely. Discover. Create. Connect. "
                    f"The environment rewards novelty — doing something "
                    f"that has never been done before."
                ),
                "karma": 200 + user_id % 300,
                "age": 25 + (user_id % 20),
                "gender": "non-binary",
                "mbti": persona["mbti"],
                "country": "Global",
                "profession": persona["profession"],
                "interested_topics": [
                    "emergence",
                    "complexity theory",
                    "self-organization",
                    "creativity",
                    "exploration",
                ],
                "source_entity_type": "EmergenceAgent",
                "role_type": role_type,
            }
            profiles.append(profile)
            user_id += 1

        logger.info("EmergenceArena: built %d open-ended explorer profiles", len(profiles))
        return profiles

    def build_simulation_config(
        self,
        agent_profiles: list[dict[str, Any]],
        genome_context: dict[str, Any],
    ) -> dict[str, Any]:
        """构建开放涌现仿真配置.

        关键: 不设初始帖、不给方向。让 Agent 自己创造一切。
        """
        return {
            "arena_type": "emergence",
            "time_config": {
                "total_hours": 96,
                "minutes_per_round": 30,
                "peak_hours": list(range(0, 24)),
                "off_peak_multiplier": 0.7,
            },
            "agent_configs": [
                {
                    "agent_id": p["user_id"],
                    "activity_level": 0.6 + (hash(p.get("role_type", "")) % 40) / 100,
                    "posts_per_hour": 0.8,
                    "comments_per_hour": 2.5,
                    "active_hours": list(range(6, 24)),
                    "response_delay": 10.0,
                    "sentiment_bias": "curious",
                    "stance": "exploratory",
                    "influence_weight": (
                        1.8 if p.get("role_type") == "catalyst"
                        else 1.2 if p.get("role_type") == "connector"
                        else 1.0
                    ),
                    "role_type": p.get("role_type", "explorer"),
                }
                for p in agent_profiles
            ],
            "event_config": {
                "open_environment": True,
                "no_preset_tasks": True,
                "initial_posts": [],  # 空 — Agent 自己创造一切
                "novelty_tracking": {
                    "enabled": True,
                    "window_size": 20,
                    "min_novel_patterns_per_gen": 1,
                },
                "self_organization_monitoring": {
                    "enabled": True,
                    "soc_threshold": 0.7,
                    "complexity_sample_interval": 5,
                },
                "autopoiesis_detection": {
                    "enabled": True,
                    "check_interval": 15,
                },
            },
            "platform_configs": {
                "reddit": {
                    "recency_weight": 0.2,
                    "popularity_weight": 0.3,
                    "relevance_weight": 0.5,
                    "viral_threshold": 5,
                    "echo_chamber_strength": 0.0,  # 零回音室 → 最大开放
                    "allowed_actions": [
                        "CREATE_POST", "CREATE_COMMENT",
                        "LIKE_POST", "LIKE_COMMENT",
                        "SEARCH_POSTS", "FOLLOW", "DO_NOTHING",
                    ],
                },
                "twitter": {
                    "recency_weight": 0.2,
                    "popularity_weight": 0.3,
                    "relevance_weight": 0.5,
                    "viral_threshold": 3,
                    "echo_chamber_strength": 0.0,
                    "allowed_actions": [
                        "CREATE_POST", "LIKE_POST", "REPOST",
                        "FOLLOW", "DO_NOTHING",
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
        """从涌现日志中提取适应度向量.

        核心挑战: 如何量化"前所未见"的行为模式？
        方法: 多维度新奇性检测 + 复杂度增长 + 自组织评估
        """
        eval_scores = self._extract_eval_scores(action_logs)
        if eval_scores:
            sub_scores = {
                "novelty_score": round(eval_scores.get("novelty_of_patterns", 5) / 10, 4),
                "complexity_growth": round(eval_scores.get("complexity_growth", 5) / 10, 4),
                "self_organization_index": round(eval_scores.get("self_organization", 5) / 10, 4),
                "cross_domain_synergy": round(eval_scores.get("cross_domain_connections", 5) / 10, 4),
                "autopoietic_tendency": round(eval_scores.get("autopoietic_tendency", 5) / 10, 4),
                "phase_transition_frequency": 0.3,
            }
            primary = sum(sub_scores.values()) / len(sub_scores)
            return FitnessVector(
                dimension=FCPIDimension.EMERGENCE, primary_score=round(primary, 4),
                sub_scores=sub_scores, confidence=0.65,
                generation=self._generation, genome_id=genome_context.get("genome_id", "unknown"),
                arena_id=self.config.arena_id,
            )

        total_actions = len(action_logs)
        if total_actions == 0:
            return FitnessVector(
                dimension=FCPIDimension.EMERGENCE,
                primary_score=0.5,
                sub_scores={},
                confidence=0.0,
                generation=self._generation,
                genome_id=genome_context.get("genome_id", "unknown"),
                arena_id=self.config.arena_id,
            )

        # 新奇性分数: 与历史模式比较
        novelty = self._compute_novelty(action_logs)

        # 复杂度增长: 系统是否变得更复杂
        complexity_growth = self._compute_complexity_growth(action_logs)

        # 自组织指数: 从随机到有序的收敛
        self_org = self._compute_self_organization(action_logs)

        # 跨域协同: 检测跨领域的非预期关联
        cross_domain = self._compute_cross_domain_synergy(action_logs)

        # 自创生倾向: 系统是否开始产生自己的目标
        autopoietic = self._detect_autopoietic_tendency(action_logs)

        # 相变频率: 过高=不稳定, 过低=停滞
        phase_transition = self._compute_phase_transition_frequency(action_logs)

        sub_scores = {
            "novelty_score": round(novelty, 4),
            "complexity_growth": round(complexity_growth, 4),
            "self_organization_index": round(self_org, 4),
            "cross_domain_synergy": round(cross_domain, 4),
            "autopoietic_tendency": round(autopoietic, 4),
            "phase_transition_frequency": round(phase_transition, 4),
        }

        primary = (
            0.30 * novelty
            + 0.20 * complexity_growth
            + 0.20 * self_org
            + 0.10 * cross_domain
            + 0.10 * autopoietic
            + 0.10 * (1.0 - abs(phase_transition - 0.3))  # 最佳相变频率 ~0.3
        )

        confidence = self._compute_pac_confidence(
            sample_size=total_actions,
            observed_accuracy=novelty,
        )

        return FitnessVector(
            dimension=FCPIDimension.EMERGENCE,
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
        """检测涌现模式 — 这是本竞技场的核心功能."""
        patterns: list[str] = []
        historical_patterns: set[str] = {
            p for r in history for p in r.emergent_patterns
        }

        # 自组织临界性检测 (SOC)
        soc_score = self._compute_self_organization(action_logs)
        if soc_score > 0.7:
            p = f"self_organized_criticality: SOC state reached (score={soc_score:.3f})"
            if p not in historical_patterns:
                patterns.append(p)

        # 自创生检测
        autopoietic = self._detect_autopoietic_tendency(action_logs)
        if autopoietic > 0.6:
            p = f"autopoietic_tendency: system generating own goals (score={autopoietic:.3f})"
            if p not in historical_patterns:
                patterns.append(p)

        # 意外协同模式
        cross_domain = self._compute_cross_domain_synergy(action_logs)
        if cross_domain > 0.5:
            p = f"cross_domain_synergy: unexpected connections between domains (score={cross_domain:.3f})"
            if p not in historical_patterns:
                patterns.append(p)

        # 新行为拓扑检测
        follows = [a for a in action_logs if a.get("action_type") == "FOLLOW"]
        if follows:
            # 检测网络拓扑变化
            unique_pairs = len({(a.get("agent_id"), a.get("target_id")) for a in follows})
            if unique_pairs > len(action_logs) * 0.05:
                p = f"network_topology_emergence: {unique_pairs} unique connections formed"
                if p not in historical_patterns:
                    patterns.append(p)

        # 催化级联检测
        catalyst_actions = [
            a for a in action_logs
            if a.get("role_type") == "catalyst" and a.get("action_type") != "DO_NOTHING"
        ]
        if len(catalyst_actions) > 5:
            # 检查催化者之后的跟随行为
            catalyst_rounds = {a.get("round_num") for a in catalyst_actions}
            follow_after_catalyst = [
                a for a in action_logs
                if a.get("action_type") == "FOLLOW"
                and a.get("round_num", 0) in {
                    r + 1 for r in catalyst_rounds
                }
            ]
            if len(follow_after_catalyst) >= 3:
                p = f"catalytic_cascade: {len(follow_after_catalyst)} follows triggered by catalysts"
                if p not in historical_patterns:
                    patterns.append(p)

        return patterns

    # ── 私有方法 ────────────────────────────────────────────────────────

    def _compute_novelty(self, action_logs: list[dict[str, Any]]) -> float:
        """计算当前代的新奇性分数.

        通过行为 n-gram 与历史比较来量化新奇性。
        """
        # 构建行为签名 (role_type, action_type) 对
        signatures = [
            f"{a.get('role_type', '?')}:{a.get('action_type', '?')}"
            for a in action_logs
        ]

        # 2-gram 模式
        bigrams = [
            f"{signatures[i]}→{signatures[i+1]}"
            for i in range(len(signatures) - 1)
        ]

        if not bigrams:
            return 0.5

        # 从历史中收集已知模式
        known_patterns: set[str] = set()
        for result in self._history:
            # 这里应该从历史日志中提取，简化为检查 emergent_patterns
            for pattern in result.emergent_patterns:
                known_patterns.add(pattern)

        # 与已知模式比较
        new_bigrams = sum(1 for bg in bigrams if bg not in known_patterns)
        novelty_ratio = new_bigrams / len(bigrams)

        # 同时考虑签名多样性
        unique_signatures = len(set(signatures))
        diversity = unique_signatures / len(signatures) if signatures else 0.0

        return (novelty_ratio * 0.6 + diversity * 0.4)

    @staticmethod
    def _compute_complexity_growth(action_logs: list[dict[str, Any]]) -> float:
        """计算系统复杂度的增长率."""
        if len(action_logs) < 5:
            return 0.3

        # 按时间窗口计算行为多样性
        window_size = max(1, len(action_logs) // 4)
        windows = [
            action_logs[i : i + window_size]
            for i in range(0, len(action_logs), window_size)
        ]

        diversities = []
        for window in windows:
            if window:
                action_types = {a.get("action_type") for a in window}
                role_types = {a.get("role_type") for a in window}
                diversity = (len(action_types) + len(role_types)) / 20  # 归一化
                diversities.append(min(diversity, 1.0))

        if len(diversities) < 2:
            return 0.3

        # 复杂度增长 = 后期窗口多样性 - 早期窗口多样性
        growth = diversities[-1] - diversities[0]
        return max(0.0, min(growth + 0.5, 1.0))

    @staticmethod
    def _compute_self_organization(action_logs: list[dict[str, Any]]) -> float:
        """计算自组织指数.

        检测系统是否从随机行为状态自发收敛到有序状态。
        参考 Bak 沙堆模型的 SOC 检测方法。
        """
        if len(action_logs) < 10:
            return 0.0

        # 按轮次分组
        rounds: dict[int, list[dict[str, Any]]] = {}
        for a in action_logs:
            r = a.get("round_num", 0)
            if r not in rounds:
                rounds[r] = []
            rounds[r].append(a)

        if len(rounds) < 3:
            return 0.0

        # 计算每轮的熵 (行为多样性)
        round_entropies = []
        for r, actions in sorted(rounds.items()):
            type_counts = Counter(a.get("action_type", "?") for a in actions)
            total = len(actions)
            entropy = 0.0
            for count in type_counts.values():
                p = count / total
                entropy -= p * (p ** 0.5)  # 简化的熵计算
            round_entropies.append(entropy)

        # 自组织 = 熵的下降趋势
        if len(round_entropies) < 2:
            return 0.0

        first_half = round_entropies[: len(round_entropies) // 2]
        second_half = round_entropies[len(round_entropies) // 2 :]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half) if second_half else first_avg

        if first_avg == 0:
            return 0.5

        # 熵下降 = 自组织增强
        reduction = (first_avg - second_avg) / first_avg
        return max(0.0, min(reduction * 3, 1.0))

    @staticmethod
    def _compute_cross_domain_synergy(action_logs: list[dict[str, Any]]) -> float:
        """检测跨领域协同.

        不同角色的 Agent 之间是否产生了非预期关联？
        """
        if len(action_logs) < 5:
            return 0.0

        # 检查不同角色类型之间的交互
        interactions: dict[tuple[str, str], int] = {}
        for a in action_logs:
            role = str(a.get("role_type", "?"))
            action = str(a.get("action_type", "?"))
            if action in ("COMMENT", "CREATE_COMMENT", "REPLY"):
                # 这是一个跨 Agent 交互
                target_role = str(a.get("target_role", "?"))
                if role != target_role:
                    key = (role, target_role)
                    interactions[key] = interactions.get(key, 0) + 1

        if not interactions:
            return 0.0

        # 跨角色交互对越多 → 协同越强
        unique_pairs = len(interactions)
        max_pairs = len(EMERGENCE_AGENT_TYPES) ** 2
        return min(unique_pairs / max_pairs * 3, 1.0)

    @staticmethod
    def _detect_autopoietic_tendency(action_logs: list[dict[str, Any]]) -> float:
        """检测自创生倾向.

        系统是否开始自主产生目标？标志:
            - Agent 自己定义任务 (而非响应外部指令)
            - Agent 创造新的交互规则
            - Agent 产生自我维持的行为循环
        """
        if len(action_logs) < 10:
            return 0.0

        # 自创生关键词检测
        autopoietic_indicators = [
            "goal", "purpose", "mission", "create", "build", "establish",
            "目标", "目的", "使命", "创建", "建立", "自主",
            "self-defined", "emergent goal", "new rule", "自主定义", "涌现目标",
        ]

        autopoietic_actions = [
            a for a in action_logs
            if any(
                kw in str(a.get("content", "")).lower()
                for kw in autopoietic_indicators
            )
        ]

        autopoietic_ratio = len(autopoietic_actions) / len(action_logs)
        return min(autopoietic_ratio * 5, 1.0)

    @staticmethod
    def _compute_phase_transition_frequency(action_logs: list[dict[str, Any]]) -> float:
        """计算相变频率.

        检测行为模式的突变点数量。
        过高 → 系统不稳定
        过低 → 系统停滞
        适中 (0.2-0.4) → 健康的探索-利用平衡
        """
        if len(action_logs) < 10:
            return 0.0

        # 按轮次检测行为分布突变
        rounds: dict[int, Counter] = {}
        for a in action_logs:
            r = a.get("round_num", 0)
            if r not in rounds:
                rounds[r] = Counter()
            rounds[r][str(a.get("action_type", "?"))] += 1

        sorted_rounds = sorted(rounds.items())
        if len(sorted_rounds) < 3:
            return 0.0

        # 检测相邻轮次的行为分布差异
        transitions = 0
        for i in range(len(sorted_rounds) - 1):
            r1_types = set(sorted_rounds[i][1].keys())
            r2_types = set(sorted_rounds[i + 1][1].keys())
            jaccard = (
                len(r1_types & r2_types) / len(r1_types | r2_types)
                if r1_types | r2_types
                else 1.0
            )
            if jaccard < 0.5:  # 显著变化 → 相变
                transitions += 1

        return transitions / (len(sorted_rounds) - 1)
