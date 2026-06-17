"""Platform Manager — 多平台生命周期管理。

管理所有 IM 平台适配器的:
  - 启动/停止 (并发连接)
  - 健康检查 (定期 ping)
  - 自动重连 (指数退避)
  - 统计聚合 (跨平台)

使用方式:
    mgr = PlatformManager()
    mgr.register(WeChatAdapter(config={"api_url": "..."}))
    mgr.register(QQAdapter(config={"ws_url": "..."}))
    mgr.register(FeishuAdapter(config={"app_id": "...", "app_secret": "..."}))

    # 并发连接所有平台
    await mgr.connect_all()

    # 通过管理器发送消息 (自动路由到正确平台)
    result = await mgr.send("wechat", "user123", "Hello!")

    # 健康检查
    status = await mgr.health_check_all()

    await mgr.disconnect_all()
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from platforms.base import PlatformAdapter, SendResult

logger = logging.getLogger("sclerotium.manager")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PlatformStatus:
    """单个平台状态 (不可变)。"""
    platform: str
    connected: bool
    messages_received: int = 0
    messages_sent: int = 0
    errors: int = 0
    last_error: str = ""
    uptime_seconds: float = 0.0


@dataclass(frozen=True)
class ManagerState:
    """管理器状态快照 (不可变)。"""
    platforms: tuple[PlatformStatus, ...]
    total_platforms: int
    connected_count: int
    total_messages_received: int
    total_messages_sent: int
    uptime_seconds: float = 0.0


# ═══════════════════════════════════════════════════════════════
# PlatformManager
# ═══════════════════════════════════════════════════════════════

class PlatformManager:
    """多平台适配器管理器。

    统一管理所有触手的生命周期, 提供:
      - 并发连接/断开
      - 消息发送 (指定平台)
      - 健康检查
      - 状态聚合

    使用方式:
        mgr = PlatformManager()
        mgr.register(WeChatAdapter(...))
        await mgr.connect_all()
        # ... 系统运行 ...
        await mgr.disconnect_all()
    """

    def __init__(self) -> None:
        self._adapters: dict[str, PlatformAdapter] = {}
        self._connected_at: dict[str, float] = {}
        self._started_at: float = 0.0
        self._running: bool = False

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def register(self, adapter: PlatformAdapter) -> None:
        """注册一个平台适配器。"""
        platform = adapter.platform_name
        if platform in self._adapters:
            logger.warning("Platform already registered: %s", platform)
        self._adapters[platform] = adapter
        logger.info("Registered platform: %s", platform)

    def unregister(self, platform: str) -> bool:
        """注销平台适配器。"""
        if platform in self._adapters:
            del self._adapters[platform]
            self._connected_at.pop(platform, None)
            logger.info("Unregistered platform: %s", platform)
            return True
        return False

    async def connect_all(self) -> dict[str, bool]:
        """并发连接所有已注册平台。

        Returns:
            {platform_name: success}
        """
        self._started_at = time.time()
        self._running = True
        results = {}

        # 并发连接
        tasks = []
        for platform, adapter in self._adapters.items():
            tasks.append(self._connect_one(platform, adapter))
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        for (platform, _), outcome in zip(self._adapters.items(), outcomes):
            if isinstance(outcome, Exception):
                results[platform] = False
                logger.error("Connect %s failed: %s", platform, outcome)
            else:
                results[platform] = outcome

        connected = sum(1 for v in results.values() if v)
        logger.info("Connected %d/%d platforms", connected, len(results))
        return results

    async def disconnect_all(self) -> None:
        """并发断开所有平台。"""
        self._running = False
        tasks = []
        for adapter in self._adapters.values():
            if adapter.is_connected:
                tasks.append(adapter.disconnect())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._connected_at.clear()
        logger.info("All platforms disconnected")

    async def send(
        self,
        platform: str,
        target: str,
        content: str,
    ) -> SendResult:
        """通过指定平台发送消息。

        Args:
            platform: 平台名 ("wechat"/"qq"/"feishu"/...)
            target: 目标 ID
            content: 消息内容

        Returns:
            SendResult
        """
        adapter = self._adapters.get(platform)
        if not adapter:
            return SendResult(
                success=False, platform=platform, target=target,
                error=f"Platform not registered: {platform}",
            )
        if not adapter.is_connected:
            return SendResult(
                success=False, platform=platform, target=target,
                error=f"Platform not connected: {platform}",
            )
        return await adapter.send_message(target, content)

    async def broadcast(
        self,
        content: str,
        platforms: list[str] | None = None,
    ) -> dict[str, SendResult]:
        """向多个平台广播消息。

        Args:
            content: 消息内容
            platforms: 目标平台列表 (None=全部)

        Returns:
            {platform: SendResult}
        """
        targets = platforms or list(self._adapters.keys())
        tasks = {}
        for p in targets:
            if p in self._adapters:
                adapter = self._adapters[p]
                if adapter.is_connected:
                    tasks[p] = adapter.send_message("broadcast", content)

        results = {}
        for p, task in tasks.items():
            try:
                results[p] = await task
            except Exception as e:
                results[p] = SendResult(
                    success=False, platform=p, target="broadcast",
                    error=str(e),
                )
        return results

    async def health_check_all(self) -> dict[str, bool]:
        """所有平台健康检查。"""
        tasks = {}
        for platform, adapter in self._adapters.items():
            tasks[platform] = adapter.health_check()
        results = {}
        for platform, task in tasks.items():
            try:
                results[platform] = await task
            except Exception:
                results[platform] = False
        return results

    def get_state(self) -> ManagerState:
        """获取管理器状态快照。"""
        statuses = []
        for platform, adapter in self._adapters.items():
            stats = adapter.stats
            uptime = 0.0
            if platform in self._connected_at:
                uptime = time.time() - self._connected_at[platform]

            statuses.append(PlatformStatus(
                platform=platform,
                connected=adapter.is_connected,
                messages_received=stats.get("messages_received", 0),
                messages_sent=stats.get("messages_sent", 0),
                errors=stats.get("errors", 0),
                last_error=stats.get("last_error", ""),
                uptime_seconds=uptime,
            ))

        return ManagerState(
            platforms=tuple(statuses),
            total_platforms=len(self._adapters),
            connected_count=sum(1 for s in statuses if s.connected),
            total_messages_received=sum(s.messages_received for s in statuses),
            total_messages_sent=sum(s.messages_sent for s in statuses),
            uptime_seconds=time.time() - self._started_at if self._started_at > 0 else 0.0,
        )

    def get_adapter(self, platform: str) -> PlatformAdapter | None:
        """获取指定平台适配器。"""
        return self._adapters.get(platform)

    def list_platforms(self) -> list[str]:
        """列出已注册平台。"""
        return list(self._adapters.keys())

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def platform_count(self) -> int:
        return len(self._adapters)

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    async def _connect_one(self, platform: str, adapter: PlatformAdapter) -> bool:
        """连接单个平台 (带重试)。"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                success = await adapter.connect()
                if success:
                    self._connected_at[platform] = time.time()
                    logger.info("Connected to %s", platform)
                    return True
            except Exception as e:
                logger.warning("%s connect attempt %d/%d failed: %s",
                               platform, attempt + 1, max_retries, e)

            if attempt < max_retries - 1:
                await asyncio.sleep(1.0 * (attempt + 1))  # 指数退避

        logger.error("%s: all %d connection attempts failed", platform, max_retries)
        return False
