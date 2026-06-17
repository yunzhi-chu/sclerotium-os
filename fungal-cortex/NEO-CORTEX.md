# Fungal Cortex v3.0 — NeoCortex Implementation Guide

> **L0→L5完整实现细节** (如同Gray's Anatomy)

## Phase 1: L0 周围神经+内分泌 (15核心类)

### L1: 三通道市场感知层

#### HMMRegimeDetector (`src/adaptive/hmm_detector.py`)
- **隐喻**: 视觉皮层V1 — 从原始价格序列提取体制特征
- **升级(ABOCD 2025)**: 滑动窗口重估计超参数、7维观测特征、6隐藏状态自动标注
- **接口**: `detect(prices: list[float]) → RegimeReport`

#### CUSUMRegimeDetector (`src/adaptive/cusum_detector.py`)
- **隐喻**: 皮肤痛觉感受器 — 对突变即时反应
- **升级(Score-Driven BOCPD 2025)**: 动态阈值(P95滚动校准)、双向累积和
- **接口**: `detect(prices: list[float]) → CUSUMReport`

#### GTHNetRegimeDetector (`src/adaptive/gthnet_detector.py`)
- **隐喻**: 前庭平衡系统 — 5玩家复制者动态
- **升级(GTH-Net 2026)**: HyperNetwork权重生成
- **接口**: `detect(observations: list[float]) → GTHNetOutput`

#### BayesianRegimeOrchestrator (`src/adaptive/regime_orchestrator.py`)
- **隐喻**: 前额叶整合皮层 — BMA贝叶斯模型平均
- **机制**: 三位专家各自意见→动态加权→统一概率分布
- **接口**: `orchestrate(opinions) → UnifiedRegimeReport`

### L2: HyperNetwork动态生成层

#### AdaptiveHyperNetwork (`src/adaptive/hypernetwork.py`)
- **隐喻**: 垂体腺(Pituitary) — 分泌三种"激素"
- **架构**: 6→32→{8,24,5} 三路输出
- **Phase 7增强**: `compile()` TorchScript JIT, `forward_compiled()` <5ms

### L3a: 自适应元学习

#### MultiDistributionTemporalSampler (`src/adaptive/temporal_sampler.py`)
- FOMAML+Reptile+Meta-SGD三算法集成

#### AdaptiveMetaLearner (`src/adaptive/meta_learner.py`)
- 突触可塑性: LTP(增强)/LTD(抑制)/稳态缩放

#### SelfEvolutionLoop (`src/adaptive/self_evolution.py`)
- 内隐适应+外显策略更新闭环

## Phase 2: L3 免疫辩论引擎 (3核心类)

### MarketOfClaims (`src/adaptive/market_of_claims.py`)
- **隐喻**: MHC抗原呈递+T/B细胞激活
- **机制**: decompose→open_market→cross_examine→synthesize
- **接口**: `process(signals) → MarketResult`

### AISImmuneValidator (`src/adaptive/immune_validator.py`)
- **隐喻**: 克隆选择+负选择+危险理论
- **99.83%准确率目标(HAIS-IDS)**
- **接口**: `validate(claims) → ValidationReport`

### DebateConsensusEngine (`src/adaptive/debate_consensus.py`)
- **隐喻**: 免疫突触+逆智慧定律防护
- **机制**: 3-5独立Agent→≥2/3通过→确认/耐受/搁置
- **接口**: `debate(claims, agents) → ConsensusResult`

## Phase 3: L4 脊髓+脑干中台 (15核心类)

### M1: 意图解析+任务编排
- **IntentParser**: `parse(user_input) → Intent`
- **TaskDAGBuilder**: `build(intent, context) → TaskDAG` (Physarum Lagrangian优化)
- **ConflictDetector**: `check_dag(dag) → list[Conflict]`

### M2: 自主执行
- **TransactionManager**: `create(desc, tasks) → Transaction`, `commit(tx_id) → (bool, str)`
- **CircuitBreakerBridge**: `is_allowed(module) → bool`

### M3: 审计+因果+反事实
- **AuditTrail**: `record(event, source, input, output, trace) → AuditRecord` (hash链+Merkle树)
- **CausalTracer**: `trace_back(target_id) → CausalChain`
- **CounterfactualEngine**: `create_scenario(name, ...) → Scenario`

### M4: 演化+验证
- **OnlineEvolutionEngine**: `micro_evolve(stats)`, `slow_evolve()`
- **StrategyAutoValidator**: `validate(name, sharpe, max_dd, win_rate) → ValidationReport`

### M5: 记忆+知识
- **VectorRetrievalEngine**: `insert(id, vector)`, `search(query, top_k) → list[SearchResult]`
- **FinancialKnowledgeGraph**: `add_entity()`, `add_relation()`, `query_relations(id, hops)`
- **MemoryWeaving**: `attend()`, `store_episode()`, `weave() → MemoryConsolidation`

### M6: 约束+监控
- **PolicyEngine**: `check(category, constraint, value) → (bool, reason)`
- **BehaviorMonitor**: `observe_param()`, `observe_signal()`, `observe_skill_call()`

## Phase 4: L5 共生生态集群 (8核心+RootAgent升级)

### AgentFactory (`src/cluster/agent_factory.py`)
- HSC干细胞生态位: 8种AgentSpecialty→create_agent, get_or_create, apoptose
- **限制**: MAX_AGENTS=50, MAX_MEMORY_MB=512

### ClusterCommunicator (`src/cluster/communicator.py`)
- 三模态: Bee(11 MessageTypes) + Bacterial(Quorum 0.6) + Ant(Pheromone evaporation)
- **Phase 7**: `enable_zmq_transport()` ZeroMQ PUB/SUB/PUSH/PULL

### AgentPoolManager (`src/cluster/pool_manager.py`)
- EAS: 3-tier pools(active/idle/sleep) + ACO routing + BCAA feedback

### EndogenousTargetEngine (`src/cluster/endogenous_engine.py`)
- Autophagy: 5 TargetTypes + 4 MetabolicModes(fed/fasting/exercise/recovery)

### DistributedConsensus (`src/cluster/consensus.py`)
- Bee quorum(0.6) + Octopus confederal + 逆智慧定律保护

### GlobalKnowledgeNetwork (`src/cluster/knowledge_network.py`)
- Mycorrhizal Wood-Wide Web: MemoryMetabolism + Mother Tree hubs + quarantine

### DistributedEvolutionEngine (`src/cluster/distributed_evolution.py`)
- Symbiogenesis + SHAP: micro(±1%) / group(A-B test) / global(weekly cull)

### GlobalAuditTrail (`src/cluster/global_audit.py`)
- Immune memory: 11 AuditEventTypes + SHA256 chain + anomaly detection

### RootAgent v4.0 (`src/orchestration/root_agent.py`)
- 新增: `submit_batch_task()`, `aggregate_results()`, `enforce_carrying_capacity()`

## Phase 5: 五座跨层级桥梁

| 桥梁 | 关键方法 |
|------|---------|
| AdaptiveDebateBridge | `adapt_from_regime()`, `feedback_to_regime()` |
| ImmuneAuditBridge | `process_claim()`, `generate_audit_record()`, `resolve_pending()` |
| DAGClusterBridge | `decompose_dag()`, `to_batch_input()`, `mark_started/completed()` |
| ClusterFeedbackBridge | `sense()`, `sense_from_stats()`, `get_l0_adjustment_summary()` |
| UnifiedEventBus | `publish()` + 4 standard events + `get_causal_trace()` + SQLite |

## Phase 6: 涌现与自愈

| 模块 | 关键方法 |
|------|---------|
| CrossLayerEmergence | `observe_l0/l3/l5()`, `execute_recalibration()`, `recognize_ecotype()` |
| SelfHealingOrchestrator | `report_health()`, `diagnose()`, `repair()`, `verify()`, `auto_heal()` |
| AutonomousGovernance | `submit_proposal()`, `review()` (5 gates), `human_override()` |

## Phase 7: 性能与安全

| 组件 | 关键方法 |
|------|---------|
| TorchScript | `HyperNetwork.compile()`, `forward_compiled()` |
| ZeroMQ | `ClusterCommunicator.enable_zmq_transport()`, `send_zmq()` |
| Merkle Tree | `AuditTrail.build_merkle_tree()`, `export_immutable_chain()` |
| msgpack | `MsgPackSerializer.encode/decode()`, `CompactEvent.serialize/deserialize()` |
| JWT | `JWTAuthManager.create_token_pair()`, `verify_token()`, `revoke_subject()` |
| Sandbox | `SandboxHardening.create_profile()`, `generate_docker_args()`, 5 security levels |
| Rate Limiter | `RateLimiter.check()`, `degrade_stage()`, GFR 5-stage kidney model |

## 开发者快速上手

```python
# 1. 导入整个系统
from src.adaptive import BayesianRegimeOrchestrator
from src.autonomous import IntentParser, TaskDAGBuilder, AuditTrail
from src.cluster import AgentFactory, ClusterCommunicator
from src.core import CrossLayerEmergence, SelfHealingOrchestrator

# 2. L0感知市场体制
orchestrator = BayesianRegimeOrchestrator()
report = orchestrator.orchestrate(opinions)

# 3. L4解析意图+建立DAG
parser = IntentParser()
intent = parser.parse("回测MACD在沪深300上90天")
dag_builder = TaskDAGBuilder()
dag = dag_builder.build(intent.intent_type.value, intent.params)

# 4. L5集群执行
factory = AgentFactory()
agent = factory.create_agent("strategy", {"strategy": "MACD"})

# 5. 跨层桥接
from src.adaptive.debate_adaptive_bridge import AdaptiveDebateBridge
bridge = AdaptiveDebateBridge()
params = bridge.adapt_from_regime("bear", 0, 0.9, 0.3)
```
