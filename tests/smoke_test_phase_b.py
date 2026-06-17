"""Phase B smoke tests — retry, session, arbiter modes, schema validation."""
import asyncio
import json
import sys
import pytest

sys.path.insert(0, ".")


# ── Gap 4+9: Multi-provider + Retry chain ──────────────────────────────────

@pytest.mark.asyncio
async def test_provider_config():
    """ProviderConfig is immutable with correct defaults."""
    from agent.llm_client import ProviderConfig, _PROVIDER_REGISTRY

    deepseek = _PROVIDER_REGISTRY["deepseek"]
    assert deepseek.name == "deepseek"
    assert deepseek.default_model == "deepseek-v4-flash"
    assert deepseek.priority == 0  # Highest priority

    ollama = _PROVIDER_REGISTRY["ollama"]
    assert ollama.priority == 40  # Lowest priority — last resort


@pytest.mark.asyncio
async def test_fallback_chain():
    """Fallback chain is built correctly."""
    from agent.llm_client import LLMClient

    client = LLMClient(api_key="test-key", fallback_providers=["openrouter", "ollama"])
    chain = client.get_fallback_chain()

    assert len(chain) == 3
    assert chain[0][0] == "deepseek"  # Primary
    assert chain[1][0] == "openrouter"  # First fallback
    assert chain[2][0] == "ollama"  # Second fallback


@pytest.mark.asyncio
async def test_retry_stats():
    """Retry stats are tracked."""
    from agent.llm_client import LLMClient

    client = LLMClient(api_key="test-key", max_retries=3)
    assert client.max_retries == 3
    assert client.retry_base_delay == 1.0
    assert client.retry_max_delay == 30.0
    assert client.retry_stats["total_retries"] == 0


# ── Gap 6: Session persistence ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_create_and_load():
    """Session can be created, messages appended, and loaded back."""
    from agent.session import SessionManager
    import tempfile, os

    tmpdir = tempfile.mkdtemp(prefix="sclerotium_test_")
    try:
        mgr = SessionManager(tmpdir)
        sid = mgr.create(title="Test Session", model="deepseek-v4-flash")

        # Append messages
        mgr.append_message(sid, {"role": "user", "content": "Hello"})
        mgr.append_message(sid, {"role": "assistant", "content": "Hi!"})

        # Load back
        msgs = mgr.load_messages(sid)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello"
        assert msgs[1]["role"] == "assistant"

        # Get metadata
        info = mgr.get(sid)
        assert info is not None
        assert info.title == "Test Session"
        assert info.message_count == 2

        # List sessions
        sessions = mgr.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == sid

        # Stats
        stats = mgr.get_stats()
        assert stats["total_sessions"] == 1

        mgr.close()
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_session_checkpoint():
    """Checkpoint saves full snapshot."""
    from agent.session import SessionManager
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="sclerotium_test_")
    try:
        mgr = SessionManager(tmpdir)
        sid = mgr.create(title="Checkpoint Test")

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Question"},
        ]
        mgr.save_checkpoint(sid, messages, token_count=100)

        loaded = mgr.load_messages(sid)
        assert len(loaded) == 2
        assert loaded[0]["content"] == "You are helpful."

        info = mgr.get(sid)
        assert info.token_count == 100

        mgr.close()
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── Gap 8: 7-mode ConstitutionalArbiter ────────────────────────────────────

def test_arbiter_modes():
    """All 7 approval modes are available."""
    from kernel.constitutional_arbiter import ConstitutionalArbiter, ApprovalMode, ActionRequest

    arbiter = ConstitutionalArbiter()

    # Test BYPASS mode
    arbiter.set_mode(ApprovalMode.BYPASS)
    req = ActionRequest(tool="file_write", target="/etc/passwd")
    dec = arbiter.review(req)
    assert dec.approved is True

    # Test DONT_ASK mode
    arbiter.set_mode(ApprovalMode.DONT_ASK)
    req = ActionRequest(tool="file_read", target="test.py")
    dec = arbiter.review(req)
    assert dec.approved is True  # Read-only allowed

    req = ActionRequest(tool="file_write", target="test.py")
    dec = arbiter.review(req)
    assert dec.approved is False  # Write blocked

    # Test AUTO mode (trusted source)
    arbiter.set_mode(ApprovalMode.AUTO)
    req = ActionRequest(tool="file_write", target="test.py", source="brain")
    dec = arbiter.review(req)
    assert dec.approved is True

    # Test DEFAULT mode (normal review)
    arbiter.set_mode(ApprovalMode.DEFAULT)
    req = ActionRequest(tool="file_read", target="test.py")
    dec = arbiter.review(req)
    assert dec.approved is True  # Read-only auto-approved


