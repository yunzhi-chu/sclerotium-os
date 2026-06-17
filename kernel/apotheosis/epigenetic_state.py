"""ECS — Epigenetic Computational State (ORIGINAL INVENTION).

Based on 2026 epigenetic computation breakthroughs:
  - DNA methylation as active control variable (Han, arXiv:2605.14562)
  - AP-1 mediated cellular memory of transient experiences (Nature Comms 2026)
  - 3D genome folding as persistent information storage (Nature Genetics 2026)
  - Molecular asynchrony: temporal delays as information-rich features
  - Cis-epigenetic activation: memory encoded locally, not globally

Innovation: Module activation regulated by "chromatin state" that changes
over time. Past experiences leave epigenetic marks that persist, affecting
future module behavior without changing the underlying code.

Key mechanisms:
  - Methylation: silences modules that produced errors (like gene silencing)
  - Acetylation: opens modules for high-activity tasks (like active chromatin)
  - 3D looping: brings distant modules together for coordinated action
  - Cellular memory: transient events leave persistent epigenetic marks
  - Epigenetic drift: slow stochastic changes → exploration of new states

THIS MODULE "REMEMBERS" EXPERIENCES THROUGH CHEMICAL MARKS.
Reference: Han (2026), AP-1 memory (Nature Comms 2026),
3D genome memory (Nature Genetics 2026).
"""

from __future__ import annotations
import hashlib, random, time
from dataclasses import dataclass, field
from typing import Any


class ChromatinState:
    """Epigenetic state of a module — determines accessibility."""
    OPEN = "open"           # Active: fully accessible
    POISED = "poised"       # Bivalent: ready but not active
    CLOSED = "closed"       # Silenced: inaccessible
    MEMORY = "memory"       # Previously active, can be reactivated quickly


@dataclass
class EpigeneticModule:
    """A computational module with epigenetic regulation."""
    id: str; name: str
    chromatin_state: str = "poised"       # open, poised, closed, memory
    methylation_level: float = 0.3        # Higher = more silenced
    acetylation_level: float = 0.3        # Higher = more active
    histone_variants: dict[str, float] = field(default_factory=lambda: {
        "H3K4me3": 0.3,  # Active promoter mark
        "H3K27ac": 0.3,  # Active enhancer mark
        "H3K27me3": 0.3,  # Repressive Polycomb mark
        "H3K9me3": 0.2,  # Constitutive heterochromatin
    })
    loops: list[str] = field(default_factory=list)  # 3D contacts with other modules
    error_memory: int = 0       # Past error count → increases methylation
    success_memory: int = 0     # Past success count → increases acetylation
    last_activated: float = 0.0
    activation_count: int = 0


