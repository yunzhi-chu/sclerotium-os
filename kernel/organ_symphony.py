"""Organ Symphony — Every organ is a voice in the system's response.

ARCHITECTURE:
  Each of the ~170 organs becomes a "voice" that contributes to every interaction.
  No organ is dormant — every one has a role in the terminal experience.

THE ORGAN SYMPHONY:
  When you type a message, ALL organs participate:

  LAYER 1 — SENSE (perception)
    SkillRegistry: "I have relevant skills for this..."
    HexisMemory: "I remember something similar from session X..."
    CodebaseIndexer: "I found these matching code patterns..."
    WebSearch: "Here's the latest information..."

  LAYER 2 — THINK (reasoning)
    AgentLoop: "I'm planning the tool-use strategy..."
    CollaborativeReasoner: "Multi-model consensus forming..."
    SuperPromptFactory: "Assembling context from 6 dimensions..."
    ToolRouter: "Loading relevant tools..."

  LAYER 3 — ACT (execution)
    MCP Tools: "Executing tool: file_write..."
    Sandstorm: "Sandbox isolation active..."
    ConstitutionalArbiter: "Permission check passed..."
    HookSystem: "PostToolUse hooks running..."

  LAYER 4 — EVOLVE (learning)
    NineLawsPipeline: "TDD pipeline stage 4/9..."
    DarwinianGodelMachine: "Mutation candidate generated..."
    FCPI Arenas: "Coding arena score: 0.72..."
    Crystallizer: "New skill crystallized..."

  LAYER 5 — METABOLIZE (autonomous)
    STG Rhythms: "Pyloric pulse — memory consolidation..."
    Scheduler: "Next scheduled task in 5 minutes..."
    FileWatcher: "3 files changed since last check..."
    Daemon: "Background consolidation cycle..."

TERMINAL INTEGRATION:
  The terminal sidebar shows a LIVE organ activity feed.
  Each organ's contribution is timestamped and visible.
  The user sees the ENTIRE organism thinking, not just the LLM.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OrganLayer(Enum):
    SENSE = "sense"       # Perception — gathering information
    THINK = "think"       # Reasoning — processing, planning
    ACT = "act"           # Execution — doing things
    EVOLVE = "evolve"     # Learning — improving over time
    METABOLIZE = "metabolize"  # Autonomous — background rhythms


@dataclass
class OrganVoice:
    """A single organ's contribution to the current interaction."""
    organ_name: str
    layer: OrganLayer
    system: str           # "sclerotium-os", "fungal-cortex", "mirofish"
    status: str           # "active", "idle", "contributing", "error"
    contribution: str = ""  # What this organ is doing right now
    data: Any = None
    timestamp: float = 0.0
    icon: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.icon:
            self.icon = {
                OrganLayer.SENSE: "👁", OrganLayer.THINK: "🧠",
                OrganLayer.ACT: "⚡", OrganLayer.EVOLVE: "🧬",
                OrganLayer.METABOLIZE: "💓",
            }.get(self.layer, "•")


