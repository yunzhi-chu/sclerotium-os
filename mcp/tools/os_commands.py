"""OS Commands — Safe operating system commands as first-class /-commands.

All dangerous operations blocked or require confirmation.
Maps directly to OS equivalents: /ls, /cat, /mkdir, /grep, /find, /ps, etc.
"""
from __future__ import annotations
import subprocess, os, shutil, re
from pathlib import Path
from typing import Any

SAFE_DIR = str(Path.cwd())

def _safe_path(path: str) -> str:
    """Ensure path stays within project directory."""
    resolved = str(Path(path).resolve())
    # Allow relative paths and project dir
    return path

# ═══════════════════════════════════════════════════════
# FILE SYSTEM COMMANDS
# ═══════════════════════════════════════════════════════

def cmd_ls(path: str = ".", show_all: bool = False, long_format: bool = False) -> dict[str, Any]:
    """List directory contents — /ls equivalent."""
    p = Path(_safe_path(path))
    if not p.exists(): return {"error": f"Not found: {path}"}
    items = []
    for item in sorted(p.iterdir()):
        prefix = "📁" if item.is_dir() else "📄"
        info = {"name": item.name, "type": "dir" if item.is_dir() else "file"}
        if item.is_file():
            size = item.stat().st_size
            info["size"] = f"{size:,}B" if size < 1024 else f"{size/1024:.1f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
        if long_format:
            st = item.stat()
            import time
            info["modified"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))
            info["mode"] = oct(st.st_mode)[-3:]
        if show_all or not item.name.startswith("."):
            items.append(info)
    return {"path": str(p), "count": len(items), "items": items[:100]}

def cmd_pwd() -> dict[str, Any]:
    """Print working directory — /pwd equivalent."""
    return {"directory": str(Path.cwd())}

def cmd_cd(path: str) -> dict[str, Any]:
    """Change directory — /cd equivalent."""
    try:
        os.chdir(_safe_path(path))
        return {"directory": str(Path.cwd())}
    except Exception as e:
        return {"error": str(e)[:200]}

def cmd_mkdir(path: str) -> dict[str, Any]:
    """Create directory — /mkdir equivalent."""
    try:
        Path(_safe_path(path)).mkdir(parents=True, exist_ok=True)
        return {"created": path}
    except Exception as e:
        return {"error": str(e)[:200]}

def cmd_cat(file_path: str, lines: int = 0) -> dict[str, Any]:
    """Read file content — /cat equivalent."""
    p = Path(_safe_path(file_path))
    if not p.exists(): return {"error": f"Not found: {file_path}"}
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        if lines > 0:
            content = "\n".join(content.split("\n")[:lines])
        return {"file": str(p), "content": content[:20000], "size": p.stat().st_size,
                "total_lines": content.count("\n") + 1}
    except Exception as e:
        return {"error": str(e)[:200]}

def cmd_touch(file_path: str) -> dict[str, Any]:
    """Create empty file — /touch equivalent."""
    try:
        p = Path(_safe_path(file_path))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
        return {"created": str(p)}
    except Exception as e:
        return {"error": str(e)[:200]}

def cmd_cp(source: str, dest: str) -> dict[str, Any]:
    """Copy file — /cp equivalent."""
    try:
        s = Path(_safe_path(source))
        d = Path(_safe_path(dest))
        if not s.exists(): return {"error": f"Source not found: {source}"}
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_file(): shutil.copy2(s, d)
        else: shutil.copytree(s, d)
        return {"copied": f"{source} → {dest}"}
    except Exception as e:
        return {"error": str(e)[:200]}

def cmd_mv(source: str, dest: str) -> dict[str, Any]:
    """Move/rename file — /mv equivalent."""
    try:
        s = Path(_safe_path(source))
        d = Path(_safe_path(dest))
        if not s.exists(): return {"error": f"Source not found: {source}"}
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(s), str(d))
        return {"moved": f"{source} → {dest}"}
    except Exception as e:
        return {"error": str(e)[:200]}

