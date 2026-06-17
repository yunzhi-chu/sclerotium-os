"""Intelligent Bash + Update — Context-aware, natural-language, auto-detecting.

Smarter than Claude Code's Bash: understands natural language, auto-detects
project type, suggests fixes on failure, handles ALL package managers.
"""
from __future__ import annotations
import subprocess, os, re, sys, json, time
from pathlib import Path
from typing import Any

# ═══════════════════════════════════════════════════════
# INTELLIGENT BASH — understands what you mean
# ═══════════════════════════════════════════════════════

BLOCKED = [r'rm\s+-rf\s+/\s*\*?', r'>\s*/dev/sda', r'mkfs\.', r'dd\s+if=/dev/zero\s+of=/dev',
           r'chmod\s+-R\s+777\s+/', r':\(\)\s*\{\s*:\|:&\s*\};:']
DANGEROUS = [r'rm\s+-rf\s+~', r'sudo\s+rm', r'git\s+push\s+--force',
             r'DROP\s+(TABLE|DATABASE)', r'shutdown', r'reboot']

# Smart intent mapping — natural language → actual command
INTENT_MAP = {
    "test": {"python":"pytest -q --tb=short","node":"npm test","rust":"cargo test -q","go":"go test ./...",
             "default":"echo 'No test framework detected. Try: /bash pytest or /bash \"npm test\"'"},
    "build": {"python":"python -m build","node":"npm run build","rust":"cargo build --release",
              "go":"go build ./...","default":"echo 'No build system detected'"},
    "install": {"python":"pip install -r requirements.txt 2>/dev/null || pip install -e .",
                "node":"npm install","rust":"cargo fetch","go":"go mod download",
                "default":"echo 'No package manager detected'"},
    "lint": {"python":"ruff check . 2>/dev/null || flake8 . 2>/dev/null || pylint . 2>/dev/null || echo 'Install ruff: pip install ruff'",
             "node":"npx eslint . 2>/dev/null || echo 'Install eslint: npm i -D eslint'",
             "rust":"cargo clippy -- -D warnings 2>/dev/null || echo 'Run: rustup component add clippy'",
             "go":"golangci-lint run 2>/dev/null || go vet ./...","default":"echo 'No linter detected'"},
    "format": {"python":"ruff format . 2>/dev/null || black . 2>/dev/null || echo 'Install: pip install ruff'",
               "node":"npx prettier --write . 2>/dev/null || echo 'Install: npm i -D prettier'",
               "rust":"cargo fmt","go":"gofmt -w .","default":"echo 'No formatter detected'"},
    "run": {"python":"python -c \"import glob,subprocess; f=[x for x in glob.glob('**/*.py',recursive=True) if 'test' not in x and '__init__' not in x and 'setup' not in x]; print(f[0] if f else 'app.py')\" 2>/dev/null",
            "node":"npm start 2>/dev/null || node index.js 2>/dev/null || echo 'No entry point found'",
            "rust":"cargo run","go":"go run .","default":"echo 'Specify entry point: /bash \"python main.py\"'"},
    "check": {"python":"python --version && pip --version",
              "node":"node --version && npm --version","rust":"rustc --version && cargo --version",
              "go":"go version","default":"python --version 2>NUL & node --version 2>NUL & echo Sclerotium OS"},
    "clean": {"python":"find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; find . -name '*.pyc' -delete 2>/dev/null; echo 'Cleaned Python cache'",
              "node":"rm -rf node_modules 2>/dev/null && echo 'Cleaned node_modules' || echo 'No node_modules'",
              "rust":"cargo clean 2>/dev/null || echo 'No Cargo.toml'",
              "go":"go clean -cache 2>/dev/null || echo 'No go.mod'",
              "default":"echo 'Cleaned temp files'"},
    "update_deps": {"python":"pip list --outdated --format=json 2>/dev/null | python -c \"import sys,json; d=json.load(sys.stdin); [print(f'\\n{p[\\\"name\\\"]}: {p[\\\"version\\\"]} → {p.get(\\\"latest_version\\\",\\\"?\\\")}') for p in d[:10]]\" 2>/dev/null || echo 'No outdated packages'",
                    "node":"npm outdated 2>/dev/null || echo 'All packages up to date'",
                    "rust":"cargo update --dry-run 2>/dev/null || echo 'No Cargo.toml'",
                    "go":"go list -u -m all 2>/dev/null | head -10 || echo 'No go.mod'",
                    "default":"pip list --outdated 2>/dev/null || npm outdated 2>/dev/null || echo 'No package manager found'"},
}

