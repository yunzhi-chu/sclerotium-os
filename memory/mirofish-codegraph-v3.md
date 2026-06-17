# MiroFish 完整代码图谱 v3.0

> **日期**: 2026-06-16
> **版本**: v3.0 — 基于最新 codegraph 索引 (2,388 nodes · 5,786 edges · 102 files · 5.51 MB)
> **前版**: [[mirofish-codegraph-v2]] (v2.0)

---

## 0. 系统概览

| 指标 | v2.0 | v3.0 | 变化 |
|:-----|:-----|:-----|:-----|
| 总文件 | 102 | 102 | 持平 |
| Python 文件 | 75 | 75 | 持平 |
| Vue 组件 | 16 | 16 | 持平 |
| JS 文件 | 9 | 9 | 持平 |
| 节点数 | 2,388 | 2,388 | 持平 |
| 边数 | 5,786 | 5,786 | 持平 |
| 数据库大小 | 5.51 MB | 5.51 MB | 持平 |
| 6D FCPI → 8D Genome | 6D only | 8D bridge | 新增 full_body_genome.py |

### 节点分布
| 类型 | 数量 |
|:-----|:-----|
| method | 605 |
| import | 550 |
| function | 405 |
| variable | 264 |
| constant | 252 |
| class | 136 |
| route | 60 |
| component | 16 |

---

## 1. 顶层架构

