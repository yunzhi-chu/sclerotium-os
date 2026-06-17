"""MCP Scheduler Tools — persistence + real tool execution.

Every scheduled job can call ANY registered MCP tool, execute skills,
or invoke MCP servers. Zero fake data — all real execution.

Supports:
  - tool_call    → calls any tool in the global ToolRegistry (200+ tools)
  - skill_run    → executes a skill by name
  - bash         → runs a shell command
  - notify       → sends result to WeChat
  - health_check → system health snapshot
  - composite    → chain multiple actions
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from mcp.server import ToolRegistry
from scheduler.engine import SchedulerEngine

# Task result log — persists every execution so results survive restarts
_RESULTS_FILE = Path("data/scheduler_results.jsonl")
_RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
_RESULTS_LOCK = threading.Lock()

_engine: SchedulerEngine | None = None
_global_registry: ToolRegistry | None = None
_registry_lock = threading.Lock()


def _persist_result(job_name: str, action_type: str, result: str, success: bool = True) -> None:
    """Append task execution result to the persistent log (thread-safe)."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "job_name": job_name,
        "action_type": action_type,
        "success": success,
        "result": result[:3000],  # Truncate for storage
    }
    with _RESULTS_LOCK:
        try:
            with open(_RESULTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass  # Don't let disk errors crash the scheduler


# ═══════════════════════════════════════════════════════════════
# Global Tool Registry (lazy init, all 200+ tools)
# ═══════════════════════════════════════════════════════════════

def _get_global_registry() -> ToolRegistry:
    """Get or create a ToolRegistry with ALL tools registered.

    This is a standalone registry for the scheduler — it doesn't
    depend on the MCP server being running.
    """
    global _global_registry
    if _global_registry is not None:
        return _global_registry

    with _registry_lock:
        if _global_registry is not None:
            return _global_registry

        registry = ToolRegistry()
        # Import and register all tool categories
        _register_all(registry)
        _global_registry = registry
        print(f"[Scheduler] Global registry ready: {registry.tool_count} tools")
        return registry


def _register_all(reg: ToolRegistry) -> None:
    """Register all tool categories into the given registry."""
    modules = [
        ("mcp.tools.system", "register_system_tools"),
        ("mcp.tools.evolution", "register_evolution_tools"),
        ("mcp.tools.memory", "register_memory_tools"),
        ("mcp.tools.sandbox", "register_sandbox_tools"),
        ("mcp.tools.skills", "register_skills_tools"),
        ("mcp.tools.code_analysis", "register_code_analysis_tools"),
        ("mcp.tools.im", "register_im_tools"),
        ("mcp.tools.desktop", "register_desktop_tools"),
        ("mcp.tools.files", "register_files_tools"),
        ("mcp.tools.info", "register_info_tools"),
        ("mcp.tools.mode", "register_mode_tools"),
        ("mcp.tools.gateways", "register_gateway_tools"),
        ("mcp.tools.advanced", "register_advanced_tools"),
        ("mcp.tools.sovereign", "register_sovereign_tools"),
        ("mcp.tools.genesis", "register_genesis_tools"),
        ("mcp.tools.cosmic", "register_cosmic_tools"),
        ("mcp.tools.omega", "register_omega_tools"),
        ("mcp.tools.innovation", "register_innovation_tools"),
        ("mcp.tools.apotheosis", "register_apotheosis_tools"),
        ("mcp.tools.cache_engine", "register_cache_tools"),
        ("mcp.tools.evolution_bridge", "register_evolution_bridge_tools"),
        ("mcp.tools.benchmark", "register_benchmark_tools"),
        ("mcp.tools.web_search", "register_web_tools"),
        ("mcp.tools.codebase_search", "register_codebase_tools"),
        ("mcp.tools.git_tools", "register_git_tools"),
        ("mcp.tools.bash_tool", "register_bash_tools"),
        ("mcp.tools.file_ops", "register_file_ops"),
        ("mcp.tools.os_commands", "register_os_commands"),
        ("mcp.tools.installer", "register_installer_tools"),
        ("mcp.tools.scheduler_mcp", "register_scheduler_mcp_tools"),
    ]
    for mod_name, func_name in modules:
        try:
            mod = __import__(mod_name, fromlist=[func_name])
            getattr(mod, func_name)(reg)
        except Exception as e:
            pass  # Silently skip unavailable modules


# ═══════════════════════════════════════════════════════════════
# Universal Tool Executor
# ═══════════════════════════════════════════════════════════════

def _invoke_tool(tool_name: str, tool_args: dict | None) -> str:
    """Invoke ANY registered MCP tool by name with real execution.

    Looks up the tool in the global registry, calls its handler
    with the provided arguments, and returns the result as a string.
    """
    if not tool_name:
        return "Error: no tool_name provided"

    args = tool_args or {}
    registry = _get_global_registry()

    # 1) Try the global ToolRegistry (200+ tools)
    handler = registry.get_handler(tool_name)
    if handler is not None:
        return _call_async_handler(handler, args, tool_name)

    # 2) Try alias mappings
    aliases = {
        "search": "web_search", "bash": "bash_smart",
        "status": "system_status", "health": "system_health",
        "memory": "memory_search", "evolution": "evolution_status",
        "file_read": "file_read", "file_write": "file_write",
        "list_files": "list_files", "git_status": "git_status",
        "git_log": "git_log", "im_send": "im_send",
        "desktop_screenshot": "desktop_screenshot",
        "codebase_search": "codebase_search", "web_fetch": "web_fetch",
        "cache_compare": "cache_compare", "memory_dream": "memory_dream",
        "quantum_verify": "quantum_verify", "ring0_review": "ring0_review",
        "goal_list": "goal_list", "schedule_list": "schedule_list",
    }
    resolved = aliases.get(tool_name, tool_name)
    if resolved != tool_name:
        handler = registry.get_handler(resolved)
        if handler is not None:
            return _call_async_handler(handler, args, resolved)

    # 3) Fallback: try to import and call directly
    return _fallback_tool_call(tool_name, args)


def _call_async_handler(handler, args: dict, tool_name: str) -> str:
    """Call an async MCP tool handler from a synchronous context."""
    try:
        # Call the handler
        coro_or_result = handler(**args)

        # If it's a coroutine, we need to run it
        if asyncio.iscoroutine(coro_or_result):
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # Running in async context — use thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(_run_coro_in_new_loop, coro_or_result)
                    result = future.result(timeout=300)
            else:
                result = loop.run_until_complete(coro_or_result)
            return _format_tool_result(result)

        # Not a coroutine — handler returned directly
        return _format_tool_result(coro_or_result)

    except Exception as e:
        # Fallback: try the built-in implementation
        return _fallback_tool_call(tool_name, args)


def _run_coro_in_new_loop(coro) -> Any:
    """Run a coroutine in a fresh event loop (thread-safe)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _format_tool_result(result: Any) -> str:
    """Format a tool result into a readable string."""
    if isinstance(result, str):
        return result[:2000]
    if isinstance(result, dict):
        # Extract common fields
        if "content" in result:
            return str(result["content"])[:2000]
        if "result" in result:
            return str(result["result"])[:2000]
        if "stdout" in result:
            return str(result["stdout"])[:1500]
        if "message" in result:
            return str(result["message"])[:2000]
        if "status" in result and "data" in result:
            return json.dumps(result["data"], ensure_ascii=False, indent=2)[:2000]
        # Generic: serialize nicely
        return json.dumps(result, ensure_ascii=False, indent=2)[:2000]
    if isinstance(result, list):
        return json.dumps(result, ensure_ascii=False, indent=2)[:2000]
    return str(result)[:2000]


def _fallback_tool_call(tool_name: str, args: dict) -> str:
    """Last-resort: try common built-in operations directly."""
    q = args.get("query", args.get("q", args.get("prompt", "")))

    if tool_name in ("web_search", "search"):
        return _web_search_multi_engine(q or str(args))

    if tool_name in ("bash_smart", "bash_exec"):
        cmd = args.get("command", args.get("cmd", ""))
        if not cmd:
            return "Error: no command"
        try:
            import subprocess
            r = subprocess.run(cmd, shell=True, timeout=300,
                              capture_output=True, text=True)
            return (r.stdout or r.stderr)[:2000]
        except Exception as e:
            return f"Bash error: {e}"

    if tool_name in ("system_health", "system_status"):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            return (
                f"CPU: {cpu}% | RAM: {mem.percent}% ({mem.used//1024//1024}MB/{mem.total//1024//1024}MB) | "
                f"Disk: {disk.percent}% ({disk.free//1024//1024//1024}GB free) | "
                f"Processes: {len(psutil.pids())}"
            )
        except Exception as e:
            return f"System status error: {e}"

    if tool_name == "schedule_list":
        jobs = _schedule_list()
        return json.dumps(jobs, ensure_ascii=False, indent=2)[:2000]

    return f"Tool '{tool_name}' not found in registry ({_get_global_registry().tool_count} tools available). Try: web_search, system_health, bash_smart, schedule_list, memory_search, etc."


# ═══════════════════════════════════════════════════════════════
# Real Web Search (multi-engine, China-friendly)
# ═══════════════════════════════════════════════════════════════

def _web_search_multi_engine(query: str) -> str:
    """Claude Code-quality search: SearXNG → Brave → Bing → Baidu → DDG."""
    if not query:
        return "Error: no search query"

    # Try the high-quality web_search function first (SearXNG + APIs)
    try:
        from mcp.tools.web_search import web_search
        result = web_search(query=query, max_results=8)
        source = result.get("source", "unknown")
        results = result.get("results", [])
        if results:
            lines = [f"[{source}] {query}:"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "")[:120]
                snippet = r.get("snippet", "")[:200]
                lines.append(f"\n{i}. {title}")
                if snippet:
                    lines.append(f"   {snippet}")
            return "\n".join(lines)[:2000]
    except Exception:
        pass

    # Fallback: direct HTML scraping
    for name, fn in [("Bing", _try_bing), ("Baidu", _try_baidu), ("DDG", _try_ddg)]:
        try:
            results = fn(query)
            if results:
                lines = [f"[{name}] {query}:"]
                for i, r in enumerate(results[:8], 1):
                    title = r.get("title", "")[:100]
                    snippet = r.get("snippet", "")[:150]
                    lines.append(f"\n{i}. {title}")
                    if snippet:
                        lines.append(f"   {snippet}")
                return "\n".join(lines)[:2000]
        except Exception:
            continue

    return f"No results found for: {query}"


def _http_get(url: str, timeout: int = 8) -> str:
    """HTTP GET with browser-like headers."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
    })
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def _try_baidu(query: str) -> list[dict]:
    """Baidu search with robust multi-pattern parsing."""
    html = _http_get(f"https://www.baidu.com/s?wd={urllib.parse.quote(query)}&rn=10", timeout=8)
    results = []
    seen = set()

    # Strategy 1: h3.t blocks with real external links
    for block in re.finditer(
        r'<h3[^>]*class="[^"]*t[^"]*"[^>]*>(.*?)</h3>',
        html, re.IGNORECASE | re.DOTALL,
    ):
        if len(results) >= 8:
            break
        inner = block.group(1)
        link = re.search(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', inner, re.IGNORECASE | re.DOTALL)
        if not link:
            continue
        href = link.group(1)
        if 'baidu.com' in href or 'hao123' in href or href in seen:
            continue
        seen.add(href)
        title = re.sub(r'<[^>]+>', '', link.group(2)).strip()
        if not title or len(title) < 3:
            continue
        # Find snippet near this h3
        after = html[block.end():block.end() + 2000]
        snip = re.search(r'<(?:span|div)[^>]*class="[^"]*(?:c-abstract|content-right)[^"]*"[^>]*>(.*?)</(?:span|div)>',
                        after, re.IGNORECASE | re.DOTALL)
        snippet = re.sub(r'<[^>]+>', '', snip.group(1)).strip() if snip else ""
        results.append({"title": html_decode(title)[:120], "url": href, "snippet": snippet[:200]})

    # Strategy 2: generic external links with smart filtering
    if not results:
        for m in re.finditer(
            r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.+?)</a>',
            html, re.IGNORECASE | re.DOTALL,
        ):
            if len(results) >= 8:
                break
            href = m.group(1)
            title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if 'baidu.com' in href or 'hao123' in href or href in seen:
                continue
            if not title or len(title) < 4:
                continue
            seen.add(href)
            results.append({"title": html_decode(title)[:120], "url": href, "snippet": ""})

    return results


