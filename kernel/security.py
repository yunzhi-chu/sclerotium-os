"""安全审计层 — 命令注入防御 + 路径沙箱 + 输入校验。

供 bash_tool / chat.py / scheduler_mcp / file_ops 共用。
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

# ═══════════════════════════════════════════════════════════════════
# 命令注入：黑名单模式
# ═══════════════════════════════════════════════════════════════════

# BLOCKED: 命中即拒绝（不可绕过）
BLOCKED_PATTERNS: list[str] = [
    # 极端系统破坏
    r'rm\s+-rf\s+/\s*\*?',
    r'>\s*/dev/sda',
    r'mkfs\.',
    r'dd\s+if=/dev/zero\s+of=/dev',
    r'chmod\s+-R\s+777\s+/',
    r':\(\)\s*\{\s*:\|:&\s*\};:',
    # 远程下载+执行
    r'curl\s+.*\b(?:sh|bash|powershell|pwsh)\s*[|\|]',
    r'wget\s+-O\s*-?\s+.*\s*[|\|]\s*(?:sh|bash|powershell)',
    r'curl\s+.*\||\|\s*curl\s+',
    # 危险命令注入
    r'\$\((?:curl|wget)\s+',  # $(curl ...) / $(wget ...)
    r'`(?:curl|wget)\s+',    # `curl ...` / `wget ...`
    # 系统破坏
    r'\bshutdown\b',
    r'\breboot\b',
    r'\bformat\s+[a-z]:',
    r'\bdeltree\b',
    r'\brd\s+/[sS]\s+[/\\]',
    # 编码/PowerShell 常见注入
    r'powershell\s+.*-EncodedCommand',
    r'powershell\s+.*-Command\s+.*(?:DownloadString|Invoke-Expression|IEX)',
    r'certutil\s+-decode',
    r'base64\s+.*--decode\s+.*\|',
]

# DANGEROUS: 命中时警告 + 保留日志，但不阻止
DANGEROUS_PATTERNS: list[str] = [
    r'rm\s+-rf\s+~',
    r'sudo\s+rm',
    r'git\s+push\s+--force',
    r'DROP\s+(?:TABLE|DATABASE)',
]


def validate_command(command: str) -> dict[str, Any]:
    """检查 shell 命令是否包含恶意模式。

    Returns:
        {"pass": True} 或
        {"pass": False, "reason": "...", "pattern": "..."}
    """
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return {
                "pass": False,
                "reason": f"命令包含被禁止的模式: {pattern}",
                "pattern": pattern,
            }
    is_dangerous = any(
        re.search(p, command, re.IGNORECASE) for p in DANGEROUS_PATTERNS
    )
    return {"pass": True, "is_dangerous": is_dangerous}


# ═══════════════════════════════════════════════════════════════════
# 路径沙箱
# ═══════════════════════════════════════════════════════════════════

# 允许的根目录（项目目录 + 用户 home 的子集）
def _get_allowed_bases() -> list[Path]:
    cwd = Path.cwd().resolve()
    # 从当前文件位置推导项目根（kernel/security.py → 项目根）
    script_dir = Path(__file__).resolve().parent.parent  # kernel/ → project root
    return sorted(
        {cwd, script_dir, Path(".").resolve(), Path.home() / ".sclerotium", Path.home() / ".claude"}
    )


def check_path_safe(file_path: str, write: bool = False) -> dict[str, Any]:
    """检查文件路径是否在允许范围内。

    Returns:
        {"pass": True, "resolved": Path} 或
        {"pass": False, "error": "..."}
    """
    path_str = str(file_path).strip().strip('"').strip("'")
    if not path_str:
        return {"pass": False, "error": "路径为空"}

    try:
        p = Path(path_str).resolve()
    except Exception as e:
        return {"pass": False, "error": f"路径解析失败: {e}"}

    # 允许项目目录下任何操作
    allowed_bases = _get_allowed_bases()
    for base in allowed_bases:
        try:
            p.relative_to(base)
            return {"pass": True, "resolved": p}
        except ValueError:
            continue

    # 写操作：只允许项目目录
    if write:
        return {
            "pass": False,
            "error": f"写操作禁止在项目目录外执行: {p}",
        }

    # 读操作：允许系统临时目录和常见的公共只读位置
    tmp_dirs = [
        Path("/tmp"), Path("/var/tmp"),
        Path(os.environ.get("TEMP", "")),
        Path(os.environ.get("TMP", "")),
    ]
    for td in tmp_dirs:
        try:
            p.relative_to(td)
            return {"pass": True, "resolved": p}
        except (ValueError, RuntimeError):
            continue

    return {
        "pass": False,
        "error": f"路径不在允许范围内: {p}。允许: {', '.join(str(b) for b in allowed_bases)}",
    }
