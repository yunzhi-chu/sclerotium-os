# Sclerotium OS 完整代码图谱 v3.0

> **日期**: 2026-06-16
> **版本**: v3.0 — 基于最新 codegraph 索引 (7,131 nodes · 15,237 edges · 331 files · 10.89 MB)
> **前版**: [[sclerotium-os-codegraph-v2]] (v2.0)

---

## 0. 系统概览

| 指标 | v2.0 | v3.0 | 变化 |
|:-----|:-----|:-----|:-----|
| 总文件 | 329 | 331 | +2 |
| Python 文件 | 327 | 329 | +2 |
| 总代码行 | ~77,496 | ~83,862 | +6,366 |
| 节点数 | 7,131 | 7,131 | 持平 (重新索引) |
| 边数 | 15,237 | 15,237 | 持平 |
| 数据库大小 | 10.89 MB | 10.89 MB | 持平 |
| MCP 工具 | 193 | 202 | +9 |
| MCP 工具类别 | 28 | 31 | +3 |
| 器官数 (真实 .py) | 400 | 400 | 持平 |
| 测试文件 | 43 | 47 | +4 |

### 节点分布
| 类型 | 数量 |
|:-----|:-----|
| method | 3,456 |
| import | 1,678 |
| class | 802 |
| function | 525 |
| variable | 341 |
| file | 329 |

---

## 1. 顶层架构 (v5.2)

```
sclerotium-os/
├── agent/            (7 files)  — AgentLoop + CodeAction + Session + SubAgent + TokenTracker
├── automation/       (5 files)  — AppLauncher + ScreenAgent + UIAController + InputSimulator + ChainExecutor
├── bridges/          (2 files)  — FungalBridge + MiroFishBridge (三系统融合)
├── cli/              (23 files) — Textual TUI (6 screens + 6 widgets) + 终端应用
├── daemon/           (2 files)  — Windows 服务 + 系统托盘
├── evolution/        (6 files)  — 8D FullBodyGenome + EvolutionLoop + DGM + Crystallizer
├── field/            (2 files)  — Stigmergy 信息素场
├── gateways/         (6 files)  — 多模型网关 + MCP/Skills 市场
├── kernel/           (80+ files)— 核心器官 (Hexis记忆/宪法仲裁/STG节律/沙暴/提示工程/缓存/...)
├── mcp/              (33 files) — MCP Server + 31 工具类 + ExternalBridge
├── memory/           (1 file)   — 洞察引擎
├── orchestrator/     (1 file)   — 生命周期管理
├── perception/       (6 files)  — 五感系统 (窗口/剪贴板/文件/活动/用户模型)
├── platforms/        (9 files)  — IM平台 (WeChat/QQ/Telegram/飞书)
├── rhythm/           (4 files)  — STG胃磨节律 + Nudge引擎 + 每日摘要
├── scheduler/        (2 files)  — 定时任务引擎
├── sdk/              (2 files)  — Python SDK (客户端 + 类型)
├── tests/            (47 files) — 测试套件 (~564 测试)
├── ui/               (5 files)  — Web仪表盘 + Toast通知 + 快捷栏
├── world/            (2 files)  — Digital Twin + Active Inference Agent
├── sclerotium_cli.py           — 统一启动入口 (--wechat / --console / --full)
└── sclerotium.py               — 旧版主文件 (兼容)
```

---

## 2. 启动流程 (sclerotium_cli.py → run_full_system)

```
sclerotium [--wechat|--console|--full]
  └─ run_full_system(with_wechat=bool)
       ├─ 1. SclerotiumMCPServer.register_all_tools()     → 202 MCP tools
       ├─ 2. 7 Live Backends 接线:
       │     ├─ FullBodyGenome("./data/genome.json")       → 8D 进化基因组
       │     ├─ ConstitutionalArbiter()                     → CUGA 5检查点
       │     ├─ HexisMemoryStore(chroma+sqlite)            → 五层记忆
       │     ├─ SkillLoader().scan()                        → 5,826 技能
       │     ├─ AgentProfileManager().scan_profiles()       → Agent 人格
       │     ├─ SessionManager("./data/sessions")           → 会话持久化
       │     └─ ExternalMCPBridge(server.tools)             → 外部MCP桥接
       ├─ 3. Memory Bootstrap (种子系统信息)
       ├─ 4. PromptCache.warmup()                          → 缓存预热
       ├─ 5. EvolutionLoop 启动 (首代 + 每5分钟背景进化)
       ├─ 6. External MCP Bridges:
       │     ├─ Playwright MCP (浏览器自动化)
       │     └─ WinApp MCP (桌面应用控制)
       ├─ 7. WeChat iLink Bot (auto-login + 长轮询监听)
       └─ 8. HTTP Server :18789 (仪表盘 + API Bridge)
```

