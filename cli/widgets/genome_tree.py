"""Genome Tree widget — Rich-based evolutionary lineage display."""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.tree import Tree


class GenomeTree:
    """Display genome evolutionary lineage as a Rich Tree."""

    def __init__(self) -> None:
        self._genomes: list[dict[str, Any]] = []

    def update(self, genomes: list[dict[str, Any]]) -> None:
        """Update with latest genome list."""
        self._genomes = genomes[:20]

    def render(self) -> Panel:
        """Render genome lineage tree."""
        if not self._genomes:
            return Panel("No genomes yet", title="Genome Lineage", border_style="bright_black")

        root = Tree("🧬 Population", guide_style="bright_black")

        for g in self._genomes[:10]:
            gid = g.get("genome_id", "unknown")[:12]
            fcpi = g.get("fcpi_total", 0)
            gen = g.get("generation", "?")
            style = "green" if fcpi > 0.7 else ("yellow" if fcpi > 0.5 else "red")
            label = f"[{style}]Gen {gen}: {gid} (FCPI: {fcpi:.3f})[/{style}]"
            node = root.add(label)

            skills = g.get("skills", [])
            if skills:
                for skill in skills[:3]:
                    node.add(f"skill: {skill}", style="dim")

        return Panel(root, title="Genome Lineage", border_style="bright_black")
