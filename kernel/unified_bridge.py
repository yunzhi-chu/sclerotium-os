"""Unified Bridge Manager — 24桥接统一激活与管理。

生命体的"神经系统总线" — 管理所有238器官间的信号路由。

桥接统计 (当前已激活):
  - conscious_bridge: L10 ConsciousKernel ↔ AgentLoop
  - immune_bridge: L0 AISImmuneValidator ↔ SecurityGateway
  - debate_bridge: L3 DebateNetwork ↔ NudgeEngine
  - meta_bridge: L6 MetaCognition ↔ AllOrgans
  - dgm_bridge: L6 DGM ↔ EvolutionLoop
  - crystallizer_bridge: L6 Crystallizer ↔ SkillRegistry
  - goal_bridge: L6 GoalExpander ↔ AgentLoop
  - skill_bridge: L6 SkillRegistry ↔ ChainExecutor
  - self_ref_bridge: L8 SelfRefCompiler ↔ Checkpoint/Restore
  - stigmergy_bridge: L5 StigmergyField ↔ EventBus
  - digital_twin_bridge: L7 DigitalTwin ↔ Dashboard
  - active_inference_bridge: L7 ActiveInference ↔ AgentLoop
  - liquid_perceptor_bridge: L1 LiquidPerceptor ↔ WindowWatcher
  - ltc_bridge: L2 LTC ↔ RhythmEngine
  - arbiter_monitor_bridge: L6 ArbiterMonitor ↔ NudgeEngine
  - causal_bridge: L4 CausalDebug ↔ MetaCognition
  - neutrosophic_bridge: L3 Neutrosophic ↔ DailyDigest
  - self_repair_bridge: L6 CodeSelfRepair ↔ SelfHealing
  - quantum_bridge: L9 Quantum ↔ EvolutionLoop
  - p2p_bridge: L9 P2P ↔ MemorySync
  - strategy_dna_bridge: StrategyDNA ↔ Genome
  - phase1_4_bridges: 4 分层桥接

使用方式:
    hub = UnifiedBridge()
    hub.register("conscious", conscious_bridge)
    hub.activate_all()
    stats = hub.get_stats()
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("sclerotium.unified_bridge")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class BridgeStatus(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass(frozen=True)
class BridgeInfo:
    """单个桥接信息。"""
    name: str
    source_layer: str       # 来源层 (L0-L10)
    target_layer: str       # 目标层
    status: BridgeStatus = BridgeStatus.INACTIVE
    message_count: int = 0
    error_count: int = 0
    last_active: float = 0.0


@dataclass(frozen=True)
class BridgeHubStats:
    """桥接中心统计。"""
    total_bridges: int
    active: int
    inactive: int
    degraded: int
    total_messages: int
    activation_ratio: float


# ═══════════════════════════════════════════════════════════════
# UnifiedBridge
# ═══════════════════════════════════════════════════════════════

class UnifiedBridge:
    """24桥接统一激活管理器。

    使用方式:
        hub = UnifiedBridge()
        hub.register("conscious", bridge_obj)
        hub.activate("conscious")
        state = hub.get_stats()
    """

    def __init__(self) -> None:
        self._bridges: dict[str, tuple[Any, BridgeInfo]] = {}
        self._message_counts: dict[str, int] = {}
        self._callbacks: dict[str, list[Callable]] = {}

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def register(
        self, name: str, bridge: Any,
        source_layer: str = "", target_layer: str = "",
    ) -> None:
        """注册一个桥接。"""
        self._bridges[name] = (bridge, BridgeInfo(
            name=name, source_layer=source_layer,
            target_layer=target_layer,
        ))

    def activate(self, name: str) -> bool:
        """激活一个桥接。"""
        if name not in self._bridges:
            return False
        bridge, info = self._bridges[name]
        new_info = BridgeInfo(
            name=info.name, source_layer=info.source_layer,
            target_layer=info.target_layer,
            status=BridgeStatus.ACTIVE, last_active=time.time(),
            message_count=info.message_count,
            error_count=info.error_count,
        )
        self._bridges[name] = (bridge, new_info)
        logger.debug("Bridge activated: %s", name)
        return True

    def deactivate(self, name: str) -> bool:
        """停用一个桥接。"""
        if name not in self._bridges:
            return False
        bridge, info = self._bridges[name]
        new_info = BridgeInfo(
            name=info.name, source_layer=info.source_layer,
            target_layer=info.target_layer,
            status=BridgeStatus.INACTIVE,
            message_count=info.message_count,
            error_count=info.error_count,
        )
        self._bridges[name] = (bridge, new_info)
        return True

    def send_message(self, from_bridge: str, to_bridge: str,
                     data: dict[str, Any]) -> bool:
        """通过桥接发送消息。"""
        if from_bridge not in self._bridges:
            return False
        bridge, info = self._bridges[from_bridge]
        if info.status != BridgeStatus.ACTIVE:
            return False

        self._message_counts[from_bridge] = (
            self._message_counts.get(from_bridge, 0) + 1
        )

        # 触发目标回调
        if to_bridge in self._callbacks:
            for cb in self._callbacks[to_bridge]:
                try:
                    cb(data)
                except Exception:
                    pass
        return True

    def on_message(self, bridge_name: str,
                   callback: Callable[[dict], None]) -> None:
        """注册桥接消息回调。"""
        if bridge_name not in self._callbacks:
            self._callbacks[bridge_name] = []
        self._callbacks[bridge_name].append(callback)

    def activate_all(self) -> dict[str, bool]:
        """激活所有已注册桥接。"""
        results = {}
        for name in self._bridges:
            results[name] = self.activate(name)
        active = sum(1 for v in results.values() if v)
        logger.info("Activated %d/%d bridges", active, len(results))
        return results

    def get_stats(self) -> BridgeHubStats:
        """获取桥接中心统计。"""
        active = sum(1 for _, info in self._bridges.values()
                    if info.status == BridgeStatus.ACTIVE)
        inactive = sum(1 for _, info in self._bridges.values()
                      if info.status == BridgeStatus.INACTIVE)
        degraded = sum(1 for _, info in self._bridges.values()
                      if info.status in (BridgeStatus.DEGRADED, BridgeStatus.FAILED))
        total = len(self._bridges)
        total_msgs = sum(self._message_counts.values())

        return BridgeHubStats(
            total_bridges=total,
            active=active, inactive=inactive, degraded=degraded,
            total_messages=total_msgs,
            activation_ratio=round(active / max(total, 1), 3),
        )

    def list_bridges(self) -> list[BridgeInfo]:
        return [info for _, info in self._bridges.values()]
