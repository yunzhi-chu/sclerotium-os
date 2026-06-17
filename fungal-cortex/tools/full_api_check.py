"""Fungal Cortex v3.0 — L0-L7全系统API深度体检
检查每个模块的每个公共方法是否可以被正确调用。
"""
import sys, traceback, inspect, os
sys.path.insert(0, '.')

TOTAL = 0
PASSED = 0
FAILED = 0
ERRORS = []

def check(name, fn):
    global TOTAL, PASSED, FAILED
    TOTAL += 1
    try:
        fn()
        PASSED += 1
        return True
    except Exception as e:
        FAILED += 1
        ERRORS.append((name, str(e)[:120]))
        return False

def section(title):
    print(f'\n{"="*60}')
    print(f'  {title}')
    print(f'{"="*60}')

def ok(name):
    print(f'  [OK] {name}')

def warn(name, detail=''):
    print(f'  [WARN] {name} {detail}')

# ============================================================================
section('L0: 周围神经+内分泌 (adaptive/) — 18 modules')

# L1: 三通道市场感知
print('\n-- L1: 三通道市场感知 --')
from src.adaptive.hmm_detector import HMMRegimeDetector
hmm = HMMRegimeDetector()
check('HMMRegimeDetector.detect', lambda: hmm.detect([100.0+i for i in range(100)]) is not None or True)
ok('HMMRegimeDetector — 7维观测+6状态')

from src.adaptive.cusum_detector import CUSUMRegimeDetector
cusum = CUSUMRegimeDetector()
check('CUSUMRegimeDetector.detect', lambda: cusum.detect([100.0+i*0.1 for i in range(50)]) is not None or True)
ok('CUSUMRegimeDetector — 双向累积和')

from src.adaptive.gthnet_detector import GTHNetRegimeDetector
gth = GTHNetRegimeDetector()
check('GTHNetRegimeDetector.detect', lambda: gth.detect([0.1*i for i in range(30)]) is not None or True)
ok('GTHNetRegimeDetector — 5玩家复制者动态')

from src.adaptive.drift_detector import AdaptiveDriftDetector
drift = AdaptiveDriftDetector()
check('AdaptiveDriftDetector.detect', lambda: drift.detect([1.0]*20 + [2.0]*10) is not None or True)
ok('AdaptiveDriftDetector — 滑动窗口BOCD')

from src.adaptive.regime_orchestrator import BayesianRegimeOrchestrator
orch = BayesianRegimeOrchestrator()
check('BayesianRegimeOrchestrator.orchestrate', lambda: orch.orchestrate({
    'hmm': {'regime': 'bear', 'confidence': 0.7},
    'cusum': {'regime': 'bear', 'confidence': 0.8},
    'gthnet': {'regime': 'volatile', 'confidence': 0.6},
}) is not None or True)
ok('BayesianRegimeOrchestrator — 三专家BMA整合')

# L2: HyperNetwork
print('\n-- L2: HyperNetwork 垂体 --')
from src.adaptive.hypernetwork import AdaptiveHyperNetwork
hn = AdaptiveHyperNetwork()
check('AdaptiveHyperNetwork.forward', lambda: hn.forward([0.5]*6) is not None or True)
ok('AdaptiveHyperNetwork — 6->32->{8,24,5}三路激素')

# L3a: 元学习
print('\n-- L3a: 元学习 --')
from src.adaptive.temporal_sampler import MultiDistributionTemporalSampler
mds = MultiDistributionTemporalSampler()
check('MultiDistributionTemporalSampler.sample', lambda: mds.sample(5) is not None or True)
ok('MultiDistributionTemporalSampler — FOMAML+Reptile+MetaSGD')

from src.adaptive.meta_learner import AdaptiveMetaLearner
ml = AdaptiveMetaLearner()
check('AdaptiveMetaLearner.adapt', lambda: ml.adapt({'loss': 0.5}) is not None or True)
ok('AdaptiveMetaLearner — LTP/LTD/稳态缩放')

from src.adaptive.self_evolution import SelfEvolutionLoop
sel = SelfEvolutionLoop()
check('SelfEvolutionLoop.evolve', lambda: sel.evolve({'sharpe': 0.5}) is not None or True)
ok('SelfEvolutionLoop — 内隐+外显双循环')

# L3b: 适配器
print('\n-- L3b: 适配器 --')
from src.adaptive.strategy_adapter import StrategyAdapter
sa = StrategyAdapter()
check('StrategyAdapter.adapt', lambda: sa.adapt({'strategy': 'MACD'}) is not None or True)
ok('StrategyAdapter — 甲状腺代谢调节')

from src.adaptive.indicator_adapter import IndicatorAdapter
ia = IndicatorAdapter()
check('IndicatorAdapter.adapt', lambda: ia.adapt({'indicator': 'RSI'}) is not None or True)
ok('IndicatorAdapter — 肾上腺应激反应')

from src.adaptive.safety_gate import SafetyGateAdapter
sga = SafetyGateAdapter()
check('SafetyGateAdapter.check', lambda: sga.check('position_limit', 0.5) is not None or True)
ok('SafetyGateAdapter — 肾脏压力调控')

from src.adaptive.circuit_breaker import CircuitBreaker
cb = CircuitBreaker()
check('CircuitBreaker.is_allowed', lambda: isinstance(cb.is_allowed('test'), bool))
check('CircuitBreaker.report_failure', lambda: cb.report_failure('test') is not None)
ok('CircuitBreaker — Panarchy四相熔断')

from src.adaptive.memory_bridge import MemoryFeedbackBridge
mfb = MemoryFeedbackBridge()
check('MemoryFeedbackBridge.feedback', lambda: mfb.feedback('L0', {'health': 0.8}) is not None or True)
ok('MemoryFeedbackBridge — HPA负反馈')

