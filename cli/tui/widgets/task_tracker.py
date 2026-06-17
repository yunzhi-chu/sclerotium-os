"""Task Tracker — Claude Code-style plan checklist with live progress.

Shows a task list where each task is:
  ☐ pending    — not yet started
  ◌ in_progress — currently working on
  ✅ completed  — done
  ❌ failed     — error

Claude Code equivalent: TodoWrite tool + TaskCreate/TaskUpdate.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static


@dataclass
class TaskItem:
    id: str
    subject: str
    status: str = "pending"  # pending, in_progress, completed, failed
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""

    @property
    def icon(self) -> str:
        return {"pending": "☐", "in_progress": "◌", "completed": "✅",
                "failed": "❌"}.get(self.status, "☐")

    @property
    def style(self) -> str:
        return {"pending": "dim", "in_progress": "bold yellow",
                "completed": "green", "failed": "bold red"}.get(self.status, "dim")


class TaskTracker(Static):
    """Live task checklist widget.

    Displays as a panel with checkboxes that update in real-time.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__("", *args, **kwargs)
        self._tasks: dict[str, TaskItem] = {}
        self._title: str = "Task Plan"

    @property
    def total(self) -> int:
        return len(self._tasks)

    @property
    def completed(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == "completed")

    @property
    def failed(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == "failed")

    @property
    def in_progress(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == "in_progress")

    @property
    def progress(self) -> float:
        if not self._tasks:
            return 0.0
        return self.completed / len(self._tasks)

    @property
    def progress_bar(self) -> str:
        if not self._tasks:
            return ""
        width = 16
        done = int(self.progress * width)
        return "█" * done + "░" * (width - done)

    # ── Task management ──────────────────────────────────────────────

    def add(self, task_id: str, subject: str, status: str = "pending") -> TaskItem:
        """Add a task to the tracker."""
        task = TaskItem(id=task_id, subject=subject, status=status)
        if status == "in_progress":
            task.started_at = time.time()
        self._tasks[task_id] = task
        self.refresh()
        return task

    def add_batch(self, tasks: list[dict[str, str]]) -> None:
        """Add multiple tasks at once (from plan generation)."""
        for t in tasks:
            self.add(t.get("id", t.get("subject", "")),
                    t.get("subject", t.get("id", "")),
                    t.get("status", "pending"))
        self.refresh()

    def start(self, task_id: str) -> None:
        """Mark a task as in_progress."""
        if task_id in self._tasks:
            self._tasks[task_id].status = "in_progress"
            self._tasks[task_id].started_at = time.time()
            self.refresh()

    def complete(self, task_id: str) -> None:
        """Mark a task as completed."""
        if task_id in self._tasks:
            self._tasks[task_id].status = "completed"
            self._tasks[task_id].completed_at = time.time()
            self.refresh()

    def fail(self, task_id: str, error: str = "") -> None:
        """Mark a task as failed."""
        if task_id in self._tasks:
            self._tasks[task_id].status = "failed"
            self._tasks[task_id].error = error
            self.refresh()

    def clear(self) -> None:
        """Clear all tasks."""
        self._tasks.clear()
        self.refresh()

    # ── Rendering ────────────────────────────────────────────────────

    def render(self) -> Panel:
        """Render the task checklist."""
        if not self._tasks:
            return Panel("No tasks", border_style="dim", title=self._title)

        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("icon", width=2)
        table.add_column("task", ratio=1)

        # Sort: in_progress first, then pending, then completed
        order = {"in_progress": 0, "pending": 1, "failed": 2, "completed": 3}
        sorted_tasks = sorted(self._tasks.values(), key=lambda t: order.get(t.status, 99))

        for task in sorted_tasks:
            text = Text(f"{task.icon} {task.subject}", style=task.style)
            if task.error:
                text.append(f"\n   └ {task.error}", style="red dim")
            table.add_row(task.icon, text)

        # Progress footer
        footer = (f"[{self.progress_bar}] {self.completed}/{self.total} done"
                  if self._tasks else "")
        if self.in_progress > 0:
            footer += f"  ({self.in_progress} active)"

        return Panel(table, border_style="cyan", title=self._title,
                     subtitle=footer)

    # ── LLM integration ──────────────────────────────────────────────

    def parse_from_llm_response(self, text: str) -> int:
        """Parse a task list from LLM response (markdown checklist format).

        Detects:
          - [ ] Task name  → pending
          - [x] Task name  → completed
          - - [ ] Task name → pending
          - * [ ] Task name → pending
        """
        count = 0
        for line in text.split("\n"):
            line = line.strip()
            # Match checklist patterns
            if line.startswith("- [ ]") or line.startswith("* [ ]"):
                subject = line[5:].strip()
                self.add(f"task_{self.total+1}", subject, "pending")
                count += 1
            elif line.startswith("- [x]") or line.startswith("* [x]"):
                subject = line[5:].strip()
                self.add(f"task_{self.total+1}", subject, "completed")
                count += 1
        return count

    def to_markdown(self) -> str:
        """Export tasks as markdown checklist."""
        lines = [f"## {self._title}\n"]
        for task in self._tasks.values():
            check = "x" if task.status == "completed" else " "
            lines.append(f"- [{check}] {task.subject}")
        lines.append(f"\n*{self.completed}/{self.total} completed*")
        return "\n".join(lines)
