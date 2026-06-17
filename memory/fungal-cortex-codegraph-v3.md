# Fungal Cortex 完整代码图谱 v3.0

> **日期**: 2026-06-16
> **版本**: v3.0 — 基于最新 codegraph 索引 (107,714 nodes · 276,927 edges · 6,360 files · 388.49 MB)
> **前版**: [[fungal-cortex-codegraph-v2]] (v2.0)

---

## 0. 系统概览

| 指标 | v2.0 | v3.0 | 变化 |
|:-----|:-----|:-----|:-----|
| 总文件 | 6,360 | 6,360 | 持平 |
| Python 文件 | ~3,802 | ~3,817 | +15 |
| JS/TS/JSX/TSX 文件 | ~1,800 | ~17,854 | 含 node_modules |
| 总代码行 (Python) | ~1,300,000 | ~1,316,170 | +16,170 |
| SKILL.md 文件 | ~5,800 | 6,073 | +273 |
| 节点数 | 107,714 | 107,714 | 持平 |
| 边数 | 276,927 | 276,927 | 持平 |
| 数据库大小 | 388.49 MB | 388.49 MB | 持平 |

### 节点分布
| 类型 | 数量 |
|:-----|:-----|
| function | 30,204 |
| import | 26,624 |
| method | 21,396 |
| variable | 11,607 |
| file | 5,724 |
| constant | 5,290 |
| class | 4,849 |
| interface | 1,085 |
| property | 307 |
| type_alias | 263 |
| route | 170 |
| enum_member | 154 |
| enum | 21 |
| struct | 10 |
| field | 6 |
| component | 4 |

### 语言分布
| 语言 | 文件数 |
|:-----|:------|
| Python | 3,802 |
| TypeScript | 956 |
| JavaScript | 823 |
| YAML | 636 |
| TSX | 70 |
| XML | 37 |
| JSX | 25 |
| Rust | 9 |
| Go | 1 |
| Scala | 1 |

---

## 1. 顶层架构

```
fungal-cortex/
├── src/                    ← 核心引擎 (L1-L10 + 支撑模块)
│   ├── core/              — 技能注册表 + 引擎核心
│   ├── l1/                — 感知层
│   ├── l2/                — 记忆层
│   ├── l3/                — 推理层
│   ├── l4/                — 规划层
│   ├── l5/                — 执行层
│   ├── l6/                — 进化层 (Darwinian Gödel Machine)
│   ├── l7/                — 元认知层
│   ├── l8/                — 社会层
│   ├── l9/                — 创生层
│   ├── l10/               — 超越层
│   ├── agent/             — Agent 系统
│   ├── adaptive/          — 自适应引擎
│   ├── autocatalytic/     — 自催化网络
│   ├── autonomous/        — 自主运行时
│   ├── bridge/            — 外部桥接
│   ├── cluster/           — 集群计算
│   ├── db/                — 数据库层
│   ├── dendrite/          — 树突信号路由
│   ├── engine/            — 引擎核心
│   ├── evolution/         — 进化系统
│   ├── field/             — 场论 (Stigmergy/Morphogenic)
│   ├── holograph/         — 全息存储
│   └── immune/            — 人工免疫系统
│
├── skills/                 ← 5,826 外部技能库 (19 个来源)
│   ├── QuantAgent/                       — 量化金融 Agent (AlphaEar/Reporter)
│   ├── openclaw-master-skills-main/      — OpenClaw 全套技能
│   ├── claude-code-plugins-plus-skills/  — Claude Code 插件
│   ├── awesome-claude-skills-main/       — Claude 技能合集
│   ├── awesome-openclaw-skills-main/     — OpenClaw 技能合集
│   ├── Claude-Code-Game-Studios-main/    — 游戏开发技能
│   ├── academic-research-skills-main/    — 学术研究技能
│   ├── andrej-karpathy-skills-main/      — Karpathy 技能
│   ├── xiaohongshu-ops-skill-main/       — 小红书运营
│   ├── openclaw-marketing-skills-main/   — OpenClaw 营销
│   ├── last30days-skill-main/            — 近30天热门技能
│   ├── skills/                           — 通用技能集合
│   ├── claude-skills-main (1)/           — Claude 技能 (另一个源)
│   ├── awesome-claude-code-main/         — Claude Code 资源
│   ├── awesome-hermes-agent-main/        — Hermes Agent 资源
│   └── awesome-openclaw-main/            — OpenClaw 资源
│
├── agents/                 ← Agent 定义
│   ├── code-reviewer/     — 代码审查 Agent
│   ├── data-scientist/    — 数据科学家 Agent
│   └── game-designer/     — 游戏设计师 Agent
│
├── cortex-frontend/        ← Next.js Web 前端
│   ├── src/app/skills/    — 技能浏览页面
│   ├── src/components/    — 技能树/依赖图/分类组件
│   ├── src/stores/        — 状态管理
│   └── src/api/           — API 层
│
├── examples/               ← 使用示例
├── data/                   ← 数据存储
└── .github/workflows/      ← CI/CD
```