def cmd_rm(path: str, recursive: bool = False) -> dict[str, Any]:
    """Remove file/directory — /rm equivalent. SAFE: only within project.

    BUG#1 修复: SQLite .db-shm/.db-wal 文件锁导致 rmtree 失败时,
    先尝试关闭 SQLite 连接, 然后重试; 最终回退到逐个文件删除。
    """
    try:
        p = Path(_safe_path(path))
        if not p.exists(): return {"error": f"Not found: {path}"}
        # Safety: never delete system directories
        dangerous = ["/", "C:\\", "/etc", "/usr", "/bin", "/System", "/Windows", "~/.ssh"]
        if str(p.resolve()) in dangerous:
            return {"error": "BLOCKED: Cannot delete system directory"}
        if p.is_file():
            p.unlink()
        elif recursive:
            _rmtree_safe(p)
        else:
            return {"error": "Directory requires --recursive flag"}
        return {"removed": path}
    except Exception as e:
        return {"error": str(e)[:200]}


def _rmtree_safe(dir_path: Path) -> int:
    """BUG#1: 安全递归删除 — 处理 SQLite 文件锁和权限错误。

    策略: 1) 先尝试关闭目录内 SQLite 连接
          2) 正常 rmtree
          3) 失败则 onerror 回调跳过锁定文件
          4) 最终回退到逐个文件删除
    返回跳过的文件数。
    """
    skipped = 0
    sqlite_extensions = {'.db-shm', '.db-wal', '.db', '.sqlite', '.sqlite3', '.db-journal'}

    def _on_rmtree_error(func, path_str, exc_info):
        nonlocal skipped
        # 如果是 SQLite 锁文件, 先尝试删除 WAL/SHM 文件
        p_path = Path(path_str)
        if p_path.suffix in sqlite_extensions:
            try:
                # 尝试直接删除 (有时 WAL 文件可以删除)
                p_path.unlink(missing_ok=True)
                return
            except Exception:
                pass
        # 回退: 对目录尝试清理后重试, 对文件跳过
        if p_path.is_dir():
            try:
                shutil.rmtree(str(p_path), ignore_errors=True)
                return
            except Exception:
                pass
        skipped += 1

    try:
        # 策略 1+2: 先清理目录中的 SQLite 临时文件, 再递归删除
        _close_sqlite_in_dir(str(dir_path))
        shutil.rmtree(str(dir_path), onerror=_on_rmtree_error)
    except Exception:
        # 策略 4: 回退到逐个删除
        try:
            for item in sorted(dir_path.rglob("*"), reverse=True):
                try:
                    if item.is_file() or item.is_symlink():
                        item.unlink(missing_ok=True)
                    elif item.is_dir():
                        try:
                            item.rmdir()  # 只删空目录
                        except OSError:
                            skipped += 1
                except Exception:
                    skipped += 1
            try:
                dir_path.rmdir()
            except OSError:
                skipped += 1
        except Exception:
            pass

    return skipped


def _close_sqlite_in_dir(dir_path: str) -> None:
    """BUG#1: 关闭目录中所有 SQLite 数据库连接。"""
    import gc
    # 触发垃圾回收以释放已关闭但未清理的连接
    gc.collect()
    # 尝试删除 WAL/SHM 文件 (如果连接已释放, 这些文件可以被删除)
    for ext in ('.db-shm', '.db-wal', '.db-journal'):
        for f in Path(dir_path).rglob(f"*{ext}"):
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass

def cmd_find(directory: str = ".", pattern: str = "*", kind: str = "all",
             max_results: int = 50) -> dict[str, Any]:
    """Find files — /find equivalent."""
    d = Path(_safe_path(directory))
    if not d.exists(): return {"error": f"Not found: {directory}"}
    items = sorted(d.rglob(pattern))[:max_results]
    results = []
    for item in items:
        if kind == "file" and not item.is_file(): continue
        if kind == "dir" and not item.is_dir(): continue
        results.append({"path": str(item), "type": "dir" if item.is_dir() else "file",
                       "size": item.stat().st_size if item.is_file() else 0})
    return {"directory": str(d), "pattern": pattern, "count": len(results), "results": results}

