"""Phase E smoke tests — plugin manifest, idempotency, session fork, voice, SDK, dashboard, Docker."""
import asyncio
import json
import sys
import pytest

sys.path.insert(0, ".")


# ── Gap: Plugin Manifest System ────────────────────────────────────────────

def test_plugin_manifest_create():
    """PluginManifest can be created from dict."""
    from kernel.plugin_manifest import PluginManifest

    m = PluginManifest.from_dict({
        "name": "test-plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "category": "test",
        "tools": ["tool_a", "tool_b"],
        "dependencies": ["dep1"],
        "enabled": True,
    })
    assert m.name == "test-plugin"
    assert len(m.tools) == 2
    assert "tool_a" in m.tools


def test_plugin_discovery_scan():
    """PluginDiscovery scans directories for manifests."""
    from kernel.plugin_manifest import PluginDiscovery, generate_manifest
    import tempfile, shutil, os

    tmp = tempfile.mkdtemp(prefix="sclerotium_plugins_")
    try:
        # Create plugin dirs with manifests
        for name, tools in [
            ("desktop-automation", ["desktop_open", "desktop_click", "desktop_screenshot"]),
            ("memory-system", ["memory_store", "memory_search"]),
        ]:
            plugin_dir = os.path.join(tmp, name)
            os.makedirs(plugin_dir, exist_ok=True)
            generate_manifest(name, tools, category="automation", output_dir=plugin_dir)

        discovery = PluginDiscovery()
        plugins = discovery.scan([tmp])

        assert len(plugins) >= 2
        names = {p.name for p in plugins}
        assert "desktop-automation" in names
        assert "memory-system" in names

        # get_all_tools
        all_tools = discovery.get_all_tools()
        assert "desktop_open" in all_tools
        assert "memory_search" in all_tools
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_plugin_topological_sort():
    """Plugins are sorted by dependency order."""
    from kernel.plugin_manifest import PluginDiscovery, PluginManifest

    discovery = PluginDiscovery()
    plugins = [
        PluginManifest(name="a", dependencies=(), tools=("tool_a",)),
        PluginManifest(name="b", dependencies=("a",), tools=("tool_b",)),
        PluginManifest(name="c", dependencies=("a", "b"), tools=("tool_c",)),
    ]
    for p in plugins:
        discovery._plugins[p.name] = p

    order = discovery._topological_sort(plugins)
    # a must come before b and c
    assert order.index("a") < order.index("b")
    assert order.index("a") < order.index("c")
    assert order.index("b") < order.index("c")


# ── Gap: Idempotency ──────────────────────────────────────────────────────

def test_idempotency_store():
    """IdempotencyStore deduplicates requests."""
    from kernel.idempotency import IdempotencyStore
    import tempfile, os

    tmp = tempfile.mkdtemp(prefix="sclerotium_idem_")
    try:
        store = IdempotencyStore(os.path.join(tmp, "idem.db"))

        key = store.generate_key("test")
        assert store.get(key) is None
        assert not store.is_duplicate(key)

        # Set
        store.set(key, {"status": "ok", "data": "test"}, ttl_seconds=60)
        assert store.is_duplicate(key)

        # Get cached
        cached = store.get(key)
        assert cached is not None
        assert cached.payload["status"] == "ok"

        # Stats
        stats = store.get_stats()
        assert stats["cached_entries"] >= 1

        store.close()
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def test_idempotency_expiry():
    """Idempotency entries expire after TTL."""
    from kernel.idempotency import IdempotencyStore
    import tempfile, os, time

    tmp = tempfile.mkdtemp(prefix="sclerotium_idem_")
    try:
        store = IdempotencyStore(os.path.join(tmp, "idem.db"))
        key = store.generate_key("expire_test")

        # Set with short TTL
        store.set(key, {"data": "test"}, ttl_seconds=0.01)
        time.sleep(0.05)

        # Should be expired
        assert not store.is_duplicate(key)

        store.close()
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ── Gap: Session Fork/Branch ──────────────────────────────────────────────

