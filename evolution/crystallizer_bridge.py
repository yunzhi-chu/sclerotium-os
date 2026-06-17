"""Crystallizer Bridge — 涌现→技能结晶管道 (L6 M7+Crystallizer)。

生命体的"学习能力" — 检测新的行为模式 → 评估价值 → 固化为可复用技能。

三阶段管道:
  1. EmergenceCapture: 从记忆流中检测新模式
  2. Crystallizer: 评估模式价值, 决定是否结晶
  3. SkillRegistry: 固化为可被 AgentLoop 调用的自动化技能

使用方式:
    cryst = CrystallizerBridge(memory_store=store)
    patterns = cryst.capture_patterns(days=7)
    for pattern in patterns:
        if cryst.evaluate(pattern).score > 0.7:
            skill = cryst.crystallize(pattern)
            print(f"New skill: {skill.name}")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.crystallizer")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class EmergentPattern:
    """涌现行为模式 (不可变)。"""
    pattern_id: str
    name: str                      # 模式名称
    description: str               # 描述
    trigger_condition: str         # 触发条件
    action_sequence: tuple[str, ...]  # 动作序列
    frequency: int = 1             # 出现频次
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    source_events: tuple[str, ...] = ()


@dataclass(frozen=True)
class PatternEvaluation:
    """模式评估结果 (不可变)。"""
    pattern: EmergentPattern
    score: float                   # 0.0–1.0 结晶价值
    is_novel: bool = True          # 是否是新模式
    is_reliable: bool = True       # 是否足够可靠 (>3次)
    is_safe: bool = True           # 是否安全
    suggestion: str = ""


@dataclass(frozen=True)
class CrystallizedSkill:
    """结晶后的技能 (不可变)。"""
    skill_id: str
    name: str
    description: str
    trigger: str
    steps: tuple[str, ...]
    confidence: float
    crystallized_at: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# CrystallizerBridge
# ═══════════════════════════════════════════════════════════════

class CrystallizerBridge:
    """涌现捕获 → 模式评估 → 技能结晶管道。

    使用方式:
        cryst = CrystallizerBridge()
        cryst.capture("用户每次打开 VS Code 后 30 秒内都会打开终端",
                      actions=["launch_vscode", "wait_30s", "launch_terminal"])
        evaluation = cryst.evaluate(latest_pattern)
        if evaluation.score > 0.7:
            skill = cryst.crystallize(latest_pattern)
    """

    MIN_FREQUENCY = 3       # 最小出现次数才能结晶
    MIN_SCORE = 0.5         # 最小评分

    def __init__(self, memory_store: Any = None) -> None:
        self._memory = memory_store
        self._patterns: dict[str, EmergentPattern] = {}
        self._crystallized: list[CrystallizedSkill] = []
        self._counter: int = 0

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def capture(
        self,
        description: str,
        trigger: str = "",
        actions: list[str] | None = None,
    ) -> EmergentPattern:
        """捕获一个涌现行为模式。

        Args:
            description: 模式描述
            trigger: 触发条件
            actions: 动作序列
        """
        actions = actions or []
        self._counter += 1
        pid = f"pattern_{self._counter:04d}"

        # 检查是否已存在相似模式
        for existing in self._patterns.values():
            if self._similarity(existing.description, description) > 0.7:
                # 更新频率
                self._patterns[existing.pattern_id] = EmergentPattern(
                    pattern_id=existing.pattern_id,
                    name=existing.name,
                    description=existing.description,
                    trigger_condition=existing.trigger_condition,
                    action_sequence=existing.action_sequence,
                    frequency=existing.frequency + 1,
                    first_seen=existing.first_seen,
                    last_seen=time.time(),
                    source_events=existing.source_events,
                )
                return self._patterns[existing.pattern_id]

        # 新模式
        pattern = EmergentPattern(
            pattern_id=pid,
            name=description[:50],
            description=description,
            trigger_condition=trigger,
            action_sequence=tuple(actions),
            frequency=1,
        )
        self._patterns[pid] = pattern
        logger.debug("New pattern captured: %s", description[:50])
        return pattern

    def evaluate(self, pattern: EmergentPattern) -> PatternEvaluation:
        """评估模式的结晶价值。

        评分因子:
          - 频率: 出现次数 / 10 (max 1.0)
          - 可靠性: frequency >= MIN_FREQUENCY
          - 新颖性: 是否与已结晶技能不同
          - 安全性: 动作序列不含危险操作
        """
        freq_score = min(1.0, pattern.frequency / 10.0)
        is_reliable = pattern.frequency >= self.MIN_FREQUENCY
        is_novel = not any(
            p.name == pattern.name for p in self._crystallized
        )
        is_safe = self._check_safety(pattern)
        score = (freq_score * 0.4 + (1.0 if is_reliable else 0.0) * 0.3
                 + (1.0 if is_novel else 0.0) * 0.15
                 + (1.0 if is_safe else 0.0) * 0.15)

        suggestion = ""
        if score >= 0.7:
            suggestion = "建议结晶 — 高分值模式"
        elif score >= 0.5:
            suggestion = "继续观察 — 需要更多数据"
        else:
            suggestion = "暂不结晶 — 模式不成熟"

        return PatternEvaluation(
            pattern=pattern, score=round(score, 3),
            is_novel=is_novel, is_reliable=is_reliable,
            is_safe=is_safe, suggestion=suggestion,
        )

    def crystallize(self, pattern: EmergentPattern) -> CrystallizedSkill:
        """将涌现模式结晶为可复用技能。

        结晶体包括:
          - 技能名称和描述
          - 触发条件
          - 动作步骤序列
          - 置信度评分
        """
        evaluation = self.evaluate(pattern)
        skill = CrystallizedSkill(
            skill_id=f"skill_{len(self._crystallized):04d}",
            name=pattern.name,
            description=pattern.description,
            trigger=pattern.trigger_condition,
            steps=pattern.action_sequence,
            confidence=evaluation.score,
        )
        self._crystallized.append(skill)

        # 存入记忆
        if self._memory:
            try:
                self._memory.store(
                    content=f"新技能结晶: {skill.name} — {skill.description}",
                    level="procedural",
                    importance=evaluation.score,
                    metadata={"skill_id": skill.skill_id,
                              "trigger": skill.trigger,
                              "steps": list(skill.steps)},
                    source="crystallizer",
                )
            except Exception:
                pass

        logger.info("Crystallized: %s (confidence=%.2f)",
                     skill.name, skill.confidence)
        return skill

    def get_patterns(self) -> list[EmergentPattern]:
        return sorted(self._patterns.values(),
                      key=lambda p: p.frequency, reverse=True)

    def get_skills(self) -> list[CrystallizedSkill]:
        return list(self._crystallized)

    def get_stats(self) -> dict[str, Any]:
        return {
            "patterns_detected": len(self._patterns),
            "skills_crystallized": len(self._crystallized),
            "avg_frequency": round(
                sum(p.frequency for p in self._patterns.values())
                / max(len(self._patterns), 1), 1
            ),
        }

    # ═══════════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _similarity(text1: str, text2: str) -> float:
        """简单的文本相似度 (Jaccard 词级)。"""
        w1 = set(text1.lower().split())
        w2 = set(text2.lower().split())
        if not w1 or not w2:
            return 0.0
        return len(w1 & w2) / len(w1 | w2)

    @staticmethod
    def _check_safety(pattern: EmergentPattern) -> bool:
        dangerous = ["rm ", "del ", "delete", "format", "shutdown",
                    "sudo", "kill", "purge"]
        for action in pattern.action_sequence:
            if any(d in action.lower() for d in dangerous):
                return False
        return True