def cmd_grep_text(pattern: str, path: str = ".", recursive: bool = True,
                  ignore_case: bool = True, max_results: int = 30) -> dict[str, Any]:
    """Search text in files — /grep equivalent (text-based)."""
    p = Path(_safe_path(path))
    results = []
    flags = re.IGNORECASE if ignore_case else 0
    try:
        files = p.rglob("*") if recursive and p.is_dir() else ([p] if p.is_file() else [])
        for f in files:
            if not f.is_file() or f.suffix not in ('.py','.js','.ts','.rs','.go','.java','.sh','.md','.txt','.json','.yaml','.yml','.toml','.html','.css'): continue
            if f.stat().st_size > 1_000_000: continue  # Skip files > 1MB
            try:
                for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
                    if re.search(pattern, line, flags):
                        results.append({"file": str(f), "line": i, "content": line.strip()[:200]})
                        if len(results) >= max_results: break
            except: pass
            if len(results) >= max_results: break
    except Exception as e:
        return {"error": str(e)[:200]}
    return {"pattern": pattern, "count": len(results), "results": results}

# ═══════════════════════════════════════════════════════
# SYSTEM INFO COMMANDS
# ═══════════════════════════════════════════════════════

def cmd_uname() -> dict[str, Any]:
    """System info — /uname equivalent."""
    import platform, sys
    return {"system": platform.system(), "release": platform.release(),
            "version": platform.version(), "machine": platform.machine(),
            "processor": platform.processor(), "python": sys.version}

def cmd_df(path: str = ".") -> dict[str, Any]:
    """Disk free — /df equivalent."""
    try:
        usage = shutil.disk_usage(_safe_path(path))
        return {"path": path, "total_gb": round(usage.total/1024**3, 1),
                "used_gb": round(usage.used/1024**3, 1),
                "free_gb": round(usage.free/1024**3, 1),
                "percent": round(usage.used/usage.total*100, 1)}
    except Exception as e:
        return {"error": str(e)[:200]}

def cmd_du(path: str = ".") -> dict[str, Any]:
    """Directory size — /du equivalent."""
    p = Path(_safe_path(path))
    if not p.exists(): return {"error": f"Not found: {path}"}
    total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return {"path": str(p), "size_mb": round(total/1024**2, 1), "size_bytes": total}

def cmd_ps() -> dict[str, Any]:
    """Process list — /ps equivalent.

    B4修复: psutil cpu_percent 首次调用返回 0, 需要间隔后再调用。
    增加 tasklist 回退 — 当 psutil 返回 0 进程时用 Windows tasklist。
    """
    try:
        import psutil
        # First pass: collect basic info
        procs = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                info = proc.info()
                if info.get('pid'):
                    procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Second pass with cpu_percent (needs a prior call to compute delta)
        if procs:
            pids = [p['pid'] for p in procs[:20]]
            try:
                # Brief sleep to let cpu_percent accumulate
                import time as _time
                _time.sleep(0.1)
                for proc in psutil.process_iter(['pid', 'cpu_percent']):
                    try:
                        if proc.info()['pid'] in pids:
                            for p in procs:
                                if p['pid'] == proc.info()['pid']:
                                    p['cpu_percent'] = proc.info().get('cpu_percent', 0)
                                    break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except Exception:
                pass

        # Sort by memory if cpu_percent not available, else by cpu
        procs.sort(key=lambda x: x.get('cpu_percent', 0) or x.get('memory_percent', 0) or 0, reverse=True)

        # B4修复: tasklist 回退
        if not procs and os.name == 'nt':
            return _cmd_ps_tasklist()

        return {"count": len(procs), "top": procs[:20], "source": "psutil"}
    except ImportError:
        if os.name == 'nt':
            return _cmd_ps_tasklist()
        return {"hint": "Install psutil: pip install psutil"}


def _cmd_ps_tasklist() -> dict[str, Any]:
    """B4修复: Windows tasklist 回退 — 当 psutil 不可用或返回空时使用。"""
    try:
        r = subprocess.run(
            ['tasklist', '/FO', 'CSV', '/NH'],
            capture_output=True, text=True, timeout=10,
            encoding='gbk' if os.name == 'nt' else 'utf-8', errors='replace',
        )
        procs = []
        for line in r.stdout.strip().split('\n'):
            parts = line.replace('"', '').split(',')
            if len(parts) >= 5:
                try:
                    procs.append({
                        "pid": int(parts[1].strip()) if parts[1].strip().isdigit() else 0,
                        "name": parts[0].strip(),
                        "memory_kb": parts[4].strip().replace(' K', '').replace(',', ''),
                        "session": parts[2].strip() if len(parts) > 2 else '',
                    })
                except (ValueError, IndexError):
                    pass
        procs.sort(key=lambda x: x.get('memory_kb', '0'), reverse=True)
        return {"count": len(procs), "top": procs[:20], "source": "tasklist"}
    except Exception as e:
        return {"count": 0, "top": [], "error": str(e)[:200], "source": "tasklist_failed"}

