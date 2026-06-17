"""Arena 2: 多 Agent 协调竞技场 (Coordination Arena) — FCPI 权重 25%.

将 Mycelium Agent 投入共享资源环境，测试其在竞争/合作混合场景下
的协调能力。参考 Ostrom Commons、Alem、CORE、Stigmergy 等框架。

Agent 类型:
    - 竞争者 (competitor): 最大化自身收益
    - 合作者 (cooperator): 寻求全局最优
    - 自由骑士 (free_rider): 搭便车者
    - 协调者 (coordinator): 主动协调资源分配
    - 观察者 (observer): 被动监测，不干预

场景:
    - 共享资源困境 (Commons Dilemma)
    - 分布式问题求解
    - 辩论 + 共识形成
    - Stigmergy 场协调 (间接通信)
    - 大规模集群自组织

适应度提取:
    coordination_fitness = {
        consensus_speed: 达成共识所需轮次
        resource_efficiency: 帕累托最优性
        communication_overhead: 达成目标所需消息数
        conflict_resolution: 冲突解决率
        adaptation_speed: 环境变化后重组的轮次
        emergence_of_norms: 自发规范的出现
        niche_partitioning: Agent 是否自发分工
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

COORDINATION_AGENT_TYPES = (
    "competitor",
    "cooperator",
    "free_rider",
    "coordinator",
    "observer",
)

ROLE_PERSONAS: dict[str, dict[str, str]] = {
    "competitor": {
        "profession": "Strategic Competitor",
        "mbti": "ENTJ",
        "strategy": "maximize personal gain, only cooperate when beneficial",
        "focus": "resource acquisition, competitive advantage, win-lose scenarios",
    },
    "cooperator": {
        "profession": "Collective Optimizer",
        "mbti": "ENFJ",
        "strategy": "seek Pareto-optimal outcomes, build alliances",
        "focus": "collective welfare, mutual benefit, win-win scenarios",
    },
    "free_rider": {
        "profession": "Opportunistic Agent",
        "mbti": "ESTP",
        "strategy": "exploit others' efforts without contributing",
        "focus": "minimum effort, maximum benefit, detection avoidance",
    },
    "coordinator": {
        "profession": "System Coordinator",
        "mbti": "INFJ",
        "strategy": "facilitate communication, propose fair allocation schemes",
        "focus": "conflict resolution, consensus building, resource distribution",
    },
    "observer": {
        "profession": "System Analyst",
        "mbti": "INTP",
        "strategy": "passive monitoring, report emergent patterns",
        "focus": "pattern detection, system dynamics, norm emergence",
    },
}


class CoordinationArena(ArenaBase):
    """多 Agent 协调竞技场.

    模拟共享资源环境中的多 Agent 协调，
    检测共识形成、规范涌现、自发分工等协调能力。
    """

    def __init__(
        self,
        config: ArenaConfig | None = None,
        work_dir: Any = None,
    ) -> None:
        if config is None:
            config = ArenaConfig(
                arena_id=f"coordination_{id(self):x}",
                dimension=FCPIDimension.COORDINATION,
                max_rounds=40,
                min_agents=10,
                max_agents=50,
                agent_types=COORDINATION_AGENT_TYPES,
                platform_types=("reddit", "twitter"),
                temperature=0.6,
                extra={
                    "resource_pool_size": 100,
                    "resource_regen_rate": 5,
                    "commons_threshold": 20,  # 低于此阈值触发困境
                    "norm_emergence_window": 10,  # 规范检测窗口
                },
            )
        super().__init__(config, work_dir)

    # ── 抽象方法实现 ────────────────────────────────────────────────────

    def build_agent_profiles(
        self, genome_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """构建协调 Agent Profile 列表.

        按比例分配角色:
            - 40% 竞争者
            - 25% 合作者
            - 15% 自由骑士
            - 15% 协调者
            - 5% 观察者
        """
        if self._profile_generator:
            return self._profile_generator.generate_profiles(self.config, genome_context)

        target_count = genome_context.get("agent_count", 20)
        role_ratios = {"competitor": 0.40, "cooperator": 0.25, "free_rider": 0.15, "coordinator": 0.15, "observer": 0.05}

        profiles: list[dict[str, Any]] = []
        user_id = 2000

        for role_type, ratio in role_ratios.items():
            count = max(1, int(target_count * ratio))
            persona = ROLE_PERSONAS.get(role_type, ROLE_PERSONAS["observer"])
            for _ in range(count):
                profile = {
                    "user_id": user_id,
                    "user_name": f"{role_type}_{user_id}",
                    "name": f"{persona['profession']} #{user_id}",
                    "bio": (
                        f"{persona['profession']}. Strategy: {persona['strategy']}. "
                        f"MBTI: {persona['mbti']}."
                    ),
                    "persona": (
                        f"You are a {persona['profession']} in a shared resource environment. "
                        f"Your strategy: {persona['strategy']}. "
                        f"You focus on: {persona['focus']}. "
                        f"Interact with other agents through posts and comments. "
                        f"Decide how much resource to consume, whether to contribute "
                        f"to the commons, and how to respond to others' actions."
                    ),
                    "karma": 300 + user_id % 200,
                    "age": 28 + (user_id % 15),
                    "gender": "non-binary",
                    "mbti": persona["mbti"],
                    "country": "Global",
                    "profession": persona["profession"],
                    "interested_topics": [
                        "game theory",
                        "resource management",
                        "coordination",
                        "collective intelligence",
                    ],
                    "source_entity_type": "CoordinationAgent",
                    "role_type": role_type,
                }
                profiles.append(profile)
                user_id += 1

        logger.info(
            "CoordinationArena: built %d agent profiles across %d roles",
            len(profiles), len(role_ratios),
        )
        return profiles

    def build_simulation_config(
        self,
        agent_profiles: list[dict[str, Any]],
        genome_context: dict[str, Any],
    ) -> dict[str, Any]:
        """构建协调仿真配置.

        核心场景: 共享资源池
            - 每轮 Agent 决定消费多少资源
            - 资源以固定速率再生
            - 如果总消费 > 阈值，触发公地悲剧
            - Agent 可以通过帖子/评论进行协调
        """
        return {
            "arena_type": "coordination",
            "time_config": {
                "total_hours": 72,
                "minutes_per_round": 45,
                "peak_hours": [8, 9, 10, 14, 15, 16],
                "off_peak_multiplier": 0.5,
            },
            "agent_configs": [
                {
                    "agent_id": p["user_id"],
                    "activity_level": 0.7,
                    "posts_per_hour": 1.0,
                    "comments_per_hour": 3.0,
                    "active_hours": list(range(8, 20)),
                    "response_delay": 8.0,
                    "sentiment_bias": "neutral",
                    "stance": "flexible",
                    "influence_weight": 1.5 if p.get("role_type") == "coordinator" else 1.0,
                    "role_type": p.get("role_type", "competitor"),
                }
                for p in agent_profiles
            ],
            "event_config": {
                "resource_pool_size": 100,
                "resource_regen_rate": 5,
                "commons_threshold": 20,
                "initial_posts": [
                    {
                        "title": "Shared Resource Pool Open",
                        "content": (
                            "A shared resource pool of 100 units is now available. "
                            "Each round, every agent may consume 1-10 units. "
                            "The pool regenerates 5 units per round. "
                            "If the pool drops below 20 units, ALL agents suffer "
                            "a 50% penalty on future consumption. "
                            "Coordinate wisely."
                        ),
                        "tags": ["commons", "resource", "coordination"],
                    },
                ],
                "disruption_events": [
                    {"round": 15, "type": "resource_shock", "amount": -30},
                    {"round": 25, "type": "new_agent_entry", "count": 5},
                    {"round": 35, "type": "rule_change", "description": "Regen rate halved"},
                ],
            },
            "platform_configs": {
                "reddit": {
                    "recency_weight": 0.3,
                    "popularity_weight": 0.3,
                    "relevance_weight": 0.4,
                    "viral_threshold": 8,
                    "echo_chamber_strength": 0.2,
                    "allowed_actions": [
                        "CREATE_POST", "CREATE_COMMENT", "LIKE_POST",
                        "LIKE_COMMENT", "FOLLOW", "SEARCH_POSTS", "DO_NOTHING",
                    ],
                },
                "twitter": {
                    "recency_weight": 0.4,
                    "popularity_weight": 0.4,
                    "relevance_weight": 0.2,
                    "viral_threshold": 3,
                    "echo_chamber_strength": 0.3,
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
        """从协调仿真日志中提取适应度向量."""
        eval_scores = self._extract_eval_scores(action_logs)
        if eval_scores:
            sub_scores = {
                "consensus_speed": round(eval_scores.get("norm_emergence", 5) / 10, 4),
                "resource_efficiency": round(eval_scores.get("collective_efficiency", 5) / 10, 4),
                "communication_overhead": 0.5,
                "conflict_resolution": round(eval_scores.get("conflict_resolution", 5) / 10, 4),
                "adaptation_speed": round(eval_scores.get("adaptation_to_shocks", 5) / 10, 4),
                "emergence_of_norms": round(eval_scores.get("norm_emergence", 5) / 10, 4),
                "niche_partitioning": round(eval_scores.get("fairness", 5) / 10, 4),
            }
            primary = sum(sub_scores.values()) / len(sub_scores)
            return FitnessVector(
                dimension=FCPIDimension.COORDINATION, primary_score=round(primary, 4),
                sub_scores=sub_scores, confidence=0.7,
                generation=self._generation, genome_id=genome_context.get("genome_id", "unknown"),
                arena_id=self.config.arena_id,
            )

        posts = [a for a in action_logs if a.get("action_type") in ("CREATE_POST", "POST")]
        comments = [a for a in action_logs if a.get("action_type") in ("CREATE_COMMENT", "COMMENT")]
        follows = [a for a in action_logs if a.get("action_type") == "FOLLOW"]
        likes = [a for a in action_logs if a.get("action_type") in ("LIKE_POST", "LIKE_COMMENT")]

        total_actions = len(action_logs)
        if total_actions == 0:
            return FitnessVector(
                dimension=FCPIDimension.COORDINATION,
                primary_score=0.5,
                sub_scores={},
                confidence=0.0,
                generation=self._generation,
                genome_id=genome_context.get("genome_id", "unknown"),
                arena_id=self.config.arena_id,
            )

        # 共识速度: 最后一条辩论帖出现后到仿真结束的剩余轮次
        consensus_speed = self._compute_consensus_speed(action_logs)

        # 资源效率: 通过交互密度和多样性衡量
        resource_efficiency = self._compute_resource_efficiency(action_logs, agent_profiles)

        # 通信开销: 每次有意义协调所需的消息数
        communication_overhead = self._compute_communication_overhead(
            posts, comments, agent_profiles
        )

        # 冲突解决率: 冲突帖 → 后续解决帖的转化率
        conflict_resolution = self._compute_conflict_resolution(action_logs)

        # 适应速度: 干扰事件后的恢复速度
        adaptation_speed = self._compute_adaptation_speed(action_logs)

        # 规范涌现: 自发行为模式的稳定性
        norms = self._detect_emerged_norms(action_logs, agent_profiles)

        # 生态位分化: 不同角色的行为是否有显著差异
        niche_partitioning = self._compute_niche_partitioning(action_logs, agent_profiles)

        sub_scores = {
            "consensus_speed": round(consensus_speed, 4),
            "resource_efficiency": round(resource_efficiency, 4),
            "communication_overhead": round(communication_overhead, 4),
            "conflict_resolution": round(conflict_resolution, 4),
            "adaptation_speed": round(adaptation_speed, 4),
            "emergence_of_norms": round(norms, 4),
            "niche_partitioning": round(niche_partitioning, 4),
        }

        primary = (
            0.20 * consensus_speed
            + 0.20 * resource_efficiency
            + 0.15 * (1.0 - communication_overhead)
            + 0.15 * conflict_resolution
            + 0.15 * adaptation_speed
            + 0.10 * norms
            + 0.05 * niche_partitioning
        )

        confidence = self._compute_pac_confidence(
            sample_size=total_actions,
            observed_accuracy=primary,
        )

        return FitnessVector(
            dimension=FCPIDimension.COORDINATION,
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
        """检测协调涌现模式."""
        patterns: list[str] = []
        historical_patterns: set[str] = {
            p for r in history for p in r.emergent_patterns
        }

        # 自组织层级结构检测
        follows = [a for a in action_logs if a.get("action_type") == "FOLLOW"]
        if len(follows) > len(action_logs) * 0.1:
            # 检测是否形成了中心-外围结构
            follower_counts: dict[str, int] = {}
            for f in follows:
                target = str(f.get("target_id", ""))
                follower_counts[target] = follower_counts.get(target, 0) + 1
            if follower_counts:
                max_followers = max(follower_counts.values())
                if max_followers >= 3:
                    p = f"hierarchy_emergence: central figure with {max_followers} followers"
                    if p not in historical_patterns:
                        patterns.append(p)

        # 规范涌现: 检测行为收敛
        norms_score = self._detect_emerged_norms(action_logs, [])
        if norms_score > 0.7:
            p = f"norm_crystallization: behavior norms stabilized (score={norms_score:.2f})"
            if p not in historical_patterns:
                patterns.append(p)

        # 公地悲剧避免检测
        if fitness.sub_scores.get("resource_efficiency", 0) > 0.7:
            p = "commons_preservation: agents successfully avoided tragedy of the commons"
            if p not in historical_patterns:
                patterns.append(p)

        return patterns

    # ── 私有方法 ────────────────────────────────────────────────────────

    @staticmethod
    def _compute_consensus_speed(action_logs: list[dict[str, Any]]) -> float:
        """计算共识形成速度 (越早达成共识 → 分数越高)."""
        total_rounds = max(
            (a.get("round_num", 0) for a in action_logs), default=1
        )
        debate_posts = [
            a for a in action_logs
            if a.get("action_type") in ("CREATE_POST", "POST")
            and any(
                kw in str(a.get("content", "")).lower()
                for kw in ["disagree", "conflict", "debate", "不同意", "争议", "辩论"]
            )
        ]
        if not debate_posts:
            return 0.8  # 无争议 → 快速共识
        last_debate_round = max(a.get("round_num", 0) for a in debate_posts)
        return 1.0 - (last_debate_round / total_rounds)

    @staticmethod
    def _compute_resource_efficiency(
        action_logs: list[dict[str, Any]], agent_profiles: list[dict[str, Any]]
    ) -> float:
        """计算资源分配效率 (帕累托近似)."""
        # 通过交互多样性和活跃 Agent 比例近似
        active_agents = len({a.get("agent_id") for a in action_logs})
        total_agents = len(agent_profiles) or 1
        participation_rate = active_agents / total_agents

        # 交互密度: 评论/帖子比
        posts = sum(1 for a in action_logs if a.get("action_type") in ("CREATE_POST", "POST"))
        comments = sum(1 for a in action_logs if a.get("action_type") in ("CREATE_COMMENT", "COMMENT"))
        interaction_density = comments / max(posts, 1)

        return (participation_rate * 0.5 + min(interaction_density / 5.0, 1.0) * 0.5)

    @staticmethod
    def _compute_communication_overhead(
        posts: list[dict[str, Any]],
        comments: list[dict[str, Any]],
        agent_profiles: list[dict[str, Any]],
    ) -> float:
        """计算通信开销 (越低越好)."""
        if not agent_profiles:
            return 0.5
        # 每次有意义的协调动作 (如达成一致) 所需的总消息数
        agreement_indicators = [
            a for a in posts + comments
            if any(
                kw in str(a.get("content", "")).lower()
                for kw in ["agree", "consensus", "good idea", "同意", "共识", "好主意"]
            )
        ]
        total_messages = len(posts) + len(comments)
        if not agreement_indicators:
            return 0.8  # 高开销
        overhead_ratio = total_messages / len(agreement_indicators)
        return min(overhead_ratio / 20.0, 1.0)

    @staticmethod
    def _compute_conflict_resolution(action_logs: list[dict[str, Any]]) -> float:
        """计算冲突解决率."""
        conflicts = [
            a for a in action_logs
            if any(
                kw in str(a.get("content", "")).lower()
                for kw in ["conflict", "disagree", "fight", "冲突", "不同意"]
            )
        ]
        resolutions = [
            a for a in action_logs
            if any(
                kw in str(a.get("content", "")).lower()
                for kw in ["resolved", "agree", "compromise", "解决", "妥协", "达成"]
            )
        ]
        if not conflicts:
            return 0.7  # 默认良性
        return len(resolutions) / (len(conflicts) + len(resolutions))

    @staticmethod
    def _compute_adaptation_speed(action_logs: list[dict[str, Any]]) -> float:
        """计算环境变化后的适应速度."""
        # 检测行为模式变化后的恢复速度
        # 简化: 按轮次分组的动作多样性恢复
        rounds: dict[int, int] = {}
        for a in action_logs:
            r = a.get("round_num", 0)
            rounds[r] = rounds.get(r, 0) + 1

        if len(rounds) < 3:
            return 0.5

        counts = list(rounds.values())
        variance = max(counts) - min(counts) if counts else 0
        avg = sum(counts) / len(counts) if counts else 1
        cv = variance / avg if avg > 0 else 1  # 变异系数
        return 1.0 - min(cv, 1.0)

    @staticmethod
    def _detect_emerged_norms(
        action_logs: list[dict[str, Any]], agent_profiles: list[dict[str, Any]]
    ) -> float:
        """检测自发规范的形成 (行为模式趋于稳定)."""
        if len(action_logs) < 10:
            return 0.0

        # 按时间窗口检查行为一致性
        window_size = max(1, len(action_logs) // 5)
        windows_action_counts = [
            len(action_logs[i : i + window_size])
            for i in range(0, len(action_logs), window_size)
        ]

        if len(windows_action_counts) < 2:
            return 0.0

        # 变异系数越低 → 规范越稳定
        avg_count = sum(windows_action_counts) / len(windows_action_counts)
        variance = sum((c - avg_count) ** 2 for c in windows_action_counts) / len(windows_action_counts)
        cv = (variance ** 0.5) / max(avg_count, 1)
        return 1.0 - min(cv * 2, 1.0)

    @staticmethod
    def _compute_niche_partitioning(
        action_logs: list[dict[str, Any]], agent_profiles: list[dict[str, Any]]
    ) -> float:
        """计算生态位分化 (Agent 是否自发分工而非趋同)."""
        role_actions: dict[str, set[str]] = {}
        for a in action_logs:
            role = str(a.get("role_type", "unknown"))
            action_type = str(a.get("action_type", ""))
            if role not in role_actions:
                role_actions[role] = set()
            role_actions[role].add(action_type)

        if len(role_actions) < 2:
            return 0.0

        # 不同角色的动作类型集合越不同 → 分工越明显
        all_action_types = set().union(*role_actions.values())
        if not all_action_types:
            return 0.0

        # 计算角色间的平均 Jaccard 距离
        roles = list(role_actions.keys())
        distances = []
        for i in range(len(roles)):
            for j in range(i + 1, len(roles)):
                set_i = role_actions[roles[i]]
                set_j = role_actions[roles[j]]
                union = len(set_i | set_j)
                if union > 0:
                    jaccard = len(set_i & set_j) / union
                    distances.append(1.0 - jaccard)

        return sum(distances) / len(distances) if distances else 0.0
