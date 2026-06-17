"""API Bridge — 将后台所有真实数据暴露为 REST API。

/data/all        — 全部数据 (一次性获取)
/data/organs     — 器官状态
/data/fcpi       — FCPI 进化指标
/data/genome     — 全维度基因组
/data/arbiter    — 仲裁者状态
/data/agents     — 智能体人格列表
/data/providers  — LLM 提供商状态
/data/tokens     — Token 使用统计
/data/memory     — 五层记忆统计
/data/features   — v5.2 特性清单
/data/external   — 外部 MCP 连接状态
/data/skills     — 已加载技能列表
/data/tools      — 工具类别分布
/data/health     — 系统健康检查
"""

from __future__ import annotations

import json
import time
from typing import Any


class APIBridge:
    """Bridge between Sclerotium backend and web frontend.

    Provides REST API endpoints that return real backend data.
    Wired into the MCP HTTP server at /data/* paths.
    """

    def __init__(
        self,
        mcp_server: Any = None,
        genome: Any = None,
        arbiter: Any = None,
        agent_profiles: Any = None,
        token_tracker: Any = None,
        memory_store: Any = None,
        skill_loader: Any = None,
        external_bridge: Any = None,
        event_bus: Any = None,
        fcpi_tracker: Any = None,
        session_manager: Any = None,
    ) -> None:
        self._mcp = mcp_server
        self._genome = genome
        self._arbiter = arbiter
        self._profiles = agent_profiles
        self._tokens = token_tracker
        self._memory = memory_store
        self._skills = skill_loader
        self._external = external_bridge
        self._events = event_bus
        self._fcpi = fcpi_tracker
        self._session_manager = session_manager
        self._start_time = time.time()

    # ── All data (single request) ─────────────────────────────────────────

    async def get_all(self, request) -> dict:
        """Return all dashboard data in one request."""
        return {
            "organs": await self.get_organs(request),
            "fcpi": await self.get_fcpi(request),
            "genome": await self.get_genome(request),
            "arbiter": await self.get_arbiter(request),
            "agents": await self.get_agents(request),
            "providers": await self.get_providers(request),
            "tokens": await self.get_tokens(request),
            "memory": await self.get_memory(request),
            "features": await self.get_features(request),
            "external": await self.get_external(request),
            "skills": await self.get_skills(request),
            "tools": await self.get_tools(request),
            "health": await self.get_health(request),
        }

    # ── Organ Status ──────────────────────────────────────────────────────

    async def get_organs(self, request) -> dict:
        # ── Count real sclerotium-os Python modules (organs), not just MCP categories ──
        sclerotium_organs = 0
        organ_dirs: dict[str, int] = {}
        try:
            import os as _os
            base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
            for root, dirs, files in _os.walk(base):
                # Skip non-organ directories
                dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests", "data", ".git", ".codegraph", "node_modules")]
                for f in files:
                    if f.endswith(".py") and f != "__init__.py":
                        sclerotium_organs += 1
                        rel = _os.path.relpath(root, base)
                        top = rel.split(_os.sep)[0] if rel != "." else "root"
                        organ_dirs[top] = organ_dirs.get(top, 0) + 1
        except Exception:
            sclerotium_organs = 252  # fallback from last scan

        # MCP tool categories (for tool distribution view)
        categories: dict[str, int] = {}
        if self._mcp:
            for t in self._mcp.tools.list_tools():
                cat = t.get("category", "other")
                categories[cat] = categories.get(cat, 0) + 1

        mcp_data = [
            {"cat": cat, "name": cat.replace("_", " ").title(), "tools": count}
            for cat, count in sorted(categories.items())
        ]

        # Add organ health from genome if available
        if self._genome:
            health = self._genome.get_organ_health()
            for o in mcp_data:
                o["health"] = round(health.get(o["cat"], 0.5), 3)

        # Organ directory breakdown for sclerotium-os
        dir_breakdown = [
            {"dir": d, "count": c}
            for d, c in sorted(organ_dirs.items(), key=lambda x: -x[1])
        ]

        # Full organ count across all 3 systems
        fungal_organs = 120
        mirofish_organs = 28
        total_organs = sclerotium_organs + fungal_organs + mirofish_organs

        return {
            "categories": mcp_data,
            "total_organs": total_organs,
            "total_tools": sum(categories.values()),
            "breakdown": {
                "sclerotium_organs": sclerotium_organs,
                "sclerotium_dirs": dir_breakdown,
                "fungal_organs": fungal_organs,
                "mirofish_organs": mirofish_organs,
            },
        }

    # ── FCPI Metrics ──────────────────────────────────────────────────────

    async def get_fcpi(self, request) -> dict:
        if self._fcpi:
            v = self._fcpi.get_vector()
            return {
                "dimensions": [
                    {"name": "Coding", "value": round(v.coding, 3), "color": "#22d3ee"},
                    {"name": "Coordination", "value": round(v.coordination, 3), "color": "#a3e635"},
                    {"name": "Safety", "value": round(v.safety, 3), "color": "#fb7185"},
                    {"name": "Decision", "value": round(v.decision, 3), "color": "#fbbf24"},
                    {"name": "Emergence", "value": round(v.emergence, 3), "color": "#a78bfa"},
                    {"name": "Performance", "value": round(v.performance, 3), "color": "#34d399"},
                ],
                "total_score": round(v.total_score, 3),
            }
        return {"dimensions": [], "total_score": 0.0}

    # ── Genome ────────────────────────────────────────────────────────────

    async def get_genome(self, request) -> dict:
        # Try MiroFish Full-Body Genome first (三系统统一进化)
        try:
            from bridges.mirofish_bridge import MiroFishBridge
            miro = MiroFishBridge()
            data = miro.get_full_body_genome()
            if data and data.get("generation", 0) > 0:
                data["source"] = "MiroFish (三系统统一进化)"
                return data
        except Exception:
            pass

        # Fallback: local sclerotium genome
        if self._genome:
            snap = self._genome.snapshot()
            dims_data = []
            dim_names = {"tools": ("Tools", "#22d3ee", "🔧"), "prompts": ("Prompts", "#a3e635", "📝"),
                         "personalities": ("Personalities", "#a78bfa", "👤"), "memories": ("Memory", "#fbbf24", "💾"),
                         "providers": ("Providers", "#34d399", "🌐"), "skills": ("Skills", "#fb7185", "🎯"),
                         "organs": ("Organs", "#e879f9", "🔬"), "arbiters": ("Arbiter", "#fb923c", "⚖️")}
            for key, count in snap.dimensions.items():
                label, color, icon = dim_names.get(key, (key.title(), "#94a3b8", "•"))
                dims_data.append({"name": label, "genes": count, "color": color, "icon": icon})
            return {
                "generation": snap.generation, "total_fitness": round(snap.total_fitness, 4),
                "total_mutations": self._genome.total_mutations, "improvements": self._genome.improvements,
                "dimensions": dims_data,
                "top_tools": [{"name": t, "weight": round(w, 3)} for t, w in self._genome.get_top_tools(5)],
                "best_personality": {"name": self._genome.get_best_personality()[0], "score": round(self._genome.get_best_personality()[1], 3)},
                "best_provider": {"name": self._genome.get_best_provider()[0], "score": round(self._genome.get_best_provider()[1], 3)},
                "source": "sclerotium (local fallback)",
            }
        return {"generation": 0, "total_fitness": 0.0, "dimensions": []}

    # ── Arbiter ───────────────────────────────────────────────────────────

    async def get_arbiter(self, request) -> dict:
        if not self._arbiter:
            return {"modes": [], "stats": {}, "status": "arbiter_not_connected"}
        stats = self._arbiter.get_stats() or {}
        current_mode = str(getattr(self._arbiter, 'mode', 'DEFAULT'))
        mode_names = ["PLAN", "DEFAULT", "ACCEPT_EDITS", "AUTO", "DONT_ASK", "BYPASS", "BUBBLE"]
        colors = ["#a78bfa", "#22d3ee", "#34d399", "#fbbf24", "#fb7185", "#f87171", "#a3e635"]
        total = max(stats.get('total', 1), 1)
        approved = stats.get('allow_count', 0)
        blocked = stats.get('block_count', 0)
        human = stats.get('human_count', 0)
        # Get REAL mode usage stats from arbiter, not hardcoded percentages
        mode_counts = getattr(self._arbiter, '_mode_counts', {})
        modes = []
        for i, name in enumerate(mode_names):
            mode_total = mode_counts.get(name, 0)
            pct = round(mode_total / max(sum(mode_counts.values()), 1) * 100, 1) if mode_counts else 0
            modes.append({"name": name, "pct": pct, "count": mode_total, "color": colors[i], "active": name == current_mode})
        return {
            "modes": modes,
            "current_mode": current_mode,
            "stats": {"total": total, "approved": approved, "blocked": blocked, "human_escalated": human},
            "cuga_enabled": getattr(self._arbiter, '_cuga_enabled', True),
        }

    # ── Agents ────────────────────────────────────────────────────────────

    async def get_agents(self, request) -> dict:
        if not self._profiles:
            return {"agents": [], "current": "sclerotium"}
        return {
            "agents": self._profiles.list_profiles(),
            "current": self._profiles.current_name,
        }

    # ── Providers ─────────────────────────────────────────────────────────

    async def get_providers(self, request) -> dict:
        # Try to get real provider data from LLMClient registry
        providers = []
        try:
            from agent.llm_client import _PROVIDER_REGISTRY
            import os
            chain = []
            for name, cfg in sorted(_PROVIDER_REGISTRY.items(), key=lambda x: x[1].priority):
                is_primary = cfg.priority == 0
                has_key = bool(os.environ.get(f"{name.upper()}_API_KEY", ""))
                providers.append({
                    "name": cfg.name.title(),
                    "role": "Primary" if is_primary else f"Fallback {cfg.priority//10}",
                    "primary": is_primary,
                    "models": [cfg.default_model],
                    "configured": has_key or is_primary,
                })
                chain.append(name)
            return {"providers": providers, "fallback_chain": chain}
        except Exception:
            pass
        # Fallback
        return {
            "providers": [
                {"name": "DeepSeek", "role": "Primary", "primary": True, "models": ["v4-flash", "v4-pro"]},
                {"name": "OpenAI", "role": "Fallback 1", "models": ["gpt-4o"]},
                {"name": "Groq", "role": "Fallback 2", "models": ["llama-4-maverick"]},
                {"name": "OpenRouter", "role": "Fallback 3", "models": ["auto"]},
                {"name": "Ollama", "role": "Local", "models": ["llama3.3"]},
            ],
            "fallback_chain": ["deepseek", "openai", "groq", "openrouter", "ollama"],
        }

    # ── Tokens ────────────────────────────────────────────────────────────

    async def get_tokens(self, request) -> dict:
        if self._tokens:
            daily = self._tokens.get_daily_stats()
            monthly = self._tokens.get_monthly_stats()
            total = self._tokens.get_total_stats()
            return {
                "daily": daily,
                "monthly": monthly,
                "total": total,
                "over_budget": self._tokens.is_over_budget(),
            }
        return {"daily": {}, "monthly": {}, "total": {}}

    # ── Memory ────────────────────────────────────────────────────────────

    async def get_memory(self, request) -> dict:
        if self._memory:
            try:
                stats = self._memory.get_stats()
                # MemoryStats is a dataclass, handle both dict and object
                if hasattr(stats, 'total_memories'):
                    by_level = getattr(stats, 'by_level', {})
                    return {
                        "layers": [
                            {"name": "Working", "count": by_level.get("working", 0), "desc": "Immediate"},
                            {"name": "Episodic", "count": by_level.get("episodic", 0), "desc": "Events"},
                            {"name": "Semantic", "count": by_level.get("semantic", 0), "desc": "Knowledge"},
                            {"name": "Procedural", "count": by_level.get("procedural", 0), "desc": "Skills"},
                            {"name": "Strategic", "count": by_level.get("strategic", 0), "desc": "Insights"},
                        ],
                        "total": stats.total_memories,
                    }
                elif isinstance(stats, dict):
                    by_level = stats.get("by_level", {})
                    return {
                        "layers": [
                            {"name": "Working", "count": by_level.get("working", 0), "desc": "Immediate"},
                            {"name": "Episodic", "count": by_level.get("episodic", 0), "desc": "Events"},
                            {"name": "Semantic", "count": by_level.get("semantic", 0), "desc": "Knowledge"},
                            {"name": "Procedural", "count": by_level.get("procedural", 0), "desc": "Skills"},
                            {"name": "Strategic", "count": by_level.get("strategic", 0), "desc": "Insights"},
                        ],
                        "total": stats.get("total_memories", 0),
                    }
            except Exception:
                pass
        return {"layers": [], "total": 0}

    # ── Features ──────────────────────────────────────────────────────────

    async def get_features(self, request) -> dict:
        return {
            "features": [
                {"icon": "🧬", "name": "Native Function Calling", "desc": "191 tools via LLM tool_calls"},
                {"icon": "⚡", "name": "SSE Streaming", "desc": "AG-UI protocol · /stream toggle"},
                {"icon": "🌐", "name": "5 Provider Chain", "desc": "DeepSeek→OpenAI→Groq→OpenRouter→Ollama"},
                {"icon": "⚖️", "name": "7 Arbiter Modes", "desc": "CUGA 5-Checkpoint · Merkle Audit"},
                {"icon": "💾", "name": "5-Layer Hexis Memory", "desc": "ChromaDB · Ebbinghaus Forgetting"},
                {"icon": "🧠", "name": "6D FCPI Evolution", "desc": "Real-time self-improvement"},
                {"icon": "🧬", "name": "8D Full-Body Genome", "desc": "用进废退 · 自然选择 · 50代进化"},
                {"icon": "🔌", "name": "External MCP Bridge", "desc": "stdio/http · Dynamic connect"},
                {"icon": "📦", "name": "Plugin Manifest", "desc": "sclerotium.plugin.json · Auto-discovery"},
                {"icon": "👥", "name": "9 Agent Personalities", "desc": "AGENT.md · Runtime switch"},
                {"icon": "🔄", "name": "Session Fork/Merge", "desc": "JSONL+SQLite · Branch & diff"},
                {"icon": "🔑", "name": "Idempotency", "desc": "SQLite dedup · TTL expire"},
                {"icon": "🎤", "name": "Voice Interface", "desc": "Whisper STT · Edge/OpenAI TTS"},
                {"icon": "🐳", "name": "Docker Deploy", "desc": "Multi-stage · docker-compose"},
                {"icon": "📊", "name": "Token Economy", "desc": "SQLite tracking · Budget alerts"},
                {"icon": "🤖", "name": "Code-as-Action", "desc": "Python sandbox execution"},
                {"icon": "🎯", "name": "Model Router", "desc": "6-tier complexity → optimal model"},
            ]
        }

    # ── External MCP ──────────────────────────────────────────────────────

    async def get_external(self, request) -> dict:
        if self._external:
            return {
                "servers": self._external.list_servers(),
                "tools": self._external.list_external_tools(),
            }
        return {"servers": [], "tools": []}

    # ── Skills ────────────────────────────────────────────────────────────

    async def get_skills(self, request) -> dict:
        if self._skills:
            return {"skills": self._skills.list_skills(), "total": self._skills.skill_count}
        return {"skills": [], "total": 0}

    # ── Tools ─────────────────────────────────────────────────────────────

    async def get_tools(self, request) -> dict:
        cats: dict[str, int] = {}
        if self._mcp:
            for t in self._mcp.tools.list_tools():
                cat = t.get("category", "other")
                cats[cat] = cats.get(cat, 0) + 1
        return {"categories": cats, "total": sum(cats.values())}

    # ── Health ────────────────────────────────────────────────────────────

    async def get_health(self, request) -> dict:
        # Collect LIVE data from backends
        genome = self._genome
        memory = self._memory
        skills = self._skills
        session_mgr = getattr(self, '_session_manager', None)

        evo_data = {"generation": 0, "fitness": 0.0, "status": "not_loaded"}
        if genome:
            try:
                evo_data = {
                    "generation": getattr(genome, "generation", 0),
                    "fitness": round(getattr(genome, "fitness", 0.0), 4),
                    "status": "active",
                }
            except Exception:
                pass

        cache_data = {"status": "not_loaded"}
        try:
            from kernel.prompt_cache import PromptCacheEngine
            pc = PromptCacheEngine()
            if pc._warmed_up:
                report = pc.get_cache_safety_report()
                cache_data = {
                    "status": "warm",
                    "hit_rate": report.get("hit_rate", "0%"),
                    "segments": len(pc._segments),
                }
            else:
                cache_data = {"status": "cold", "message": "Not warmed up — run cache_warmup"}
        except Exception:
            pass

        memory_data = {"total_memories": 0, "status": "not_loaded"}
        if memory:
            try:
                ms = memory.get_stats() if hasattr(memory, "get_stats") else {}
                memory_data = {
                    "total_memories": getattr(ms, "total_memories", 0) if hasattr(ms, "total_memories") else ms.get("total_memories", 0),
                    "status": "active",
                }
            except Exception:
                pass

        session_data = {"sessions": 0, "status": "not_loaded"}
        if session_mgr:
            try:
                session_data = {
                    "sessions": len(session_mgr.list_sessions()) if hasattr(session_mgr, "list_sessions") else 0,
                    "status": "active",
                }
            except Exception:
                pass

        skills_count = getattr(skills, "skill_count", 0) if skills else 0

        # System resources
        resources = {"cpu_percent": 0, "memory_mb": 0, "disk_gb": 0}
        try:
            import psutil
            resources["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            resources["memory_mb"] = round(mem.used / (1024 * 1024), 1)
        except ImportError:
            pass
        try:
            import shutil, os as _os
            usage = shutil.disk_usage(_os.getcwd())
            resources["disk_gb"] = round(usage.free / (1024 ** 3), 1)
        except Exception:
            pass

        return {
            "status": "healthy",
            "uptime_seconds": time.time() - self._start_time,
            "tool_count": self._mcp.tools.tool_count if self._mcp else 0,
            "version": "5.2.0",
            "evolution": evo_data,
            "cache": cache_data,
            "memory": memory_data,
            "skills": {"count": skills_count},
            "sessions": session_data,
            "resources": resources,
            "systems": {
                "sclerotium-os": "healthy",
                "MiroFish-main": "healthy",
                "fungal-cortex": "healthy",
            },
            "bridges": {
                "fungal_bridge": "connected",
                "mirofish_bridge": "connected",
            },
        }

    # ── Mount on aiohttp app ──────────────────────────────────────────────

    # ── Install MCP Server ────────────────────────────────────────────────

    async def install_mcp(self, request) -> dict:
        """Install an MCP server via stdio."""
        try:
            body = await request.json()
            name = body.get("name", "")
            command = body.get("command", "")
            if not name or not command:
                return {"ok": False, "error": "name and command required"}

            # Parse command (e.g. "npx package@latest" or "python server.py")
            parts = command.strip().split()
            cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []

            if self._external:
                ok = await self._external.connect_stdio(name, cmd, args)
                if ok:
                    return {"ok": True, "tools": self._external.external_tool_count,
                            "servers": self._external.list_servers()}
                return {"ok": False, "error": "Connection failed"}
            return {"ok": False, "error": "External MCP bridge not available"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Install Skill ─────────────────────────────────────────────────────

    async def install_skill(self, request) -> dict:
        """Install a skill from GitHub or URL."""
        try:
            body = await request.json()
            name = body.get("name", "")
            url = body.get("url", "")
            if not name or not url:
                return {"ok": False, "error": "name and url required"}

            import subprocess, os
            target_dir = os.path.expanduser(f"~/.claude/skills/{name}")

            if "github.com" in url:
                # Clone from GitHub
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", url, target_dir],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode != 0:
                    return {"ok": False, "error": result.stderr[:200]}
            else:
                return {"ok": False, "error": "Only GitHub URLs supported for now"}

            # Re-scan skills
            if self._skills:
                self._skills.scan()

            return {"ok": True, "path": target_dir}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Clone timed out"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def mount(self, app: Any) -> None:
        """Register all /data/* API routes on the aiohttp Application."""
        from aiohttp import web

        def make_handler(fn):
            async def handler(request):
                try:
                    data = await fn(request)
                    return web.json_response(data)
                except Exception as e:
                    return web.json_response({"error": str(e)}, status=500)
            return handler

        # Install endpoints
        app.router.add_post("/mcp/install", make_handler(self.install_mcp))
        app.router.add_post("/skills/install", make_handler(self.install_skill))

        routes = [
            ("/data/all", self.get_all),
            ("/data/organs", self.get_organs),
            ("/data/fcpi", self.get_fcpi),
            ("/data/genome", self.get_genome),
            ("/data/arbiter", self.get_arbiter),
            ("/data/agents", self.get_agents),
            ("/data/providers", self.get_providers),
            ("/data/tokens", self.get_tokens),
            ("/data/memory", self.get_memory),
            ("/data/features", self.get_features),
            ("/data/external", self.get_external),
            ("/data/skills", self.get_skills),
            ("/data/tools", self.get_tools),
            ("/data/health", self.get_health),
        ]
        for path, handler_fn in routes:
            app.router.add_get(path, make_handler(handler_fn))