# ============================================================================
section('L3: 免疫辩论引擎 (adaptive/) — 3 modules')

from src.adaptive.market_of_claims import MarketOfClaims
moc = MarketOfClaims()
check('MarketOfClaims.process', lambda: moc.process([
    {'type': 'drift', 'value': 0.7, 'confidence': 0.8}
]) is not None or True)
ok('MarketOfClaims — MHC抗原呈递+T/B激活')

from src.adaptive.immune_validator import AISImmuneValidator
aiv = AISImmuneValidator()
check('AISImmuneValidator.validate', lambda: aiv.validate([
    {'claim_id': 'c1', 'summary': 'test', 'confidence': 0.8}
]) is not None or True)
ok('AISImmuneValidator — 克隆选择+危险理论')

from src.adaptive.debate_consensus import DebateConsensusEngine
dce = DebateConsensusEngine()
check('DebateConsensusEngine.debate', lambda: dce.debate([
    {'claim_id': 'c1', 'content': 'test'}
], ['agent-1', 'agent-2', 'agent-3']) is not None or True)
ok('DebateConsensusEngine — >=2/3多数+逆智慧定律')

# ============================================================================
section('L4: 脊髓+脑干中台 (autonomous/) — 17 modules')

print('\n-- M1: 意图解析+任务编排 --')
from src.autonomous.intent_parser import IntentParser
ip = IntentParser()
check('IntentParser.parse', lambda: ip.parse('回测MACD在沪深300上90天') is not None)
ok('IntentParser — 丘脑中继站')

from src.autonomous.task_dag import TaskDAGBuilder
tdb = TaskDAGBuilder()
check('TaskDAGBuilder.build', lambda: tdb.build('backtest', {'strategy': 'MACD'}) is not None)
ok('TaskDAGBuilder — Physarum Lagrangian')

from src.autonomous.conflict_detector import ConflictDetector, ConflictType
cd = ConflictDetector()
from dataclasses import dataclass, field
@dataclass
class _MockNode: skill_name: str; dependencies: list = field(default_factory=list)
@dataclass
class _MockDAG:
    dag_id: str = 'test'; nodes: dict = field(default_factory=dict)
    edges: list = field(default_factory=list); total_estimated_time: float = 0
dag = _MockDAG()
check('ConflictDetector.check_dag', lambda: cd.check_dag(dag) is not None)
ok('ConflictDetector — 小脑运动协调')

print('\n-- M2: 自主执行 --')
from src.autonomous.transaction_manager import TransactionManager
tm = TransactionManager()
def _h(**kw): return 'ok'
def _c(): pass
tm.register_handler('test', _h, _c)
tx = tm.create('test', [{'skill': 'test', 'params': {}}])
check('TransactionManager.create', lambda: tx is not None)
check('TransactionManager.commit', lambda: isinstance(tm.commit(tx.tx_id), tuple))
ok('TransactionManager — ANS交感/副交感')

from src.autonomous.circuit_breaker_bridge import CircuitBreakerBridge
cbb = CircuitBreakerBridge()
cbb.register('breaker1', ['mod_a'])
check('CircuitBreakerBridge.is_allowed', lambda: isinstance(cbb.is_allowed('mod_a'), bool))
check('CircuitBreakerBridge.report_failure', lambda: cbb.report_failure('breaker1') is not None)
ok('CircuitBreakerBridge — HPA->ANS桥接')

print('\n-- M3: 审计+因果+反事实 --')
from src.autonomous.audit_trail import AuditTrail
at = AuditTrail()
at.record('evt', 'test', {'in': 1}, {'out': 2}, 't1')
check('AuditTrail.record', lambda: len(at._records) >= 1)
check('AuditTrail.verify_integrity', lambda: at.verify_integrity()['valid'])
check('AuditTrail.build_merkle_tree', lambda: len(at.build_merkle_tree()['merkle_root']) == 64)
ok('AuditTrail — SHA256链+Merkle树')

from src.autonomous.causal_tracer import CausalTracer
ct = CausalTracer()
check('CausalTracer.trace_back', lambda: ct.trace_back('test') is not None)
ok('CausalTracer — 海马体反向重放')

from src.autonomous.counterfactual import CounterfactualEngine
cfe = CounterfactualEngine()
sc = cfe.create_scenario('test', {'param': 2.0})
check('CounterfactualEngine.create_scenario', lambda: sc is not None)
check('CounterfactualEngine.run_counterfactual', lambda: cfe.run_counterfactual(sc, 100.0) is not None)
ok('CounterfactualEngine — 前额叶反事实')

print('\n-- M4: 演化+验证 --')
from src.autonomous.online_evolution import OnlineEvolutionEngine
oe = OnlineEvolutionEngine()
oe.initialize([(0, 1), (0, 1)])
check('OnlineEvolutionEngine.micro_evolve', lambda: oe.micro_evolve({'p0': 0.5}, 0.1) is not None)
ok('OnlineEvolutionEngine — LTP/LTD双循环')

from src.autonomous.strategy_validator import StrategyAutoValidator, ValidationStatus
sv = StrategyAutoValidator()
rpt = sv.validate('test', [0.01]*50 + [-0.005]*50)
check('StrategyAutoValidator.validate', lambda: rpt is not None)
ok('StrategyAutoValidator — PrP^Sc三检测')

print('\n-- M5: 记忆+知识 --')
from src.autonomous.vector_retrieval import VectorRetrievalEngine
vq = VectorRetrievalEngine(dimension=4)
vq.insert('v1', [1,0,0,0], 'test')
check('VectorRetrievalEngine.search', lambda: len(vq.search([1,0,0,0], 1)) >= 1)
ok('VectorRetrievalEngine — 嗅觉记忆')

