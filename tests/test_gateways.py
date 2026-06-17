"""Tests for Phase 3 gateways — models, MCP market, skills market."""

import pytest
from mcp.server import SclerotiumMCPServer


@pytest.fixture
def tools():
    server = SclerotiumMCPServer()
    server.register_all_tools()
    return server.tools


class TestModelGateway:
    def test_model_tools_registered(self, tools):
        for n in ["model_list_providers", "model_list_models", "model_chat", "model_test"]:
            assert tools.get_handler(n) is not None

    @pytest.mark.asyncio
    async def test_list_providers(self, tools):
        result = await tools.get_handler("model_list_providers")()
        assert len(result) >= 15  # 20+ providers

    @pytest.mark.asyncio
    async def test_list_models(self, tools):
        result = await tools.get_handler("model_list_models")(provider="all")
        assert len(result) >= 30

    @pytest.mark.asyncio
    async def test_list_models_filtered(self, tools):
        result = await tools.get_handler("model_list_models")(provider="deepseek")
        assert all(m["provider"] == "deepseek" for m in result)

    @pytest.mark.asyncio
    async def test_test_connection(self, tools):
        result = await tools.get_handler("model_test")(provider_id="unknown")
        assert result["status"] == "error"


class TestMCPMarket:
    def test_mcp_tools_registered(self, tools):
        for n in ["mcp_search", "mcp_categories", "mcp_trending", "mcp_popular", "mcp_registries", "mcp_stats"]:
            assert tools.get_handler(n) is not None

    @pytest.mark.asyncio
    async def test_search(self, tools):
        result = await tools.get_handler("mcp_search")(query="postgres")
        assert len(result) >= 1
        assert any("postgres" in r["name"] for r in result)

    @pytest.mark.asyncio
    async def test_search_by_category(self, tools):
        result = await tools.get_handler("mcp_search")(query="", category="database")
        assert all(r["category"] == "database" for r in result)

    @pytest.mark.asyncio
    async def test_categories(self, tools):
        cats = await tools.get_handler("mcp_categories")()
        assert len(cats) >= 10
        assert "database" in cats

    @pytest.mark.asyncio
    async def test_trending(self, tools):
        result = await tools.get_handler("mcp_trending")(top_n=5)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_popular(self, tools):
        result = await tools.get_handler("mcp_popular")(top_n=5)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_registries(self, tools):
        result = await tools.get_handler("mcp_registries")()
        assert len(result) >= 5

    @pytest.mark.asyncio
    async def test_stats(self, tools):
        stats = await tools.get_handler("mcp_stats")()
        assert stats["total_registries"] >= 5


class TestSkillsMarket:
    def test_skills_tools_registered(self, tools):
        for n in ["skills_search", "skills_categories", "skills_trending",
                   "skills_popular", "skills_registries", "skills_stats", "skills_detail"]:
            assert tools.get_handler(n) is not None

    @pytest.mark.asyncio
    async def test_search(self, tools):
        result = await tools.get_handler("skills_search")(query="code review")
        assert len(result) >= 1
        assert any("review" in r["name"] for r in result)

    @pytest.mark.asyncio
    async def test_search_by_category(self, tools):
        result = await tools.get_handler("skills_search")(query="", category="security")
        assert all(r["category"] == "security" for r in result)

    @pytest.mark.asyncio
    async def test_categories(self, tools):
        cats = await tools.get_handler("skills_categories")()
        assert len(cats) >= 15
        assert "coding" in cats

    @pytest.mark.asyncio
    async def test_trending(self, tools):
        result = await tools.get_handler("skills_trending")(top_n=5)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_popular(self, tools):
        result = await tools.get_handler("skills_popular")(top_n=5)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_registries(self, tools):
        result = await tools.get_handler("skills_registries")()
        assert len(result) >= 5

    @pytest.mark.asyncio
    async def test_stats(self, tools):
        stats = await tools.get_handler("skills_stats")()
        assert stats["total_skills_listed"] > 1_000_000

    @pytest.mark.asyncio
    async def test_detail_found(self, tools):
        result = await tools.get_handler("skills_detail")(name="code-reviewer")
        assert result is not None
        assert result["name"] == "code-reviewer"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, tools):
        result = await tools.get_handler("skills_detail")(name="nonexistent_skill_xyz")
        assert result is None


def test_total_tool_count(tools):
    assert tools.tool_count >= 62  # 45 + 17 new gateway tools


def test_gateway_modules_importable():
    from gateways.models import UniversalModelGateway
    from gateways.mcp_market import MCPMarketGateway
    from gateways.skills_market import SkillsMarketGateway

    assert UniversalModelGateway().list_providers()
    assert len(MCPMarketGateway().list_registries()) >= 5
    assert len(SkillsMarketGateway().list_registries()) >= 5
