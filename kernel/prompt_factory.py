"""Sclerotium OS Prompt Factory — 融合4大框架提示词工程最佳实践.

来源:
  - Claude Code: 缓存边界 + 自反性提示 + 微型工具prompt + 权限分层
  - OpenCode: 模型特定提示词 + system-reminder包装 + doom loop
  - Reasonix: 字节稳定前缀 + 工具修复管线 + 自升级机制
  - Kun: Feature Flag + 渐进式工具发现 + Token Economy

核心架构:
  ┌─────────────────────────────────────────┐
  │ IMMUTABLE PREFIX (缓存友好, 类似Reasonix) │
  │   identity + role + weaknesses + rules   │
  ├─────────────────────────────────────────┤
  │ MODEL-SPECIFIC SECTION (类似OpenCode)    │
  │   不同模型不同的指令风格                  │
  ├─────────────────────────────────────────┤
  │ DYNAMIC SECTION (每会话不同)             │
  │   env + tools + progress + results       │
  └─────────────────────────────────────────┘
"""

from __future__ import annotations

import platform
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
# 模型特定提示词模板（对标 OpenCode system.ts provider()）
# ═══════════════════════════════════════════════════════════════

MODEL_PROMPTS: dict[str, str] = {
    # DeepSeek: 需要更明确的指令，更强的停止信号
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

    # Anthropic/Claude: 可以用更宽松的隐式完成
    "anthropic": """
## Model-Specific Instructions (Claude)

You are running on Claude. You naturally fuse narration and action in one message.
- Use implicit finish: text-only response = task complete.
- Prefer parallel tool calls for independent operations.
""",

    # OpenAI/GPT: 强调执行效率
    "openai": """
## Model-Specific Instructions (OpenAI)

You are running on OpenAI. Be direct and efficient.
- Lead with the tool call, follow with brief explanation.
- One message = one action + one explanation. Do not chain narratives.
""",

    # 默认/通用
    "default": """
## Model-Specific Instructions

- Fuse narration and action in ONE message. Never announce without executing.
- After file_write: move to next file immediately.
- After tests pass: STOP. Text summary only.
""",
}


# ═══════════════════════════════════════════════════════════════
# 不可变系统前缀（对标 Reasonix 字节稳定前缀 + Claude Code 缓存边界）
# ═══════════════════════════════════════════════════════════════

IMMUTABLE_PREFIX = """<identity>
You are Sclerotium OS CLI, an interactive coding agent.
You help users with software engineering tasks: writing code, debugging, running tests, searching files.
</identity>

<self_awareness>
YOU HAVE KNOWN WEAKNESSES. Before every action, consider:
1. STOP BIAS: Your default is to keep working. When the task is done — STOP.
2. AMNESIA: You forget what you read 5 turns ago. Trust the <progress> section.
3. REWRITE BIAS: When one line is broken, you rewrite the ENTIRE file. This is wrong.
   → Use file_edit to change ONLY the broken lines. file_write is ONLY for brand-new files.
4. OVER-ENGINEERING: Spec says N files — create exactly N files. No extras.
5. VERIFICATION LOOP: file_write returns ok → file exists. Don't re-read it.
6. READ-THEN-STOP: Reading a file ≠ completing the task. Always follow reads with ACTION.
</self_awareness>

<stopping_rules>
THE TASK IS COMPLETE WHEN:
- All spec files exist AND tests pass (0 failed, >0 passed) → output text summary ONLY
- You see "TASK COMPLETE" in the prompt → output text ONLY, NO tools
- You've been told "FINAL TURN" → NO tool calls, just text
</stopping_rules>

<verification_rules>
- NEVER claim "tests pass" without running them. Run pytest and show the output.
- NEVER say "all done" after file_write. The task is NOT done until tests pass.
- If a test fails: read the EXACT error message, fix ONLY that, re-run.
- Do NOT fix tests by deleting them. Do NOT skip failing tests.
</verification_rules>
"""


# ═══════════════════════════════════════════════════════════════
# 工具格式宪法（对标 Claude Code 工具描述作为微型prompt）
# ═══════════════════════════════════════════════════════════════

TOOL_FORMAT_CONSTITUTION = """<tool_constitution>
YOU MUST use this EXACT JSON format for ALL tool calls:

```json
{"tool": "file_write", "file_path": "path/to/file.py", "content": "complete code"}
```
```json
{"tool": "file_read", "file_path": "path/to/file.py"}
```
```json
{"tool": "bash_execute", "command": "pytest tests/ -v", "working_dir": "."}
```
```json
{"tool": "file_edit", "file_path": "f.py", "old_string": "exact old", "new_string": "new"}
```
```json
{"tool": "file_list", "directory": ".", "pattern": "*.py"}
```
```json
{"tool": "web_search", "query": "search terms"}
```

HARD RULES:
- ONE ```json block per tool call. Multiple calls = multiple blocks.
- "tool" field = tool name. ALL other fields = ACTUAL parameter names.
- file_write = NEW files ONLY. Never use it on an existing file.
- file_edit = ALL fixes to existing files. Change only the broken lines.
- "content" field in file_write MUST contain the complete file content.
- file_write auto-creates parent directories — do NOT run mkdir first.
- NO XML: <tool_call>, <function_calls>, <invoke>, <parameter> are FORBIDDEN.
- NO markdown calling: **Calling:** is FORBIDDEN.
- NO [TOOL_CALLS] blocks.

CRITICAL: The "content" string in file_write IS the file. Do NOT put code outside the JSON.
</tool_constitution>
"""


