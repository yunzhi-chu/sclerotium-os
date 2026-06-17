"""Tool Use Widget — Claude Code-style expandable tool call/result display.

Replicates Claude Code's tool-call rendering:
  - Expandable/collapsible tool header
  - Syntax-highlighted arguments
  - Color-coded results (success=green, error=red)
  - Incremental output for long-running tools

Claude Code equivalent: ToolCallCard.tsx, ToolResultCard.tsx
"""

from __future__ import annotations

import json
from typing import Any

from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from textual.containers import Container, Vertical
from textual.widgets import Button, Static


class ToolUseWidget(Static):
    """A single tool-call with expandable result.

    Displays as:
      🔧 tool_name (args_summary)        [expand/collapse]
      ┌──────────────────────────────────┐
      │ Tool result (when expanded)      │
      └──────────────────────────────────┘
    """

    def __init__(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any = None,
        *,
        is_error: bool = False,
        is_streaming: bool = False,
    ) -> None:
        super().__init__()
        self.tool_name = tool_name
        self.arguments = arguments
        self.result = result
        self.is_error = is_error
        self.is_streaming = is_streaming
        self._expanded = False

    def on_mount(self) -> None:
        self._render_header()

    def _render_header(self) -> None:
        """Render the tool call header."""
        args_summary = ", ".join(
            f"{k}={str(v)[:40]}" for k, v in list(self.arguments.items())[:3]
        )
        icon = "🔧" if not self.is_error else "❌"
        style = "bold blue" if not self.is_error else "bold red"
        status = " [streaming...]" if self.is_streaming else ""

        self.update(Text(f"{icon} {self.tool_name}({args_summary}){status}", style=style))

    def append_result(self, chunk: str) -> None:
        """Append streaming result chunk."""
        if self.result is None:
            self.result = ""
        self.result += chunk
        self.refresh()

    def toggle_expand(self) -> None:
        """Toggle result visibility."""
        self._expanded = not self._expanded
        self.refresh()

    def render(self) -> Panel:
        """Render the complete widget."""
        header = Text(f"🔧 {self.tool_name}", style="bold blue")
        args_text = Syntax(
            json.dumps(self.arguments, indent=2, ensure_ascii=False, default=str),
            "json", theme="monokai",
        )

        content_parts = [header, args_text]

        if self.result is not None:
            if self.is_error:
                result_panel = Panel(
                    str(self.result)[:2000],
                    border_style="red",
                    title="Error",
                )
            else:
                result_text = str(self.result)
                try:
                    result_syntax = Syntax(
                        json.dumps(json.loads(result_text), indent=2, ensure_ascii=False)
                        if result_text.strip().startswith("{")
                        else result_text,
                        "json" if result_text.strip().startswith("{") else "text",
                        theme="monokai",
                    )
                    result_panel = Panel(
                        result_syntax,
                        border_style="green",
                        title="Result",
                    )
                except Exception:
                    result_panel = Panel(
                        result_text[:2000],
                        border_style="green",
                        title="Result",
                    )
            content_parts.append(result_panel)

        return Panel(
            Vertical(*content_parts) if len(content_parts) > 1 else content_parts[0],
            border_style="blue" if not self.is_error else "red",
        )


def make_tool_widget(
    tool_name: str,
    arguments: dict[str, Any],
    result: Any = None,
    is_error: bool = False,
) -> Panel:
    """Quick factory for creating tool-use display panels without the full widget.

    Used for inline tool rendering in Rich-based contexts.
    """
    args_str = json.dumps(arguments, indent=2, ensure_ascii=False, default=str)
    result_str = str(result)[:2000] if result is not None else ""

    content = f"**{tool_name}**\n```json\n{args_str[:500]}\n```"
    if result_str:
        content += f"\n\n**Result:**\n```\n{result_str[:1000]}\n```"

    return Panel(
        content,
        border_style="red" if is_error else "blue",
        title=f"Tool: {tool_name}",
    )