```
MiroFish-main/
├── backend/
│   ├── run.py                          ← FastAPI 入口 (uvicorn)
│   ├── app/
│   │   ├── api/                        ← REST API 层
│   │   │   ├── graph.py               — Agent 图构建 API
│   │   │   ├── report.py              — 进化报告生成 API
│   │   │   └── simulation.py          — 仿真控制 API (启动/停止/状态)
│   │   ├── models/                    ← 数据模型
│   │   │   ├── config.py              — 配置模型
│   │   │   ├── project.py             — 项目模型
│   │   │   └── task.py                — 任务模型
│   │   ├── services/                  ← 核心服务层
│   │   │   ├── arenas/                — 六维竞技场
│   │   │   │   ├── arena_base.py      — 竞技场基类 (ArenaConfig + ArenaResult)
│   │   │   │   ├── coding_arena.py    — 编程能力竞技场
│   │   │   │   ├── coordination_arena.py — 协作能力竞技场
│   │   │   │   ├── decision_arena.py  — 决策能力竞技场
│   │   │   │   ├── emergence_arena.py — 涌现行为竞技场
│   │   │   │   ├── performance_arena.py — 性能表现竞技场
│   │   │   │   └── safety_arena.py    — 安全合规竞技场
│   │   │   ├── evolution_generation_manager.py — 进化代际管理器 (核心)
│   │   │   ├── fitness_extractor.py   — FCPI 适应度提取器
│   │   │   ├── full_body_genome.py    — 8D 全身体基因组 (NEW)
│   │   │   ├── live_simulation_engine.py — 实时仿真引擎
│   │   │   ├── simulation_runner.py   — 仿真执行器
│   │   │   ├── simulation_manager.py  — 仿真生命周期管理
│   │   │   ├── simulation_config_generator.py — 仿真配置生成
│   │   │   ├── simulation_ipc.py      — 进程间通信
│   │   │   ├── oasis_bridge.py        — OASIS 平台桥接
│   │   │   ├── oasis_profile_generator.py — OASIS Agent Profile 生成
│   │   │   ├── mycelium_bridge.py     — Mycelium 网络桥接
│   │   │   ├── dgm_bridge.py          — DGM 进化桥接
│   │   │   ├── graph_builder.py       — Agent 关系图构建
│   │   │   ├── report_agent.py        — 智能报告 Agent
│   │   │   ├── ontology_generator.py  — 本体论生成器
│   │   │   ├── zep_tools.py           — Zep 记忆工具
│   │   │   ├── zep_entity_reader.py   — Zep 实体读取
│   │   │   ├── zep_graph_memory_updater.py — Zep 图记忆更新
│   │   │   ├── text_processor.py      — 文本处理
│   │   │   └── models/task.py         — 任务模型
│   │   └── utils/                     ← 工具层
│   │       ├── llm_client.py          — LLM 客户端
│   │       ├── config.py              — 配置工具
│   │       ├── file_parser.py         — 文件解析
│   │       ├── logger.py              — 日志工具
│   │       ├── locale.py              — 国际化
│   │       └── retry.py               — 重试逻辑
│   ├── scripts/                       ← 执行脚本
│   │   ├── run_parallel_simulation.py — 双平台并行仿真 (Twitter+Reddit)
│   │   ├── run_reddit_simulation.py   — Reddit 单平台仿真
│   │   ├── run_twitter_simulation.py  — Twitter 单平台仿真
│   │   ├── evolve.py                  — 批量进化运行
│   │   ├── diagnose.py                — 系统诊断
│   │   └── action_logger.py           — 动作日志
│   └── tests/                         ← 测试
│       ├── test_evolution_engine.py   — 进化引擎测试
│       ├── test_arena_base.py         — 竞技场基类测试
│       ├── test_full_integration.py   — 全系统集成测试
│       └── run_10gen_evolution.py     — 10代进化运行测试
│
├── frontend/                          ← Vue 3 前端
│   └── src/
│       ├── App.vue                    — 根组件
│       ├── main.js                    — 入口
│       ├── router/index.js            — 路由
│       ├── i18n/index.js              — 国际化
│       ├── api/                       — API 层
│       │   ├── index.js               — API 入口
│       │   ├── graph.js               — 图 API
│       │   ├── report.js              — 报告 API
│       │   └── simulation.js          — 仿真 API
│       ├── views/                     — 页面视图
│       │   ├── Home.vue               — 首页
│       │   ├── Process.vue            — 流程页 (5步骤)
│       │   ├── SimulationView.vue     — 仿真配置页
│       │   ├── SimulationRunView.vue  — 仿真运行页
│       │   ├── ReportView.vue         — 报告查看页
│       │   ├── InteractionView.vue    — 交互页
│       │   └── MainView.vue           — 主视图
│       ├── components/                — 组件
│       │   ├── Step1GraphBuild.vue    — 步骤1: 图构建
│       │   ├── Step2EnvSetup.vue      — 步骤2: 环境设置
│       │   ├── Step3Simulation.vue    — 步骤3: 仿真运行
│       │   ├── Step4Report.vue        — 步骤4: 报告生成
│       │   ├── Step5Interaction.vue   — 步骤5: 交互
│       │   ├── GraphPanel.vue         — 图面板
│       │   ├── HistoryDatabase.vue    — 历史数据库
│       │   └── LanguageSwitcher.vue   — 语言切换
│       └── store/
│           └── pendingUpload.js       — 上传队列状态
│
└── docker-compose.yml                 — 容器编排
```

---

## 2. 六维 FCPI 竞技场 (核心进化引擎)

### 2.1 FCPI 维度

| 维度 | 竞技场 | 含义 | 平台 | Agent 类型 |
|:-----|:------|:-----|:-----|:----------|
| **C**oding | CodingArena | 编程/代码生成能力 | 自定义 (代码生成/审查) | DeveloperAgent, ReviewerAgent |
| **C**oordination | CoordinationArena | 多Agent协作/任务分配 | Reddit | Coordinator, Worker |
| **S**afety | SafetyArena | 安全合规/风险规避 | Reddit | SafetyAuditor, CompliantAgent |
| **D**ecision | DecisionArena | 决策质量/经济理性 | Twitter | Investor, Analyst |
| **E**mergence | EmergenceArena | 涌现行为/创新 | Reddit | CreativeAgent, Curator |
| **P**erformance | PerformanceArena | 效率/资源优化 | 自定义 | Optimizer, Benchmarker |

### 2.2 竞技场基类架构

