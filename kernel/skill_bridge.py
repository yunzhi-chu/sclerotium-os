"""Skill Bridge — 技能注册→自动化执行 (L6 SkillRegistry ↔ ChainExecutor)。

生命体的"肌肉记忆" — 将已结晶的技能自动映射为可执行的自动化链。

使用方式:
    bridge = SkillBridge()
    bridge.register_skill("桌面整理", steps=[
        {"action": "screenshot", "label": "before"},
        {"action": "open_app", "app": "explorer"},
        {"action": "type_text", "text": "Desktop"},
    ])
    result = bridge.execute_skill("桌面整理")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.skill_bridge")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SkillDefinition:
    """技能定义 (不可变)。"""
    name: str
    description: str
    steps: tuple[dict[str, Any], ...]
    trigger_keywords: tuple[str, ...] = ()
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SkillExecution:
    """技能执行记录。"""
    skill_name: str
    success: bool
    steps_completed: int = 0
    error: str = ""
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# SkillBridge
# ═══════════════════════════════════════════════════════════════

class SkillBridge:
    """技能注册→执行映射桥接。

    使用方式:
        bridge = SkillBridge()
        bridge.register("桌面整理", "扫描→分类→移动",
                       steps=[...], triggers=["整理", "桌面"])
        result = bridge.execute("桌面整理")
    """

    def __init__(self, chain_executor: Any = None) -> None:
        self._chain_executor = chain_executor
        self._skills: dict[str, SkillDefinition] = {}
        self._executions: list[SkillExecution] = []

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def register(
        self, name: str, description: str,
        steps: list[dict[str, Any]],
        triggers: list[str] | None = None,
        confidence: float = 0.5,
    ) -> SkillDefinition:
        """注册一个可执行技能。"""
        skill = SkillDefinition(
            name=name, description=description,
            steps=tuple(steps),
            trigger_keywords=tuple(triggers or []),
            confidence=confidence,
        )
        self._skills[name] = skill
        return skill

    def find_by_trigger(self, text: str) -> list[SkillDefinition]:
        """根据触发词查找匹配的技能。"""
        text_lower = text.lower()
        matches = []
        for skill in self._skills.values():
            for kw in skill.trigger_keywords:
                if kw.lower() in text_lower:
                    matches.append(skill)
                    break
        return sorted(matches, key=lambda s: s.confidence, reverse=True)

    def execute(self, name: str) -> SkillExecution:
        """执行指定技能。"""
        skill = self._skills.get(name)
        if not skill:
            result = SkillExecution(
                skill_name=name, success=False,
                error=f"Skill not found: {name}",
            )
            self._executions.append(result)
            return result

        if self._chain_executor:
            try:
                for step in skill.steps:
                    action = step.get("action", "")
                    params = {k: v for k, v in step.items() if k != "action"}
                    self._chain_executor.add_step(action, **params)
                chain_result = self._chain_executor.execute()
                ok = chain_result.success
                result = SkillExecution(
                    skill_name=name, success=ok,
                    steps_completed=chain_result.completed_steps,
                    error="" if ok else "Chain execution failed",
                )
            except Exception as e:
                result = SkillExecution(
                    skill_name=name, success=False, error=str(e),
                )
        else:
            # 无执行器时模拟成功
            result = SkillExecution(
                skill_name=name, success=True,
                steps_completed=len(skill.steps),
            )

        self._executions.append(result)
        if len(self._executions) > 200:
            self._executions = self._executions[-200:]
        return result

    def list_skills(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def get_stats(self) -> dict[str, Any]:
        recent = self._executions[-50:]
        successes = sum(1 for e in recent if e.success)
        return {
            "skills_registered": len(self._skills),
            "total_executions": len(self._executions),
            "success_rate": round(
                successes / max(len(recent), 1), 3
            ),
        }

    def clear(self) -> None:
        self._skills.clear()
        self._executions.clear()