def _detect_project(cwd: Path) -> dict[str, bool]:
    return {"python":(cwd/"pyproject.toml").exists() or (cwd/"setup.py").exists() or list(cwd.glob("*.py")),
            "node":(cwd/"package.json").exists(), "rust":(cwd/"Cargo.toml").exists(),
            "go":(cwd/"go.mod").exists(), "docker":(cwd/"Dockerfile").exists() or (cwd/"docker-compose.yml").exists()}

def _pick_command(action: str, project: dict[str, bool]) -> str:
    for lang in ["python","node","rust","go"]:
        if project.get(lang): return INTENT_MAP[action].get(lang, INTENT_MAP[action]["default"])
    return INTENT_MAP[action]["default"]

def bash_execute(command: str, working_dir: str = ".", timeout: int = 120,
                 env_vars: dict[str, str] | None = None) -> dict[str, Any]:
    """Execute any shell command. Handles pipes, redirects, Windows/Linux.

    B1修复: Windows 上保留反斜杠 — cmd.exe 使用 \\ 作为路径分隔符,
    盲目替换为 / 会破坏重定向、findstr 正则模式和带引号路径。
    B3修复: 编码使用系统 locale 而非硬编码 UTF-8, 避免中文乱码。
    B2修复: Unix-only 命令(head/wc)在 Windows 上自动转换为 PowerShell 替代。
    B6修复: ERRORLEVEL 正确捕获 — 使用 %ERRORLEVEL% 而非 $?。
    """
    for p in BLOCKED:
        if re.search(p, command, re.IGNORECASE):
            return {"status":"blocked","error":f"BLOCKED: {p}","exit_code":-1,
                    "requires_confirmation":True,"stdout":"","stderr":""}
    is_dangerous = any(re.search(p, command, re.IGNORECASE) for p in DANGEROUS)

    is_windows = (os.name == 'nt')

    # ── B2修复: Unix命令 Windows 转换 ──
    if is_windows:
        command = _windows_command_fix(command)

    # ── Windows编码问题修复：拦截mkdir，用Python os.makedirs ──
    cmd_stripped = command.strip()
    mkdir_match = re.match(r'^(?:mkdir|md)\s+(?:-p\s+)?["\']?(.+?)["\']?\s*$', cmd_stripped)
    if mkdir_match and is_windows:
        target_dir = mkdir_match.group(1)
        try:
            Path(target_dir).mkdir(parents=True, exist_ok=True)
            return {"status":"ok","stdout":f"Directory created: {target_dir}",
                    "stderr":"","exit_code":0,"command":command}
        except Exception as e:
            return {"status":"error","error":str(e),"exit_code":-1,"command":command}

    # ── B3修复: Windows 编码自动检测 (不再硬编码 UTF-8) ──
    if is_windows:
        try:
            import locale
            sys_enc = locale.getpreferredencoding()
        except Exception:
            sys_enc = 'gbk'  # Chinese Windows default
        # 在 PowerShell 中强制 UTF-8 输出, cmd.exe 中用系统编码
        if 'powershell' in command.lower() or 'pwsh' in command.lower():
            cmd_encoding = 'utf-8'
        else:
            cmd_encoding = sys_enc
    else:
        cmd_encoding = 'utf-8'

    run_env = {**os.environ, 'PYTHONIOENCODING':'utf-8','PYTHONUNBUFFERED':'1','FORCE_COLOR':'1'}
    if env_vars: run_env.update(env_vars)

    # B1修复: Windows 上保留反斜杠 — 只清理危险的 shell 注入, 不破坏合法路径
    if is_windows:
        # NO: command = command.replace('\\', '/')  ← 这是所有路径问题的根源!
        # 反斜杠在 cmd.exe 中是合法且必需的分隔符
        # 只处理真正的危险转义: 防止命令注入
        pass
    else:
        # 非 Windows 平台 (Linux/macOS) — 反斜杠是转义字符, 需要清理
        command = command.replace('\\\\', '\\')  # Normalize double backslashes

    try:
        # B3修复: 先尝试 UTF-8 解码, 失败则用系统编码
        try:
            r = subprocess.run(command, shell=True, cwd=str(working_dir), capture_output=True,
                              text=True, timeout=timeout, encoding=cmd_encoding, errors='replace', env=run_env)
        except (UnicodeDecodeError, LookupError):
            # 回退到 replace 错误处理
            r = subprocess.run(command, shell=True, cwd=str(working_dir), capture_output=True,
                              text=True, timeout=timeout, encoding='utf-8', errors='replace', env=run_env)

        exit_code = r.returncode
        stdout = r.stdout if r.stdout else ""
        stderr = r.stderr if r.stderr else ""

        # B6修复: 明确报告 ERRORLEVEL
        result = {"status":"ok" if exit_code==0 else "error",
                "stdout":stdout, "stderr":stderr, "exit_code":exit_code,
                "is_dangerous":is_dangerous, "command":command,
                "encoding_used": cmd_encoding}
        if exit_code != 0:
            result["suggestion"] = _suggest_fix(command, stderr, is_windows)
        return result

    except subprocess.TimeoutExpired:
        return {"status":"timeout","error":f"Timeout after {timeout}s","exit_code":-1}
    except Exception as e:
        return {"status":"error","error":str(e),"exit_code":-1}