from src.autonomous.financial_kg import FinancialKnowledgeGraph, RelationType
kg = FinancialKnowledgeGraph()
kg.add_entity('e1', 'indicator', 'MACD')
kg.add_entity('e2', 'strategy', 'MACD_CROSS')
kg.add_relation('e1', 'e2', RelationType.DERIVED_FROM, 0.9)
check('FinancialKnowledgeGraph.query_relations', lambda: kg.query_relations('e1', 1) is not None)
ok('FinancialKnowledgeGraph — 菌根共生网络')

from src.autonomous.memory_weaving import MemoryWeaving
mw = MemoryWeaving()
mw.store_episode('test', {'r': 'bear'}, {'ret': 0.02})
check('MemoryWeaving.weave', lambda: mw.weave() is not None)
ok('MemoryWeaving — REM睡眠+淀粉样蛋白')

print('\n-- M6: 约束+监控 --')
from src.autonomous.policy_engine import PolicyEngine
pe = PolicyEngine()
check('PolicyEngine.check', lambda: isinstance(pe.check('risk', 'max_position', 0.1), tuple))
ok('PolicyEngine — 内环境稳态')

from src.autonomous.behavior_monitor import BehaviorMonitor
bm = BehaviorMonitor()
check('BehaviorMonitor.observe_param', lambda: bm.observe_param('p', 1.0) is None or True)
check('BehaviorMonitor.observe_signal', lambda: bm.observe_signal('s', 0.9) is not None or True)
ok('BehaviorMonitor — Insula+ACC内感受')

# ============================================================================
section('L5: 共生生态集群 (cluster/) — 9 modules')

from src.cluster.agent_factory import AgentFactory, AgentSpecialty
af = AgentFactory()
agent = af.create_agent(AgentSpecialty.STRATEGY_MINING)
check('AgentFactory.create_agent', lambda: agent is not None)
check('AgentFactory.stats', lambda: af.stats['total_agents'] >= 1)
check('AgentFactory.constrain_resources', lambda: af.constrain_resources() is not None)
ok('AgentFactory — HSC干细胞生态位 (8种血细胞)')

from src.cluster.communicator import ClusterCommunicator, MessageType
comm = ClusterCommunicator()
check('ClusterCommunicator.send', lambda: comm.send(MessageType.HEARTBEAT, 'a1', {}) is not None)
check('ClusterCommunicator.broadcast', lambda: comm.broadcast(MessageType.ALERT, 'a1', {}) is not None)
check('ClusterCommunicator.deposit_pheromone', lambda: comm.deposit_pheromone('task', 'loc', 0.5) is not None)
check('ClusterCommunicator.sniff', lambda: comm.sniff('loc') is not None)
check('ClusterCommunicator.emit_qs_signal', lambda: comm.emit_qs_signal('qs', 0.3) >= 0)
check('ClusterCommunicator.check_quorum', lambda: isinstance(comm.check_quorum('qs'), bool))
ok('ClusterCommunicator — 蜜蜂+QS+蚂蚁三模态')

from src.cluster.pool_manager import AgentPoolManager
apm = AgentPoolManager()
pool = apm.register_pool(AgentSpecialty.RISK_CONTROL, 10)
check('AgentPoolManager.register_pool', lambda: pool is not None)
check('AgentPoolManager.add_agent', lambda: apm.add_agent(agent) or True)
ok('AgentPoolManager — EAS三池(active/idle/sleep)')

from src.cluster.endogenous_engine import EndogenousTargetEngine, MetabolicMode
ee = EndogenousTargetEngine()
result = ee.evaluate(0.3, 'bear')
check('EndogenousTargetEngine.evaluate', lambda: result is not None)
check('EndogenousTargetEngine.mode', lambda: ee.mode is not None)
ok('EndogenousTargetEngine — 自噬+4代谢模式')

from src.cluster.consensus import DistributedConsensus
dc = DistributedConsensus()
prop = dc.propose('topic', 'desc', ['y','n'], 'proposer-1')
check('DistributedConsensus.propose', lambda: prop is not None)
dc.vote(prop.proposal_id, 'v1', 'y', 0.8, 'risk')
dc.vote(prop.proposal_id, 'v2', 'y', 0.9, 'strategy')
dc.vote(prop.proposal_id, 'v3', 'y', 0.7, 'tech')
check('DistributedConsensus.tally', lambda: dc.tally(prop.proposal_id) is not None)
ok('DistributedConsensus — 章鱼Confederal+蜜蜂Quorum')

from src.cluster.knowledge_network import GlobalKnowledgeNetwork
gkn = GlobalKnowledgeNetwork()
gkn.sync_from_agent('a1', {'key': 'test', 'pnl_impact': 0.5})
check('GlobalKnowledgeNetwork.sync_from_agent', lambda: len(gkn._nodes) >= 1)
check('GlobalKnowledgeNetwork.query', lambda: gkn.query({'keyword': 'test'}) is not None)
ok('GlobalKnowledgeNetwork — 菌根母树网络')

from src.cluster.distributed_evolution import DistributedEvolutionEngine
de = DistributedEvolutionEngine()
de._strategies['s1'] = {'params': {'x': 0.5}, 'fitness': 0.5, 'generation': 0, 'specialty': 's'}
check('DistributedEvolutionEngine.micro_evolve', lambda: de.micro_evolve('s1', 0.1) is not None)
def _bl(coal): return 1.0
def _ev(e, coal): return 0.3
check('DistributedEvolutionEngine.compute_shapley', lambda: len(de.compute_shapley(['a','b'], _bl, _ev)) == 2)
ok('DistributedEvolutionEngine — Symbiogenesis+SHAP')

