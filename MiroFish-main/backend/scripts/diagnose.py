"""诊断脚本 — 追踪 Arena → Simulation → Extract 完整执行路径.

逐层检查每个环节是否正常工作。
"""

import importlib.util
import json
import os
import sys
import types
from pathlib import Path

BACKEND = Path(__file__).parent.parent

# 加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND / ".env")
    print(f"[ENV] LLM_API_KEY={'***' if os.environ.get('LLM_API_KEY') else 'MISSING'}")
    print(f"[ENV] LLM_MODEL_NAME={os.environ.get('LLM_MODEL_NAME', 'NOT SET')}")
except Exception as e:
    print(f"[ENV] Failed: {e}")

# 加载模块
def setup():
    for pkg_path, pkg_name in [
        ("app", "app"), ("app/services", "app.services"),
        ("app/services/arenas", "app.services.arenas"),
    ]:
        if pkg_name not in sys.modules:
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(BACKEND / pkg_path)]
            pkg.__package__ = pkg_name
            sys.modules[pkg_name] = pkg

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(BACKEND / path))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    m.__package__ = name.rsplit(".", 1)[0]
    m.__name__ = name
    spec.loader.exec_module(m)
    return m

setup()

arena_base = load("app.services.arenas.arena_base", "app/services/arenas/arena_base.py")
coding = load("app.services.arenas.coding_arena", "app/services/arenas/coding_arena.py")
coord = load("app.services.arenas.coordination_arena", "app/services/arenas/coordination_arena.py")
safety = load("app.services.arenas.safety_arena", "app/services/arenas/safety_arena.py")
decision = load("app.services.arenas.decision_arena", "app/services/arenas/decision_arena.py")
emergence = load("app.services.arenas.emergence_arena", "app/services/arenas/emergence_arena.py")
perf = load("app.services.arenas.performance_arena", "app/services/arenas/performance_arena.py")
livesim = load("app.services.live_simulation_engine", "app/services/live_simulation_engine.py")

FCPIDimension = arena_base.FCPIDimension

ARENAS = {
    "coding": coding.CodingArena,
    "coordination": coord.CoordinationArena,
    "safety": safety.SafetyArena,
    "decision": decision.DecisionArena,
    "emergence": emergence.EmergenceArena,
    "performance": perf.PerformanceArena,
}

print("=" * 60)
print("DIAGNOSIS: Tracing Arena -> Simulation -> Extract")
print("=" * 60)

# ── Step 1: 检查 LiveAgentSimulator ──
print("\n[1] LiveAgentSimulator:")
sim = livesim.LiveAgentSimulator()
print(f"    api_key set: {bool(sim.api_key)}")
print(f"    model: {sim.model}")
print(f"    base_url: {sim.base_url}")

# Test lightweight path (force no API)
sim_no_api = livesim.LiveAgentSimulator(api_key="")
ctx = {
    "genome_id": "diagnose_test_001",
    "generation": 1,
    "code_snippets": [{"id": "1", "name": "test", "source": "def test(): pass", "context": "test"}],
    "decision_tasks": [{"name": "Test", "description": "Test task", "subgoals": ["do"], "difficulty": 0.5}],
    "performance_data": {"routing_latency_ms": 150, "event_throughput": 8000,
        "field_update_cells_per_ms": 500, "token_efficiency": 0.65,
        "memory_compression_ratio": 0.5, "scalability_factor": 0.6},
    "agent_count": 8,
}

print(f"\n[2] Testing lightweight path for each arena:")
for arena_name, arena_cls in ARENAS.items():
    arena = arena_cls(work_dir=Path(f"/tmp/diag_{arena_name}"))
    profiles = arena.build_agent_profiles(ctx)

    # Test with lightweight sim (no API key)
    arena.set_simulation_engine(sim_no_api)
    session = sim_no_api.run_arena_session(arena_name, profiles, ctx, rounds=2)

    print(f"\n  --- {arena_name} ---")
    print(f"  Messages: {len(session.messages)}")
    print(f"  Eval scores: {session.eval_scores}")
    print(f"  Eval scores populated: {bool(session.eval_scores)}")

    # If eval_scores exist, test extract_fitness
    if session.eval_scores:
        # Convert session to action_logs format
        logs = []
        for msg in session.messages:
            logs.append({
                "round_num": msg.round_num, "agent_id": msg.agent_id,
                "agent_name": msg.agent_name, "role_type": msg.role_type,
                "action_type": msg.action_type, "content": msg.content,
                "score": msg.score, "metadata": msg.metadata,
            })
        if session.eval_scores:
            logs.append({
                "round_num": 99, "agent_id": -1, "agent_name": "EVAL",
                "role_type": "evaluator", "action_type": "EVALUATE",
                "content": json.dumps(session.eval_scores),
                "eval_scores": session.eval_scores,
            })

        # Check if _extract_eval_scores finds them
        found = arena._extract_eval_scores(logs)
        print(f"  _extract_eval_scores found: {found is not None}")
        if found:
            print(f"  Extracted scores: {found}")

        # Now test actual extract_fitness
        fitness = arena.extract_fitness(logs, profiles, ctx)
        print(f"  Fitness primary: {fitness.primary_score:.4f}")
        print(f"  Fitness subs: {fitness.sub_scores}")
    else:
        print(f"  *** eval_scores EMPTY — this is the bug! ***")

# ── Step 3: 测试完整 run_generation 流程 ──
print(f"\n\n[3] Full run_generation test (coding arena, lightweight sim):")
arena = coding.CodingArena(work_dir=Path("/tmp/diag_full"))
arena.set_simulation_engine(sim_no_api)
result = arena.run_generation(ctx, action_logs=None)
print(f"  Success: {result.success}")
if result.fitness_vector:
    print(f"  Primary: {result.fitness_vector.primary_score:.4f}")
    print(f"  Subs: {result.fitness_vector.sub_scores}")
    print(f"  Confidence: {result.fitness_vector.confidence:.4f}")
else:
    print(f"  No fitness vector! Errors: {result.errors}")

# ── Step 4: 检查 extract_fitness 是否真的进入了 eval_scores 分支 ──
print(f"\n[4] Direct extract_fitness test with eval score injection:")
logs_with_eval = [
    {"round_num": 1, "agent_id": 1001, "role_type": "senior_engineer",
     "action_type": "REVIEW", "content": "Looks good"},
    {"round_num": 99, "agent_id": -1, "role_type": "evaluator",
     "action_type": "EVALUATE", "content": "{}",
     "eval_scores": {"code_correctness": 8.5, "security_awareness": 7.2,
                     "review_thoroughness": 6.8, "collaboration_quality": 7.5,
                     "innovation_in_fixes": 5.5}},
]
fitness = arena.extract_fitness(logs_with_eval, [], ctx)
print(f"  Primary: {fitness.primary_score:.4f}")
print(f"  Subs: {fitness.sub_scores}")
expected = round((0.85 + 0.72 + 0.68 + 0.75 + 0.55 + 0.3) / 6, 4)
print(f"  Expected: ~{expected}")
print(f"  Match: {abs(fitness.primary_score - expected) < 0.05}")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
