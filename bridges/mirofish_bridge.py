"""Sclerotium OS — Bridge to MiroFish evolution engine. Loads ALL 28 organs.

Fully expanded: 6 arenas + core services + models + utils.
Uses importlib to bypass heavy dependencies (Zep Cloud, Flask, etc.)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from kernel.project_paths import add_subsystem_paths

add_subsystem_paths()


def _ensure_packages() -> None:
    """Register package stubs for MiroFish imports."""
    from types import ModuleType
    _packages = [
        ("app", "app"),
        ("app/services", "app.services"),
        ("app/services/arenas", "app.services.arenas"),
        ("app/services/utils", "app.services.utils"),
        ("app/services/models", "app.services.models"),
        ("app/models", "app.models"),
        ("app/models/utils", "app.models.utils"),
        ("app/api", "app.api"),
        ("app/utils", "app.utils"),
        ("app/utils/utils", "app.utils.utils"),
    ]
    for pkg_path, pkg_name in _packages:
        if pkg_name not in sys.modules:
            mod = ModuleType(pkg_name)
            mod.__path__ = [str(_MIROFISH / pkg_path)]
            mod.__package__ = pkg_name
            sys.modules[pkg_name] = mod


def _import_module(rel_path: str, module_name: str) -> Any:
    """Import a single Python file directly, bypassing __init__.py chains."""
    _ensure_packages()
    full_path = _MIROFISH / rel_path
    spec = importlib.util.spec_from_file_location(
        module_name, str(full_path),
        submodule_search_locations=[str(full_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {rel_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class OrganStatus:
    def __init__(self, name: str, layer: str):
        self.name = name; self.layer = layer
        self.loaded = False; self.error: str | None = None; self.instance: Any = None


class MiroFishBridge:
    """Unified adapter for ALL MiroFish services (28 organs)."""

    def __init__(self) -> None:
        self._initialized = False
        self._organs: dict[str, OrganStatus] = {}
        self._total = 0; self._loaded = 0

    async def initialize(self) -> dict[str, bool]:
        if self._initialized: return {n: s.loaded for n, s in self._organs.items()}
        _ensure_packages()

        # 6 Arenas
        for name, cls in [
            ("coding_arena", "CodingArena"), ("coordination_arena", "CoordinationArena"),
            ("safety_arena", "SafetyArena"), ("decision_arena", "DecisionArena"),
            ("emergence_arena", "EmergenceArena"), ("performance_arena", "PerformanceArena"),
        ]:
            self._try_load(name, "arenas", f"app/services/arenas/{name}.py",
                           f"app.services.arenas.{name}", cls)
        self._try_load("arena_base", "arenas", "app/services/arenas/arena_base.py",
                       "app.services.arenas.arena_base", "FCPIDimension")

        # Core services
        for name, path, mod, cls in [
            ("evolution_manager", "app/services/evolution_generation_manager.py",
             "app.services.evolution_generation_manager", "EvolutionGenerationManager"),
            ("fitness_extractor", "app/services/fitness_extractor.py",
             "app.services.fitness_extractor", "EmergentFitnessExtractor"),
            ("live_simulator", "app/services/live_simulation_engine.py",
             "app.services.live_simulation_engine", "LiveAgentSimulator"),
            ("dgm_bridge", "app/services/dgm_bridge.py", "app.services.dgm_bridge", "DGMBridge"),
            ("mycelium_bridge", "app/services/mycelium_bridge.py",
             "app.services.mycelium_bridge", "MyceliumBridge"),
            ("oasis_bridge", "app/services/oasis_bridge.py", "app.services.oasis_bridge", "OasisBridge"),
            ("graph_builder", "app/services/graph_builder.py",
             "app.services.graph_builder", "GraphBuilderService"),
            ("ontology_generator", "app/services/ontology_generator.py",
             "app.services.ontology_generator", "OntologyGenerator"),
            ("oasis_profile_generator", "app/services/oasis_profile_generator.py",
             "app.services.oasis_profile_generator", "OasisProfileGenerator"),
            ("simulation_manager", "app/services/simulation_manager.py",
             "app.services.simulation_manager", "SimulationManager"),
            ("simulation_runner", "app/services/simulation_runner.py",
             "app.services.simulation_runner", "SimulationRunner"),
            ("simulation_config_generator", "app/services/simulation_config_generator.py",
             "app.services.simulation_config_generator", "SimulationParameters"),
            ("simulation_ipc", "app/services/simulation_ipc.py",
             "app.services.simulation_ipc", "SimulationIPCClient"),
            ("text_processor", "app/services/text_processor.py",
             "app.services.text_processor", "TextProcessor"),
            ("report_agent", "app/services/report_agent.py",
             "app.services.report_agent", "ReportOutline"),
            ("report_manager", "app/services/report_agent.py",
             "app.services.report_agent", "ReportLogger"),
        ]:
            self._try_load(name, "services", path, mod, cls)

        # Models
        for name, path, mod, cls in [
            ("project_manager", "app/models/project.py", "app.models.project", "ProjectManager"),
            ("task_manager", "app/models/task.py", "app.models.task", "TaskManager"),
        ]:
            self._try_load(name, "models", path, mod, cls)

        # Utils
        for name, path, mod, cls in [
            ("llm_client", "app/utils/llm_client.py", "app.utils.llm_client", "LLMClient"),
            ("file_parser", "app/utils/file_parser.py", "app.utils.file_parser", "FileParser"),
            ("retry_client", "app/utils/retry.py", "app.utils.retry", "RetryableAPIClient"),
        ]:
            self._try_load(name, "utils", path, mod, cls)

        self._initialized = self._loaded > 0
        return {n: s.loaded for n, s in self._organs.items()}

    def _try_load(self, name: str, layer: str, path: str, mod_name: str, cls_name: str) -> Any:
        self._total += 1
        status = OrganStatus(name, layer); self._organs[name] = status
        try:
            mod = _import_module(path, mod_name)
            if cls_name == "FCPIDimension":
                status.instance = getattr(mod, cls_name)
            else:
                cls = getattr(mod, cls_name)
                try: status.instance = cls()
                except TypeError: status.instance = cls
            status.loaded = True; self._loaded += 1
            return status.instance
        except Exception as e:
            status.error = str(e)[:120]; return None

    def _get(self, name: str) -> Any:
        s = self._organs.get(name); return s.instance if s and s.loaded else None

    async def shutdown(self) -> None: self._initialized = False

    def status_report(self) -> dict:
        layers: dict = {}
        for name, s in sorted(self._organs.items()):
            layers.setdefault(s.layer, {"total":0,"loaded":0,"organs":[]})
            layers[s.layer]["total"] += 1
            if s.loaded: layers[s.layer]["loaded"] += 1
            layers[s.layer]["organs"].append({"name":name,"loaded":s.loaded,"error":s.error if not s.loaded else None})
        return {"system":"MiroFish","total_organs":self._total,"loaded":self._loaded,
                "percent":round(self._loaded/max(self._total,1)*100,1),"layers":layers}

    # ── Evolution API ──────────────────────────────────────────────────

    async def evolution_start(self, generations=10, population=50, work_dir="uploads/evolution", resume=False) -> dict:
        mgr = self._get("evolution_manager")
        if mgr is None: return {"status":"error","errors":["EvolutionManager not loaded"]}
        try:
            result = await mgr.run(generations=generations, population_size=population,
                                   work_dir=work_dir, resume=resume)
            return {"status":"completed","generations_completed":getattr(result,"generations_completed",0),
                    "fcpi_total":getattr(result,"fcpi_total",0.0),"panarchy_phase":getattr(result,"panarchy_phase","r")}
        except Exception as e: return {"status":"error","errors":[str(e)]}

    async def evolution_status(self) -> dict:
        mgr = self._get("evolution_manager")
        if mgr is None: return {"phase":"PENDING","current_generation":0}
        return {"current_generation":getattr(mgr,"current_generation",0),"phase":getattr(mgr,"phase","PENDING"),
                "panarchy_phase":getattr(mgr,"panarchy_phase","r"),"population_size":getattr(mgr,"population_size",0)}

    # ── v5.2 Full-Body Genome ──────────────────────────────────────────

    def _get_genome(self) -> Any:
        path = _MIROFISH / "app/services/full_body_genome.py"
        spec = importlib.util.spec_from_file_location("mirofish_genome", str(path))
        if spec is None or spec.loader is None: return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("mirofish_genome", mod)
        spec.loader.exec_module(mod)
        return mod.get_genome()

    def get_full_body_genome(self) -> dict:
        try:
            g = self._get_genome()
            return g.get_api_data() if g else {}
        except Exception: return {}

    def feed_sclerotium_to_genome(self, data: dict) -> bool:
        try:
            g = self._get_genome()
            if g: g.feed_sclerotium_data(data); return True
        except Exception: pass
        return False

    def evolve_genome(self) -> dict:
        try:
            g = self._get_genome()
            if g: g.evolve(); return g.get_api_data()
        except Exception: pass
        return {}