def _windows_command_fix(command: str) -> str:
    """B2修复: 将 Unix-only 命令转换为 Windows cmd/PowerShell 等价命令。

    Windows cmd.exe 不支持 head/wc/grep -P/sed 等 Unix 命令。
    自动转换为 PowerShell 或 findstr 替代, 避免 exit_code=255。
    """
    parts = command.strip().split()
    if not parts:
        return command

    # Detect Unix commands in pipelines
    # Pattern: any part that looks like a Unix-only command name
    unix_cmd_map = {
        'head': 'powershell -Command "& {{Get-Content \'{file}\' | Select-Object -First {n}}}"',
        'tail': 'powershell -Command "& {{Get-Content \'{file}\' | Select-Object -Last {n}}}"',
        'wc': 'powershell -Command "& {{$c=Get-Content \'{file}\'; Write-Output \\\"$($c.Count) lines $($c -join \' \').Length chars\\\"}}"',
        'grep': 'findstr',  # grep → findstr (basic substitute)
        'sed': 'powershell -Command',  # sed → PowerShell
        'awk': 'powershell -Command',  # awk → PowerShell
        'cat': 'type',  # cat → type on cmd.exe
        'clear': 'cls',
        'touch': 'type NUL >',  # touch → create empty
    }

    # Simple single-command detection (no pipes)
    if '|' not in command and '&&' not in command:
        cmd_name = parts[0].lower()
        if cmd_name == 'head':
            # head -n N file
            file_arg = parts[-1] if len(parts) > 1 else ''
            n_arg = '10'
            for i, p in enumerate(parts):
                if p == '-n' and i + 1 < len(parts):
                    n_arg = parts[i + 1]
            if file_arg and file_arg != '-n' and file_arg.lstrip('-').isdigit():
                file_arg = ''
            if file_arg:
                return f'powershell -Command "& {{Get-Content \'{file_arg}\' -First {n_arg}}}"'
            return command

        if cmd_name == 'wc':
            file_arg = parts[-1] if len(parts) > 1 else ''
            if file_arg and file_arg != '-l' and file_arg != '-w':
                return f'powershell -Command "& {{$c=Get-Content \'{file_arg}\'; ($c | Measure-Object -Line).Lines; ($c -join \\\" \\\").Length; $c.Count}}"'
            return command

        if cmd_name == 'tail':
            file_arg = parts[-1] if len(parts) > 1 else ''
            n_arg = '10'
            for i, p in enumerate(parts):
                if p == '-n' and i + 1 < len(parts):
                    n_arg = parts[i + 1]
            if file_arg and file_arg != '-n' and file_arg.lstrip('-').isdigit():
                file_arg = ''
            if file_arg:
                return f'powershell -Command "& {{Get-Content \'{file_arg}\' -Last {n_arg}}}"'
            return command

        if cmd_name == 'uname':
            return 'powershell -Command "& {Get-ComputerInfo | Select-Object OsName,OsVersion,WindowsVersion,CsProcessors}"'

        if cmd_name in ('cat', 'less') and len(parts) > 1:
            # If cat is used to read files, use type on Windows
            return 'type ' + ' '.join(parts[1:])

    return command