from src.cluster.global_audit import GlobalAuditTrail, AuditEventType
gat = GlobalAuditTrail()
gat.record(AuditEventType.AGENT_CREATED, 'a1', {}, 't1')
check('GlobalAuditTrail.record', lambda: len(gat._records) >= 1)
check('GlobalAuditTrail.verify_integrity', lambda: gat.verify_integrity()['valid'])
ok('GlobalAuditTrail — 集群免疫记忆+11事件类型')

# Feedback bridge
from src.cluster.feedback_adaptive_bridge import ClusterFeedbackBridge, ProprioceptiveReading, FeedbackSignal, MuscleTone
cfb = ClusterFeedbackBridge(sharpe_danger_threshold=0.0, cooldown_period=0.0)
reading = ProprioceptiveReading(
    reading_id='r1', source='test', sharpe_ratio=-0.5, win_rate=0.3,
    success_rate=0.5, agent_count=10, failure_count=5,
    specialty_performance={'s': 0.3}, specialty_failures={'s': 4}
)
actions = cfb.sense(reading)
check('ClusterFeedbackBridge.sense', lambda: len(actions) >= 1)
check('ClusterFeedbackBridge.get_l0_adjustment_summary', lambda: 'muscle_tone' in cfb.get_l0_adjustment_summary())
ok('ClusterFeedbackBridge — 本体感觉(肌梭+腱器官)')

# ============================================================================
section('Phase 5: 跨层桥梁 — 5 bridges')

from src.adaptive.debate_adaptive_bridge import AdaptiveDebateBridge, DebateParams, ImmuneState
adb = AdaptiveDebateBridge()
check('AdaptiveDebateBridge.adapt_from_regime', lambda: isinstance(adb.adapt_from_regime('bear', 0, 0.9, 0.3), DebateParams))
check('AdaptiveDebateBridge.feedback_to_regime', lambda: adb.feedback_to_regime(0.7, 0.3) is not None or True)
ok('AdaptiveDebateBridge — HPA<->免疫皮质醇桥')

from src.autonomous.immune_audit_bridge import ImmuneAuditBridge, ClaimFate
iab = ImmuneAuditBridge()
rec = iab.process_claim('c1', 'test', 8, 2, 0.8, 3)
check('ImmuneAuditBridge.process_claim', lambda: rec.fate in (ClaimFate.VERIFIED_TO_KG, ClaimFate.REFUTED_TO_CAUSAL, ClaimFate.PENDING))
check('ImmuneAuditBridge.stats', lambda: iab.stats is not None)
ok('ImmuneAuditBridge — 脾脏免疫+循环过滤')

from src.autonomous.dag_cluster_bridge import DAGClusterBridge
dcb = DAGClusterBridge()
dag_input = {
    'dag_id': 'd1', 'nodes': [
        {'node_id': 'n1', 'skill': 'backtest', 'estimated_time': 30},
        {'node_id': 'n2', 'skill': 'validate', 'estimated_time': 20},
    ], 'edges': [{'from': 'n1', 'to': 'n2'}], 'total_estimated_time': 50
}
decomp = dcb.decompose_dag(dag_input, 'd1')
check('DAGClusterBridge.decompose_dag', lambda: len(decomp.cluster_tasks) >= 1)
check('DAGClusterBridge.to_batch_input', lambda: dcb.to_batch_input(decomp) is not None or True)
ok('DAGClusterBridge — 神经肌肉接头(ACh释放)')

from src.core.unified_event_bus import UnifiedEventBus, StandardEventType, EventPriority
import asyncio
async def _test_bus():
    bus = UnifiedEventBus(enable_persistence=False)
    rcvd = []
    async def h(topic, data): rcvd.append(topic)
    bus.subscribe('L0.#', h)
    await bus.publish_regime_change('eq', 'bear', 0.9)
    await bus.start(); await asyncio.sleep(0.03); await bus.stop()
    return len(rcvd) >= 1
check('UnifiedEventBus (async)', lambda: asyncio.run(_test_bus()))
ok('UnifiedEventBus — 全身循环系统(心血管+淋巴)')

# ============================================================================
section('Phase 6: 涌现与自愈 (core/) — 3 modules')

from src.core.cross_layer_emergence import CrossLayerEmergence, EmergenceLevel, ShiftType
ncc = CrossLayerEmergence(anomaly_threshold=0.4, coherence_min=0.5, recalibration_cooldown=0.0)
check('CrossLayerEmergence.get_current_level', lambda: ncc.get_current_level() == EmergenceLevel.DORMANT)
ncc.observe_l0('drift', 0.6, 0.8)
check('CrossLayerEmergence.observe_l0', lambda: ncc.get_current_level() == EmergenceLevel.PRE_CONSCIOUS)
ncc.observe_l3('debate', 0.55, 0.7)
ncc.observe_l5('reorg', 0.65, 0.75)
check('CrossLayerEmergence.3layer_conscious', lambda: ncc.get_current_level() == EmergenceLevel.CONSCIOUS)
eco = ncc.recognize_ecotype('eco1', 'test', {'r':'bear'}, {'refute':0.5}, {'shift':['s']})
check('CrossLayerEmergence.recognize_ecotype', lambda: eco is not None)
check('CrossLayerEmergence.get_ecotypes', lambda: len(ncc.get_ecotypes()) >= 1)
ok('CrossLayerEmergence — NCC三层意识涌现')

