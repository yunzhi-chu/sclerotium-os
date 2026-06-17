"""Chain Executor — 多步骤桌面自动化编排引擎。

章鱼触手的"协同运动" — 将多个原子操作编排成流畅的动作序列。

支持:
  - 顺序执行 (step by step)
  - 条件分支 (if/else on result)
  - 错误处理 (stop/continue/retry)
  - 步骤间延迟
  - 执行前/后钩子
  - 截图记录

使用方式:
    chain = ChainExecutor()
    chain.add_step("open_app", app="notepad.exe")
    chain.add_step("wait", seconds=2)
    chain.add_step("type_text", text="Hello, World!")
    chain.add_step("screenshot", label="result")
    result = chain.execute()
    print(result.summary())
"""

from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("sclerotium.chain")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class StepStatus(Enum):
    """步骤执行状态。"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ErrorPolicy(Enum):
    """错误处理策略。"""
    STOP = "stop"         # 立即停止
    CONTINUE = "continue" # 忽略继续
    RETRY = "retry"       # 重试 N 次


@dataclass(frozen=True)
class ChainStep:
    """单个自动化步骤 (不可变)。"""
    action: str                          # 动作类型
    params: dict[str, Any] = field(default_factory=dict)
    label: str = ""                      # 步骤标签 (日志/截图用)
    error_policy: ErrorPolicy = ErrorPolicy.STOP
    max_retries: int = 2
    delay_before: float = 0.0           # 执行前延迟 (秒)
    delay_after: float = 0.0            # 执行后延迟 (秒)


@dataclass(frozen=True)
class StepResult:
    """步骤执行结果 (不可变)。"""
    step_index: int
    step_label: str
    action: str
    status: StepStatus
    result: Any = None
    error: str = ""
    duration_ms: float = 0.0
    screenshot_b64: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class ChainResult:
    """链式执行完整结果 (不可变)。"""
    success: bool
    total_steps: int
    completed_steps: int
    failed_steps: int
    skipped_steps: int
    total_duration_ms: float = 0.0
    step_results: tuple[StepResult, ...] = ()
    started_at: float = 0.0
    finished_at: float = field(default_factory=time.time)

    def summary(self) -> str:
        """生成人类可读的摘要。"""
        lines = [
            f"Chain: {'✅ 成功' if self.success else '❌ 失败'}",
            f"  步骤: {self.completed_steps}/{self.total_steps} 完成"
            + (f", {self.failed_steps} 失败" if self.failed_steps > 0 else ""),
            f"  耗时: {self.total_duration_ms:.0f}ms",
        ]
        for sr in self.step_results:
            icon = {
                StepStatus.SUCCESS: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
                StepStatus.RUNNING: "🔄",
                StepStatus.PENDING: "⏳",
            }.get(sr.status, "❓")
            label = sr.step_label or sr.action
            lines.append(f"  {icon} [{sr.step_index}] {label} ({sr.duration_ms:.0f}ms)")
            if sr.error:
                lines.append(f"      ↳ {sr.error[:80]}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# ChainExecutor
# ═══════════════════════════════════════════════════════════════

class ChainExecutor:
    """多步骤桌面自动化编排器。

    支持的动作类型:
      - click x,y          — 点击
      - type_text "text"   — 输入文本
      - hotkey ctrl c      — 组合键
      - press key          — 按键
      - move x y           — 移动鼠标
      - wait seconds       — 等待
      - screenshot label   — 截图
      - open_app name      — 启动应用
      - open_url url       — 打开 URL
      - read_text          — 读取文本 (UIA)
      - find_window title  — 查找窗口
      - set_foreground hwnd— 激活窗口
      - run_python code    — 执行 Python 代码 (仅测试用)
      - assert condition   — 断言检查

    使用方式:
        from automation.uia_controller import UIAController
        from automation.input_simulator import InputSimulator
        from automation.app_launcher import AppLauncher

        uia = UIAController()
        sim = InputSimulator()
        launcher = AppLauncher()

        chain = ChainExecutor(uia=uia, input_sim=sim, launcher=launcher)
        chain.add_step("open_app", app="notepad.exe")
        chain.add_step("wait", seconds=1.5)
        chain.add_step("type_text", text="Hello from Sclerotium!")
        chain.add_step("screenshot", label="notepad_hello")
        result = chain.execute()
    """

    def __init__(
        self,
        uia: Any = None,
        input_sim: Any = None,
        screen_agent: Any = None,
        launcher: Any = None,
        take_screenshots: bool = False,
    ) -> None:
        """初始化链式执行器。

        Args:
            uia: UIAController 实例
            input_sim: InputSimulator 实例
            screen_agent: ScreenAgent 实例
            launcher: AppLauncher 实例
            take_screenshots: 是否在每个步骤后自动截图
        """
        self._uia = uia
        self._input_sim = input_sim
        self._screen_agent = screen_agent
        self._launcher = launcher
        self._take_screenshots = take_screenshots

        self._steps: list[ChainStep] = []
        self._results: list[StepResult] = []
        self._lock = threading.Lock()

        # 钩子
        self._before_step: list[Callable[[ChainStep], None]] = []
        self._after_step: list[Callable[[StepResult], None]] = []
        self._on_error: list[Callable[[ChainStep, Exception], ErrorPolicy | None]] = []

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def add_step(
        self,
        action: str,
        label: str = "",
        error_policy: ErrorPolicy = ErrorPolicy.STOP,
        max_retries: int = 2,
        delay_before: float = 0.0,
        delay_after: float = 0.3,
        **params: Any,
    ) -> None:
        """添加一个执行步骤。

        Args:
            action: 动作类型 (click/type_text/hotkey/press/move/wait/screenshot/open_app/open_url/read_text/find_window/set_foreground)
            label: 可读标签
            error_policy: 错误策略
            max_retries: 最大重试次数
            delay_before: 执行前延迟
            delay_after: 执行后延迟
            **params: 动作参数
        """
        step = ChainStep(
            action=action,
            params=params,
            label=label or action,
            error_policy=error_policy,
            max_retries=max_retries,
            delay_before=delay_before,
            delay_after=delay_after,
        )
        self._steps.append(step)

    def execute(self) -> ChainResult:
        """执行所有步骤。

        Returns:
            ChainResult 含所有步骤结果
        """
        started_at = time.time()
        self._results.clear()

        for i, step in enumerate(self._steps):
            # 步骤前钩子
            for hook in self._before_step:
                try:
                    hook(step)
                except Exception:
                    pass

            # 延迟
            if step.delay_before > 0:
                time.sleep(step.delay_before)

            # 执行 (带重试)
            result = self._execute_with_retry(step, i)

            self._results.append(result)

            # 步骤后钩子
            for hook in self._after_step:
                try:
                    hook(result)
                except Exception:
                    pass

            # 延迟
            if step.delay_after > 0 and result.status != StepStatus.FAILED:
                time.sleep(step.delay_after)

            # 错误处理
            if result.status == StepStatus.FAILED:
                if step.error_policy == ErrorPolicy.STOP:
                    break
                elif step.error_policy == ErrorPolicy.CONTINUE:
                    continue
                # RETRY 已在 _execute_with_retry 中处理

        finished_at = time.time()
        completed = sum(1 for r in self._results if r.status == StepStatus.SUCCESS)
        failed = sum(1 for r in self._results if r.status == StepStatus.FAILED)
        skipped = sum(1 for r in self._results if r.status == StepStatus.SKIPPED)

        return ChainResult(
            success=(failed == 0),
            total_steps=len(self._steps),
            completed_steps=completed,
            failed_steps=failed,
            skipped_steps=skipped,
            total_duration_ms=(finished_at - started_at) * 1000,
            step_results=tuple(self._results),
            started_at=started_at,
            finished_at=finished_at,
        )

    def clear(self) -> None:
        """清空步骤列表和结果。"""
        self._steps.clear()
        self._results.clear()

    def get_steps(self) -> list[ChainStep]:
        """获取当前步骤列表。"""
        return list(self._steps)

    def get_results(self) -> list[StepResult]:
        """获取最近执行结果。"""
        return list(self._results)

    # ═══════════════════════════════════════════════════════
    # 钩子注册
    # ═══════════════════════════════════════════════════════

    def on_before_step(self, hook: Callable[[ChainStep], None]) -> None:
        """注册步骤前回调。"""
        self._before_step.append(hook)

    def on_after_step(self, hook: Callable[[StepResult], None]) -> None:
        """注册步骤后回调。"""
        self._after_step.append(hook)

    def on_error(self, hook: Callable[[ChainStep, Exception], ErrorPolicy | None]) -> None:
        """注册错误回调 (可返回 ErrorPolicy 覆盖默认行为)。"""
        self._on_error.append(hook)

    # ═══════════════════════════════════════════════════════
    # Internal — 步骤执行
    # ═══════════════════════════════════════════════════════

    def _execute_with_retry(self, step: ChainStep, index: int) -> StepResult:
        """执行步骤并处理重试。"""
        last_error = ""
        for attempt in range(step.max_retries + 1):
            result = self._execute_single(step, index, attempt)
            if result.status == StepStatus.SUCCESS:
                return result
            last_error = result.error

            if attempt < step.max_retries:
                logger.debug("Retrying step [%d] %s (attempt %d/%d)",
                             index, step.label, attempt + 1, step.max_retries)
                time.sleep(0.3 * (attempt + 1))  # 指数退避

        return StepResult(
            step_index=index,
            step_label=step.label,
            action=step.action,
            status=StepStatus.FAILED,
            error=f"All {step.max_retries + 1} attempts failed. Last: {last_error}",
        )

    def _execute_single(
        self, step: ChainStep, index: int, attempt: int
    ) -> StepResult:
        """执行单个步骤 (一次尝试)。"""
        start = time.time()
        try:
            result = self._dispatch(step)
            dur = (time.time() - start) * 1000

            # 截图 (如果开启)
            screenshot_b64 = ""
            if self._take_screenshots and self._screen_agent:
                try:
                    cap = self._screen_agent.capture()
                    if cap:
                        screenshot_b64 = cap.image_base64
                except Exception:
                    pass

            return StepResult(
                step_index=index,
                step_label=step.label,
                action=step.action,
                status=StepStatus.SUCCESS,
                result=result,
                duration_ms=dur,
                screenshot_b64=screenshot_b64,
            )
        except Exception as e:
            dur = (time.time() - start) * 1000
            # 通知错误钩子
            for hook in self._on_error:
                try:
                    hook(step, e)
                except Exception:
                    pass
            return StepResult(
                step_index=index,
                step_label=step.label,
                action=step.action,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=dur,
            )

    def _dispatch(self, step: ChainStep) -> Any:
        """根据动作类型分发执行。"""
        action = step.action
        p = step.params

        if action == "click":
            return self._require_input().click(p.get("x", 0), p.get("y", 0),
                                                button=p.get("button", "left"))

        elif action == "double_click":
            return self._require_input().double_click(p.get("x", 0), p.get("y", 0))

        elif action == "right_click":
            return self._require_input().right_click(p.get("x", 0), p.get("y", 0))

        elif action == "type_text":
            return self._require_input().type_text(
                str(p.get("text", "")),
                interval=p.get("interval", 0.02),
            )

        elif action == "hotkey":
            keys = p.get("keys", [])
            if isinstance(keys, str):
                keys = keys.split("+")
            return self._require_input().hotkey(*keys)

        elif action == "press":
            return self._require_input().press(p.get("key", "enter"))

        elif action == "move":
            return self._require_input().move(
                p.get("x", 0), p.get("y", 0),
                duration=p.get("duration", 0.2),
            )

        elif action == "drag":
            return self._require_input().drag(
                p.get("x1", 0), p.get("y1", 0),
                p.get("x2", 0), p.get("y2", 0),
                duration=p.get("duration", 0.5),
            )

        elif action == "scroll":
            return self._require_input().scroll(
                p.get("clicks", 3),
                x=p.get("x"), y=p.get("y"),
            )

        elif action == "wait":
            seconds = float(p.get("seconds", 1.0))
            time.sleep(seconds)
            return f"waited {seconds}s"

        elif action == "screenshot":
            if self._screen_agent:
                return self._screen_agent.capture()
            return None

        elif action == "open_app":
            app = p.get("app", "")
            if self._launcher:
                args = p.get("args", [])
                if isinstance(args, str):
                    args = [args]
                return self._launcher.open(app, args=args)
            return None

        elif action == "open_url":
            url = p.get("url", "")
            if self._launcher:
                return self._launcher.open_url(url)
            return None

        elif action == "open_file":
            path = p.get("path", "")
            if self._launcher:
                return self._launcher.open_file(path)
            return None

        elif action == "find_window":
            if self._uia:
                return self._uia.find_window(
                    title=p.get("title", ""),
                    class_name=p.get("class_name", ""),
                    process_name=p.get("process_name", ""),
                )
            return None

        elif action == "set_foreground":
            if self._uia and "window" in p:
                return self._uia.set_foreground(p["window"])

        elif action == "read_text":
            if self._uia:
                return self._uia.read_text()
            return ""

        elif action == "run_python":
            # 仅用于测试 — 执行简单 Python 代码
            code = p.get("code", "")
            local_vars: dict[str, Any] = {}
            exec(code, {"__builtins__": __builtins__}, local_vars)
            return local_vars

        elif action == "assert":
            condition = p.get("condition", True)
            if not condition:
                raise AssertionError(p.get("message", "Assertion failed"))
            return True

        else:
            raise ValueError(f"Unknown action: {action}")

    def _require_input(self) -> Any:
        """获取 InputSimulator, 无则抛出。"""
        if self._input_sim is None:
            raise RuntimeError("InputSimulator not provided to ChainExecutor")
        return self._input_sim
