"""Tests for Phase 4 Advanced Modules — P0/P1/P2."""

import pytest
from mcp.server import SclerotiumMCPServer

@pytest.fixture
def tools():
    s = SclerotiumMCPServer(); s.register_all_tools(); return s.tools

class TestRefactoring:
    def test_all_registered(self, tools):
        for n in ["refactor_analyze","refactor_dead_code","refactor_duplicates","refactor_impact","refactor_callers"]:
            assert tools.get_handler(n) is not None
    @pytest.mark.asyncio
    async def test_analyze(self, tools):
        r = await tools.get_handler("refactor_analyze")(path=".")
        assert "total_symbols" in r
    @pytest.mark.asyncio
    async def test_dead_code(self, tools):
        r = await tools.get_handler("refactor_dead_code")(path=".")
        assert isinstance(r, list)

class TestVisionDesktop:
    def test_all_registered(self, tools):
        for n in ["vision_click","vision_type","vision_screenshot","vision_open","vision_chain"]:
            assert tools.get_handler(n) is not None

class TestFormalVerify:
    def test_registered(self, tools):
        assert tools.get_handler("verify_code") is not None
        assert tools.get_handler("verify_safety") is not None
    @pytest.mark.asyncio
    async def test_verify_clean(self, tools):
        r = await tools.get_handler("verify_code")(code="x=1+1")
        assert r["passed"] is True
    @pytest.mark.asyncio
    async def test_verify_dangerous(self, tools):
        r = await tools.get_handler("verify_code")(code="eval('1+1')")
        assert r["passed"] is False

class TestSourceEvolve:
    def test_registered(self, tools):
        assert tools.get_handler("evolve_detect") is not None
        assert tools.get_handler("evolve_cycle") is not None
    @pytest.mark.asyncio
    async def test_detect(self, tools):
        r = await tools.get_handler("evolve_detect")(path=".")
        assert isinstance(r, list)

class TestWASM:
    def test_registered(self, tools):
        assert tools.get_handler("wasm_execute") is not None
    @pytest.mark.asyncio
    async def test_execute(self, tools):
        r = await tools.get_handler("wasm_execute")(code="print(42)")
        assert "42" in r.get("stdout","")

class TestProactiveMemory:
    def test_registered(self, tools):
        assert tools.get_handler("memory_predict") is not None
        assert tools.get_handler("memory_dream") is not None

class TestDebugger:
    def test_registered(self, tools):
        assert tools.get_handler("debug_code") is not None
        assert tools.get_handler("debug_suggest") is not None
    @pytest.mark.asyncio
    async def test_debug(self, tools):
        r = await tools.get_handler("debug_code")(code="print(1/0)")
        assert "root_cause" in r

class TestSubAgent:
    def test_registered(self, tools):
        assert tools.get_handler("subagent_dispatch") is not None

class TestHooksPlugins:
    def test_registered(self, tools):
        assert tools.get_handler("hooks_list") is not None
        assert tools.get_handler("plugins_list") is not None

class TestTestGenerator:
    def test_registered(self, tools):
        assert tools.get_handler("test_analyze") is not None
        assert tools.get_handler("test_generate") is not None

class TestCrossOS:
    def test_registered(self, tools):
        assert tools.get_handler("cross_os_platform") is not None

class TestVoiceRemote:
    def test_registered(self, tools):
        assert tools.get_handler("voice_listen") is not None
        assert tools.get_handler("remote_start") is not None

def test_imports():
    from kernel.advanced.code_refactor import SemanticRefactorEngine, CallGraph
    from kernel.advanced.vision_desktop import VisionDesktopAgent
    from kernel.advanced.formal_verify import FormalVerifier, RejectionSampler
    from kernel.advanced.source_evolve import SourceEvolutionEngine
    from kernel.advanced.wasm_sandbox import WASMSandbox
    from kernel.advanced.proactive_memory import ProactiveMemoryEngine
    from kernel.advanced.debugger import DebuggerAgent
    from kernel.advanced.subagent_delegation import SubAgentDelegator, AgentRole
    from kernel.advanced.hooks_plugin import HooksPluginSystem, HookEvent, HookType
    from kernel.advanced.test_generator import TestGenerator
    from kernel.advanced.cross_os_desktop import CrossOSDesktop
    from kernel.advanced.voice_remote import VoiceInput, RemoteControl

def test_total_tool_count(tools):
    assert tools.tool_count >= 90