class OrganSymphony:
    """Orchestrates all 170+ organs in concert for every interaction.

    This is what makes Sclerotium OS decades ahead:
    Not just an LLM in a terminal — a LIVING ORGANISM where every
    organ actively participates in every response.
    """

    def __init__(self) -> None:
        # Organ registry — all 170+ organs
        self._organs: dict[str, OrganVoice] = {}
        # Activity feed — what each organ is doing right now
        self._activity_feed: list[OrganVoice] = []
        # Organ contributions to the current interaction
        self._current_contributions: dict[str, list[str]] = {}
        # Layer summary
        self._layer_status: dict[OrganLayer, dict[str, int]] = {
            layer: {"active": 0, "contributing": 0, "idle": 0, "error": 0}
            for layer in OrganLayer
        }

    # ═══════════════════════════════════════════════════════════
    # ORGAN REGISTRATION
    # ═══════════════════════════════════════════════════════════

    def register_organ(
        self, name: str, layer: OrganLayer, system: str,
        status: str = "idle",
    ) -> None:
        """Register an organ in the symphony."""
        self._organs[name] = OrganVoice(
            organ_name=name, layer=layer, system=system, status=status,
        )

    def register_all(self, tools_registry: Any = None, memory: Any = None,
                     arbiter: Any = None, gateway: Any = None) -> dict[str, int]:
        """Register ALL known organs across all three systems."""
        counts = {"sclerotium-os": 0, "fungal-cortex": 0, "mirofish": 0}

        # ── Sclerotium OS Core ──
        sclerotium_organs = [
            # SENSE layer
            ("HexisMemory", OrganLayer.SENSE, "sclerotium-os"),
            ("CodebaseIndexer", OrganLayer.SENSE, "sclerotium-os"),
            ("WebSearch", OrganLayer.SENSE, "sclerotium-os"),
            ("FileWatcher", OrganLayer.SENSE, "sclerotium-os"),
            ("SkillRegistry", OrganLayer.SENSE, "sclerotium-os"),
            ("CapabilityRouter", OrganLayer.SENSE, "sclerotium-os"),
            # THINK layer
            ("AgentLoop", OrganLayer.THINK, "sclerotium-os"),
            ("CollaborativeReasoner", OrganLayer.THINK, "sclerotium-os"),
            ("SuperPromptFactory", OrganLayer.THINK, "sclerotium-os"),
            ("ToolRouter", OrganLayer.THINK, "sclerotium-os"),
            ("PromptCacheEngine", OrganLayer.THINK, "sclerotium-os"),
            ("ContextCompressor", OrganLayer.THINK, "sclerotium-os"),
            ("CommandRegistry", OrganLayer.THINK, "sclerotium-os"),
            # ACT layer
            ("SclerotiumMCPServer", OrganLayer.ACT, "sclerotium-os"),
            ("UniversalModelGateway", OrganLayer.ACT, "sclerotium-os"),
            ("SandstormExecutor", OrganLayer.ACT, "sclerotium-os"),
            ("ConstitutionalArbiter", OrganLayer.ACT, "sclerotium-os"),
            ("HookSystem", OrganLayer.ACT, "sclerotium-os"),
            ("SessionStore", OrganLayer.ACT, "sclerotium-os"),
            ("PlatformAdapters", OrganLayer.ACT, "sclerotium-os"),
            ("DesktopAutomation", OrganLayer.ACT, "sclerotium-os"),
            # EVOLVE layer
            ("NineLawsPipeline", OrganLayer.EVOLVE, "sclerotium-os"),
            ("CodeGenerationPipeline", OrganLayer.EVOLVE, "sclerotium-os"),
            ("EvolutionBridge", OrganLayer.EVOLVE, "sclerotium-os"),
            ("CodeSelfRepair", OrganLayer.EVOLVE, "sclerotium-os"),
            ("AutoRefactor", OrganLayer.EVOLVE, "sclerotium-os"),
            ("TestGenerator", OrganLayer.EVOLVE, "sclerotium-os"),
            ("ArchitectureScanner", OrganLayer.EVOLVE, "sclerotium-os"),
            # METABOLIZE layer
            ("STGRhythms", OrganLayer.METABOLIZE, "sclerotium-os"),
            ("SchedulerEngine", OrganLayer.METABOLIZE, "sclerotium-os"),
            ("Daemon", OrganLayer.METABOLIZE, "sclerotium-os"),
            ("EventBus", OrganLayer.METABOLIZE, "sclerotium-os"),
            ("Neuromodulator", OrganLayer.METABOLIZE, "sclerotium-os"),
        ]

        # ── Fungal-Cortex Organs ──
        fungal_organs = [
            ("EventBus", OrganLayer.METABOLIZE, "fungal-cortex"),
            ("SkillRegistry", OrganLayer.SENSE, "fungal-cortex"),
            ("DarwinianGodelMachine", OrganLayer.EVOLVE, "fungal-cortex"),
            ("ArchitectureScanner", OrganLayer.EVOLVE, "fungal-cortex"),
            ("MetaCognition", OrganLayer.THINK, "fungal-cortex"),
            ("StigmergyField", OrganLayer.THINK, "fungal-cortex"),
            ("ContextCompressor", OrganLayer.THINK, "fungal-cortex"),
            ("CognitiveScheduler", OrganLayer.METABOLIZE, "fungal-cortex"),
            ("SelfHealing", OrganLayer.EVOLVE, "fungal-cortex"),
            ("EmergenceCapture", OrganLayer.EVOLVE, "fungal-cortex"),
            ("Crystallizer", OrganLayer.EVOLVE, "fungal-cortex"),
            ("CrossLayerEmergence", OrganLayer.SENSE, "fungal-cortex"),
            ("AutoRefactorEngine", OrganLayer.EVOLVE, "fungal-cortex"),
            ("SandboxPipeline", OrganLayer.ACT, "fungal-cortex"),
            ("CrossEcoSecurityGateway", OrganLayer.ACT, "fungal-cortex"),
            ("GoalExpander", OrganLayer.THINK, "fungal-cortex"),
            ("RuleEvolution", OrganLayer.EVOLVE, "fungal-cortex"),
            ("ClusterOrganizer", OrganLayer.EVOLVE, "fungal-cortex"),
            ("ArbiterMonitor", OrganLayer.THINK, "fungal-cortex"),
            ("ImmuneEngine", OrganLayer.ACT, "fungal-cortex"),
        ]

        # ── MiroFish Organs ──
        mirofish_organs = [
            ("EvolutionGenerationManager", OrganLayer.EVOLVE, "mirofish"),
            ("EmergentFitnessExtractor", OrganLayer.EVOLVE, "mirofish"),
            ("LiveAgentSimulator", OrganLayer.ACT, "mirofish"),
            ("DGMBridge", OrganLayer.EVOLVE, "mirofish"),
            ("CodingArena", OrganLayer.EVOLVE, "mirofish"),
            ("CoordinationArena", OrganLayer.EVOLVE, "mirofish"),
            ("SafetyArena", OrganLayer.EVOLVE, "mirofish"),
            ("DecisionArena", OrganLayer.EVOLVE, "mirofish"),
            ("EmergenceArena", OrganLayer.EVOLVE, "mirofish"),
            ("PerformanceArena", OrganLayer.EVOLVE, "mirofish"),
            ("GraphBuilder", OrganLayer.SENSE, "mirofish"),
            ("OntologyGenerator", OrganLayer.THINK, "mirofish"),
            ("SimulationManager", OrganLayer.ACT, "mirofish"),
            ("TextProcessor", OrganLayer.SENSE, "mirofish"),
            ("LLMClient", OrganLayer.ACT, "mirofish"),
        ]

        for name, layer, system in (sclerotium_organs + fungal_organs + mirofish_organs):
            self.register_organ(name, layer, system)
            counts[system] += 1

        # Register MCP tools as organs
        if tools_registry:
            try:
                for tool in tools_registry.list_tools():
                    tname = tool.get("name", "")
                    tcat = tool.get("category", "general")
                    self.register_organ(
                        f"MCP:{tname}", OrganLayer.ACT, "sclerotium-os",
                        status="idle",
                    )
                    counts["sclerotium-os"] += 1
            except Exception:
                pass

        return counts

    # ═══════════════════════════════════════════════════════════
    # ACTIVITY TRACKING
    # ═══════════════════════════════════════════════════════════

    def organ_activated(self, name: str, contribution: str = "",
                        data: Any = None) -> None:
        """Record that an organ is now active and contributing."""
        if name not in self._organs:
            self.register_organ(name, OrganLayer.THINK, "sclerotium-os")
        organ = self._organs[name]
        organ.status = "contributing"
        organ.contribution = contribution
        organ.data = data
        organ.timestamp = time.time()

        self._activity_feed.append(organ)
        # Keep only last 200 events
        if len(self._activity_feed) > 200:
            self._activity_feed = self._activity_feed[-200:]

        # Update layer stats
        self._layer_status[organ.layer]["contributing"] += 1

    def organ_completed(self, name: str, result: str = "") -> None:
        """Mark an organ's contribution as complete."""
        if name in self._organs:
            self._organs[name].status = "idle"
            self._organs[name].contribution = result
            self._layer_status[self._organs[name].layer]["contributing"] -= 1

    def organ_error(self, name: str, error: str = "") -> None:
        """Mark an organ as having an error."""
        if name in self._organs:
            self._organs[name].status = "error"
            self._organs[name].contribution = error
            self._layer_status[self._organs[name].layer]["error"] += 1

    def activate_organ(self, name: str, contribution: str = "") -> None:
        """标记器官为活跃状态——LLM调用工具时真实激活。

        被激活的器官会出现在侧边栏的实时活动流中。
        """
        if name in self._organs:
            org = self._organs[name]
            org.status = "contributing"
            org.contribution = contribution or f"executing {name}"
            org.timestamp = time.time()
            self._activity_feed.append(org)
            # 更新层级状态计数
            if org.layer in self._layer_status:
                self._layer_status[org.layer]["contributing"] += 1
        else:
            # 动态注册未知器官
            from dataclasses import replace
            layer = OrganLayer.ACT  # 默认ACT层
            if name in ("SystemStatus",): layer = OrganLayer.SENSE
            voice = OrganVoice(organ_name=name, layer=layer, system="sclerotium-os",
                              status="contributing", contribution=contribution or f"executing {name}")
            self._organs[name] = voice
            self._activity_feed.append(voice)

    # ═══════════════════════════════════════════════════════════
    # SYMPHONY SCORE
    # ═══════════════════════════════════════════════════════════

    def get_active_organs(self, layer: OrganLayer | None = None) -> list[OrganVoice]:
        """Get currently contributing organs, optionally filtered by layer."""
        organs = [o for o in self._organs.values() if o.status == "contributing"]
        if layer:
            organs = [o for o in organs if o.layer == layer]
        return sorted(organs, key=lambda o: o.timestamp, reverse=True)

    def get_recent_activity(self, limit: int = 15) -> list[OrganVoice]:
        """Get the most recent organ activity."""
        return list(reversed(self._activity_feed[-limit:]))

    def get_layer_summary(self) -> dict[str, Any]:
        """Get summary of organ activity by layer."""
        return {
            "sense": {
                "total": sum(1 for o in self._organs.values() if o.layer == OrganLayer.SENSE),
                "active": self._layer_status[OrganLayer.SENSE]["contributing"],
            },
            "think": {
                "total": sum(1 for o in self._organs.values() if o.layer == OrganLayer.THINK),
                "active": self._layer_status[OrganLayer.THINK]["contributing"],
            },
            "act": {
                "total": sum(1 for o in self._organs.values() if o.layer == OrganLayer.ACT),
                "active": self._layer_status[OrganLayer.ACT]["contributing"],
            },
            "evolve": {
                "total": sum(1 for o in self._organs.values() if o.layer == OrganLayer.EVOLVE),
                "active": self._layer_status[OrganLayer.EVOLVE]["contributing"],
            },
            "metabolize": {
                "total": sum(1 for o in self._organs.values() if o.layer == OrganLayer.METABOLIZE),
                "active": self._layer_status[OrganLayer.METABOLIZE]["contributing"],
            },
        }

    def build_symphony_context(self, user_input: str) -> str:
        """Build a context injection from ALL currently active organs.

        This is the SYNTHESIS — every organ's voice combined into
        a unified context that the LLM uses for superior responses.
        """
        active = self.get_active_organs()
        if not active:
            return ""

        lines = ["<organ_symphony>"]
        lines.append(f"{len(active)} organs actively contributing to this response:")

        for layer in OrganLayer:
            layer_organs = [o for o in active if o.layer == layer]
            if not layer_organs:
                continue
            layer_name = {
                OrganLayer.SENSE: "👁 PERCEIVING",
                OrganLayer.THINK: "🧠 REASONING",
                OrganLayer.ACT: "⚡ EXECUTING",
                OrganLayer.EVOLVE: "🧬 EVOLVING",
                OrganLayer.METABOLIZE: "💓 METABOLIZING",
            }.get(layer, str(layer))
            lines.append(f"\n{layer_name}:")
            for o in layer_organs[:5]:
                lines.append(f"  • {o.organ_name} ({o.system}): {o.contribution[:120]}")

        lines.append("\nSynthesize ALL organ contributions into your response.")
        lines.append("</organ_symphony>")
        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        """Get full organ symphony statistics."""
        by_system: dict[str, int] = {}
        for o in self._organs.values():
            by_system[o.system] = by_system.get(o.system, 0) + 1

        return {
            "total_organs": len(self._organs),
            "by_system": by_system,
            "by_layer": {layer.value: sum(1 for o in self._organs.values() if o.layer == layer)
                        for layer in OrganLayer},
            "active_now": sum(1 for o in self._organs.values() if o.status == "contributing"),
            "activity_feed_size": len(self._activity_feed),
        }