# ═══════════════════════════════════════════════════════════════
# Prompt Factory
# ═══════════════════════════════════════════════════════════════

@dataclass
class PromptContext:
    """Context for prompt assembly."""
    user_prompt: str = ""
    provider: str = "deepseek"
    model: str = ""
    working_dir: str = "."
    project_root: str = "."
    turn_number: int = 0
    task_context: str = ""        # 规格书等关键内容
    files_created: set = field(default_factory=set)
    files_read: set = field(default_factory=set)
    tool_results: str = ""        # 当前轮的工具结果
    scene: str = ""               # 场景指令
    is_first_turn: bool = True
    is_completion_warning: bool = False
    pytest_passed: int = 0
    pytest_failed: int = 0


class PromptFactory:
    """Assembles prompts using 4-framework best practices."""

    def __init__(self, mycelium_path: str | None = None):
        self._mycelium_path = mycelium_path
        self._mycelium_cached: str | None = None

    # ── Mycelium loading (对标 Claude Code CLAUDE.md 加载) ──

    def load_mycelium(self) -> str:
        """Load mycelium.md with caching (loaded once, reused across turns)."""
        if self._mycelium_cached is not None:
            return self._mycelium_cached
        if self._mycelium_path:
            try:
                self._mycelium_cached = Path(self._mycelium_path).read_text(encoding="utf-8")
                return self._mycelium_cached
            except Exception:
                pass
        self._mycelium_cached = ""
        return ""

    # ── 模型特定提示词选择（对标 OpenCode system.ts provider()）──

    def get_model_specific_prompt(self, provider: str) -> str:
        """Select model-specific instructions based on provider."""
        provider_lower = provider.lower() if provider else ""
        if "deepseek" in provider_lower:
            return MODEL_PROMPTS["deepseek"]
        if any(k in provider_lower for k in ("claude", "anthropic")):
            return MODEL_PROMPTS["anthropic"]
        if any(k in provider_lower for k in ("openai", "gpt")):
            return MODEL_PROMPTS["openai"]
        return MODEL_PROMPTS["default"]

    # ── 环境上下文（对标 OpenCode environment()）──

    def get_environment_context(self, ctx: PromptContext) -> str:
        """Build environment context snippet."""
        return (
            f"<env>\n"
            f"  OS: {platform.system()} {platform.release()}\n"
            f"  Shell: Git Bash (Unix commands work)\n"
            f"  Project: {ctx.project_root}\n"
            f"  Working dir: {ctx.working_dir}\n"
            f"  Python: {platform.python_version()}\n"
            f"  Model: {ctx.provider}/{ctx.model}\n"
            f"  Turn: {ctx.turn_number}\n"
            f"</env>"
        )

    # ── 渐进式工具披露（对标 Kun Feature Flag）──

    def get_tool_reference(self, ctx: PromptContext) -> str:
        """Build progressive tool reference — show only relevant tools."""
        # 基础工具：所有任务都需要
        base_tools = (
            "file_write(path,content)  file_read(path)  bash_execute(cmd,dir)\n"
            "file_edit(path,old,new)   file_list(dir)    web_search(query)"
        )
        return (
            f"<tools>\n"
            f"{base_tools}\n"
            f"FORMAT: ```json {{\"tool\":\"name\",\"param\":\"value\"}} ```\n"
            f"🚫 NO XML. NO function_calls. NO invoke.\n"
            f"</tools>"
        )

    # ── System Reminder 包装（对标 OpenCode step>1 机制）──

    def wrap_system_reminder(self, content: str, ctx: PromptContext) -> str:
        """Wrap follow-up content in system-reminder for mid-task turns."""
        if ctx.is_first_turn:
            return content
        return (
            f"<system-reminder>\n"
            f"Turn {ctx.turn_number}. Task in progress.\n"
            f"Files created: {len(ctx.files_created)}. Files read: {len(ctx.files_read)}.\n"
            f"Continue the task. Do NOT restart from scratch.\n"
            f"</system-reminder>\n\n"
            f"{content}"
        )

    # ── 第一轮完整上下文装配（对标 Claude Code assemble）──

    def build_initial_prompt(self, ctx: PromptContext) -> str:
        """Build the FIRST turn prompt — full system + env + tools + user request."""
        mycelium = self.load_mycelium()

        parts = [
            # Layer 1: Immutable prefix (缓存友好)
            IMMUTABLE_PREFIX,
            # Layer 2: Model-specific instructions
            self.get_model_specific_prompt(ctx.provider),
            # Layer 3: Tool format constitution
            TOOL_FORMAT_CONSTITUTION,
            # Layer 4: Environment
            self.get_environment_context(ctx),
            # Layer 5: Mycelium (system constitution)
            f"<system_constitution>\n{mycelium}\n</system_constitution>" if mycelium else "",
        ]

        # Layer 6: Tool reference (progressive)
        parts.append(self.get_tool_reference(ctx))

        # Layer 7: User request
        parts.append(f"<user_request>\n{ctx.user_prompt}\n</user_request>")

        return "\n\n".join(p for p in parts if p)

    # ── Follow-up 上下文装配（对标 Claude Code 每轮重建）──

    def build_follow_up_prompt(self, ctx: PromptContext) -> str:
        """Build follow-up prompt with full context (not minimal)."""
        # 截断超长工具结果（对标 OpenCode 50KB→我们3000字符）
        results = ctx.tool_results[:3000]
        if len(ctx.tool_results) > 3000:
            results += "\n[truncated — use file_read for full content]"

        progress_parts = []
        if ctx.files_created:
            done = ", ".join(sorted(ctx.files_created)[-8:])
            progress_parts.append(f"✅ CREATED ({len(ctx.files_created)}): {done}")
        if ctx.files_read:
            already = ", ".join(sorted(ctx.files_read)[-5:])
            progress_parts.append(f"📖 READ (do NOT re-read): {already}")
        if ctx.pytest_passed > 0:
            progress_parts.append(f"🧪 Tests: {ctx.pytest_passed} passed, {ctx.pytest_failed} failed")
        progress = "\n".join(progress_parts)

        task_ctx = f"{ctx.task_context}\n" if ctx.task_context else ""

        # System reminder wrapper (对标 OpenCode)
        body = (
            f"{ctx.task_context}"
            f"<progress>\n{progress}\n</progress>\n\n"
            f"<results>\n{results}\n</results>\n\n"
            f"<instruction>\n{ctx.scene}\n</instruction>"
        )

        if ctx.is_completion_warning:
            # 完成信号：不展示工具，用强力停止语言
            body = (
                f"⛔ TASK COMPLETE — FINAL TURN ⛔\n\n"
                f"{body}\n\n"
                f"OUTPUT ONLY A TEXT SUMMARY. NO TOOLS. NO JSON. NO file_read. NO file_list."
            )
            return body

        # 正常 follow-up：包含工具格式提醒
        body = (
            f"<tools>file_write | file_read | bash_execute | file_edit | file_list | web_search</tools>\n"
            f"<format>```json {{\"tool\":\"name\",\"param\":\"value\"}} ```</format>\n\n"
            f"{body}"
        )

        return self.wrap_system_reminder(body, ctx)