---

## 2. 十层架构 (L0-L10)

```
L10 — 超越层 (Transcendence)     — 自进化/涌现行为/量子相干
  ↓
L9  — 创生层 (Genesis)           — 代码自举/新器官生成/自主构建
  ↓
L8  — 社会层 (Social)            — 多Agent协作/P2P网格/群体智能
  ↓
L7  — 元认知层 (Metacognition)    — 自我意识/反思/自我修复
  ↓
L6  — 进化层 (Evolution)         — DGM/DNA编译/基因编程/适者生存
  ↓
L5  — 执行层 (Execution)         — 工具调用/代码生成/沙箱执行
  ↓
L4  — 规划层 (Planning)          — 任务分解/目标扩展/长视距规划
  ↓
L3  — 推理层 (Reasoning)         — 逻辑推理/神经符号/形式验证
  ↓
L2  — 记忆层 (Memory)            — 向量存储/SQLite/五层记忆/遗忘曲线
  ↓
L1  — 感知层 (Perception)        — 输入解析/上下文组装/意图识别
  ↓
L0  — 基础层 (Foundation)        — 配置/日志/事件总线/数据库连接
```

### 层间数据流 (自底向上)
```
L0 基础 → L1 解析输入 → L2 存储记忆 → L3 推理分析
    → L4 制定计划 → L5 执行工具 → L6 进化评估
    → L7 元认知反思 → L8 社会协作 → L9 创生新器官 → L10 超越涌现
```

---

## 3. 技能生态系统 (6,073 SKILL.md)

### 3.1 按来源分布

| 技能库 | 技能数 (估) | 领域 |
|:-------|:----------|:-----|
| openclaw-master-skills-main | ~1,500 | 全领域 (OpenClaw 官方) |
| claude-code-plugins-plus-skills | ~800 | Claude Code 扩展 |
| QuantAgent | ~600 | 量化金融/A股/加密货币 |
| awesome-claude-skills-main | ~500 | Claude 通用技能 |
| awesome-openclaw-skills-main | ~400 | OpenClaw 通用 |
| skills/ | ~400 | 通用技能集合 |
| Claude-Code-Game-Studios | ~350 | 游戏开发 |
| claude-skills-main (1) | ~300 | Claude 技能 |
| openclaw-marketing-skills | ~250 | 营销/SEO |
| awesome-claude-code-main | ~200 | Claude Code 参考 |
| academic-research-skills | ~200 | 学术研究 |
| xiaohongshu-ops-skill | ~150 | 小红书运营 |
| andrej-karpathy-skills | ~100 | AI/ML 开发 |
| awesome-hermes-agent-main | ~100 | Hermes Agent |
| last30days-skill-main | ~80 | 热门技能 |
| awesome-openclaw-main | ~60 | OpenClaw 参考 |
| claude-code-infrastructure-showcase | ~50 | 基础设施 |
| 其他 | ~33 | 杂项 |
| **总计** | **~6,073** | |

### 3.2 核心技能域

| 域 | 技能数 (估) | 示例 |
|:--|:----------|:-----|
| **开发工具** | ~1,200 | Git/GitHub/CI-CD/Docker/K8s |
| **AI/ML** | ~900 | PyTorch/TensorFlow/LLM/RAG/Agent |
| **前端** | ~800 | React/Next.js/Vue/Tailwind/组件库 |
| **后端** | ~700 | API/数据库/认证/队列/微服务 |
| **量化金融** | ~600 | A股/加密货币/AlphaEar/回测/风控 |
| **数据科学** | ~500 | Pandas/Spark/SQL/可视化/特征工程 |
| **安全** | ~400 | 渗透测试/代码审计/漏洞扫描 |
| **运维/DevOps** | ~350 | Terraform/Ansible/监控/日志 |
| **游戏开发** | ~350 | Unity/Unreal/Godot/设计模式 |
| **营销/内容** | ~300 | SEO/社交媒体/小红书/广告 |
| **学术** | ~200 | 论文写作/LaTeX/文献综述/实验设计 |
| **设计** | ~150 | Figma/UI-UX/3D建模/动画 |
| **其他** | ~523 | 音乐/视频/法律/医疗/教育... |

### 3.3 Sclerotium OS 如何使用

