"""Insight Engine — 从记忆流中提取战略洞察。

生命体的"元认知" — 不只看"发生了什么"，更要理解"这意味着什么"。

洞察类型:
  - WORK_PATTERN:   "你连续3天晚上11点后还在写代码"
  - TECH_EVOLUTION: "你从 Python 向 TypeScript 过渡中"
  - PRODUCTIVITY:   "你周五下午效率最低, 建议安排在周五做轻松任务"
  - LEARNING:       "你在学 Rust 但反复中断, 每次中断在泛型章节"
  - HEALTH:         "本周平均睡眠窗口只有5小时"
  - PREFERENCE:     "你偏好函数式风格, 几乎所有 utils 都是纯函数"

使用方式:
    engine = InsightEngine(memory_store=store)
    insights = engine.analyze()  # 分析最近7天记忆
    for insight in insights:
        print(insight.to_human_readable())
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from kernel.hexis_memory import HexisMemoryStore, MemoryEntry, MemoryLevel

logger = logging.getLogger("sclerotium.insight")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class InsightCategory(str, Enum):
    """洞察类别。"""
    WORK_PATTERN = "work_pattern"         # 工作模式
    TECH_EVOLUTION = "tech_evolution"     # 技术栈演变
    PRODUCTIVITY = "productivity"          # 效率分析
    LEARNING = "learning"                  # 学习行为
    HEALTH = "health"                      # 健康建议
    PREFERENCE = "preference"             # 用户偏好
    TOOL_USAGE = "tool_usage"             # 工具使用
    SCHEDULE = "schedule"                  # 日程规律
    ANOMALY = "anomaly"                   # 异常检测
    SUGGESTION = "suggestion"             # 主动建议


@dataclass(frozen=True)
class Insight:
    """一条战略洞察 (不可变)。"""
    category: InsightCategory
    title: str                              # 简短标题
    description: str                        # 详细描述
    confidence: float = 0.5                 # 置信度 (0.0–1.0)
    evidence: tuple[str, ...] = ()          # 支撑证据 (记忆内容片段)
    suggestion: str = ""                    # 建议行动
    urgency: float = 0.0                    # 紧迫度 (0.0–1.0)
    generated_at: float = field(default_factory=time.time)
    valid_until: float = 0.0               # 有效期 (0=永久)

    def to_human_readable(self) -> str:
        """人类可读格式。"""
        emoji = {
            InsightCategory.WORK_PATTERN: "📊",
            InsightCategory.TECH_EVOLUTION: "🔧",
            InsightCategory.PRODUCTIVITY: "⚡",
            InsightCategory.LEARNING: "📚",
            InsightCategory.HEALTH: "💚",
            InsightCategory.PREFERENCE: "🎨",
            InsightCategory.TOOL_USAGE: "🛠️",
            InsightCategory.SCHEDULE: "📅",
            InsightCategory.ANOMALY: "⚠️",
            InsightCategory.SUGGESTION: "💡",
        }.get(self.category, "🔍")

        lines = [f"{emoji} **{self.title}** (置信度: {self.confidence:.0%})"]
        lines.append(f"   {self.description}")
        if self.suggestion:
            lines.append(f"   → {self.suggestion}")
        if self.evidence:
            lines.append(f"   依据: {', '.join(self.evidence[:3])}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "suggestion": self.suggestion,
            "urgency": self.urgency,
            "generated_at": self.generated_at,
        }


# ═══════════════════════════════════════════════════════════════
# InsightEngine
# ═══════════════════════════════════════════════════════════════

class InsightEngine:
    """从记忆流中提取深层洞察。

    使用方式:
        store = HexisMemoryStore()
        engine = InsightEngine(memory_store=store)
        insights = engine.analyze(days=7)
        for insight in insights:
            store.store(insight.description, level="strategic",
                        importance=insight.confidence,
                        metadata=insight.to_dict())
    """

    def __init__(
        self,
        memory_store: HexisMemoryStore,
        min_confidence: float = 0.3,
    ) -> None:
        self._store = memory_store
        self._min_confidence = min_confidence
        self._generated: list[Insight] = []

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def analyze(self, days: int = 7) -> list[Insight]:
        """分析最近 N 天记忆, 生成所有洞察。

        Args:
            days: 分析窗口 (天数)

        Returns:
            洞察列表 (按置信度排序)
        """
        # 获取最近 N 天的 Episodic 和 Semantic 记忆
        episodic = self._get_recent_memories(
            MemoryLevel.EPISODIC.value, days
        )
        semantic = self._get_recent_memories(
            MemoryLevel.SEMANTIC.value, days * 4  # 语义记忆保持更久
        )

        all_memories = episodic + semantic
        if not all_memories:
            return []

        all_text = " ".join(m.content for m in all_memories)

        insights: list[Insight] = []
        insights.extend(self._analyze_work_pattern(all_memories, all_text))
        insights.extend(self._analyze_tech_evolution(all_memories, all_text))
        insights.extend(self._analyze_tool_usage(all_memories, all_text))
        insights.extend(self._analyze_schedule(all_memories))
        insights.extend(self._analyze_health(all_text))
        insights.extend(self._generate_suggestions(all_memories, all_text))

        # 过滤低置信度
        insights = [i for i in insights if i.confidence >= self._min_confidence]

        # 去重相似洞察
        insights = self._deduplicate(insights)

        self._generated = insights
        return sorted(insights, key=lambda i: i.confidence, reverse=True)

    def get_latest(self) -> list[Insight]:
        """获取最近生成的洞察。"""
        return list(self._generated)

    def store_insights(self) -> int:
        """将当前洞察存入记忆 (Strategic 层)。

        Returns:
            存储的洞察数
        """
        count = 0
        for insight in self._generated:
            if insight.confidence >= 0.5:
                self._store.store(
                    content=insight.description,
                    level=MemoryLevel.STRATEGIC.value,
                    importance=insight.confidence,
                    metadata=insight.to_dict(),
                    source="insight_engine",
                )
                count += 1
        return count

    # ═══════════════════════════════════════════════════════
    # 分析器 — 工作模式
    # ═══════════════════════════════════════════════════════

    def _analyze_work_pattern(
        self, memories: list[MemoryEntry], text: str,
    ) -> list[Insight]:
        """检测工作模式。"""
        insights = []

        # 检测编程语言使用
        lang_patterns = self._count_languages(text)
        top_langs = [l for l, c in lang_patterns.most_common(3) if c >= 3]
        if top_langs:
            insights.append(Insight(
                category=InsightCategory.WORK_PATTERN,
                title="编程语言偏好",
                description=f"主要使用: {', '.join(top_langs)}",
                confidence=min(0.9, sum(c for _, c in lang_patterns.most_common(3)) / 20),
                evidence=tuple(f"{l} ({c}次)" for l, c in lang_patterns.most_common(3)),
            ))

        # 检测工作强度
        file_edits = sum(
            1 for m in memories
            if "文件修改" in m.content or "file" in m.content.lower()
        )
        if file_edits > 20:
            insights.append(Insight(
                category=InsightCategory.WORK_PATTERN,
                title="高编码活跃度",
                description=f"过去几天有 {file_edits} 次文件修改, 编码活跃度高",
                confidence=min(0.8, file_edits / 50),
                suggestion="考虑定时休息, 避免长时间连续编码",
            ))

        # 调试模式检测
        debug_keywords = ["bug", "fix", "修复", "错误", "error", "debug", "调试",
                          "test", "测试", "pytest", "assert"]
        debug_count = sum(
            1 for m in memories
            if any(kw in m.content.lower() for kw in debug_keywords)
        )
        if debug_count > 5:
            insights.append(Insight(
                category=InsightCategory.WORK_PATTERN,
                title="频繁调试周期",
                description=f"检测到 {debug_count} 次调试/修复活动",
                confidence=min(0.7, debug_count / 15),
                suggestion="可能遇到复杂 bug, 建议先写测试再修复",
            ))

        return insights

    def _analyze_tech_evolution(
        self, memories: list[MemoryEntry], text: str,
    ) -> list[Insight]:
        """检测技术栈演变。"""
        insights = []

        # 检测语言/框架过渡
        transition_pairs = [
            ("python", "typescript"),
            ("javascript", "typescript"),
            ("python", "rust"),
            ("java", "kotlin"),
        ]
        for old_l, new_l in transition_pairs:
            old_count = text.lower().count(old_l)
            new_count = text.lower().count(new_l)
            if new_count > old_count > 0 and new_count >= 5:
                insights.append(Insight(
                    category=InsightCategory.TECH_EVOLUTION,
                    title=f"技术栈迁移: {old_l} → {new_l}",
                    description=f"{new_l} ({new_count}次) 使用频率超过 {old_l} ({old_count}次)",
                    confidence=min(0.8, new_count / (old_count + new_count)),
                    suggestion=f"建议将旧 {old_l} 代码库逐步迁移到 {new_l}",
                ))

        # 新工具/框架检测
        known = {"python", "typescript", "javascript", "rust", "go", "java",
                 "react", "vue", "node", "docker", "git", "sql", "html", "css"}
        new_tech = []
        for m in memories[-20:]:
            for word in m.content.lower().split():
                word = word.strip(".,;:()[]{}\"'")
                if len(word) > 3 and word.isalpha() and word not in known:
                    new_tech.append(word)

        tech_counter = Counter(new_tech)
        emerging = [(t, c) for t, c in tech_counter.most_common(5) if c >= 3]
        if emerging:
            insights.append(Insight(
                category=InsightCategory.TECH_EVOLUTION,
                title="新技术接触",
                description=f"最近频繁接触: {', '.join(f'{t}({c}次)' for t, c in emerging)}",
                confidence=0.5,
                suggestion="可能是学习新技术的信号",
            ))

        return insights

    def _analyze_tool_usage(
        self, memories: list[MemoryEntry], text: str,
    ) -> list[Insight]:
        """检测工具使用模式。"""
        insights = []

        app_counter = Counter()
        for m in memories:
            meta = m.metadata or {}
            app = meta.get("app", "")
            if app:
                app_counter[app] += 1

        top_apps = app_counter.most_common(5)
        if top_apps:
            app_list = ", ".join(f"{a}({c}次)" for a, c in top_apps[:3])
            insights.append(Insight(
                category=InsightCategory.TOOL_USAGE,
                title="常用工具",
                description=f"最常使用: {app_list}",
                confidence=0.85,
            ))

        return insights

    def _analyze_schedule(
        self, memories: list[MemoryEntry],
    ) -> list[Insight]:
        """检测日程规律。"""
        insights = []

        # 按小时统计活跃度
        hour_counter = Counter()
        for m in memories:
            ts = m.timestamp
            hour = int(time.strftime("%H", time.localtime(ts)))
            hour_counter[hour] += 1

        if hour_counter:
            peak_hour = hour_counter.most_common(1)[0][0]
            night_activity = sum(
                c for h, c in hour_counter.items() if h >= 23 or h <= 5
            )
            total = sum(hour_counter.values())

            if night_activity > total * 0.15:
                insights.append(Insight(
                    category=InsightCategory.SCHEDULE,
                    title="深夜工作模式",
                    description=f"{night_activity}/{total} 次活动在深夜 (23:00-05:00)",
                    confidence=min(0.8, night_activity / total + 0.2),
                    suggestion="长期深夜工作影响健康, 建议调整作息",
                ))

            insights.append(Insight(
                category=InsightCategory.SCHEDULE,
                title=f"高效时段: {peak_hour}:00",
                description=f"你在 {peak_hour}:00 左右最活跃, "
                            f"建议将重要任务安排在此时间段",
                confidence=0.6,
            ))

        return insights

    def _analyze_health(self, text: str) -> list[Insight]:
        """生成健康建议 (基于可检测信号)。"""
        insights = []

        # 检测长时间工作
        text_lower = text.lower()
        long_session_keywords = ["60分钟", "2小时", "3小时", "久坐", "长时间"]
        for kw in long_session_keywords:
            if kw in text_lower:
                insights.append(Insight(
                    category=InsightCategory.HEALTH,
                    title="长时间工作提醒",
                    description=f"检测到长时间连续工作 ({kw})",
                    confidence=0.7,
                    suggestion="每小时站起来活动5分钟, 保护眼睛和脊椎",
                    urgency=0.6,
                ))
                break

        return insights

    def _generate_suggestions(
        self, memories: list[MemoryEntry], text: str,
    ) -> list[Insight]:
        """生成主动建议。"""
        insights = []

        # 检测重复操作 → 建议自动化
        rep_patterns = self._detect_repetition(memories)
        for pattern, count in rep_patterns:
            if count >= 3:
                insights.append(Insight(
                    category=InsightCategory.SUGGESTION,
                    title="可自动化的重复操作",
                    description=f"你重复了 {count} 次: {pattern}",
                    confidence=min(0.7, count / 8),
                    suggestion="我可以帮你在未来自动执行这个操作",
                ))

        # 基于活跃度建议休息
        if len(memories) > 30:
            insights.append(Insight(
                category=InsightCategory.SUGGESTION,
                title="定期休息提醒",
                description="你今天工作比较密集, 记得按时休息",
                confidence=0.5,
                suggestion="我可以每小时提醒你起来活动",
            ))

        return insights

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _get_recent_memories(
        self, level: str, days: int,
    ) -> list[MemoryEntry]:
        """获取指定层级最近 N 天的记忆。"""
        cutoff = time.time() - days * 86400
        return [
            m for m in self._store.dump_layer(level, limit=500)
            if m.timestamp >= cutoff
        ]

    @staticmethod
    def _count_languages(text: str) -> Counter:
        """统计编程语言/框架提及次数。"""
        langs = [
            "python", "typescript", "javascript", "rust", "go", "java",
            "c++", "sql", "html", "css", "react", "vue", "svelte",
            "django", "flask", "fastapi", "next.js", "node",
        ]
        counter = Counter()
        text_lower = text.lower()
        for lang in langs:
            count = text_lower.count(lang)
            if count > 0:
                counter[lang] = count
        return counter

    @staticmethod
    def _detect_repetition(
        memories: list[MemoryEntry],
    ) -> list[tuple[str, int]]:
        """检测重复操作模式。"""
        actions = []
        for m in memories[-50:]:
            content = m.content.lower()
            for prefix in ["窗口切换:", "文件修改:", "复制代码片段"]:
                if prefix in content:
                    # 提取操作类型
                    actions.append(content[:60])
                    break

        counter = Counter(actions)
        return counter.most_common(5)

    @staticmethod
    def _deduplicate(insights: list[Insight]) -> list[Insight]:
        """去重相似洞察。"""
        seen: set[str] = set()
        result = []
        for insight in insights:
            key = f"{insight.category.value}:{insight.title[:30]}"
            if key not in seen:
                seen.add(key)
                result.append(insight)
        return result
