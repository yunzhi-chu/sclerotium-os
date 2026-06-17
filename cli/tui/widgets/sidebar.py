"""Sidebar — Live Organ Activity with Organ Flow animation.

Shows organism vitals AND the living organ flow animation.
The flow shows organs circulating through the 5 layers like blood.
"""
from __future__ import annotations
import math, time
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static


class OrganismSidebar(Static):
    """Right sidebar — vitals + organ flow animation."""

    _fcpi: dict[str, float] = {}
    _memory_stats: dict[str, int] = {}
    _stg_phase: str = "pyloric"
    _tools_active: int = 0
    _security_allowed: int = 0
    _security_blocked: int = 0
    _mode: str = "work"
    _generation: int = 0
    _context_window: int = 1_000_000
    _history_tokens: int = 0
    _symphony_stats: dict = {}
    _recent_activity: list = []
    _flow_frame: int = 0
    _thinking: bool = False
    _start_time: float = 0.0

    # Organ cycle for flow animation
    FLOW_ORGANS = {
        "sense": ["HexisMemory", "CodebaseIndexer", "SkillRegistry", "CapabilityRouter", "WebSearch"],
        "think": ["AgentLoop", "Collaborative", "SuperPrompt", "ToolRouter", "PromptCache"],
        "act": ["Gateway", "MCP:file_write", "Sandstorm", "Arbiter", "HookSystem"],
        "evolve": ["NineLaws", "DarwinianGM", "CodingArena", "Crystallizer", "ArchScanner"],
        "metabolize": ["STGRhythms", "Scheduler", "EventBus", "Neuromod", "Daemon"],
    }
    LAYER_ICONS = {"sense": "👁", "think": "🧠", "act": "⚡", "evolve": "🧬", "metabolize": "💓"}
    LAYER_COLORS = {"sense": "dim cyan", "think": "bold yellow", "act": "bold green",
                    "evolve": "bold magenta", "metabolize": "dim"}

    def update_symphony(self, stats: dict, activity: list) -> None:
        self._symphony_stats = stats
        self._recent_activity = activity[-8:] if activity else []
        self.refresh()

    def update_vitals(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, f'_{k}'): setattr(self, f'_{k}', v)
        self.refresh()

    def start_flow(self) -> None:
        self._thinking = True
        self._start_time = time.time()
        self._flow_frame = 0

    def stop_flow(self) -> None:
        self._thinking = False

    def tick_flow(self, active_organs: list | None = None) -> None:
        if not self._thinking: return
        self._flow_frame += 1
        if self._flow_frame % 2 != 0: return
        if active_organs:
            # 直接使用真实的OrganVoice对象
            self._recent_activity = list(active_organs[-8:])
        self.refresh()

    def _build_flow(self) -> str:
        """Build the organ flow — shows REAL active organs from the symphony.

        When thinking, displays which organs are actually contributing right now.
        Falls back to organ cycling animation when no real data is available.
        """
        if not self._thinking:
            return ""

        # ── 真实活跃器官 ──
        real_organs: dict[str, list[str]] = {}
        for v in self._recent_activity[-10:]:
            layer = getattr(v, 'layer', None)
            layer_name = layer.value if hasattr(layer, 'value') else str(layer)
            name = getattr(v, 'organ_name', '?')
            if layer_name not in real_organs:
                real_organs[layer_name] = []
            if name not in real_organs[layer_name]:
                real_organs[layer_name].append(name)

        lines = ["", "[bold]🧬 Organ Flow[/]", ""]
        layers = ["sense", "think", "act", "evolve", "metabolize"]

        for i, layer in enumerate(layers):
            icon = self.LAYER_ICONS.get(layer, "•")
            color = self.LAYER_COLORS.get(layer, "dim")

            if layer in real_organs and real_organs[layer]:
                # 显示真实活跃器官
                names = real_organs[layer][:3]  # 最多3个
                for j, name in enumerate(names):
                    dot = "●" if j == 0 else "○"
                    arrow = " → " if j < len(names)-1 else ""
                    lines.append(f"  {icon} [{color}]{dot} {name:<18}[/{color}]{arrow}")
            else:
                # 无真实数据时显示idle状态
                lines.append(f"  {icon} [dim]○ idle[/dim]")

        return "\n".join(lines)

    def render(self) -> Panel:
        parts = []

        # --- Vitals ---
        fcpi_total = sum(self._fcpi.values()) / max(len(self._fcpi), 1) if self._fcpi else 0
        bar = "█" * int(fcpi_total * 10) + "░" * (10 - int(fcpi_total * 10))
        parts.append(f"📊 FCPI: [cyan]{bar}[/] {fcpi_total:.2f}")
        parts.append(f"🧠 Memory: {sum(self._memory_stats.values())} in {len(self._memory_stats)} layers")
        parts.append(f"💓 STG: [yellow]{self._stg_phase}[/] | Mode: [blue]{self._mode}[/]")
        parts.append(f"🔧 Tools: [green]{self._tools_active}[/] | Security: [green]{self._security_allowed}[/]/[red]{self._security_blocked}[/]")
        ctx_pct = (self._history_tokens / self._context_window * 100) if self._context_window else 0
        parts.append(f"📜 Context: [dim]{self._history_tokens:,}/{self._context_window//1000}K[/] ({ctx_pct:.1f}%)")

        # --- Symphony stats ---
        if self._symphony_stats:
            by_layer = self._symphony_stats.get("by_layer", {})
            total = self._symphony_stats.get("total_organs", 0)
            active = self._symphony_stats.get("active_now", 0)
            parts.append("")
            parts.append(f"[bold]🧬 Organ Symphony[/] ({total} organs, {active} active)")
            for layer in ["sense", "think", "act", "evolve", "metabolize"]:
                count = by_layer.get(layer, 0)
                icon = self.LAYER_ICONS.get(layer, "•")
                parts.append(f"  {icon} {layer}: [dim]{count}[/]")

        # --- Organ Flow Animation (when thinking) ---
        flow = self._build_flow()
        if flow:
            parts.append(flow)
        # --- Recent Activity ---
        elif self._recent_activity:
            parts.append("")
            parts.append("[bold]📡 Recent Activity[/]")
            for v in self._recent_activity[-5:]:
                name = getattr(v, 'organ_name', '?')[:18]
                icon = getattr(v, 'icon', '•')
                contrib = getattr(v, 'contribution', '')[:30] or 'active'
                parts.append(f"  {icon} [dim]{name}[/] {contrib}")

        return Panel("\n".join(parts), title="🧬 Organism Vitals", border_style="cyan", padding=(0, 1))
