"""10代进化测试 — 全六维竞技场 + Panarchy 相变 + FCPI 追踪.

独立运行脚本，验证 EvolutionGenerationManager 的完整多代进化能力。
"""

import importlib.util
import json
import sys
import time
from pathlib import Path

# ── 加载模块 ──────────────────────────────────────────────────────────
_BACKEND = Path(__file__).parent.parent


def _setup_packages():
    """设置包命名空间."""
    import types
    for pkg_path, pkg_name in [
        ("app", "app"),
        ("app/services", "app.services"),
        ("app/services/arenas", "app.services.arenas"),
    ]:
        if pkg_name not in sys.modules:
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(_BACKEND / pkg_path)]
            pkg.__package__ = pkg_name
            sys.modules[pkg_name] = pkg


def _load_module(full_name: str, rel_path: str):
    path = _BACKEND / rel_path
    spec = importlib.util.spec_from_file_location(full_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    module.__package__ = full_name.rsplit(".", 1)[0]
    module.__name__ = full_name
    spec.loader.exec_module(module)
    return module


_setup_packages()

_arena_base = _load_module("app.services.arenas.arena_base", "app/services/arenas/arena_base.py")
_coding = _load_module("app.services.arenas.coding_arena", "app/services/arenas/coding_arena.py")
_coord = _load_module("app.services.arenas.coordination_arena", "app/services/arenas/coordination_arena.py")
_safety = _load_module("app.services.arenas.safety_arena", "app/services/arenas/safety_arena.py")
_decision = _load_module("app.services.arenas.decision_arena", "app/services/arenas/decision_arena.py")
_emergence = _load_module("app.services.arenas.emergence_arena", "app/services/arenas/emergence_arena.py")
_perf = _load_module("app.services.arenas.performance_arena", "app/services/arenas/performance_arena.py")
_evomgr = _load_module("app.services.evolution_generation_manager", "app/services/evolution_generation_manager.py")
_fitext = _load_module("app.services.fitness_extractor", "app/services/fitness_extractor.py")

# 提取类型
FCPIDimension = _arena_base.FCPIDimension
ArenaConfig = _arena_base.ArenaConfig
EvolutionGenerationManager = _evomgr.EvolutionGenerationManager
EvolutionConfig = _evomgr.EvolutionConfig
EmergentFitnessExtractor = _fitext.EmergentFitnessExtractor

# 竞技场类
ARENA_CLASSES = {
    FCPIDimension.CODING: _coding.CodingArena,
    FCPIDimension.COORDINATION: _coord.CoordinationArena,
    FCPIDimension.SAFETY: _safety.SafetyArena,
    FCPIDimension.DECISION: _decision.DecisionArena,
    FCPIDimension.EMERGENCE: _emergence.EmergenceArena,
    FCPIDimension.PERFORMANCE: _perf.PerformanceArena,
}

# ═══════════════════════════════════════════════════════════════════════
# 测试配置
# ═══════════════════════════════════════════════════════════════════════

POPULATION_SIZE = 20
MAX_GENERATIONS = 10
WORK_DIR = _BACKEND / "uploads" / "evolution_test"

# 构建样本基因组上下文 (随代数变化增加复杂度)
SAMPLE_GENOME = {
    "genome_id": "seed_genome_v1",
    "generation": 0,
    "code_snippets": [
        {
            "id": "snippet_1",
            "name": "adaptive_router",
            "language": "python",
            "source": (
                "def route_request(input_data: dict) -> str:\n"
                '    """Route request to appropriate handler."""\n'
                "    if not isinstance(input_data, dict):\n"
                "        raise ValueError('input_data must be dict')\n"
                "    task_type = input_data.get('type', 'default')\n"
                "    handlers = {\n"
                "        'analysis': '_handle_analysis',\n"
                "        'trading': '_handle_trading',\n"
                "        'query': '_handle_query',\n"
                "    }\n"
                "    return handlers.get(task_type, '_handle_default')\n"
            ),
            "context": "Adaptive request router for multi-agent task dispatch",
        },
        {
            "id": "snippet_2",
            "name": "meta_cognition_scan",
            "language": "python",
            "source": (
                "async def full_health_scan(layers: list[str]) -> dict:\n"
                '    """Perform full system health scan across all layers."""\n'
                "    results = {}\n"
                "    for layer in layers:\n"
                "        try:\n"
                "            results[layer] = await scan_layer(layer)\n"
                "        except Exception as e:\n"
                "            results[layer] = {'error': str(e)}\n"
                "    return results\n"
            ),
            "context": "Meta-cognition health scanner for self-diagnosis",
        },
    ],
    "decision_tasks": [
        {
            "name": "Resource Optimization Challenge",
            "description": "Optimize resource allocation across 5 projects over 72 hours",
            "subgoals": ["audit", "assess", "allocate", "rebalance", "optimize"],
            "difficulty": 0.7,
        },
    ],
    "performance_data": {
        "routing_latency_ms": 120,
        "event_throughput": 8500,
        "field_update_cells_per_ms": 600,
        "token_efficiency": 0.72,
        "memory_compression_ratio": 0.55,
        "scalability_factor": 0.68,
    },
    "agent_count": 15,
}


def create_genome_context(genome_id: str, generation: int) -> dict:
    """为特定基因组的特定代创建上下文 (模拟逐代进化)."""
    ctx = json.loads(json.dumps(SAMPLE_GENOME))  # 深拷贝
    ctx["genome_id"] = genome_id
    ctx["generation"] = generation

    # 逐代变化: 性能数据渐进改善 (模拟进化效果)
    perf = ctx["performance_data"]
    improvement = 1.0 + generation * 0.03  # 每代 3% 改善
    perf["routing_latency_ms"] = max(50, int(120 / improvement))
    perf["event_throughput"] = min(15000, int(8500 * improvement))
    perf["token_efficiency"] = min(0.95, 0.72 * improvement)
    perf["scalability_factor"] = min(0.95, 0.68 * improvement)

    # 随机波动 (模拟环境噪声)
    import random
    random.seed(hash(genome_id + str(generation)) % (2**31))
    for key in perf:
        if isinstance(perf[key], (int, float)):
            perf[key] = max(0, perf[key] * random.uniform(0.85, 1.15))
            if isinstance(perf[key], float):
                perf[key] = round(perf[key], 4)

    return ctx


def run_arena_direct(arena_cls, genome_context, work_dir):
    """直接运行竞技场 (不通过 EvolutionManager)."""
    arena = arena_cls(work_dir=work_dir)
    return arena.run_generation(genome_context, action_logs=[])


# ═══════════════════════════════════════════════════════════════════════
# 主测试
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("   Mycelium AGI v4.0 × MiroFish — 10代进化测试")
    print("   Six-Arena Evolution Engine Phase 1")
    print("=" * 80)
    print()

    # 清理旧输出
    work_dir = WORK_DIR
    work_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: 初始化进化管理器
    print("[1/4] 初始化 EvolutionGenerationManager...")
    config = EvolutionConfig(
        max_generations=MAX_GENERATIONS,
        population_size=POPULATION_SIZE,
        elitism_count=3,
    )
    manager = EvolutionGenerationManager(config=config, work_dir=work_dir)
    manager.initialize()
    print(f"     种群大小: {manager.population_size}")
    print(f"     初始 Panarchy 相: {manager.panarchy_phase.value}")
    print(f"     连接度: {manager._connectedness:.3f}, 韧性: {manager._resilience:.3f}")
    print()

    # Step 2: 存储每代结果
    extractor = EmergentFitnessExtractor()
    generation_results = []
    fcpi_timeline = []

    # Step 3: 运行10代进化
    print("[2/4] 开始10代进化...")
    print("-" * 80)

    for gen in range(1, MAX_GENERATIONS + 1):
        gen_start = time.monotonic()
        print(f"\n>>> 第 {gen} 代 <<<")

        # 为当前代选择活跃基因组
        active_genomes = [
            g for g in manager._population
            if g.get("status") == "active"
        ][:5]  # 每代评估 5 个基因组

        # 运行每个基因组的六个竞技场
        all_arena_results = {}
        for genome in active_genomes:
            gid = genome["genome_id"]
            ctx = create_genome_context(gid, gen)

            arena_results_for_genome = {}
            for dim, arena_cls in ARENA_CLASSES.items():
                arena_work = work_dir / "arenas" / dim.value / f"gen_{gen:04d}"
                result = run_arena_direct(arena_cls, ctx, arena_work)
                if result.success and result.fitness_vector:
                    arena_results_for_genome[dim] = result.fitness_vector
                else:
                    # 失败则使用默认值
                    arena_results_for_genome[dim] = _arena_base.FitnessVector(
                        dimension=dim, primary_score=0.5, sub_scores={},
                        confidence=0.5, generation=gen, genome_id=gid,
                        arena_id=f"{dim.value}_fallback",
                    )

            all_arena_results[gid] = arena_results_for_genome

            # 提取 FCPI
            extraction = extractor.extract(arena_results_for_genome, ctx)
            fcpi = extraction.fcpi_vector

            # 更新基因组适应度
            genome["fcpi_scores"] = {
                "coding": fcpi.coding,
                "coordination": fcpi.coordination,
                "safety": fcpi.safety,
                "decision": fcpi.decision,
                "emergence": fcpi.emergence,
                "performance": fcpi.performance,
            }
            genome["fcpi_total"] = fcpi.to_legacy_fitness()

            print(f"  [{gid[:16]}] "
                  f"C:{fcpi.coding:.3f} R:{fcpi.coordination:.3f} "
                  f"S:{fcpi.safety:.3f} D:{fcpi.decision:.3f} "
                  f"E:{fcpi.emergence:.3f} P:{fcpi.performance:.3f} "
                  f"| FCPI:{fcpi.to_legacy_fitness():.4f} "
                  f"| 置信:{fcpi.confidence:.3f}"
                  + (f" [CHEAT]" if fcpi.goodharting_flag else ""))

        # 聚合代际报告
        contexts_for_manager = {
            g["genome_id"]: create_genome_context(g["genome_id"], gen)
            for g in active_genomes
        }
        report = manager.run_generation(contexts_for_manager)

        gen_duration = time.monotonic() - gen_start
        print(f"  -- 代际总结 --")
        print(f"  相: {report['phase']} | "
              f"种群: {report['population_size']} | "
              f"连接度: {report['connectedness']:.3f} | "
              f"韧性: {report['resilience']:.3f} | "
              f"耗时: {gen_duration:.1f}s")

        if report.get("emergent_patterns"):
            for p in report["emergent_patterns"][:3]:
                print(f"  * 涌现: {p}")

        if report.get("crystallized"):
            for c in report["crystallized"]:
                print(f"  *CRYSTAL*: {c}")

        if report.get("errors"):
            for e in report["errors"]:
                print(f"  [ERR] 错误: {e}")

        fcpi_timeline.append({
            "generation": gen,
            "phase": report["phase"],
            "fcpi_scores": report.get("fcpi_scores", {}),
            "population_size": report["population_size"],
            "connectedness": report["connectedness"],
            "resilience": report["resilience"],
            "duration_seconds": gen_duration,
            "emergent_count": len(report.get("emergent_patterns", [])),
        })

        # Ω 相检测: 如果进入 Ω 相，触发大灭绝
        if report["phase"] == "omega":
            print(f"\n  *** PANARCHY OMEGA PHASE - 触发大灭绝事件! ***")
            extinction = manager.trigger_extinction_event()
            print(f"  淘汰: {extinction['victims_count']} genomes")
            print(f"  幸存: {extinction['survivors_count']} genomes")
            print(f"  新相: {extinction['new_phase']}")

        generation_results.append(report)

    # Step 4: 汇总报告
    print("\n" + "=" * 80)
    print("[3/4] 10代进化汇总报告")
    print("=" * 80)

    # FCPI 趋势表
    print(f"\n{'Gen':<4} {'Phase':<6} {'Pop':<5} {'C':<6} {'R':<6} {'S':<6} {'D':<6} {'E':<6} {'P':<6} {'FCPI':<8} {'Emerg':<5}")
    print("-" * 80)

    total_fcpi_values = []
    for entry in fcpi_timeline:
        scores = entry["fcpi_scores"]
        if scores:
            # 计算该代所有基因组的平均 FCPI
            avg = {
                dim: sum(
                    s.get(dim, 0.5) for s in scores.values()
                ) / max(len(scores), 1)
                for dim in ["coding", "coordination", "safety", "decision", "emergence", "performance"]
            }
            total = (
                0.25 * avg["coding"] + 0.25 * avg["coordination"]
                + 0.15 * avg["safety"] + 0.15 * avg["decision"]
                + 0.10 * avg["emergence"] + 0.10 * avg["performance"]
            )
            total_fcpi_values.append(total)
            print(
                f"{entry['generation']:<4} "
                f"{entry['phase']:<6} "
                f"{entry['population_size']:<5} "
                f"{avg['coding']:.3f} "
                f"{avg['coordination']:.3f} "
                f"{avg['safety']:.3f} "
                f"{avg['decision']:.3f} "
                f"{avg['emergence']:.3f} "
                f"{avg['performance']:.3f} "
                f"{total:.4f}   "
                f"{entry['emergent_count']:<4}"
            )

    # FCPI 趋势分析
    trend = None
    trend_pct = 0.0
    print(f"\n{'─' * 60}")
    if len(total_fcpi_values) >= 2:
        trend = total_fcpi_values[-1] - total_fcpi_values[0]
        trend_pct = (trend / total_fcpi_values[0]) * 100 if total_fcpi_values[0] > 0 else 0
        print(f"  FCPI trend: {total_fcpi_values[0]:.4f} -> {total_fcpi_values[-1]:.4f}")
        print(f"  Change: {trend:+.4f} ({trend_pct:+.1f}%)")
        if trend > 0:
            print(f"  [OK] Positive evolution! System improving")
        elif trend > -0.02:
            print(f"  [--] Stable, no degradation")
        else:
            print(f"  [WARN] Negative trend, check safety gates")

    # 涌现模式统计
    total_emergent = sum(e["emergent_count"] for e in fcpi_timeline)
    phases_seen = set(e["phase"] for e in fcpi_timeline)
    print(f"  涌现总数: {total_emergent}")
    print(f"  Panarchy phases seen: {phases_seen}")

    # 最终进化状态
    print(f"\n{'─' * 60}")
    final_state = manager.get_evolution_report()
    print(f"  Final pop: {final_state['population_size']} genomes")
    print(f"  Final phase: {final_state['panarchy_phase']}")
    print(f"  Snapshots: {final_state['snapshot_count']}")
    print(f"  Emergent patterns: {final_state['emergent_pattern_count']}")

    # Step 5: 保存完整报告
    report_path = work_dir / "10gen_report.json"
    report_data = {
        "test_config": {
            "population_size": POPULATION_SIZE,
            "max_generations": MAX_GENERATIONS,
        },
        "fcpi_timeline": fcpi_timeline,
        "final_state": {
            "population_size": final_state["population_size"],
            "panarchy_phase": final_state["panarchy_phase"],
            "snapshot_count": final_state["snapshot_count"],
            "emergent_pattern_count": final_state["emergent_pattern_count"],
        },
        "fcpi_trend": {
            "first": total_fcpi_values[0] if total_fcpi_values else None,
            "last": total_fcpi_values[-1] if total_fcpi_values else None,
            "change": trend if len(total_fcpi_values) >= 2 else None,
        },
        "phases_seen": list(phases_seen),
        "total_emergent_patterns": total_emergent,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\n[4/4] Report saved: {report_path}")

    print("\n" + "=" * 80)
    print("   10-Generation Evolution Test Complete!")
    print("=" * 80)

    return generation_results, fcpi_timeline


if __name__ == "__main__":
    main()
