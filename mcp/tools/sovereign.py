"""MCP Sovereign Tools — P3 ProgramBench/BeyondSWE/MXC/Quantum grade."""
from __future__ import annotations
from typing import Any
from mcp.server import ToolRegistry

async def _system_build(spec_json: str) -> dict:
    from kernel.sovereign.system_builder import SystemBuilder
    import json, tempfile, os
    spec = json.loads(spec_json) if isinstance(spec_json, str) else spec_json
    builder = SystemBuilder()
    behavior = builder.extract_behavior(spec.get("executable","echo"), spec.get("docs",""))
    modules_plan = builder.design_architecture(behavior)
    modules = {m.name: builder.generate_module(m, behavior) for m in modules_plan}
    out = tempfile.mkdtemp(prefix="sysbuild_")
    result = builder.integrate(modules, out)
    fuzz = builder.fuzz_verify(out, behavior, 10)
    return {"modules": len(modules), "output": out, "fuzz_passed": fuzz["passed"], "fuzz_failed": fuzz["failed"]}

async def _cross_repo_search(issue: str) -> list[dict]:
    from kernel.sovereign.cross_repo import CrossRepoReasoner
    return CrossRepoReasoner().search_upstream(issue, ["."])

async def _domain_knowledge(query: str) -> dict:
    from kernel.sovereign.domain_knowledge import DomainKnowledge
    dk = DomainKnowledge()
    domain = dk.match_domain(query)
    return {"matched_domain": domain, "libraries": dk.suggest_libraries(domain) if domain else []}

async def _dep_migrate_scan(root: str, old_api: str, new_api: str) -> list[dict]:
    """Scan codebase for deprecated API usages. Auto-detects common deprecations when params empty."""
    from kernel.sovereign.dep_migrate import DependencyMigrator
    dm = DependencyMigrator()

    if old_api and new_api:
        dm.add_rule(old_api, new_api)
    else:
        # 自动探测: 常见 Python/JS API 迁移规则 (P0-3 fix)
        AUTO_RULES: dict[str, str] = {
            "datetime.utcnow()": "datetime.now(datetime.UTC)",
            "datetime.utcfromtimestamp": "datetime.fromtimestamp(..., tz=datetime.UTC)",
            "collections.Mapping": "collections.abc.Mapping",
            "collections.Iterable": "collections.abc.Iterable",
            "inspect.getargspec": "inspect.signature",
            "inspect.formatargspec": "inspect.signature",
            "threading.Thread.setDaemon": "threading.Thread.daemon = True",
            "Queue": "queue.Queue",
            "ConfigParser": "configparser.ConfigParser",
            "raw_input": "input",
            "xrange": "range",
            "has_key": "in",
            "os.popen": "subprocess.Popen",
            "commands.getoutput": "subprocess.check_output",
            "$.ajax": "fetch()",
            "componentWillMount": "componentDidMount",
            "componentWillReceiveProps": "getDerivedStateFromProps",
        }
        for old, new in AUTO_RULES.items():
            dm.add_rule(old, new)

    return dm.scan(root)

async def _kernel_capabilities() -> dict:
    from kernel.sovereign.kernel_intel import KernelIntegrator
    ki = KernelIntegrator()
    return {"platform": ki.capabilities.platform, "sandbox": ki.capabilities.sandbox_level,
            "mxc": ki.capabilities.mxc_available, "policy": ki.get_security_policy()}

async def _quantum_verify(code: str, claim: str) -> dict:
    from kernel.sovereign.quantum_hybrid import QuantumHybridVerifier
    qv = QuantumHybridVerifier()
    witness = qv.generate_witness(code, claim)
    # SOV#9修复: 返回详细的验证分解信息
    details = getattr(witness, "breakdown", {}) or {}
    result = {
        "verified": witness.verified,
        "confidence": witness.confidence,
        "code_hash": witness.code_hash,
        "threshold": 0.7,
        "structural_score": details.get("structural", "?"),
        "safety_score": details.get("safety", "?"),
        "relevance_score": details.get("relevance", "?"),
    }
    if not witness.verified:
        result["failure_reason"] = (
            f"Confidence ({witness.confidence:.2f}) below threshold (0.7). "
            "Try a more specific claim that matches the code semantics."
        )
    return result

async def _quantum_gate(original: str, modified: str, claim: str) -> dict:
    from kernel.sovereign.quantum_hybrid import QuantumHybridVerifier
    return QuantumHybridVerifier().verify_self_modification(original, modified, claim)

async def _formal_prove(code: str) -> dict:
    from kernel.sovereign.formal_prover import NeuroSymbolicProver
    return NeuroSymbolicProver().prove_all(code)

