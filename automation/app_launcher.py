"""App Launcher — 应用启动器 + 文件/URL 打开。

章鱼触手的"伸手"动作 — 启动程序、打开文件、打开 URL。

使用方式:
    launcher = AppLauncher()
    result = launcher.open("notepad.exe")
    result = launcher.open_url("https://github.com")
    result = launcher.open_file("C:\\Users\\me\\document.pdf")
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.launcher")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LaunchResult:
    """启动结果 (不可变)。"""
    success: bool
    target: str = ""
    process_id: int = 0
    status: str = ""           # "launched" / "already_running" / "error" / "not_found"
    error: str = ""
    launched_at: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# 常用应用映射
# ═══════════════════════════════════════════════════════════════

# 常用应用名 → 可执行文件/命令
_COMMON_APPS: dict[str, list[str]] = {
    "vscode": ["code", "code.cmd"],
    "visual studio code": ["code", "code.cmd"],
    "notepad": ["notepad.exe"],
    "记事本": ["notepad.exe"],
    "notepad++": ["notepad++.exe"],
    "calculator": ["calc.exe"],
    "计算器": ["calc.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "explorer": ["explorer.exe"],
    "资源管理器": ["explorer.exe"],
    "task manager": ["taskmgr.exe"],
    "任务管理器": ["taskmgr.exe"],
    "paint": ["mspaint.exe"],
    "画图": ["mspaint.exe"],
    "snipping tool": ["SnippingTool.exe"],
    "截图工具": ["SnippingTool.exe"],
    "wordpad": ["write.exe"],
    "写字板": ["write.exe"],
    "control panel": ["control.exe"],
    "控制面板": ["control.exe"],
    "chrome": ["chrome.exe", "google-chrome"],
    "firefox": ["firefox.exe"],
    "edge": ["msedge.exe"],
    "terminal": ["wt.exe", "WindowsTerminal.exe"],
    "终端": ["wt.exe"],
}


class AppLauncher:
    """跨平台应用和文件启动器。

    使用方式:
        launcher = AppLauncher()
        result = launcher.open("notepad")
        result = launcher.open("C:\\path\\to\\file.txt")
        result = launcher.open_url("https://example.com")
    """

    def __init__(self) -> None:
        self._launch_history: list[LaunchResult] = []
        self._running_processes: dict[int, subprocess.Popen] = {}

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def open(
        self,
        target: str,
        args: list[str] | None = None,
        working_dir: str | None = None,
    ) -> LaunchResult:
        """打开应用或文件。

        Args:
            target: 应用名 (如 "notepad")、可执行文件路径、或文件路径
            args: 命令行参数
            working_dir: 工作目录

        策略 (Windows):
          1. 已知应用 → 直接启动
          2. 未知应用 → where 搜索 → 找到则启动
          3. 仍然未知 → os.startfile() 让 Windows 自动处理
        """
        args = args or []
        resolved = self._resolve_app_name(target)

        # Strategy: use os.startfile for best Windows compatibility
        if platform.system() == "Windows":
            try:
                os.startfile(resolved)
                # os.startfile doesn't return PID, estimate
                result = LaunchResult(
                    success=True, target=target,
                    process_id=0, status="launched",
                )
                self._record(result)
                return result
            except FileNotFoundError:
                # Try dynamic search via 'where'
                found = self._dynamic_find(target)
                if found:
                    try:
                        os.startfile(found)
                        return LaunchResult(success=True, target=target, process_id=0, status="launched")
                    except Exception:
                        pass
                # Last resort: subprocess
                pass
            except Exception:
                pass

        # Fallback: subprocess
        cmd = [resolved] + args
        try:
            proc = subprocess.Popen(
                cmd, cwd=working_dir,
                shell=True if platform.system() == "Windows" else False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self._running_processes[proc.pid] = proc
            result = LaunchResult(success=True, target=target, process_id=proc.pid, status="launched")
            self._record(result)
            return result
        except FileNotFoundError:
            result = LaunchResult(success=False, target=target, status="not_found",
                                   error=f"Application not found: {target}")
            self._record(result)
            return result
        except Exception as e:
            result = LaunchResult(success=False, target=target, status="error", error=str(e))
            self._record(result)
            return result

    @staticmethod
    def _dynamic_find(name: str) -> str | None:
        """动态搜索应用: where → dir 扫描 Program Files → 注册表查询"""
        # 1. where command
        try:
            r = subprocess.run(["where", name], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip().split("\n")[0].strip()
        except Exception:
            pass
        # 2. Search Program Files
        for base in [os.environ.get("ProgramFiles", "C:\\Program Files"),
                     os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")]:
            try:
                pattern = f'"{base}\\*{name}*.exe"'
                r = subprocess.run(f'dir /s /b {pattern} 2>nul', shell=True, capture_output=True, text=True, timeout=10)
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip().split("\n")[0].strip()
            except Exception:
                pass
        return None

    def open_url(self, url: str) -> LaunchResult:
        """在默认浏览器中打开 URL。"""
        import webbrowser
        try:
            webbrowser.open(url)
            result = LaunchResult(
                success=True,
                target=url,
                status="opened",
            )
        except Exception as e:
            result = LaunchResult(
                success=False,
                target=url,
                status="error",
                error=str(e),
            )
        self._record(result)
        return result

    def open_file(self, path: str) -> LaunchResult:
        """用默认关联程序打开文件。

        Args:
            path: 文件路径
        """
        if not os.path.exists(path):
            return LaunchResult(
                success=False,
                target=path,
                status="not_found",
                error=f"File not found: {path}",
            )

        if platform.system() == "Windows":
            try:
                os.startfile(path)
                result = LaunchResult(
                    success=True,
                    target=path,
                    status="opened",
                )
                self._record(result)
                return result
            except Exception as e:
                return LaunchResult(
                    success=False,
                    target=path,
                    status="error",
                    error=str(e),
                )

        return self.open(path)

    def open_with(
        self,
        file_path: str,
        app: str,
    ) -> LaunchResult:
        """用指定应用打开文件。

        如: open_with("report.pdf", "chrome")
        """
        return self.open(app, args=[file_path])

    def is_running(self, pid: int) -> bool:
        """检查指定 PID 的进程是否仍在运行。"""
        if pid in self._running_processes:
            proc = self._running_processes[pid]
            return proc.poll() is None
        try:
            import psutil
            return psutil.pid_exists(pid)
        except Exception:
            return False

    def terminate(self, pid: int) -> bool:
        """终止指定 PID 的进程。"""
        if pid in self._running_processes:
            try:
                self._running_processes[pid].terminate()
                del self._running_processes[pid]
                return True
            except Exception:
                pass
        try:
            import psutil
            psutil.Process(pid).terminate()
            return True
        except Exception:
            return False

    def get_history(self, limit: int = 20) -> list[LaunchResult]:
        """获取启动历史。"""
        return self._launch_history[-limit:]

    def clear_history(self) -> None:
        """清空历史。"""
        self._launch_history.clear()

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _resolve_app_name(self, name: str) -> str:
        """将应用名解析为可执行文件路径。"""
        name_lower = name.lower().strip()

        # 直接匹配常用应用
        if name_lower in _COMMON_APPS:
            for candidate in _COMMON_APPS[name_lower]:
                # 检查是否在 PATH 中
                if self._which(candidate):
                    return candidate
            # 返回首选名
            return _COMMON_APPS[name_lower][0]

        # 带 .exe 后缀
        if name_lower.endswith(".exe"):
            return name

        return name

    @staticmethod
    def _which(program: str) -> str | None:
        """检查程序是否在系统 PATH 中 (类 Unix which)。"""
        if os.path.isabs(program) and os.path.exists(program):
            return program

        path_ext = os.environ.get("PATHEXT", ".EXE;.CMD;.BAT")
        exts = path_ext.split(";")

        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            base = os.path.join(path_dir, program)
            # 先试直接路径
            if os.path.exists(base):
                return base
            # 再加扩展名
            for ext in exts:
                candidate = base + ext.lower()
                if os.path.exists(candidate):
                    return candidate

        return None

    def _record(self, result: LaunchResult) -> None:
        """记录启动历史。"""
        self._launch_history.append(result)
        if len(self._launch_history) > 500:
            self._launch_history = self._launch_history[-500:]