def html_decode(text: str) -> str:
    """Decode HTML entities."""
    import html as _html
    return _html.unescape(text)


def _try_bing(query: str) -> list[dict]:
    """Bing China search."""
    encoded = urllib.parse.quote(query)
    html = _http_get(f"https://cn.bing.com/search?q={encoded}&count=10", timeout=8)
    results = []
    for m in re.finditer(
        r'<li class="b_algo"[^>]*>.*?<h2[^>]*>.*?<a[^>]*href="(https?://[^"]*)"[^>]*>(.*?)</a>',
        html, re.DOTALL,
    ):
        title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if title and len(title) > 2:
            results.append({"title": title[:120], "url": m.group(1), "snippet": ""})
        if len(results) >= 8:
            break
    return results


def _try_ddg(query: str) -> list[dict]:
    """DuckDuckGo Lite search."""
    encoded = urllib.parse.quote(query)
    html = _http_get(f"https://lite.duckduckgo.com/lite/?q={encoded}", timeout=8)
    titles = re.findall(r'<a[^>]*class="result-link"[^>]*>([^<]+)</a>', html)
    snippets = re.findall(r'<td[^>]*class="result-snippet"[^>]*>([^<]+)</td>', html)
    results = []
    for i in range(min(len(titles), len(snippets), 8)):
        results.append({"title": titles[i].strip(), "snippet": snippets[i].strip()})
    return results