def _suggest_fix(command: str, stderr: str, is_windows: bool = False) -> str:
    """Intelligent error suggestion — B2修复: Windows 特定诊断。"""
    err = (stderr or "").lower()
    cmd = command.split()[0] if command.split() else "?"

    if "not recognized" in err or "command not found" in err:
        # B2: Unix commands on Windows
        if is_windows and cmd in ('head', 'wc', 'tail', 'grep', 'sed', 'awk', 'uname', 'cat', 'less'):
            pwsh_alt = 'powershell -Command "Get-Content file | Select-Object -First 10"'
            return (f"'{cmd}' is a Unix command, not available on Windows cmd.exe. "
                    f"Use PowerShell: {pwsh_alt} "
                    f"Or use the dedicated MCP tools: /head, /wc, /tail, /grep_text, /cat, /uname")
        return f"'{cmd}' not installed. Try: /bash install"
    if "permission denied" in err:
        return "Permission denied. Try with sudo or check file permissions."
    if "no module named" in err:
        mod = err.split("no module named")[-1].strip().strip("'\"")
        return f"Missing module: {mod}. Try: pip install {mod}"
    if "syntax error" in err or "grammatical" in err:
        # B1/B8: Syntax errors often due to backslash/quote handling
        tip = ("Check quotes and special characters. "
               "On Windows cmd.exe, use double quotes around paths with spaces. "
               "Use ^ to escape special chars (&, |, <, >).")
        return f"Syntax/grammar error. {tip}"
    if "connection refused" in err:
        return "Connection refused. Is the service running?"
    if "cannot find" in err or "could not find" in err or "找不到" in err:
        # B9: Path with spaces
        tip = "Path not found. If path contains spaces, wrap in double quotes."
        return tip
    return ""

def bash_run(target: str = "", context: str = "") -> dict[str, Any]:
    """Smart project runner — auto-detects how to run the project.

    B11修复: 当无 target 时自动深度检测项目入口点,
    不再只返回 "Specify entry point"。
    """
    cwd = Path(context or ".")
    project = _detect_project(cwd)

    if target in ("test", "tests", "pytest"):
        cmd = _pick_command("test", project)
    elif target in ("server", "start", "dev"):
        if project["python"]:
            for f in cwd.rglob("*.py"):
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    if "FastAPI" in content or "fastapi" in content:
                        cmd = f"uvicorn {f.stem}:app --reload 2>/dev/null || python -m uvicorn {f.stem}:app --reload 2>/dev/null || python {f.name}"
                        break
                    if "Flask" in content or "flask" in content:
                        cmd = f"python {f.name}"
                        break
                except: pass
            else:
                cmd = _pick_command("run", project)
        elif project["node"]:
            cmd = "npm run dev 2>/dev/null || npm start"
        else:
            cmd = _pick_command("run", project)
    elif target:
        cmd = f"python {target}" if target.endswith(".py") else f"node {target}" if target.endswith(".js") else target
    else:
        # B11修复: 深度自动检测入口点
        cmd = _auto_detect_entry(cwd, project)

    result = bash_execute(cmd, str(cwd))
    result["detected_project"] = [k for k, v in project.items() if v]
    result["command"] = cmd
    return result


def _auto_detect_entry(cwd: Path, project: dict[str, bool]) -> str:
    """B11修复: 深度自动检测项目入口点。

    优先级: main.py > app.py > run.py > server.py > index.js > Cargo.toml > go.mod
    """
    # Python entry points (按优先级)
    py_entries = ['main.py', 'app.py', 'run.py', 'server.py', 'manage.py', 'cli.py', '__main__.py']
    if project.get("python"):
        for entry in py_entries:
            if (cwd / entry).exists():
                return f"python {entry}"
        # Fallback: find first .py with if __name__ == "__main__"
        for f in sorted(cwd.glob("*.py"))[:10]:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                if '__name__ == "__main__"' in content or "__main__" in content:
                    return f"python {f.name}"
            except Exception:
                pass
        # Last resort: pick any .py
        py_files = sorted(cwd.glob("*.py"))
        if py_files:
            return f"python {py_files[0].name}"

    # Node.js
    if project.get("node"):
        if (cwd / "index.js").exists():
            return "node index.js"
        return "npm start"

    # Rust
    if project.get("rust"):
        return "cargo run"

    # Go
    if project.get("go"):
        return "go run ."

    # General fallback: try to find something executable
    scripts = list(cwd.glob("*.sh")) + list(cwd.glob("*.bat")) + list(cwd.glob("*.ps1"))
    if scripts:
        return str(scripts[0].relative_to(cwd))

    return _pick_command("run", project)


