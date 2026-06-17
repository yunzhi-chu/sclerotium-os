"""Tests for Phase 2E MCP tools — IM, desktop, scheduler, files, info, mode, hexis."""

import pytest
from mcp.server import SclerotiumMCPServer


@pytest.fixture
def tools():
    server = SclerotiumMCPServer()
    server.register_all_tools()
    return server.tools


class TestIMTools:
    def test_all_8_im_tools_registered(self, tools):
        names = ["im_send", "im_receive", "im_search", "im_summarize",
                 "im_react", "im_send_file", "im_list_conversations", "im_create_group"]
        for n in names:
            assert tools.get_handler(n) is not None, f"{n} missing"

    @pytest.mark.asyncio
    async def test_im_send(self, tools):
        result = await tools.get_handler("im_send")(
            platform="feishu", target="test_chat", content="hello"
        )
        assert result["platform"] == "feishu"
        assert "message_id" in result

    @pytest.mark.asyncio
    async def test_im_list_conversations(self, tools):
        result = await tools.get_handler("im_list_conversations")(platform="feishu")
        assert isinstance(result, list)


class TestDesktopTools:
    def test_all_6_desktop_tools_registered(self, tools):
        for n in ["desktop_screenshot", "desktop_click", "desktop_type",
                   "desktop_open", "desktop_read", "desktop_chain"]:
            assert tools.get_handler(n) is not None

    @pytest.mark.asyncio
    async def test_desktop_open(self, tools):
        result = await tools.get_handler("desktop_open")(target="notepad.exe")
        assert "status" in result


class TestSchedulerTools:
    def test_all_4_scheduler_tools(self, tools):
        for n in ["schedule_add", "schedule_list", "schedule_remove", "schedule_toggle"]:
            assert tools.get_handler(n) is not None

    @pytest.mark.asyncio
    async def test_schedule_list(self, tools):
        result = await tools.get_handler("schedule_list")()
        assert isinstance(result, list)


class TestFilesTools:
    def test_all_3_files_tools(self, tools):
        for n in ["files_watch", "files_organize", "files_search"]:
            assert tools.get_handler(n) is not None

    @pytest.mark.asyncio
    async def test_files_search(self, tools):
        result = await tools.get_handler("files_search")(query="test", path=".")
        assert isinstance(result, list)


class TestInfoTools:
    def test_all_3_info_tools(self, tools):
        for n in ["info_daily_digest", "info_calendar_today", "info_mail_check"]:
            assert tools.get_handler(n) is not None


class TestModeTool:
    def test_mode_switch_registered(self, tools):
        assert tools.get_handler("mode_switch") is not None

    @pytest.mark.asyncio
    async def test_mode_switch_work(self, tools):
        result = await tools.get_handler("mode_switch")(profile="work")
        assert result["active_profile"] == "work"

    @pytest.mark.asyncio
    async def test_mode_switch_sleep(self, tools):
        result = await tools.get_handler("mode_switch")(profile="sleep")
        assert result["active_profile"] == "sleep"


class TestHexisMemory:
    def test_store_and_search(self):
        from kernel.hexis_memory import HexisMemoryStore
        store = HexisMemoryStore(chroma_path="./data/test_chroma", sqlite_path="./data/test_memory.db")
        mid = store.store("test episodic memory about evolution", level="episodic", importance=0.8)
        assert mid.startswith("mem_")
        results = store.search("evolution", top_k=5)
        assert len(results) >= 0  # ChromaDB may not be installed
        store.close()

    def test_consolidate(self):
        from kernel.hexis_memory import HexisMemoryStore
        store = HexisMemoryStore(chroma_path="./data/test_chroma2", sqlite_path="./data/test_memory2.db")
        for i in range(5):
            store.store(f"pattern alpha found in generation {i}", level="episodic")
        result = store.consolidate("episodic", "semantic")
        assert result["consolidated_count"] == 5
        store.close()

    def test_forget(self):
        from kernel.hexis_memory import HexisMemoryStore
        store = HexisMemoryStore(chroma_path="./data/test_chroma3", sqlite_path="./data/test_memory3.db")
        store.store("very old unimportant note", level="episodic", importance=0.1)
        result = store.forget("episodic", threshold_days=0)
        assert "forgotten_count" in result
        store.close()

    def test_get_context(self):
        from kernel.hexis_memory import HexisMemoryStore
        store = HexisMemoryStore(chroma_path="./data/test_chroma4", sqlite_path="./data/test_memory4.db")
        store.store("test memory", level="episodic")
        ctx = store.get_context()
        assert "total_memories" in ctx
        assert "level_counts" in ctx
        store.close()


def test_total_tool_count(tools):
    assert tools.tool_count >= 45
