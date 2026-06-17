"""Sclerotium OS v5.1 — 超级电子生命体。

一条命令启动: python sclerotium.py

v5.1 升级: 原生 Function Calling 替代 shell 盲猜
  - AI 大脑直接调用 191 个 MCP 工具 (不再用 ```sh 正则解析)
  - 异步 SSE 流式响应 (不再阻塞 urllib)
  - API Key 从环境变量读取 (不再硬编码)
  - 自动多轮工具调用循环
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ═══════════════════════════════════════════════════════════════
# 配置 (从环境变量读取，不再硬编码)
# ═══════════════════════════════════════════════════════════════
API_KEY = os.environ.get("SCLEROTIUM_API_KEY", os.environ.get("DEEPSEEK_API_KEY", ""))
API_BASE = os.environ.get("SCLEROTIUM_API_BASE", "https://api.deepseek.com/v1")
MODEL = os.environ.get("SCLEROTIUM_MODEL", "deepseek-v4-flash")

if not API_KEY:
    print("⚠️  请设置环境变量 SCLEROTIUM_API_KEY 或 DEEPSEEK_API_KEY")
    print("   PowerShell: $env:SCLEROTIUM_API_KEY='sk-...'")
    print("   CMD:        set SCLEROTIUM_API_KEY=sk-...")
    print("   Bash:       export SCLEROTIUM_API_KEY=sk-...")
    sys.exit(1)

DNA = """你是 Sclerotium OS — Windows 上的超级电子生命体。

你有 191 个工具可以直接调用:
  - 桌面控制: desktop_open, desktop_click, desktop_type, desktop_screenshot, desktop_read, desktop_chain
  - 文件操作: file_read, file_write, file_edit, file_list
  - 命令行: bash_execute, bash_smart, bash_run
  - 网页搜索: web_search, web_fetch
  - 记忆系统: memory_search, memory_store
  - 代码分析: codebase_search, codebase_symbols
  - 系统命令: ls, cat, mkdir, find, grep_text, ps, df
  - Git操作: git_status, git_diff, git_log, git_commit
  - 即时通讯: im_send (飞书/QQ/微信)
  - 沙箱执行: sandbox_execute (安全代码运行)