# ═══════════════════════════════════════════════════════════════
# Scheduler Engine Access
# ═══════════════════════════════════════════════════════════════

def _get_engine() -> SchedulerEngine:
    global _engine
    if _engine is None:
        _engine = SchedulerEngine()
        _engine.set_handler_factory(_make_action_handler)
        _engine.initialize()
    return _engine


# ═══════════════════════════════════════════════════════════════
# Action Handler Factory
# ═══════════════════════════════════════════════════════════════

def _make_action_handler(action_type: str, action_params: dict | None):
    """Create a handler that executes REAL actions via the global ToolRegistry.

    Returns a synchronous callable for BackgroundScheduler/Timer compatibility.
    Results are always pushed to WeChat.
    """
    params = action_params or {}

    def _wechat(msg: str):
        """Push result to WeChat via thread-safe outbox queue.

        Falls back to disk persistence if WeChat is unavailable
        (no sender yet, import error, etc.). Results are NEVER silently lost.
        """
        if not msg:
            return
        pushed = False
        try:
            from platforms.wechat_ilink import notify_system_result
            pushed = notify_system_result(msg[:1500])
        except Exception:
            pass
        if not pushed:
            # WeChat unavailable — result is still in the persistent log
            pass

    def _format_for_wechat(raw: str, action: str) -> str:
        """Format raw tool output into a human-readable WeChat message.

        No JSON dumps, no raw dicts. Clean, readable text only.
        """
        if not raw:
            return ""

        # Try to parse as JSON
        data = None
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass

        if data is None:
            # Plain text — use as-is
            return raw.strip()[:1200]

        # Web search results
        if "results" in data or "query" in data:
            results = data.get("results", [])
            query = data.get("query", "")
            if results:
                lines = []
                if query:
                    lines.append(f"{query}:")
                for i, r in enumerate(results[:5], 1):
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    # Clean up the title — remove URL fragments
                    if "http" in title:
                        title = title.split("http")[0].strip()
                    lines.append(f"\n{i}. {title}")
                    if snippet:
                        # Extract key data points from snippet
                        clean = snippet.replace(" ", " ").replace(" ", " ")
                        lines.append(f"   {clean[:200]}")
                return "\n".join(lines)[:1200]

        # System status
        if "uptime_seconds" in data or "evolution" in data:
            evo = data.get("evolution", {})
            cache = data.get("cache", {})
            mem = data.get("memory", {})
            return (
                f"System: up {data.get('uptime_seconds', 0):.0f}s | "
                f"Evolution: Gen{evo.get('generation',0)} fit={evo.get('fitness',0):.3f} | "
                f"Cache: {cache.get('segments',0)} segments | "
                f"Memory: {mem.get('total_memories',0)} entries"
            )

        # Generic dict — extract meaningful fields
        keys = list(data.keys())
        if "status" in keys and len(keys) <= 3:
            # Simple status response
            status = data.get("status", "")
            msg = data.get("message", data.get("result", data.get("content", "")))
            if msg:
                return f"[{status}] {str(msg)[:1000]}"
            return f"[{status}] {str(data)[:500]}"

        # Fallback: key-value summary
        parts = []
        for k, v in data.items():
            if k in ("results", "data", "_cache", "raw"):
                continue
            if isinstance(v, (int, float, str, bool)):
                parts.append(f"{k}: {v}")
        if parts:
            return " | ".join(parts[:8])[:800]

        return str(data)[:800]

    def handler():
        now = time.strftime("%H:%M:%S")
        print(f"[Scheduler] [{now}] FIRE: {action_type}")

        result = ""

        if action_type == "tool_call":
            tool = params.get("tool_name", params.get("tool", ""))
            tool_args = params.get("tool_args", params.get("args", {}))
            if not tool:
                result = "Error: tool_name not specified in action_params"
            else:
                result = _invoke_tool(tool, tool_args)

        elif action_type == "skill_run":
            skill = params.get("skill_name", params.get("skill", ""))
            skill_args = params.get("skill_args", params.get("args", {}))
            if not skill:
                result = "Error: skill_name not specified"
            else:
                # Skills are executed via the skills tool
                result = _invoke_tool("skill_search", {"query": skill})
                if "not found" in result.lower() or "no " in result.lower():
                    result = _invoke_tool("skill_execute", {"name": skill, "args": skill_args})

        elif action_type == "bash":
            cmd = params.get("command", params.get("cmd", ""))
            if cmd:
                result = _invoke_tool("bash_smart", {"action": cmd, "context": ""})

        elif action_type == "notify":
            result = params.get("message", params.get("title", ""))

        elif action_type == "search_and_report":
            query = params.get("query", params.get("q", ""))
            if query:
                result = _web_search_multi_engine(query)

        elif action_type == "composite":
            # Chain multiple sub-actions
            actions = params.get("actions", [])
            parts = []
            for act in actions:
                at = act.get("action_type", act.get("type", "tool_call"))
                ap = act.get("action_params", act.get("params", {}))
                r = _make_action_handler(at, ap)()
                parts.append(r)
            result = "\n---\n".join(parts)

        elif action_type == "health_check":
            result = _fallback_tool_call("system_health", {})

        elif action_type == "schedule_status":
            result = json.dumps(_schedule_list(), ensure_ascii=False, indent=2)

        else:
            # Try as a tool name directly
            result = _invoke_tool(action_type, params)

        # Log raw result, persist to disk, and push formatted text to WeChat
        print(f"[Scheduler] [{now}] Result: {str(result)[:200]}")
        if result:
            formatted = _format_for_wechat(result, action_type)
            _wechat(formatted)
        # ALWAYS persist — even empty/error results
        job_name = params.get("_job_name", params.get("name", action_type))
        _persist_result(job_name, action_type, str(result)[:3000])

    return handler