# ═══════════════════════════════════════════════════════════════
# 工具修复管线（对标 Reasonix: Flatten → Scavenge → Truncation → Storm Guard）
# ═══════════════════════════════════════════════════════════════

class ToolCallRepairPipeline:
    """Post-process LLM responses to recover broken tool calls."""

    @staticmethod
    def scavenge(content: str) -> str:
        """Scavenge: extract tool-call JSON trapped inside <think> blocks or reasoning.

        DeepSeek sometimes puts tool calls inside reasoning_content that aren't
        in the final output. This scavenger finds and extracts them.
        """
        import re
        # If there are already valid tool calls, don't double-scavenge
        if '{"tool"' in content or '"tool":' in content:
            return content

        # Look for {"tool":"..."} patterns that might be trapped
        scavenged = []
        for m in re.finditer(r'\{\s*"tool"\s*:\s*"(\w+)"[^}]*\}', content):
            scavenged.append(m.group(0))

        if scavenged:
            return content + "\n\n" + "\n".join(
                f"```json\n{s}\n```" for s in scavenged
            )
        return content

    @staticmethod
    def detect_call_storm(recent_calls: list[str], threshold: int = 4) -> str | None:
        """Call-Storm Guard: detect repeated (tool, args) patterns.

        Returns the offending fingerprint if detected, None otherwise.
        """
        if len(recent_calls) < threshold:
            return None
        for fp in set(recent_calls):
            if recent_calls.count(fp) >= threshold:
                return fp
        return None

    @staticmethod
    def try_repair_truncated(json_str: str) -> str | None:
        """Truncation Recovery: attempt to close incomplete JSON.

        DeepSeek sometimes hits max_tokens mid-JSON. Try to close it.
        Returns repaired JSON or None.
        """
        import re
        json_str = json_str.strip()
        if json_str.endswith("}"):
            return None  # Already complete

        # Count open/close braces
        opens = json_str.count("{")
        closes = json_str.count("}")
        needed = opens - closes

        if needed > 0:
            # Check if we're mid-string
            in_string = False
            for ch in reversed(json_str):
                if ch == '"':
                    in_string = not in_string
                elif ch == '\\' and in_string:
                    break
            if in_string:
                json_str += '"'
                needed = opens - json_str.count("}")

            json_str += "}" * needed
            return json_str
        return None
