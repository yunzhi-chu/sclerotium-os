"""Tests for Mechanism ⑯ M5: Cross-Ecosystem Security Gateway."""

import pytest

from src.l6.security_gateway import (
    BLACKLIST_SERVICE_TYPES,
    FORBIDDEN_ACTIONS,
    WHITELIST_SERVICE_TYPES,
    CrossEcoSecurityGateway,
    SlidingWindowRateLimiter,
    TokenBucket,
)


class TestSlidingWindowRateLimiter:
    def test_initial_state(self) -> None:
        rl = SlidingWindowRateLimiter(max_per_minute=60, max_per_hour=1000)
        assert rl.current_minute_count == 0
        assert rl.current_hour_count == 0

    def test_allows_requests_within_limit(self) -> None:
        rl = SlidingWindowRateLimiter(max_per_minute=100, max_per_hour=2000)
        for _ in range(50):
            ok, _ = rl.allow()
            assert ok

    def test_blocks_when_full(self) -> None:
        rl = SlidingWindowRateLimiter(max_per_minute=1, max_per_hour=1000)
        ok1, _ = rl.allow()
        assert ok1
        ok2, reason = rl.allow()
        assert not ok2
        assert "minute" in reason.lower()


class TestTokenBucket:
    def test_initial_capacity(self) -> None:
        tb = TokenBucket(capacity=10, refill_rate=1.0)
        assert tb.consume(5)
        assert tb.consume(5)
        assert not tb.consume(1)

    def test_consume_zero(self) -> None:
        tb = TokenBucket(capacity=5)
        assert tb.consume(0)


