"""Permission Dialog — Claude Code-style interactive permission screen.

Replicates Claude Code's permission prompt:
  - Shows tool name + arguments
  - Risk level indicator (color-coded)
  - Reason for requiring confirmation
  - Allow / Deny / Always Allow (this session) buttons
  - Keyboard shortcuts (Y/N/A)

Claude Code equivalent: PermissionPrompt.tsx + yoloClassifier UI
"""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.text import Text
from textual.containers import Center, Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class PermissionDialog(ModalScreen[bool]):
    """Modal dialog for confirming tool execution.

    Claude Code equivalent: the permission prompt that appears when
    the ML classifier flags a high-risk operation.
    """

    def __init__(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        risk_level: str = "MEDIUM",
        reason: str = "",
    ) -> None:
        super().__init__()
        self.tool_name = tool_name
        self.arguments = arguments
        self.risk_level = risk_level
        self.reason = reason

    def compose(self):
        risk_color = {
            "CRITICAL": "bold red",
            "HIGH": "red",
            "MEDIUM": "yellow",
            "LOW": "dim",
        }.get(self.risk_level, "white")

        args_summary = ", ".join(
            f"{k}={str(v)[:60]}" for k, v in list(self.arguments.items())[:5]
        )

        yield Container(
            Static(
                f"⚠ Tool Execution Requires Confirmation",
                classes="permission-warning",
            ),
            Static(f"Tool: {self.tool_name}", classes="tool-call-header"),
            Static(f"Arguments: {args_summary}"),
            Static(
                f"Risk Level: [{risk_color}]{self.risk_level}[/]",
            ),
            Static(f"Reason: {self.reason}") if self.reason else Static(""),
            Static(""),
            Horizontal(
                Button("✅ Allow Once", variant="primary", id="allow-once"),
                Button("🔓 Allow All (this session)", variant="default", id="allow-session"),
                Button("❌ Deny", variant="error", id="deny"),
            ),
            id="permission-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "allow-once":
            self.dismiss(True)
        elif event.button.id == "allow-session":
            # Signal to grant session-wide permission
            self.dismiss(True)
        elif event.button.id == "deny":
            self.dismiss(False)
