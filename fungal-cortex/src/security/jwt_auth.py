"""Phase 7.2a: JWTAuthManager — "皮肤角质层"(Stratum Corneum) JWT认证.

Biological Metaphor:
  皮肤角质层——持续脱落再生(28天周期):
    角质细胞(老化的)不断从表面脱落 → JWT短期过期(15min)
    基底层干细胞不断分裂产生新角质细胞 → refresh token轮转(7天)
    皮脂腺分泌油脂维持屏障完整性 → token签名验证
    破损皮肤→立即修复(血小板+纤维蛋白) → token泄露→立即revoke

  多层认证:
    1. Access Token (15min): 角质层——频繁更换, 最小权限
    2. Refresh Token (7d): 基底层——用于生成新的access token
    3. API Key (永久): 皮脂腺——基础身份识别

Reference:
  Proksch et al. (2008), "The skin barrier", JDDG 6:410-416;
  RFC 7519 (JWT); OAuth 2.0 Refresh Token Rotation
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


@dataclass
class TokenPair:
    """Access + Refresh token pair — like epidermis + basal layer."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes
    refresh_expires_in: int = 604800  # 7 days
    issued_at: float = field(default_factory=time.time)


@dataclass
class TokenClaims:
    """Decoded JWT claims — like skin cell metadata."""

    sub: str  # Subject (user/agent ID)
    iss: str = "fungal-cortex"  # Issuer
    aud: str = "cortex-api"  # Audience
    iat: float = field(default_factory=time.time)
    exp: float = 0.0
    jti: str = ""  # JWT ID (unique)
    token_type: str = "access"
    scopes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class JWTAuthManager:
    """JWT token lifecycle manager — like skin barrier maintenance.

    Config:
      - access_ttl: access token lifetime (default 15min — keratinocyte lifespan)
      - refresh_ttl: refresh token lifetime (default 7d — epidermal turnover)
      - secret_key: HMAC signing key (should come from env var)
      - token_rotation: whether to issue new refresh token on each use
    """

    def __init__(
        self,
        secret_key: str | None = None,
        access_ttl: int = 900,
        refresh_ttl: int = 604800,
        issuer: str = "fungal-cortex",
        audience: str = "cortex-api",
        token_rotation: bool = True,
    ) -> None:
        self._secret = secret_key or self._generate_secret()
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._issuer = issuer
        self._audience = audience
        self._token_rotation = token_rotation

        # Revocation registry (like scar tissue registry)
        self._revoked_tokens: dict[str, float] = {}  # {jti: revoked_at}
        self._revoked_subjects: dict[str, float] = {}  # {sub: revoked_at}

    # ── Token Creation ──────────────────────────────────────────────

    def create_token_pair(self, subject: str,
                          scopes: list[str] | None = None,
                          metadata: dict[str, Any] | None = None) -> TokenPair:
        """Create a new access + refresh token pair.

        Like basal stem cells generating a new epidermal layer.
        """
        now = time.time()

        # Access token (short-lived — like keratinocyte)
        access_claims = self._build_claims(
            subject, TokenType.ACCESS, now,
            ttl=self._access_ttl, scopes=scopes or [], metadata=metadata or {},
        )
        access_token = self._encode_token(access_claims)

        # Refresh token (long-lived — like basal stem cell)
        refresh_claims = self._build_claims(
            subject, TokenType.REFRESH, now,
            ttl=self._refresh_ttl, scopes=["refresh"], metadata={},
        )
        refresh_token = self._encode_token(refresh_claims)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._access_ttl,
            refresh_expires_in=self._refresh_ttl,
            issued_at=now,
        )

    def refresh_access(self, refresh_token: str) -> TokenPair | None:
        """Use a refresh token to get a new access token.

        Like basal stem cells dividing to replace shed keratinocytes.
        """
        claims = self.verify_token(refresh_token)
        if claims is None:
            return None
        if claims.token_type != "refresh":
            return None

        # Revoke old refresh token if rotation enabled
        if self._token_rotation:
            self.revoke_token(claims.jti)

        # Issue new pair
        return self.create_token_pair(
            subject=claims.sub,
            scopes=claims.scopes,
            metadata=claims.metadata,
        )

    # ── Token Verification ──────────────────────────────────────────

    def verify_token(self, token: str) -> TokenClaims | None:
        """Verify a token's signature and claims.

        Like the immune system checking if a cell's MHC-I is intact.
        """
        try:
            claims = self._decode_token(token)
        except Exception:
            return None

        # Check expiration
        if claims.exp < time.time():
            return None

        # Check issuer
        if claims.iss != self._issuer:
            return None

        # Check revocation
        if claims.jti in self._revoked_tokens:
            return None
        if claims.sub in self._revoked_subjects:
            # Subject revoked — reject all tokens regardless of issue time.
            # Like complete epidermal shedding: all keratinocytes from this
            # generation are invalid, no matter when they were produced.
            return None

        return claims

    def verify_api_key(self, api_key: str, expected_hash: str) -> bool:
        """Verify an API key against its stored hash.

        Like the skin's acid mantle checking pH balance.
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return hmac.compare_digest(key_hash, expected_hash)

    # ── Token Revocation ────────────────────────────────────────────

    def revoke_token(self, jti: str) -> None:
        """Revoke a specific token by JWT ID.

        Like removing a damaged keratinocyte.
        """
        self._revoked_tokens[jti] = time.time()
        # Auto-clean old revocations (>30 days)
        cutoff = time.time() - 2592000
        self._revoked_tokens = {
            k: v for k, v in self._revoked_tokens.items() if v > cutoff
        }

    def revoke_subject(self, subject: str) -> None:
        """Revoke all tokens for a subject.

        Like complete epidermal shedding (desquamation).
        """
        self._revoked_subjects[subject] = time.time()

    def is_revoked(self, jti: str) -> bool:
        return jti in self._revoked_tokens

    # ── Internal Token Encoding/Decoding ────────────────────────────

    def _build_claims(self, subject: str, token_type: TokenType,
                      now: float, ttl: int, scopes: list[str],
                      metadata: dict[str, Any]) -> TokenClaims:
        jti = hashlib.md5(f"{subject}|{now}|{token_type.value}".encode()).hexdigest()[:16]
        return TokenClaims(
            sub=subject,
            iss=self._issuer,
            aud=self._audience,
            iat=now,
            exp=now + ttl,
            jti=jti,
            token_type=token_type.value,
            scopes=scopes,
            metadata=metadata,
        )

    def _encode_token(self, claims: TokenClaims) -> str:
        """Encode claims to a JWT-like token (simplified — no PyJWT dependency).

        Format: base64(header).base64(payload).hmac_signature
        """
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": claims.sub,
            "iss": claims.iss,
            "aud": claims.aud,
            "iat": claims.iat,
            "exp": claims.exp,
            "jti": claims.jti,
            "token_type": claims.token_type,
            "scopes": claims.scopes,
        }

        header_b64 = self._b64_encode(json.dumps(header, separators=(",", ":")))
        payload_b64 = self._b64_encode(json.dumps(payload, separators=(",", ":")))
        signing_input = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            self._secret.encode(), signing_input.encode(), hashlib.sha256,
        ).hexdigest()[:32]

        return f"{header_b64}.{payload_b64}.{signature}"

    def _decode_token(self, token: str) -> TokenClaims:
        """Decode and verify token signature."""
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        header_b64, payload_b64, signature = parts
        signing_input = f"{header_b64}.{payload_b64}"

        # Verify signature
        expected_sig = hmac.new(
            self._secret.encode(), signing_input.encode(), hashlib.sha256,
        ).hexdigest()[:32]
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid signature")

        payload = json.loads(self._b64_decode(payload_b64))
        return TokenClaims(
            sub=payload["sub"],
            iss=payload["iss"],
            aud=payload.get("aud", ""),
            iat=payload["iat"],
            exp=payload["exp"],
            jti=payload.get("jti", ""),
            token_type=payload.get("token_type", "access"),
            scopes=payload.get("scopes", []),
        )

    @staticmethod
    def _b64_encode(data: str) -> str:
        import base64
        return base64.urlsafe_b64encode(data.encode()).rstrip(b"=").decode()

    @staticmethod
    def _b64_decode(data: str) -> str:
        import base64
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data).decode()

    @staticmethod
    def _generate_secret() -> str:
        return hashlib.sha256(str(time.time()).encode()).hexdigest()

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "revoked_tokens": len(self._revoked_tokens),
            "revoked_subjects": len(self._revoked_subjects),
            "access_ttl": self._access_ttl,
            "refresh_ttl": self._refresh_ttl,
            "token_rotation": self._token_rotation,
        }
