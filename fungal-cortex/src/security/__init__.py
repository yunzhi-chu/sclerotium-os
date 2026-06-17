"""Security layer — "多层皮肤屏障 + 血脑屏障" (Multi-layer Skin Barrier + Blood-Brain Barrier).

Biological Metaphor:
  人体多层防护:
    皮肤角质层(持续脱落再生, 28天周期) = JWT token轮转
    胎盘屏障(只允许必需营养通过) = Docker gVisor+seccomp
    血脑屏障(阻止>98%药物分子) = API认证+速率限制
    DNA校对(3'→5' exonuclease) = 不可篡改hash链

Phase 7 Security Modules:
  - JWT Auth: token-based API authentication with refresh rotation
  - Rate Limiter: sliding window rate limiting (GFR肾小球滤过 analog)
  - Sandbox Hardening: Docker security profiles (gVisor, seccomp, no-network)
"""

from __future__ import annotations

from src.security.jwt_auth import JWTAuthManager, TokenPair, TokenType
from src.security.rate_limiter import RateLimiter, SlidingWindow, LimitExceeded
from src.security.sandbox_hardening import SandboxHardening, SandboxProfile, SecurityLevel

__all__ = [
    "JWTAuthManager",
    "TokenPair",
    "TokenType",
    "RateLimiter",
    "SlidingWindow",
    "LimitExceeded",
    "SandboxHardening",
    "SandboxProfile",
    "SecurityLevel",
]
