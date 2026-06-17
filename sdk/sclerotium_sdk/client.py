"""Sclerotium OS SDK Client — programmatic access."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from sdk.sclerotium_sdk.types import (
    ChatResponse, SclerotiumConfig, SessionInfo,
    StreamEvent, ToolCallResult, ToolDefinition,
)

logger = logging.getLogger("sclerotium.sdk")


class SclerotiumClient:
    """Async client for Sclerotium OS HTTP API.

    Usage:
        async with SclerotiumClient(SclerotiumConfig(api_key="sk-...")) as client:
            response = await client.chat("Hello!")
            tools = await client.list_tools()
    """

    def __init__(self, config: SclerotiumConfig | None = None) -> None:
        self.config = config or SclerotiumConfig()
        self._session = None

    async def __aenter__(self) -> SclerotiumClient:
        import aiohttp
        self._session = aiohttp.ClientSession(
            base_url=self.config.base_url,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers={"Authorization": f"Bearer {self.config.api_key}"} if self.config.api_key else {},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._session:
            await self._session.close()

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context manager.")
        async with self._session.post(path, json=body) as resp:
            return await resp.json()

    async def _get(self, path: str) -> dict[str, Any]:
        if not self._session:
            raise RuntimeError("Client not connected.")
        async with self._session.get(path) as resp:
            return await resp.json()

    # ── Chat ──────────────────────────────────────────────────────────

    async def chat(self, message: str, history: list[dict] | None = None) -> ChatResponse:
        """Send a chat message."""
        data = await self._post("/chat", {"message": message, "history": history or []})
        return ChatResponse(
            content=data.get("content", ""),
            tokens_used=data.get("tokens", 0),
            model=data.get("model", ""),
        )

    async def chat_stream(self, message: str) -> AsyncIterator[StreamEvent]:
        """Stream chat response token-by-token."""
        if not self._session:
            raise RuntimeError("Client not connected.")

        async with self._session.post("/chat/stream", json={"message": message}) as resp:
            buffer = ""
            async for chunk, _ in resp.content.iter_chunks():
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            yield StreamEvent(type=data.get("type", "token"), data=data.get("data"))
                        except json.JSONDecodeError:
                            pass

    # ── Tools ─────────────────────────────────────────────────────────

    async def list_tools(self) -> list[ToolDefinition]:
        """List all available tools."""
        data = await self._get("/tools")
        return [
            ToolDefinition(
                name=t.get("name", ""),
                description=t.get("description", ""),
                parameters=t.get("parameters", {}),
                category=t.get("category", "general"),
            )
            for t in data.get("tools", [])
        ]

    async def call_tool(self, name: str, args: dict[str, Any]) -> ToolCallResult:
        """Call a tool directly."""
        data = await self._post("/chat", {
            "message": f"/tool {name}",
            "tool_name": name,
            "tool_args": args,
        })
        return ToolCallResult(
            tool_name=name,
            result=data,
            success="error" not in str(data).lower(),
        )

    # ── Sessions ──────────────────────────────────────────────────────

    async def list_sessions(self) -> list[SessionInfo]:
        data = await self._get("/sessions")
        return [
            SessionInfo(
                session_id=s.get("id", ""),
                title=s.get("title", ""),
                model=s.get("model", ""),
                message_count=s.get("message_count", 0),
                token_count=s.get("token_count", 0),
            )
            for s in data.get("sessions", [])
        ]

    # ── Health ────────────────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        return await self._get("/health")