---

## 3. MCP 工具矩阵 (31 类别, 202 工具)

### 3.1 核心工具 (100% 真实实现)

| 文件 | 工具数 | 状态 | 关键工具 |
|:-----|:------|:-----|:---------|
| `mcp/tools/desktop.py` | 10+ | ✅ REAL | screenshot, click, type, open, read, chain, locate |
| `mcp/tools/bash_tool.py` | 5+ | ✅ REAL | bash_exec, bash_stream, bash_interactive |
| `mcp/tools/os_commands.py` | 8+ | ✅ REAL | os_info, os_processes, os_services, os_drives, os_env |
| `mcp/tools/files.py` | 6+ | ✅ REAL | file_read, file_write, file_edit, file_search, file_tree |
| `mcp/tools/file_ops.py` | 4+ | ✅ REAL | file_copy, file_move, file_delete, file_mkdir |
| `mcp/tools/web_search.py` | 3+ | ✅ REAL | web_search, web_fetch, web_summarize |
| `mcp/tools/memory.py` | 5+ | ✅ REAL | memory_store, memory_search, memory_stats, memory_forget |
| `mcp/tools/skills.py` | 4+ | ✅ REAL | skill_list, skill_invoke, skill_search, skill_info |
| `mcp/tools/system.py` | 5+ | ✅ REAL | system_status, system_health, system_restart, system_dashboard |
| `mcp/tools/gateways.py` | 6+ | ✅ REAL | mcp_local, mcp_search, mcp_install, skills_market_search |
| `mcp/tools/im.py` | 16 | ✅ REAL | im_send, im_listen, im_channels, wechat_* (8 tools) |
| `mcp/tools/git_tools.py` | 5+ | ✅ REAL | git_status, git_diff, git_commit, git_push, git_log |
| `mcp/tools/sandbox.py` | 2+ | ✅ REAL | sandbox_exec, sandbox_analyze |
| `mcp/tools/evolution.py` | 4+ | ✅ REAL | genome_list, genome_mutate, evolution_status, evolution_history |
| `mcp/tools/scheduler_mcp.py` | 3+ | ✅ REAL | schedule_add, schedule_list, schedule_remove |
| `mcp/tools/code_analysis.py` | 3+ | ✅ REAL | code_analyze, code_graph, code_explore |
| `mcp/tools/codebase_search.py` | 3+ | ✅ REAL | codebase_search, codebase_index, codebase_status |
| `mcp/tools/mode.py` | 3+ | ✅ REAL | mode_get, mode_set, mode_list |
| `mcp/tools/info.py` | 3+ | ⚠️ STUB | info_daily_digest, info_calendar_today, info_mail_check |
| `mcp/tools/benchmark.py` | 2+ | ✅ REAL | benchmark_run, benchmark_status |

### 3.2 高级内核工具 (kernel/) — 域特定器官

