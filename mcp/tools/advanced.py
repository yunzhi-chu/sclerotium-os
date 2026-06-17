"""MCP Advanced Tools — P0/P1/P2 capabilities (30+ new tools)."""

from __future__ import annotations

from typing import Any
from mcp.server import ToolRegistry


# ── P0: Code Refactoring ─────────────────────────────────────────────

async def _refactor_analyze(path: str = ".") -> dict:
    from kernel.advanced.code_refactor import SemanticRefactorEngine
    engine = SemanticRefactorEngine(path)
    return engine.analyze_codebase()

async def _refactor_dead_code(path: str = ".") -> list[dict]:
    from kernel.advanced.code_refactor import SemanticRefactorEngine
    return SemanticRefactorEngine(path).find_dead_code()

async def _refactor_duplicates(path: str = ".") -> list[dict]:
    from kernel.advanced.code_refactor import SemanticRefactorEngine
    return SemanticRefactorEngine(path).find_duplicates()

async def _refactor_impact(symbol: str, path: str = ".") -> dict:
    from kernel.advanced.code_refactor import SemanticRefactorEngine
    return SemanticRefactorEngine(path).call_graph.impact_analysis(symbol)

async def _refactor_callers(symbol: str, path: str = ".") -> list[dict]:
    from kernel.advanced.code_refactor import SemanticRefactorEngine
    engine = SemanticRefactorEngine(path)
    engine.call_graph.build()
    callers = engine.call_graph.find_callers(symbol)
    return [{"name": c.name, "file": c.file, "line": c.line} for c in callers]

# ── P0: Vision Desktop ───────────────────────────────────────────────

async def _vision_click(target: str, method: str = "auto") -> dict:
    from kernel.advanced.vision_desktop import VisionDesktopAgent
    return await VisionDesktopAgent().click(target, method)

async def _vision_type(text: str, target: str = "") -> dict:
    from kernel.advanced.vision_desktop import VisionDesktopAgent
    return await VisionDesktopAgent().type_text(text, target)

async def _vision_screenshot(region: tuple | None = None) -> dict:
    from kernel.advanced.vision_desktop import VisionDesktopAgent
    return await VisionDesktopAgent().screenshot(region)

async def _vision_open(app_name: str) -> dict:
    from kernel.advanced.vision_desktop import VisionDesktopAgent
    return await VisionDesktopAgent().open_app(app_name)

async def _vision_chain(steps: list[dict]) -> dict:
    from kernel.advanced.vision_desktop import VisionDesktopAgent
    return await VisionDesktopAgent().chain_execute(steps)

# ── P0: Formal Verification ──────────────────────────────────────────

async def _verify_code(code: str) -> dict:
    from kernel.advanced.formal_verify import FormalVerifier
    result = FormalVerifier().verify(code)
    return {"passed": result.passed, "violations": len(result.violations),
            "warnings": result.warnings}

async def _verify_safety(code: str, checks: list[str] | None = None) -> dict:
    from kernel.advanced.formal_verify import FormalVerifier
    result = FormalVerifier().verify(code, checks)
    return {"passed": result.passed, "violations": [v for v in result.violations]}

# ── P1: Source Evolution ─────────────────────────────────────────────

async def _evolve_detect(path: str = ".") -> list[dict]:
    from kernel.advanced.source_evolve import SourceEvolutionEngine
    return SourceEvolutionEngine().detect_optimization_targets(path)

async def _evolve_cycle(path: str = ".") -> dict:
    from kernel.advanced.source_evolve import SourceEvolutionEngine
    cycle = SourceEvolutionEngine().run_cycle(path)
    return {"mutations": len(cycle.mutations), "passed_verification": cycle.passed_verification,
            "passed_health_probe": cycle.passed_health_probe}

# ── P1: WASM Sandbox ─────────────────────────────────────────────────

async def _wasm_execute(code: str, timeout: int = 30) -> dict:
    from kernel.advanced.wasm_sandbox import WASMSandbox
    result = await WASMSandbox().execute(code, timeout)
    return {"stdout": result.stdout, "stderr": result.stderr,
            "exit_code": result.exit_code, "duration_ms": result.duration_ms}

# ── P1: Proactive Memory ─────────────────────────────────────────────

# 共享引擎实例: 避免每次调用创建新实例 (新实例无 access_history, dream/predict 永远返回空)
_proactive_engine = None

