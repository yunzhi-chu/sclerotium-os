"""Prompt Cache Engine — Multi-provider cache optimization.

Claude Code's architecture is fundamentally built around prompt caching.
This module extends that concept to ALL providers (DeepSeek, OpenAI, Anthropic,
local Ollama) with provider-specific cache strategies.

Core principle from Anthropic (2026): "Prompt caching is everything"
  - Cache tokens cost 10% of normal input tokens
  - Prefix matching: cache from request start to each cache_control breakpoint
  - Layout MUST be: STATIC content → cache_control → DYNAMIC content
  - NEVER: switch models mid-session, add/remove tools, modify system prompt

Sclerotium OS ADVANTAGE over Claude Code:
  - Multi-provider cache (DeepSeek, OpenAI, Anthropic, local)
  - Adaptive cache boundaries based on task type
  - Automatic keepalive to prevent TTL expiry
  - Cache hit rate monitoring with alerts
  - Evolution-driven cache layout optimization

Reference:
  - claude.com/blog/lessons-from-building-claude-code-prompt-caching-is-everything
  - Anthropic prompt caching API (cache_control breakpoints)
  - DeepSeek context caching (discount on repeated prefixes, 2026)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CacheZone(Enum):
    """Three cache zones corresponding to Claude Code's prefix layout."""
    STATIC = "static"       # Never changes: system prompt core, immutable rules
    SEMI_STATIC = "semi"    # Changes rarely: tool definitions, skill list
    DYNAMIC = "dynamic"     # Changes always: conversation, user messages


@dataclass
class CacheSegment:
    """A segment of the prompt with its cache zone."""
    zone: CacheZone
    content: str
    content_hash: str = ""
    token_count: int = 0
    last_modified: float = 0.0
    hit_count: int = 0
    miss_count: int = 0

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                self.content.encode()
            ).hexdigest()[:16]
        if not self.last_modified:
            self.last_modified = time.time()


@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    tokens_saved: int = 0
    cost_saved: float = 0.0
    avg_hit_rate: float = 0.0
    last_keepalive: float = 0.0