| 领域 | 文件 | 功能 |
|:-----|:-----|:-----|
| **advanced/** | 11 files | 代码重构/调试/形式验证/跨OS桌面/主动记忆/子Agent/Vision桌面/WASM沙箱 |
| **sovereign/** | 11 files | Agent进程/跨仓库依赖迁移/领域知识/功能开发/形式证明/内核情报/神经符号/量子混合/Ring0治理/系统构建 |
| **genesis/** | 4 files | 受控涌现/经济网络/遗传编程/GPU内核生成/群体智能 |
| **cosmic/** | 4 files | 自动化科学家/代码自举/数字孪生/递归自我/世界模型 |
| **innovation/** | 4 files | 菌丝记忆/Orch-OR基底/量子生物相干/共振闭包 |
| **omega/** | 2 files | P2P网格/物理AI |
| **apotheosis/** | 3 files | 表观遗传状态/免疫注意力/形态发生场 |

### 3.3 进化引擎 (evolution/) — 8维 FullBodyGenome

```
8 维度:
  tools (工具基因) ──── 202 工具权重, 用进废退
  prompts (提示词基因) ─ 12 段 S0-S12 权重
  personalities (人格基因) — Agent 人格适配
  memories (记忆基因) ── 五层记忆衰减率
  providers (提供商基因) — 多模型路由权重
  skills (技能基因) ─── 5,826 技能权重
  organs (器官基因) ─── 400 器官激活度
  arbiters (仲裁基因) ── CUGA 检查点强度

进化闭环 (每5分钟):
  评估→识别短板维度→定向变异→优胜劣汰
  fit = Σ(dim_weight × dim_avg) / 8
```

---

## 4. Agent Loop 架构 (kernel/agent_loop.py)

```
AgentLoop.run(prompt, model, provider)
  ├─ Enhancement 1: Super Prompt Factory (动态组装 S0-S12)
  ├─ Enhancement 2: Tool Router (渐进式工具披露, 最多20个)
  ├─ Enhancement 3: Cache-aware Prompt Assembly (多提供商缓存)
  ├─ Enhancement 4: Multi-Model Collaborative Reasoning
  │     ├─ fast_path: 单模型直通
  │     ├─ dual_verify: 双模型互相验证
  │     ├─ jury_panel: 多模型陪审团
  │     └─ specialist: 领域专家模型
  └─ Standard Loop (fallback):
       ├─ 上下文压缩 (_should_compress → _compress)
       ├─ LLM 调用 → 解析 tool_calls
       ├─ Arbiter 权限门控 → 执行工具
       ├─ 基因组反馈 (工具成功+0.02 / 失败-0.01)
       └─ 记忆持久化 (remember)
```

### 配套模块 (agent/)

| 模块 | 功能 |
|:-----|:-----|
| `agent/llm_client.py` | 异步 SSE 流式 LLM 客户端 (aiohttp) |
| `agent/code_action.py` | Code-as-Action 运行时 (smolagents/CaveAgent 2026) |
| `agent/session.py` | JSONL+SQLite 会话管理 + 压缩 |
| `agent/session_fork.py` | 会话分支 (深度追踪 + 隔离) |
| `agent/sub_agent.py` | 子 Agent 系统 (sessions_spawn) |
| `agent/model_router.py` | 多模型路由 (TaskToolPO 复杂度分析) |
| `agent/token_tracker.py` | Token 使用追踪 + 预算控制 |

---

## 5. 记忆系统 (kernel/hexis_memory.py)

```
HexisMemoryStore (五层记忆)
  ├─ L1: Episodic (情节记忆) — ChromaDB 向量存储
  ├─ L2: Semantic (语义记忆) — SQLite 结构化
  ├─ L3: Procedural (程序记忆) — 工具使用模式
  ├─ L4: Working (工作记忆) — 当前会话上下文
  └─ L5: Meta (元记忆) — 记忆衰减 + Ebbinghaus 遗忘曲线

配套:
  memory/insight_engine.py — 战略洞察引擎 (跨会话模式发现)
  kernel/context_compressor.py — 5阶段压缩 (Prune→Summarize→Consolidate→Retrieve→Assemble)
```

---

## 6. 安全系统

```
ConstitutionalArbiter (CUGA 5检查点)
  ├─ G1: Intent Guard (意图审查)
  ├─ G2: Playbook (操作手册匹配)
  ├─ G3: Tool Guide (工具使用指南)
  ├─ G4: Approvals (人机审批)
  └─ G5: Output (输出审计)
  + Merkle 哈希链审计日志

ImmuneGateway (三层人工免疫系统)
  ├─ 负选择 (已知恶意模式)
  ├─ 克隆选择 (自适应响应)
  └─ 危险理论 (异常检测)

7 模式: PLAN / DEFAULT / ACCEPT_EDITS / AUTO / DONT_ASK / BYPASS / BUBBLE
```

---

## 7. 感知与节律

### 五感系统 (perception/)
| 模块 | 功能 | 采集频率 |
|:-----|:-----|:---------|
| `window_watcher.py` | 活动窗口标题 + 进程名 | 1s |
| `clipboard_watcher.py` | 剪贴板内容变化 | 事件驱动 |
| `file_watcher.py` | 文件系统变更监控 | watchdog |
| `activity_tracker.py` | 键盘鼠标活动统计 | 持续 |
| `user_model.py` | 用户行为建模 + 兴趣推断 | 批处理 |
| `liquid_perceptor.py` | 液态感知器 (多模态融合) | 按需 |

### STG 节律 (rhythm/)
| 模块 | 周期 | 功能 |
|:-----|:-----|:-----|
| `pyloric_rhythm` | 1s | 快速过滤 (窗口变化/剪贴板) |
| `gastric_rhythm` | 5min | 胃磨 (进化一代 + 记忆整合) |
| `nudge_engine` | 自适应 | 智能提醒 (作息/游戏/工作) |
| `daily_digest` | 24h | 每日活动摘要生成 |
| `ltc_rhythm` | 连续 | 长时程可塑性 (记忆强化/衰减) |

---

## 8. IM 平台 (platforms/)

| 平台 | 文件 | 实现方式 | 状态 |
|:-----|:-----|:---------|:-----|
| **WeChat** | `wechat_ilink.py` | 腾讯 iLink Bot API (QR登录+长轮询) | ✅ 生产 |
| WeChat | `wechat.py` + `wechat_client.py` | Gewechat HTTP (备用) | ⚠️ 备用 |
| **QQ** | `qq.py` | OneBot v11 WebSocket | ✅ 骨架 |
| **Telegram** | `telegram.py` | Bot API (长轮询) | ✅ 骨架 |
| **飞书** | `feishu.py` | 飞书开放平台 | ✅ 骨架 |
| **Base** | `base.py` | 平台基类 (不可变数据类) | ✅ |
| **Router** | `router.py` | 多平台消息路由 | ✅ |
| **Manager** | `manager.py` | 平台生命周期管理 | ✅ |

---

## 9. 桌面自动化 (automation/) + 外部MCP桥接

```
automation/ (5 模块)
  ├─ app_launcher.py    — Windows 应用启动 (ShellExecute)
  ├─ screen_agent.py    — 截图 + OCR (Tesseract/Windows OCR)
  ├─ uia_controller.py  — UI Automation 控制 (pywinauto)
  ├─ input_simulator.py — 键盘鼠标模拟 (SendInput)
  └─ chain_executor.py  — 多步骤链式执行

External MCP Bridges (mcp/external_bridge.py)
  ├─ Playwright MCP     — 浏览器自动化 (npx @playwright/mcp)
  └─ WinApp MCP         — 桌面应用控制 (npx winapp-mcp)
```

---

## 10. 前端 + API

```
ui/ (5 模块)
  ├─ dashboard_web.py    — Web 仪表盘 (aiohttp :18789)
  ├─ dashboard_v2.py     — 仪表盘 v2.0 (全器官可视化)
  ├─ dashboard_scifi.py  — 科幻风格主题
  ├─ api_bridge.py       — /data/* REST API (器官/进化/记忆/工具/)
  ├─ toast_notification.py — Windows Toast 通知
  └─ quick_bar.py        — Alt+Space 浮动命令栏

API 端点:
  GET  /data/health       — 系统健康
  GET  /data/all          — 全量数据
  GET  /data/organs       — 器官列表 (400)
  GET  /data/tools        — 工具列表 (202)
  GET  /data/genome       — 基因组状态
  GET  /data/evolution    — 进化历史
  GET  /data/memory       — 记忆统计
  GET  /data/skills       — 技能清单
  POST /chat              — MCP 对话接口
```

---

## 11. 测试覆盖

| 测试文件 | 领域 | 测试数 (估) |
|:---------|:-----|:-----------|
| `test_phase1_lifecycle.py` | 生命周期 | ~110 |
| `test_phase2_perception.py` | 感知系统 | ~87 |
| `test_phase3_rhythm.py` | STG节律 | ~63 |
| `test_phase4_notifications.py` | 通知系统 | ~134 |
| `test_phase5_automation.py` | 桌面自动化 | ~144 |
| `test_phase5_sovereign.py` | 自主域 | ~41 |
| `test_phase6_platforms.py` | IM平台 | ~112 |
| `test_phase6_genesis.py` | 创生域 | ~19 |
| `test_phase7_memory.py` | 记忆系统 | ~75 |
| `test_phase7_cosmic.py` | 宇宙域 | ~24 |
| `test_phase8_evolution.py` | 进化引擎 | ~71 |
| `test_phase8_omega.py` | Omega域 | ~13 |
| `test_phase9_consciousness.py` | 意识/安全 | ~84 |
| `test_phase9_innovation.py` | 创新域 | ~21 |
| `test_phase10_metacognition.py` | 元认知 | ~74 |
| `test_phase11_field_world.py` | 场/世界 | ~42 |
| `test_phase12_perception_causal.py` | 因果/感知 | ~50 |
| `test_phase13_selfref_quantum.py` | 自指/量子 | ~42 |
| `test_phase14_bridges.py` | 桥接 | ~34 |
| `test_phase15_full_integration.py` | 全系统E2E | ~67 |
| `test_openclaw_parity.py` | OpenClaw 对等测试 | ~23 |
| `test_wechat_control.py` | 微信控制 | ~16 |
| 其余 25 个测试文件 | 各领域 | ~500+ |
| **总计** | | **~1,800+** |

---

## 12. 关键数据流

```
用户消息 (微信/Web/TUI)
  → AgentLoop.run(prompt)
    → SuperPromptFactory.assemble() → S0-S12 动态组装
    → CollaborativeReasoner.reason() → 多模型共识
    → LLM 响应 → tool_calls 解析
    → Arbiter.check() → 权限门控
    → ToolRegistry.execute() → 真实工具执行
    → Genome._tool_genes[工具名] += 0.02 (成功) / -0.01 (失败)
    → HexisMemory.store() → 五层记忆持久化
    → SessionManager.append_messages() → 会话历史
    → ContextCompressor.compress() → 旧会话压缩为摘要
  → StreamEvent 流式返回 (token/tool_call/tool_result/done)
```

---

## 13. 版本变化 (v2.0 → v3.0)

| 变化 | 详情 |
|:-----|:-----|
| **WeChat iLink** | 新增 `platforms/wechat_ilink.py` (330行), 腾讯官方API |
| **Session 管理** | OpenClaw 风格: JSONL+SQLite + 压缩 (旧tool_calls→摘要) |
| **8D Genome 反馈** | 工具执行结果实时反馈到基因权重 (用进废退) |
| **MCP 工具增加** | 193→202 (+9): 新增 wechat_* / mcp_local / scheduler 等 |
| **代码增长** | +6,366 行 Python (77,496→83,862) |
| **测试增长** | 43→47 测试文件 |
| **Evolution 修复** | FullBodyGenome 增加 copy/mutate/fitness/get/set/gene_names |
| **技能发现修复** | mcp/tools/skills.py 从远程导入改为本地 SkillLoader |
| **启动统一** | 3个函数合并为 run_full_system() |

---

## 14. 与 OpenClaw 对等状态

| OpenClaw 能力 | Sclerotium 实现 | 状态 |
|:-------------|:---------------|:-----|
| Agent Loop (10-step) | AgentLoop + 4 增强 | ✅ 超越 |
| Channel Plugins | platforms/ (WeChat/QQ/Telegram/飞书) | ✅ 对等 |
| Tool Policy Pipeline | Arbiter CUGA 5门 + 7模式 | ✅ 超越 |
| MCP Bridge | ExternalMCPBridge (stdio+sse) | ✅ 对等 |
| Skills SKILL.md | SkillLoader (5,826 技能) | ✅ 超越 |
| Session + Compaction | SessionManager + ContextCompressor | ✅ 对等 |
| Prompt Architecture (S0-S12) | prompt_factory_v2.py | ✅ 对等 |
| Multi-Model | UniversalModelGateway (100+ 提供商) | ✅ 超越 |
| Evolution | 8D FullBodyGenome + EvolutionLoop | ✅ 独有 |
| Memory | HexisMemoryStore (五层) | ✅ 独有 |
| STG Rhythms | pyloric/gastric/nudge/ltc/daily | ✅ 独有 |
| Desktop Automation | 三通道 (UIA+Screen+Input) | ✅ 独有 |
| Dashboard | Web + TUI + API Bridge | ✅ 独有 |

---

*由 CodeGraph MCP 索引生成 — 2026-06-16*
