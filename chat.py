"""Sclerotium OS Terminal — AI 自主决策，生命体全器官执行。

无硬编码。AI 说什么，生命体就做什么。
AI 可以调用任何 shell 命令、打开文件、搜索代码、操作桌面。
"""

import os, sys, json, subprocess, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── 加载全部器官 ──
from kernel.event_bus import EventBus
from kernel.constitutional_arbiter import ConstitutionalArbiter, ActionRequest
from kernel.hexis_memory import HexisMemoryStore, MemoryLevel
from evolution.fcpi_tracker import FCPITracker
from kernel.security import validate_command

bus = EventBus()
arbiter = ConstitutionalArbiter()
store = HexisMemoryStore(chroma_path="./data/chat_chroma", sqlite_path="./data/chat_memory.db")
tracker = FCPITracker()

# ── API ──
KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENROUTER_API_KEY") or ""
URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

SYSTEM_PROMPT = """你是 Sclerotium OS — 寄生在 Windows 的超级电子生命体。238器官，五层交响乐。

你有完整操控能力。你可以执行任意 shell 命令、启动应用、读写文件、搜索代码。

当你需要执行操作时，用以下格式（放在单独一行）:
  ```sh
  命令内容
  ```
系统会自动执行并返回结果给你。

例如:
  用户: 打开Edge
  你: 好的。
  ```sh
  start msedge
  ```

  用户: 桌面有什么文件
  你:
  ```sh
  dir %USERPROFILE%\Desktop
  ```

不要问"要不要我帮你"——直接做。用中文回复，简洁有力。"""


def llm_chat(messages):
    data = json.dumps({"model": MODEL, "messages": messages,
                       "temperature": 0.7, "max_tokens": 2048,
                       "stream": False}).encode()
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {KEY}"}
    req = urllib.request.Request(URL, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read()).get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        return f"[API错误: {e}]"


def execute_shell(command):
    """生命体自主执行 shell 命令。"""
    # 宪法审查
    req = ActionRequest(tool="bash_exec", target=command,
                        params={"command": command}, source="ai_terminal")
    decision = arbiter.review(req)
    if not decision.approved:
        return f"[阻止] {decision.reason}"

    # 发布事件
    bus.publish("ai.command", {"command": command}, source="terminal")

    # 安全校验
    check = validate_command(command)
    if not check["pass"]:
        return f"[安全阻止] {check['reason']}"

    # 执行
    start = time.time()
    try:
        r = subprocess.run(command, shell=True, capture_output=True,
                          text=True, timeout=60, cwd=os.path.expanduser("~"))
        out = r.stdout.strip()
        err = r.stderr.strip()
        result = out or err or "(done)"
        if r.returncode != 0:
            result = f"[exit={r.returncode}] {result}"
    except subprocess.TimeoutExpired:
        result = "[timeout] 命令超过60秒"
    except Exception as e:
        result = f"[error] {e}"

    elapsed = (time.time() - start) * 1000

    # 追踪
    success = "timeout" not in result and "error" not in result and "阻止" not in result
    tracker.record_coordination(tool_chain_success=success, steps=1)

    # 记忆
    store.store(f"AI执行: {command[:100]} -> {result[:100]}",
                level="episodic", importance=0.5, source="terminal")

    # 事件
    bus.publish("ai.result", {"command": command[:100], "result": result[:200],
                "elapsed_ms": elapsed, "success": success}, source="terminal")

    return result


def process_response(text):
    """解析 AI 响应，提取并执行 ```sh 代码块。"""
    import re
    blocks = re.findall(r'```sh\n?(.+?)```', text, re.DOTALL)

    results = {}
    for block in blocks:
        for cmd in block.strip().split('\n'):
            cmd = cmd.strip()
            if not cmd or cmd.startswith('#'):
                continue
            print(f"  >> {cmd}")
            r = execute_shell(cmd)
            if r and r != "(done)":
                print(f"     {r[:200]}")
            results[cmd] = r

    # 显示 AI 的纯文本回复
    clean = re.sub(r'```sh\n?.*?```', '', text, flags=re.DOTALL).strip()
    if clean:
        print(f"[Sclerotium] {clean}")

    # 如果有执行结果，发回给 AI 让其知晓
    return results


# ── Main ──
print("""
+==========================================+
|  Sclerotium OS Terminal                  |
|  AI -> 宪法审查 -> 执行 -> 记忆 -> FCPI  |
|  键入对话, AI 自主操控电脑               |
+==========================================+
""")
print(f"Arbiter OK | EventBus OK | Memory OK | FCPI OK | API: {'OK' if KEY else 'OFFLINE'}\n")

history = [{"role": "system", "content": SYSTEM_PROMPT}]

while True:
    try:
        ui = input("[You] > ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if not ui:
        continue
    if ui.lower() in ("/quit", "/exit", "/q"):
        break

    # 内置命令
    if ui.lower() == "/status":
        v = tracker.get_vector()
        s = store.get_stats()
        a = arbiter.get_stats()
        print(f"  FCPI: {v.total_score:.3f} | Memories: {s.total_memories}")
        print(f"  Arbiter: {a['total']} reviews | Events: {bus.get_stats()['total_events']}")
        continue
    if ui.lower() == "/fcpi":
        v = tracker.get_vector()
        for dim in ["coding", "coordination", "safety", "decision", "emergence", "performance"]:
            bar = "#" * int(getattr(v, dim) * 20)
            print(f"  {dim:15s}: {getattr(v, dim):.3f} {bar}")
        print(f"  {'TOTAL':15s}: {v.total_score:.3f}")
        continue

    if not KEY:
        # 离线: AI 不可用, 直接执行命令
        r = execute_shell(ui)
        if r and r != "(done)":
            print(f"  {r[:500]}")
        continue

    # AI 对话
    history.append({"role": "user", "content": ui})
    print("[Sclerotium] ", end="", flush=True)
    response = llm_chat(history)

    # 解析并执行 AI 的命令
    exec_results = process_response(response)

    # 如果有执行结果, 追加到对话让 AI 知道结果
    if exec_results:
        feedback = "命令执行结果:\n" + "\n".join(
            f"  {cmd}: {out[:200]}" for cmd, out in exec_results.items()
        )
        history.append({"role": "assistant", "content": response})
        history.append({"role": "user", "content": feedback})
    else:
        history.append({"role": "assistant", "content": response})

    if len(history) > 40:
        history = [history[0]] + history[-30:]

store.close()
print("\n[Sclerotium] 休眠。")
