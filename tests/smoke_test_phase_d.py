"""Phase D smoke tests — approval UI, installer, E2E integration."""
import asyncio
import sys
import pytest

sys.path.insert(0, ".")


# ── Gap 14: Approval UI ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approval_ui_creation():
    """ApprovalUIManager creates and tracks requests."""
    from kernel.approval_ui import (
        ApprovalUIManager, ApprovalRequest, ApprovalStatus, RiskLevel,
    )

    mgr = ApprovalUIManager(default_timeout=1.0)

    # Create request
    req = mgr.request(
        "file_write",
        {"file_path": "config.yaml", "content": "key: value"},
        reason="Writing config file",
        risk=RiskLevel.T2,
        source="brain",
    )
    assert req.tool == "file_write"
    assert req.risk_level == RiskLevel.T2
    assert req.status == ApprovalStatus.PENDING
    assert "file_write" in req.summary

    # Check pending
    pending = mgr.get_pending()
    assert len(pending) == 1

    # Decide
    ok = await mgr.decide(req.request_id, approved=True)
    assert ok

    # Verify decision
    status = mgr._decisions.get(req.request_id)
    assert status == ApprovalStatus.APPROVED


@pytest.mark.asyncio
async def test_approval_timeout():
    """Approval request times out correctly."""
    from kernel.approval_ui import ApprovalUIManager, ApprovalStatus, RiskLevel

    mgr = ApprovalUIManager(default_timeout=0.1)

    req = mgr.request("bash_execute", {"command": "ls"}, risk=RiskLevel.T2)
    status = await mgr.wait_for_decision(req, timeout=0.1)
    assert status == ApprovalStatus.TIMEOUT


def test_risk_levels():
    """IETF AIGA risk tiers are defined."""
    from kernel.approval_ui import RiskLevel

    assert RiskLevel.T0.value == "t0"  # Read-only
    assert RiskLevel.T4.value == "t4"  # Critical
    assert len(RiskLevel) == 5


# ── E2E: Full system startup (without API key) ─────────────────────────────

@pytest.mark.asyncio
async def test_full_system_import_chain():
    """All critical modules load without errors."""
    # Phase A modules
    from agent.llm_client import LLMClient, ToolCall, LLMResponse, ProviderConfig
    from agent.code_action import CodeActionRuntime, ExecutionResult

    # Phase B modules
    from agent.session import SessionManager, SessionInfo
    from kernel.constitutional_arbiter import (
        ConstitutionalArbiter, ApprovalMode, ActionRequest, ArbiterDecision,
    )
    from mcp.validation import ToolSchemaValidator

    # Phase C modules
    from kernel.errors import SclerotiumError, SafeResult, safe_execute
    from kernel.structured_logger import StructuredLogger
    from agent.model_router import ModelRouter, ModelRoute
    from agent.token_tracker import TokenTracker
    from kernel.organ_protocol import OrganProtocol, OrganRegistry
    from kernel.platform_detect import PlatformInfo, detect_platform
    from kernel.config_watcher import ConfigWatcher
    from agent.sub_agent import SubAgentManager, SubAgentResult

    # Phase D modules
    from kernel.approval_ui import ApprovalUIManager, ApprovalRequest, RiskLevel

    # MCP server
    from mcp.server import SclerotiumMCPServer

    # All good
    assert LLMClient is not None
    assert CodeActionRuntime is not None
    assert SessionManager is not None
    assert ConstitutionalArbiter is not None
    assert ToolSchemaValidator is not None
    assert safe_execute is not None
    assert ModelRouter is not None
    assert TokenTracker is not None
    assert OrganRegistry is not None
    assert ConfigWatcher is not None
    assert SubAgentManager is not None
    assert ApprovalUIManager is not None
    assert SclerotiumMCPServer is not None


@pytest.mark.asyncio
async def test_mcp_tool_count():
    """MCP server registers 191+ tools."""
    from mcp.server import SclerotiumMCPServer

    server = SclerotiumMCPServer()
    server.register_all_tools()
    assert server.tools.tool_count >= 190, f"Expected 190+ tools, got {server.tools.tool_count}"


# ── E2E: Code action → tool execution chain ────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_code_action_to_tool():
    """Code action executes tools through the full chain."""
    from mcp.server import SclerotiumMCPServer
    from agent.code_action import CodeActionRuntime

    server = SclerotiumMCPServer()
    server.register_all_tools()

    runtime = CodeActionRuntime()
    runtime.register_from_registry(server.tools, ["bash_execute", "file_write", "file_read"])

    # Write → Read roundtrip
    result = await runtime.execute("""
tools["file_write"](file_path="data/_e2e_test.txt", content="E2E test content")
read_result = tools["file_read"](file_path="data/_e2e_test.txt")
print("CONTENT=" + read_result.get("content", "").strip())
""")
    assert result.success, f"E2E failed: {result.error}"
    assert "E2E test content" in result.output


# ── E2E: Session persistence roundtrip ─────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_session_roundtrip():
    """Session survives create → save → reload → resume."""
    from agent.session import SessionManager
    import tempfile, shutil, os

    tmp = tempfile.mkdtemp(prefix="sclerotium_e2e_")
    try:
        mgr = SessionManager(tmp)
        sid = mgr.create(title="E2E Test Session", model="deepseek-v4-flash")

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
        ]

        for msg in messages:
            mgr.append_message(sid, msg)

        # Save checkpoint
        mgr.save_checkpoint(sid, messages, token_count=150)

        # Reload
        loaded = mgr.load_messages(sid)
        assert len(loaded) == 3
        assert loaded[0]["role"] == "system"
        assert loaded[2]["content"] == "Python is a programming language."

        # Metadata intact
        info = mgr.get(sid)
        assert info.token_count == 150

        mgr.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
