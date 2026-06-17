# Fungal Cortex v2.0 → v3.0 Migration Guide

> **如同手术方案——每一步都有明确的切口、缝合和愈合标准**

## 概述

v3.0 将 Fungal Cortex 从仅拥有 L6"大脑皮层"的状态，补齐为拥有完整 L0-L7 生命体架构。

### v2.0 (旧)
```
L6 (Meta-Cognition) + 部分 L7 (Execution)
+ 基础 bridge/ + immune/ + field/ + holograph/
= 87 .py 文件
```

### v3.0 (新)
```
L0 (周围神经+内分泌) → adaptive/ (18类)
L3 (免疫辩论引擎) → adaptive/ (3类)
L4 (脊髓+脑干中台) → autonomous/ (15+2类)
L5 (共生生态集群) → cluster/ (8+1+1类)
Phase 5 (跨层桥梁) → 5座桥梁 (4包)
Phase 6 (涌现+自愈) → core/ (3类)
Phase 7 (性能+安全) → security/ + 增强 (6类)
= ~96 .py 文件, ~31,800 行
```

## 新增包结构

```
src/
├── adaptive/          # L0+L3 (原有基础上大幅扩展)
│   ├── hmm_detector.py, cusum_detector.py, gthnet_detector.py  [新]
│   ├── drift_detector.py, regime_orchestrator.py               [新]
│   ├── hypernetwork.py, strategy_adapter.py, ...               [新]
│   ├── market_of_claims.py, immune_validator.py, ...           [新]
│   └── debate_adaptive_bridge.py                               [Phase 5]
├── autonomous/        # L4 [全新包]
│   ├── intent_parser.py, task_dag.py, conflict_detector.py     [M1]
│   ├── transaction_manager.py, circuit_breaker_bridge.py       [M2]
│   ├── audit_trail.py, causal_tracer.py, counterfactual.py     [M3]
│   ├── online_evolution.py, strategy_validator.py              [M4]
│   ├── vector_retrieval.py, financial_kg.py, memory_weaving.py [M5]
│   ├── policy_engine.py, behavior_monitor.py                   [M6]
│   ├── immune_audit_bridge.py                                  [Phase 5]
│   └── dag_cluster_bridge.py                                   [Phase 5]
├── cluster/            # L5 [全新包]
│   ├── agent_factory.py, communicator.py, pool_manager.py
│   ├── endogenous_engine.py, consensus.py
│   ├── knowledge_network.py, distributed_evolution.py
│   ├── global_audit.py
│   └── feedback_adaptive_bridge.py                             [Phase 5]
├── core/               # 事件总线+涌现+自愈 [大幅扩展]
│   ├── unified_event_bus.py                                    [Phase 5]
│   ├── cross_layer_emergence.py                                [Phase 6]
│   ├── self_healing.py                                         [Phase 6]
│   └── autonomous_governance.py                                [Phase 6]
├── security/           # [全新包]
│   ├── jwt_auth.py                                             [Phase 7]
│   ├── rate_limiter.py                                         [Phase 7]
│   └── sandbox_hardening.py                                    [Phase 7]
└── utils/
    └── serialization.py                                        [Phase 7]
```

## 迁移检查清单

### 1. 导入路径变更

| v2.0 路径 | v3.0 路径 |
|----------|----------|
| `from src.bridge.l0_l7_pipeline import` | 无直接替代 — 由 UnifiedEventBus 替代 |
| `from src.core.event_bus import EventBus` | `from src.core import EventBus` 或 `UnifiedEventBus` |
| 无对应 | `from src.adaptive import BayesianRegimeOrchestrator` |
| 无对应 | `from src.autonomous import IntentParser, TaskDAGBuilder` |
| 无对应 | `from src.cluster import AgentFactory, ClusterCommunicator` |
| 无对应 | `from src.security import JWTAuthManager, RateLimiter` |

### 2. 新全局事件类型

```python
# v2.0: topic strings were free-form
await event_bus.publish_nowait("l6.scan.complete", data)

# v3.0: StandardEventType enum
from src.core.unified_event_bus import StandardEventType
await bus.publish_quick(StandardEventType.REGIME_CHANGE.value, data)
```

### 3. 确定性Hash

```python
# v2.0: 使用 Python uuid.uuid4() (非确定性)
import uuid
record_id = str(uuid.uuid4())

# v3.0: 使用 hashlib.md5 (确定性, 可重现)
import hashlib
record_id = hashlib.md5(f"{prefix}|{time.time()}".encode()).hexdigest()[:16]
```

### 4. 日志

```python
# v2.0: print() or logging
print(f"Event happened: {event}")

# v3.0: CortexLogger (结构化JSON)
from src.utils.logging import CortexLogger
self._logger = CortexLogger("module_name")
self._logger.info("event_happened", key=value)
```

### 5. 跨层通信

```python
# v2.0: 直接调用其他层的方法 (紧耦合)

# v3.0: 通过 UnifiedEventBus (松耦合)
from src.core.unified_event_bus import UnifiedEventBus
bus = UnifiedEventBus()
await bus.publish_regime_change("equilibrium", "bear", 0.85)
```

### 6. 自愈能力

```python
# v2.0: 无自愈能力

# v3.0: SelfHealingOrchestrator 4阶段自愈
from src.core.self_healing import SelfHealingOrchestrator
sho = SelfHealingOrchestrator()
wound = sho.report_health("L5", "agent_pool", 0.5, 3, 3)
cycle = sho.auto_heal(wound.wound_id)
```

### 7. 治理

```python
# v2.0: 直接修改参数

# v3.0: 5道关卡审查
from src.core.autonomous_governance import AutonomousGovernance, ChangeType
ag = AutonomousGovernance()
prop = ag.submit_proposal(ChangeType.PARAMETER_UPDATE, "param", new_val, old_val)
dec = ag.review(prop.proposal_id, gate_inputs)
```

### 8. 安全

```python
# v2.0: 无认证层

# v3.0: JWT token认证
from src.security.jwt_auth import JWTAuthManager
jwt = JWTAuthManager()
pair = jwt.create_token_pair("agent-1", ["read", "trade"])
claims = jwt.verify_token(pair.access_token)
```

## 架构优势

| 维度 | v2.0 | v3.0 |
|------|------|------|
| 层级覆盖 | L6+L7 | L0-L7完整生命体 |
| 模块数量 | 87 | ~96 |
| 生物隐喻 | 部分 | 42个明确隐喻 |
| 跨层通信 | 直接调用 | 5座桥梁+UnifiedEventBus |
| 自愈能力 | 无 | 4阶段伤口愈合 |
| 治理 | 无 | 5道关卡 |
| 安全 | 基础 | JWT+RateLimit+Sandbox+Merkle |
| 性能 | 标准 | TorchScript+ZeroMQ+msgpack |

## 向后兼容

v3.0 保持对 v2.0 核心模块的向后兼容:
- `src/l6/` 所有模块不变
- `src/trading/` 所有模块不变
- `src/bridge/` 保留原有桥梁(新桥在各自包内)
- `src/core/event_bus.py` 保留(`UnifiedEventBus` 是增强版)
- `src/core/skill_registry.py` 保留