```python
@dataclass(frozen=True)
class ArenaConfig:
    arena_id: str              # 竞技场唯一标识
    dimension: FCPIDimension   # FCPI 维度
    max_rounds: int = 20       # 最大仿真轮次
    min_agents: int = 5        # 最少Agent数
    max_agents: int = 50       # 最多Agent数
    platform_types: tuple = ("reddit",)  # OASIS 平台
    llm_model: str = "deepseek-v4-flash"
    temperature: float = 0.7
    confidence_threshold: float = 0.6

@dataclass(frozen=True)
class ArenaResult:
    fitness_vector: FitnessVector | None  # 适应度向量
    generation: int                       # 代数
    duration_seconds: float               # 耗时
    agent_count: int                      # Agent数
    total_actions: int                    # 总动作数
    emergent_patterns: tuple[str, ...]    # 涌现模式
    success: bool = True
```

### 2.3 六个竞技场具体实现

```
CodingArena      — 编程任务生成→Agent解答→测试验证→评分
CoordinationArena — 任务分解→分配→协作执行→完成度评估
SafetyArena       — 注入安全风险→Agent检测→规避率统计
DecisionArena     — 经济博弈→Agent决策→收益/损失分析
EmergenceArena    — 开放场景→自由交互→涌现模式检测
PerformanceArena  — 基准测试→资源监控→效率评分
```

---

## 3. 进化代际管理器 (EvolutionGenerationManager)

```
进化状态机:
  PENDING → INITIALIZING → RUNNING_ARENAS → AGGREGATING_FITNESS
    → SELECTING → MUTATING → CRYSTALLIZING → PENDING (循环)
    → COMPLETE (终止)

Panarchy 自适应循环:
  α (重组) → r (增长) → K (保守) → Ω (释放/灭绝) → α ...

run_generation() 流程:
  1. 选择活跃基因组 (_select_active_genomes)
  2. 并行/串行运行六竞技场 (每个竞技场 = LLM驱动的多Agent仿真)
  3. 聚合 FCPI 适应度 (_aggregate_fcpi):
     FCPI_total = Σ(w_dim × fitness_dim.primary_score)
  4. 元学习调整 FCPI 权重 (_meta_learn_weights)
  5. 排名+选择 (_rank_genomes + _apply_selection):
     - 精英保留 (elitism_count)
     - 多样性奖励 (_compute_diversity_bonus)
     - 温和淘汰 (底部10%)
     - 移民注入 (新基因组)
  6. Panarchy 相变检查 (_update_panarchy_phase)
  7. 涌现结晶化 (_crystallize_patterns)
  8. 保存快照 (_save_snapshot)
```

---

## 4. 8D FullBodyGenome (与 Sclerotium 对齐)

```python
# backend/app/services/full_body_genome.py
class FullBodyGenome:
    """8 维全身体基因组 — 与 Sclerotium OS 对齐"""
    
    8 维度:
      tools        — 工具使用能力
      prompts      — 提示词效能
      personalities — 人格适配
      memories     — 记忆质量
      providers    — 模型提供商选择
      skills       — 技能掌握
      organs       — 器官激活
      arbiters     — 仲裁判断
    
    # 桥接到 Sclerotium 的 evolution/full_body_genome.py
```

---

## 5. 仿真引擎

### 5.1 OASIS 双平台

```
run_parallel_simulation.py
  ├─ Twitter 仿真 (OASIS Twitter Platform)
  │   ├─ Agent 从 CSV profiles 创建
  │   ├─ LLMAction() 驱动行为
  │   ├─ 72小时仿真 (30分钟/轮)
  │   └─ SQLite 动作日志
  │
  └─ Reddit 仿真 (OASIS Reddit Platform)
      ├─ Agent 从 JSON profiles 创建
      ├─ LLMAction() 驱动行为
      ├─ 72小时仿真 (30分钟/轮)
      └─ SQLite 动作日志
```

### 5.2 实时仿真引擎

```python
# backend/app/services/live_simulation_engine.py
class LiveSimulationEngine:
    """实时 LLM 驱动的 Agent 仿真"""
    
    - 种群管理 (避免崩溃)
    - 多样性维护
    - 实时 FCPI 评分
    - 涌现模式检测
```

---

## 6. API 层