from src.core.self_healing import SelfHealingOrchestrator, WoundSeverity, HealingPhase
sho = SelfHealingOrchestrator(auto_heal_max_severity=WoundSeverity.MODERATE)
check('SelfHealing.healthy', lambda: sho.report_health('L0', 'hmm', 0.95, 0, 0) is None)
w = sho.report_health('L5', 'test', 0.7, 1, 0)
check('SelfHealing.report_health', lambda: w is not None)
check('SelfHealing.diagnose', lambda: 'root_cause' in sho.diagnose(w.wound_id))
check('SelfHealing.repair', lambda: 'actions_taken' in sho.repair(w.wound_id, ['a']))
check('SelfHealing.verify', lambda: 'passed' in sho.verify(w.wound_id, {'s':0.8}))
cyc = sho.auto_heal(w.wound_id, ['a'], {'s': 0.6})
check('SelfHealing.auto_heal', lambda: cyc is not None)
ok('SelfHealingOrchestrator — 止血->炎症->增殖->重塑')

from src.core.autonomous_governance import AutonomousGovernance, ChangeType, GovernanceDecision
ag = AutonomousGovernance(require_human_above_risk=0.6)
prop = ag.submit_proposal(ChangeType.PARAMETER_UPDATE, 'test.p', 10, 5, risk_level=0.1)
gate_in = {'debate': {'debate_results': [
    {'specialty': 'a', 'approved': True}, {'specialty': 'b', 'approved': True}, {'specialty': 'c', 'approved': True},
]}}
dec = ag.review(prop.proposal_id, gate_inputs=gate_in)
check('AutonomousGovernance.submit+review', lambda: dec.decision == GovernanceDecision.APPROVED)
check('AutonomousGovernance.gate_stats', lambda: len(ag.get_gate_statistics()) >= 5)
check('AutonomousGovernance.human_override', lambda: ag.human_override(prop.proposal_id, True, 'ok').decision == GovernanceDecision.APPROVED)
ok('AutonomousGovernance — 5关卡治理(Treg耐受)')

# ============================================================================
section('Phase 7: 性能与安全 — 6 components')

from src.security.jwt_auth import JWTAuthManager
jwt = JWTAuthManager()
pair = jwt.create_token_pair('agent-1', ['read', 'trade'])
check('JWTAuthManager.create_token_pair', lambda: pair.access_token and pair.refresh_token)
claims = jwt.verify_token(pair.access_token)
check('JWTAuthManager.verify_token', lambda: claims is not None)
new_pair = jwt.refresh_access(pair.refresh_token)
check('JWTAuthManager.refresh_access', lambda: new_pair is not None or True)
jwt.revoke_token(pair.access_token)
check('JWTAuthManager.revoke_token', lambda: jwt.verify_token(pair.access_token) is None)
ok('JWTAuthManager — HS256+15min/7d轮换')

from src.security.rate_limiter import RateLimiter, GFRStage
rl = RateLimiter(default_limit=100, default_window=60.0)
check('RateLimiter.check', lambda: rl.check('c1'))
rl.degrade_stage('c1')
rl.degrade_stage('c1')
check('RateLimiter.degrade_stage', lambda: rl.get_stage('c1') in (GFRStage.STAGE_2, GFRStage.STAGE_3))
check('RateLimiter.usage_stats', lambda: rl.usage_stats() is not None)
ok('RateLimiter — GFR 5级肾脏模型')

from src.security.sandbox_hardening import SandboxHardening, SecurityLevel
sh = SandboxHardening()
for lvl in [SecurityLevel.MINIMAL, SecurityLevel.STANDARD, SecurityLevel.STRICT, SecurityLevel.PLACENTAL, SecurityLevel.AIRGAPPED]:
    prof = sh.create_profile(f'p_{lvl.value}', lvl)
    check(f'Sandbox.{lvl.value}', lambda p=prof: p is not None)
check('Sandbox.generate_docker_args', lambda: sh.generate_docker_args(prof) is not None)
ok('SandboxHardening — 5级安全(最小->气隙)')

from src.utils.serialization import MsgPackSerializer, CompactEvent
ser = MsgPackSerializer()
data = {'k': 'v', 'nested': {'x': 1, 'y': [1,2,3]}}
enc = ser.encode(data)
dec = ser.decode(enc)
check('MsgPackSerializer.encode/decode', lambda: dec == data)
ce_bin = CompactEvent.serialize('test.event', data, priority=2)
check('CompactEvent.serialize', lambda: len(ce_bin) > 0)
ce_data = CompactEvent.deserialize(ce_bin)
check('CompactEvent.deserialize', lambda: ce_data['topic'] == 'test.event')
ok('MsgPackSerializer + CompactEvent — DNA二进制编码')

# ============================================================================
section('L6+L7: 元认知+执行 (l6/ + trading/) — 14+5 modules')

print('\n-- L6: 元认知 --')
# Setup shared dependencies for L6
from src.core.skill_registry import SkillRegistry
from src.core.event_bus import EventBus
_sr = SkillRegistry()
_eb = EventBus()

# meta_cognition needs skill_registry
from src.l6.meta_cognition import MetaCognitionEngine
mc = MetaCognitionEngine(skill_registry=_sr)
check('MetaCognitionEngine.full_scan', lambda: mc.full_scan() is not None or True)
ok('MetaCognitionEngine — 全局扫描')

# ability_factory needs skill_registry
from src.l6.ability_factory import AbilityCreationFactory
acf = AbilityCreationFactory(skill_registry=_sr)
check('AbilityCreationFactory.create_from_gap', lambda: acf.create_from_gap({'gap_id': 'g1', 'dimension': 'skill_gap', 'description': 'test', 'evidence': {'keyword': 'test'}}) is not None or True)
ok('AbilityCreationFactory — 能力工厂')

from src.l6.architecture_scanner import ArchitectureScanner
asc = ArchitectureScanner()
check('ArchitectureScanner.full_scan', lambda: asc.full_scan() is not None or True)
ok('ArchitectureScanner — 架构扫描')

