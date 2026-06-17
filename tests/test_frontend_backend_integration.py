"""Frontend-Backend Integration Audit."""
import asyncio, json, sys
sys.path.insert(0, ".")

async def main():
    from mcp.server import SclerotiumMCPServer
    from kernel.constitutional_arbiter import ConstitutionalArbiter
    from kernel.hexis_memory import HexisMemoryStore
    from kernel.skill_loader import SkillLoader
    from mcp.external_bridge import ExternalMCPBridge
    from evolution.fcpi_tracker import FCPITracker
    from evolution.full_body_genome import FullBodyGenome
    from ui.api_bridge import APIBridge
    from ui.dashboard_scifi import SCIFI_DASHBOARD

    server = SclerotiumMCPServer(); server.register_all_tools()
    arbiter = ConstitutionalArbiter()
    memory = HexisMemoryStore(chroma_path="./data/brain_chroma", sqlite_path="./data/brain.db")
    skills = SkillLoader(); skills.scan(max_skills=20)
    ext = ExternalMCPBridge(server.tools)
    fcpi = FCPITracker()
    genome = FullBodyGenome("./data/genome.json")

    async def dh(**kw): return {"status": "ok"}
    server.tools.register(name="ext_demo", description="Demo", parameters={"type":"object","properties":{}}, handler=dh, category="external/demo")

    api = APIBridge(mcp_server=server, arbiter=arbiter, memory_store=memory, skill_loader=skills, external_bridge=ext, fcpi_tracker=fcpi, genome=genome)
    html = SCIFI_DASHBOARD

    print("Frontend-Backend Integration Audit")
    print("=" * 60)

    checks = [
        ("/data/health", "get_health", "html:healthy"),
        ("/data/organs", "get_organs", "organ-grid"),
        ("/data/genome", "get_genome", "genome-dimensions"),
        ("/data/arbiter", "get_arbiter", "arbiter-lanes"),
        ("/data/agents", "get_agents", "agent-cards"),
        ("/data/providers", "get_providers", "provider-chain"),
        ("/data/tokens", "get_tokens", "token-bars"),
        ("/data/memory", "get_memory", "memory-layers"),
        ("/data/features", "get_features", "features-grid"),
        ("/data/external", "get_external", "ext-mcp"),
        ("/data/skills", "get_skills", "html:skills"),
        ("/data/tools", "get_tools", "tool-categories"),
        ("/data/all", "get_all", "html:all"),
    ]

    ok = 0
    for path, fn_name, html_id in checks:
        try:
            data = await getattr(api, fn_name)(None)
            has_data = bool(data) and (isinstance(data, dict) and len(data) > 0)
            in_html = html_id.replace("html:", "") in html
            status = "OK" if has_data and in_html else ("data" if has_data else "html")
            if has_data and in_html: ok += 1
            print(f"  [{status:4s}] {path:<18s} data={len(str(data)):<6d} html={'YES' if in_html else 'NO':3s}")
        except Exception as e:
            print(f"  [ERR] {path:<18s} {str(e)[:60]}")

    # Chat + Marketplace panels
    chat = "Neural Link" in html and "sendMessage" in html and "chat-input" in html
    market = "Marketplace" in html and "installMCP" in html and "installSkill" in html
    live = "fetchLiveData" in html
    genome_panel = "MiroFish Powered" in html
    scifi = "Particle" in html and "GSAP" in html
    print(f"\n  Chat Panel:      {'OK' if chat else 'MISSING'}")
    print(f"  Marketplace:     {'OK' if market else 'MISSING'}")
    print(f"  Live Data Fetch: {'OK' if live else 'MISSING'}")
    print(f"  Genome Panel:    {'OK' if genome_panel else 'MISSING'}")
    print(f"  Sci-Fi Theme:    {'OK' if scifi else 'MISSING'}")

    memory.close()
    print(f"\n{'='*60}")
    print(f"  Integration: {ok}/{len(checks)} endpoints | Chat: {'OK' if chat else 'NO'} | Market: {'OK' if market else 'NO'} | Live: {'OK' if live else 'NO'}")
    total = ok + (1 if chat else 0) + (1 if market else 0) + (1 if live else 0) + (1 if genome_panel else 0) + (1 if scifi else 0)
    print(f"  Overall: {total}/{len(checks)+5} complete")


if __name__ == "__main__":
    asyncio.run(main())
