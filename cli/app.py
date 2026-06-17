"""Sclerotium OS — CLI Application Entry Point.

FULL BODY startup: loads ALL ~170 organs across all three systems.
  fungal-cortex (~45) + MiroFish (~35) + Sclerotium OS (~90) = ~170 organs

Usage:
  python -m cli                        # Interactive REPL (full body)
  python -m cli --tui                  # Claude Code-style Textual TUI ★ NEW
  python -m cli.app --dashboard        # Dashboard view
  python -m cli.app --status           # Quick status
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Fix Windows console encoding for Rich
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.layout import Layout

from cli.screens.dashboard import DashboardScreen
from cli.screens.evolution import EvolutionScreen
from cli.screens.memory import MemoryScreen
from cli.screens.repl import REPLScreen

from mcp.server import SclerotiumMCPServer
from gateways.models import UniversalModelGateway


class OrganStatus:
    """Tracks a single organ's loading state."""
    __slots__ = ('name', 'layer', 'loaded', 'error', 'instance')
    def __init__(self, name: str, layer: str):
        self.name = name
        self.layer = layer
        self.loaded = False
        self.error: str | None = None
        self.instance: Any = None


class SclerotiumCLI:
    """Main CLI application — full body startup.

    Initializes ALL organs: fungal-cortex (~45) + MiroFish (~35) + Sclerotium OS (~90).
    Prints a comprehensive organ status report on startup.
    """

    def __init__(self) -> None:
        self.console = Console(force_terminal=True)
        self._organs: dict[str, OrganStatus] = {}
        self._total_organs = 0
        self._loaded_organs = 0

        # Core infrastructure (always loaded first)
        self.mcp = SclerotiumMCPServer()
        self.dashboard = DashboardScreen()
        self.evolution = EvolutionScreen()
        self.memory_screen = MemoryScreen()
        self.repl = REPLScreen(self.console)

        # Register MCP tools
        self.mcp.register_all_tools()

        # Load ALL organs
        self._init_sclerotium_organs()
        self._init_bridges_sync()

        # Wire to REPL
        self._wire_commands()
        self.repl.set_llm_handler(self._handle_llm_message)

        self._tools = self.mcp.tools

    # ══════════════════════════════════════════════════════════════════
    # FULL BODY INITIALIZATION — sclerotium-os kernel organs (~90)
    # ══════════════════════════════════════════════════════════════════

    def _init_sclerotium_organs(self) -> None:
        """Load EVERY sclerotium-os kernel organ."""

        # ── kernel root (4) ──
        self._try("hexis_memory", "kernel", "kernel.hexis_memory", "HexisMemoryStore",
                  chroma_path="./data/chroma", sqlite_path="./data/memory.db")
        self._try("constitutional_arbiter", "kernel", "kernel.constitutional_arbiter",
                  "ConstitutionalArbiter", audit_log_path="./data/audit.jsonl")
        self._try("sandstorm", "kernel", "kernel.sandstorm", "SandstormExecutor")
        self._try("evolution_bridge", "kernel", "kernel.evolution_bridge", "EvolutionBridge")

        # ── STG rhythms (5) ──
        self._try("pattern_generator", "stg", "kernel.stg.pattern_generator", "CentralPatternGenerator")
        self._try("pyloric_rhythm", "stg", "kernel.stg.pyloric_rhythm", "PyloricRhythm")
        self._try("gastric_rhythm", "stg", "kernel.stg.gastric_rhythm", "GastricRhythm")
        self._try("neuromodulator", "stg", "kernel.stg.neuromodulator", "Neuromodulator")
        self._try("winnerless_competition", "stg", "kernel.stg.winnerless_competition", "WinnerlessCompetition")

        # ── apotheosis (3) ──
        self._try("epigenetic_state", "apotheosis", "kernel.apotheosis.epigenetic_state", "EpigeneticComputationalState")
        self._try("immuno_attention", "apotheosis", "kernel.apotheosis.immuno_attention", "ImmunoAttentionNetwork")
        self._try("morphogenic_field", "apotheosis", "kernel.apotheosis.morphogenic_field", "MorphogenicField")

        # ── cosmic (5) ──
        self._try("auto_scientist", "cosmic", "kernel.cosmic.auto_scientist", "AutoScientist")
        self._try("code_bootstrap", "cosmic", "kernel.cosmic.code_bootstrap", "CodeBootstrap")
        self._try("digital_twin", "cosmic", "kernel.cosmic.digital_twin", "CognitiveDigitalTwin")
        self._try("recursive_self", "cosmic", "kernel.cosmic.recursive_self", "RecursiveSelfImprover")
        self._try("world_model", "cosmic", "kernel.cosmic.world_model", "WorldModel")

        # ── genesis (5) ──
        self._try("genetic_programming", "genesis", "kernel.genesis.genetic_program", "GeneticProgrammingEngine")
        self._try("controlled_emergence", "genesis", "kernel.genesis.controlled_emergence", "ControlledEmergence")
        self._try("economic_net", "genesis", "kernel.genesis.economic_net", "EconomicNetwork")
        self._try("gpu_kernel_gen", "genesis", "kernel.genesis.gpu_kernel_gen", "GPUKernelGenerator")
        self._try("swarm_intel", "genesis", "kernel.genesis.swarm_intel", "SwarmCoordinator")

        # ── innovation (4) ──
        self._try("mycelial_memory", "innovation", "kernel.innovation.mycelial_memory", "MycelialMemristiveMemory")
        self._try("orch_or", "innovation", "kernel.innovation.orch_or_substrate", "OrchORSubstrate")
        self._try("quantum_bio", "innovation", "kernel.innovation.quantum_bio_coherence", "QuantumBioCoherenceEngine")
        self._try("resonant_closure", "innovation", "kernel.innovation.resonant_closure", "ResonantClosureKernel")

        # ── omega (2) ──
        self._try("physical_ai", "omega", "kernel.omega.physical_ai", "PhysicalAI")
        self._try("p2p_mesh", "omega", "kernel.omega.p2p_mesh", "P2PMeshNetwork")

        # ── advanced (15) ──
        self._try("call_graph", "advanced", "kernel.advanced.code_refactor", "CallGraph")
        self._try("semantic_refactor", "advanced", "kernel.advanced.code_refactor", "SemanticRefactorEngine")
        self._try("vision_desktop", "advanced", "kernel.advanced.vision_desktop", "VisionDesktopAgent")
        self._try("formal_verifier", "advanced", "kernel.advanced.formal_verify", "FormalVerifier")
        self._try("rejection_sampler", "advanced", "kernel.advanced.formal_verify", "RejectionSampler")
        self._try("cross_os_desktop", "advanced", "kernel.advanced.cross_os_desktop", "CrossOSDesktop")
        self._try("debugger_agent", "advanced", "kernel.advanced.debugger", "DebuggerAgent")
        self._try("hooks_plugin", "advanced", "kernel.advanced.hooks_plugin", "HooksPluginSystem")
        self._try("proactive_memory", "advanced", "kernel.advanced.proactive_memory", "ProactiveMemoryEngine")
        self._try("source_evolve", "advanced", "kernel.advanced.source_evolve", "SourceEvolutionEngine")
        self._try("subagent_delegator", "advanced", "kernel.advanced.subagent_delegation", "SubAgentDelegator")
        self._try("test_generator", "advanced", "kernel.advanced.test_generator", "TestGenerator")
        self._try("voice_input", "advanced", "kernel.advanced.voice_remote", "VoiceInput")
        self._try("remote_control", "advanced", "kernel.advanced.voice_remote", "RemoteControl")
        self._try("wasm_sandbox", "advanced", "kernel.advanced.wasm_sandbox", "WASMSandbox")

        # ── sovereign (6+) ──
        self._try("agent_process_mgr", "sovereign", "kernel.sovereign.agent_process", "AgentProcessManager")
        self._try("cross_repo", "sovereign", "kernel.sovereign.cross_repo", "CrossRepoReasoner")
        self._try("ring0_governor", "sovereign", "kernel.sovereign.ring0_gov", "Ring0Governor")
        self._try("long_horizon", "sovereign", "kernel.sovereign.long_horizon")
        self._try("system_builder", "sovereign", "kernel.sovereign.system_builder")
        self._try("feature_dev", "sovereign", "kernel.sovereign.feature_dev")
        self._try("domain_knowledge", "sovereign", "kernel.sovereign.domain_knowledge")
        self._try("dep_migrate", "sovereign", "kernel.sovereign.dep_migrate")
        self._try("formal_prover", "sovereign", "kernel.sovereign.formal_prover")
        self._try("kernel_intel", "sovereign", "kernel.sovereign.kernel_intel")
        self._try("quantum_hybrid", "sovereign", "kernel.sovereign.quantum_hybrid")
        self._try("neuro_symbolic", "sovereign", "kernel.sovereign.neuro_symbolic")

        # ── cache (3) ──
        self._try("prompt_cache", "cache", "kernel.cache.prompt_cache_engine", "PromptCacheEngine")
        self._try("delta_encoder", "cache", "kernel.cache.prompt_cache_engine", "DeltaEncoder")
        self._try("cache_tracker", "cache", "kernel.cache.prompt_cache_engine", "CacheHitTracker")

        # ── gateways (3) ──
        self.gateway = UniversalModelGateway()
        self._register_organ("model_gateway", "gateways", True, self.gateway)
        self._try("mcp_market", "gateways", "gateways.mcp_market", "MCPMarketGateway")
        self._try("skills_market", "gateways", "gateways.skills_market", "SkillsMarketGateway")

        # ── platforms (4) ──
        self._try("platform_base", "platforms", "platforms.base", "PlatformAdapter")
        self._try("feishu", "platforms", "platforms.feishu", "FeishuAdapter")
        self._try("qq", "platforms", "platforms.qq", "QQAdapter")
        self._try("wechat", "platforms", "platforms.wechat", "WeChatAdapter")

        # ── automation (4) ──
        self._try("uia_controller", "automation", "automation.uia_controller", "UIAController")
        self._try("screen_agent", "automation", "automation.screen_agent", "ScreenAgent")
        self._try("input_simulator", "automation", "automation.input_simulator", "InputSimulator")
        self._try("app_launcher", "automation", "automation.app_launcher", "AppLauncher")

        # ── scheduler (1) ──
        self._try("scheduler_engine", "scheduler", "scheduler.engine", "SchedulerEngine")

    # ── Organ loader helpers ───────────────────────────────────────────

    def _try(self, name: str, layer: str, module_path: str,
             class_name: str | None = None, **kwargs) -> Any:
        """Try to import and instantiate an organ. Returns instance or None."""
        self._total_organs += 1
        status = OrganStatus(name, layer)
        self._organs[name] = status
        try:
            mod = __import__(module_path, fromlist=[class_name] if class_name else [])
            if class_name:
                cls = getattr(mod, class_name)
                if kwargs:
                    instance = cls(**kwargs)
                else:
                    try:
                        instance = cls()
                    except TypeError:
                        instance = cls  # Store class if can't instantiate
                status.instance = instance
            else:
                status.instance = mod  # Whole module as organ
            status.loaded = True
            self._loaded_organs += 1
            return status.instance
        except Exception as e:
            status.error = str(e)[:120]
            return None

    def _register_organ(self, name: str, layer: str, loaded: bool,
                        instance: Any = None) -> None:
        """Register an already-constructed organ."""
        self._total_organs += 1
        status = OrganStatus(name, layer)
        status.loaded = loaded
        status.instance = instance
        if loaded:
            self._loaded_organs += 1
        self._organs[name] = status

    # ── Bridge initialization ──────────────────────────────────────────

    def _init_bridges_sync(self) -> None:
        """Initialize bridges (constructors only, async init deferred)."""
        try:
            from bridges.fungal_bridge import FungalBridge
            self._fungal_bridge = FungalBridge()
            self._register_organ("fungal_bridge", "bridges", True, self._fungal_bridge)
            import mcp.tools.evolution as evo
            evo._fungal_bridge = self._fungal_bridge
        except Exception as e:
            self._register_organ("fungal_bridge", "bridges", False)
            import mcp.tools.evolution as evo
            evo._fungal_bridge = None

        try:
            from bridges.mirofish_bridge import MiroFishBridge
            self._mirofish_bridge = MiroFishBridge()
            self._register_organ("mirofish_bridge", "bridges", True, self._mirofish_bridge)
            import mcp.tools.evolution as evo
            evo.set_bridge(self._mirofish_bridge)
        except Exception as e:
            self._register_organ("mirofish_bridge", "bridges", False)
            import mcp.tools.evolution as evo
            evo.set_bridge(None)

    async def _init_bridges_async(self) -> None:
        """Async initialization for bridges that need event loop."""
        if hasattr(self, '_fungal_bridge') and self._fungal_bridge:
            try:
                await self._fungal_bridge.initialize()
            except Exception as e:
                pass

        if hasattr(self, '_mirofish_bridge') and self._mirofish_bridge:
            try:
                await self._mirofish_bridge.initialize()
            except Exception as e:
                pass

    # ══════════════════════════════════════════════════════════════════
    # COMMAND WIRING
    # ══════════════════════════════════════════════════════════════════

    def _wire_commands(self) -> None:
        """Connect REPL slash commands to MCP tool handlers."""
        self.repl.register_handler("/status", self._cmd_status)
        self.repl.register_handler("/evolve", self._cmd_evolve)
        self.repl.register_handler("/memory", self._cmd_memory)
        self.repl.register_handler("/skills", self._cmd_skills)
        self.repl.register_handler("/genome", self._cmd_genome)
        self.repl.register_handler("/sandbox", self._cmd_sandbox)
        self.repl.register_handler("/scan", self._cmd_scan)
        self.repl.register_handler("/config", self._cmd_config)
        self.repl.register_handler("/audit", self._cmd_audit)
        self.repl.register_handler("/digest", self._cmd_digest)
        self.repl.register_handler("/mode", self._cmd_mode)

    async def _handle_llm_message(self, prompt: str) -> str:
        """Send a message through the Sclerotium body (Gateway -> mycelium.md)."""
        from gateways.models import RoutingStrategy
        try:
            response = await self.gateway.chat(
                prompt=prompt, model="deepseek-v4-pro", provider="deepseek",
                strategy=RoutingStrategy.BEST)
            content = response.get("content", "") if isinstance(response, dict) else str(response)
            return content if content else f"[Gateway empty. Error: {response.get('error', 'unknown')}]"
        except Exception as exc:
            return f"[Gateway error: {exc}]"

    # ══════════════════════════════════════════════════════════════════
    # COMMAND HANDLERS
    # ══════════════════════════════════════════════════════════════════

    async def _cmd_status(self, _args: list[str]) -> dict[str, Any]:
        handler = self._tools.get_handler("system_status")
        if handler:
            result = await handler()
            if "evolution" in result:
                self.evolution.update({
                    "current_generation": result["evolution"].get("total_generations_run", 0),
                    "phase": result["evolution"].get("phase", "IDLE"),
                    "fcpi_total": result["evolution"].get("current_best_fcpi", 0),
                })
            self.dashboard.push_event("system_status", "Status queried")
            return result
        return {"error": "system_status not available"}

    async def _cmd_evolve(self, args: list[str]) -> dict[str, Any]:
        generations = 10
        population = 50
        try:
            if args: generations = int(args[0])
        except ValueError: pass
        for i, a in enumerate(args):
            if a == "--population" and i + 1 < len(args):
                try: population = int(args[i + 1])
                except ValueError: pass
        handler = self._tools.get_handler("evolution_start")
        if handler:
            self.dashboard.push_event("evolution.tick",
                                      f"Starting {generations} generations (pop={population})")
            result = await handler(generations=generations, population=population)
            self.dashboard.push_event("evolution.tick",
                                      f"Evolution complete — FCPI: {result.get('fcpi_total', 'N/A')}")
            return result
        return {"error": "evolution_start not available"}

    async def _cmd_memory(self, args: list[str]) -> None:
        query = " ".join(args) if args else ""
        if not query:
            self.repl.render_error("Usage: /memory <query>")
            return
        handler = self._tools.get_handler("memory_search")
        if handler:
            results = await handler(query=query)
            self.memory_screen.render_search_results(query, results, self.console)

    async def _cmd_skills(self, _args: list[str]) -> None:
        handler = self._tools.get_handler("skill_list")
        if handler:
            skills = await handler()
            table = Table(title="Registered Skills", border_style="cyan")
            table.add_column("Name", width=20, style="bold")
            table.add_column("Module", width=18, style="dim")
            table.add_column("Category", width=14)
            table.add_column("Version", width=8)
            for s in skills[:30]:
                table.add_row(s.get("name", "?")[:18], s.get("module", "?")[:16],
                              s.get("category", "?")[:12], s.get("version", "?")[:6])
            if not skills: table.add_row("(none)", "", "", "")
            self.console.print(table)

    async def _cmd_genome(self, args: list[str]) -> None:
        if args:
            handler = self._tools.get_handler("genome_get")
            if handler:
                self.repl.render_json(await handler(genome_id=args[0]))
            return
        handler = self._tools.get_handler("genome_list")
        if handler:
            genomes = await handler(top_n=10)
            self.dashboard.update_genomes(genomes)
            table = Table(title="Top Genomes", border_style="cyan")
            table.add_column("Genome ID", width=14)
            table.add_column("FCPI", width=8, justify="right")
            table.add_column("Gen", width=6)
            for g in genomes:
                table.add_row(g.get("genome_id", "")[:12],
                              f"{g.get('fcpi_total', 0):.3f}",
                              str(g.get("generation", "?")))
            if not genomes: table.add_row("(none)", "", "")
            self.console.print(table)

    async def _cmd_sandbox(self, args: list[str]) -> None:
        code = " ".join(args)
        if not code:
            self.repl.render_error("Usage: /sandbox <python_code>")
            return
        handler = self._tools.get_handler("sandbox_execute")
        if handler:
            result = await handler(code=code)
            self.repl.render_code(code, "python")
            self.console.print(f"stdout: {result.get('stdout', '')}")
            if result.get("stderr"):
                self.console.print(f"stderr: {result['stderr']}", style="red")
            self.console.print(f"exit_code={result.get('exit_code')} | "
                               f"duration={result.get('duration_ms', 0):.0f}ms")

    async def _cmd_scan(self, args: list[str]) -> dict[str, Any]:
        path = args[0] if args else "."
        handler = self._tools.get_handler("scan_code")
        if handler:
            result = await handler(path=path)
            issues = result.get("issues", [])
            scores = result.get("scores", {})
            self.dashboard.push_event("scan", f"Code scan: {len(issues)} issues found")
            return {"issues_found": len(issues), "scores": scores}
        return {"error": "scan_code not available"}

    async def _cmd_config(self, args: list[str]) -> dict[str, Any]:
        handler = self._tools.get_handler("system_config")
        if not handler: return {"error": "system_config not available"}
        if not args: return await handler()
        if len(args) == 1: return await handler(key=args[0])
        return await handler(key=args[0], value=args[1])

    async def _cmd_audit(self, _args: list[str]) -> dict[str, Any]:
        return {"status": "Audit log — Phase 2D"}

    async def _cmd_digest(self, _args: list[str]) -> dict[str, Any]:
        return {"status": "Daily digest — Phase 2E"}

    async def _cmd_mode(self, args: list[str]) -> dict[str, Any]:
        if not args:
            return {"error": "Usage: /mode <work|sleep|game|meeting|creative>"}
        profile = args[0]
        valid = {"work", "sleep", "game", "meeting", "creative"}
        if profile not in valid:
            return {"error": f"Invalid: {profile}. Valid: {', '.join(sorted(valid))}"}
        self.dashboard.push_event("mode.switch", f"Switching to profile: {profile}")
        return {"active_profile": profile, "status": "switched"}

    # ══════════════════════════════════════════════════════════════════
    # STATUS REPORT — full body organ map
    # ══════════════════════════════════════════════════════════════════

    def _organ_report(self) -> dict:
        """Aggregate organ status across all three systems."""
        layers: dict[str, dict] = {}
        for name, s in sorted(self._organs.items()):
            layers.setdefault(s.layer, {"total": 0, "loaded": 0, "organs": []})
            layers[s.layer]["total"] += 1
            if s.loaded:
                layers[s.layer]["loaded"] += 1
            layers[s.layer]["organs"].append({
                "name": name, "loaded": s.loaded,
                "error": s.error if not s.loaded else None,
            })
        return {
            "total": self._total_organs,
            "loaded": self._loaded_organs,
            "percent": round(self._loaded_organs / max(self._total_organs, 1) * 100, 1),
            "layers": layers,
        }

    def print_full_body_report(self) -> None:
        """Print the complete full-body organ status to console."""
        report = self._organ_report()
        pct = report["percent"]
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))

        self.console.print()
        self.console.print(Panel(
            Text(f"🧬 SCLEROTIUM OS — FULL BODY STARTUP", style="bold cyan", justify="center"),
            border_style="cyan"))
        self.console.print(f"  Organs: [{bar}] {report['loaded']}/{report['total']} ({pct}%)")
        self.console.print()

        # By system grouping
        system_groups = {
            "🦑 SCLEROTIUM OS": ["kernel", "stg", "apotheosis", "cosmic", "genesis",
                                  "innovation", "omega", "advanced", "sovereign", "cache",
                                  "gateways", "platforms", "automation", "scheduler"],
            "🍄 fungal-cortex": ["external_fungal"],
            "🐟 MiroFish": ["external_mirofish"],
        }

        for sys_name, layer_names in system_groups.items():
            sys_total = 0
            sys_loaded = 0
            layer_lines: list[str] = []
            for lname in layer_names:
                info = report["layers"].get(lname)
                if info:
                    sys_total += info["total"]
                    sys_loaded += info["loaded"]
                    l_bar = "▓" * info["loaded"] + "·" * (info["total"] - info["loaded"])
                    # Show failed organ names
                    failed = [o["name"] for o in info["organs"] if not o["loaded"]]
                    fail_str = f"  ⚡ {', '.join(failed[:5])}" if failed else ""
                    if len(failed) > 5:
                        fail_str += f" +{len(failed)-5} more"
                    layer_lines.append(f"  {lname:<22} [{l_bar}] {info['loaded']}/{info['total']}{fail_str}")
            if sys_total > 0:
                sys_pct = round(sys_loaded / max(sys_total, 1) * 100)
                sys_bar = "█" * (sys_pct // 5) + "░" * (20 - sys_pct // 5)
                self.console.print(f"  {sys_name} [{sys_bar}] {sys_loaded}/{sys_total} ({sys_pct}%)")
                for line in layer_lines:
                    self.console.print(line)
                self.console.print()

        # Bridge organs (loaded from external systems)
        if hasattr(self, '_fungal_bridge') and self._fungal_bridge:
            self._fungal_bridge.print_status()
            self.console.print()
        if hasattr(self, '_mirofish_bridge') and self._mirofish_bridge:
            self._mirofish_bridge.print_status()
            self.console.print()

    # ══════════════════════════════════════════════════════════════════
    # RUN MODES
    # ══════════════════════════════════════════════════════════════════

    def run_dashboard(self) -> None:
        self.dashboard.render(self.console)

    def run_status(self) -> None:
        status = self.dashboard.render_compact()
        self.console.print(f"[cyan]{status}[/cyan]")

    async def run_repl(self) -> None:
        await self.repl.run_loop()

    async def run(self) -> None:
        """Main entry point — Claude Code-style Textual TUI is DEFAULT."""
        args = sys.argv[1:]

        # ── Legacy Rich REPL mode (opt-in only) ──
        if "--legacy" in args:
            self.print_full_body_report()
            await self._init_bridges_async()
            if hasattr(self, '_fungal_bridge') and self._fungal_bridge:
                self._fungal_bridge.print_status()
            if hasattr(self, '_mirofish_bridge') and self._mirofish_bridge:
                self._mirofish_bridge.print_status()
            if "--dashboard" in args:
                self.run_dashboard()
            elif "--status" in args:
                self.run_status()
            else:
                await self.run_repl()
            return

        # ── DEFAULT: Claude Code-style Textual TUI ──
        await self._run_tui()

    async def _run_tui(self) -> None:
        """Launch the Claude Code-style Textual TUI."""
        from cli.tui.app import SclerotiumTUI

        # Pre-init bridges for full body awareness
        await self._init_bridges_async()

        app = SclerotiumTUI()
        await app.run_async()


if __name__ == "__main__":
    cli = SclerotiumCLI()
    asyncio.run(cli.run())