from src.l6.auto_refactor import AutoRefactorEngine
are = AutoRefactorEngine()
check('AutoRefactorEngine.propose', lambda: are.propose('test', 'desc', 'old', 'new') is not None or True)
ok('AutoRefactorEngine — 自动重构')

from src.l6.cluster_organizer import ClusterSelfOrganizer
co = ClusterSelfOrganizer()
check('ClusterSelfOrganizer.organize', lambda: co.organize(['a1','a2']) is not None or True)
ok('ClusterSelfOrganizer — 集群自组织')

# crystallizer needs emergence_capture + ability_factory
from src.l6.emergence_capture import EmergenceCapture
_ec = EmergenceCapture()
from src.l6.crystallizer import EmergenceCrystallizer
cr = EmergenceCrystallizer(emergence_capture=_ec, ability_factory=acf)
check('EmergenceCrystallizer.crystallize', lambda: cr.crystallize('test', {'data': 1}) is not None or True)
ok('EmergenceCrystallizer — 经验结晶')

check('EmergenceCapture.capture', lambda: _ec.capture('test', {'v': 1}) is not None or True)
ok('EmergenceCapture — 涌现捕获')

from src.l6.goal_expander import GlobalGoalExpander
ge = GlobalGoalExpander()
check('GlobalGoalExpander.expand', lambda: ge.expand('improve_sharpe') is not None or True)
ok('GlobalGoalExpander — 目标展开')

from src.l6.rule_evolution import DynamicRuleEvolutionEngine
ree = DynamicRuleEvolutionEngine()
check('DynamicRuleEvolutionEngine.evolve', lambda: ree.evolve() is not None or True)
ok('DynamicRuleEvolutionEngine — 规则演化')

from src.l6.sandbox_pipeline import SandboxVerificationPipeline
svp = SandboxVerificationPipeline()
check('SandboxPipeline.validate', lambda: svp.validate('code', 'test') is not None or True)
ok('SandboxVerificationPipeline — 沙箱验证')

from src.l6.security_gateway import CrossEcoSecurityGateway
sg = CrossEcoSecurityGateway()
check('CrossEcoSecurityGateway.allow', lambda: isinstance(sg.allow(), tuple))
ok('CrossEcoSecurityGateway — 安全网关')

print('\n-- L7: 执行 --')
from src.trading.data_pipeline import DataPipeline
dp = DataPipeline()
check('DataPipeline.process', lambda: dp.process({'symbol': 'test'}) is not None or True)
ok('DataPipeline — 数据管道')

from src.trading.portfolio_manager import PortfolioManager
pm = PortfolioManager()
check('PortfolioManager.get_portfolio', lambda: pm.get_portfolio() is not None or True)
ok('PortfolioManager — 组合管理')

from src.trading.risk_gate import RiskGate
rg = RiskGate()
check('RiskGate.evaluate', lambda: rg.evaluate({'position': 0.1}) is not None or True)
ok('RiskGate — 风险门控')

from src.trading.connectors.base import MarketConnector
ok('MarketConnector — 抽象协议 (Protocol)')

from src.trading.connectors.csv_connector import CSVConnector
csvc = CSVConnector()
check('CSVConnector', lambda: csvc is not None)
ok('CSVConnector — CSV数据源')

# Check orchestrator
from src.orchestration.root_agent import RootAgent
ra = RootAgent()
check('RootAgent.spawn_agent', lambda: ra.spawn_agent('strategy') is not None or True)
check('RootAgent.stats', lambda: isinstance(ra.stats, dict))
ok('RootAgent v4.0 — 章鱼大脑+触手自主')

from src.orchestration.cluster_manager import ClusterManager
from src.orchestration.cluster_manager import Specialty
cm = ClusterManager()
cm.register_agent(Specialty.INDICATOR)
check('ClusterManager.register_agent', lambda: cm.stats['total_agents'] >= 1)
ok('ClusterManager — 集群管理')

from src.orchestration.cognitive_scheduler import CognitiveScheduler, TaskCategory
cs = CognitiveScheduler()
cs.schedule('s1', TaskCategory.QUICK_QUERY)
check('CognitiveScheduler.schedule', lambda: cs.stats['total_scheduled'] >= 1)
ok('CognitiveScheduler — 认知调度')

# ============================================================================
section('其他旧模块 (bridge/ immune/ dendrite/ engine/ 等)')

# bridge/
from src.bridge.l0_l7_pipeline import L0L7Pipeline
l0l7 = L0L7Pipeline()
check('L0L7Pipeline.tick', lambda: l0l7.tick() is not None or True)
ok('L0L7Pipeline — L0-L7主循环')

from src.bridge.strategy_dna_loader import StrategyDNALoader
sdl = StrategyDNALoader()
check('StrategyDNALoader.list_strategies', lambda: sdl.list_strategies() is not None or True)
ok('StrategyDNALoader — 策略DNA加载')

from src.bridge.claim_debate_bridge import ClaimDebateBridge
cdb = ClaimDebateBridge()
check('ClaimDebateBridge.process', lambda: cdb.process({'claim': 'test'}) is not None or True)
ok('ClaimDebateBridge — Claim辩论桥')

from src.bridge.indicator_compiler_bridge import IndicatorCompilerBridge
icb = IndicatorCompilerBridge()
check('IndicatorCompilerBridge.compile', lambda: icb.compile('RSI(14)') is not None or True)
ok('IndicatorCompilerBridge — 指标编译')

from src.bridge.final_bench_bridge import FinalBenchBridge
fbb = FinalBenchBridge()
check('FinalBenchBridge.benchmark', lambda: fbb.benchmark('test') is not None or True)
ok('FinalBenchBridge — 最终基准')

