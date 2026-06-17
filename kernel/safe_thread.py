"""SafeThread — threading.Thread 替代品, 内置异常管理 + 优雅关闭。

P1-3 fix: 系统中 30 处裸 threading.Thread 使用缺少异常处理和统一关闭协议。
SafeThread 提供:
  - 自动异常捕获和日志记录 (不再 silent death)
  - threading.Event 优雅关闭信号
  - 线程状态追踪 (started/running/stopped/error)
  - 上下文管理器支持

使用方式:
    # 替换前:
    t = threading.Thread(target=my_loop, daemon=True)
    t.start()

    # 替换后:
    t = SafeThread(name="my-loop", target=my_loop)
    t.start()
    # ...
    t.shutdown()  # 发送停止信号, 等待最多 5 秒

Target 函数签名:
    def my_loop(stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            do_work()
            stop_event.wait(1.0)  # 每秒检查一次停止信号
"""

from __future__ import annotations

import logging
import threading
import time
import traceback
from enum import Enum
from typing import Callable

logger = logging.getLogger("sclerotium.safe_thread")


class ThreadState(str, Enum):
    STARTED = "started"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class SafeThread:
    """具有内置异常处理和优雅关闭能力的线程包装器。

    与裸 threading.Thread 不同:
      - target 函数接收 threading.Event 作为第一个参数 (停止信号)
      - 未捕获异常被记录 (线程不会静默死亡)
      - shutdown() 设置停止信号 + 带超时 join
      - 线程状态可通过 .state 属性查询
    """

    def __init__(
        self,
        name: str,
        target: Callable[[threading.Event], None],
        daemon: bool = True,
        shutdown_timeout: float = 5.0,
        **kwargs,
    ) -> None:
        self.name = name
        self._target = target
        self._daemon = daemon
        self._shutdown_timeout = shutdown_timeout
        self._kwargs = kwargs
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._state = ThreadState.STARTED

    def start(self) -> None:
        """启动线程。"""
        self._thread = threading.Thread(
            target=self._run_wrapper,
            name=self.name,
            daemon=self._daemon,
        )
        self._thread.start()
        logger.debug("SafeThread %s started", self.name)

    def shutdown(self, timeout: float | None = None) -> None:
        """发送停止信号, 等待线程结束。"""
        timeout = timeout if timeout is not None else self._shutdown_timeout
        logger.debug("SafeThread %s: sending stop signal", self.name)
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("SafeThread %s did not stop within %.1fs", self.name, timeout)
            else:
                self._state = ThreadState.STOPPED
                logger.debug("SafeThread %s stopped", self.name)

    @property
    def state(self) -> ThreadState:
        return self._state

    @property
    def stop_event(self) -> threading.Event:
        return self._stop_event

    @property
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run_wrapper(self) -> None:
        """包装 target 调用, 捕获异常并更新状态。"""
        self._state = ThreadState.RUNNING
        try:
            self._target(self._stop_event, **self._kwargs)
        except Exception:
            logger.error(
                "SafeThread %s crashed:\n%s",
                self.name,
                traceback.format_exc(),
            )
            self._state = ThreadState.ERROR
        else:
            self._state = ThreadState.STOPPED

    def __enter__(self) -> SafeThread:
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.shutdown()


def safe_sleep(stop_event: threading.Event, seconds: float) -> bool:
    """可中断的 sleep — 返回 True 表示被中断。"""
    return stop_event.wait(seconds)


# ═══════════════════════════════════════════════════════════════
# Legacy compatibility: 将现有 threading.Thread(target=fn) 迁移到 SafeThread
# ═══════════════════════════════════════════════════════════════

def migrate_to_safe(
    name: str,
    target: Callable[[], None],
    daemon: bool = True,
    poll_interval: float = 1.0,
    shutdown_timeout: float = 5.0,
) -> SafeThread:
    """迁移辅助: 将无参数的 threading.Thread target 包装为 SafeThread。

    原 target 在循环中被调用; SafeThread 的 stop_event 在每次循环前检查。

    Args:
        name: 线程名称
        target: 原线程函数 (无参数, 每次调用执行一个工作周期)
        daemon: 是否守护线程
        poll_interval: 停止信号检查间隔
        shutdown_timeout: 关闭超时
    """
    def _adapted_target(stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            try:
                target()
            except Exception:
                logger.error(
                    "SafeThread(migrated) %s iteration failed:\n%s",
                    name, traceback.format_exc(),
                )
            stop_event.wait(poll_interval)

    return SafeThread(
        name=name,
        target=_adapted_target,
        daemon=daemon,
        shutdown_timeout=shutdown_timeout,
    )
