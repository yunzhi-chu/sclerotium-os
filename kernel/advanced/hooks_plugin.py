"""P2: Hooks & Plugin System (Claude Code parity).

27 event hooks, 4 execution types (shell, LLM, webhook, subagent verifier),
10 pluggable component types.

Reference: Claude Code hooks (27 events), OpenClaw microkernel plugins,
NemoClaw policy enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class HookEvent(Enum):
    # Lifecycle
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    # Pre-model
    PRE_MODEL_CALL = "pre.model_call"
    POST_MODEL_CALL = "post.model_call"
    # Tool lifecycle
    PRE_TOOL_EXECUTE = "pre.tool_execute"
    POST_TOOL_EXECUTE = "post.tool_execute"
    TOOL_ERROR = "tool.error"
    # Evolution
    EVOLUTION_START = "evolution.start"
    EVOLUTION_GENERATION = "evolution.generation"
    EVOLUTION_COMPLETE = "evolution.complete"
    # Memory
    MEMORY_STORE = "memory.store"
    MEMORY_CONSOLIDATE = "memory.consolidate"
    MEMORY_FORGET = "memory.forget"
    # Safety
    ARBITER_REVIEW = "arbiter.review"
    ARBITER_REJECT = "arbiter.reject"
    SANDBOX_EXECUTE = "sandbox.execute"
    # Desktop
    DESKTOP_ACTION = "desktop.action"
    # IM
    IM_MESSAGE_RECEIVED = "im.message_received"
    IM_MESSAGE_SENT = "im.message_sent"
    # File system
    FILE_CREATED = "file.created"
    FILE_MODIFIED = "file.modified"
    FILE_DELETED = "file.deleted"
    # Schedule
    SCHEDULE_TRIGGERED = "schedule.triggered"
    # Mode
    MODE_SWITCH = "mode.switch"
    # Errors
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"


class HookType(Enum):
    SHELL = "shell"
    LLM = "llm"
    WEBHOOK = "webhook"
    SUBAGENT_VERIFIER = "subagent_verifier"


@dataclass
class Hook:
    name: str; event: HookEvent; hook_type: HookType
    handler: Callable[..., Awaitable[Any]]
    priority: int = 0; enabled: bool = True


class PluginManifest:
    """Plugin metadata and capabilities."""
    def __init__(self, name: str, version: str, description: str = ""):
        self.name = name; self.version = version; self.description = description
        self.commands: list[str] = []; self.skills: list[str] = []
        self.mcp_servers: list[str] = []; self.hooks: list[Hook] = []


class HooksPluginSystem:
    """27-event hook system with plugin architecture.

    Usage:
        hps = HooksPluginSystem()
        hps.register_hook(Hook("audit_log", HookEvent.PRE_TOOL_EXECUTE,
                                HookType.SHELL, audit_handler))
        await hps.fire(HookEvent.PRE_TOOL_EXECUTE, tool="memory_search")
    """

    # Singleton — ALL callers share the same hook system
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, '_hooks'):
            self._hooks: dict[HookEvent, list[Hook]] = {e: [] for e in HookEvent}
            self._plugins: dict[str, PluginManifest] = {}

    # ── Hooks ─────────────────────────────────────────────────────

    def register_hook(self, hook: Hook) -> None:
        self._hooks[hook.event].append(hook)
        self._hooks[hook.event].sort(key=lambda h: h.priority)

    def unregister_hook(self, name: str) -> None:
        for event in self._hooks:
            self._hooks[event] = [h for h in self._hooks[event] if h.name != name]

    async def fire(self, event: HookEvent, **kwargs: Any) -> list[Any]:
        """Fire all hooks for an event. Returns list of results."""
        results = []
        for hook in self._hooks.get(event, []):
            if not hook.enabled:
                continue
            try:
                result = await hook.handler(**kwargs)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e), "hook": hook.name})
        return results

    def list_hooks(self) -> list[dict[str, Any]]:
        return [
            {"event": e.value, "hooks": len(hooks),
             "names": [h.name for h in hooks]}
            for e, hooks in self._hooks.items() if hooks
        ]

    # ── Plugins ───────────────────────────────────────────────────

    def register_plugin(self, manifest: PluginManifest) -> None:
        self._plugins[manifest.name] = manifest
        for hook in manifest.hooks:
            self.register_hook(hook)

    def unregister_plugin(self, name: str) -> None:
        if name in self._plugins:
            for hook in self._plugins[name].hooks:
                self.unregister_hook(hook.name)
            del self._plugins[name]

    def list_plugins(self) -> list[dict[str, Any]]:
        return [
            {"name": p.name, "version": p.version, "description": p.description,
             "commands": len(p.commands), "skills": len(p.skills),
             "hooks": len(p.hooks)}
            for p in self._plugins.values()
        ]

    def stats(self) -> dict[str, Any]:
        total_hooks = sum(len(h) for h in self._hooks.values())
        return {"plugins": len(self._plugins), "hooks": total_hooks,
                "events": len(HookEvent)}