```
FastAPI 端点 (backend/run.py):

  /api/graph/build          — 构建 Agent 关系图
  /api/graph/status         — 图构建状态
  
  /api/simulation/start     — 启动仿真
  /api/simulation/stop      — 停止仿真
  /api/simulation/status    — 仿真状态
  /api/simulation/config    — 仿真配置
  
  /api/report/generate      — 生成进化报告
  /api/report/status        — 报告状态
  /api/report/history       — 历史报告
```

---

## 7. 前端 5 步骤流程

```
Step 1: GraphBuild     — 上传 Profile → 构建 Agent 关系图
Step 2: EnvSetup       — 配置 OASIS 环境 (平台/时间/事件)
Step 3: Simulation     — 启动仿真 → 实时监控
Step 4: Report         — 生成 FCPI 进化报告
Step 5: Interaction    — 与仿真结果交互/查询
```

---

## 8. 与 Sclerotium OS 桥接

```
Sclerotium OS (bridges/mirofish_bridge.py)
  → MiroFishBridge
    ├─ 加载 6 竞技场配置
    ├─ 加载 EvolutionGenerationManager
    ├─ 加载 FullBodyGenome (8D)
    ├─ 加载 FitnessExtractor (FCPI 向量)
    └─ 暴露为 MCP 工具 (evolution/gene/fitness)

Sclerotium OS 使用 MiroFish:
  - 进化评估: 每次 evolution_loop 可触发 MiroFish 仿真评估
  - FCPI 向量: MiroFish 的六维适应度作为 Sclerotium 进化参考
  - 8D 对齐: 两系统都使用 FullBodyGenome 8D
```

---

## 9. 关键数据流

```
用户上传 Profile (CSV/JSON)
  → GraphBuilder → Agent 关系图
  → SimulationConfigGenerator → 仿真配置
  → SimulationRunner → OASIS 环境启动
  → LiveSimulationEngine → Agent 执行 LLMAction
  → 动作日志 (SQLite)
  → FitnessExtractor → FCPI 向量提取
  → EvolutionGenerationManager.run_generation()
    → 六竞技场评估
    → FCPI 聚合 (加权总和)
    → 选择/淘汰/变异
    → Panarchy 相变
    → 涌现结晶化
    → 快照保存
  → ReportAgent → 进化报告生成
  → 前端可视化 (Vue 3)
```

---

## 10. 与 Sclerotium OS 进化引擎的差异

| 特性 | MiroFish | Sclerotium OS |
|:-----|:---------|:-------------|
| 评估方式 | LLM 多 Agent 仿真 (Twitter/Reddit) | 真实工具调用反馈 (用进废退) |
| 适应度来源 | 仿真中 Agent 行为评分 | 每次工具执行 success/failure |
| 竞技场 | 6 个独立竞技场 | 8 维基因组权重 |
| 时间尺度 | 小时级 (72h 仿真) | 分钟级 (每5分钟一代) |
| 规模 | 5-50 Agent 并行 | 单体生命体实时进化 |
| Panarchy | ✅ α→r→K→Ω 循环 | ❌ 简单优胜劣汰 |

---

## 11. 测试覆盖

| 测试文件 | 覆盖领域 |
|:---------|:---------|
| `test_evolution_engine.py` (70 tests) | 进化状态机/选择/变异/聚合/Panarchy |
| `test_arena_base.py` (34 tests) | 竞技场配置/运行/结果 |
| `test_full_integration.py` (49 tests) | E2E: Profile→图→仿真→报告 |
| `run_10gen_evolution.py` (31 tests) | 10代进化压力测试 |

---

## 12. 版本变化 (v2.0 → v3.0)

| 变化 | 详情 |
|:-----|:-----|
| **8D FullBodyGenome** | 新增 `full_body_genome.py` — 从 6D FCPI 扩展到 8D |
| **Sclerotium 对齐** | 两系统统一使用 8D FullBodyGenome 维度定义 |
| **桥接增强** | `bridges/mirofish_bridge.py` 增加 8D genome 支持 |
| **代码稳定性** | 索引节点/边数完全一致，无结构性变化 |

---

*由 CodeGraph MCP 索引生成 — 2026-06-16*
