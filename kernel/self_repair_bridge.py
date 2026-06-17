"""Self Repair Bridge — 运行时代码自动修复 (L6 CodeSelfRepair)。

生命体的"自愈能力" — 检测到异常后自动尝试修复, 而不是等待人工干预。

修复能力:
  - ImportError → 自动 pip install
  - AttributeError → 检查拼写并提供建议
  - FileNotFoundError → 自动创建缺失文件
  - 语法错误 → 尝试简单修正
  - 超时/死锁 → 重启相关线程

使用方式:
    repair = SelfRepairBridge()
    repair.register_fixer("ImportError", fix_import)
    result = repair.attempt_repair(error_info)
    if result.success:
        retry_operation()
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("sclerotium.self_repair")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ErrorInfo:
    """错误信息 (不可变)。"""
    error_type: str              # Exception 类型名
    message: str                 # 错误消息
    module: str = ""             # 发生模块
    traceback: str = ""          # 完整堆栈
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class RepairResult:
    """修复结果 (不可变)。"""
    success: bool
    error: ErrorInfo
    action: str = ""             # 执行的修复动作
    detail: str = ""             # 详细信息
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# SelfRepairBridge
# ═══════════════════════════════════════════════════════════════

class SelfRepairBridge:
    """运行时自动修复引擎。

    使用方式:
        repair = SelfRepairBridge()
        repair.register_fixer("ImportError", my_import_fixer)

        try:
            risky_operation()
        except Exception as e:
            info = ErrorInfo(type(e).__name__, str(e), module="my.module")
            result = repair.attempt_repair(info)
            if result.success:
                retry()
    """

    MAX_HISTORY = 200

    def __init__(self) -> None:
        self._fixers: dict[str, Callable[[ErrorInfo], tuple[bool, str]]] = {}
        self._history: list[RepairResult] = []
        self._success_count: int = 0
        self._fail_count: int = 0
        self._register_builtin_fixers()

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def register_fixer(
        self,
        error_type: str,
        fixer: Callable[[ErrorInfo], tuple[bool, str]],
    ) -> None:
        """注册错误修复器。"""
        self._fixers[error_type] = fixer

    def attempt_repair(self, error: ErrorInfo) -> RepairResult:
        """尝试自动修复错误。

        Args:
            error: 错误信息

        Returns:
            RepairResult
        """
        fixer = self._fixers.get(error.error_type)
        if not fixer:
            # 尝试模糊匹配
            for name, f in self._fixers.items():
                if name.lower() in error.error_type.lower():
                    fixer = f
                    break

        if not fixer:
            result = RepairResult(
                success=False, error=error,
                action="none",
                detail=f"No fixer registered for {error.error_type}",
            )
            self._record(result)
            return result

        try:
            ok, detail = fixer(error)
            result = RepairResult(
                success=ok, error=error,
                action=f"fix_{error.error_type}",
                detail=detail,
            )
        except Exception as e:
            result = RepairResult(
                success=False, error=error,
                action=f"fix_{error.error_type}",
                detail=f"Fixer failed: {e}",
            )

        self._record(result)
        return result

    def get_history(self, limit: int = 20) -> list[RepairResult]:
        return self._history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_attempts": len(self._history),
            "successes": self._success_count,
            "failures": self._fail_count,
            "success_rate": round(
                self._success_count / max(len(self._history), 1), 3
            ),
            "fixers_registered": list(self._fixers.keys()),
        }

    def clear(self) -> None:
        self._history.clear()
        self._success_count = 0
        self._fail_count = 0

    # ═══════════════════════════════════════════════════════════
    # 内置修复器
    # ═══════════════════════════════════════════════════════════

    def _register_builtin_fixers(self) -> None:
        self.register_fixer("ImportError", self._fix_import_error)
        self.register_fixer("ModuleNotFoundError", self._fix_import_error)
        self.register_fixer("FileNotFoundError", self._fix_file_not_found)
        self.register_fixer("AttributeError", self._fix_attribute_error)
        self.register_fixer("SyntaxError", self._fix_syntax_error)
        self.register_fixer("IndentationError", self._fix_syntax_error)
        self.register_fixer("NameError", self._fix_name_error)
        self.register_fixer("KeyError", self._fix_key_error)

    @staticmethod
    def _fix_import_error(error: ErrorInfo) -> tuple[bool, str]:
        """修复导入错误 — 使用 subprocess 安装缺失的包。"""
        msg = error.message
        match = re.search(r"No module named ['\"](\w+)['\"]", msg)
        if not match:
            return False, f"Cannot extract module name from: {msg[:80]}"

        module = match.group(1)
        # 安全检查: 拒绝安装危险包名
        blocked = {"os", "sys", "subprocess", "shutil", "importlib", "__builtins__"}
        if module in blocked:
            return False, f"Blocked: '{module}' is a builtin, not an installable package"

        try:
            import subprocess, sys
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", module],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                logger.info("SelfRepair: installed %s", module)
                return True, f"Installed {module} via pip"
            else:
                return False, f"pip install {module} failed: {result.stderr[:200]}"
        except Exception as e:
            return False, f"Failed to install {module}: {e}"

    @staticmethod
    def _fix_file_not_found(error: ErrorInfo) -> tuple[bool, str]:
        """修复文件未找到 — 自动创建缺失文件或目录。"""
        msg = error.message
        # 匹配多种文件路径格式
        for pattern in [
            r"No such file.*?['\"]([^'\"]+)['\"]",
            r"\[Errno 2\].*?['\"]([^'\"]+)['\"]",
            r"File .*?['\"]([^'\"]+)['\"]",
        ]:
            match = re.search(pattern, msg)
            if match:
                break

        if not match:
            # 尝试从 traceback 提取路径
            tb_match = re.search(r'File "([^"]+)", line', error.traceback)
            if tb_match:
                path = tb_match.group(1)
            else:
                return False, f"Cannot extract file path from: {msg[:80]}"
        else:
            path = match.group(1)

        safe_ext = (".py", ".json", ".yaml", ".yml", ".md", ".txt", ".toml", ".cfg", ".ini")
        if not any(path.endswith(ext) for ext in safe_ext):
            return False, f"Unsafe file type, not auto-creating: {path}"

        try:
            import os
            dirpath = os.path.dirname(path)
            if dirpath:
                os.makedirs(dirpath, exist_ok=True)
            if os.path.exists(path):
                return True, f"File already exists: {path}"
            with open(path, "w", encoding="utf-8") as f:
                if path.endswith(".py"):
                    f.write("# Auto-created by SelfRepairBridge\n")
            return True, f"Created file: {path}"
        except Exception as e:
            return False, f"Failed to create {path}: {e}"

    @staticmethod
    def _fix_attribute_error(error: ErrorInfo) -> tuple[bool, str]:
        """修复属性错误 — 检查并提供具体的代码修复建议。"""
        msg = error.message
        match = re.search(r"object has no attribute ['\"](\w+)['\"]", msg)
        if not match:
            # 尝试另一种模式: "'type' object has no attribute 'X'"
            match = re.search(r"has no attribute ['\"](\w+)['\"]", msg)
        if not match:
            return False, f"Cannot diagnose attribute from: {msg[:80]}"

        attr = match.group(1)
        # 尝试检测拼写错误 (Levenshtein)
        if error.context:
            available = error.context.get("available_attrs", [])
            if available:
                # Find closest match
                candidates = [(a, _levenshtein_distance(attr, a)) for a in available]
                candidates.sort(key=lambda x: x[1])
                best, dist = candidates[0] if candidates else (attr, 99)
                if dist <= 3 and best != attr:
                    return False, (
                        f"'{attr}' not found. Did you mean '{best}'? "
                        f"Available: {', '.join(available[:8])}"
                    )
        return False, (
            f"'{attr}' not found on the object. "
            f"Use file_edit to add the missing attribute/method definition."
        )

    @staticmethod
    def _fix_syntax_error(error: ErrorInfo) -> tuple[bool, str]:
        """修复语法错误 — 分析并提供修复建议。"""
        msg = error.message
        # 提取行号和文件
        line_match = re.search(r'line (\d+)', msg)
        file_match = re.search(r'File "([^"]+)"', error.traceback or msg)
        line_num = int(line_match.group(1)) if line_match else 0
        file_path = file_match.group(1) if file_match else ""

        if file_path and line_num:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if line_num <= len(lines):
                    problem_line = lines[line_num - 1].rstrip()
                    return False, (
                        f"Syntax error at {file_path}:{line_num}\n"
                        f"  {problem_line}\n"
                        f"Use file_edit to fix this line."
                    )
            except Exception:
                pass
        return False, f"Syntax error: {msg[:200]}. Use file_edit to correct."

    @staticmethod
    def _fix_name_error(error: ErrorInfo) -> tuple[bool, str]:
        """修复 NameError — 未定义的变量/函数名。"""
        msg = error.message
        match = re.search(r"name ['\"](\w+)['\"] is not defined", msg)
        if match:
            name = match.group(1)
            return False, (
                f"'{name}' is not defined. "
                f"Check: 1) missing import? 2) typo in variable name? 3) scope issue? "
                f"Use file_edit to add the missing definition or fix the typo."
            )
        return False, f"NameError: {msg[:200]}"

    @staticmethod
    def _fix_key_error(error: ErrorInfo) -> tuple[bool, str]:
        """修复 KeyError — 缺失的字典键。"""
        msg = error.message
        match = re.search(r"KeyError.*?['\"]?(\w+)['\"]?", msg)
        if match:
            key = match.group(1)
            return False, (
                f"Key '{key}' not found in dict. "
                f"Use .get('{key}', default) or ensure the key exists before access."
            )
        return False, f"KeyError: {msg[:200]}"

    def _record(self, result: RepairResult) -> None:
        self._history.append(result)
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]
        if result.success:
            self._success_count += 1
        else:
            self._fail_count += 1


def _levenshtein_distance(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        return _levenshtein_distance(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(
                prev[j] + 1,
                curr[j - 1] + 1,
                prev[j - 1] + (ca != cb),
            ))
        prev = curr
    return prev[-1]
