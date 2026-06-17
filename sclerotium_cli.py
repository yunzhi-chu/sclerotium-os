"""Sclerotium OS CLI — 一条命令启动。

    sclerotium                  # Web 仪表盘模式 (localhost:18789)
    sclerotium --wechat         # 微信模式 + 完整生命系统 (All organs)
    sclerotium --console        # 终端对话模式
    sclerotium --full           # 终端 + Web 并行
"""

import asyncio
import sys
import os


def main():
    """Entry point for 'sclerotium' command."""
    args = sys.argv[1:]
    mode = "dash"

    if "--console" in args or "-c" in args:
        mode = "console"
    elif "--wechat" in args or "-w" in args:
        mode = "wechat"
    elif "--full" in args or "-f" in args:
        mode = "full"
    elif "--help" in args or "-h" in args:
        print(__doc__)
        return

    if mode == "dash":
        asyncio.run(run_full_system(with_wechat=False))
    elif mode == "console":
        from sclerotium import run_console
        run_console()
    elif mode == "wechat":
        asyncio.run(run_full_system(with_wechat=True))
    elif mode == "full":
        asyncio.run(run_full())


async def run_full_system(with_wechat: bool = False):
    """Start the COMPLETE Sclerotium OS lifeform. P1-2 refactor: split into helpers."""
    mode_name = "WeChat" if with_wechat else "Dashboard"
    print(f"Starting Sclerotium OS {'+ WeChat' if with_wechat else ''}...")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from mcp.server import SclerotiumMCPServer
    from mcp.external_bridge import ExternalMCPBridge
    server = SclerotiumMCPServer()
    server.register_all_tools()
    print(f"  [{mode_name}] {server.tools.tool_count} MCP tools registered")

    # ── Integration Layer: wire all 16 subsystems into a living organism ──
    genome, memory, skills, ext_bridge = _init_backends(server, mode_name)
    try:
        from kernel.integration_layer import activate_full_integration
        integration_report = activate_full_integration()
        hooks_count = integration_report.get("hooks_registered", 0)
        swarm_status = integration_report.get("swarm", "?")
        cache_status = integration_report.get("cache", "?")
        print(f"  [{mode_name}] Integration: {hooks_count} hooks | swarm={swarm_status} | cache={cache_status}")
    except Exception as e:
        print(f"  [{mode_name}] Integration: skipped ({e})")
    wechat_bot = await _init_wechat(mode_name, with_wechat)

    print(f"  [{mode_name}] Dashboard: http://localhost:18789")
    print(f"  [{mode_name}] Health:    http://localhost:18789/data/health")
    print(f"  [{mode_name}] API:       http://localhost:18789/data/all")
    if wechat_bot:
        print(f"  [{mode_name}] WeChat:    微信已连接，发消息试试")
    print()
    await server.run_http(port=18789)


def _init_backends(server, mode_name: str):
    """Wire all live backends: genome, arbiter, memory, skills, profiles, sessions. P1-2 helper."""
    genome = memory = skills = None
    ext_bridge = None
    try:
        from kernel.constitutional_arbiter import ConstitutionalArbiter
        from kernel.hexis_memory import HexisMemoryStore
        from kernel.skill_loader import SkillLoader
        from evolution.full_body_genome import FullBodyGenome
        from kernel.agent_profiles import AgentProfileManager
        from agent.session import SessionManager
        from mcp.external_bridge import ExternalMCPBridge

        genome = FullBodyGenome("./data/genome.json")
        genome.load_checkpoint()
        arbiter = ConstitutionalArbiter()

        try:
            from mcp.tools.evolution import set_local_genome
            set_local_genome(genome)
        except Exception:
            pass

        memory = HexisMemoryStore(chroma_path="./data/brain_chroma", sqlite_path="./data/brain.db")
        skills = SkillLoader(); skills.scan()
        profiles = AgentProfileManager(); profiles.scan_profiles()
        session_mgr = SessionManager("./data/sessions")

        ext_bridge = ExternalMCPBridge(server.tools)
        server.wire_live_backends(
            genome=genome, arbiter=arbiter, agent_profiles=profiles,
            memory_store=memory, skill_loader=skills, external_bridge=ext_bridge,
            session_manager=session_mgr,
        )
        wired = len([v for v in server._live_backends.values() if v])
        print(f"  [{mode_name}] {wired} live backends wired (genome/gen{genome.generation}/skills{skills.skill_count}/memory/profiles/sessions)")

        _bootstrap_memory(memory, skills, server, mode_name)
        _bootstrap_cache(skills, server, genome, mode_name)
        _bootstrap_evolution(genome, mode_name)
    except Exception as e:
        print(f"  [{mode_name}] Backends limited: {e}")

    _connect_external_bridges(ext_bridge, mode_name)
    return genome, memory, skills, ext_bridge


