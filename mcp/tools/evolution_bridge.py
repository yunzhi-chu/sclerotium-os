"""MCP Evolution Bridge Tool — MiroFish↔Sclerotium evolution cycle."""
from mcp.server import ToolRegistry

async def _evolution_extract_modules() -> dict:
    from kernel.evolution_bridge import EvolutionBridge
    bridge = EvolutionBridge(".")
    return bridge.extract_modules()

async def _evolution_full_cycle() -> dict:
    from kernel.evolution_bridge import EvolutionBridge
    bridge = EvolutionBridge(".")
    return bridge.run_evolution_cycle()

async def _evolution_status() -> dict:
    from kernel.evolution_bridge import EvolutionBridge
    return EvolutionBridge(".").get_status()

def register_evolution_bridge_tools(registry: ToolRegistry) -> None:
    tools = [
        ("evolution_extract_modules", "Extract Sclerotium OS source modules as genome_context for MiroFish arenas.", _evolution_extract_modules),
        ("evolution_full_cycle", "Run one complete MiroFish→Sclerotium self-evolution cycle.", _evolution_full_cycle),
        ("evolution_bridge_status", "Get evolution bridge status (snapshots, actions, cycles).", _evolution_status),
    ]
    for name, desc, handler in tools:
        registry.register(name=name, description=desc, parameters={"type":"object","properties":{},"required":[]}, handler=handler, category="evolution")