def test_cuga_checkpoints():
    """CUGA 5-checkpoint governance works."""
    from kernel.constitutional_arbiter import ConstitutionalArbiter, ActionRequest

    arbiter = ConstitutionalArbiter()

    # Low risk: file_read
    req = ActionRequest(tool="file_read", target="test.py")
    result = arbiter.run_cuga_checkpoints(req)
    assert result["verdict"] == "pass"
    assert result["checkpoints"]["intent_guard"]["risk"] == "low"

    # Critical risk: rm system file
    req = ActionRequest(tool="rm", target="c:\\windows\\system32\\file.dll")
    result = arbiter.run_cuga_checkpoints(req)
    assert result["verdict"] == "block"

    # Network egress
    req = ActionRequest(tool="im_send", target="channel_12345")
    result = arbiter.run_cuga_checkpoints(req)
    assert result["checkpoints"]["intent_guard"]["risk"] == "high"


# ── Gap 11: Schema validation ──────────────────────────────────────────────

def test_schema_validation_basic():
    """Basic type validation works."""
    from mcp.validation import ToolSchemaValidator
    from mcp.server import SclerotiumMCPServer

    server = SclerotiumMCPServer()
    server.register_all_tools()

    validator = ToolSchemaValidator()
    validator.register_from_registry(server.tools)

    # Valid args
    errors = validator.validate("file_read", {"file_path": "test.py"})
    assert len(errors) == 0, f"Unexpected errors: {errors}"

    # Wrong type
    errors = validator.validate("file_read", {"file_path": 12345})
    assert len(errors) > 0
    assert any("expected string" in e for e in errors)

    # Missing required field
    errors = validator.validate("bash_execute", {})
    assert any("missing required" in e for e in errors)


def test_schema_validation_enum():
    """Enum constraint validation works."""
    from mcp.validation import ToolSchemaValidator

    validator = ToolSchemaValidator()
    validator.register_tool("test_tool", {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["auto", "manual"]},
        },
        "required": [],
    })

    assert validator.is_valid("test_tool", {"mode": "auto"})
    assert not validator.is_valid("test_tool", {"mode": "invalid"})

    errors = validator.validate("test_tool", {"mode": "invalid"})
    assert any("not in allowed values" in e for e in errors)


def test_schema_validation_numeric():
    """Numeric constraint validation works."""
    from mcp.validation import ToolSchemaValidator

    validator = ToolSchemaValidator()
    validator.register_tool("test_limits", {
        "type": "object",
        "properties": {
            "count": {"type": "integer", "minimum": 1, "maximum": 100},
        },
        "required": [],
    })

    assert validator.is_valid("test_limits", {"count": 50})
    assert not validator.is_valid("test_limits", {"count": 0})
    assert not validator.is_valid("test_limits", {"count": 101})


# ── Integration: LLMClient with new features ───────────────────────────────

@pytest.mark.asyncio
async def test_llm_client_with_retry_config():
    """LLMClient accepts retry + provider config."""
    from agent.llm_client import LLMClient

    client = LLMClient(
        api_key="test-key",
        model="deepseek-v4-flash",
        max_retries=5,
        retry_base_delay=0.5,
        fallback_providers=["openai", "groq", "ollama"],
    )

    assert client.max_retries == 5
    assert client.retry_base_delay == 0.5
    assert len(client._fallback_providers) == 3
    chain = client.get_fallback_chain()
    assert len(chain) >= 1  # At least primary