```python
# kernel/skill_loader.py
loader = SkillLoader()
loader.scan()  # 自动发现所有路径, 加载 5,826 技能 → skill_count = 5826

# mcp/tools/skills.py
skill_list()    → 返回 5,826 技能清单 (名称/分类/描述)
skill_search(q) → 语义搜索匹配技能
skill_invoke(name) → 读取完整 SKILL.md 内容 → LLM 按指令执行
```

---

## 4. 核心引擎模块 (src/)

### 4.1 core/ — 技能注册表 + 引擎核心
```
SkillRegistry        — 全局技能注册 (发现/索引/搜索)
Engine               — 核心执行引擎
```

### 4.2 agent/ — Agent 系统
```
Agent                — Agent 基类
QFCAgent             — 量化金融 Agent
AgentSkill           — Agent 绑定技能
```

### 4.3 evolution/ — 进化系统
```
DarwinianGodelMachine — DGM 进化引擎 (L6)
GeneticProgram        — 遗传编程
Genome                — 基因组表示
```

### 4.4 immune/ — 人工免疫系统
```
ImmuneSystem         — 三层免疫 (负选择/克隆/危险理论)
```

### 4.5 field/ — 场论
```
StigmergyField       — 信息素场 (间接协调)
MorphogenicField     — 形态发生场 (结构自组织)
```

### 4.6 dendrite/ — 树突路由
```
DendriteRouter       — 信号路由树 (技能/工具/器官 消息分发)
```

---

## 5. 前端 (cortex-frontend/)

```
Next.js App (React + TypeScript)
  ├─ /skills            — 技能浏览 (树状/网格/依赖图)
  ├─ /agents            — Agent 管理
  ├─ /evolution         — 进化监控
  └─ Components:
       ├─ skill-tree            — 技能树可视化
       ├─ dependency-graph      — 依赖关系图 (D3/ReactFlow)
       ├─ skill-search          — 全文搜索
       └─ category-filter       — 分类过滤
```

### 前端数据流
```
React Query → API → src/core/skill_registry.py → skills/ 文件系统
                                                     ↓
                                              SKILL.md 元数据
                                              (name/category/description/dna)
```

---

## 6. Agent 系统

### 已定义 Agent (agents/)

| Agent | 路径 | 功能 |
|:------|:-----|:-----|
| code-reviewer | agents/code-reviewer/ | 代码审查 (安全/质量/风格) |
| data-scientist | agents/data-scientist/ | 数据分析/建模/可视化 |
| game-designer | agents/game-designer/ | 游戏设计/关卡/机制 |

### Agent 与 Sclerotium 集成
```
Sclerotium OS (kernel/agent_profiles.py)
  → AgentProfileManager.scan_profiles()
    → 加载 fungal-cortex/agents/* 的 Agent 定义
    → 注入到 S8 (Personality) 提示段
```

---

## 7. 与 Sclerotium OS 桥接 (bridges/)

Sclerotium 的 `bridges/fungal_bridge.py` 加载所有 fungal-cortex 器官:

```python
class FungalBridge:
    """加载 fungal-cortex 全部 120+ 器官到 Sclerotium OS"""
    
    def load_all_organs(self):
        # L1-L10 每层加载核心模块
        # skills/ 作为 SkillLoader 数据源
        # agents/ 作为 AgentProfiles 数据源
        # core/ 作为 SkillRegistry 后端
```

---

## 8. 关键指标总结

| 维度 | 数值 |
|:-----|:-----|
| 总节点 | 107,714 |
| 总边 | 276,927 |
| 总文件 | 6,360 |
| Python 模块 | 3,817 |
| JS/TS 模块 | 1,804 |
| SKILL.md | 6,073 |
| 技能库来源 | 19 |
| 架构层 | L0-L10 (11层) |
| Agent 定义 | 3+ |
| 数据库大小 | 388.49 MB |
| 代码行 (Python) | ~1,316,170 |
| 代码行 (JS/TS) | ~500,000+ |

---

## 9. 版本变化 (v2.0 → v3.0)

| 变化 | 详情 |
|:-----|:-----|
| **技能增长** | 5,826 → 6,073 (+247 SKILL.md, 来自新增技能库) |
| **Python 增长** | 3,802 → 3,817 文件 (+15) |
| **代码行增长** | ~1,300,000 → ~1,316,170 (+16,170) |
| **索引稳定性** | 节点/边数不变 (重新索引后一致) |
| **技能发现修复** | Sclerotium 端 SkillLoader 正确加载全部 6,073 技能 |

---

*由 CodeGraph MCP 索引生成 — 2026-06-16*