def _bootstrap_memory(memory, skills, server, mode_name: str) -> None:
    """Initialize memory store and seed bootstrap entry. P1-2 helper."""
    try:
        memory.start()
        memory.store(
            content=f"Sclerotium OS v5.2 booted at {__import__('datetime').datetime.now().isoformat()}. "
                     f"{skills.skill_count} skills, {server.tools.tool_count} tools.",
            level="episodic", importance=0.8, source="system",
        )
        print(f"  [{mode_name}] Memory: bootstrapped ({memory.get_stats().total_memories} entries)")
    except Exception as e:
        print(f"  [{mode_name}] Memory bootstrap: {e}")


def _bootstrap_cache(skills, server, genome, mode_name: str) -> None:
    """Warm up prompt cache engine. P1-2 helper."""
    try:
        from kernel.prompt_cache import PromptCacheEngine, CacheZone
        pc = PromptCacheEngine()
        pc.add_segment("system_prompt",
            f"Sclerotium OS v5.2 — {skills.skill_count} skills, {server.tools.tool_count} tools, genome gen {genome.generation}",
            CacheZone.STATIC)
        pc.add_segment("tools_def", "[]", CacheZone.SEMI_STATIC)
        pc.assemble("deepseek")
        print(f"  [{mode_name}] Cache: warmed up ({len(pc._segments)} segments)")
    except Exception as e:
        print(f"  [{mode_name}] Cache warmup: {e}")


def _bootstrap_evolution(genome, mode_name: str) -> None:
    """Start evolution engine with background loop. P1-2 helper."""
    try:
        from evolution.evolution_loop import EvolutionLoop
        evo = EvolutionLoop(genome=genome, mode="auto")
        try:
            result = evo.evolve_generation()
            print(f"  [{mode_name}] Evolution: bootstrapped gen {result.generation} (fitness={result.new_fitness:.3f})")
        except Exception:
            pass

        async def _evolution_loop():
            while True:
                await asyncio.sleep(300)
                try:
                    result = evo.evolve_generation()
                    if result.improved:
                        print(f"  [Evo] Gen {result.generation}: {result.old_fitness:.3f}→{result.new_fitness:.3f}")
                except Exception:
                    pass
        asyncio.create_task(_evolution_loop())
    except Exception as e:
        print(f"  [{mode_name}] Evolution engine: {e}")


def _connect_external_bridges(ext_bridge, mode_name: str) -> None:
    """Connect external MCP bridges (Playwright, WinApp). P1-2 helper."""
    if ext_bridge is None:
        return
    import platform, asyncio as _asyncio
    npx_cmd = "cmd" if platform.system() == "Windows" else "npx"
    npx_args = ["/c", "npx", "-y"] if platform.system() == "Windows" else ["-y"]
    for name, pkg in [("Playwright", "@playwright/mcp"), ("WinApp", "winapp-mcp")]:
        try:
            ok = _asyncio.get_event_loop().run_until_complete(
                ext_bridge.connect_stdio(name.lower(), npx_cmd, npx_args + [pkg])
            )
            if ok:
                print(f"  [{mode_name}] {name} MCP: loaded")
        except Exception as e:
            print(f"  [{mode_name}] {name} MCP: not available ({e})")


async def _init_wechat(mode_name: str, with_wechat: bool) -> bool | None:
    """Initialize WeChat iLink bot. P1-2 helper."""
    if not with_wechat:
        return None
    try:
        from platforms.wechat_ilink import get_qr_code, wait_for_login, start_listening, try_auto_login
        if try_auto_login():
            start_listening(server_url="http://localhost:18789")
            print(f"  [{mode_name}] WeChat: auto-login OK, listening")
            return True
        print(f"\n  [{mode_name}] 首次使用或登录已过期，请扫码:")
        qr = get_qr_code()
        result = wait_for_login(timeout=120)
        if result.get("success"):
            start_listening(server_url="http://localhost:18789")
            print(f"  [{mode_name}] WeChat: logged in + listening")
            return True
        print(f"  [{mode_name}] WeChat: login skipped ({result.get('error', 'timeout')})")
    except Exception as e:
        print(f"  [{mode_name}] WeChat: {e}")
    return None


async def run_full():
    """Start console + web dashboard in parallel."""
    import asyncio
    from sclerotium import run_console

    async def console_wrapper():
        await asyncio.get_event_loop().run_in_executor(None, run_console)

    await asyncio.gather(run_full_system(with_wechat=False), console_wrapper())


if __name__ == "__main__":
    main()