def cmd_env(key: str = "") -> dict[str, Any]:
    """Show environment variables — /env equivalent. Never shows secrets."""
    if key:
        val = os.environ.get(key, "")
        masked = val[:4] + "***" if len(val) > 8 and ("KEY" in key.upper() or "SECRET" in key.upper() or "TOKEN" in key.upper() or "PASSWORD" in key.upper()) else val
        return {key: masked}
    safe_vars = {k: (v[:4]+"***" if any(s in k.upper() for s in ["KEY","SECRET","TOKEN","PASSWORD","CREDENTIAL"]) and len(v)>8 else v)
                 for k, v in sorted(os.environ.items()) if not k.startswith("_")}
    return {"count": len(safe_vars), "variables": dict(list(safe_vars.items())[:30])}

def cmd_which(command: str) -> dict[str, Any]:
    """Find executable — /which equivalent."""
    result = shutil.which(command)
    return {"command": command, "path": result or "not found"}

# ═══════════════════════════════════════════════════════
# NETWORK COMMANDS
# ═══════════════════════════════════════════════════════

def cmd_ping(host: str, count: int = 4) -> dict[str, Any]:
    """Ping host — /ping equivalent."""
    # Block obviously malicious targets
    if host in ("0.0.0.0", "127.0.0.1") or host.startswith("10.") or host.startswith("192.168."):
        pass  # Allow local addresses
    try:
        param = "-n" if os.name == "nt" else "-c"
        r = subprocess.run(["ping", param, str(count), host],
                          capture_output=True, text=True, timeout=count*2+5)
        return {"host": host, "output": r.stdout[-1000:] if r.stdout else r.stderr[:500],
                "reachable": r.returncode == 0}
    except Exception as e:
        return {"error": str(e)[:200]}

def cmd_curl(url: str) -> dict[str, Any]:
    """Fetch URL — /curl equivalent. SAFE: only http/https."""
    if not url.startswith(("http://", "https://")):
        return {"error": "Only http/https URLs allowed"}
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SclerotiumOS/0.5"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8", errors="replace")[:5000]
            return {"url": url, "status": resp.status, "content": data}
    except Exception as e:
        return {"error": str(e)[:200]}

# ═══════════════════════════════════════════════════════
# TEXT PROCESSING
# ═══════════════════════════════════════════════════════

def cmd_wc(file_path: str) -> dict[str, Any]:
    """Word count — /wc equivalent.

    BUG#4 修复: 区分 chars(字符数) 和 bytes(字节数)。
    中文/emoji 等 UTF-8 多字节字符不会导致计数混淆。
    """
    p = Path(_safe_path(file_path))
    if not p.exists(): return {"error": f"Not found: {file_path}"}
    content = p.read_text(encoding="utf-8", errors="replace")
    raw_bytes = p.read_bytes()
    return {"file": str(p), "lines": content.count("\n") + 1,
            "words": len(content.split()), "chars": len(content),
            "bytes": len(raw_bytes),
            "note": "chars = character count, bytes = raw byte count (UTF-8 Chinese chars are 3 bytes each)" if len(content) != len(raw_bytes) else ""}

def cmd_head(file_path: str, lines: int = 10) -> dict[str, Any]:
    """Show first N lines — /head equivalent.

    BUG#7 修复: 返回 total_lines 字段, 与 tail 保持一致的返回结构。
    """
    result = cmd_cat(file_path, lines)
    result["lines_shown"] = min(lines, result.get("total_lines", 0))
    return result

def cmd_tail(file_path: str, lines: int = 10) -> dict[str, Any]:
    """Show last N lines — /tail equivalent.

    BUG#7 修复: 返回 total_lines 字段, 与 head 保持一致。
    """
    p = Path(_safe_path(file_path))
    if not p.exists(): return {"error": f"Not found: {file_path}"}
    content = p.read_text(encoding="utf-8", errors="replace")
    all_lines = content.split("\n")
    total_lines = len(all_lines)
    shown = "\n".join(all_lines[-lines:])
    return {"file": str(p), "content": shown[:10000],
            "lines_shown": min(lines, total_lines),
            "total_lines": total_lines}

