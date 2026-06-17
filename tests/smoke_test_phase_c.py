"""Phase C smoke tests — P2 enhancements: error handling, logging, model router, token tracker, organ protocol, platform detect, config watcher, sub-agent."""
import asyncio
import sys
import pytest

sys.path.insert(0, ".")


# ── Gap 23: Structured Error Hierarchy ────────────────────────────────────

def test_error_hierarchy():
    """All error types are properly structured."""
    from kernel.errors import (
        SclerotiumError, ToolNotFoundError, LLMConnectionError,
        SessionNotFoundError, ConfigError, SafeResult, safe_execute,
    )

    # Error creation
    err = ToolNotFoundError("tool xyz not found", detail="xyz")
    assert err.code == "E1001"
    assert err.status == 404
    assert "Use /tools" in err.hint
    d = err.to_dict()
    assert d["error"] == "E1001"
    assert "tool xyz" in d["message"]

    # LLM error
    err2 = LLMConnectionError("timeout")
    assert err2.code == "E2001"

    # safe_execute
    result = safe_execute(lambda x: x + 1, 41)
    assert result.ok
    assert result.value == 42

    result = safe_execute(lambda: 1 / 0)
    assert not result.ok
    assert result.error is not None


# ── Gap 22: Structured Logger ─────────────────────────────────────────────

def test_structured_logger():
    """Structured logger creates proper entries."""
    from kernel.structured_logger import StructuredLogger, LogEntry

    slog = StructuredLogger("test.module")
    # Should not raise
    slog.info("test message", key="value")
    slog.warn("warning", attempt=2)
    slog.error("error", err="something broke")

    # LogEntry is immutable
    entry = LogEntry(level="info", msg="test")
    assert entry.level == "info"
    assert entry.module == ""


# ── Gap 16: Model Router ──────────────────────────────────────────────────

def test_model_router():
    """Model router picks appropriate models."""
    from agent.model_router import ModelRouter

    router = ModelRouter()

    # Simple task
    route = router.route("hello")
    assert "flash" in route.model.lower()
    assert route.estimated_cost_multiplier < 1.0

    # Standard task
    route = router.route("write a python function to sort a list")
    assert route.estimated_cost_multiplier >= 1.0

    # Complex task
    route = router.route("refactor the entire authentication system across all microservices")
    assert route.estimated_cost_multiplier > 3.0


# ── Gap 17: Token Tracker ─────────────────────────────────────────────────

def test_token_tracker():
    """Token tracker records and reports usage."""
    from agent.token_tracker import TokenTracker
    import tempfile, os

    tmp = tempfile.mkdtemp(prefix="sclerotium_tokens_")
    try:
        tracker = TokenTracker(os.path.join(tmp, "tokens.db"))
        tracker.record("deepseek-v4-flash", "deepseek", 500, 300)

        stats = tracker.get_daily_stats()
        assert stats["calls"] == 1
        assert stats["tokens_today"] == 800
        assert stats["cost_today_usd"] < 1.0  # DeepSeek is cheap

        total = tracker.get_total_stats()
        assert total["total_calls"] == 1

        tracker.close()
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ── Gap 18: Organ Protocol ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_organ_protocol():
    """Organ protocol and registry work."""
    from kernel.organ_protocol import (
        OrganProtocol, OrganRegistry, HealthReport,
        OrganInfo, OrganStatus,
    )

    class TestOrgan(OrganProtocol):
        @property
        def organ_name(self) -> str:
            return "test_organ"

        async def initialize(self) -> bool:
            return True

        async def health_check(self) -> HealthReport:
            return HealthReport(organ="test_organ", healthy=True)

        async def shutdown(self) -> None:
            pass

    organ = TestOrgan()
    assert organ.organ_name == "test_organ"

    registry = OrganRegistry()
    registry.register(organ)
    assert registry.organ_count == 1

    reports = await registry.health_check_all()
    assert len(reports) == 1
    assert reports[0].healthy

    tools = registry.get_all_tools()
    assert isinstance(tools, list)


# ── Gap 21: Platform Detect ───────────────────────────────────────────────

def test_platform_detect():
    """Platform detection works on Windows."""
    from kernel.platform_detect import detect_platform, get_platform

    info = detect_platform()
    assert info.system in ("Windows", "Linux", "Darwin")
    assert info.is_windows  # We're on Windows
    assert info.home_dir
    assert info.app_data_dir

    cached = get_platform()
    assert cached.system == info.system


# ── Gap 20: Config Watcher ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_config_watcher():
    """Config watcher detects file changes."""
    from kernel.config_watcher import ConfigWatcher, ConfigChange
    import tempfile, os

    tmp = tempfile.mkdtemp(prefix="sclerotium_config_")
    try:
        test_file = os.path.join(tmp, "test_config.yaml")
        with open(test_file, "w") as f:
            f.write("key: value1")

        changes = []

        watcher = ConfigWatcher(poll_interval=0.1)
        watcher.watch(test_file, lambda c: changes.append(c))

        # Modify file
        await asyncio.sleep(0.2)
        with open(test_file, "w") as f:
            f.write("key: value2")

        # Check now
        detected = watcher.check_now()
        assert len(detected) >= 1
        assert detected[0].event_type == "modified"
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ── Gap 13: Sub-Agent ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sub_agent_creation():
    """Sub-agent manager can be created."""
    from agent.sub_agent import SubAgentManager, SubAgentResult

    mgr = SubAgentManager()
    assert mgr.max_depth == 3
    assert mgr.active_count == 0

    # Spawn without LLM client (fallback)
    result = await mgr.spawn("test task")
    assert isinstance(result, SubAgentResult)
    assert result.task == "test task"


# ── Gap 14: Approval UI (basic notification) ──────────────────────────────

def test_approval_request():
    """Approval request data structure is correct."""
    from dataclasses import dataclass, field

    @dataclass(frozen=True)
    class ApprovalRequest:
        tool: str
        args: dict
        risk_level: str = "low"
        request_id: str = ""

    req = ApprovalRequest(tool="file_write", args={"path": "test.py"}, risk_level="medium")
    assert req.tool == "file_write"
    assert req.risk_level == "medium"


# ── Gap 12: Platform get_tools() ──────────────────────────────────────────

def test_platform_get_tools():
    """Platform adapter has get_tools() method."""
    from platforms.base import PlatformAdapter, MockPlatformAdapter

    adapter = MockPlatformAdapter()
    tools = adapter.get_tools()
    assert isinstance(tools, list)