# ═══════════════════════════════════════════════════════════════
# MCP Tool Handlers (schedule_add, schedule_list, etc.)
# ═══════════════════════════════════════════════════════════════

async def _schedule_add(name: str, trigger: str, trigger_config: dict,
                        action_type: str, action_params: dict | None = None,
                        enabled: bool = True) -> dict:
    engine = _get_engine()
    handler = _make_action_handler(action_type, action_params)
    job_id = engine.add_job(
        name, trigger, trigger_config, handler, enabled,
        action_type=action_type, action_params=action_params,
    )
    if job_id:
        print(f"[Scheduler] Job created + persisted: {name} ({trigger})")
    return {"job_id": job_id, "name": name, "trigger": trigger,
            "action_type": action_type, "enabled": enabled}


async def _schedule_list() -> list[dict]:
    engine = _get_engine()
    return [{"job_id": j.job_id, "name": j.name, "trigger": j.trigger,
             "trigger_desc": j.trigger_description, "next_run": j.next_run_time,
             "enabled": j.enabled, "status": j.status}
            for j in engine.list_jobs()]


async def _schedule_remove(job_id: str) -> dict:
    engine = _get_engine()
    ok = engine.remove_job(job_id)
    return {"status": "removed" if ok else "not_found", "job_id": job_id}


