"""Hooks System — Claude Code-equivalent PreToolUse/PostToolUse interception.

Claude Code hooks are Shell scripts that run deterministically at lifecycle points.
Sclerotium hooks are Python callables that can modify or block tool execution.

Hook points:
  PreToolUse   — Before tool execution (can block by returning False)
  PostToolUse  — After tool execution (can modify result)
  SessionStart — When session begins
  SessionStop  — When session ends
  PreCompact   — Before context compaction
"""
from __future__ import annotations
from typing import Any, Callable
from dataclasses import dataclass, field

HookFunc = Callable[..., Any]

@dataclass
class Hook:
    name: str; point: str; matcher: str = "*"
    pattern: str = "*"; fn: HookFunc | None = None
    enabled: bool = True

class HookSystem:
    def __init__(self): self._hooks: list[Hook] = []
    def register(self, hook: Hook): self._hooks.append(hook)
    def unregister(self, name: str): self._hooks = [h for h in self._hooks if h.name != name]

    def run(self, point: str, tool_name: str = "", args: dict[str, Any] | None = None,
            result: Any = None) -> tuple[bool, Any]:
        """Run all matching hooks. Returns (allow, modified_result)."""
        modified = result
        for h in self._hooks:
            if h.point != point or not h.enabled: continue
            if h.matcher != "*" and h.matcher != tool_name: continue
            if h.pattern != "*" and h.pattern not in str(args or ""): continue
            try:
                if point == "PreToolUse":
                    r = h.fn(tool_name, args or {}) if h.fn else True
                    if r is False: return False, modified
                elif point == "PostToolUse" and h.fn:
                    modified = h.fn(tool_name, args or {}, result)
            except Exception: pass
        return True, modified

# ── Built-in hooks ──
def auto_format_hook(tool_name: str, args: dict, result: Any = None) -> Any:
    """PostToolUse: auto-run ruff/black on edited Python files."""
    import subprocess
    fp = args.get("file_path") or args.get("path") or ""
    if fp and fp.endswith(".py") and tool_name in ("file_write","file_edit"):
        try:
            r = subprocess.run(["ruff", "check", "--fix", fp], capture_output=True, timeout=10)
            if result and isinstance(result, dict):
                result["auto_format"] = r.stdout.decode()[:200] if r.stdout else "ok"
        except Exception: pass
    return result

def git_auto_add_hook(tool_name: str, args: dict, result: Any = None) -> Any:
    """PostToolUse: auto-git-add files after write/edit."""
    import subprocess
    fp = args.get("file_path") or args.get("path") or ""
    if fp and tool_name in ("file_write", "file_edit"):
        try: subprocess.run(["git", "add", fp], capture_output=True, timeout=5)
        except Exception: pass
    return result