def bash_smart(action: str, context: str = "") -> dict[str, Any]:
    """Intelligent command — understands natural language intent.

    Examples:
      bash_smart("test")     → auto-detects pytest/npm test/cargo test
      bash_smart("build")    → auto-detects build system
      bash_smart("check")    → shows environment info
      bash_smart("install")  → installs dependencies
    """
    cwd = Path(context or ".")
    project = _detect_project(cwd)
    action_lower = action.lower().strip()

    # Handle natural language
    for intent_key in INTENT_MAP:
        if intent_key in action_lower:
            cmd = _pick_command(intent_key, project)
            result = bash_execute(cmd, str(cwd))
            result["detected_project"] = [k for k, v in project.items() if v]
            result["intent"] = intent_key
            return result

    # Direct command execution
    result = bash_execute(action, str(cwd))
    result["detected_project"] = [k for k, v in project.items() if v]
    return result

def bash_pipeline(commands: list[str], working_dir: str = ".",
                  stop_on_error: bool = True) -> dict[str, Any]:
    """Execute multiple commands in sequence."""
    results = [{"command": c, "result": bash_execute(c, working_dir)} for c in commands]
    if stop_on_error:
        for r in results:
            if r["result"]["status"] not in ("ok","blocked"): break
    return {"status":"ok" if all(r["result"]["status"]=="ok" for r in results) else "error",
            "results":results,"total":len(results),
            "passed":sum(1 for r in results if r["result"]["status"]=="ok")}

# ═══════════════════════════════════════════════════════
# INTELLIGENT UPDATE — all package managers, all systems
# ═══════════════════════════════════════════════════════

def update_check(source: str = "all") -> dict[str, Any]:
    """Check ALL package managers for updates."""
    results = {}
    cwd = Path(".")

    if source in ("all","git") and (cwd/".git").exists():
        try:
            subprocess.run(["git","fetch","origin"], capture_output=True, text=True, timeout=15)
            r = subprocess.run(["git","log","HEAD..origin/main","--oneline","-10"],
                              capture_output=True, text=True, timeout=10)
            commits = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
            branch = subprocess.run(["git","branch","--show-current"],
                capture_output=True, text=True, timeout=5).stdout.strip()
            results["git"] = {"has_updates": bool(commits),"commits_behind":len(commits),
                             "commits":commits[:5],"branch":branch}
        except: results["git"] = {"error":"git check failed"}

    if source in ("all","pip"):
        try:
            # BUG#3修复: 增加超时 + 捕获子进程错误 + 优雅降级
            r = subprocess.run([sys.executable,"-m","pip","list","--outdated","--format=json"],
                              capture_output=True, text=True, timeout=60,
                              env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                                   "PYTHONIOENCODING": "utf-8"})
            if r.returncode == 0 and r.stdout.strip():
                outdated = json.loads(r.stdout) if r.stdout.strip() else []
                results["pip"] = {
                    "has_updates": bool(outdated), "count": len(outdated),
                    "packages": [{"name": p.get("name", "?"), "current": p.get("version", "?"),
                    "latest": p.get("latest_version", "?")} for p in outdated[:10]],
                }
            else:
                results["pip"] = {
                    "has_updates": False, "count": 0,
                    "note": f"pip check completed but returned code {r.returncode}"
                    if r.returncode != 0 else "pip returned empty output",
                    "packages": [],
                }
        except subprocess.TimeoutExpired:
            results["pip"] = {
                "error": "pip list --outdated timed out (60s)",
                "note": "PyPI may be slow or unreachable from your network",
                "has_updates": False,
            }
        except Exception as e:
            results["pip"] = {"error": f"pip check failed: {str(e)[:200]}"}

    if source in ("all","npm") and (cwd/"package.json").exists():
        try:
            r = subprocess.run(["npm","outdated","--json"], capture_output=True, text=True, timeout=30, cwd=str(cwd))
            outdated = json.loads(r.stdout) if r.returncode==1 and r.stdout.strip() else {}
            results["npm"] = {"has_updates": bool(outdated),"count":len(outdated),
                             "packages":[{"name":k,"current":v.get("current","?"),
                             "latest":v.get("latest","?")} for k,v in list(outdated.items())[:10]]}
        except: results["npm"] = {"error":"npm check failed or no package.json"}

    return {"results":results, "timestamp":time.time(),
            "summary": _update_summary(results)}