def test_session_fork():
    """Session can be forked into independent copy."""
    from agent.session import SessionManager
    from agent.session_fork import SessionForkManager
    import tempfile, shutil

    tmp = tempfile.mkdtemp(prefix="sclerotium_fork_")
    try:
        mgr = SessionManager(tmp)
        sid = mgr.create(title="Original Session")
        mgr.append_message(sid, {"role": "user", "content": "msg 1"})
        mgr.append_message(sid, {"role": "assistant", "content": "msg 2"})

        fork_mgr = SessionForkManager(mgr)
        result = fork_mgr.fork(sid)

        assert result.operation == "fork"
        assert result.message_count == 2
        assert result.new_session_id != sid

        # Fork has same messages
        forked_msgs = mgr.load_messages(result.new_session_id)
        assert len(forked_msgs) == 2
        assert forked_msgs[0]["content"] == "msg 1"

        mgr.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_session_branch_and_merge():
    """Session branch and merge operations work."""
    from agent.session import SessionManager
    from agent.session_fork import SessionForkManager
    import tempfile, shutil

    tmp = tempfile.mkdtemp(prefix="sclerotium_branch_")
    try:
        mgr = SessionManager(tmp)
        sid = mgr.create(title="Main")
        mgr.append_message(sid, {"role": "user", "content": "base msg"})

        fork_mgr = SessionForkManager(mgr)

        # Branch
        branch_result = fork_mgr.branch(sid, branch_name="experiment")
        assert branch_result.operation == "branch"

        # Add messages to branch
        mgr.append_message(branch_result.new_session_id, {"role": "user", "content": "branch msg"})
        branch_msgs = mgr.load_messages(branch_result.new_session_id)
        assert len(branch_msgs) == 2

        # Merge branch back
        merge_result = fork_mgr.merge(sid, branch_result.new_session_id)
        assert merge_result.merged_message_count >= 1

        # Diff
        diff = fork_mgr.diff(sid, branch_result.new_session_id)
        assert "session_a" in diff

        mgr.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── Gap: Voice Interface ──────────────────────────────────────────────────

def test_voice_config():
    """VoiceConfig is immutable and has correct defaults."""
    from kernel.voice import VoiceConfig, VoiceInterface

    config = VoiceConfig()
    assert config.stt_backend == "whisper"
    assert config.tts_backend == "edge"
    assert config.language == "zh-CN"

    voice = VoiceInterface(config)
    assert voice.config == config


# ── Gap: SDK ──────────────────────────────────────────────────────────────

def test_sdk_types():
    """SDK types are correct."""
    from sdk.sclerotium_sdk.types import (
        ChatResponse, ToolDefinition, SessionInfo,
        StreamEvent, SclerotiumConfig,
    )

    config = SclerotiumConfig(api_key="test-key", model="deepseek-v4-flash")
    assert config.model == "deepseek-v4-flash"

    resp = ChatResponse(content="Hello!")
    assert resp.content == "Hello!"
    assert not resp.tool_calls


# ── Gap: Enhanced Web UI ──────────────────────────────────────────────────

def test_dashboard_html():
    """Dashboard HTML is valid and contains key elements."""
    from ui.dashboard_v2 import DASHBOARD_HTML, DashboardV2

    assert "Sclerotium OS v5.2" in DASHBOARD_HTML
    assert "FCPI" in DASHBOARD_HTML
    assert "Token" in DASHBOARD_HTML
    assert "refresh" in DASHBOARD_HTML
    assert "#0d1117" in DASHBOARD_HTML  # Dark theme background

    dash = DashboardV2()
    assert dash is not None


# ── Gap: Type Safety ──────────────────────────────────────────────────────

def test_pyproject_strict():
    """pyproject.toml has strict mypy enabled."""
    import tomllib
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)

    mypy = config.get("tool", {}).get("mypy", {})
    assert mypy.get("strict") is True, "mypy strict mode not enabled"
    assert mypy.get("disallow_untyped_defs") is True


# ── Gap: Docker ───────────────────────────────────────────────────────────

def test_dockerfile_exists():
    """Dockerfile and docker-compose exist."""
    import os
    assert os.path.exists("Dockerfile"), "Dockerfile missing"
    assert os.path.exists("docker-compose.yml"), "docker-compose.yml missing"

    with open("Dockerfile", encoding="utf-8") as f:
        content = f.read()
    assert "FROM python" in content
    assert "SCLEROTIUM" in content
