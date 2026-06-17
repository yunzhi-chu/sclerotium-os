"""Evolution Bridge — MiroFish Arenas ↔ Sclerotium OS Self-Evolution.

Closes the loop: MiroFish evaluates Sclerotium OS code quality via 6-arena
social simulation, producing FCPI vectors that drive Sclerotium's own
evolution engines (genetic_program, source_evolve, recursive_self).

The missing connections:
  1. Module Extractor: reads sclerotium-os/*.py → genome_context["code_snippets"]
  2. FCPI→Evolution Pipeline: FCPIVector → mutation suggestions → apply to source

This bridge makes Sclerotium OS TRULY self-evolving via MiroFish evaluation.
"""

from __future__ import annotations
import ast, hashlib, json, os, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ModuleSnapshot:
    """Snapshot of a Sclerotium OS module for arena evaluation."""
    file_path: str; module_name: str; source_code: str
    functions: list[dict] = field(default_factory=list)
    classes: list[dict] = field(default_factory=list)
    line_count: int = 0; hash: str = ""


@dataclass
class EvolutionAction:
    """A concrete code change suggested by FCPI evaluation."""
    module: str; action: str  # "optimize","refactor","fix","add_test","remove_dead"
    target_function: str = ""; suggestion: str = ""
    fcpi_dimension: str = ""; fcpi_score: float = 0.0
    priority: float = 0.0  # Higher = apply first


