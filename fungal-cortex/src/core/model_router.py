"""LLM model router — adaptive routing between deep/quick/fallback models."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.config import LLMConfig, get_config
from src.utils.logging import CortexLogger


class CognitiveDepth(Enum):
    """Maps to L1-L6 cognitive hierarchy."""

    L1_FAST = 1         # Quick pattern match (~200ms)
    L2_DECIDE = 2        # Binary decision
    L3_DEBATE = 3        # Multi-perspective analysis
    L4_RESEARCH = 4      # Multi-step reasoning
    L5_PLAN = 5          # Long-horizon planning
    L6_META = 6          # Self-reflective metacognition


@dataclass
class ModelResponse:
    """Structured response from any model."""

    content: str
    model: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelRouter:
    """Routes requests to the appropriate LLM model based on cognitive depth.

    - L1-L2: quick_think (fast, cheap) for simple pattern matching
    - L3-L4: deep_think (balanced) for analysis
    - L5-L6: deep_think (thorough) for planning and metacognition
    - Error/retry: fallback model
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or get_config().llm
        self._logger = CortexLogger("model_router")
        self._stats: dict[str, dict[str, Any]] = {
            "deep": {"calls": 0, "total_tokens": 0, "total_ms": 0.0, "errors": 0},
            "quick": {"calls": 0, "total_tokens": 0, "total_ms": 0.0, "errors": 0},
            "fallback": {"calls": 0, "total_tokens": 0, "total_ms": 0.0, "errors": 0},
        }

    def select_model(self, depth: CognitiveDepth) -> str:
        """Select the appropriate model for the given cognitive depth."""
        if depth in (CognitiveDepth.L1_FAST, CognitiveDepth.L2_DECIDE):
            return self.config.quick_think_model
        return self.config.deep_think_model

    def select_temperature(self, depth: CognitiveDepth) -> float:
        """Select temperature based on depth — lower for deep thinking."""
        if depth in (CognitiveDepth.L1_FAST, CognitiveDepth.L2_DECIDE):
            return self.config.temperature_quick
        return self.config.temperature_deep

    # ── Optimized token limits per cognitive depth (2026 tuned) ─────
    DEPTH_TOKEN_BUDGET: dict[CognitiveDepth, int] = {
        CognitiveDepth.L1_FAST: 256,
        CognitiveDepth.L2_DECIDE: 512,
        CognitiveDepth.L3_DEBATE: 1024,
        CognitiveDepth.L4_RESEARCH: 1536,
        CognitiveDepth.L5_PLAN: 2048,
        CognitiveDepth.L6_META: 2048,
    }

    def select_max_tokens(self, depth: CognitiveDepth) -> int:
        """Select token budget based on depth with optimized limits."""
        # Use optimized per-depth limits if available, fall back to config
        if depth in self.DEPTH_TOKEN_BUDGET:
            return self.DEPTH_TOKEN_BUDGET[depth]
        if depth in (CognitiveDepth.L1_FAST, CognitiveDepth.L2_DECIDE):
            return self.config.max_tokens_quick
        return self.config.max_tokens_deep

    def build_prompt(
        self, depth: CognitiveDepth, system: str, user: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Build a complete prompt envelope with depth-appropriate instructions."""
        depth_instructions = {
            CognitiveDepth.L1_FAST: "Respond with only the answer. No explanation needed.",
            CognitiveDepth.L2_DECIDE: "State your decision with one sentence of reasoning.",
            CognitiveDepth.L3_DEBATE: "Analyze from multiple perspectives. List pros and cons.",
            CognitiveDepth.L4_RESEARCH: "Reason step by step. Cite evidence for each claim.",
            CognitiveDepth.L5_PLAN: "Create a structured plan with milestones, dependencies, and risks.",
            CognitiveDepth.L6_META: "Reflect on your own reasoning process. Identify assumptions, gaps, and alternative approaches.",
        }
        return {
            "model": self.select_model(depth),
            "temperature": self.select_temperature(depth),
            "max_tokens": self.select_max_tokens(depth),
            "system": system,
            "user": user + "\n\n" + depth_instructions[depth],
            "context": context or {},
        }

    async def call(self, depth: CognitiveDepth, system: str, user: str, context: dict[str, Any] | None = None) -> ModelResponse:
        """Execute an LLM call with automatic fallback on error.

        This is the abstract interface. Concrete implementations inject the
        actual API client (DeepSeek, OpenAI, etc.) via dependency injection.
        """
        model = self.select_model(depth)
        tier = self._model_tier(model)
        t0 = time.perf_counter()

        try:
            response = await self._execute_call(depth, system, user, context)
            elapsed = (time.perf_counter() - t0) * 1000
            self._stats[tier]["calls"] += 1
            self._stats[tier]["total_tokens"] += response.tokens_used
            self._stats[tier]["total_ms"] += elapsed
            self._logger.info("model_call_success", model=model, depth=depth.name, latency_ms=int(elapsed), tokens=response.tokens_used)
            return response
        except Exception as exc:
            self._stats[tier]["errors"] += 1
            self._logger.error("model_call_failed", model=model, error=str(exc))
            if model != self.config.fallback_model:
                self._logger.info("model_fallback", from_model=model, to_model=self.config.fallback_model)
                return await self._call_fallback(depth, system, user, context)
            raise

    async def _execute_call(self, depth: CognitiveDepth, system: str, user: str, context: dict[str, Any] | None = None) -> ModelResponse:
        """Actual API call — override in concrete implementation."""
        raise NotImplementedError("Inject a concrete LLM client via subclass or DI")

    async def _call_fallback(self, depth: CognitiveDepth, system: str, user: str, context: dict[str, Any] | None = None) -> ModelResponse:
        """Fallback to the designated fallback model."""
        t0 = time.perf_counter()
        try:
            # Re-execute with fallback model (implementation injects actual client)
            response = await self._execute_fallback(depth, system, user, context)
            elapsed = (time.perf_counter() - t0) * 1000
            self._stats["fallback"]["calls"] += 1
            self._stats["fallback"]["total_tokens"] += response.tokens_used
            self._stats["fallback"]["total_ms"] += elapsed
            return response
        except Exception:
            self._logger.error("fallback_failed")
            raise

    async def _execute_fallback(self, depth: CognitiveDepth, system: str, user: str, context: dict[str, Any] | None = None) -> ModelResponse:
        raise NotImplementedError("Inject a concrete LLM client via subclass or DI")

    def _model_tier(self, model: str) -> str:
        if model == self.config.deep_think_model:
            return "deep"
        if model == self.config.quick_think_model:
            return "quick"
        return "fallback"

    @property
    def stats(self) -> dict[str, Any]:
        return {
            tier: {
                **data,
                "avg_latency_ms": data["total_ms"] / data["calls"] if data["calls"] else 0,
                "avg_tokens": data["total_tokens"] / data["calls"] if data["calls"] else 0,
            }
            for tier, data in self._stats.items()
        }


class HttpModelRouter(ModelRouter):
    """Concrete router that calls real LLM HTTP APIs with retry logic.

    Uses httpx for async HTTP with exponential backoff on failures.
    Set environment variables:
        LLM_API_KEY — API key for the LLM service
        LLM_API_BASE — Base URL for the LLM API
    """

    def __init__(self, config: LLMConfig | None = None, max_retries: int = 3, base_delay: float = 1.0):
        super().__init__(config)
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._api_key = __import__("os").environ.get("LLM_API_KEY", "")
        self._api_base = __import__("os").environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")

    async def _execute_call(
        self, depth: CognitiveDepth, system: str, user: str,
        context: dict[str, Any] | None = None,
    ) -> ModelResponse:
        """Real HTTP API call with retry and exponential backoff."""
        return await self._http_call(
            self.select_model(depth), system, user,
            temperature=self.select_temperature(depth),
            max_tokens=self.select_max_tokens(depth),
        )

    async def _execute_fallback(
        self, depth: CognitiveDepth, system: str, user: str,
        context: dict[str, Any] | None = None,
    ) -> ModelResponse:
        """Fallback HTTP call using the fallback model."""
        return await self._http_call(
            self.config.fallback_model, system, user,
            temperature=0.3,  # Conservative for fallback
            max_tokens=self.config.max_tokens_deep,
        )

    async def _http_call(
        self, model: str, system: str, user: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ModelResponse:
        import asyncio as _asyncio
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx is required for HttpModelRouter. Install with: pip install httpx")

        if not self._api_key:
            self._logger.warn("llm_api_key_not_set", message="LLM_API_KEY not configured — using local fallback mode")
            return ModelResponse(
                content=f"[Local Fallback] Analysis for: {user[:200]}",
                model="fallback/local",
                tokens_used=0,
                latency_ms=0.0,
                finish_reason="fallback_no_api_key",
                metadata={"source": "local_fallback", "reason": "LLM_API_KEY not set"},
            )

        url = f"{self._api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error = ""
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        choice = data["choices"][0]
                        return ModelResponse(
                            content=choice["message"]["content"],
                            model=model,
                            tokens_used=data.get("usage", {}).get("total_tokens", 0),
                            finish_reason=choice.get("finish_reason", "stop"),
                            latency_ms=0,
                        )
                    elif resp.status_code == 429:
                        delay = self._base_delay * (2 ** attempt)
                        self._logger.warn("llm_rate_limited", attempt=attempt, delay=delay)
                        await _asyncio.sleep(delay)
                    elif resp.status_code >= 500:
                        delay = self._base_delay * (2 ** attempt)
                        await _asyncio.sleep(delay)
                    else:
                        last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                        break
            except Exception as e:
                last_error = str(e)
                if attempt < self._max_retries - 1:
                    delay = self._base_delay * (2 ** attempt)
                    await _asyncio.sleep(delay)

        raise RuntimeError(f"LLM API call failed after {self._max_retries} retries: {last_error}")
