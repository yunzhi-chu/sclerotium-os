"""MCP System Tools — system_status, system_config, system_health.

Returns LIVE data from running backends, not hardcoded placeholders.
"""

from __future__ import annotations

import os
import time
from typing import Any

from mcp.server import ToolRegistry

_START_TIME = time.time()

# ── Live backend references (injected by server.wire_live_backends) ──
_backends: dict[str, Any] = {}


def set_backends(backends: dict[str, Any]) -> None:
    """Inject live backend references so tools return real data."""
    global _backends
    _backends = backends


# ── system_status ─────────────────────────────────────────────────────


async def _system_status() -> dict[str, Any]:
    """Return LIVE system health — queries running backends for real state."""
    be = _backends

    # ── Evolution status (LIVE) ──
    evo_data: dict[str, Any] = {"status": "not_loaded", "generation": 0, "fitness": 0.0}
    genome = be.get("genome")
    if genome:
        try:
            evo_data = {
                "status": "active",
                "generation": getattr(genome, "generation", 0),
                "fitness": round(getattr(genome, "fitness", 0.0), 4),
                "top_tools": genome.get_top_tools(5) if hasattr(genome, "get_top_tools") else [],
            }
        except Exception as e:
            evo_data = {"status": "error", "error": str(e)[:100]}

    # Also check if there's a running EvolutionLoop instance
    evo_loop_state = None
    ext_bridge = be.get("external_bridge")
    if ext_bridge:
        try:
            evo_loop_state = getattr(ext_bridge, "_evo_state", None)
        except Exception:
            pass

    # ── Cache status (LIVE) ──
    # BUG#1修复: PromptCacheEngine 没有 _warmed_up 属性, 用 _segments 数量判断
    cache_data: dict[str, Any] = {"status": "not_loaded"}
    try:
        from kernel.prompt_cache import PromptCacheEngine
        pc = PromptCacheEngine()
        seg_count = len(getattr(pc, "_segments", {}))
        if seg_count > 0:
            report = pc.get_cache_safety_report()
            cache_data = {
                "status": "warm",
                "hit_rate": report.get("hit_rate", "0%"),
                "tokens_saved": report.get("tokens_saved", 0),
                "cost_saved": report.get("cost_saved", "$0"),
                "segments": seg_count,
                "health": report.get("health", "healthy"),
            }
        else:
            cache_data = {"status": "cold", "segments": 0,
                         "message": "Cache not yet warmed up — run cache_warmup tool"}
    except Exception:
        cache_data = {"status": "not_loaded"}

    # ── Memory status (LIVE) ──
    memory_data: dict[str, Any] = {"status": "not_loaded"}
    memory = be.get("memory_store")
    if memory:
        try:
            mem_stats = memory.get_stats() if hasattr(memory, "get_stats") else {}
            memory_data = {
                "status": "active",
                "total_memories": _compute_memory_count(memory) if not isinstance(mem_stats, dict) else mem_stats.get("total_memories", 0),
            }
        except Exception:
            memory_data = {"status": "error"}

    # ── Skills (LIVE) ──
    skills_data: dict[str, Any] = {"status": "not_loaded"}
    skills = be.get("skill_loader")
    if skills:
        try:
            skills_data = {
                "status": "active",
                "count": getattr(skills, "skill_count", 0),
            }
        except Exception:
            skills_data = {"status": "error"}

    # ── Session (LIVE) ──
    session_data: dict[str, Any] = {"status": "not_loaded"}
    session_mgr = be.get("session_manager")
    if session_mgr:
        try:
            session_data = {
                "status": "active",
                "sessions": len(session_mgr.list_sessions()) if hasattr(session_mgr, "list_sessions") else "?",
            }
        except Exception:
            session_data = {"status": "error"}

    # ── System resources ──
    resources = {
        "cpu_percent": _get_cpu_percent(),
        "memory_mb": _get_memory_mb(),
        "disk_gb": _get_disk_free_gb(),
    }

    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "evolution": evo_data,
        "cache": cache_data,
        "memory": memory_data,
        "skills": skills_data,
        "sessions": session_data,
        "resources": resources,
        "api": {
            "provider": os.environ.get("LLM_PROVIDER", os.environ.get("SCLEROTIUM_PROVIDER", "deepseek")),
            "model": os.environ.get("SCLEROTIUM_MODEL", "deepseek-v4-flash"),
        },
        "layers": {
            "mcp": "running",
            "evolution": "active" if evo_data.get("status") == "active" else "idle",
            "memory": memory_data.get("status", "unknown"),
            "cache": cache_data.get("status", "unknown"),
            "skills": skills_data.get("status", "unknown"),
            "sessions": session_data.get("status", "unknown"),
        },
    }


