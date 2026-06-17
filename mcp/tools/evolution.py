"""MCP Evolution Tools — evolution_start, evolution_status, genome_list, genome_get, genome_mutate.

Bridges to MiroFish Phase 1 Evolution Engine via MiroFishBridge.
When bridge unavailable, uses LOCAL FullBodyGenome for real data.
"""

from __future__ import annotations

from typing import Any

from mcp.server import ToolRegistry


# ── Global bridge + local genome references ────────────────────────────

_bridge: Any = None  # MiroFishBridge instance
_local_genome: Any = None  # Local FullBodyGenome fallback


def set_bridge(bridge: Any) -> None:
    """Inject the MiroFishBridge instance."""
    global _bridge
    _bridge = bridge


def set_local_genome(genome: Any) -> None:
    """Inject local FullBodyGenome as fallback when MiroFish unavailable."""
    global _local_genome
    _local_genome = genome


def _get_genome():
    """Get best available genome — MiroFish or local."""
    return _local_genome


# ── evolution_start ───────────────────────────────────────────────────


async def _evolution_start(
    generations: int = 10,
    population: int = 50,
    work_dir: str = "uploads/evolution",
    resume: bool = False,
) -> dict[str, Any]:
    """Start a multi-generation evolution run across all 6 FCPI arenas."""
    global _local_genome  # 声明在函数顶部, 避免 SyntaxError (PEP 3104)

    if _bridge is not None:
        return await _bridge.evolution_start(
            generations=generations, population=population,
            work_dir=work_dir, resume=resume,
        )

    # 本地回退: 运行本地进化循环
    try:
        from evolution.evolution_loop import EvolutionLoop
        if _local_genome:
            loop = EvolutionLoop(genome=_local_genome, mode="auto")
            for _ in range(min(generations, 10)):
                result = loop.evolve_generation()
            # 进化完成后, 将全局引用指向 loop._genome (进化后的基因组),
            # 否则 _local_genome 仍指向原始基因组 (generation=0), 保存会覆盖正确数据。
            _local_genome = loop._genome
            _local_genome.save_checkpoint()
            state = loop.get_state()
            return {
                "status": "completed",
                "generations_completed": state.generation,
                "fitness": round(state.current_score, 4),
                "improvements": state.improvements,
                "regressions": state.regressions,
                "engine": "local_full_body_genome",
            }
    except Exception as e:
        return {"status": "error", "errors": [f"Local evolution failed: {e}"]}

    return {"status": "error", "errors": ["Evolution engine not available — MiroFish bridge not connected and no local genome"]}


# ── evolution_status ──────────────────────────────────────────────────


async def _evolution_status() -> dict[str, Any]:
    """Query current evolution state — MiroFish or local genome."""
    if _bridge is not None:
        return await _bridge.evolution_status()

    # 本地基因组实时数据
    if _local_genome:
        try:
            top = _local_genome.get_top_tools(5)
            dims = {}
            for d in ["tools", "prompts", "personalities", "memories", "providers", "skills", "organs", "arbiters"]:
                genes = getattr(_local_genome, f"_{d}_genes", {})
                if genes:
                    dims[d] = round(sum(genes.values()) / len(genes), 4)
            return {
                "engine": "local_full_body_genome",
                "generation": _local_genome.generation,
                "fitness": round(_local_genome.fitness, 4),
                "top_tools": [{"name": t, "weight": round(w, 3)} for t, w in top],
                "dimensions": dims,
                "total_mutations": getattr(_local_genome, "total_mutations", 0),
                "improvements": getattr(_local_genome, "improvements", 0),
            }
        except Exception as e:
            return {"engine": "local", "error": str(e)[:100]}

    return {"engine": "none", "message": "No evolution engine available — start sclerotium with --wechat or --full"}


# ── evolution_pause / evolution_resume ─────────────────────────────────


async def _evolution_pause() -> dict[str, Any]:
    if _bridge is not None:
        return await _bridge.evolution_pause()
    return {"status": "ok", "message": "Local evolution paused (no-op for in-process engine)"}


async def _evolution_resume() -> dict[str, Any]:
    if _bridge is not None:
        return await _bridge.evolution_resume()
    return {"status": "ok", "message": "Local evolution resumed"}


# ── genome_list ───────────────────────────────────────────────────────


async def _genome_list(top_n: int = 20) -> dict[str, Any]:
    """List genomes — from MiroFish bridge or local genome."""
    if _bridge is not None:
        result = _bridge.genome_list(top_n)
        return {"genomes": result, "total": len(result), "source": "mirofish"} if result else {"genomes": [], "total": 0, "source": "mirofish"}

    # 本地基因组
    if _local_genome:
        try:
            top = _local_genome.get_top_tools(min(top_n, 10))
            return {
                "genomes": [{
                    "genome_id": f"local_gen_{_local_genome.generation}",
                    "generation": _local_genome.generation,
                    "fitness": round(_local_genome.fitness, 4),
                    "top_tools": [{"name": t, "weight": round(w, 3)} for t, w in top],
                }],
                "total": 1,
                "source": "local_full_body_genome",
            }
        except Exception as e:
            return {"genomes": [], "total": 0, "source": "local", "error": str(e)[:100]}

    return {"genomes": [], "total": 0, "source": "none", "message": "No genome available"}


# ── genome_get ────────────────────────────────────────────────────────


