"""Gray-box testing: 验证各种提示词下的意图检测 + 上下文构建 + 代码生成路径。

不依赖LLM API，只测试代码逻辑的正确性。
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))

PASS = 0
FAIL = 0

def t(name, fn, *args, expected=None):
    global PASS, FAIL
    try:
        r = fn(*args)
        if expected is not None:
            assert r == expected, f"Expected {expected!r}, got {r!r}"
        PASS += 1
        print(f"  [PASS] {name}")
    except Exception as e:
        FAIL += 1
        print(f"  [FAIL] {name}: {e}")

# ═══════════════════════════════════════════════════════════════
# 1. 意图检测测试
# ═══════════════════════════════════════════════════════════════

print("\n=== Intent Detection ===")

code_kw = ["写", "编写", "生成", "创建", "开发", "实现", "build", "create",
           "write", "generate", "code", "make", "implement", "script",
           "程序", "脚本", "代码", "api", "函数", "应用", "网站",
           "html", "css", "python", "javascript", "fastapi", "flask"]
search_kw = ["搜索", "查找", "查询", "最新", "新闻", "是什么", "怎么", "如何",
             "search", "find", "lookup", "what is", "how to", "latest",
             "介绍一下", "有没有", "推荐", "哪个", "区别", "对比"]
file_kw = ["看看", "查看", "读", "分析", "检查", "review", "read", "check",
           "打开", "open", "show", "显示", "内容", "文件内容"]
debug_kw = ["修复", "bug", "错误", "不工作", "坏了", "fix", "debug", "error",
            "broken", "solve", "解决", "问题", "为什么", "怎么回事"]

def detect_intent(prompt):
    p = prompt.lower()
    if any(kw in p for kw in code_kw): return "CODE"
    if any(kw in p for kw in search_kw): return "SEARCH"
    if any(kw in p for kw in file_kw): return "FILE"
    if any(kw in p for kw in debug_kw): return "DEBUG"
    return "GENERAL"

t("code: 帮我写个Python爬虫", detect_intent, "帮我写个Python爬虫", expected="CODE")
t("code: Create a FastAPI backend", detect_intent, "Create a FastAPI backend", expected="CODE")
t("code: 生成一个HTML登录页面", detect_intent, "生成一个HTML登录页面", expected="CODE")
t("code: build me a script", detect_intent, "build me a script", expected="CODE")
t("code: implement a REST API", detect_intent, "implement a REST API", expected="CODE")
t("search: Python 3.13有什么新特性", detect_intent, "Python 3.13有什么新特性", expected="SEARCH")
t("search: 搜索最新的AI论文", detect_intent, "搜索最新的AI论文", expected="SEARCH")
t("search: how to use FastAPI", detect_intent, "how to use FastAPI", expected="SEARCH")
t("file: 帮我看看这个文件", detect_intent, "帮我看看这个文件", expected="FILE")
t("file: 查看app.py的内容", detect_intent, "查看app.py的内容", expected="FILE")
t("debug: 这个bug怎么修", detect_intent, "这个bug怎么修", expected="DEBUG")
t("debug: fix the error in server.py", detect_intent, "fix the error in server.py", expected="DEBUG")
t("general: 你好", detect_intent, "你好", expected="GENERAL")
t("general: 今天天气怎么样", detect_intent, "今天天气怎么样", expected="GENERAL")

# ═══════════════════════════════════════════════════════════════
# 2. 上下文构建测试
# ═══════════════════════════════════════════════════════════════

print("\n=== Context Building ===")

from cli.tui.app import SclerotiumTUI

# 验证环境上下文能被构建
app = SclerotiumTUI()
preamble = app._build_environment_preamble()
assert "<environment>" in preamble, "Environment block missing"
assert "Windows" in preamble or "Linux" in preamble or "Darwin" in preamble, "OS not in env"
assert "Project:" in preamble, "Project path missing"
assert "Python:" in preamble, "Python version missing"
assert "Tools:" in preamble, "Tools list missing"
t("environment preamble built", lambda: len(preamble) > 100, expected=True)

# 验证完整上下文构建（需要mock tools）
print("  (Full context test requires running TUI — skipped)")

# ═══════════════════════════════════════════════════════════════
# 3. 参数别名系统测试
# ═══════════════════════════════════════════════════════════════

print("\n=== Parameter Alias System ===")

# 测试别名映射逻辑
_PARAM_ALIASES = {
    "raw": "query", "text": "query", "cmd": "command",
    "dir": "directory", "path": "file_path", "target": "file_path",
    "prompt": "query", "source": "file_path", "dest": "file_path",
    "name": "query", "value": "content", "data": "content",
    "body": "content", "code": "content",
}

def simulate_alias(args, valid_params):
    """模拟 agent_loop 的参数别名映射"""
    mapped = dict(args)
    for bad, good_candidate in _PARAM_ALIASES.items():
        if bad in mapped and bad not in valid_params:
            if good_candidate in valid_params:
                mapped[good_candidate] = mapped.pop(bad)
            else:
                val = mapped.pop(bad)
                val_str = str(val).lower()
                if val_str.startswith(("c:", "/", ".", "~")) or "\\" in val_str:
                    for c in ("file_path", "path", "pattern", "project_root", "directory"):
                        if c in valid_params:
                            mapped[c] = val
                            break
                if bad not in mapped:
                    for pname in valid_params:
                        if pname not in mapped:
                            mapped[pname] = val
                            break
    return mapped

# codebase_index accepts: project_root
r = simulate_alias({"raw": "all"}, {"project_root"})
t("alias: raw->project_root for codebase_index", lambda: r, expected={"project_root": "all"})

# codebase_files accepts: pattern, sort_by
r = simulate_alias({"file_path": "*.py"}, {"pattern", "sort_by"})
t("alias: file_path->pattern for codebase_files", lambda: "pattern" in r, expected=True)

# bash_execute accepts: command, working_dir, timeout
r = simulate_alias({"cmd": "ls"}, {"command", "working_dir", "timeout"})
t("alias: cmd->command for bash_execute", lambda: r, expected={"command": "ls"})

# git_log accepts: n (not count)
r = simulate_alias({"count": 5}, {"n", "oneline", "repo"})
t("alias: count falls to first unused", lambda: "n" in r, expected=True)

# ═══════════════════════════════════════════════════════════════
# 4. 多轮Nudge系统测试
# ═══════════════════════════════════════════════════════════════

print("\n=== Multi-Turn Nudge Logic ===")

def simulate_nudge(agent_turn, has_tool_calls):
    """模拟多轮循环的nudge决策"""
    if not has_tool_calls:
        nudges_given = agent_turn - 1
        if nudges_given < 3:
            return "NUDGE"
        return "BREAK"
    return "CONTINUE_WITH_TOOLS"

t("nudge: turn1 no tools -> nudge 1/3", simulate_nudge, 1, False, expected="NUDGE")
t("nudge: turn2 no tools -> nudge 2/3", simulate_nudge, 2, False, expected="NUDGE")
t("nudge: turn3 no tools -> nudge 3/3", simulate_nudge, 3, False, expected="NUDGE")
t("nudge: turn4 no tools -> break", simulate_nudge, 4, False, expected="BREAK")
t("nudge: turn1 has tools -> continue", simulate_nudge, 1, True, expected="CONTINUE_WITH_TOOLS")
t("nudge: turn5 has tools -> continue", simulate_nudge, 5, True, expected="CONTINUE_WITH_TOOLS")

# ═══════════════════════════════════════════════════════════════
# 5. 工具调用解析测试
# ═══════════════════════════════════════════════════════════════

print("\n=== Tool Call Parsing ===")

from kernel.agent_loop import AgentLoop
loop = AgentLoop()

# XML format
xml_input = '创建文件\n<tool_call>file_write</tool_call><file_path>test.py</file_path><content>print("hello")</content>\n文件已创建'
calls = loop._extract_tool_calls(xml_input)
t("parse XML tool call", lambda: len(calls) == 1 and calls[0]["name"] == "file_write", expected=True)
t("parse XML args", lambda: calls[0]["arguments"].get("file_path") == "test.py", expected=True)
t("parse XML content", lambda: "print" in calls[0]["arguments"].get("content", ""), expected=True)

# Markdown Calling format
md_input = 'Testing...\n**Calling:** `web_search`\n```json\n{"query": "python 3.13"}\n```\n'
calls = loop._extract_tool_calls(md_input)
t("parse Markdown tool call", lambda: len(calls) >= 1, expected=True)
t("parse Markdown name", lambda: any(c["name"] == "web_search" for c in calls), expected=True)

# Multiple tool calls
multi_input = '<tool_call>file_write</tool_call><file_path>a.py</file_path><content>1</content>\n<tool_call>file_write</tool_call><file_path>b.py</file_path><content>2</content>'
calls = loop._extract_tool_calls(multi_input)
t("parse multiple XML calls", lambda: len(calls) == 2, expected=True)
t("parse multi call names", lambda: [c["name"] for c in calls] == ["file_write", "file_write"], expected=True)

# No tool calls
plain = "Here is a response without any tool calls."
calls = loop._extract_tool_calls(plain)
t("no tool calls in plain text", lambda: len(calls) == 0, expected=True)

# ═══════════════════════════════════════════════════════════════
# 6. 代码预览提取测试
# ═══════════════════════════════════════════════════════════════

print("\n=== Code Preview ===")

import tempfile
tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
tmp.write("#!/usr/bin/env python\n\"\"\"Test module.\"\"\"\nimport os\n\ndef main():\n    pass\n")
tmp.close()

# 模拟 file_write 后的预览提取
try:
    with open(tmp.name, encoding="utf-8", errors="replace") as pf:
        first_lines = [next(pf).rstrip()[:80] for _ in range(5)]
    preview_lines = [l for l in first_lines if l]
    t("code preview extracts 5 lines", lambda: len(preview_lines) == 5, expected=True)
    t("code preview has shebang", lambda: preview_lines[0].startswith("#!/"), expected=True)
finally:
    os.unlink(tmp.name)

# ═══════════════════════════════════════════════════════════════
# Results
# ═══════════════════════════════════════════════════════════════

print(f"\n{'='*60}")
print(f"  {PASS}/{PASS+FAIL} gray-box tests passed")
if FAIL == 0:
    print("  ALL TESTS PASSED")
print(f"{'='*60}")
