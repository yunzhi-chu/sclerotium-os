"""Tests for Phase 7 security modules: JWT, Rate Limiter, Sandbox."""
import hashlib
import pytest
from src.security.jwt_auth import JWTAuthManager, TokenType
from src.security.rate_limiter import RateLimiter, GFRStage, LimitExceeded
from src.security.sandbox_hardening import (
    SandboxHardening, SecurityLevel, SandboxProfile,
)


class TestJWTAuth:
    def test_create_and_verify(self):
        jwt = JWTAuthManager()
        pair = jwt.create_token_pair("agent-1", ["read"])
        claims = jwt.verify_token(pair.access_token)
        assert claims is not None
        assert claims.sub == "agent-1"

    def test_refresh_rotation(self):
        jwt = JWTAuthManager(token_rotation=True)
        pair = jwt.create_token_pair("agent-2")
        new_pair = jwt.refresh_access(pair.refresh_token)
        assert new_pair is not None
        assert new_pair.access_token != pair.access_token

    def test_revocation(self):
        jwt = JWTAuthManager()
        pair = jwt.create_token_pair("agent-3")
        claims = jwt.verify_token(pair.access_token)
        jwt.revoke_token(claims.jti)
        assert jwt.verify_token(pair.access_token) is None

    def test_subject_revocation(self):
        jwt = JWTAuthManager()
        pair = jwt.create_token_pair("subject-1")
        jwt.revoke_subject("subject-1")
        assert jwt.verify_token(pair.access_token) is None

    def test_api_key_verification(self):
        jwt = JWTAuthManager()
        key = "secret-key-123"
        expected = hashlib.sha256(key.encode()).hexdigest()
        assert jwt.verify_api_key(key, expected)
        assert not jwt.verify_api_key("wrong", expected)

    def test_expired_token(self):
        jwt = JWTAuthManager(access_ttl=-1)  # Already expired
        pair = jwt.create_token_pair("agent-4")
        claims = jwt.verify_token(pair.access_token)
        assert claims is None


class TestRateLimiter:
    def test_basic_allow_block(self):
        rl = RateLimiter(default_limit=5, default_window=10.0, burst_multiplier=1.0)
        for i in range(5):
            assert rl.check("key1")
        assert not rl.check("key1")  # 6th should be blocked

    def test_burst_allowance(self):
        rl = RateLimiter(default_limit=10, default_window=10.0, burst_multiplier=1.5)
        allowed = sum(1 for _ in range(15) if rl.check("key2"))
        assert allowed == 15  # burst = 15

    def test_gfr_degradation(self):
        rl = RateLimiter(default_limit=100, default_window=60.0)
        stage = rl.degrade_stage("key3")
        assert stage == GFRStage.STAGE_2
        stage = rl.degrade_stage("key3")
        assert stage == GFRStage.STAGE_3

    def test_gfr_improvement(self):
        rl = RateLimiter(default_limit=100, default_window=60.0)
        rl.degrade_stage("key4")
        rl.degrade_stage("key4")
        stage = rl.improve_stage("key4")
        assert stage == GFRStage.STAGE_2

    def test_limit_exceeded_raises(self):
        rl = RateLimiter(default_limit=1, default_window=60.0, burst_multiplier=1.0)
        rl.check("key5")
        with pytest.raises(LimitExceeded):
            rl.check_or_raise("key5")

    def test_usage_stats(self):
        rl = RateLimiter(default_limit=10, default_window=60.0)
        rl.check("key6")
        usage = rl.get_usage("key6")
        assert usage["current"] == 1
        assert usage["gfr_stage"] == "stage_1"

    def test_reset(self):
        rl = RateLimiter(default_limit=5, default_window=10.0, burst_multiplier=1.0)
        for _ in range(5):
            rl.check("key7")
        assert not rl.check("key7")
        rl.reset("key7")
        assert rl.check("key7")


class TestSandboxHardening:
    def test_default_profiles(self):
        sh = SandboxHardening()
        profiles = sh.list_profiles()
        assert len(profiles) >= 5  # All security levels

    def test_minimal_profile(self):
        sh = SandboxHardening()
        p = sh.get_default_profile(SecurityLevel.MINIMAL)
        assert not p.readonly_rootfs
        assert p.network_disabled

    def test_placental_profile(self):
        sh = SandboxHardening()
        p = sh.get_default_profile(SecurityLevel.PLACENTAL)
        assert p.drop_all_capabilities
        assert p.memory_limit_mb <= 256
        assert p.pids_limit <= 8

    def test_airgapped_profile(self):
        sh = SandboxHardening()
        p = sh.get_default_profile(SecurityLevel.AIRGAPPED)
        assert p.pids_limit <= 4
        assert p.memory_limit_mb <= 128

    def test_docker_args_generation(self):
        sh = SandboxHardening()
        p = sh.get_default_profile(SecurityLevel.STANDARD)
        args = sh.generate_docker_args(p)
        assert "--network=none" in args or "--read-only" in args

    def test_docker_compose_generation(self):
        sh = SandboxHardening()
        p = sh.get_default_profile(SecurityLevel.STRICT)
        compose = sh.generate_docker_compose(p, "cortex:latest")
        assert "services" in compose

    def test_validation(self):
        sh = SandboxHardening()
        p = sh.get_default_profile(SecurityLevel.PLACENTAL)
        valid, issues = sh.validate_profile(p)
        assert valid

    def test_custom_profile(self):
        sh = SandboxHardening()
        p = sh.create_profile("custom", SecurityLevel.STRICT, "Custom", 512)
        assert p.name == "custom"
        assert p.security_level == SecurityLevel.STRICT

    def test_seccomp_profile(self):
        sh = SandboxHardening()
        p = sh.get_default_profile(SecurityLevel.PLACENTAL)
        assert "defaultAction" in p.seccomp_profile
        assert "syscalls" in p.seccomp_profile