def _get_proactive_engine():
    global _proactive_engine
    if _proactive_engine is None:
        from kernel.advanced.proactive_memory import ProactiveMemoryEngine
        _proactive_engine = ProactiveMemoryEngine()
    return _proactive_engine


async def _memory_predict(context: str, top_k: int = 5) -> list[dict]:
    engine = _get_proactive_engine()
    preds = engine.predict_next(context, top_k)
    return [{"topic": p.topic, "confidence": p.confidence, "sources": p.sources} for p in preds]


async def _memory_dream() -> dict:
    engine = _get_proactive_engine()
    return await engine.dream()


def record_memory_access(query: str, topics: list[str] | None = None) -> None:
    """供 HexisMemoryStore 调用, 自动记录记忆访问模式 (修复 Bug #2)。"""
    try:
        _get_proactive_engine().record_access(query, topics)
    except Exception:
        pass

# ── P1: Debugger ─────────────────────────────────────────────────────

async def _debug_code(code: str) -> dict:
    from kernel.advanced.debugger import DebuggerAgent
    session = await DebuggerAgent().debug(code)
    return {"error": session.error[:200], "root_cause": session.root_cause,
            "trace_lines": len(session.trace)}

async def _debug_suggest(code: str) -> dict:
    from kernel.advanced.debugger import DebuggerAgent
    agent = DebuggerAgent()
    session = await agent.debug(code)
    return await agent.suggest_fix(session)

# ── P2: Sub-agent Delegation ─────────────────────────────────────────

async def _subagent_dispatch(role: str, prompt: str) -> dict:
    from kernel.advanced.subagent_delegation import SubAgentDelegator, SubAgentTask, AgentRole
    try:
        r = AgentRole(role)
    except ValueError:
        return {"error": f"Invalid role: {role}. Valid: {[r.value for r in AgentRole]}"}
    results = await SubAgentDelegator().fan_out([SubAgentTask(r, prompt)])
    r0 = results[0]
    return {"role": r0.role.value, "output": r0.output[:500], "success": r0.success}

# ── P2: Hooks/Plugins ────────────────────────────────────────────────

async def _hooks_list() -> list[dict]:
    from kernel.advanced.hooks_plugin import HooksPluginSystem
    return HooksPluginSystem().list_hooks()

async def _plugins_list() -> list[dict]:
    from kernel.advanced.hooks_plugin import HooksPluginSystem
    return HooksPluginSystem().list_plugins()

# ── P2: Test Generator ───────────────────────────────────────────────

async def _test_analyze(filepath: str) -> dict:
    from kernel.advanced.test_generator import TestGenerator
    return TestGenerator().analyze_file(filepath)

async def _test_generate(function_name: str, params: list[str] | None = None) -> list[dict]:
    from kernel.advanced.test_generator import TestGenerator
    return TestGenerator().generate_test_cases({"name": function_name, "params": params or []})

# ── P2: Cross-OS Desktop ─────────────────────────────────────────────

async def _cross_os_platform() -> dict:
    from kernel.advanced.cross_os_desktop import CrossOSDesktop
    return CrossOSDesktop().stats()

async def _cross_os_windows() -> list[dict]:
    from kernel.advanced.cross_os_desktop import CrossOSDesktop
    return CrossOSDesktop().get_windows()

# ── P2: Voice/Remote ─────────────────────────────────────────────────

async def _voice_listen(duration: int = 5) -> dict:
    from kernel.advanced.voice_remote import VoiceInput
    return await VoiceInput().listen(duration)

async def _remote_start(port: int = 8765) -> dict:
    from kernel.advanced.voice_remote import RemoteControl
    return await RemoteControl(port=port).start_server()