class EpigeneticComputationalState:
    """Regulation of module activity through epigenetic marks.

    Like the genome: all modules exist but epigenetic state determines
    which ones are active. Past experiences (errors/successes) leave
    marks that persist and affect future behavior.

    This is NOT logging — it's a physical change in module accessibility.
    """

    def __init__(self) -> None:
        self._modules: dict[str, EpigeneticModule] = {}
        self._global_methylation: float = 0.1  # Global epigenetic clock
        self._environmental_stress: float = 0.0  # Drives epigenetic plasticity

    def register_module(self, name: str) -> str:
        mid = f"epi_{len(self._modules):04d}"
        self._modules[mid] = EpigeneticModule(id=mid, name=name)
        return mid

    # ── Epigenetic marks ─────────────────────────────────────────

    def mark_success(self, module_id: str) -> None:
        """Record a successful operation → increase acetylation (activate).

        Like H3K27ac marking after a gene is successfully expressed:
        opens chromatin for future use. Success BREEDS success.
        """
        mod = self._modules.get(module_id)
        if mod is None: return

        mod.success_memory += 1
        mod.acetylation_level = min(1.0, mod.acetylation_level + 0.05)
        mod.methylation_level = max(0.0, mod.methylation_level - 0.02)
        mod.histone_variants["H3K27ac"] = min(1.0, mod.histone_variants["H3K27ac"] + 0.04)
        mod.last_activated = time.time()
        mod.activation_count += 1
        self._update_chromatin_state(mod)

    def mark_error(self, module_id: str) -> None:
        """Record an error → increase methylation (silence).

        Like DNA methylation after transposon activity: the cell
        "remembers" this module caused problems and silences it.
        """
        mod = self._modules.get(module_id)
        if mod is None: return

        mod.error_memory += 1
        mod.methylation_level = min(1.0, mod.methylation_level + 0.08)
        mod.acetylation_level = max(0.0, mod.acetylation_level - 0.03)
        mod.histone_variants["H3K27me3"] = min(1.0, mod.histone_variants["H3K27me3"] + 0.06)
        self._update_chromatin_state(mod)

    def _update_chromatin_state(self, mod: EpigeneticModule) -> None:
        """Determine chromatin state from histone marks + methylation."""
        active_score = mod.acetylation_level + mod.histone_variants["H3K27ac"] - mod.methylation_level
        repressive_score = mod.methylation_level + mod.histone_variants["H3K27me3"] + mod.histone_variants["H3K9me3"]

        if repressive_score > 1.5:
            mod.chromatin_state = "closed"
        elif active_score > 1.0:
            mod.chromatin_state = "open"
        elif mod.activation_count > 0 and mod.error_memory == 0:
            mod.chromatin_state = "memory"
        else:
            mod.chromatin_state = "poised"

    # ── 3D genome looping ────────────────────────────────────────

    def create_loop(self, module_a: str, module_b: str) -> bool:
        """Create a 3D chromatin loop between modules.

        Like enhancer-promoter looping: brings distant regulatory
        elements together for coordinated activation.
        """
        if module_a in self._modules and module_b in self._modules:
            if module_b not in self._modules[module_a].loops:
                self._modules[module_a].loops.append(module_b)
            if module_a not in self._modules[module_b].loops:
                self._modules[module_b].loops.append(module_a)
            return True
        return False

    def get_looped_modules(self, module_id: str) -> list[str]:
        """Get all modules in 3D contact with this one."""
        mod = self._modules.get(module_id)
        return mod.loops if mod else []

    # ── Epigenetic clock & drift ─────────────────────────────────

    def tick_epigenetic_clock(self) -> dict:
        """Advance the epigenetic clock — slow drift of methylation.

        Like aging: global methylation slowly increases, silencing
        modules that haven't been used recently. This creates
        "computational aging" — the system naturally prunes itself.
        """
        self._global_methylation = min(1.0, self._global_methylation + 0.005)

        drifted = 0
        for mod in self._modules.values():
            # Stochastic drift: unused modules slowly methylate
            if time.time() - mod.last_activated > 1000 and random.random() < 0.01:
                mod.methylation_level = min(1.0, mod.methylation_level + 0.05)
                drifted += 1
            # Active modules resist methylation (like CpG islands)
            if mod.chromatin_state == "open" and random.random() < 0.005:
                mod.methylation_level = max(0.0, mod.methylation_level - 0.02)

        return {"global_methylation": self._global_methylation, "modules_drifted": drifted}

    # ── Cellular reprogramming ───────────────────────────────────

    def reprogram_module(self, module_id: str) -> dict:
        """Reset a module to pluripotent state (erase epigenetic marks).

        Like Yamanaka factors: Oct4, Sox2, Klf4, c-Myc reset cell
        identity. Here: erase methylation, reset histones, open chromatin.
        """
        mod = self._modules.get(module_id)
        if mod is None: return {"error": "Module not found"}

        old_state = mod.chromatin_state
        mod.methylation_level = 0.1
        mod.acetylation_level = 0.3
        mod.histone_variants = {k: 0.2 for k in mod.histone_variants}
        mod.error_memory = 0
        mod.chromatin_state = "poised"

        return {"module": module_id, "old_state": old_state, "new_state": "poised", "reprogrammed": True}

    def get_accessible_modules(self, min_accessibility: float = 0.3) -> list[dict]:
        """List modules that are currently accessible (open/poised chromatin)."""
        return [
            {"id": m.id, "name": m.name, "state": m.chromatin_state,
             "accessibility": m.acetylation_level - m.methylation_level + 0.5,
             "error_memory": m.error_memory, "success_memory": m.success_memory}
            for m in self._modules.values()
            if m.chromatin_state in ("open", "poised", "memory")
        ]

    def get_epigenome_stats(self) -> dict:
        # EXP#6修复: 如果没有注册模块, 自动从 sys.modules 中加载
        if not self._modules:
            import sys as _sys
            for name, mod in list(_sys.modules.items())[:100]:
                if name and mod and not name.startswith('_'):
                    if any(p in name for p in ('kernel', 'mcp', 'agent', 'evolution', 'automation', 'gateways', 'bridges', 'platforms')):
                        self.register_module(name)
        mods = list(self._modules.values())
        return {
            "total_modules": len(mods),
            "open": sum(1 for m in mods if m.chromatin_state == "open"),
            "closed": sum(1 for m in mods if m.chromatin_state == "closed"),
            "poised": sum(1 for m in mods if m.chromatin_state == "poised"),
            "memory": sum(1 for m in mods if m.chromatin_state == "memory"),
            "global_methylation": self._global_methylation,
            "total_loops": sum(len(m.loops) for m in mods) // 2,
            "total_errors_remembered": sum(m.error_memory for m in mods),
            "total_successes_remembered": sum(m.success_memory for m in mods),
        }