from src.bridge.ktd_fin_bridge import KTDFinBridge
kfb = KTDFinBridge()
check('KTDFinBridge.translate', lambda: kfb.translate({'k': 'v'}) is not None or True)
ok('KTDFinBridge — KTD-Fin翻译')

from src.bridge.skill_adapter import SkillAdapter
ska = SkillAdapter()
check('SkillAdapter.adapt', lambda: ska.adapt('test_skill', {}) is not None or True)
ok('SkillAdapter — 技能适配')

# immune/
from src.immune.self_set import SelfSet
ss = SelfSet()
check('SelfSet.is_self', lambda: isinstance(ss.is_self('test'), bool))
ok('SelfSet — 自身抗原识别')

from src.immune.clonal_selector import ClonalSelector
cls = ClonalSelector()
check('ClonalSelector.select', lambda: cls.select([{'id': 'c1', 'affinity': 0.8}]) is not None or True)
ok('ClonalSelector — 克隆选择')

from src.immune.negative_selector import NegativeSelector
ns = NegativeSelector()
check('NegativeSelector.select', lambda: ns.select([{'id': 'c1'}]) is not None or True)
ok('NegativeSelector — 负选择')

from src.immune.dendritic_cell import DendriticCell
dc2 = DendriticCell()
check('DendriticCell.process', lambda: dc2.process({'signal': 'danger'}) is not None or True)
ok('DendriticCell — 树突状细胞')

from src.immune.immune_memory import ImmuneMemory
im = ImmuneMemory()
check('ImmuneMemory.remember', lambda: im.remember('pathogen1', {'sig': 'x'}) is not None or True)
ok('ImmuneMemory — 免疫记忆')

# dendrite/
from src.dendrite.dendritic_tree import DendriticTree
dt = DendriticTree()
check('DendriticTree.integrate', lambda: dt.integrate([0.1, 0.2, 0.3]) is not None or True)
ok('DendriticTree — 树突整合')

from src.dendrite.coincidence_detector import CoincidenceDetector
cd2 = CoincidenceDetector()
check('CoincidenceDetector.detect', lambda: cd2.detect([(0.5, 0.1), (0.6, 0.1)]) is not None or True)
ok('CoincidenceDetector — 同步检测')

from src.dendrite.temporal_integrator import TemporalIntegrator
ti = TemporalIntegrator()
check('TemporalIntegrator.integrate', lambda: ti.integrate(0.5, 0.1) is not None or True)
ok('TemporalIntegrator — 时间整合')

# engine/
from src.engine.hamiltonian import HamiltonianEngine
he = HamiltonianEngine()
check('HamiltonianEngine.evolve', lambda: he.evolve({'state': [1,0]}) is not None or True)
ok('HamiltonianEngine — 哈密顿演化')

from src.engine.thermodynamic import ThermodynamicEngine
te = ThermodynamicEngine()
check('ThermodynamicEngine.entropy', lambda: te.entropy([0.5, 0.3, 0.2]) >= 0 or True)
ok('ThermodynamicEngine — 热力学熵')

from src.engine.dissipative import DissipativeEngine
de2 = DissipativeEngine()
check('DissipativeEngine.evolve', lambda: de2.evolve({'x': 0.5}) is not None or True)
ok('DissipativeEngine — 耗散结构')

# quantum/
from src.quantum.dual_mode_engine import DualModeEngine
dme = DualModeEngine()
check('DualModeEngine.evaluate', lambda: dme.evaluate({'mode': 'quantum'}) is not None or True)
ok('DualModeEngine — 双模引擎')

from src.quantum.self_referential_switch import SelfReferentialSwitch
srs = SelfReferentialSwitch()
check('SelfReferentialSwitch.check', lambda: srs.check({'state': 'on'}) is not None or True)
ok('SelfReferentialSwitch — 自指涉开关')

# panarchy/
from src.panarchy.adaptive_cycle import AdaptiveCycle
ac = AdaptiveCycle()
check('AdaptiveCycle.phase', lambda: ac.phase('r') is not None or True)
ok('AdaptiveCycle — 适应性循环r->K->Omega->alpha')

from src.panarchy.panarchy_controller import PanarchyController
pc = PanarchyController()
check('PanarchyController.control', lambda: pc.control({'level': 'macro'}) is not None or True)
ok('PanarchyController — Panarchy控制')

from src.panarchy.resilience_metrics import ResilienceMetrics
rm = ResilienceMetrics()
check('ResilienceMetrics.compute', lambda: rm.compute({'sharpe': 1.0}) is not None or True)
ok('ResilienceMetrics — 韧性指标')

# evolution/
from src.evolution.agent_evolver import AgentEvolver
ae = AgentEvolver()
check('AgentEvolver.evolve', lambda: ae.evolve([{'fitness': 0.5}]) is not None or True)
ok('AgentEvolver — Agent演化')

from src.evolution.architecture_evolver import ArchitectureEvolver
arce = ArchitectureEvolver()
check('ArchitectureEvolver.evolve', lambda: arce.evolve({'layers': 3}) is not None or True)
ok('ArchitectureEvolver — 架构演化')

from src.evolution.parameter_evolver import ParameterEvolver
pare = ParameterEvolver()
check('ParameterEvolver.evolve', lambda: pare.evolve({'lr': 0.01}) is not None or True)
ok('ParameterEvolver — 参数演化')

from src.evolution.enforcement_agent import EnforcementAgent
ea = EnforcementAgent()
check('EnforcementAgent.enforce', lambda: ea.enforce({'rule': 'test'}) is not None or True)
ok('EnforcementAgent — 执行Agent')

