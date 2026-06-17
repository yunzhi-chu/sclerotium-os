"""MCP Gateway Tools — model providers, MCP market, skills market."""

from __future__ import annotations

from typing import Any

from mcp.server import ToolRegistry
from gateways.models import UniversalModelGateway
from gateways.mcp_market import MCPMarketGateway
from gateways.skills_market import SkillsMarketGateway

_models = UniversalModelGateway()
_mcp = MCPMarketGateway()
_skills = SkillsMarketGateway()

# ── Model tools ──────────────────────────────────────────────────────

async def _model_list_providers() -> list[dict]:
    return _models.list_providers()

async def _model_list_models(provider: str = "all") -> list[dict]:
    return _models.list_models(provider)

async def _model_chat(prompt: str, model: str = "", provider: str = "", strategy: str = "cheapest") -> dict:
    from gateways.models import RoutingStrategy
    s = {"cheapest": RoutingStrategy.CHEAPEST, "fastest": RoutingStrategy.FASTEST,
         "best": RoutingStrategy.BEST, "fallback": RoutingStrategy.FALLBACK}.get(strategy)
    return await _models.chat(prompt, model or None, provider or None, s)

async def _model_test(provider_id: str) -> dict:
    return _models.test_connection(provider_id)

# ── MCP Market tools ─────────────────────────────────────────────────

async def _mcp_search(query: str, category: str = "all") -> list[dict]:
    return _mcp.search(query, category)

async def _mcp_categories() -> list[str]:
    return _mcp.list_categories()

async def _mcp_trending(top_n: int = 10) -> list[dict]:
    return _mcp.get_trending(top_n)

async def _mcp_popular(top_n: int = 10) -> list[dict]:
    return _mcp.get_popular(top_n)

async def _mcp_registries() -> list[dict]:
    return _mcp.list_registries()

async def _mcp_stats() -> dict:
    return _mcp.stats()

# ── Skills Market tools ──────────────────────────────────────────────

async def _skills_search(query: str, category: str = "all") -> list[dict]:
    return _skills.search(query, category)

async def _skills_categories() -> list[str]:
    return _skills.list_categories()

async def _skills_trending(top_n: int = 10) -> list[dict]:
    return _skills.get_trending(top_n)

async def _skills_popular(top_n: int = 10) -> list[dict]:
    return _skills.get_popular(top_n)

async def _skills_registries() -> list[dict]:
    return _skills.list_registries()

async def _skills_stats() -> dict:
    return _skills.stats()

async def _skills_detail(name: str) -> dict | None:
    return _skills.get_skill_detail(name)


# ── LOCAL MCP stats (not remote market) ────────────────────────────────

async def _mcp_local() -> dict:
    """List locally registered MCP tools (not remote market)."""
    from mcp.server import SclerotiumMCPServer
    try:
        s = SclerotiumMCPServer()
        s.register_all_tools()
        tools = s.tools.list_tools()
        cats = {}
        for t in tools:
            c = t.get("category", "other")
            cats[c] = cats.get(c, 0) + 1
        return {
            "total": len(tools),
            "categories": dict(sorted(cats.items(), key=lambda x: -x[1])),
            "tools": [{"name": t["name"], "category": t["category"], "description": t["description"][:120]}
                      for t in sorted(tools, key=lambda t: (t["category"], t["name"]))],
        }
    except Exception as e:
        return {"total": 0, "error": str(e)}


def register_gateway_tools(registry: ToolRegistry) -> None:
    # Models (4)
    for name, desc, params, handler in [
        ("model_list_providers", "List all 20+ model providers (OpenAI, Anthropic, DeepSeek, Groq, Ollama...) with model counts and free tiers.", {"type": "object", "properties": {}, "required": []}, _model_list_providers),
        ("model_list_models", "List models from all providers or filter by one.", {"type": "object", "properties": {"provider": {"type": "string", "default": "all"}}, "required": []}, _model_list_models),
        ("model_chat", "Send a chat completion via the optimal route (cheapest/fastest/best/fallback).", {"type": "object", "properties": {"prompt": {"type": "string"}, "model": {"type": "string", "default": ""}, "provider": {"type": "string", "default": ""}, "strategy": {"type": "string", "default": "cheapest"}}, "required": ["prompt"]}, _model_chat),
        ("model_test", "Test connectivity to a specific model provider.", {"type": "object", "properties": {"provider_id": {"type": "string"}}, "required": ["provider_id"]}, _model_test),
    ]:
        registry.register(name=name, description=desc, parameters=params, handler=handler, category="models")

    # MCP Market (6+1) — REMOTE registries + LOCAL tools
    for name, desc, params, handler in [
        ("mcp_search", "[REMOTE MARKET] Search external MCP registries (SafeMCP/Glama/MCP.so). For LOCAL tools, use mcp_local.", {"type": "object", "properties": {"query": {"type": "string"}, "category": {"type": "string", "default": "all"}}, "required": ["query"]}, _mcp_search),
        ("mcp_categories", "[REMOTE MARKET] List MCP categories from external registries.", {"type": "object", "properties": {}, "required": []}, _mcp_categories),
        ("mcp_trending", "[REMOTE MARKET] Trending MCP servers from external registries.", {"type": "object", "properties": {"top_n": {"type": "integer", "default": 10}}, "required": []}, _mcp_trending),
        ("mcp_popular", "[REMOTE MARKET] Most-installed MCP servers from external registries.", {"type": "object", "properties": {"top_n": {"type": "integer", "default": 10}}, "required": []}, _mcp_popular),
        ("mcp_registries", "[REMOTE MARKET] List external MCP registries.", {"type": "object", "properties": {}, "required": []}, _mcp_registries),
        ("mcp_stats", "[REMOTE MARKET] External MCP ecosystem stats.", {"type": "object", "properties": {}, "required": []}, _mcp_stats),
        ("mcp_local", "[LOCAL] List ALL 202 locally registered MCP tools with categories. USE THIS FIRST.", {"type": "object", "properties": {}, "required": []}, _mcp_local),
    ]:
        registry.register(name=name, description=desc, parameters=params, handler=handler, category="mcp_market")

    # Skills Market (7) — REMOTE registries. For LOCAL skills, use skill_list.
    for name, desc, params, handler in [
        ("skills_search", "[REMOTE MARKET] Search external skill registries. LOCAL skills (5,826): use skill_list.", {"type": "object", "properties": {"query": {"type": "string"}, "category": {"type": "string", "default": "all"}}, "required": ["query"]}, _skills_search),
        ("skills_categories", "[REMOTE MARKET] External registry categories.", {"type": "object", "properties": {}, "required": []}, _skills_categories),
        ("skills_trending", "[REMOTE MARKET] Trending skills from external registries.", {"type": "object", "properties": {"top_n": {"type": "integer", "default": 10}}, "required": []}, _skills_trending),
        ("skills_popular", "[REMOTE MARKET] Most-installed skills from external registries.", {"type": "object", "properties": {"top_n": {"type": "integer", "default": 10}}, "required": []}, _skills_popular),
        ("skills_registries", "[REMOTE MARKET] External skills registries.", {"type": "object", "properties": {}, "required": []}, _skills_registries),
        ("skills_stats", "[REMOTE MARKET] External skills ecosystem stats.", {"type": "object", "properties": {}, "required": []}, _skills_stats),
        ("skills_detail", "[REMOTE MARKET] External skill details.", {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, _skills_detail),
    ]:
        registry.register(name=name, description=desc, parameters=params, handler=handler, category="skills_market")