def _build_param_schema(name: str) -> dict:
    """BUG#3 修复: 为每个 advanced 工具构建精确的参数 Schema。

    不再使用空 {} 伪装 — 每个工具都声明其真实的必需参数,
    这样 LLM 才能正确生成 function calling 参数。
    """
    schemas = {
        # P0: Code Refactoring
        "refactor_analyze": {
            "properties": {"path": {"type": "string", "default": ".", "description": "Path to analyze"}},
            "required": [],
        },
        "refactor_dead_code": {
            "properties": {"path": {"type": "string", "default": ".", "description": "Path to scan for dead code"}},
            "required": [],
        },
        "refactor_duplicates": {
            "properties": {"path": {"type": "string", "default": ".", "description": "Path to scan for duplicates"}},
            "required": [],
        },
        "refactor_impact": {
            "properties": {
                "symbol": {"type": "string", "description": "Symbol name to analyze impact for"},
                "path": {"type": "string", "default": ".", "description": "Path to codebase root"},
            },
            "required": ["symbol"],
        },
        "refactor_callers": {
            "properties": {
                "symbol": {"type": "string", "description": "Function/class name to find callers for"},
                "path": {"type": "string", "default": ".", "description": "Path to codebase root"},
            },
            "required": ["symbol"],
        },
        # P0: Vision Desktop — BUG#3 核心修复: 所有 vision 工具有正确参数
        "vision_click": {
            "properties": {
                "target": {"type": "string", "description": "UI element name/text/description to click"},
                "method": {"type": "string", "default": "auto", "enum": ["auto", "uia", "ocr"],
                          "description": "Click method: auto (UIA then OCR), uia (accessibility tree), ocr (screen text)"},
            },
            "required": ["target"],
        },
        "vision_type": {
            "properties": {
                "text": {"type": "string", "description": "Text to type into the focused element"},
                "target": {"type": "string", "default": "", "description": "Optional: element to click before typing (to focus)"},
            },
            "required": ["text"],
        },
        "vision_screenshot": {
            "properties": {
                "region": {
                    "type": "array", "items": {"type": "integer"},
                    "description": "Optional screenshot region as [left, top, right, bottom]",
                },
            },
            "required": [],
        },
        "vision_open": {
            "properties": {
                "app_name": {"type": "string", "description": "Application name or path to open (e.g. 'notepad', 'chrome')"},
            },
            "required": ["app_name"],
        },
        "vision_chain": {
            "properties": {
                "steps": {
                    "type": "array",
                    "description": "List of action steps. Each step has 'action' + action-specific params.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["click", "type", "open", "screenshot", "wait"]},
                        },
                        "required": ["action"],
                    },
                },
            },
            "required": ["steps"],
        },
        # P0: Formal Verification
        "verify_code": {
            "properties": {"code": {"type": "string", "description": "Source code to formally verify"}},
            "required": ["code"],
        },
        "verify_safety": {
            "properties": {
                "code": {"type": "string", "description": "Source code to check"},
                "checks": {"type": "array", "items": {"type": "string"}, "description": "List of safety checks to run"},
            },
            "required": ["code"],
        },
        # P1: Source Evolution
        "evolve_detect": {
            "properties": {"path": {"type": "string", "default": ".", "description": "Path to analyze for optimization targets"}},
            "required": [],
        },
        "evolve_cycle": {
            "properties": {"path": {"type": "string", "default": ".", "description": "Path to run evolution cycle on"}},
            "required": [],
        },
        # P1: WASM Sandbox
        "wasm_execute": {
            "properties": {
                "code": {"type": "string", "description": "Code to execute in WASM sandbox"},
                "timeout": {"type": "integer", "default": 30, "description": "Execution timeout in seconds"},
            },
            "required": ["code"],
        },
        # P1: Proactive Memory
        "memory_predict": {
            "properties": {
                "context": {"type": "string", "description": "Current context to predict next needed memories from"},
                "top_k": {"type": "integer", "default": 5, "description": "Number of predictions to return"},
            },
            "required": ["context"],
        },
        "memory_dream": {
            "properties": {},  # 无参数: 分析内部 access_history
            "required": [],
        },
        # P1: Debugger
        "debug_code": {
            "properties": {"code": {"type": "string", "description": "Source code to debug"}},
            "required": ["code"],
        },
        "debug_suggest": {
            "properties": {"code": {"type": "string", "description": "Source code to debug and suggest fix for"}},
            "required": ["code"],
        },
        # P2: Sub-agent
        "subagent_dispatch": {
            "properties": {
                "role": {"type": "string", "description": "Agent role: security/performance/review/architect/test/writer"},
                "prompt": {"type": "string", "description": "Task prompt for the sub-agent"},
            },
            "required": ["role", "prompt"],
        },
        # P2: Hooks/Plugins
        "hooks_list": {"properties": {}, "required": []},
        "plugins_list": {"properties": {}, "required": []},
        # P2: Test Generator
        "test_analyze": {
            "properties": {"filepath": {"type": "string", "description": "Path to Python file to analyze for testable units"}},
            "required": ["filepath"],
        },
        "test_generate": {
            "properties": {
                "function_name": {"type": "string", "description": "Name of the function to generate tests for"},
                "params": {"type": "array", "items": {"type": "string"}, "description": "Parameter names for the function"},
            },
            "required": ["function_name"],
        },
        # P2: Cross-OS
        "cross_os_platform": {"properties": {}, "required": []},
        "cross_os_windows": {"properties": {}, "required": []},
        # P2: Voice/Remote
        "voice_listen": {
            "properties": {"duration": {"type": "integer", "default": 5, "description": "Listening duration in seconds"}},
            "required": [],
        },
        "remote_start": {
            "properties": {"port": {"type": "integer", "default": 8765, "description": "TCP port for remote control server"}},
            "required": [],
        },
    }

    schema = schemas.get(name, {"properties": {}, "required": []})
    return {"type": "object", "properties": schema.get("properties", {}), "required": schema.get("required", [])}