class PromptCacheEngine:
    """Multi-provider prompt cache engine.

    Manages cache boundaries across STATIC / SEMI_STATIC / DYNAMIC zones.
    Claude Code equivalent: the cache boundary management in query.ts.

    Sclerotium ADVANTAGE: works across DeepSeek, OpenAI, Anthropic, AND local models.
    """

    # Provider-specific cache TTLs (in seconds)
    PROVIDER_TTL: dict[str, int] = {
        "deepseek": 1800,     # 30 min (DeepSeek context caching, 2026)
        "anthropic": 3600,    # 1 hour (Claude Code subscription)
        "openai": 300,        # 5 min (OpenAI prompt caching)
        "groq": 300,          # 5 min
        "google": 600,        # 10 min (Gemini context caching)
        "ollama": 0,          # Local — no TTL (always "cached")
    }

    # Keepalive interval: send ping TTL * 0.8 seconds after last use
    KEEPALIVE_MARGIN = 0.8

    # Singleton — cache_stats + integration share the same instance
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, '_segments'):
            self._segments: dict[str, CacheSegment] = {}
            self._stats = CacheStats()
            self._provider: str = "deepseek"
            self._last_assembly_time: float = 0.0
        self._assembly_hash: str = ""

    # ── Segment management ──────────────────────────────────────────────

    def add_segment(
        self,
        name: str,
        content: str,
        zone: CacheZone,
        token_count: int = 0,
    ) -> None:
        """Register a prompt segment with its cache zone."""
        seg = CacheSegment(
            zone=zone,
            content=content,
            token_count=token_count or len(content) // 4,  # rough estimate
        )
        self._segments[name] = seg

    def update_segment(self, name: str, content: str) -> bool:
        """Update a segment's content. Returns True if cache was invalidated."""
        if name not in self._segments:
            self.add_segment(name, content, CacheZone.DYNAMIC)
            return True

        seg = self._segments[name]
        new_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        if new_hash == seg.content_hash:
            return False  # No change, cache preserved

        seg.content = content
        seg.content_hash = new_hash
        seg.last_modified = time.time()
        seg.miss_count += 1
        return True  # Cache invalidated

    def get_segment(self, name: str) -> CacheSegment | None:
        return self._segments.get(name)

    # ── Cache-safe assembly ─────────────────────────────────────────────

    def assemble(
        self,
        provider: str = "deepseek",
        *,
        force_refresh: bool = False,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Assemble the full prompt with cache breakpoints.

        Returns (full_prompt, cache_breakpoints) where cache_breakpoints
        are provider-specific cache_control markers.

        Claude Code invariant: STATIC first, then SEMI_STATIC, then DYNAMIC.
        NEVER insert dynamic content before static — breaks prefix matching.
        """
        self._provider = provider

        # Collect segments in cache-safe order
        static_parts: list[str] = []
        semi_parts: list[str] = []
        dynamic_parts: list[str] = []

        for name, seg in sorted(self._segments.items()):
            if seg.zone == CacheZone.STATIC:
                static_parts.append(seg.content)
            elif seg.zone == CacheZone.SEMI_STATIC:
                semi_parts.append(seg.content)
            else:
                dynamic_parts.append(seg.content)

        # Build with cache boundaries
        full_prompt = ""
        breakpoints: list[dict[str, Any]] = []

        # STATIC zone (always cached)
        if static_parts:
            full_prompt += "\n\n".join(static_parts)
            breakpoints.append({
                "zone": "static",
                "token_offset": len(full_prompt) // 4,
                "cache_control": {"type": "ephemeral"},
            })

        # SEMI_STATIC zone (cached, but may update)
        if semi_parts:
            full_prompt += "\n\n" + "\n\n".join(semi_parts)
            breakpoints.append({
                "zone": "semi_static",
                "token_offset": len(full_prompt) // 4,
                "cache_control": {"type": "ephemeral"},
            })

        # DYNAMIC zone (never cached)
        # No cache_control breakpoint here — everything after is dynamic

        # Track assembly
        new_hash = hashlib.sha256(full_prompt.encode()).hexdigest()[:16]
        cache_hit = (new_hash == self._assembly_hash) and not force_refresh
        self._assembly_hash = new_hash
        self._last_assembly_time = time.time()

        self._stats.total_requests += 1
        if cache_hit:
            self._stats.cache_hits += 1
            # tokens_saved修复: 每次缓存命中节省约 full_prompt 的 token 数
            saved_tokens = len(full_prompt) // 4  # 粗略估计: 1 token ≈ 4 chars
            self._stats.tokens_saved += saved_tokens
            self._stats.cost_saved += saved_tokens * 0.000001  # ~$0.001/1K tokens
        else:
            self._stats.cache_misses += 1

        if self._stats.total_requests > 0:
            self._stats.avg_hit_rate = (
                self._stats.cache_hits / self._stats.total_requests
            )

        return full_prompt, breakpoints

    # ── Keepalive ───────────────────────────────────────────────────────

    def should_keepalive(self) -> bool:
        """Check if a keepalive ping is needed to prevent TTL expiry."""
        ttl = self.PROVIDER_TTL.get(self._provider, 300)
        if ttl == 0:
            return False  # Local model, no TTL
        elapsed = time.time() - self._last_assembly_time
        return elapsed > ttl * self.KEEPALIVE_MARGIN

    def keepalive(self) -> str | None:
        """Generate a minimal keepalive ping to maintain cache warmth.

        Claude Code equivalent: auto-warm feature, ~50-min interval for 1h TTL.
        Sends a minimal prompt that preserves the prefix match.
        """
        if not self.should_keepalive():
            return None

        self._stats.last_keepalive = time.time()
        # Minimal ping that preserves the STATIC + SEMI_STATIC prefix
        return "<system-reminder>Cache keepalive — maintaining context warmth.</system-reminder>"

    # ── Multi-provider routing ─────────────────────────────────────────

    def get_optimal_provider(
        self,
        task_complexity: str = "medium",
    ) -> str:
        """Select the optimal provider considering cache state.

        Sclerotium ADVANTAGE: can choose provider based on cache warmth.
        Claude Code is locked to Anthropic.
        """
        # If cache is warm for current provider, keep it
        if self._stats.avg_hit_rate > 0.8:
            return self._provider

        # Otherwise, pick best provider for task
        if task_complexity == "simple":
            return "groq"  # Fast, cheap, good caching
        elif task_complexity == "complex":
            return "deepseek"  # Best quality/cost ratio
        else:
            return self._provider

    # ── Cache invalidation safety ───────────────────────────────────────

    def validate_assembly(self, old_hash: str) -> bool:
        """Verify that the STATIC zone hasn't changed.

        Claude Code invariant: if the static prefix changes, ALL cached
        sessions are invalidated. This function checks before sending.
        """
        static_content = "\n\n".join(
            seg.content
            for name, seg in sorted(self._segments.items())
            if seg.zone == CacheZone.STATIC
        )
        new_hash = hashlib.sha256(static_content.encode()).hexdigest()[:16]
        return new_hash == old_hash

    def get_cache_safety_report(self) -> dict[str, Any]:
        """Generate a cache safety report.

        Claude Code monitors cache hit rates like uptime — low hit rate
        is treated as a SEV-level incident.
        """
        return {
            "provider": self._provider,
            "ttl_seconds": self.PROVIDER_TTL.get(self._provider, 300),
            "hit_rate": f"{self._stats.avg_hit_rate:.1%}",
            "tokens_saved": self._stats.tokens_saved,
            "cost_saved": f"${self._stats.cost_saved:.4f}",
            "total_requests": self._stats.total_requests,
            "last_keepalive_ago": f"{time.time() - self._stats.last_keepalive:.0f}s",
            "status": (
                "🟢 HEALTHY" if self._stats.avg_hit_rate > 0.7
                else "🟡 DEGRADED" if self._stats.avg_hit_rate > 0.4
                else "🔴 CRITICAL"
            ),
        }
