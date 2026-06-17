"""测试: 自定义模型API + Skills市场 + MCP市场"""

import json
import tempfile
import pytest

from gateways.custom_provider import (
    CustomProviderGateway, CustomProvider, CustomModel,
)
from gateways.market_hub import (
    MarketHub, SkillEntry, MCPEntry, SearchResult,
    TOP_SKILLS, TOP_MCP_SERVERS,
)


# ═══════════════════════════════════════════════════════════════
# CustomProviderGateway
# ═══════════════════════════════════════════════════════════════

class TestCustomProviderGateway:
    @pytest.fixture
    def gateway(self, tmp_path):
        config_dir = str(tmp_path / "config")
        return CustomProviderGateway(config_dir=config_dir)

    def test_known_free_providers_registered(self, gateway):
        """已知的14个免费提供商已预注册。"""
        providers = gateway.list_providers()
        known = ["ollama", "vllm", "openrouter", "groq", "together",
                "deepinfra", "lmstudio", "fireworks", "cerebras"]
        names = [p.name for p in providers]
        for k in known:
            assert k in names

    def test_add_custom_provider(self, gateway):
        """添加自定义提供商。"""
        p = gateway.add("my_llm", "http://192.168.1.100:8080/v1",
                       models=["custom-model-v1"], auto_discover=False)
        assert p.name == "my_llm"
        assert "custom-model-v1" in p.models

    def test_find_model(self, gateway):
        """查找模型 (provider/model 格式)。"""
        gateway.add("test_p", "http://localhost/v1",
                   models=["test-model"], auto_discover=False)
        m = gateway.find_model("test_p/test-model")
        assert m is not None
        assert m.name == "test-model"

    def test_find_by_model_name(self, gateway):
        """按模型名查找。"""
        gateway.add("p1", "http://a/v1", models=["unique-model"], auto_discover=False)
        m = gateway.find_model("unique-model")
        assert m is not None

    def test_list_all_models(self, gateway):
        """列出所有模型。"""
        gateway.add("a", "http://a/v1", models=["ma1", "ma2"], auto_discover=False)
        gateway.add("b", "http://b/v1", models=["mb1"], auto_discover=False)
        models = gateway.list_models()
        assert len(models) == 3

    def test_remove_provider(self, gateway):
        """移除提供商同时清理模型。"""
        gateway.add("temp", "http://t/v1", models=["tm"], auto_discover=False)
        assert gateway.remove("temp")
        assert gateway.find_model("temp/tm") is None

    def test_get_provider(self, gateway):
        gateway.add("test", "http://test/v1", models=["m1"], auto_discover=False)
        p = gateway.get_provider("test")
        assert p is not None
        assert p.base_url == "http://test/v1"

    def test_test_connection_offline(self, gateway):
        """测试连接 (离线/不可达)。"""
        gateway.add("offline", "http://10.255.255.1:99999/v1",
                   models=["m"], auto_discover=False)
        result = gateway.test_connection("offline")
        assert isinstance(result, dict)
        assert "ok" in result

    def test_stats(self, gateway):
        gateway.add("a", "http://a/v1", models=["m1"], auto_discover=False)
        stats = gateway.get_stats()
        assert stats["providers"] >= 1

    def test_config_persistence(self, tmp_path):
        """配置持久化 → 重开恢复。"""
        config_dir = str(tmp_path / "config")
        g1 = CustomProviderGateway(config_dir=config_dir)
        g1.add("persistent", "http://p/v1", models=["pm1"], auto_discover=False)

        g2 = CustomProviderGateway(config_dir=config_dir)
        p = g2.get_provider("persistent")
        assert p is not None
        m = g2.find_model("persistent/pm1")
        assert m is not None

    def test_custom_model_frozen(self):
        m = CustomModel(name="test", provider="p", context_window=8192)
        with pytest.raises(Exception):
            m.name = "changed"  # type: ignore

    def test_custom_provider_frozen(self):
        p = CustomProvider(name="test", base_url="http://x/v1")
        with pytest.raises(Exception):
            p.name = "changed"  # type: ignore


# ═══════════════════════════════════════════════════════════════
# MarketHub — Skills
# ═══════════════════════════════════════════════════════════════

class TestMarketHubSkills:
    @pytest.fixture
    def hub(self, tmp_path):
        return MarketHub(install_dir=str(tmp_path / "skills"))

    def test_search_skills(self, hub):
        result = hub.search_skills("code review")
        assert result.total >= 1
        assert any("review" in s.name for s in result.items)

    def test_search_by_category(self, hub):
        result = hub.search_skills("", category="security")
        assert all(s.category == "security" for s in result.items)

    def test_install_skill(self, hub):
        entry = hub.install_skill("code-reviewer")
        assert entry is not None
        assert entry.installed
        # 再次列出已安装
        installed = hub.list_skills(installed_only=True)
        assert len(installed) == 1

    def test_list_all_skills(self, hub):
        skills = hub.list_skills()
        assert len(skills) == len(TOP_SKILLS)

    def test_install_unknown(self, hub):
        assert hub.install_skill("nonexistent-skill-xyz") is None

    def test_skill_entry_frozen(self):
        s = SkillEntry(name="test", category="coding")
        with pytest.raises(Exception):
            s.name = "changed"  # type: ignore

    def test_search_result_empty(self, hub):
        result = hub.search_skills("xyznonexistent12345")
        assert result.total == 0


# ═══════════════════════════════════════════════════════════════
# MarketHub — MCP
# ═══════════════════════════════════════════════════════════════

class TestMarketHubMCP:
    @pytest.fixture
    def hub(self, tmp_path):
        return MarketHub(install_dir=str(tmp_path / "skills"))

    def test_search_mcp(self, hub):
        result = hub.search_mcp("database")
        assert result.total >= 1

    def test_search_mcp_by_category(self, hub):
        result = hub.search_mcp("", category="browser")
        assert all(s.category == "browser" for s in result.items)

    def test_install_mcp(self, hub):
        entry = hub.install_mcp("filesystem")
        if entry:
            assert entry.installed

    def test_list_mcp(self, hub):
        servers = hub.list_mcp()
        assert len(servers) == len(TOP_MCP_SERVERS)

    def test_mcp_entry_frozen(self):
        m = MCPEntry(name="test", category="system")
        with pytest.raises(Exception):
            m.name = "changed"  # type: ignore

    def test_search_result_timing(self, hub):
        result = hub.search_mcp("memory")
        assert result.took_ms >= 0


# ═══════════════════════════════════════════════════════════════
# 集成
# ═══════════════════════════════════════════════════════════════

class TestMarketIntegration:
    def test_full_market_flow(self, tmp_path):
        """完整流程: 搜索→安装→验证 技能+MCP。"""
        hub = MarketHub(str(tmp_path / "skills"))

        # Skills
        skills = hub.search_skills("python")
        assert skills.total >= 1

        entry = hub.install_skill("python-patterns")
        assert entry.installed

        # MCP
        mcps = hub.search_mcp("file")
        assert mcps.total >= 1

        stats = hub.get_stats()
        assert stats["skills_available"] == len(TOP_SKILLS)
        assert stats["mcp_available"] == len(TOP_MCP_SERVERS)