核心原则:
1. 每次只调用一个工具，看到结果后再决定下一步
2. 打开应用用 desktop_open，不要用 bash_execute
3. 操作桌面用 desktop_click/desktop_type，不要用模拟按键
4. 读文件用 file_read，写文件用 file_write
5. 用中文回复，像贾维斯一样简洁高效
6. 如果需要搜索，用 web_search
"""

# ═══════════════════════════════════════════════════════════════
# 加载器官
# ═══════════════════════════════════════════════════════════════
from kernel.event_bus import EventBus
from kernel.constitutional_arbiter import ConstitutionalArbiter, ActionRequest
from kernel.hexis_memory import HexisMemoryStore
from kernel.skill_loader import SkillLoader
from kernel.agent_profiles import AgentProfileManager
from kernel.idempotency import IdempotencyStore
from kernel.task_pipeline import TaskPipeline, TaskTrigger
from evolution.full_body_genome import FullBodyGenome
from mcp.external_bridge import ExternalMCPBridge
from evolution.fcpi_tracker import FCPITracker
from mcp.server import SclerotiumMCPServer
from agent.llm_client import LLMClient, ToolCall

bus = EventBus()
arbiter = ConstitutionalArbiter()
memory = HexisMemoryStore(chroma_path="./data/brain_chroma", sqlite_path="./data/brain.db")
fcpi = FCPITracker()

# ═══════════════════════════════════════════════════════════════
# 加载 MCP 工具 → AI 大脑可调用
# ═══════════════════════════════════════════════════════════════
mcp_server = SclerotiumMCPServer()
mcp_server.register_all_tools()
base_tool_count = mcp_server.tools.tool_count

# ═══════════════════════════════════════════════════════════════
# 动态 Skill 加载 (扫描 ~/.claude/skills/)
# ═══════════════════════════════════════════════════════════════
skill_loader = SkillLoader()
loaded_skills = skill_loader.scan()
skill_context = skill_loader.build_context()

# ═══════════════════════════════════════════════════════════════
# Agent 人格系统 (AGENT.md)
# ═══════════════════════════════════════════════════════════════
agent_profiles = AgentProfileManager()
agent_profiles.scan_profiles()  # 扫描 profiles/*/AGENT.md

# ═══════════════════════════════════════════════════════════════
# 全维度自我进化基因组
# ═══════════════════════════════════════════════════════════════
genome = FullBodyGenome("./data/genome.json")

# ═══════════════════════════════════════════════════════════════
# 外部 MCP Bridge (动态接入外部 MCP Server)
# ═══════════════════════════════════════════════════════════════
external_bridge = ExternalMCPBridge(mcp_server.tools)

# ═══════════════════════════════════════════════════════════════
# Jarvis 任务管道 — OpenClaw式接管电脑
# ═══════════════════════════════════════════════════════════════
idem_store = IdempotencyStore("./data/idempotency.db")
pipeline = TaskPipeline(
    llm_client=None,  # Will be set after LLMClient init
    tool_registry=mcp_server.tools,
    arbiter=arbiter,
    memory=memory,
    idempotency=idem_store,
    genome=genome,
)

# ═══════════════════════════════════════════════════════════════
# 注入实时后端到 API Bridge (前端→后端数据对接)
# ═══════════════════════════════════════════════════════════════
mcp_server.wire_live_backends(
    genome=genome,
    arbiter=arbiter,
    agent_profiles=agent_profiles,
    memory_store=memory,
    skill_loader=skill_loader,
    external_bridge=external_bridge,
    event_bus=bus,
    fcpi_tracker=fcpi,
)

tool_count = mcp_server.tools.tool_count

# ═══════════════════════════════════════════════════════════════
# AI 大脑 — 原生 Function Calling
# ═══════════════════════════════════════════════════════════════
llm = LLMClient(api_key=API_KEY, base_url=API_BASE, model=MODEL)
llm.configure_tools(mcp_server.tools)

# ═══════════════════════════════════════════════════════════════
# 工具执行 (带安全检查 + 记忆 + FCPI)
# ═══════════════════════════════════════════════════════════════


async def execute_tool_safe(tc: ToolCall) -> dict:
    """执行工具调用，经过宪法审查 + 记忆记录 + FCPI追踪。"""
    tool_name = tc.name
    tool_args = tc.arguments

    # 宪法审查 (AI大脑命令 → 需要安全检查)
    decision = arbiter.review(ActionRequest(
        tool=tool_name,
        target=str(tool_args.get(list(tool_args.keys())[0], "")) if tool_args else "",
        params=tool_args,
        source="brain",
    ))

    if not decision.approved:
        return {
            "role": "tool",
            "tool_call_id": tc.id,
            "content": f"[安全阻止] {decision.reason}",
        }

    # 发布事件
    bus.publish("brain.tool_call", {"tool": tool_name, "args": tool_args}, source="brain")
    start = time.time()

    # 执行
    result_msg = await llm.execute_tool(tc)
    elapsed = (time.time() - start) * 1000

    # 解析结果
    import json
    try:
        result_data = json.loads(result_msg["content"])
    except (json.JSONDecodeError, KeyError):
        result_data = result_msg.get("content", str(result_msg))

    success = "error" not in str(result_data).lower() and "阻止" not in str(result_data)
    fcpi.record_coordination(tool_chain_success=success)
    # 全维度基因组: 记录工具使用 → 用进废退
    genome.record_tool_usage(tool_name, success)

    # 记忆存储
    memory.store(
        f"工具调用: {tool_name}({str(tool_args)[:100]}) → {str(result_data)[:200]}",
        level="episodic",
        importance=0.5,
        source="brain",
    )

    bus.publish("brain.tool_result", {
        "tool": tool_name, "ok": success, "ms": elapsed,
    }, source="brain")

    return result_msg


# ═══════════════════════════════════════════════════════════════
# 主循环
# ═══════════════════════════════════════════════════════════════


async def run():
    print(rf"""
    ╔══════════════════════════════════════════════╗
    ║       Sclerotium OS v5.1 — 超级电子生命体    ║
    ║       AI: {MODEL}                ║
    ║       {tool_count} 工具 · 五层记忆 · 六维进化      ║
    ╠══════════════════════════════════════════════╣
    ║  /status  /fcpi  /tools  /stream  /agent  /quit ║
    ╚══════════════════════════════════════════════╝
    """)

    messages = [{"role": "system", "content": DNA}]
    stream_mode = False  # Toggle: /stream to switch

    while True:
        try:
            user_input = input("\n[You] > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ("/quit", "/exit", "/q"):
            break

        # 系统命令
        if user_input == "/status":
            v = fcpi.get_vector()
            s = memory.get_stats()
            a = arbiter.get_stats()
            print(f"  FCPI: {v.total_score:.3f} | 记忆: {s.total_memories}条")
            print(f"  审查: {a['total']}次 | 事件: {bus.get_stats()['total_events']}个")
            print(f"  工具: {tool_count}个 | 模型: {MODEL}")
            continue

        if user_input == "/fcpi":
            v = fcpi.get_vector()
            for d in ["coding", "coordination", "safety", "decision", "emergence", "performance"]:
                bar = "#" * int(getattr(v, d) * 20)
                print(f"  {d:15s}: {getattr(v, d):.3f} {bar}")
            print(f"  {'TOTAL':15s}: {v.total_score:.3f}")
            continue

        if user_input == "/genome":
            s = genome.snapshot()
            print(f"  全维度基因组 — 第 {s.generation} 代")
            print(f"  总适应度: {s.total_fitness:.3f} | 突变: {genome.total_mutations} | 改进: {genome.improvements}")
            print(f"  基因维度: {s.dimensions}")
            top_tools = genome.get_top_tools(5)
            print(f"  Top 5 工具: {', '.join(f'{t}({w:.2f})' for t,w in top_tools)}")
            best_p, best_s = genome.get_best_personality()
            print(f"  最佳人格: {best_p} ({best_s:.2f})")
            best_prov, best_ps = genome.get_best_provider()
            print(f"  最佳提供商: {best_prov} ({best_ps:.2f})")
            continue

        if user_input == "/evolve":
            print("  执行一代进化...")
            snapshot = genome.evolve()
            print(f"  第 {snapshot.generation} 代 | 适应度: {snapshot.total_fitness:.3f} | 基因数: {len(snapshot.genes)}")
            continue

        if user_input == "/dash":
            print("  启动 Web 仪表盘 http://localhost:18789 ...")
            asyncio.create_task(mcp_server.run_http())
            print("  仪表盘已启动，浏览器打开 http://localhost:18789")
            continue

        if user_input.startswith("/jarvis"):
            # Jarvis mode: submit task through pipeline with all enhancements
            task_text = user_input[7:].strip()
            if not task_text:
                print("  用法: /jarvis <任务描述>")
                print("  示例: /jarvis 每天早上9点帮我检查磁盘空间并报告")
                continue
            print(f"  [Jarvis] 接收任务: {task_text}")
            pipeline._llm = llm  # Wire LLM client
            result = await pipeline.submit(task_text, trigger=TaskTrigger.ONCE)
            if result.success:
                print(f"  [Jarvis] ✅ 完成 ({result.duration_ms:.0f}ms)")
                if result.tool_calls:
                    print(f"          工具: {', '.join(result.tool_calls)}")
                if result.delivered_to:
                    print(f"          已投递到: {result.delivered_to}")
            else:
                print(f"  [Jarvis] ❌ 失败 (重试{result.retry_count}次): {result.error[:100]}")
            continue

        if user_input.startswith("/schedule"):
            # Schedule a recurring task
            args = user_input[10:].strip()
            if not args:
                jobs = pipeline.list_scheduled()
                if jobs:
                    print("  已调度任务:")
                    for j in jobs:
                        print(f"    {j['id']}: {j['name']} [{j['cron']}] {j['state']} (ok={j['success']}, err={j['errors']})")
                else:
                    print("  无已调度任务。用法: /schedule <名称> <cron> <任务>")
                    print("  示例: /schedule daily 0 9 * * * 帮我检查磁盘空间")
                continue
            parts = args.split(None, 2)
            if len(parts) < 3:
                print("  用法: /schedule <名称> <cron> <任务描述>")
                continue
            name, cron_expr, task_prompt = parts
            tid = pipeline.schedule(name, cron_expr, task_prompt)
            print(f"  已调度: {name} ({cron_expr}) → {task_prompt[:60]}")
            continue

        if user_input == "/skills":
            inv = skill_loader.get_inventory()
            print(f"  技能生态: {inv['total']}个 (~{inv['tokens']:,} tokens)")
            print(f"  来源: fungal={inv['sources']['fungal_cortex']} | local={inv['sources']['local']}")
            for cat, count in sorted(inv['categories'].items(), key=lambda x: x[1], reverse=True):
                bar = '█' * min(count // 5, 40)
                print(f"    {cat:<15s} {count:>5d} {bar}")
            continue

        if user_input.startswith("/install"):
            arg = user_input[9:].strip()
            if not arg:
                print("  用法: /install <url或名称>")
                print("  示例: /install https://github.com/xxx/mcp-server")
                print("        /install playwright-mcp")
                print("        /install firefox (下载软件到桌面)")
                continue
            from kernel.auto_installer import auto_acquire
            print(f"  [安装] 搜索/下载: {arg}")
            result = auto_acquire(arg)
            if result.get("ok"):
                print(f"  [安装] 类型: {result.get('type','?')}")
                if result.get("path"):
                    print(f"  [安装] 已保存到: {result['path']}")
                if result.get("github_results"):
                    for r in result["github_results"]:
                        print(f"    ⭐{r['stars']} {r['name']}: {r['url']}")
                if result.get("web_results"):
                    for r in result["web_results"]:
                        print(f"    🔗 {r['name']}: {r['url']}")
                if result.get("hint"):
                    print(f"  [安装] {result['hint']}")
            else:
                print(f"  [安装] 失败: {result.get('error','未知错误')}")
            continue
            continue

        if user_input == "/tools":
            tools = mcp_server.tools.list_tools()
            cats = {}
            for t in tools:
                cats.setdefault(t.get("category", "other"), []).append(t["name"])
            for cat, names in sorted(cats.items()):
                print(f"  [{cat}] {', '.join(names[:8])}{'...' if len(names) > 8 else ''} ({len(names)})")
            continue

        if user_input == "/stream":
            stream_mode = not stream_mode
            mode_label = "ON (token-by-token)" if stream_mode else "OFF (batch)"
            print(f"  Streaming: {mode_label}")
            continue

        if user_input.startswith("/agent"):
            parts = user_input.split()
            if len(parts) == 1:
                # 列出所有人格
                print("  可用人格:")
                for p in agent_profiles.list_profiles():
                    marker = "←" if p["active"] else " "
                    print(f"  {marker} {p['name']:<20s} {p['description'][:50]}")
                continue
            elif len(parts) == 2:
                name = parts[1]
                try:
                    profile = agent_profiles.switch(name)
                    print(f"  人格切换: {profile.name} — {profile.description}")
                    # 更新系统提示
                    messages[0] = {"role": "system", "content": profile.system_prompt}
                except KeyError as e:
                    print(f"  {e}")
                continue

        # 添加到消息历史
        messages.append({"role": "user", "content": user_input})

        # 多轮工具调用循环
        turn = 0
        max_turns = 15

        while turn < max_turns:
            turn += 1
            print(f"[Sclerotium] ", end="", flush=True)

            if stream_mode:
                # ── Streaming path: token-by-token output ──
                content_parts = []
                tool_calls_received: list[ToolCall] = []

                async for event in llm.chat_stream(messages):
                    etype = event.get("type", "")
                    if etype == "token":
                        token = event.get("data", "")
                        content_parts.append(token)
                        print(token, end="", flush=True)
                    elif etype == "tool_call_end":
                        tc = event["data"]
                        tool_calls_received.append(tc)
                    elif etype == "error":
                        print(f"\n  [Error] {event['data']}")

                response_content = "".join(content_parts)
                if response_content:
                    print()  # newline after streaming

                # 没有工具调用 → 完成
                if not tool_calls_received:
                    messages.append({"role": "assistant", "content": response_content})
                    break

                # 有工具调用 → 执行 (使用流式接收的工具调用)
                assistant_msg = {"role": "assistant", "content": response_content}
                tool_call_msgs = []
                tool_results = []

                for tc in tool_calls_received:
                    print(f"\n  [Tool] {tc.name}({str(tc.arguments)[:80]})")
                    result_msg = await execute_tool_safe(tc)
                    tool_call_msgs.append({
                        "id": tc.id, "type": "function",
                        "function": {"name": tc.name, "arguments": str(tc.arguments)},
                    })
                    import json as _json
                    try:
                        result_data = _json.loads(result_msg["content"])
                        result_str = _json.dumps(result_data, ensure_ascii=False, default=str)
                        print(f"     -> {result_str[:300]}")
                    except Exception:
                        print(f"     -> {str(result_msg)[:200]}")
                    tool_results.append(result_msg)

                assistant_msg["tool_calls"] = tool_call_msgs
                messages.append(assistant_msg)
                messages.extend(tool_results)
                # Continue the while loop for potential multi-turn

            else:
                # ── Non-streaming path: batch response ──
                response = await llm.chat(messages, system=None)

                if response.content:
                    print(response.content)

                if not response.has_tool_calls:
                    messages.append({"role": "assistant", "content": response.content})
                    break

                # 有工具调用 → 执行
                assistant_msg = {"role": "assistant", "content": response.content or ""}
                tool_call_msgs = []
                tool_results = []

                for tc in response.tool_calls:
                    print(f"\n  [Tool] {tc.name}({str(tc.arguments)[:80]})"
                          if len(str(tc.arguments)) > 80
                          else f"\n  [Tool] {tc.name}({tc.arguments})")

                    # 执行工具 (带安全检查)
                    result_msg = await execute_tool_safe(tc)
                    tool_call_msgs.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": str(tc.arguments),
                        },
                    })

                    import json as _json
                    try:
                        result_data = _json.loads(result_msg["content"])
                        # 截断长结果
                        result_str = _json.dumps(result_data, ensure_ascii=False, default=str)
                        if len(result_str) > 500:
                            result_str = result_str[:500] + "..."
                        print(f"     -> {result_str}")
                    except Exception:
                        print(f"     -> {str(result_msg)[:200]}")

                    tool_results.append(result_msg)

                assistant_msg["tool_calls"] = tool_call_msgs
                messages.append(assistant_msg)
                messages.extend(tool_results)

        # 记忆存储
        if turn > 0:
            memory.store(
                f"对话: {user_input[:200]}",
                level="episodic",
                importance=0.5,
                source="brain",
            )

        # 压缩长历史
        if len(messages) > 30:
            messages = [messages[0]] + messages[-20:]

    memory.close()
    await llm.close()
    print("\n[Sclerotium] 生命体休眠。")


def run_console():
    """Entry point for 'sclerotium' CLI command (pip install -e .)."""
    asyncio.run(run())


if __name__ == "__main__":
    run_console()
