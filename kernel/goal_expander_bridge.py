"""Goal Expander Bridge — 模糊指令展开 (L6 GoalExpander ≈ Codex /goal)。

生命体的"理解能力" — 将人类的模糊指令展开为具体可执行的步骤。

示例:
  "整理一下" →
    1. 扫描当前目录结构
    2. 识别文件类型 (代码/文档/图片)
    3. 创建分类文件夹
    4. 移动文件到对应文件夹
    5. 生成整理报告

  "帮我看看这个项目" →
    1. 检查项目结构
    2. 读取 README
    3. 分析依赖 (requirements.txt/package.json)
    4. 运行测试 (如果存在)
    5. 汇总关键信息

使用方式:
    expander = GoalExpanderBridge()
    steps = expander.expand("整理桌面")
    for step in steps:
        print(f"{step.index}. {step.action}: {step.description}")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.goal_expander")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GoalStep:
    """目标展开步骤 (不可变)。"""
    index: int
    action: str                    # 动作类型 (scan/read/analyze/execute/report)
    description: str               # 人类可读描述
    tool: str = ""                 # 对应 MCP 工具
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: int | None = None  # 依赖的前置步骤索引
    expected_output: str = ""


@dataclass(frozen=True)
class GoalPlan:
    """目标展开计划 (不可变)。"""
    goal: str
    steps: tuple[GoalStep, ...]
    total_steps: int
    estimated_complexity: float = 0.5
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# 内置目标模板库
# ═══════════════════════════════════════════════════════════════

GOAL_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "整理": [
        {"action": "scan", "desc": "扫描当前目录结构",
         "tool": "codebase_search", "params": {"query": "file structure"}},
        {"action": "classify", "desc": "识别文件类型并分类",
         "tool": "files_organize", "params": {"dry_run": True}},
        {"action": "organize", "desc": "按类型移动到对应文件夹",
         "tool": "files_organize", "params": {"dry_run": False}},
        {"action": "report", "desc": "生成整理报告",
         "tool": "file_read", "params": {}},
    ],
    "分析": [
        {"action": "scan", "desc": "检查项目结构",
         "tool": "codebase_search", "params": {"query": "project overview"}},
        {"action": "read", "desc": "读取关键文件 (README/配置)",
         "tool": "file_read", "params": {}},
        {"action": "analyze", "desc": "分析依赖和构建系统",
         "tool": "codebase_search", "params": {"query": "dependencies"}},
        {"action": "test", "desc": "运行现有测试",
         "tool": "bash_exec", "params": {"command": "pytest"}},
        {"action": "report", "desc": "汇总项目关键信息",
         "tool": "", "params": {}},
    ],
    "打开": [
        {"action": "launch", "desc": "启动目标应用",
         "tool": "desktop_open", "params": {}},
        {"action": "wait", "desc": "等待应用加载",
         "tool": "wait", "params": {"seconds": 3}},
    ],
    "调试": [
        {"action": "read", "desc": "读取相关源代码",
         "tool": "file_read", "params": {}},
        {"action": "search", "desc": "搜索相关错误日志",
         "tool": "grep", "params": {"pattern": "error"}},
        {"action": "test", "desc": "运行相关测试",
         "tool": "bash_exec", "params": {"command": "pytest -k related"}},
        {"action": "fix", "desc": "应用修复",
         "tool": "file_edit", "params": {}},
        {"action": "verify", "desc": "验证修复",
         "tool": "bash_exec", "params": {"command": "pytest"}},
    ],
}


# ═══════════════════════════════════════════════════════════════
# GoalExpanderBridge
# ═══════════════════════════════════════════════════════════════

class GoalExpanderBridge:
    """模糊指令展开引擎。

    使用方式:
        expander = GoalExpanderBridge()
        plan = expander.expand("帮我整理一下桌面")
        for step in plan.steps:
            print(step.description)
    """

    def __init__(self) -> None:
        self._templates: dict[str, list[dict[str, Any]]] = dict(GOAL_TEMPLATES)
        self._history: list[GoalPlan] = []

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def expand(self, goal: str) -> GoalPlan:
        """将模糊目标展开为具体步骤。

        Args:
            goal: 用户输入 (如 "整理桌面", "分析这个项目")

        Returns:
            GoalPlan 含步骤序列
        """
        # 匹配内置模板
        template = self._match_template(goal)
        steps: list[GoalStep] = []

        for i, tpl in enumerate(template):
            step = GoalStep(
                index=i + 1,
                action=tpl.get("action", "execute"),
                description=tpl.get("desc", f"Step {i+1}"),
                tool=tpl.get("tool", ""),
                params=tpl.get("params", {}),
                depends_on=i if i > 0 else None,
                expected_output=tpl.get("expected", ""),
            )
            steps.append(step)

        plan = GoalPlan(
            goal=goal,
            steps=tuple(steps),
            total_steps=len(steps),
            estimated_complexity=min(1.0, len(steps) / 10.0),
        )
        self._history.append(plan)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        return plan

    def add_template(self, keyword: str, steps: list[dict[str, Any]]) -> None:
        """添加自定义目标模板。"""
        self._templates[keyword] = steps

    def get_history(self, limit: int = 10) -> list[GoalPlan]:
        return self._history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "templates": len(self._templates),
            "template_keywords": list(self._templates.keys()),
            "plans_generated": len(self._history),
            "avg_steps": round(
                sum(p.total_steps for p in self._history)
                / max(len(self._history), 1), 1
            ),
        }

    # ═══════════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════════

    def _match_template(self, goal: str) -> list[dict[str, Any]]:
        """匹配目标到最佳模板。"""
        goal_lower = goal.lower()
        best_keyword = ""
        best_score = 0

        for keyword in self._templates:
            score = 0
            # 精确包含
            if keyword in goal_lower:
                score += 3
            # 分词匹配
            for ch in keyword:
                if ch in goal_lower:
                    score += 0.5
            if score > best_score:
                best_score = score
                best_keyword = keyword

        if best_keyword and best_score >= 1:
            return self._templates[best_keyword]

        # 默认: 通用分析模板
        return GOAL_TEMPLATES["分析"]
