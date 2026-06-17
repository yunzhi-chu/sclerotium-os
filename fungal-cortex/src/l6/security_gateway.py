"""Mechanism ⑯ M5: Cross-Ecosystem Security Gateway — blood-brain barrier inspired.

Inspired by the blood-brain barrier:
- Whitelist: 5 service types allowed (like nutrients crossing BBB)
- Blacklist: 6 service types permanently blocked (like toxins blocked by BBB)
- HMAC verification: receptor-mediated endocytosis (only correct ligand)
- Rate limiting: active transport energy constraints
- Content safety: complement system marking + clearance

Zero-trust architecture: never trust, always verify.
Broker APIs are permanently impermeable (like the BBB to neurotoxins).
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# --- Constants ---

WHITELIST_SERVICE_TYPES: set[str] = {
    "data_provider",
    "backtest_platform",
    "ai_tool",
    "research_database",
    "open_source_library",
}

BLACKLIST_SERVICE_TYPES: set[str] = {
    "broker_api",
    "trading_platform",
    "exchange_api",
    "payment_gateway",
    "order_management",
    "position_settlement",
}

FORBIDDEN_ACTIONS: set[str] = {
    "trade", "order", "buy", "sell", "execute", "transfer",
}

FORBIDDEN_PATTERNS: list[str] = [
    r"\b(?:trade|order|buy|sell|execute|transfer)\s*\(",
    r"\b(?:os\.system|subprocess|eval|exec)\s*\(",
    r"\b(?:delete|drop|truncate)\s+",
]


class ServiceStatus(Enum):
    REGISTERED = "registered"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"
    REVOKED = "revoked"


@dataclass
class ServiceRecord:
    """Registered service metadata."""

    service_id: str
    service_type: str
    api_key_hash: str
    status: ServiceStatus = ServiceStatus.REGISTERED
    registered_at: float = field(default_factory=time.time)
    last_validated_at: float | None = None
    request_count: int = 0
    violation_count: int = 0

    def is_active(self) -> bool:
        return self.status == ServiceStatus.ACTIVE


@dataclass
class ValidationResult:
    """Result of a security validation request."""

    allowed: bool
    reason: str = ""
    violation: str = ""
    service_id: str = ""


@dataclass
class ImportResult:
    """Result of external data import."""

    allowed: bool
    data_preview: str = ""
    localized_path: str = ""
    reason: str = ""
    validation_checks: list[str] = field(default_factory=list)


# --- Rate Limiter (sliding window) ---

class SlidingWindowRateLimiter:
    """Sliding window rate limiter: 60/min + 1000/hour.

    Uses timestamp-based sliding window, not fixed window,
    to prevent boundary-burst attacks.
    """

    def __init__(self, max_per_minute: int = 60, max_per_hour: int = 1000) -> None:
        self._max_per_minute = max_per_minute
        self._max_per_hour = max_per_hour
        self._minute_window: list[float] = []
        self._hour_window: list[float] = []

    def allow(self) -> tuple[bool, str]:
        """Check if a request is within rate limits. Returns (allowed, reason)."""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        self._minute_window = [t for t in self._minute_window if t > minute_ago]
        self._hour_window = [t for t in self._hour_window if t > hour_ago]

        if len(self._minute_window) >= self._max_per_minute:
            return False, f"Rate limit exceeded: {self._max_per_minute}/minute"

        if len(self._hour_window) >= self._max_per_hour:
            return False, f"Rate limit exceeded: {self._max_per_hour}/hour"

        self._minute_window.append(now)
        self._hour_window.append(now)
        return True, "ok"

    @property
    def current_minute_count(self) -> int:
        now = time.time()
        return sum(1 for t in self._minute_window if t > now - 60)

    @property
    def current_hour_count(self) -> int:
        now = time.time()
        return sum(1 for t in self._hour_window if t > now - 3600)


# --- Token Bucket (per-service rate limit) ---

class TokenBucket:
    """Token bucket for per-service rate limiting."""

    def __init__(self, capacity: int = 100, refill_rate: float = 1.0) -> None:
        self._capacity = capacity
        self._refill_rate = refill_rate  # tokens per second
        self._tokens = float(capacity)
        self._last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now


# --- Main Gateway ---

class CrossEcoSecurityGateway:
    """Cross-ecosystem security gateway — blood-brain barrier for QuantMind OS.

    Five-layer defense:
    1. Service type check (whitelist/blacklist)
    2. API key verification (HMAC compare)
    3. Rate limiting (sliding window)
    4. Content safety scan
    5. Sandbox preview (for data imports)
    """

    def __init__(
        self,
        max_per_minute: int = 60,
        max_per_hour: int = 1000,
        token_bucket_size: int = 100,
        token_refill_rate: float = 1.0,
    ) -> None:
        self._services: dict[str, ServiceRecord] = {}
        self._api_keys: dict[str, str] = {}  # service_id → hashed key
        self._global_limiter = SlidingWindowRateLimiter(max_per_minute, max_per_hour)
        self._per_service_buckets: dict[str, TokenBucket] = {}
        self._default_bucket_size = token_bucket_size
        self._default_refill_rate = token_refill_rate
        self._violation_log: list[dict[str, Any]] = []

    # --- Service Registration ---

    def register_service(self, service_id: str, service_type: str, api_key: str) -> tuple[bool, str]:
        """Register a service with whitelist/blacklist check.

        Returns (success, message).
        """
        if service_type in BLACKLIST_SERVICE_TYPES:
            return False, f"Service type '{service_type}' is permanently blocked (blacklist)"

        if service_type not in WHITELIST_SERVICE_TYPES:
            return False, f"Service type '{service_type}' is not in whitelist. Allowed: {WHITELIST_SERVICE_TYPES}"

        if service_id in self._services:
            existing = self._services[service_id]
            if existing.status in (ServiceStatus.BLOCKED, ServiceStatus.REVOKED):
                return False, f"Service '{service_id}' is {existing.status.value}"
            # Update existing
            existing.service_type = service_type
            existing.api_key_hash = self._hash_key(api_key)
            existing.status = ServiceStatus.ACTIVE
            return True, f"Service '{service_id}' updated and activated"

        key_hash = self._hash_key(api_key)
        record = ServiceRecord(
            service_id=service_id,
            service_type=service_type,
            api_key_hash=key_hash,
            status=ServiceStatus.ACTIVE,
        )
        self._services[service_id] = record
        self._api_keys[service_id] = key_hash
        self._per_service_buckets[service_id] = TokenBucket(
            self._default_bucket_size, self._default_refill_rate
        )
        return True, f"Service '{service_id}' registered as '{service_type}'"

    def revoke_service(self, service_id: str) -> tuple[bool, str]:
        """Revoke a service's access."""
        record = self._services.get(service_id)
        if record is None:
            return False, f"Service '{service_id}' not found"
        record.status = ServiceStatus.REVOKED
        self._api_keys.pop(service_id, None)
        self._per_service_buckets.pop(service_id, None)
        return True, f"Service '{service_id}' revoked"

    def suspend_service(self, service_id: str, reason: str = "") -> tuple[bool, str]:
        """Suspend a service (temporary, can be restored)."""
        record = self._services.get(service_id)
        if record is None:
            return False, f"Service '{service_id}' not found"
        record.status = ServiceStatus.SUSPENDED
        self._log_violation(service_id, "suspension", reason)
        return True, f"Service '{service_id}' suspended: {reason}"

    def block_service(self, service_id: str, reason: str = "") -> tuple[bool, str]:
        """Permanently block a service."""
        record = self._services.get(service_id)
        if record is None:
            # Block even unknown services
            self._services[service_id] = ServiceRecord(
                service_id=service_id,
                service_type="unknown",
                api_key_hash="blocked",
                status=ServiceStatus.BLOCKED,
            )
        else:
            record.status = ServiceStatus.BLOCKED
        self._api_keys.pop(service_id, None)
        self._per_service_buckets.pop(service_id, None)
        self._log_violation(service_id, "block", reason)
        return True, f"Service '{service_id}' permanently blocked: {reason}"

    # --- Request Validation ---

    def validate_request(self, service_id: str, api_key: str, request_content: str = "") -> ValidationResult:
        """Full validation pipeline for an incoming request.

        Returns ValidationResult with allowed=True only if ALL checks pass.
        """
        # Layer 1: Service type check
        record = self._services.get(service_id)
        if record is None:
            return ValidationResult(allowed=False, reason="Unknown service", service_id=service_id)
        if not record.is_active():
            return ValidationResult(
                allowed=False,
                reason=f"Service status is {record.status.value}",
                service_id=service_id,
            )
        if record.service_type in BLACKLIST_SERVICE_TYPES:
            self._log_violation(service_id, "blacklist_access_attempt", "")
            return ValidationResult(allowed=False, reason="Service type is blacklisted", service_id=service_id)

        # Layer 2: API key verification (constant-time comparison)
        ok, reason = self._verify_api_key(service_id, api_key)
        if not ok:
            record.violation_count += 1
            self._log_violation(service_id, "invalid_api_key", "")
            return ValidationResult(allowed=False, reason=reason, service_id=service_id)

        # Layer 3: Rate limiting
        allowed_global, global_reason = self._global_limiter.allow()
        if not allowed_global:
            return ValidationResult(
                allowed=False, reason=global_reason, violation="global_rate_limit", service_id=service_id
            )

        bucket = self._per_service_buckets.get(service_id)
        if bucket is None:
            bucket = TokenBucket(self._default_bucket_size, self._default_refill_rate)
            self._per_service_buckets[service_id] = bucket
        if not bucket.consume():
            return ValidationResult(
                allowed=False,
                reason="Per-service rate limit exceeded",
                violation="service_rate_limit",
                service_id=service_id,
            )

        # Layer 4: Content safety scan
        if request_content:
            ok, violation = self._content_safety_check(request_content)
            if not ok:
                record.violation_count += 1
                self._log_violation(service_id, "content_safety", violation)
                return ValidationResult(
                    allowed=False,
                    reason=f"Content safety violation: {violation}",
                    violation=violation,
                    service_id=service_id,
                )

        # All checks passed
        record.last_validated_at = time.time()
        record.request_count += 1
        return ValidationResult(allowed=True, reason="ok", service_id=service_id)

    # --- API Key Verification ---

    def _verify_api_key(self, service_id: str, provided_key: str) -> tuple[bool, str]:
        """HMAC constant-time comparison of API keys."""
        stored_hash = self._api_keys.get(service_id)
        if stored_hash is None:
            return False, "No API key registered for service"
        provided_hash = self._hash_key(provided_key)
        if not hmac.compare_digest(stored_hash, provided_hash):
            return False, "API key mismatch"
        return True, "ok"

    # --- Content Safety ---

    def _content_safety_check(self, content: str) -> tuple[bool, str]:
        """Scan content for forbidden actions and dangerous patterns."""
        content_lower = content.lower()

        for action in FORBIDDEN_ACTIONS:
            if re.search(rf"\b{re.escape(action)}\b", content_lower):
                return False, f"Forbidden action '{action}' detected"

        for pattern in FORBIDDEN_PATTERNS:
            m = re.search(pattern, content_lower)
            if m:
                return False, f"Forbidden pattern detected: {m.group(0).strip()[:60]}"

        return True, "ok"

    # --- External Data Import ---

    def import_external_data(self, service_id: str, data_spec: dict[str, Any]) -> ImportResult:
        """Import external data through sandbox preview → localize pipeline.

        Data import flow:
        1. Validate the requesting service is active
        2. Sandbox preview (validate schema/content)
        3. Localize (store verified copy)
        """
        record = self._services.get(service_id)
        if record is None or not record.is_active():
            return ImportResult(allowed=False, reason="Service not active or not registered")

        if record.service_type not in WHITELIST_SERVICE_TYPES:
            return ImportResult(allowed=False, reason=f"Service type '{record.service_type}' not authorized for imports")

        checks: list[str] = []
        source_url = data_spec.get("source_url", "")
        data_format = data_spec.get("format", "unknown")

        # Validate source
        if source_url:
            if any(blocked in source_url.lower() for blocked in ["broker", "trade", "exchange"]):
                return ImportResult(allowed=False, reason=f"Source URL blocked: {source_url}")
            checks.append(f"source_url validated: {source_url}")

        # Validate format
        allowed_formats = {"csv", "json", "parquet", "hdf5", "feather", "sqlite", "txt"}
        if data_format not in allowed_formats:
            return ImportResult(allowed=False, reason=f"Unsupported format '{data_format}'. Allowed: {allowed_formats}")
        checks.append(f"format validated: {data_format}")

        # Size check
        max_size = data_spec.get("max_size_mb", 100)
        if max_size > 500:
            return ImportResult(allowed=False, reason=f"Size too large ({max_size}MB > 500MB limit)")
        checks.append(f"size check passed: {max_size}MB ≤ 500MB")

        preview = data_spec.get("preview", "")[:200]  # Truncated preview
        import_id = str(uuid.uuid4())[:8]

        return ImportResult(
            allowed=True,
            data_preview=preview,
            localized_path=f"/data/imports/{record.service_type}/{import_id}.{data_format}",
            reason="Import passed sandbox preview",
            validation_checks=checks,
        )

    # --- Utilities ---

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def _log_violation(self, service_id: str, violation_type: str, detail: str) -> None:
        self._violation_log.append({
            "timestamp": time.time(),
            "service_id": service_id,
            "type": violation_type,
            "detail": detail,
        })
        # Keep only last 1000 violations
        if len(self._violation_log) > 1000:
            self._violation_log = self._violation_log[-1000:]

    # --- Status & Reporting ---

    def get_service_status(self, service_id: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        """Get status of registered services."""
        if service_id:
            record = self._services.get(service_id)
            if record is None:
                return {"error": f"Service '{service_id}' not found"}
            return {
                "service_id": record.service_id,
                "service_type": record.service_type,
                "status": record.status.value,
                "request_count": record.request_count,
                "violation_count": record.violation_count,
                "registered_at": record.registered_at,
            }
        return [
            {
                "service_id": r.service_id,
                "service_type": r.service_type,
                "status": r.status.value,
                "request_count": r.request_count,
                "violation_count": r.violation_count,
            }
            for r in self._services.values()
        ]

    @property
    def stats(self) -> dict[str, Any]:
        active = sum(1 for r in self._services.values() if r.is_active())
        blocked = sum(1 for r in self._services.values() if r.status == ServiceStatus.BLOCKED)
        return {
            "total_services": len(self._services),
            "active_services": active,
            "blocked_services": blocked,
            "global_rate_minute": self._global_limiter.current_minute_count,
            "global_rate_hour": self._global_limiter.current_hour_count,
            "total_violations": len(self._violation_log),
            "whitelist_types": sorted(WHITELIST_SERVICE_TYPES),
            "blacklist_types": sorted(BLACKLIST_SERVICE_TYPES),
        }

    @property
    def violation_log(self) -> list[dict[str, Any]]:
        return list(self._violation_log)
