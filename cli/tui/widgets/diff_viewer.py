"""Diff Viewer — Claude Code-style syntax-highlighted code diff display.

Replicates Claude Code's diff rendering for file edits:
  - Green background for added lines
  - Red background for removed lines
  - Line numbers
  - Side-by-side or unified view

Claude Code equivalent: DiffView.tsx (uses React + syntax highlighting)
"""

from __future__ import annotations

from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


def render_unified_diff(
    diff_text: str,
    file_path: str = "",
    language: str = "",
) -> Panel:
    """Render a unified diff with color-coded additions/deletions.

    Claude Code equivalent: unified diff with +/- line highlighting.
    """
    lines = diff_text.split("\n")
    rendered_lines: list[Text] = []

    for line in lines[:200]:  # Cap at 200 lines
        if line.startswith("+++") or line.startswith("---"):
            rendered_lines.append(Text(line, style="bold blue"))
        elif line.startswith("@@"):
            rendered_lines.append(Text(line, style="cyan"))
        elif line.startswith("+"):
            rendered_lines.append(Text(line, style="green"))
        elif line.startswith("-"):
            rendered_lines.append(Text(line, style="red"))
        else:
            rendered_lines.append(Text(line, style="dim"))

    title = f"Diff: {file_path}" if file_path else "Diff"
    return Panel(
        "\n".join(str(r) for r in rendered_lines) if rendered_lines else diff_text[:5000],
        border_style="blue",
        title=title,
    )


def render_edit_preview(
    old_code: str,
    new_code: str,
    file_path: str = "",
    language: str = "python",
) -> Panel:
    """Render a before/after code comparison.

    Claude Code equivalent: FileEditTool preview with old/new side-by-side.
    """
    old_syntax = Syntax(old_code, language, theme="monokai", line_numbers=True)
    new_syntax = Syntax(new_code, language, theme="monokai", line_numbers=True)

    title = f"Edit: {file_path}" if file_path else "Edit Preview"
    return Panel(
        f"**Before:**\n{old_syntax}\n\n**After:**\n{new_syntax}",
        border_style="yellow",
        title=title,
    )
