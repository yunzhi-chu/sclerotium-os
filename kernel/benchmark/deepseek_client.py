"""DeepSeek API Client — LLM driver for Sclerotium OS benchmarks.

Connects to DeepSeek API for real LLM-driven evaluation tasks.
Uses deepseek-v4-pro for maximum coding capability.

API: DeepSeek OpenAI-compatible endpoint
Key: sk-9a10241fc127458f8d552c0a3f88b1f7
Model: deepseek-v4-pro (latest and most capable)
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class LLMResponse:
    """Response from DeepSeek API."""
    content: str
    model: str
    tokens_prompt: int = 0
    tokens_completion: int = 0
    duration_ms: float = 0
    finish_reason: str = ""
    error: str = ""


class DeepSeekClient:
    """OpenAI-compatible DeepSeek API client.

    Usage:
        client = DeepSeekClient()
        resp = await client.chat("Write a Python function to sort a list")
        print(resp.content)
    """

    BASE_URL = "https://api.deepseek.com/v1"
    API_KEY = "sk-9a10241fc127458f8d552c0a3f88b1f7"
    MODEL = "deepseek-v4-pro"

    def __init__(self, model: str | None = None) -> None:
        self._model = model or self.MODEL
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(120.0),
        )
        self._request_count = 0
        self._total_tokens = 0
        self._total_duration = 0.0
        self._errors = 0

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "model": self._model,
            "requests": self._request_count,
            "total_tokens": self._total_tokens,
            "total_duration_s": round(self._total_duration, 1),
            "errors": self._errors,
        }

    async def chat(
        self,
        prompt: str,
        system: str = "You are an expert software engineer. Write clean, correct, efficient code.",
        temperature: float = 0.2,
        top_p: float = 0.8,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a chat completion request."""
        self._request_count += 1
        t0 = time.monotonic()

        try:
            resp = await self._client.post(
                "/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens,
                },
            )
            data = resp.json()

            if resp.status_code != 200:
                self._errors += 1
                return LLMResponse(
                    content="",
                    model=self._model,
                    error=data.get("error", {}).get("message", f"HTTP {resp.status_code}"),
                )

            choice = data.get("choices", [{}])[0]
            usage = data.get("usage", {})

            tokens_prompt = usage.get("prompt_tokens", 0)
            tokens_completion = usage.get("completion_tokens", 0)
            self._total_tokens += tokens_prompt + tokens_completion

            duration = (time.monotonic() - t0) * 1000
            self._total_duration += duration / 1000

            return LLMResponse(
                content=choice.get("message", {}).get("content", ""),
                model=data.get("model", self._model),
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                duration_ms=duration,
                finish_reason=choice.get("finish_reason", ""),
            )

        except Exception as e:
            self._errors += 1
            return LLMResponse(
                content="",
                model=self._model,
                error=str(e),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    async def chat_batch(
        self,
        prompts: list[str],
        system: str = "You are an expert software engineer.",
        temperature: float = 0.2,
        top_p: float = 0.8,
        max_tokens: int = 4096,
        concurrency: int = 5,
    ) -> list[LLMResponse]:
        """Send multiple chat requests with concurrency control."""
        semaphore = asyncio.Semaphore(concurrency)

        async def _bounded(prompt: str) -> LLMResponse:
            async with semaphore:
                return await self.chat(prompt, system=system, temperature=temperature, top_p=top_p, max_tokens=max_tokens)

        tasks = [_bounded(p) for p in prompts]
        return await asyncio.gather(*tasks)

    async def close(self) -> None:
        await self._client.aclose()