def register_sovereign_tools(registry: ToolRegistry) -> None:
    # All tools defined with their individual parameter schemas.
    # Fixes P0-1 (formal_prove), P0-2 (quantum_verify), P0-3 (dep_migrate_scan)
    # which previously used empty {} params causing signature mismatch / missing arg errors.
    tools: list[tuple[str, str, Any, dict]] = [
        ("system_build", "Build complete software system from spec (ProgramBench grade).", _system_build,
         {"type": "object", "properties": {"spec_json": {"type": "string", "description": "JSON specification for the system to build"}}, "required": ["spec_json"]}),

        ("cross_repo_search", "Search external repos for related fixes (BeyondSWE CrossRepo).", _cross_repo_search,
         {"type": "object", "properties": {"issue": {"type": "string", "description": "Issue description to search for across repos"}}, "required": ["issue"]}),

        ("domain_knowledge", "Get domain-specific knowledge and libraries (BeyondSWE DomainFix).", _domain_knowledge,
         {"type": "object", "properties": {"query": {"type": "string", "description": "Query to match domain and suggest libraries for"}}, "required": ["query"]}),

        # P0-3 fix: dep_migrate_scan — was missing all 3 required params, now has defaults
        ("dep_migrate_scan", "Scan codebase for deprecated API usages (BeyondSWE DepMigrate). Auto-detects APIs when old_api/new_api are empty.", _dep_migrate_scan,
         {"type": "object", "properties": {
             "root": {"type": "string", "description": "Root directory to scan", "default": "."},
             "old_api": {"type": "string", "description": "Old/deprecated API to find. If empty, auto-scans for common deprecations.", "default": ""},
             "new_api": {"type": "string", "description": "New replacement API. If empty, auto-detects when possible.", "default": ""},
         }, "required": []}),

        ("kernel_capabilities", "Detect OS kernel-level sandbox capabilities (MXC/Quine/ATLAS).", _kernel_capabilities,
         {"type": "object", "properties": {}, "required": []}),

        # P0-2 fix: quantum_verify — was missing both 'code' and 'claim' required args
        ("quantum_verify", "Quantum-hybrid code verification (Quantum Godel Machine grade). Requires code and claim to verify.", _quantum_verify,
         {"type": "object", "properties": {
             "code": {"type": "string", "description": "Source code to verify"},
             "claim": {"type": "string", "description": "Claim to verify about the code (e.g. 'no memory leaks', 'correct sorting')"},
         }, "required": ["code", "claim"]}),

        ("quantum_gate", "Quantum self-modification gate verification.", _quantum_gate,
         {"type": "object", "properties": {
             "original": {"type": "string", "description": "Original code before modification"},
             "modified": {"type": "string", "description": "Modified code after self-modification"},
             "claim": {"type": "string", "description": "Claim that the modification preserves semantics"},
         }, "required": ["original", "modified", "claim"]}),

        # P0-1 fix: formal_prove — was receiving 'symbol'+'path' but expects 'code'
        ("formal_prove", "Neuro-symbolic theorem proving for code (AlphaProof grade). Pass code to prove properties about.", _formal_prove,
         {"type": "object", "properties": {
             "code": {"type": "string", "description": "Source code to formally prove properties about"},
         }, "required": ["code"]}),
    ]

    # Phase 5 extended tools
    async def _feature_plan(spec_json: str) -> dict:
        import json as _json
        from kernel.sovereign.feature_dev import FeatureDeveloper, FeatureSpec
        spec = FeatureSpec(**_json.loads(spec_json) if isinstance(spec_json, str) else spec_json)
        dev = FeatureDeveloper()
        impact = dev.analyze_impact(spec)
        plan = dev.generate_implementation_plan(spec)
        scaffold = dev.scaffold_feature(plan, f"./data/features/{spec.name}")
        return {"impact": impact, "plan_risk": plan.risk_level, "estimated_lines": plan.estimated_lines, "scaffold": scaffold}

    async def _agent_spawn(code: str, role: str = "worker") -> dict:
        from kernel.sovereign.agent_process import AgentProcessManager
        mgr = AgentProcessManager()
        agent = mgr.spawn(code, role=role)
        return {"agent_id": agent.agent_id, "pid": agent.pid, "status": agent.status}

    async def _agent_tree() -> dict:
        from kernel.sovereign.agent_process import AgentProcessManager
        return AgentProcessManager().get_tree()

    async def _ring0_review(operation: str, params_json: str = "{}") -> dict:
        import json as _json
        from kernel.sovereign.ring0_gov import Ring0Governor
        gov = Ring0Governor()
        params = _json.loads(params_json) if isinstance(params_json, str) else params_json
        verdict = gov.review(operation, params)
        return {"allowed": verdict.allowed, "reason": verdict.reason, "require_human": verdict.require_human}

    async def _ring0_constitution() -> list[str]:
        from kernel.sovereign.ring0_gov import Ring0Governor
        return Ring0Governor().get_constitution()

    async def _goal_create(description: str, sub_goals_json: str = "[]") -> dict:
        import json as _json
        from kernel.sovereign.long_horizon import LongHorizonExecutor
        sub_goals = _json.loads(sub_goals_json) if isinstance(sub_goals_json, str) else []
        goal = LongHorizonExecutor().create_goal(description, sub_goals or None)
        return {"goal_id": goal.id, "sub_goals": len(goal.sub_goals), "status": goal.status.value}

    async def _goal_execute(goal_id: str) -> dict:
        from kernel.sovereign.long_horizon import LongHorizonExecutor
        return LongHorizonExecutor().execute_all(goal_id)

    async def _goal_list() -> list[dict]:
        from kernel.sovereign.long_horizon import LongHorizonExecutor
        return LongHorizonExecutor().list_goals()

    async def _neuro_symbolic_verify(code: str) -> dict:
        from kernel.sovereign.neuro_symbolic import NeuroSymbolicReasoner
        return NeuroSymbolicReasoner().verify_all(code)

    async def _sdia_search(problem: str, solutions_json: str = "[]") -> dict:
        import json as _json
        from kernel.sovereign.neuro_symbolic import NeuroSymbolicReasoner
        solutions = _json.loads(solutions_json) if isinstance(solutions_json, str) else []
        # 主权#2修复: 如果未提供方案空间, 自动从 sys.modules 构建
        if not solutions:
            import sys
            solutions = [f"{name}: {getattr(mod, '__doc__', '')[:80] or 'system module'}"
                        for name, mod in list(sys.modules.items())[:30]
                        if name and mod and not name.startswith('_')][:20]
        result = NeuroSymbolicReasoner().sdia_search(problem, solutions)
        # BUG-003修复: 防止 None 结果导致下标错误
        if result is None:
            result = {"candidates_explored": len(solutions), "candidates_relevant": 0,
                     "solutions_verified": 0, "best_solution": None,
                     "note": "No matching solutions found in search space"}
        return result

    extended_tools: list[tuple[str, str, Any, dict]] = [
        ("feature_plan", "Generate large-scale feature implementation plan (FeatureBench grade).", _feature_plan,
         {"type": "object", "properties": {"spec_json": {"type": "string", "description": "JSON feature specification"}}, "required": ["spec_json"]}),

        ("agent_spawn", "Spawn agent as native OS process (Quine fork/exec model).", _agent_spawn,
         {"type": "object", "properties": {"code": {"type": "string", "description": "Code for the agent to execute"}, "role": {"type": "string", "default": "worker"}}, "required": ["code"]}),

        ("agent_tree", "Get agent process tree visualization.", _agent_tree,
         {"type": "object", "properties": {}, "required": []}),

        ("ring0_review", "Ring-0 deny-by-default security review (ATLAS grade).", _ring0_review,
         {"type": "object", "properties": {"operation": {"type": "string", "description": "Operation to review"}, "params_json": {"type": "string", "default": "{}"}}, "required": ["operation"]}),

        ("ring0_constitution", "Get immutable Ring-0 security constitution.", _ring0_constitution,
         {"type": "object", "properties": {}, "required": []}),

        ("goal_create", "Create ultra-long-horizon autonomous goal with sub-goals (DeepSWE grade).", _goal_create,
         {"type": "object", "properties": {"description": {"type": "string", "description": "Goal description"}, "sub_goals_json": {"type": "string", "default": "[]"}}, "required": ["description"]}),

        ("goal_execute", "Execute all steps of a long-horizon goal.", _goal_execute,
         {"type": "object", "properties": {"goal_id": {"type": "string", "description": "Goal ID to execute"}}, "required": ["goal_id"]}),

        ("goal_list", "List all active long-horizon goals.", _goal_list,
         {"type": "object", "properties": {}, "required": []}),

        ("neuro_symbolic_verify", "Neuro-symbolic hybrid code verification (SWUT/SDIA grade).", _neuro_symbolic_verify,
         {"type": "object", "properties": {"code": {"type": "string", "description": "Source code to verify"}}, "required": ["code"]}),

        ("sdia_search", "Super Dynamic Inspiration Algorithm search.", _sdia_search,
         {"type": "object", "properties": {"problem": {"type": "string", "description": "Problem to solve"}, "solutions_json": {"type": "string", "default": "[]"}}, "required": ["problem"]}),
    ]
    tools.extend(extended_tools)

    for name, desc, handler, params in tools:
        registry.register(name=name, description=desc, parameters=params, handler=handler, category="sovereign")