async def _genome_get(genome_id: str) -> dict[str, Any]:
    """Get genome detail — from MiroFish or local."""
    if _bridge is not None:
        result = _bridge.genome_get(genome_id)
        if result is None:
            return {"error": f"Genome not found: {genome_id}"}
        return result

    # 本地基因组
    if _local_genome and genome_id.startswith("local_gen"):
        try:
            top = _local_genome.get_top_tools(10)
            # BUG#10修复: FullBodyGenome 的属性名不带复数 's'
            # e.g. _tool_genes (not _tools_genes), _prompt_genes (not _prompts_genes)
            dims = {}
            dim_attr_map = {
                "tools": ("_tool_genes", "_tool_usage"),
                "prompts": ("_prompt_genes", None),
                "personalities": ("_personality_genes", "_personality_usage"),
                "memories": ("_memory_genes", None),
                "providers": ("_provider_genes", None),
                "skills": ("_skill_genes", None),
                "organs": ("_organ_genes", None),
                "arbiters": ("_arbiter_genes", None),
            }
            for d, (attr, _) in dim_attr_map.items():
                genes = getattr(_local_genome, attr, {})
                if genes:
                    dims[d] = {k: round(v, 3) for k, v in sorted(genes.items(), key=lambda x: -x[1])[:5]}
            if not dims:
                dims = {"tools": {}, "prompts": {}, "personalities": {}}
            return {
                "genome_id": genome_id,
                "generation": _local_genome.generation,
                "fitness": round(_local_genome.fitness, 4),
                "dimensions": dims,
                "top_tools": [{"name": t, "weight": round(w, 3)} for t, w in top],
            }
        except Exception as e:
            return {"error": str(e)[:100]}

    return {"error": f"Genome not found: {genome_id}. Use genome_list to see available genomes."}


# ── genome_mutate ─────────────────────────────────────────────────────


async def _genome_mutate(
    genome_id: str,
    mutation_type: str,
    target: str = "",
) -> dict[str, Any]:
    """Apply a mutation to a genome (INSERT/DELETE/SUBSTITUTE/CROSSOVER/DUPLICATE).

    Relies on fungal-cortex DarwinianGodelMachine via FungalBridge.
    Falls back to local genome mutation.
    """
    # 尝试真菌桥接
    try:
        from bridges.fungal_bridge import FungalBridge
        fungal = FungalBridge()
        result = fungal.mutate_genome(genome_id, mutation_type, target)
        if result and "error" not in str(result).lower():
            return result
    except Exception:
        pass

    # 本地基因组突变
    if _local_genome:
        try:
            candidate = _local_genome.mutate(num_mutations=3, strength=1.0)
            return {
                "status": "mutated",
                "genome_id": genome_id,
                "mutation_type": mutation_type,
                "target": target or "random",
                "old_fitness": round(_local_genome.fitness, 4),
                "new_fitness": round(candidate.fitness, 4),
                "engine": "local_full_body_genome",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)[:100]}

    return {"status": "error", "message": "No genome available for mutation"}


# ── Registration ─────────────────────────────────────────────────────


def register_evolution_tools(registry: ToolRegistry) -> None:
    registry.register(
        name="evolution_start",
        description="Start a multi-generation evolution run across all 6 FCPI arenas (coding, coordination, safety, decision, emergence, performance). Returns best FCPI vector, Panarchy phase, and emergent patterns.",
        parameters={
            "type": "object",
            "properties": {
                "generations": {
                    "type": "integer",
                    "description": "Number of generations to run (default: 10)",
                    "default": 10,
                },
                "population": {
                    "type": "integer",
                    "description": "Population size per generation (default: 50)",
                    "default": 50,
                },
                "work_dir": {
                    "type": "string",
                    "description": "Working directory for evolution artifacts",
                    "default": "uploads/evolution",
                },
                "resume": {
                    "type": "boolean",
                    "description": "Resume from last checkpoint",
                    "default": False,
                },
            },
            "required": [],
        },
        handler=_evolution_start,
        category="evolution",
    )

    registry.register(
        name="evolution_status",
        description="Query current evolution state: generation, phase, FCPI vector, Panarchy cycle, population stats.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=_evolution_status,
        category="evolution",
    )

    registry.register(
        name="evolution_pause",
        description="Pause the current evolution run. Can be resumed later.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=_evolution_pause,
        category="evolution",
    )

    registry.register(
        name="evolution_resume",
        description="Resume a previously paused evolution run.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=_evolution_resume,
        category="evolution",
    )

    registry.register(
        name="genome_list",
        description="List top N genomes ranked by FCPI total score.",
        parameters={
            "type": "object",
            "properties": {
                "top_n": {
                    "type": "integer",
                    "description": "Number of top genomes to return (default: 20)",
                    "default": 20,
                },
            },
            "required": [],
        },
        handler=_genome_list,
        category="evolution",
    )

    registry.register(
        name="genome_get",
        description="Get a single genome's full details: FCPI vector, mutation history, skill set.",
        parameters={
            "type": "object",
            "properties": {
                "genome_id": {
                    "type": "string",
                    "description": "Genome ID to retrieve",
                },
            },
            "required": ["genome_id"],
        },
        handler=_genome_get,
        category="evolution",
    )

    registry.register(
        name="genome_mutate",
        description="Apply a mutation (INSERT/DELETE/SUBSTITUTE/CROSSOVER/DUPLICATE) to a genome. Returns new genome ID, verification result, and diff preview.",
        parameters={
            "type": "object",
            "properties": {
                "genome_id": {
                    "type": "string",
                    "description": "Genome ID to mutate",
                },
                "mutation_type": {
                    "type": "string",
                    "description": "Mutation type: INSERT, DELETE, SUBSTITUTE, CROSSOVER, or DUPLICATE",
                    "enum": ["INSERT", "DELETE", "SUBSTITUTE", "CROSSOVER", "DUPLICATE"],
                },
                "target": {
                    "type": "string",
                    "description": "Target module/function/parameter for the mutation",
                    "default": "",
                },
            },
            "required": ["genome_id", "mutation_type"],
        },
        handler=_genome_mutate,
        category="evolution",
    )