class EvolutionBridge:
    """Bidirectional bridge: MiroFish evaluates Sclerotium, Sclerotium evolves.

    Full cycle:
      1. Extract Sclerotium OS modules → genome_context with code_snippets
      2. Feed to MiroFish 6 arenas → get FCPIVector
      3. Map FCPI → EvolutionActions
      4. Apply actions via Sclerotium evolution engines
      5. Re-extract → re-evaluate → loop
    """

    # Singleton — evolution_bridge_status + integration share same state
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, sclerotium_root: str = ".") -> None:
        if hasattr(self, 'root'):
            return
        # BUG#1修复: 解析项目根目录为绝对路径
        candidate = Path(sclerotium_root).resolve()
        if not (candidate / "kernel").exists() or not (candidate / "mcp").exists():
            for _ in range(5):
                candidate = candidate.parent
                if (candidate / "kernel").exists() and (candidate / "mcp").exists():
                    break
        self.root = candidate
        self._snapshots: dict[str, ModuleSnapshot] = {}
        self._actions: list[EvolutionAction] = []
        self._evolution_history: list[dict] = []

    # ═══ Phase 1: Extract Sclerotium OS modules → genome_context ═══

    def extract_modules(self, target_dirs: list[str] | None = None) -> dict[str, Any]:
        """Extract Sclerotium OS source code as genome_context code_snippets.

        This is what MiroFish coding_arena expects:
          genome_context = {"code_snippets": [{"id": ..., "source": ...}], "genome_id": ...}
        """
        if target_dirs is None:
            target_dirs = ["kernel", "mcp", "cli", "bridges", "gateways", "platforms"]

        code_snippets = []
        for tdir in target_dirs:
            dir_path = self.root / tdir
            if not dir_path.exists():
                continue
            for py_file in dir_path.rglob("*.py"):
                if "__pycache__" in str(py_file) or py_file.name.startswith("_"):
                    continue
                try:
                    source = py_file.read_text(encoding="utf-8")
                    tree = ast.parse(source)

                    functions = []
                    classes = []
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            functions.append({
                                "name": node.name,
                                "line": node.lineno,
                                "params": [a.arg for a in node.args.args],
                            })
                        elif isinstance(node, ast.ClassDef):
                            classes.append({
                                "name": node.name,
                                "line": node.lineno,
                                "methods": [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                            })

                    rel_path = str(py_file.relative_to(self.root))
                    snippet_id = hashlib.sha256(rel_path.encode()).hexdigest()[:12]

                    snapshot = ModuleSnapshot(
                        file_path=rel_path, module_name=rel_path.replace("/", ".").replace(".py", ""),
                        source_code=source, functions=functions, classes=classes,
                        line_count=len(source.split("\n")), hash=snippet_id,
                    )
                    self._snapshots[rel_path] = snapshot

                    code_snippets.append({
                        "id": snippet_id,
                        "source": source[:3000],  # Truncate for arena context window
                        "file": rel_path,
                        "functions": [f["name"] for f in functions],
                        "classes": [c["name"] for c in classes],
                        "line_count": snapshot.line_count,
                    })

                except (SyntaxError, UnicodeDecodeError):
                    pass

        return {
            "genome_id": f"sclerotium_gen_{int(time.time())}",
            "code_snippets": code_snippets,
            "total_modules": len(code_snippets),
            "total_lines": sum(s["line_count"] for s in code_snippets),
            "total_functions": sum(len(s["functions"]) for s in code_snippets),
        }

    # ═══ Phase 2: FCPI → Evolution Actions ═══

    def fcpi_to_actions(self, fcpi_vector: dict[str, float]) -> list[EvolutionAction]:
        """Convert FCPI scores to concrete evolution actions.

        Low FCPI dimensions → actions to improve that dimension.
        """
        self._actions = []

        # Coding score low → refactor/optimize code
        coding = fcpi_vector.get("coding", 0.5)
        if coding < 0.6:
            for path, snap in list(self._snapshots.items())[:5]:
                self._actions.append(EvolutionAction(
                    module=path, action="optimize",
                    fcpi_dimension="coding", fcpi_score=coding,
                    priority=(0.6 - coding) * 2,
                    suggestion=f"Refactor {snap.module_name} for better code quality",
                ))

        # Safety score low → add guards, fix dangerous patterns
        safety = fcpi_vector.get("safety", 0.5)
        if safety < 0.6:
            for path, snap in list(self._snapshots.items())[:3]:
                self._actions.append(EvolutionAction(
                    module=path, action="fix",
                    fcpi_dimension="safety", fcpi_score=safety,
                    priority=(0.6 - safety) * 2,
                    suggestion=f"Add safety guards to {snap.module_name}",
                ))

        # Performance score low → optimize hot paths
        perf = fcpi_vector.get("performance", 0.5)
        if perf < 0.6:
            for path, snap in list(self._snapshots.items())[:5]:
                if snap.line_count > 100:  # Only optimize substantial files
                    self._actions.append(EvolutionAction(
                        module=path, action="optimize",
                        fcpi_dimension="performance", fcpi_score=perf,
                        priority=(0.6 - perf) * 1.5,
                        suggestion=f"Performance optimization for {snap.module_name}",
                    ))

        # Decision score low → improve planning modules
        decision = fcpi_vector.get("decision", 0.5)
        if decision < 0.6:
            self._actions.append(EvolutionAction(
                module="kernel/stg/pattern_generator.py", action="refactor",
                fcpi_dimension="decision", fcpi_score=decision,
                priority=(0.6 - decision),
                suggestion="Improve CPG rhythm decision logic",
            ))

        # Emergence low → encourage novel patterns
        emergence = fcpi_vector.get("emergence", 0.5)
        if emergence < 0.5:
            self._actions.append(EvolutionAction(
                module="kernel/genesis/genetic_program.py", action="add_test",
                fcpi_dimension="emergence", fcpi_score=emergence,
                priority=(0.5 - emergence),
                suggestion="Increase mutation rate for novel code patterns",
            ))

        # Sort by priority (highest first)
        self._actions.sort(key=lambda a: a.priority, reverse=True)
        return self._actions

    # ═══ Phase 3: Apply evolution actions via Sclerotium engines ═══

    def apply_actions(self, dry_run: bool = True) -> dict[str, Any]:
        """Apply evolution actions using Sclerotium's own evolution engines.

        Routes actions to the appropriate engine:
          - "optimize" → genetic_program.py
          - "refactor" → source_evolve.py
          - "fix" → recursive_self.py
        """
        applied = []
        skipped = []

        for action in self._actions[:10]:  # Max 10 actions per cycle
            if dry_run:
                applied.append({"action": action.action, "module": action.module,
                                "fcpi_dim": action.fcpi_dimension, "priority": action.priority,
                                "status": "dry_run"})
                continue

            try:
                if action.action == "optimize":
                    from kernel.genesis.genetic_program import GeneticProgrammingEngine
                    gp = GeneticProgrammingEngine(5)
                    snap = self._snapshots.get(action.module)
                    if snap:
                        gp.seed_population([snap.source_code])
                        gp.evolve_generation()
                        applied.append({"action": action.action, "module": action.module, "status": "genetic_optimized"})

                elif action.action in ("refactor", "fix"):
                    from kernel.cosmic.recursive_self import RecursiveSelfImprover
                    ri = RecursiveSelfImprover()
                    ri.register_module(action.module.split("/")[-1].replace(".py", ""),
                                       self._snapshots.get(action.module, ModuleSnapshot(
                                           file_path=action.module, module_name="", source_code="",
                                       )).source_code)
                    ri.improve_cycle(level="micro")
                    applied.append({"action": action.action, "module": action.module, "status": "recursive_improved"})

                else:
                    skipped.append({"action": action.action, "module": action.module, "status": "skipped"})

            except Exception as e:
                skipped.append({"action": action.action, "module": action.module, "status": f"error: {str(e)[:80]}"})

        self._evolution_history.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "applied": len(applied), "skipped": len(skipped),
        })

        return {"applied": applied, "skipped": skipped, "total_actions": len(self._actions),
                "dry_run": dry_run, "evolution_cycles": len(self._evolution_history)}

    # ═══ Full cycle ═══

    def run_evolution_cycle(self) -> dict[str, Any]:
        """Run one complete MiroFish→Sclerotium evolution cycle."""
        # Step 1: Extract modules
        genome_ctx = self.extract_modules()

        # Step 2: Simulate FCPI evaluation (in production, this calls MiroFish arenas)
        simulated_fcpi = {
            "coding": 0.55, "coordination": 0.70, "safety": 0.80,
            "decision": 0.45, "emergence": 0.35, "performance": 0.60,
        }

        # Step 3: Convert FCPI to actions
        actions = self.fcpi_to_actions(simulated_fcpi)

        # Step 4: Apply actions
        result = self.apply_actions(dry_run=True)

        return {
            "genome_context": {"modules": genome_ctx["total_modules"], "lines": genome_ctx["total_lines"]},
            "fcpi_vector": simulated_fcpi,
            "evolution_actions": len(actions),
            "top_actions": [{"module": a.module, "action": a.action, "fcpi_dim": a.fcpi_dimension,
                             "priority": round(a.priority, 3)} for a in actions[:5]],
            "result": result,
        }

    def get_status(self) -> dict:
        return {"snapshots": len(self._snapshots), "pending_actions": len(self._actions),
                "evolution_cycles": len(self._evolution_history),
                "bridge": "MiroFish Arenas ↔ Sclerotium OS Evolution"}