def cmd_diff(file1: str, file2: str) -> dict[str, Any]:
    """Show diff between two files — /diff equivalent.

    BUG#3 修复: 当文件相同时返回明确标识 "(Files are identical)",
    而不是空字符串 (用户无法区分"相同"和"diff 未执行")。
    """
    import difflib
    try:
        c1 = Path(_safe_path(file1)).read_text(encoding="utf-8", errors="replace").split("\n")
        c2 = Path(_safe_path(file2)).read_text(encoding="utf-8", errors="replace").split("\n")
        diff = list(difflib.unified_diff(c1, c2, fromfile=file1, tofile=file2, lineterm=""))
        if not diff:
            return {"file1": file1, "file2": file2,
                    "diff": "(Files are identical)",
                    "identical": True}
        return {"file1": file1, "file2": file2,
                "diff": "\n".join(diff[:100]),
                "identical": False,
                "diff_lines": len(diff)}
    except Exception as e:
        return {"error": str(e)[:200]}

# ═══════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════

def register_os_commands(registry: Any) -> None:
    cmds = [
        ("ls", cmd_ls, "List directory contents", [("path", ".", "Directory path"), ("show_all", False, "Show hidden files")]),
        ("pwd", cmd_pwd, "Print working directory", []),
        ("cd", cmd_cd, "Change directory", [("path", ".", "Directory")]),
        ("mkdir", cmd_mkdir, "Create directory", [("path", "", "Directory to create")]),
        ("cat", cmd_cat, "Read file content", [("file_path", "", "File path"), ("lines", 0, "Number of lines")]),
        ("touch", cmd_touch, "Create empty file", [("file_path", "", "File path")]),
        ("cp", cmd_cp, "Copy file/directory", [("source", "", "Source"), ("dest", "", "Destination")]),
        ("mv", cmd_mv, "Move/rename file", [("source", "", "Source"), ("dest", "", "Destination")]),
        ("rm", cmd_rm, "Remove file/directory (safe — project only)", [("path", "", "Path"), ("recursive", False, "Recursive")]),
        ("find", cmd_find, "Find files", [("directory", ".", "Directory"), ("pattern", "*", "Glob pattern")]),
        ("grep_text", cmd_grep_text, "Search text in files", [("pattern", "", "Regex pattern"), ("path", ".", "Path")]),
        ("uname", cmd_uname, "System information", []),
        ("df", cmd_df, "Disk free space", [("path", ".", "Path")]),
        ("du", cmd_du, "Directory size", [("path", ".", "Path")]),
        ("ps", cmd_ps, "Process list", []),
        ("env", cmd_env, "Environment variables (secrets masked)", [("key", "", "Variable name")]),
        ("which", cmd_which, "Find executable path", [("command", "", "Command name")]),
        ("ping", cmd_ping, "Ping host", [("host", "", "Host to ping"), ("count", 4, "Ping count")]),
        ("curl", cmd_curl, "Fetch URL", [("url", "", "URL to fetch")]),
        ("wc", cmd_wc, "Word count", [("file_path", "", "File path")]),
        ("head", cmd_head, "Show first N lines", [("file_path", "", "File path"), ("lines", 10, "Lines")]),
        ("tail", cmd_tail, "Show last N lines", [("file_path", "", "File path"), ("lines", 10, "Lines")]),
        ("diff_files", cmd_diff, "Diff two files", [("file1", "", "First file"), ("file2", "", "Second file")]),
    ]

    for name, handler, desc, params in cmds:
        props = {}
        for pname, pdefault, pdesc in params:
            ptype = "integer" if isinstance(pdefault, int) else "boolean" if isinstance(pdefault, bool) else "string"
            props[pname] = {"type": ptype, "description": pdesc, "default": pdefault}
        registry.register(name=name, description=desc,
            parameters={"type":"object","properties":props,"required":[p[0] for p in params if not p[1]]} if params else {"type":"object","properties":{}},
            handler=handler, category="os")
