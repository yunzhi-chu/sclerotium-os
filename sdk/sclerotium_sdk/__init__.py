"""Sclerotium OS SDK — programmatic access to the electronic lifeform.

Usage:
    from sclerotium_sdk import SclerotiumClient

    async with SclerotiumClient(api_key="sk-...") as client:
        # Chat
        response = await client.chat("Open Notepad")
        print(response.content)

        # Stream
        async for chunk in client.chat_stream("Search for Python tutorials"):
            print(chunk["data"], end="")

        # Tools
        tools = await client.list_tools()
        result = await client.call_tool("file_read", {"file_path": "test.py"})

        # Sessions
        sessions = await client.list_sessions()
        msgs = await client.load_session("abc123")
"""

from sdk.sclerotium_sdk.client import SclerotiumClient, SclerotiumConfig
from sdk.sclerotium_sdk.types import (
    ChatResponse, ToolDefinition, SessionInfo,
    StreamEvent, ToolCallResult,
)

__all__ = [
    "SclerotiumClient", "SclerotiumConfig",
    "ChatResponse", "ToolDefinition", "SessionInfo",
    "StreamEvent", "ToolCallResult",
]
