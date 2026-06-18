"""Sclerotium OS — Bridge to fungal-cortex. Loads ALL ~45 organs.

Fully expanded to touch every layer of fungal-cortex:
  core (9) + l6 (15) + adaptive (19) + autonomous (15) + immune (3)
  + field (1) + evolution (3) + cluster (8) + dendrite + morphogen + panarchy
  + holograph + autocatalytic + quantum + orchestration + agent + security
  + monitoring + trading + bridge

原则: import, 不 copy — 零代码重复。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from kernel.project_paths import add_subsystem_paths

add_subsystem_paths()


class OrganStatus:
    """Tracks an organ's loading state."""
    def __init__(self, name: str, layer: str):
        self.name = name
        self.layer = layer
        self.loaded = False
        self.error: str | None = None
        self.instance: Any = None


class FungalBridge:
    """Unified adapter for ALL fungal-cortex services (~45 organs)."""

    def __init__(self) -> None:
        self._initialized = False
        self._organs: dict[str, OrganStatus] = {}
        self._total = 0
        self._loaded = 0

    @property
    def initialized(self) -> bool:
        return self._initialized

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def initialize(self) -> bool:
        """Lazy-load ALL fungal-cortex services. Returns True if any succeeded."""
        if self._initialized:
            return True

        # ── core/ (9 organs) ──
        await self._try_async("event_bus", "core", "src.core.event_bus", "EventBus")
        await self._try_async("unified_event_bus", "core", "src.core.unified_event_bus", "UnifiedEventBus")
        self._try_load("skill_registry", "core", "src.core.skill_registry", "SkillRegistry")
        self._try_load("cognitive_scheduler", "core", "src.core.cognitive_scheduler", "CognitiveScheduler")
        self._try_load("self_healing", "core", "src.core.self_healing", "HealthReport")
        self._try_load("autonomous_governance", "core", "src.core.autonomous_governance", "AutonomousGovernance")
        self._try_load("cross_layer_emergence", "core", "src.core.cross_layer_emergence", "CrossLayerEmergence")
        self._try_load("context_compressor", "core", "src.core.context_compressor", "ContextCompressor")
        self._try_load("model_router", "core", "src.core.model_router", "HttpModelRouter")

        # ── l6/ meta-cognition (15 organs) ──
        self._try_load("meta_cognition", "l6", "src.l6.meta_cognition", "MetaCognitionEngine")
        self._try_load("dgm", "l6", "src.l6.darwinian_godel_machine", "DarwinianGodelMachine")
        self._try_load("architecture_scanner", "l6", "src.l6.architecture_scanner", "ArchitectureScanner")
        self._try_load("auto_refactor", "l6", "src.l6.auto_refactor", "AutoRefactorEngine")
        self._try_load("ability_factory", "l6", "src.l6.ability_factory", "AbilityCreationFactory",
                       skill_registry=self._get("skill_registry"),
                       sandbox=self._get("sandbox_pipeline"),
                       event_bus=self._get("event_bus"))
        self._try_load("emergence_capture", "l6", "src.l6.emergence_capture", "EmergenceCapture")
        self._try_load("crystallizer", "l6", "src.l6.crystallizer", "EmergenceCrystallizer",
                       emergence_capture=self._get("emergence_capture"),
                       ability_factory=self._get("ability_factory"),
                       event_bus=self._get("event_bus"))
        self._try_load("sandbox_pipeline", "l6", "src.l6.sandbox_pipeline", "SandboxVerificationPipeline")
        self._try_load("security_gateway", "l6", "src.l6.security_gateway", "CrossEcoSecurityGateway")
        self._try_load("rule_evolution", "l6", "src.l6.rule_evolution", "DynamicRuleEvolutionEngine")
        self._try_load("goal_expander", "l6", "src.l6.goal_expander", "GlobalGoalExpander")
        self._try_load("cluster_organizer", "l6", "src.l6.cluster_organizer", "ClusterSelfOrganizer")
        self._try_load("code_self_repair", "l6", "src.l6.code_self_repair", "CodeSelfRepair")
        self._try_load("arbiter_monitor", "l6", "src.l6.arbiter_monitor", "ArbiterMonitor")
        self._try_load("mas2_arch_customizer", "l6", "src.l6.mas2_architecture_customizer", "MAS2ArchitectureCustomizer")

        # ── adaptive/ (L0 peripheral nerves, 18 modules) ──
        self._try_load("circuit_breaker", "adaptive", "src.adaptive.circuit_breaker", "CircuitBreaker")
        self._try_load("cusum_detector", "adaptive", "src.adaptive.cusum_detector", "CUSUMRegimeDetector")
        self._try_load("debate_adaptive_bridge", "adaptive", "src.adaptive.debate_adaptive_bridge", "AdaptiveDebateBridge")
        self._try_load("debate_consensus", "adaptive", "src.adaptive.debate_consensus", "DebateConsensusEngine")
        self._try_load("drift_detector", "adaptive", "src.adaptive.drift_detector", "AdaptiveDriftDetector")
        self._try_load("hypernetwork", "adaptive", "src.adaptive.hypernetwork", "AdaptiveHyperNetwork")
        self._try_load("immune_validator", "adaptive", "src.adaptive.immune_validator", "ImmuneValidationReport")
        self._try_load("indicator_adapter", "adaptive", "src.adaptive.indicator_adapter", "IndicatorAdapter")
        self._try_load("market_of_claims", "adaptive", "src.adaptive.market_of_claims", "MarketOfClaims")
        self._try_load("memory_bridge", "adaptive", "src.adaptive.memory_bridge", "MemoryFeedbackReport")
        self._try_load("meta_learner", "adaptive", "src.adaptive.meta_learner", "AdaptiveMetaLearner")
        self._try_load("regime_orchestrator", "adaptive", "src.adaptive.regime_orchestrator", "BayesianRegimeOrchestrator")
        self._try_load("safety_gate", "adaptive", "src.adaptive.safety_gate", "SafetyGateAdapter")
        self._try_load("self_evolution", "adaptive", "src.adaptive.self_evolution", "EvolutionReport")
        self._try_load("strategy_adapter", "adaptive", "src.adaptive.strategy_adapter", "StrategyAdapter")
        self._try_load("temporal_sampler", "adaptive", "src.adaptive.temporal_sampler", "MultiDistributionTemporalSampler")

        # ── autonomous/ (L4 spinal midbrain, 16 modules) ──
        self._try_load("audit_trail", "autonomous", "src.autonomous.audit_trail", "AuditTrail")
        self._try_load("behavior_monitor", "autonomous", "src.autonomous.behavior_monitor", "BehaviorMonitor")
        self._try_load("causal_tracer", "autonomous", "src.autonomous.causal_tracer", "CausalTracer")
        self._try_load("circuit_breaker_bridge", "autonomous", "src.autonomous.circuit_breaker_bridge", "CircuitBreakerBridge")
        self._try_load("conflict_detector", "autonomous", "src.autonomous.conflict_detector", "ConflictDetector")
        self._try_load("counterfactual", "autonomous", "src.autonomous.counterfactual", "CounterfactualEngine")
        self._try_load("dag_cluster_bridge", "autonomous", "src.autonomous.dag_cluster_bridge", "DAGDecomposition")
        self._try_load("intent_parser", "autonomous", "src.autonomous.intent_parser", "IntentParser")
        self._try_load("memory_weaving", "autonomous", "src.autonomous.memory_weaving", "MemoryConsolidation")
        self._try_load("online_evolution", "autonomous", "src.autonomous.online_evolution", "OnlineEvolutionEngine")
        self._try_load("policy_engine", "autonomous", "src.autonomous.policy_engine", "PolicyEngine")
        self._try_load("strategy_validator", "autonomous", "src.autonomous.strategy_validator", "StrategyAutoValidator")
        self._try_load("task_dag", "autonomous", "src.autonomous.task_dag", "TaskDAG")
        self._try_load("transaction_manager", "autonomous", "src.autonomous.transaction_manager", "TransactionManager")
        self._try_load("vector_retrieval", "autonomous", "src.autonomous.vector_retrieval", "VectorRetrievalEngine")

        # ── immune/ (5 modules) ──
        self._try_load("clonal_selector", "immune", "src.immune.clonal_selector", "ClonalSelector")
        self._try_load("dendritic_cell", "immune", "src.immune.dendritic_cell", "DendriticCell")
        self._try_load("immune_memory", "immune", "src.immune.immune_memory", "ImmuneMemory")
        self._try_load("negative_selector", "immune", "src.immune.negative_selector", "NegativeSelector")
        self._try_load("self_set", "immune", "src.immune.self_set", "SelfSet")

        # ── field/ (3 modules) ──
        self._try_load("field_geometry", "field", "src.field.field_geometry", "FieldGeometry")
        self._try_load("stigmergy_field", "field", "src.field.stigmergy_field", "StigmergyField")

        # ── evolution/ (4 modules) ──
        self._try_load("agent_evolver", "evolution", "src.evolution.agent_evolver", "AgentEvolver")
        self._try_load("architecture_evolver", "evolution", "src.evolution.architecture_evolver", "ArchitectureEvolver")
        self._try_load("enforcement_agent", "evolution", "src.evolution.enforcement_agent", "EnforcementAgent")
        self._try_load("parameter_evolver", "evolution", "src.evolution.parameter_evolver", "ParameterEvolver")

        # ── cluster/ (8 modules) ──
        self._try_load("agent_factory", "cluster", "src.cluster.agent_factory", "AgentFactory")
        self._try_load("communicator", "cluster", "src.cluster.communicator", "ClusterCommunicator")
        self._try_load("consensus", "cluster", "src.cluster.consensus", "DistributedConsensus")
        self._try_load("distributed_evolution", "cluster", "src.cluster.distributed_evolution", "DistributedEvolutionEngine")
        self._try_load("endogenous_engine", "cluster", "src.cluster.endogenous_engine", "EndogenousTargetEngine")
        self._try_load("global_audit", "cluster", "src.cluster.global_audit", "GlobalAuditTrail")
        self._try_load("knowledge_network", "cluster", "src.cluster.knowledge_network", "GlobalKnowledgeNetwork")
        self._try_load("pool_manager", "cluster", "src.cluster.pool_manager", "AgentPoolManager")

        # ── dendrite/ (3 modules) ──
        self._try_load("coincidence_detector", "dendrite", "src.dendrite.coincidence_detector", "CoincidenceDetector")
        self._try_load("dendritic_tree", "dendrite", "src.dendrite.dendritic_tree", "DendriticTree")
        self._try_load("temporal_integrator", "dendrite", "src.dendrite.temporal_integrator", "TemporalIntegrator")

        # ── morphogen/ (3 modules) ──
        self._try_load("guided_selforg", "morphogen", "src.morphogen.guided_selforg", "GuidedSelfOrganization")
        self._try_load("morphogen_gradient", "morphogen", "src.morphogen.morphogen_gradient", "MorphogenGradient")
        self._try_load("turing_patterning", "morphogen", "src.morphogen.turing_patterning", "TuringPatterning")

        # ── panarchy/ (3 modules) ──
        self._try_load("adaptive_cycle", "panarchy", "src.panarchy.adaptive_cycle", "AdaptiveCycle")
        self._try_load("panarchy_controller", "panarchy", "src.panarchy.panarchy_controller", "PanarchyController")
        self._try_load("resilience_metrics", "panarchy", "src.panarchy.resilience_metrics", "ResilienceMetrics")

        # ── holograph/ (3 modules) ──
        self._try_load("anomaly_projector", "holograph", "src.holograph.anomaly_projector", "AnomalyProjector")
        self._try_load("fractal_encoder", "holograph", "src.holograph.fractal_encoder", "FractalEncoder")
        self._try_load("holographic_query", "holograph", "src.holograph.holographic_query", "HolographicQuery")

        # ── autocatalytic/ (3 modules) ──
        self._try_load("constraint_closure", "autocatalytic", "src.autocatalytic.constraint_closure", "ConstraintClosure")
        self._try_load("phase_transition", "autocatalytic", "src.autocatalytic.phase_transition", "PhaseTransition")
        self._try_load("skill_catalysis", "autocatalytic", "src.autocatalytic.skill_catalysis_graph", "SkillCatalysisGraph")

        # ── quantum/ (2 modules) ──
        self._try_load("dual_mode_engine", "quantum", "src.quantum.dual_mode_engine", "DualModeEngine")
        self._try_load("self_referential_switch", "quantum", "src.quantum.self_referential_switch", "SelfReferentialSwitch")

        # ── security/ (2 modules) ──
        self._try_load("jwt_auth", "security", "src.security.jwt_auth", "JWTAuthManager")
        self._try_load("rate_limiter", "security", "src.security.rate_limiter", "RateLimiter")

        # ── monitoring/ (2 modules) ──
        self._try_load("alerts", "monitoring", "src.monitoring.alerts", "Alert")
        self._try_load("prometheus_exporter", "monitoring", "src.monitoring.prometheus_exporter", "PrometheusExporter")

        # ── engine/ (3 modules) ──
        self._try_load("thermodynamic", "engine", "src.engine.thermodynamic", "ThermodynamicEngine")
        self._try_load("hamiltonian", "engine", "src.engine.hamiltonian", "HamiltonianFlow")
        self._try_load("dissipative", "engine", "src.engine.dissipative", "DissipativeFlow")

        # ── orchestration/ (3 modules) ──
        self._try_load("root_agent", "orchestration", "src.orchestration.root_agent", "RootAgent")
        self._try_load("cluster_manager", "orchestration", "src.orchestration.cluster_manager", "SpecialtyCluster")
        self._try_load("orch_cognitive_scheduler", "orchestration", "src.orchestration.cognitive_scheduler", "CognitiveScheduler")

        # ── agent/ (3 modules) ──
        self._try_load("hyphal_agent", "agent", "src.agent.hyphal_agent", "HyphalAgent")
        self._try_load("agent_state", "agent", "src.agent.agent_state", "AgentStateTracker")
        self._try_load("enactive_loop", "agent", "src.agent.enactive_loop", "EnactiveLoop")

        # ── bridge/ (sample 4 key bridges) ──
        self._try_load("l0_l7_pipeline", "bridge", "src.bridge.l0_l7_pipeline", "L0L7Pipeline")
        self._try_load("conscious_bridge", "bridge", "src.bridge.conscious_bridge", "ConsciousBridge")
        self._try_load("skill_adapter", "bridge", "src.bridge.skill_adapter", "SkillAdapter")
        self._try_load("final_bench_bridge", "bridge", "src.bridge.final_bench_bridge", "MAERScore")

        # ── L1-L10 layers (sample key modules) ──
        self._try_load("l1_liquid_perceptor", "l1", "src.l1.liquid_perceptor", "LiquidState")
        self._try_load("l2_multi_model_router", "l2", "src.l2.multi_model_router", "RoutingDecision")
        self._try_load("l3_debate_network", "l3", "src.l3.mycorrhizal_debate_network", "DebateNode")
        self._try_load("l4_rl_conductor", "l4", "src.l4.rl_conductor_orchestrator", "ExecutionPlan")
        self._try_load("l5_swarm_self_organizer", "l5", "src.l5.swarm_self_organizer", "PhotormoneField")
        self._try_load("l7_active_inference", "l7", "src.l7.active_inference_agent", "Policy")
        self._try_load("l8_self_referential", "l8", "src.l8.self_referential_compiler", "SystemGenome")
        self._try_load("l9_hybrid_quantum", "l9", "src.l9.hybrid_quantum_agent", "QuantumCircuit")
        self._try_load("l10_conscious_kernel", "l10", "src.l10.conscious_kernel", "ConsciousnessLevel")

        # ── trading/ (3 modules) ──
        self._try_load("data_pipeline", "trading", "src.trading.data_pipeline", "TickData")
        self._try_load("risk_gate", "trading", "src.trading.risk_gate", "RiskGate")
        self._try_load("portfolio_manager", "trading", "src.trading.portfolio_manager", "PortfolioManager")

        # ── Start EventBus ──
        eb = self._get("event_bus")
        if eb and hasattr(eb, "start"):
            try:
                await eb.start()
            except Exception:
                pass

        self._initialized = True
        return self._loaded > 0

    async def shutdown(self) -> None:
        eb = self._get("event_bus")
        if eb and hasattr(eb, "stop"):
            try:
                await eb.stop()
            except Exception:
                pass
        self._initialized = False

    # ── Internal loaders ───────────────────────────────────────────────

    def _get_config(self):
        """Lazy-load fungal-cortex config singleton."""
        if not hasattr(self, '_cached_config'):
            try:
                from src.config import get_config
                self._cached_config = get_config()
            except Exception:
                self._cached_config = None
        return self._cached_config

    def _try_load(self, name: str, layer: str, module_path: str,
                  class_name: str | None = None, **kwargs) -> Any:
        """Try to import and instantiate an organ. Tries: kwargs > no-arg > config > store class."""
        self._total += 1
        status = OrganStatus(name, layer)
        self._organs[name] = status
        try:
            mod = __import__(module_path, fromlist=[class_name] if class_name else [])
            if class_name:
                cls = getattr(mod, class_name)
                instance = None
                # 1) Try with explicit kwargs
                if kwargs:
                    try:
                        instance = cls(**kwargs)
                    except Exception:
                        pass
                # 2) Try no-arg
                if instance is None:
                    try:
                        instance = cls()
                    except TypeError:
                        pass
                # 3) Try with fungal-cortex config
                if instance is None:
                    cfg = self._get_config()
                    if cfg is not None:
                        try:
                            instance = cls(config=cfg)
                        except Exception:
                            pass
                # 4) Store class itself as loaded organ
                if instance is None:
                    instance = cls
                status.instance = instance
            else:
                status.instance = mod
            status.loaded = True
            self._loaded += 1
            return status.instance
        except Exception as e:
            status.error = str(e)[:120]
            status.instance = None
            return None

    async def _try_async(self, name: str, layer: str, module_path: str,
                         class_name: str) -> Any:
        """Async loader for organs that need await on construction."""
        return self._try_load(name, layer, module_path, class_name)

    def _get(self, name: str) -> Any:
        """Get an organ instance by name."""
        s = self._organs.get(name)
        return s.instance if s and s.loaded else None

    # ── Public API ─────────────────────────────────────────────────────

    def status_report(self) -> dict:
        """Return full organ status for all layers."""
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
            "system": "fungal-cortex",
            "total_organs": self._total,
            "loaded": self._loaded,
            "percent": round(self._loaded / max(self._total, 1) * 100, 1),
            "layers": layers,
        }

    def print_status(self) -> None:
        """Pretty-print organ status to console."""
        report = self.status_report()
        bar = "█" * int(report["percent"] / 5) + "░" * (20 - int(report["percent"] / 5))
        print(f"  🍄 fungal-cortex [{bar}] {report['loaded']}/{report['total_organs']} ({report['percent']}%)")
        for layer, info in sorted(report["layers"].items()):
            l_loaded = info.get("loaded", 0)
            l_total = info.get("total", 0)
            layer_bar = "▓" * l_loaded + "·" * (l_total - l_loaded)
            print(f"    {layer:<20} [{layer_bar}] {l_loaded}/{l_total}")

    # ── Property accessors ─────────────────────────────────────────────

    @property
    def event_bus(self) -> Any: return self._get("event_bus")
    @property
    def unified_event_bus(self) -> Any: return self._get("unified_event_bus")
    @property
    def skill_registry(self) -> Any: return self._get("skill_registry")
    @property
    def cognitive_scheduler(self) -> Any: return self._get("cognitive_scheduler")
    @property
    def self_healing(self) -> Any: return self._get("self_healing")
    @property
    def autonomous_governance(self) -> Any: return self._get("autonomous_governance")
    @property
    def cross_layer_emergence(self) -> Any: return self._get("cross_layer_emergence")
    @property
    def context_compressor(self) -> Any: return self._get("context_compressor")
    @property
    def model_router(self) -> Any: return self._get("model_router")
    @property
    def meta_cognition(self) -> Any: return self._get("meta_cognition")
    @property
    def dgm(self) -> Any: return self._get("dgm")
    @property
    def scanner(self) -> Any: return self._get("architecture_scanner")
    @property
    def auto_refactor(self) -> Any: return self._get("auto_refactor")
    @property
    def ability_factory(self) -> Any: return self._get("ability_factory")
    @property
    def emergence_capture(self) -> Any: return self._get("emergence_capture")
    @property
    def crystallizer(self) -> Any: return self._get("crystallizer")
    @property
    def sandbox_pipeline(self) -> Any: return self._get("sandbox_pipeline")
    @property
    def security_gateway(self) -> Any: return self._get("security_gateway")
    @property
    def rule_evolution(self) -> Any: return self._get("rule_evolution")
    @property
    def goal_expander(self) -> Any: return self._get("goal_expander")
    @property
    def cluster_organizer(self) -> Any: return self._get("cluster_organizer")
    @property
    def code_self_repair(self) -> Any: return self._get("code_self_repair")
    @property
    def arbiter_monitor(self) -> Any: return self._get("arbiter_monitor")
    @property
    def stigmergy(self) -> Any: return self._get("stigmergy_field")
    @property
    def immune_engine(self) -> Any: return self._get("immune_engine")
    @property
    def multi_level_evolution(self) -> Any: return self._get("multi_level_evolution")
    @property
    def panarchy_controller(self) -> Any: return self._get("panarchy_controller")

    # ── Skill helpers ──────────────────────────────────────────────────

    def list_skills(self) -> list[dict[str, Any]]:
        sr = self._get("skill_registry")
        if sr and hasattr(sr, "_skills"):
            return [s.to_dict() for s in sr._skills.values()]
        return []

    def get_skill(self, name: str) -> dict[str, Any] | None:
        sr = self._get("skill_registry")
        if sr and hasattr(sr, "_skills"):
            s = sr._skills.get(name)
            return s.to_dict() if s else None
        return None

    def register_skill(self, name: str, description: str,
                       module: str = "sclerotium", category: str = "evolved") -> bool:
        sr = self._get("skill_registry")
        if not sr: return False
        from src.core.skill_registry import SkillMeta
        return sr.register(SkillMeta(name=name, description=description,
                                      module=module, category=category))

    # ── Scan helpers ───────────────────────────────────────────────────

    async def scan_code(self, path: str = ".", dimensions: list[str] | None = None) -> dict[str, Any]:
        scanner = self._get("architecture_scanner")
        if not scanner: return {"issues": [], "scores": {}, "total_issues": 0}

        all_issues = scanner.scan_all(path) if hasattr(scanner, "scan_all") else scanner.full_scan()
        scores = scanner.get_scores() if hasattr(scanner, "get_scores") else {}
        if dimensions:
            all_issues = [i for i in all_issues if getattr(i, "dimension", "") in dimensions]
        return {
            "issues": [{"dimension": getattr(i, "dimension", ""),
                        "severity": getattr(i, "severity", ""),
                        "file": getattr(i, "file", ""),
                        "description": getattr(i, "description", ""),
                        "suggestion": getattr(i, "suggestion", "")} for i in all_issues],
            "scores": scores, "total_issues": len(all_issues),
        }

    # ── DGM helpers ────────────────────────────────────────────────────

    def mutate_genome(self, genome_id: str, mutation_type: str, target: str = "") -> dict[str, Any]:
        dgm = self._get("dgm")
        if not dgm: return {"error": "DGM not initialized"}
        result = dgm.apply_mutation(genome_id, mutation_type, target)
        return {"new_genome_id": result.get("genome_id", ""),
                "mutation_applied": mutation_type,
                "verification_passed": result.get("verified", False),
                "diff_preview": result.get("diff", "")}