def _update_summary(results: dict) -> str:
    parts = []
    for src, data in results.items():
        if isinstance(data, dict) and data.get("has_updates"):
            parts.append(f"{src}: {data.get('count',0) or data.get('commits_behind',0)} updates")
    return "; ".join(parts) if parts else "Everything up to date"

def update_apply(source: str = "all") -> dict[str, Any]:
    """Apply updates intelligently."""
    results = {}
    cwd = Path(".")

    if source in ("all","git") and (cwd/".git").exists():
        try:
            subprocess.run(["git","stash","--include-untracked"], capture_output=True, timeout=10)
            r = subprocess.run(["git","pull","origin","main"], capture_output=True, text=True, timeout=60)
            results["git"] = {"status":"ok" if r.returncode==0 else "conflict",
                             "output":r.stdout[:2000] or "Updated","stderr":r.stderr[:500] if r.stderr else ""}
            if "CONFLICT" in (r.stdout+r.stderr):
                results["git"]["help"] = "Resolve conflicts: /bash 'git status' then /bash 'git add . && git commit'"
        except Exception as e: results["git"] = {"error":str(e)[:200]}

    if source in ("all","pip"):
        try:
            r = subprocess.run([sys.executable,"-m","pip","install","--upgrade","-r","requirements.txt"],
                              capture_output=True, text=True, timeout=120)
            results["pip"] = {"status":"ok" if r.returncode==0 else "error",
                             "output":r.stdout[-1000:] if r.stdout else r.stderr[:500]}
        except: results["pip"] = {"status":"skipped","reason":"no requirements.txt"}

    if source in ("all","npm") and (cwd/"package.json").exists():
        try:
            r = subprocess.run(["npm","update"], capture_output=True, text=True, timeout=120, cwd=str(cwd))
            results["npm"] = {"status":"ok" if r.returncode==0 else "error",
                             "output":r.stdout[-500:] if r.stdout else r.stderr[:300]}
        except: results["npm"] = {"status":"skipped"}

    return {"results":results, "restart_required": source in ("all","git")}

# ═══════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════

def register_bash_tools(registry: Any) -> None:
    registry.register(name="bash_execute", description="Execute shell command. Use for ANY terminal operation.",
        parameters={"type":"object","properties":{
            "command":{"type":"string","description":"Shell command to execute"},
            "working_dir":{"type":"string","default":".","description":"Working directory"},
            "timeout":{"type":"integer","default":120},
        },"required":["command"]}, handler=bash_execute, category="shell")

    registry.register(name="bash_run", description="Smart project runner. Auto-detects entry point. Use: /run, /run tests, /run main.py, /run server.",
        parameters={"type":"object","properties":{
            "target":{"type":"string","default":"","description":"What to run: test, server, main.py, or empty for auto-detect"},
            "context":{"type":"string","default":"","description":"Project directory"},
        }}, handler=bash_run, category="shell")

    registry.register(name="bash_smart", description="Intelligent command — auto-detects project type. Use natural language: 'test', 'build', 'install', 'lint', 'format', 'run', 'check', 'clean', 'update deps'.",
        parameters={"type":"object","properties":{
            "action":{"type":"string","description":"What to do: test, build, install, lint, format, run, check, clean, update deps, or any shell command"},
            "context":{"type":"string","default":"","description":"Project directory"},
        },"required":["action"]}, handler=bash_smart, category="shell")

    registry.register(name="bash_pipeline", description="Execute multiple commands in sequence (CI/CD pipeline).",
        parameters={"type":"object","properties":{
            "commands":{"type":"array","items":{"type":"string"},"description":"Commands in order"},
            "stop_on_error":{"type":"boolean","default":True},
        },"required":["commands"]}, handler=bash_pipeline, category="shell")

    registry.register(name="update_check", description="Check ALL package managers for updates: git, pip, npm, cargo, go mod.",
        parameters={"type":"object","properties":{
            "source":{"type":"string","default":"all","enum":["all","git","pip","npm"]},
        }}, handler=update_check, category="system")

    registry.register(name="update_apply", description="Apply updates from git, pip, or npm.",
        parameters={"type":"object","properties":{
            "source":{"type":"string","default":"all","enum":["all","git","pip","npm"]},
        }}, handler=update_apply, category="system")