async def _schedule_update(job_id: str, name: str = "", trigger_config: dict | None = None,
                           enabled: bool | None = None) -> dict:
    engine = _get_engine()
    job = engine.get_job(job_id)
    if not job:
        return {"status": "not_found", "job_id": job_id}
    if name:
        job.name = name
    if trigger_config:
        job.trigger_config = trigger_config
    if enabled is not None:
        engine.toggle_job(job_id, enabled)
    return {"status": "updated", "job_id": job_id, "name": job.name}


async def _schedule_toggle(job_id: str, enabled: bool) -> dict:
    engine = _get_engine()
    ok = engine.toggle_job(job_id, enabled)
    return {"status": "ok" if ok else "not_found", "enabled": enabled}


async def _schedule_log(count: int = 20, job_name: str = "") -> dict:
    """Read the persistent task execution log.

    Returns the most recent task results from data/scheduler_results.jsonl.
    Results survive restarts — always available even if WeChat was offline.
    """
    if not _RESULTS_FILE.exists():
        return {"status": "empty", "results": [], "count": 0,
                "message": "No task results yet. Scheduled tasks haven't fired, or results were cleared."}

    results = []
    try:
        with open(_RESULTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if job_name and job_name not in entry.get("job_name", ""):
                        continue
                    results.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        return {"status": "error", "results": [], "count": 0, "error": str(e)}

    # Return most recent first
    results.reverse()
    total = len(results)
    results = results[:count]

    return {
        "status": "ok",
        "results": results,
        "count": len(results),
        "total": total,
        "file": str(_RESULTS_FILE),
    }


def register_scheduler_mcp_tools(registry: ToolRegistry) -> None:
    # Register our own tools AFTER initializing the global registry reference
    global _global_registry
    if _global_registry is None:
        _global_registry = registry
        print(f"[Scheduler] Global registry set: {registry.tool_count} tools")

    for name, desc, params, handler in [
        ("schedule_add",
         "Create a scheduled task. action_type: tool_call (calls ANY of 200+ tools), skill_run, bash, notify, search_and_report, health_check, composite (chain multiple). action_params.tool_name specifies which tool to call. ALL execution is REAL — no fake data.",
         {"type": "object", "properties": {
             "name": {"type": "string"},
             "trigger": {"type": "string", "description": "cron, interval, or date"},
             "trigger_config": {"type": "object", "description": "{seconds: 30} for interval, {hour:9,minute:0} for cron"},
             "action_type": {"type": "string", "description": "tool_call, skill_run, bash, notify, search_and_report, health_check, composite"},
             "action_params": {"type": "object", "description": '{"tool_name": "web_search", "tool_args": {"query": "上证指数"}}'},
             "enabled": {"type": "boolean", "default": True}},
          "required": ["name", "trigger", "trigger_config", "action_type"]},
         _schedule_add),
        ("schedule_list", "List all scheduled tasks.", {"type": "object", "properties": {}, "required": []}, _schedule_list),
        ("schedule_remove", "Remove a scheduled task.", {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}, _schedule_remove),
        ("schedule_update", "Update a scheduled task.", {"type": "object", "properties": {"job_id": {"type": "string"}, "name": {"type": "string"}, "trigger_config": {"type": "object"}, "enabled": {"type": "boolean"}}, "required": ["job_id"]}, _schedule_update),
        ("schedule_toggle", "Enable/disable a scheduled task.", {"type": "object", "properties": {"job_id": {"type": "string"}, "enabled": {"type": "boolean"}}, "required": ["job_id", "enabled"]}, _schedule_toggle),
        ("schedule_log", "View past scheduled task execution results. Results are persisted to disk and survive restarts. Use this to check what your scheduled tasks produced.", {"type": "object", "properties": {"count": {"type": "integer", "default": 20, "description": "Number of recent results to return"}, "job_name": {"type": "string", "description": "Filter by job name (optional)"}}, "required": []}, _schedule_log),
    ]:
        registry.register(name=name, description=desc, parameters=params, handler=handler, category="scheduler")
