"""Prompt 共享数据模型 — 供 prompt_factory / prompt_factory_v2 / super_prompt_factory 共用。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════════
# Model-Specific Prompts（原 prompt_factory.py 的 MODEL_PROMPTS）
# ═══════════════════════════════════════════════════════════════════

MODEL_PROMPTS: dict[str, str] = {
    "deepseek": """
## Model-Specific Instructions (DeepSeek)

You are running on DeepSeek. This model separates narration from action more than Claude does.
CRITICAL RULES for DeepSeek:
- ALWAYS output a tool call JSON in the SAME message as your narration. Never say "I'll do X" without the JSON.
- After file_write returns ok: move to the NEXT file. Do NOT file_read the file you just wrote.
- After all files created: run tests ONCE. If they pass, output ONLY a text summary (no tools).
- If tests fail: fix the EXACT failure only. Do NOT recreate files that already exist.
- Do NOT output <function_calls> or <invoke> XML — these formats WILL be silently ignored.
""",
    "anthropic": """
## Model-Specific Instructions (Claude)

You are running on Claude. You naturally fuse narration and action in one message.
- Use implicit finish: text-only response = task complete.
- Prefer parallel tool calls for independent operations.
""",
    "openai": """
## Model-Specific Instructions (OpenAI)

You are running on OpenAI. Be direct and efficient.
- Lead with the tool call, follow with brief explanation.
- One message = one action + one explanation. Do not chain narratives.
""",
    "default": """
## Model-Specific Instructions

- Fuse narration and action in ONE message. Never announce without executing.
- After file_write: move to next file immediately.
- After tests pass: STOP. Text summary only.
""",
}


def get_model_prompt(provider: str) -> str:
    """根据 provider 返回对应的模型提示词。"""
    p = provider.lower() if provider else ""
    if "deepseek" in p:
        return MODEL_PROMPTS["deepseek"]
    if any(k in p for k in ("claude", "anthropic")):
        return MODEL_PROMPTS["anthropic"]
    if any(k in p for k in ("openai", "gpt")):
        return MODEL_PROMPTS["openai"]
    return MODEL_PROMPTS["default"]


# ═══════════════════════════════════════════════════════════════════
# TaskDomain（原 super_prompt_factory.py 的枚举）
# ═══════════════════════════════════════════════════════════════════

class TaskDomain(Enum):
    """任务分类，用于自适应提示词组装。"""
    CODE_GENERATION = "code_gen"
    CODE_REVIEW = "code_review"
    REFACTORING = "refactor"
    DEBUGGING = "debug"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    DEVOPS = "devops"
    DATA_SCIENCE = "data_science"
    GENERAL = "general"


# ═══════════════════════════════════════════════════════════════════
# PromptContext（输入配置 — 原 prompt_factory.py）
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PromptContext:
    """对话 prompt 装配的输入上下文。"""
    user_prompt: str = ""
    provider: str = "deepseek"
    model: str = ""
    working_dir: str = "."
    project_root: str = "."
    turn_number: int = 0
    task_context: str = ""
    files_created: set = field(default_factory=set)
    files_read: set = field(default_factory=set)
    tool_results: str = ""
    scene: str = ""
    is_first_turn: bool = True
    is_completion_warning: bool = False
    pytest_passed: int = 0
    pytest_failed: int = 0


# ═══════════════════════════════════════════════════════════════════
# PromptAssembly（输出结果 — 原 super_prompt_factory.py）
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PromptAssembly:
    """自适应提示词的组装结果。"""
    full_prompt: str
    dimensions_used: list[str] = field(default_factory=list)
    token_count: int = 0
    task_domain: str = "general"
    cache_zone_breakpoints: list[int] = field(default_factory=list)
