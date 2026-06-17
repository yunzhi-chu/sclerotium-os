# Fungal Cortex v3.0 — Architecture

> **从42个器官到1个完整生命体** (From 42 Organs to 1 Complete Organism)

## 系统层级 (System Layers)

```
┌──────────────────────────────────────────────────────────────────┐
│ L7: Execution & Portfolio (trading/, bridge/)                     │
│     DataPipeline · RiskGate · PortfolioManager · OrderRouter      │
├──────────────────────────────────────────────────────────────────┤
│ L6: Meta-Cognition & Self-Improvement (l6/)                       │
│     MetaCognitionEngine · AbilityFactory · EmergenceCapture       │
│     AutoRefactorEngine · SecurityGateway · RuleEvolution          │
├──────────────────────────────────────────────────────────────────┤
│ L5: Symbiotic Cluster Platform (cluster/) ── Phase 4              │
│     AgentFactory(HSC) · Communicator(Bee+QS+Ant) · Pool(EAS)      │
│     EndogenousEngine(Autophagy) · Consensus(Bee+Octopus)          │
│     KnowledgeNetwork(Mycorrhizal) · Evolution(Symbiogenesis)      │
│     GlobalAudit(ImmuneMemory)                                     │
├──────────────────────────────────────────────────────────────────┤
│ L4: Spinal Cord + Brainstem (autonomous/) ── Phase 3              │
│  M1: IntentParser(Thalamus) + TaskDAG(Physarum) +                 │
│      ConflictDetector(Cerebellum)                                  │
│  M2: TransactionManager(ANS) + CircuitBreakerBridge(PVN)          │
│  M3: AuditTrail(Stigmergy) + CausalTracer(Hippocampus) +          │
│      Counterfactual(Prefrontal)                                    │
│  M4: OnlineEvolution(LTP/LTD) + StrategyValidator(Prion)          │
│  M5: VectorRetrieval(Olfactory) + FinancialKG(Mycorrhizal) +      │
│      MemoryWeaving(REM+Amyloid)                                    │
│  M6: PolicyEngine(Homeostasis) + BehaviorMonitor(Insula+ACC)      │
├──────────────────────────────────────────────────────────────────┤
│ L3: Immune Debate Engine (adaptive/) ── Phase 2                   │
│     MarketOfClaims · AISImmuneValidator · DebateConsensusEngine   │
├──────────────────────────────────────────────────────────────────┤
│ L0: Peripheral Nervous + Endocrine (adaptive/) ── Phase 1         │
│  L1: HMM · CUSUM · GTH-Net · DriftDetector · RegimeOrchestrator   │
│  L2: HyperNetwork(Pituitary) · StrategyAdapter · SafetyGate       │
│  L3a: TemporalSampler · MetaLearner · SelfEvolutionLoop           │
│  L6: CircuitBreaker · MemoryBridge                                │
└──────────────────────────────────────────────────────────────────┘
```

## 跨层级桥梁 (Cross-Layer Bridges) — Phase 5

```
 L0 (Peripheral)  ←→ L3 (Immune)   [5.1 AdaptiveDebateBridge: HPA axis]
 L3 (Immune)      ←→ L4 (Spinal)   [5.2 ImmuneAuditBridge: Spleen]
 L4 (Spinal)      ←→ L5 (Muscle)   [5.3 DAGClusterBridge: Neuromuscular Jn]
 L5 (Muscle)      ←→ L0 (Peripheral) [5.4 ClusterFeedbackBridge: Proprioception]
 ALL LAYERS       ←→ ALL           [5.5 UnifiedEventBus: Circulatory System]
```

## 涌现与自治 (Emergence & Autonomy) — Phase 6

```
 CrossLayerEmergence    [L0+L3+L5 3-layer consciousness detection]
 SelfHealingOrchestrator [Hemostasis→Inflammation→Proliferation→Remodeling]
 AutonomousGovernance   [5-Gate: Policy→Behavior→Debate→Counterfactual→Human]
```

## 性能与安全 (Performance & Security) — Phase 7

```
Performance:    TorchScript · ZeroMQ · msgpack · MerkleTree
Security:       JWT Rotation · Rate Limiter(GFR) · Sandbox(gVisor) · Hash Chain
```

## 数据流 (Data Flow)

```
Market Data → L0 (Sensing) → L3 (Debate) → L4 (Execution Plan)
                                            ↓
                                       L5 (Cluster Run) → Results
                                            ↓
                                       L4 (Audit + Evolution)
                                            ↓
                                  L5 Feedback → L0 Adaptation
                                            ↓
                                  L6 (Meta-Cognition: full scan optimization)
                                            ↓
                                  L7 (Portfolio: risk gate → order execution)
```

## 项目统计 (Project Statistics)

| 层 | 模块数 | 核心包 |
|-----|--------|--------|
| L0 + L3 | 18 | `src/adaptive/` |
| L4 | 17 | `src/autonomous/` |
| L5 | 10 | `src/cluster/` |
| L6 | 9 | `src/l6/` |
| L7 | 5 | `src/trading/`, `src/bridge/` |
| Core + Phase 5-7 | 13 | `src/core/`, `src/security/` |
| **Total** | **~96** | |