def register_advanced_tools(registry: ToolRegistry) -> None:
    tools = [
        # P0: Code Refactoring (5)
        ("refactor_analyze", "Build call graph and analyze entire codebase structure.", _refactor_analyze),
        ("refactor_dead_code", "Find unused functions/classes (no callers).", _refactor_dead_code),
        ("refactor_duplicates", "Find functions with same name in different files.", _refactor_duplicates),
        ("refactor_impact", "Analyze what would break if a symbol changes.", _refactor_impact),
        ("refactor_callers", "Find all callers of a specific symbol.", _refactor_callers),
        # P0: Vision Desktop (5)
        ("vision_click", "Click UI element via computer vision (UIA+OCR).", _vision_click),
        ("vision_type", "Type text via computer vision.", _vision_type),
        ("vision_screenshot", "Screenshot with optional region.", _vision_screenshot),
        ("vision_open", "Open an application.", _vision_open),
        ("vision_chain", "Execute chain of desktop actions.", _vision_chain),
        # P0: Formal Verification (2)
        ("verify_code", "Formally verify code safety (SEVerA-style 6 checks).", _verify_code),
        ("verify_safety", "Run specific safety checks on code.", _verify_safety),
        # P1: Source Evolution (2)
        ("evolve_detect", "Detect optimization targets in codebase (MOSS-style).", _evolve_detect),
        ("evolve_cycle", "Run one source-level evolution cycle.", _evolve_cycle),
        # P1: WASM Sandbox (1)
        ("wasm_execute", "Execute code in WASM zero-trust sandbox.", _wasm_execute),
        # P1: Proactive Memory (2)
        ("memory_predict", "Predict needed memories 3-5 turns ahead.", _memory_predict),
        ("memory_dream", "Run offline memory consolidation (dreaming).", _memory_dream),
        # P1: Debugger (2)
        ("debug_code", "Debug code under actual debugger (Debug2Fix style).", _debug_code),
        ("debug_suggest", "Suggest fix based on debug analysis.", _debug_suggest),
        # P2: Sub-agent (1)
        ("subagent_dispatch", "Dispatch task to specialized sub-agent (6 roles).", _subagent_dispatch),
        # P2: Hooks/Plugins (2)
        ("hooks_list", "List all registered event hooks.", _hooks_list),
        ("plugins_list", "List installed plugins.", _plugins_list),
        # P2: Test Generator (2)
        ("test_analyze", "Analyze file and find testable units.", _test_analyze),
        ("test_generate", "Generate test cases for a function.", _test_generate),
        # P2: Cross-OS (2)
        ("cross_os_platform", "Get cross-OS desktop platform info.", _cross_os_platform),
        ("cross_os_windows", "List open windows.", _cross_os_windows),
        # P2: Voice/Remote (2)
        ("voice_listen", "Listen and transcribe speech.", _voice_listen),
        ("remote_start", "Start remote control server.", _remote_start),
    ]

    for name, desc, handler in tools:
        # BUG#3 修复: 每个工具都有精确的参数 Schema, 不再用空 {} 伪装
        params = _build_param_schema(name)
        registry.register(name=name, description=desc, parameters=params, handler=handler, category="advanced")