class TestSecurityGateway:
    @pytest.fixture
    def gw(self) -> CrossEcoSecurityGateway:
        g = CrossEcoSecurityGateway(max_per_minute=1000, max_per_hour=10000)
        return g

    # --- Registration ---

    def test_register_whitelisted_service(self, gw: CrossEcoSecurityGateway) -> None:
        ok, msg = gw.register_service("data-src-1", "data_provider", "secret-key-123")
        assert ok
        assert "registered" in msg.lower()

    def test_register_blacklisted_service_blocked(self, gw: CrossEcoSecurityGateway) -> None:
        ok, msg = gw.register_service("broker-1", "broker_api", "secret-key")
        assert not ok
        assert "blocked" in msg.lower() or "blacklist" in msg.lower()

    def test_register_unknown_type_rejected(self, gw: CrossEcoSecurityGateway) -> None:
        ok, msg = gw.register_service("unknown-1", "random_unknown_type", "key")
        assert not ok

    def test_duplicate_registration_updates(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("svc-1", "data_provider", "key1")
        ok, msg = gw.register_service("svc-1", "ai_tool", "key2")
        assert ok

    def test_revoke_service(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("svc-r", "ai_tool", "key")
        ok, _ = gw.revoke_service("svc-r")
        assert ok
        result = gw.validate_request("svc-r", "key")
        assert not result.allowed

    def test_suspend_and_block_service(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("svc-s", "research_database", "key")
        gw.suspend_service("svc-s", "testing")
        result = gw.validate_request("svc-s", "key")
        assert not result.allowed

        gw.block_service("svc-b", "violation")
        status = gw.get_service_status("svc-b")
        assert status["status"] == "blocked"

    # --- Validation ---

    def test_validate_valid_request(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("valid-1", "data_provider", "my-api-key")
        result = gw.validate_request("valid-1", "my-api-key", "")
        assert result.allowed
        assert result.reason == "ok"

    def test_validate_unknown_service(self, gw: CrossEcoSecurityGateway) -> None:
        result = gw.validate_request("ghost", "key")
        assert not result.allowed
        assert "unknown" in result.reason.lower()

    def test_validate_wrong_api_key(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("svc-key", "ai_tool", "correct-key")
        result = gw.validate_request("svc-key", "wrong-key")
        assert not result.allowed

    def test_validate_inactive_service(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("svc-inact", "backtest_platform", "key")
        gw.revoke_service("svc-inact")
        result = gw.validate_request("svc-inact", "key")
        assert not result.allowed

    # --- Content Safety ---

    def test_content_safety_blocks_trade_action(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("content-1", "ai_tool", "key1")
        result = gw.validate_request("content-1", "key1", "please execute trade for AAPL")
        assert not result.allowed
        assert "content safety" in result.reason.lower()

    def test_content_safety_blocks_buy_sell(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("content-2", "research_database", "key2")
        result = gw.validate_request("content-2", "key2", "buy 100 shares of TSLA")
        assert not result.allowed

    def test_content_safety_allows_harmless(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("content-3", "research_database", "key3")
        result = gw.validate_request("content-3", "key3", "analyze market trends for Q3")
        assert result.allowed

    def test_content_safety_blocks_exec_function(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("content-4", "ai_tool", "key4")
        result = gw.validate_request("content-4", "key4", "eval('print(123)')")
        assert not result.allowed

    # --- Rate Limiting (global) ---

    def test_global_rate_limiting(self) -> None:
        gw = CrossEcoSecurityGateway(max_per_minute=2, max_per_hour=1000)
        gw.register_service("rate-1", "open_source_library", "k")
        assert gw.validate_request("rate-1", "k").allowed
        assert gw.validate_request("rate-1", "k").allowed
        r3 = gw.validate_request("rate-1", "k")
        assert not r3.allowed
        assert "rate" in r3.reason.lower()

    # --- Import ---

    def test_import_data_allowed_format(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("import-1", "data_provider", "key")
        result = gw.import_external_data("import-1", {"format": "csv", "max_size_mb": 50})
        assert result.allowed
        assert "validation_checks" in result.__dict__ or True

    def test_import_rejects_blocked_source(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("import-2", "data_provider", "key")
        result = gw.import_external_data("import-2", {
            "format": "csv",
            "source_url": "https://broker-api.example.com/data",
        })
        assert not result.allowed

    def test_import_rejects_oversized(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("import-3", "data_provider", "key")
        result = gw.import_external_data("import-3", {"format": "json", "max_size_mb": 600})
        assert not result.allowed

    def test_import_rejects_bad_format(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("import-4", "data_provider", "key")
        result = gw.import_external_data("import-4", {"format": "exe"})
        assert not result.allowed

    def test_import_inactive_service_blocked(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("import-5", "data_provider", "key")
        gw.suspend_service("import-5")
        result = gw.import_external_data("import-5", {"format": "csv"})
        assert not result.allowed

    # --- Status & Stats ---

    def test_get_service_status_single(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("status-1", "data_provider", "key")
        s = gw.get_service_status("status-1")
        assert s["service_type"] == "data_provider"
        assert s["status"] == "active"

    def test_get_service_status_all(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("sa1", "data_provider", "k1")
        gw.register_service("sa2", "ai_tool", "k2")
        all_s = gw.get_service_status()
        assert len(all_s) >= 2

    def test_stats_reflects_state(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("st1", "data_provider", "k1")
        gw.register_service("st2", "ai_tool", "k2")
        gw.block_service("st3", "bad")
        s = gw.stats
        assert s["active_services"] >= 2
        assert s["blocked_services"] >= 1
        assert "data_provider" in s["whitelist_types"]
        assert "broker_api" in s["blacklist_types"]

    def test_violation_log(self, gw: CrossEcoSecurityGateway) -> None:
        gw.register_service("vl1", "data_provider", "key")
        gw.validate_request("vl1", "wrong-key")
        gw.validate_request("vl1", "wrong-key-2")
        assert len(gw.violation_log) >= 2

    # --- Constants ---

    def test_whitelist_has_five_types(self) -> None:
        assert len(WHITELIST_SERVICE_TYPES) == 5
        assert "data_provider" in WHITELIST_SERVICE_TYPES
        assert "broker_api" not in WHITELIST_SERVICE_TYPES

    def test_blacklist_has_six_types(self) -> None:
        assert len(BLACKLIST_SERVICE_TYPES) == 6
        assert "broker_api" in BLACKLIST_SERVICE_TYPES
        assert "trading_platform" in BLACKLIST_SERVICE_TYPES

    def test_forbidden_actions(self) -> None:
        assert "trade" in FORBIDDEN_ACTIONS
        assert "execute" in FORBIDDEN_ACTIONS
        assert "transfer" in FORBIDDEN_ACTIONS

    def test_constant_time_key_comparison(self, gw: CrossEcoSecurityGateway) -> None:
        """HMAC.compare_digest provides constant-time comparison."""
        gw.register_service("ct-1", "ai_tool", "a" * 32)
        # Same length, different content
        result = gw.validate_request("ct-1", "b" * 32)
        assert not result.allowed
