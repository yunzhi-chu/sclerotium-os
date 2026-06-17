"""MCP Apotheosis Tools — Immuno-Attention + Morphogenesis + Epigenetics.

Status: Experimental research modules. Tools require valid kernel state.
"""

from mcp.server import ToolRegistry


async def _immuno_mature(antigen: str = "code_optimization", generations: int = 5) -> dict:
    try:
        from kernel.apotheosis.immuno_attention import ImmunoAttentionNetwork
        ian = ImmunoAttentionNetwork()
        ian.generate_antibody(antigen)
        return ian.affinity_maturation(antigen, generations)
    except Exception as e:
        return {"status": "not_available", "message": f"ImmunoAttentionNetwork failed: {e}"}


async def _morpho_grow(size: int = 50, steps: int = 20) -> dict:
    try:
        from kernel.apotheosis.morphogenic_field import MorphogenicField
        mf = MorphogenicField(size)
        for _ in range(steps):
            mf.step()
        return {"pattern": mf.get_pattern(), "architecture": {k: len(v) for k, v in mf.get_architecture().items()}}
    except Exception as e:
        return {"status": "not_available", "message": f"MorphogenicField failed: {e}"}


async def _epigenetic_learn() -> dict:
    """Get current epigenetic state — reads from live kernel, no hardcoded test data."""
    try:
        from kernel.apotheosis.epigenetic_state import EpigeneticComputationalState
        ecs = EpigeneticComputationalState()
        return ecs.get_epigenome_stats() if hasattr(ecs, 'get_epigenome_stats') else {"status": "no_data", "modules": 0}
    except Exception as e:
        return {"status": "not_available", "message": f"EpigeneticComputationalState failed: {e}"}


async def _self_repair(
    error_type: str = "",
    error_message: str = "",
    module: str = "",
    file_path: str = "",
    line_number: int = 0,
) -> dict:
    """Run self-repair on a detected error. Returns repair result with action taken.

    When the system encounters a code error, call this tool to attempt automatic repair.
    It will try: pip install for ImportError, file creation for FileNotFoundError,
    and provide specific fix instructions for other errors.
    """
    from kernel.self_repair_bridge import SelfRepairBridge, ErrorInfo
    repair = SelfRepairBridge()
    info = ErrorInfo(
        error_type=error_type,
        message=error_message,
        module=module,
        context={"file_path": file_path, "line_number": line_number},
    )
    result = repair.attempt_repair(info)
    return {
        "success": result.success,
        "action": result.action,
        "detail": result.detail,
        "error_type": error_type,
    }


def register_apotheosis_tools(registry: ToolRegistry) -> None:
    tools = [
        ("immuno_mature", "Immunological Attention — antibody affinity maturation (experimental).", _immuno_mature,
         {"type": "object", "properties": {"antigen": {"type": "string", "default": "code_optimization"}, "generations": {"type": "integer", "default": 5}}, "required": []}),
        ("morpho_grow", "Morphogenic Field — self-organizing architecture via reaction-diffusion (experimental).", _morpho_grow,
         {"type": "object", "properties": {"size": {"type": "integer", "default": 50}, "steps": {"type": "integer", "default": 20}}, "required": []}),
        ("epigenetic_learn", "Epigenetic State — reads LIVE chromatin-mediated module regulation (experimental).", _epigenetic_learn,
         {"type": "object", "properties": {}, "required": []}),
        ("self_repair", "Auto-repair code errors: fixes ImportError (pip install), FileNotFoundError (create file), and diagnoses other errors with specific fix instructions.", _self_repair,
         {"type": "object", "properties": {
             "error_type": {"type": "string", "description": "Exception type: ImportError, ModuleNotFoundError, FileNotFoundError, AttributeError, SyntaxError, NameError, KeyError"},
             "error_message": {"type": "string", "description": "The full error message"},
             "module": {"type": "string", "description": "Module where the error occurred", "default": ""},
             "file_path": {"type": "string", "description": "File path for the error", "default": ""},
             "line_number": {"type": "integer", "description": "Line number of the error", "default": 0},
         }, "required": ["error_type", "error_message"]}),
    ]
    for name, desc, handler, params in tools:
        registry.register(name=name, description=desc, parameters=params, handler=handler, category="apotheosis")
