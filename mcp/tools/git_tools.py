"""Git Integration — Claude Code-equivalent git commit/diff/log/blame.

Uses subprocess to call git directly. No external dependencies.
"""
from __future__ import annotations
import subprocess, os
from pathlib import Path
from typing import Any

def _is_git_repo(cwd: str) -> bool:
    """BUG-GIT#1: 检查目录是否是 Git 仓库。"""
    from pathlib import Path
    p = Path(cwd).resolve()
    # 向上搜索 .git 目录 (支持子目录调用)
    for _ in range(10):
        if (p / ".git").exists():
            return True
        parent = p.parent
        if parent == p:
            break
        p = parent
    return False


def _run_git(args: list[str], cwd: str = ".") -> dict[str, Any]:
    """BUG-GIT#1修复: 前置检查 + 结构化错误返回。"""
    # 前置检查: Git 仓库是否存在
    if not _is_git_repo(cwd):
        return {
            "status": "error",
            "success": False,
            "error_code": "NOT_A_GIT_REPO",
            "error_message": f"Directory '{Path(cwd).resolve()}' is not inside a Git repository.",
            "suggestion": "Initialize a repo with 'git init' or change to a directory that contains a .git folder.",
            "exit_code": 128,
        }

    try:
        r = subprocess.run(["git"] + args, capture_output=True, text=True,
                          cwd=cwd, timeout=30, encoding="utf-8", errors="replace")

        # BUG-GIT#4: 结构化返回
        result = {
            "success": r.returncode == 0,
            "exit_code": r.returncode,
            "stdout": r.stdout[:5000] if r.returncode == 0 else "",
            "stderr": r.stderr[:1000] if r.returncode != 0 else "",
        }

        # BUG-GIT#2: staged 选项错误诊断
        if r.returncode != 0 and "unknown option" in (r.stderr or ""):
            result["status"] = "error"
            result["error_code"] = "INVALID_OPTION"
            result["error_message"] = "Invalid git option specified."
            result["suggestion"] = "Check the git command syntax. For staged changes, use 'git diff --staged'."
        elif r.returncode != 0:
            result["status"] = "error"
            if "not a git repository" in (r.stderr or "").lower():
                result["error_code"] = "NOT_A_GIT_REPO"
                result["error_message"] = "Not inside a Git repository."
            elif "did not match any file" in (r.stderr or ""):
                result["error_code"] = "FILE_NOT_FOUND"
                result["error_message"] = "No matching files found."
            else:
                result["error_message"] = (r.stderr or "Unknown error")[:200]
        else:
            result["status"] = "ok"

        return result
    except FileNotFoundError:
        return {"status": "error", "success": False, "error_code": "GIT_NOT_INSTALLED",
                "error_message": "Git not found. Install git first.",
                "suggestion": "Download from https://git-scm.com/downloads"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "success": False, "error_code": "TIMEOUT",
                "error_message": "Git command timed out after 30 seconds."}
    except Exception as e:
        return {"status": "error", "success": False, "error_code": "UNKNOWN_ERROR",
                "error_message": str(e)[:200]}

def git_status(repo: str = ".") -> dict[str, Any]:
    return _run_git(["status", "--short"], repo)

def git_diff(staged: bool = False, file_path: str = "", repo: str = ".") -> dict[str, Any]:
    args = ["diff"]
    if staged: args.append("--staged")
    if file_path: args.append(file_path)
    return _run_git(args, repo)

def git_log(n: int = 10, oneline: bool = True, repo: str = ".") -> dict[str, Any]:
    args = ["log", f"-{n}"]
    if oneline: args.append("--oneline")
    return _run_git(args, repo)

def git_commit(message: str, files: list[str] | None = None, repo: str = ".") -> dict[str, Any]:
    args = ["commit", "-m", message]
    if files: args.extend(files)
    return _run_git(args, repo)

def git_add(files: list[str], repo: str = ".") -> dict[str, Any]:
    return _run_git(["add"] + files, repo)

def git_branch(repo: str = ".") -> dict[str, Any]:
    return _run_git(["branch", "--list"], repo)

def git_blame(file_path: str, lines: str = "", repo: str = ".") -> dict[str, Any]:
    args = ["blame", "--show-name", "--show-number"]
    if lines: args.extend(["-L", lines])
    args.append(file_path)
    return _run_git(args, repo)

def register_git_tools(registry: Any) -> None:
    for name, handler, desc, params in [
        ("git_status", git_status, "Show working tree status (git status --short)", {}),
        ("git_diff", git_diff, "Show changes (git diff). Use staged=True for staged changes.",
         {"staged": {"type": "boolean", "default": False}, "file_path": {"type": "string", "default": ""}}),
        ("git_log", git_log, "Show commit history (git log)", {"n": {"type": "integer", "default": 10}}),
        ("git_commit", git_commit, "Create a commit with message",
         {"message": {"type": "string"}, "files": {"type": "array", "items": {"type": "string"}}}),
        ("git_add", git_add, "Stage files for commit", {"files": {"type": "array", "items": {"type": "string"}}}),
        ("git_branch", git_branch, "List branches", {}),
        ("git_blame", git_blame, "Show line-by-line authorship",
         {"file_path": {"type": "string"}, "lines": {"type": "string", "default": ""}}),
    ]:
        registry.register(name=name, description=desc, parameters={
            "type": "object", "properties": params,
            "required": [k for k, v in params.items() if v.get("type") == "string" and "default" not in v]
        } if params else {"type": "object", "properties": {}}, handler=handler, category="git")
