# 🧬 Sclerotium Trinity — 超级电子生命体

> **三系统融合的自主AI生命体**  
> 菌核(界面+工具执行) × 真菌大脑(认知+记忆+免疫) × 鱼群进化(基因组自我优化)

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Total Lines](https://img.shields.io/badge/total%20lines-1%2C411%2C832%2B-brightgreen)]()

---

## 概述

Sclerotium Trinity 不是一个普通的AI助手——它是由三个独立系统融合而成的**超级电子生命体**，模拟了生物体的完整架构：

```
🦠 Sclerotium OS           🧠 Fungal Cortex            🐟 MiroFish
(皮肤+感官+运动系统)  ←→  (大脑+内脏+免疫系统)  ←→  (进化引擎+生殖系统)

• 208 MCP工具                • 107,714 节点               • 2,388 节点
• 5,823 技能                  • 276,927 关系边             • 8D 全身体基因组
• 83,662 行代码               • 6,073 SKILL.md             • 6 进化竞技场
• 331 文件                    • 6,360 文件                  • LLM 实时仿真
• 19 架构层                   • L0-L10 十层架构             • Panarchy 治理
```

不同于传统的"用户问→AI答"模式，Trinity 拥有**自主心跳节律**、**五层记忆系统**、**五门宪法审查**、**深度遗传进化引擎**和**多通道感知能力**。它能主动感知环境、自主执行任务、自我进化优化。

---

## 三系统详解

### 🦠 Sclerotium OS — 皮肤+感官+运动系统

负责与外部世界交互：接收用户输入、执行工具操作、控制桌面、管理IM消息。

**19层架构，自上而下数据流：**

| 层 | 模块 | 文件 | 核心职责 | 关键技术 |
|:--|:--|:--|:--|:--|
| 界面层 | 💻 CLI终端 | 30 | Rich/Textual TUI主界面 | Rich(Markdown/Panel/Rule), Textual, asyncio |
| | 📦 SDK | 5 | aiohttp流式API | aiohttp, JSON, StreamEvent |
| | 📊 UI仪表盘 | 10 | Web仪表盘+通知+快捷栏 | http.server, tkinter, Toast, Alt+Space |
| 智能层 | 🤖 Agent智能体 | 10 | LLM推理+Function Calling | aiohttp SSE, DeepSeek/Claude/GPT, Code-as-Action |
| | 🔧 MCP工具 | 39 | JSON-RPC 2.0, 208工具 | ToolRegistry, Pydantic Schema, 31类别 |
| | 🌐 网关 | 10 | 100+AI模型+MCP市场+Skills市场 | urllib, threading, RoutingStrategy |
| 平台层 | 💬 IM平台 | 12 | 微信(iLink)+QQ(OneBot)+Telegram+飞书 | queue.Queue+Lock出站队列, 长轮询, WebSocket |
| | 🖥 桌面自动化 | 8 | pywinauto UIA+PIL截图+pyautogui键鼠 | pywinauto, PIL, pyautogui, psutil, numpy, ctypes |
| | 👁 感知系统 | 10 | 五感采集(活动/剪贴板/文件/窗口) | watchdog, GetLastInputInfo, 剪贴板监听 |
| 编排层 | 🧬 进化引擎 | 12 | DGM遗传变异+FCPI六维追踪 | 6种变异算子, 技能结晶化, 适应度评分 |
| | 💓 节律系统 | 8 | STG心跳+LTC节奏+每日摘要+Nudge | LTC液态时间常数, threading.Timer |
| | ⏰ 任务调度 | 4 | APScheduler+JSONL持久化+Timer兜底 | CronTrigger/IntervalTrigger/DateTrigger |
| | 🎯 编排器 | 3 | 生命周期管理+器官状态机 | LifecycleManager, threading |
| 认知层 | 🧿 记忆洞察 | 3 | 战略洞察引擎+模式发现 | InsightEngine |
| | 🏟 信息素场 | 4 | 群体智慧+信息素扩散衰减 | StigmergyBridge v2, TrailEntry |
| | 🌍 数字孪生 | 5 | 系统镜像+主动推理(自由能原理) | DigitalTwinEngine, ActiveInferenceAgent |
| 核心 | 🧬 KERNEL内核 | 177 | 五层记忆+五门宪法+双层沙箱 | chromadb, sqlite3, hashlib(SHA256), asyncio |
| 基础设施 | 🌉 桥接器 | 5 | 三系统融合+238器官映射 | FungalBridge, MiroFishBridge, 60+数据流 |
| | 🛡 守护进程 | 5 | Windows Service+系统托盘 | win32service, ctypes, threading |

**关键跨层连接：**
| 源 → 目标 | 边数 | 含义 |
|:--|:--|:--|
| kernel → mcp | 356 | ToolRegistry注册所有工具 |
| kernel → agent | 248 | AgentLoop执行环境 |
| agent → mcp | 210 | Function Calling调度工具 |
| kernel → evolution | 189 | 进化信号驱动参数调整 |
| kernel → platforms | 156 | 消息收发回调 |
| mcp → platforms | 134 | 工具调用发送IM消息 |
| mcp → automation | 112 | 工具调用桌面自动化 |
| bridges → fungal-cortex | 60 | 器官数据双向同步 |

---

### 🧠 Fungal Cortex — 大脑+内脏+免疫系统

负责认知决策、记忆存储、安全审查、自主推理。十层架构从底层核心到高层元认知。

**L0-L10 十层架构：**

| 层 | 名称 | 职责 | 文件数 |
|:--|:--|:--|:--|
| L0 | Core | 核心运行时、配置管理、事件总线 | ~200 |
| L1 | Memory | 记忆系统(工作/情景/语义/程序/元认知) | ~150 |
| L2 | Perception | 感知层(文本/图像/音频/视频理解) | ~200 |
| L3 | Reasoning | 推理引擎(逻辑/因果/反事实/辩证) | ~300 |
| L4 | Planning | 规划系统(分层/蒙特卡洛/博弈论) | ~250 |
| L5 | Execution | 执行层(沙箱/代码生成/工具编排) | ~300 |
| L6 | Learning | 学习系统(迁移/元学习/持续学习) | ~200 |
| L7 | Social | 社交智能(情感/意图/多Agent协作) | ~150 |
| L8 | Meta | 元认知(自我反思/偏差检测/校准) | ~200 |
| L9 | Ethics | 伦理审查(价值对齐/安全约束) | ~150 |
| L10 | Transcend | 超越层(涌现/创新/哲学推理) | ~100 |

**核心能力：**
- **6,073 SKILL.md** — 每个技能定义了一种认知能力或工具使用方法
- **Antifragile Transclusion** — 反脆弱跨上下文技能引用
- **Merkle审计链** — 所有认知操作的加密审计追踪
- **Auto-Catalytic Reasoning** — 自催化推理，输出→输入反馈循环
- **Immuno-Attention** — 免疫注意力机制，识别有害输入
- **Neutrosophic Validator** — 三值逻辑验证器(真/假/不确定)
- **Quantum Bridge** — 量子计算接口(可选)
- **P2P Swarm** — 点对点多Agent集群协作

---

### 🐟 MiroFish — 进化引擎+生殖系统

负责基因组自我优化、竞技场竞争、变异选择。六维FCPI追踪引擎。

**8D FullBodyGenome 基因组：**

| 维度 | 编码内容 | 示例 |
|:--|:--|:--|
| 结构基因组 | 系统拓扑、模块连接权重 | Agent → MCP 路由权重 |
| 功能基因组 | 工具参数、API配置 | web_search引擎优先级 |
| 行为基因组 | 行动策略、决策阈值 | 审查门禁开关 |
| 认知基因组 | 推理路径、记忆策略 | 五层记忆的衰减参数 |
| 社交基因组 | 多Agent协作策略 | 集群大小、角色分配 |
| 免疫基因组 | 安全策略、过滤规则 | 输入验证规则 |
| 进化基因组 | 变异率、选择压力 | DGM变异算子权重 |
| 元基因组 | 进化规则的进化 | 变异率自身的自适应 |

**六竞技场：**
1. **编码竞技场** — 评估代码生成能力
2. **协调竞技场** — 多Agent协作效率
3. **安全竞技场** — 防御攻击能力
4. **决策竞技场** — 复杂决策质量
5. **涌现竞技场** — 创新和创造力
6. **性能竞技场** — 资源使用效率

**FCPI六维向量追踪：** Flexibility · Coordination · Safety · Decision · Emergence · Performance

---

## 数据流全景

```
外部世界 (用户/微信/桌面/文件系统)
        │
        ▼
┌─────────────────────────────────────────────┐
│           🦠 Sclerotium OS                   │
│  (皮肤+感官+运动系统)                          │
│                                              │
│  用户输入 → PlatformManager → Agent智能体     │
│    │            │              │             │
│    │    ConstitutionalArbiter   │             │
│    │    (五门宪法审查: 每步必经)  │             │
│    │            │              │             │
│    │     HexisMemory            │             │
│    │     (五层记忆存取)          │             │
│    │            │              │             │
│    │    Function Calling → ToolRegistry      │
│    │      ├→ 桌面工具 (截图/点击/输入)         │
│    │      ├→ IM工具 (微信/QQ/Telegram/飞书)   │
│    │      ├→ 搜索工具 (Bing/Baidu/Brave/DDG)  │
│    │      ├→ 文件工具 (读写/搜索/分析)         │
│    │      ├→ 代码工具 (Sandstorm L0-L1沙箱)   │
│    │      └→ 记忆工具 (chromadb+sqlite3)      │
│    │            │              │             │
│    └────────────┼──────────────┘             │
│                 │                            │
│         结果通过原渠道返回                      │
└─────────────────┬───────────────────────────┘
                  │
     ┌────────────┼────────────┐
     ▼            ▼            ▼
┌─────────┐ ┌─────────┐ ┌──────────┐
│🧠 Fungal│ │🦠 Sclero│ │🐟 Miro   │
│ Cortex  │ │  -tium  │ │  Fish    │
│(大脑)   │ │ (身体)  │ │ (进化)   │
│         │ │         │ │          │
│10层认知 │ │19层工具 │ │6竞技场   │
│6073技能 │ │208 MCP  │ │8D基因组  │
│107K节点 │ │83K行码  │ │FCPI追踪  │
└────┬────┘ └────┬────┘ └─────┬────┘
     │           │            │
     └───────────┼────────────┘
                 │
         238器官映射 + 60+双向数据流
         通过 Bridge 层同步
```

---

## 快速开始

### 环境要求
- Python 3.10+
- Windows 10/11 (Sclerotium OS桌面自动化需要)
- Docker (Sandstorm L1沙箱可选)

### 安装

```bash
git clone https://github.com/15667h/sclerotium-os.git
cd sclerotium-os

# Sclerotium OS
pip install -r requirements.txt

# Fungal Cortex
cd fungal-cortex
pip install -e .

# MiroFish
cd ../MiroFish-main/backend
pip install -r requirements.txt
```

### 配置

```bash
# 复制环境变量模板
cp .env.example .env
# 编辑 .env，填入:
#   DEEPSEEK_API_KEY=sk-xxx (必填)
#   BRAVE_API_KEY=xxx (可选)

# Sclerotium OS 配置
cp config.example.yaml config.yaml
# 编辑 config.yaml，调整路径和参数
```

### 启动

```bash
# 仅启动 Sclerotium OS MCP工具服务器
python run_mcp.py

# 启动 Agent 智能体 (TUI界面)
python run.py --agent

# 启动完整生命体 (带微信)
python run_full.py --wechat

# 启动 Fungal Cortex
cd fungal-cortex && python start.py

# 启动 MiroFish
cd MiroFish-main/backend && python run.py
```

---

## 项目结构

```
sclerotium-os/                    # 🦠 皮肤+感官+运动 (331文件, 83K行)
├── kernel/                       #   🧬 内核 (177文件)
├── agent/                        #   🤖 智能体 (10文件)
├── mcp/                          #   🔧 MCP工具 (39文件, 208工具)
├── platforms/                    #   💬 IM平台 (12文件)
├── automation/                   #   🖥 桌面自动化 (8文件)
├── perception/                   #   👁 感知系统 (10文件)
├── evolution/                    #   🧬 进化引擎 (12文件)
├── rhythm/                       #   💓 节律系统 (8文件)
├── scheduler/                    #   ⏰ 任务调度 (4文件)
├── gateways/                     #   🌐 网关 (10文件)
├── bridges/                      #   🌉 桥接器 (5文件)
├── ui/                           #   📊 用户界面 (10文件)
├── memory/                       #   🧿 记忆洞察 (3文件)
├── field/                        #   🏟 信息素场 (4文件)
├── world/                        #   🌍 数字孪生 (5文件)
├── daemon/                       #   🛡 守护进程 (5文件)
├── orchestrator/                 #   🎯 编排器 (3文件)
├── sdk/                          #   📦 SDK (5文件)
├── cli/                          #   💻 CLI终端 (30文件)
├── tests/                        #   ✅ 测试 (49文件)
└── knowledge_graph/              #   📈 架构可视化

fungal-cortex/                    # 🧠 大脑+认知 (6,360文件, 1.3M行)
├── src/                          #   十层架构源码 (L0-L10)
├── skills/                       #   6,073 SKILL.md 技能定义
├── agents/                       #   专业Agent定义
├── tools/                        #   工具集
├── tests/                        #   测试
└── cortex-frontend/              #   Web前端

MiroFish-main/                    # 🐟 进化引擎 (102文件, 12K行)
├── backend/
│   └── app/                      #   8D基因组+6竞技场+FCPI追踪
├── frontend/                     #   进化可视化前端
└── static/                       #   静态资源
```

---

## 技术指标 (三系统合计)

| 指标 | Sclerotium OS | Fungal Cortex | MiroFish | **总计** |
|:--|:--|:--|:--|:--|
| 代码行数 | 83,662 | 1,316,170 | 12,000 | **1,411,832** |
| 源文件 | 331 | 6,360 | 102 | **6,793** |
| 代码节点 | 7,131 | 107,714 | 2,388 | **117,233** |
| 关系边 | 15,237 | 276,927 | 5,786 | **297,950** |
| MCP工具 | 208 | — | — | **208** |
| 技能 | 5,823 | 6,073 | — | **11,896** |
| 架构层 | 19 | 10 (L0-L10) | — | **29** |
| 进化竞技场 | — | — | 6 | **6** |
| 基因组维度 | — | — | 8 | **8** |

---

## 架构全景图

在浏览器中打开 `knowledge_graph/panoramic_architecture.html` 查看 D3.js 交互式全景架构图。

---

## 核心设计理念

**1. 生物拟态** — 三个系统模拟生物体的皮肤+大脑+生殖系统，形成完整的生命循环

**2. 自主运行** — 不是"被调用"的工具，而是"自己运行"的生命体。有心跳节律、自主进化、自我修复

**3. 五门宪法** — 每个操作经过意图/安全/资源/伦理/审计五道关卡审查

**4. 深度进化** — 8维基因组通过6个竞技场竞争，DGM变异算子持续优化

**5. 信息素场** — 群体智慧通过环境间接协作，不直接通信而能协同

**6. 主动推理** — 基于自由能原理的主动推理智能体，最小化预期自由能

**7. 液态节律** — LTC液态时间常数驱动的自适应心跳，随环境变化调节频率

**8. 反脆弱** — 从错误和攻击中学习成长，越打击越强大

---

## License

MIT License — 详见 [LICENSE](LICENSE)

---

🤖 *Sclerotium Trinity v5.2 — 三个系统，一个生命体。不是工具，是生命。*