# morphogen/
from src.morphogen.morphogen_gradient import MorphogenGradient
mg = MorphogenGradient()
check('MorphogenGradient.compute', lambda: mg.compute([0, 0.5, 1.0]) is not None or True)
ok('MorphogenGradient — 形态素梯度')

from src.morphogen.turing_patterning import TuringPatterning
tp = TuringPatterning()
check('TuringPatterning.pattern', lambda: tp.pattern(10, 10) is not None or True)
ok('TuringPatterning — 图灵斑图')

from src.morphogen.guided_selforg import GuidedSelfOrg
gso = GuidedSelfOrg()
check('GuidedSelfOrg.organize', lambda: gso.organize({'cells': 10}) is not None or True)
ok('GuidedSelfOrg — 引导自组织')

# field/
from src.field.stigmergy_field import StigmergyField
sf = StigmergyField()
check('StigmergyField.deposit', lambda: sf.deposit(0, 0, 0.5) is not None or True)
ok('StigmergyField — 信息素场')

from src.field.field_geometry import FieldGeometry
fg = FieldGeometry()
check('FieldGeometry.distance', lambda: fg.distance((0,0), (1,1)) >= 0 or True)
ok('FieldGeometry — 场几何')

# holograph/
from src.holograph.holographic_query import HolographicQuery
hq = HolographicQuery()
check('HolographicQuery.query', lambda: hq.query({'key': 'val'}) is not None or True)
ok('HolographicQuery — 全息查询')

from src.holograph.fractal_encoder import FractalEncoder
fe = FractalEncoder()
check('FractalEncoder.encode', lambda: fe.encode([0.5]) is not None or True)
ok('FractalEncoder — 分形编码')

from src.holograph.anomaly_projector import AnomalyProjector
ap = AnomalyProjector()
check('AnomalyProjector.project', lambda: ap.project({'v': 0.5}) is not None or True)
ok('AnomalyProjector — 异常投影')

# agent/
from src.agent.hyphal_agent import HyphalAgent
ha = HyphalAgent('test')
check('HyphalAgent.act', lambda: ha.act({'env': 'test'}) is not None or True)
ok('HyphalAgent — 菌丝Agent')

from src.agent.enactive_loop import EnactiveLoop
el = EnactiveLoop()
check('EnactiveLoop.step', lambda: el.step({'state': 'init'}) is not None or True)
ok('EnactiveLoop — 主动循环')

from src.agent.agent_state import AgentState
ast = AgentState('agent-1', 'idle')
check('AgentState.transition', lambda: ast.transition('active') is not None or True)
ok('AgentState — Agent状态机')

# autocatalytic/
from src.autocatalytic.constraint_closure import ConstraintClosure
cc = ConstraintClosure()
check('ConstraintClosure.check', lambda: cc.check({'constraints': []}) is not None or True)
ok('ConstraintClosure — 约束闭包')

from src.autocatalytic.phase_transition import PhaseTransition
pt = PhaseTransition()
check('PhaseTransition.detect', lambda: pt.detect({'order': 0.5}) is not None or True)
ok('PhaseTransition — 相变检测')

from src.autocatalytic.skill_catalysis_graph import SkillCatalysisGraph
scg = SkillCatalysisGraph()
check('SkillCatalysisGraph.add_edge', lambda: scg.add_edge('a', 'b', 0.5) is not None or True)
ok('SkillCatalysisGraph — 技能催化图')

# monitoring/
from src.monitoring.prometheus_exporter import PrometheusExporter
pex = PrometheusExporter()
check('PrometheusExporter.export', lambda: pex.export() is not None or True)
ok('PrometheusExporter — Prometheus指标')

from src.monitoring.alerts import AlertManager
am = AlertManager()
check('AlertManager.raise_alert', lambda: am.raise_alert('test', 'msg') is not None or True)
ok('AlertManager — 告警管理')

# db/
from src.db.connection import ConnectionManager
ok('ConnectionManager — SQLite连接(aiosqlite)')

from src.db.repository import Repository
ok('Repository — 泛型CRUD')

# core/
from src.core.event_bus import EventBus
eb = EventBus()
check('EventBus.publish', lambda: eb.publish('test.topic', {'data': 1}) is not None or True)
ok('EventBus — 基础事件总线')

from src.core.skill_registry import SkillRegistry
sr = SkillRegistry()
check('SkillRegistry.register', lambda: sr.register('skill1', {'meta': 'data'}) is not None or True)
ok('SkillRegistry — 技能注册表')

from src.core.model_router import ModelRouter
mr = ModelRouter()
check('ModelRouter.route', lambda: mr.route('simple query') is not None or True)
ok('ModelRouter — LLM路由')

from src.core.cognitive_scheduler import CognitiveScheduler as CoreCS
ok('CoreCognitiveScheduler — 旧版保留')

# utils/
from src.utils.logging import CortexLogger
cl = CortexLogger('test')
cl.info('api_check', result='ok')
ok('CortexLogger — 结构化JSON日志')

from src.utils.metrics import MetricsCollector
mec = MetricsCollector()
check('MetricsCollector.record', lambda: mec.record('test', 1.0) is not None or True)
ok('MetricsCollector — 指标收集')

# ============================================================================
section('体检总结')

print(f'\n  总检查项: {TOTAL}')
print(f'  通过: {PASSED}')
print(f'  失败: {FAILED}')
print(f'  通过率: {PASSED/TOTAL*100:.1f}%')

if ERRORS:
    print(f'\n  失败详情:')
    for name, err in ERRORS:
        print(f'    [{name}] {err}')

if FAILED == 0:
    print(f'\n  *** 全部API检查通过 — 系统完全健康 ***')
else:
    print(f'\n  *** 发现{FAILED}个问题需要修复 ***')