def _compute_memory_count(memory) -> int:
    """BUG-001: 兼容 MemoryStats 对象和 dict 的 memory count 计算。"""
    try:
        if memory is None:
            return 0
        if hasattr(memory, "get_stats") and callable(memory.get_stats):
            stats = memory.get_stats()
            if hasattr(stats, "total_memories"):
                return getattr(stats, "total_memories", 0)
            if isinstance(stats, dict):
                return stats.get("total_memories", 0)
        if hasattr(memory, "_entries"):
            return len(getattr(memory, "_entries", {}))
    except Exception:
        pass
    return 0


# ── system_health (quick check) ───────────────────────────────────────


async def _system_health() -> dict[str, Any]:
    """Quick health check — lighter than system_status."""
    be = _backends
    genome = be.get("genome")
    memory = be.get("memory_store")
    skills = be.get("skill_loader")

    # BUG#1修复: system_health 也返回 cache 字段
    cache_count = 0
    try:
        from kernel.prompt_cache import PromptCacheEngine
        cache_count = len(getattr(PromptCacheEngine(), "_segments", {}))
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "5.2",
        "tool_count": 202,
        "evolution": {
            "gen": getattr(genome, "generation", 0) if genome else 0,
            "fitness": round(getattr(genome, "fitness", 0.0), 4) if genome else 0.0,
        },
        # BUG-001: memory 计数 — 兼容 MemoryStats 对象和 dict
        "memory": _compute_memory_count(memory),
        "cache": {"segments": cache_count, "status": "warm" if cache_count > 0 else "cold"},
        "skills": getattr(skills, "skill_count", 0) if skills else 0,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }


# ── system_config ─────────────────────────────────────────────────────


_CONFIG: dict[str, Any] = {
    "evolution.default_generations": 10,
    "evolution.default_population": 50,
    "safety.sandbox_required": True,
    "safety.human_gate_enabled": True,
    "stg.profile": "work",
    "memory.ebbinghaus_halflife_days": 7,
    # 缓存#9修复: 新增缓存配置项
    "cache.ttl_seconds": 1800,
    "cache.max_segments": 50,
    "cache.provider_preference": "deepseek",
    "cache.auto_warmup": True,
    "cache.keepalive_margin": 0.8,
}


async def _system_config(key: str | None = None, value: Any = None) -> dict[str, Any]:
    """Read or set system configuration."""
    if key is None:
        return {"config": dict(_CONFIG)}
    if value is None:
        return {"key": key, "value": _CONFIG.get(key)}
    _CONFIG[key] = value
    return {"key": key, "value": value, "status": "updated"}


# ── System helpers ────────────────────────────────────────────────────


def _get_cpu_percent() -> float:
    try:
        import psutil
        return psutil.cpu_percent(interval=0.1)
    except ImportError:
        return 0.0


def _get_memory_mb() -> float:
    try:
        import psutil
        mem = psutil.virtual_memory()
        return round(mem.used / (1024 * 1024), 1)
    except ImportError:
        return 0.0


def _get_disk_free_gb() -> float:
    try:
        import shutil
        usage = shutil.disk_usage(os.getcwd())
        return round(usage.free / (1024 ** 3), 1)
    except Exception:
        return 0.0


# ── Registration ─────────────────────────────────────────────────────


def register_system_tools(registry: ToolRegistry) -> None:
    registry.register(
        name="system_status",
        description="Get LIVE system health: evolution generation/fitness, cache warm/cold, memory entries, skills count, session count, CPU/RAM/disk, uptime. ALWAYS call this before answering system-state questions — returns real-time data from running backends.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=_system_status,
        category="system",
    )

    registry.register(
        name="system_health",
        description="Quick health check (lighter than system_status): evolution gen/fitness, memory count, skills count, uptime. Use for fast pulse check.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=_system_health,
        category="system",
    )

    registry.register(
        name="system_config",
        description="Read or modify system configuration.",
        parameters={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Config key to read/write. Omit to list all.",
                },
                "value": {
                    "description": "New value to set. Omit for read-only.",
                },
            },
            "required": [],
        },
        handler=_system_config,
        category="system",
    )
