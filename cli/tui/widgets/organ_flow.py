"""Organ Flow — Living circulation animation.

Replaces the dead spinner with a living animation of organ names
flowing through the 5-layer architecture, like blood circulating
through a living body.

Flow pattern:
  SENSE → THINK → ACT → EVOLVE → METABOLIZE
     ↑                                    │
     └────────────────────────────────────┘
"""

from __future__ import annotations

import time
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class OrganFlow(Static):
    """Living organ circulation animation — beats any spinner."""

    # Organ names by layer, cycled through during animation
    ORGAN_CYCLE = {
        "sense": [
            "HexisMemory", "CodebaseIndexer", "SkillRegistry",
            "CapabilityRouter", "WebSearch", "GraphBuilder",
            "FileWatcher", "CrossLayerEmergence", "TextProcessor",
        ],
        "think": [
            "AgentLoop", "SuperPromptFactory", "CollaborativeReasoner",
            "ToolRouter", "PromptCacheEngine", "ContextCompressor",
            "MetaCognition", "StigmergyField", "GoalExpander",
            "CommandRegistry", "OntologyGenerator", "ArbiterMonitor",
        ],
        "act": [
            "Gateway", "MCP:file_write", "SandstormExecutor",
            "ConstitutionalArbiter", "HookSystem", "SessionStore",
            "PlatformAdapters", "DesktopAutomation", "MCP:sandbox",
            "SimulationManager", "LiveAgentSimulator", "LLMClient",
            "SclerotiumMCPServer", "ImmuneEngine",
        ],
        "evolve": [
            "NineLawsPipeline", "DarwinianGodelMachine", "CodingArena",
            "SafetyArena", "Crystallizer", "ArchitectureScanner",
            "AutoRefactorEngine", "EmergenceCapture", "TestGenerator",
            "EvolutionManager", "FitnessExtractor", "DGMBridge",
            "CoordinationArena", "DecisionArena", "EmergenceArena",
            "PerformanceArena", "CodeSelfRepair", "RuleEvolution",
            "ClusterOrganizer", "SourceEvolutionEngine",
        ],
        "metabolize": [
            "STGRhythms", "SchedulerEngine", "EventBus",
            "Neuromodulator", "Daemon", "CognitiveScheduler",
        ],
    }

    # Layer colors and icons
    LAYER_STYLE = {
        "sense": ("👁", "dim cyan"),
        "think": ("🧠", "bold yellow"),
        "act": ("⚡", "bold green"),
        "evolve": ("🧬", "bold magenta"),
        "metabolize": ("💓", "dim"),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__("", *args, **kwargs)
        self._frame: int = 0
        self._active_organs: list[tuple[str, str, str]] = []  # (layer, name, icon)
        self._pulse_phase: float = 0.0
        self._start_time: float = time.time()

    def tick(self, active_organs: list[tuple[str, str]] | None = None) -> None:
        """Advance one animation frame. Call at ~8-10 fps.

        Args:
            active_organs: List of (layer, organ_name) tuples currently active.
                          If None, cycles through all organs.
        """
        self._frame += 1
        self._pulse_phase = (time.time() - self._start_time) % 2.0

        if active_organs:
            self._active_organs = [
                (layer, name, self.LAYER_STYLE.get(layer, ("•", "dim"))[0])
                for layer, name in active_organs
            ]
        else:
            # Auto-cycle: pick organs based on frame number
            self._active_organs = []
            cycle_layers = ["sense", "think", "act", "evolve", "metabolize"]
            for i, layer in enumerate(cycle_layers):
                organs = self.ORGAN_CYCLE.get(layer, [])
                if organs:
                    idx = (self._frame + i * 3) % len(organs)
                    icon = self.LAYER_STYLE.get(layer, ("•", "dim"))[0]
                    self._active_organs.append((layer, organs[idx], icon))

        self.refresh()

    def render(self) -> Panel:
        """Render the living organ flow."""
        if not self._active_organs:
            return Panel(Text("", style="dim"), border_style="dim",
                        title="Organ Flow")

        # Build flow lines
        lines = []
        n = len(self._active_organs)

        for i, (layer, name, icon) in enumerate(self._active_organs):
            # Calculate pulse effect — sine wave offset by position
            pulse = abs(__import__('math').sin(self._pulse_phase * 3 + i * 0.8))
            intensity = int(0.4 + pulse * 0.6)

            style = self.LAYER_STYLE.get(layer, ("•", "dim"))[1]
            # Dimmer when not pulsing
            dimmed = style.replace("bold ", "") if intensity < 0.6 else style

            # Flow arrow between organs
            arrow = ""
            if i < n - 1:
                arrow_frames = [" → ", " ─→ ", " ═→ ", " ─→ "]
                arrow = arrow_frames[self._frame % 4]

            # Organ label with pulse brightness
            prefix = "●" if pulse > 0.7 else "○"
            lines.append(f"{icon} {prefix} {name:<22}{arrow}")

        # Bottom flow returns to top
        lines.append("   ↑" + " " * 21 + "└" + "─" * 30 + "┘")

        text = Text("\n".join(lines))
        return Panel(text, border_style="cyan", title="🧬 Organ Flow",
                    subtitle=f"SENSE → THINK → ACT → EVOLVE → METABOLIZE")
