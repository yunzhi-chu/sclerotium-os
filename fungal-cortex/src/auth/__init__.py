"""API key authentication middleware for Fungal Cortex v2.0.

Uses FastAPI's APIKeyHeader dependency injection pattern.
All routes except /api/health require a valid API key.
"""

from __future__ import annotations

import hashlib
import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Configured via CORTEX_API_KEY env var; if unset, auth is disabled.
_REQUIRED_KEY_HASH: str | None = None


def _init_key():
    global _REQUIRED_KEY_HASH
    key = os.environ.get("CORTEX_API_KEY", "")
    if key:
        _REQUIRED_KEY_HASH = hashlib.sha256(key.encode()).hexdigest()


_init_key()


def verify_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> bool:
    """Verify the provided API key against the configured key.

    If CORTEX_API_KEY is not set, authentication is disabled and all
    requests are allowed (development mode).
    """
    if _REQUIRED_KEY_HASH is None:
        return True
    if api_key is None:
        raise HTTPException(status_code=401, detail="X-API-Key header required")
    if hashlib.sha256(api_key.encode()).hexdigest() != _REQUIRED_KEY_HASH:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


def is_auth_enabled() -> bool:
    """Return whether API key authentication is currently enforced."""
    return _REQUIRED_KEY_HASH is not None
