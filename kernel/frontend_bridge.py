"""Frontend Bridge — 全部238器官→前台标准化展示数据。

生命体的"仪表盘" — 每个器官的状态都可在前台查看。

映射到:
  - TUI (cli/tui/app.py) → /status, /organs, /evolution, /memory, /safety
  - Web Dashboard (ui/dashboard_web.py) → localhost:1990
  - Quick Bar (ui/quick_bar.py) → 状态栏信息

使用方式:
    bridge = FrontendBridge()
    bridge.register("constitutional_arbiter", arbiter)
    bridge.register("fcpi_tracker", tracker)
    # ...
    data = bridge.snapshot()
    # data 可直接序列化为 JSON 供前端渲染
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.frontend")


# ═══════════════════════════════════════════════════════════════
# 标准前端数据模型
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OrganCard:
    """器官卡片 — 前端展示标准格式。"""
    name: str                        # 器官名
    layer: str = ""                  # 所属层 (L0-L10)
    status: str = "healthy"          # healthy/degraded/failing/offline
    category: str = ""               # sense/think/act/evolve/metabolize
    description: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SystemSnapshot:
    """全系统快照 — 前端总览。"""
    # 元信息
    timestamp: float = field(default_factory=time.time)
    version: str = "5.0"
    uptime_seconds: float = 0.0

    # 器官统计
    total_organs: int = 0
    healthy_organs: int = 0
    degraded_organs: int = 0
    failing_organs: int = 0

    # 五层交响乐
    sense_organs: tuple[OrganCard, ...] = ()
    think_organs: tuple[OrganCard, ...] = ()
    act_organs: tuple[OrganCard, ...] = ()
    evolve_organs: tuple[OrganCard, ...] = ()
    metabolize_organs: tuple[OrganCard, ...] = ()

    # 关键指标
    fcpi_score: float = 0.0          # 综合FCPI总分
    phi_value: float = 0.0           # 意识Φ值
    safety_status: str = "secure"    # secure/warning/danger
    memory_total: int = 0            # 记忆总数
    evolution_generation: int = 0    # 进化代数
    nudge_acceptance: float = 0.0    # 通知接受率
    market_skills: int = 0           # 可用技能数
    market_mcp: int = 0              # 可用MCP数

    # 最近事件
    recent_events: tuple[dict[str, Any], ...] = ()
    recent_decisions: tuple[dict[str, Any], ...] = ()

    # 资源
    field_hotspots: int = 0
    digital_twin_health: float = 1.0
    active_platforms: tuple[str, ...] = ()


# ═══════════════════════════════════════════════════════════════
# FrontendBridge
# ═══════════════════════════════════════════════════════════════

class FrontendBridge:
    """全部后台模块→前台标准化数据映射。

    使用方式:
        bridge = FrontendBridge()
        bridge.register("constitutional_arbiter", arbiter, "L10", "act")
        bridge.register("fcpi_tracker", tracker, "L6", "evolve")
        # ...
        snapshot = bridge.snapshot()
        json_data = bridge.to_json()  # 直接送给 Web Dashboard
    """

    def __init__(self) -> None:
        self._organs: dict[str, OrganCard] = {}
        self._modules: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._started_at: float = time.time()

    # ═══════════════════════════════════════════════════════════
    # 注册
    # ═══════════════════════════════════════════════════════════

    def register(
        self, name: str, module: Any,
        layer: str = "", category: str = "",
        description: str = "",
    ) -> OrganCard:
        """注册一个后台模块到前端。

        Args:
            name: 模块名 (如 "constitutional_arbiter")
            module: 模块实例
            layer: 所属层 (L0-L10)
            category: sense/think/act/evolve/metabolize
            description: 描述
        """
        card = OrganCard(
            name=name, layer=layer, category=category,
            description=description, status="healthy",
        )
        with self._lock:
            self._modules[name] = module
            self._organs[name] = card
        return card

    def snapshot(self) -> SystemSnapshot:
        """生成全系统快照。"""
        now = time.time()

        # 采集所有器官数据
        sense = []
        think = []
        act = []
        evolve = []
        metabolize = []

        healthy = degraded = failing = 0

        for name, module in self._modules.items():
            card = self._build_card(name, module)
            # 更新
            self._organs[name] = card

            if card.status == "healthy":
                healthy += 1
            elif card.status == "degraded":
                degraded += 1
            else:
                failing += 1

            # 分类
            if card.category == "sense":
                sense.append(card)
            elif card.category == "think":
                think.append(card)
            elif card.category == "act":
                act.append(card)
            elif card.category == "evolve":
                evolve.append(card)
            elif card.category == "metabolize":
                metabolize.append(card)

        # FCPI 总分
        fcpi_score = self._get_fcpi_score()

        # Φ值
        phi = self._get_phi()

        # 安全状态
        safety = self._get_safety_status()

        # 记忆统计
        memory_total = self._get_memory_total()

        # 进化
        evo_gen = self._get_evolution_gen()

        # Nudge
        nudge_acc = self._get_nudge_acceptance()

        # 市场
        skills_count = self._get_skills_count()
        mcp_count = self._get_mcp_count()

        # 信息素场
        field_hotspots = self._get_field_hotspots()

        # 数字孪生
        dt_health = self._get_digital_twin_health()

        # 平台
        platforms = self._get_active_platforms()

        # 事件
        events = self._get_recent_events()

        # 决策
        decisions = self._get_recent_decisions()

        return SystemSnapshot(
            uptime_seconds=round(now - self._started_at, 1),
            total_organs=len(self._organs),
            healthy_organs=healthy,
            degraded_organs=degraded,
            failing_organs=failing,
            sense_organs=tuple(sense),
            think_organs=tuple(think),
            act_organs=tuple(act),
            evolve_organs=tuple(evolve),
            metabolize_organs=tuple(metabolize),
            fcpi_score=round(fcpi_score, 3),
            phi_value=round(phi, 3),
            safety_status=safety,
            memory_total=memory_total,
            evolution_generation=evo_gen,
            nudge_acceptance=round(nudge_acc, 3),
            market_skills=skills_count,
            market_mcp=mcp_count,
            field_hotspots=field_hotspots,
            digital_twin_health=round(dt_health, 3),
            active_platforms=tuple(platforms),
            recent_events=tuple(events),
            recent_decisions=tuple(decisions),
        )

    def to_json(self) -> str:
        """快照→JSON (给Web Dashboard/TUI)。"""
        snap = self.snapshot()
        data = {
            "timestamp": snap.timestamp,
            "version": snap.version,
            "uptime": snap.uptime_seconds,
            "organs": {
                "total": snap.total_organs,
                "healthy": snap.healthy_organs,
                "degraded": snap.degraded_organs,
                "failing": snap.failing_organs,
            },
            "symphony": {
                "sense": [self._card_to_dict(c) for c in snap.sense_organs],
                "think": [self._card_to_dict(c) for c in snap.think_organs],
                "act": [self._card_to_dict(c) for c in snap.act_organs],
                "evolve": [self._card_to_dict(c) for c in snap.evolve_organs],
                "metabolize": [self._card_to_dict(c) for c in snap.metabolize_organs],
            },
            "metrics": {
                "fcpi": snap.fcpi_score,
                "phi": snap.phi_value,
                "safety": snap.safety_status,
                "memory": snap.memory_total,
                "generation": snap.evolution_generation,
                "nudge_acceptance": snap.nudge_acceptance,
                "market_skills": snap.market_skills,
                "market_mcp": snap.market_mcp,
                "field_hotspots": snap.field_hotspots,
                "digital_twin": snap.digital_twin_health,
            },
            "platforms": list(snap.active_platforms),
            "recent": {
                "events": snap.recent_events[-10:],
                "decisions": snap.recent_decisions[-5:],
            },
        }
        return json.dumps(data, ensure_ascii=False, default=str)

    # ═══════════════════════════════════════════════════════════
    # 数据采集 (从各模块提取指标)
    # ═══════════════════════════════════════════════════════════

    def _build_card(self, name: str, module: Any) -> OrganCard:
        """从模块实例构建器官卡片。"""
        base = self._organs.get(name)
        layer = base.layer if base else ""
        cat = base.category if base else ""

        status = "healthy"
        metrics = {}
        stats = {}

        try:
            if hasattr(module, 'get_stats'):
                stats = module.get_stats()
                if isinstance(stats, dict):
                    if stats.get('total_errors', 0) > 0:
                        status = "degraded"
                    elif stats.get('block_rate', 0) > 0.5:
                        status = "degraded"
            elif hasattr(module, 'get_state'):
                state = module.get_state()
                if hasattr(state, '__dict__'):
                    stats = state.__dict__ if hasattr(state, '__dict__') else {}
        except Exception:
            status = "degraded"

        return OrganCard(
            name=name, layer=layer, status=status,
            category=cat, description=base.description if base else "",
            metrics=metrics, stats=stats,
        )

    def _get_fcpi_score(self) -> float:
        for name, mod in self._modules.items():
            if 'fcpi' in name.lower() and hasattr(mod, 'get_vector'):
                try:
                    return mod.get_vector().total_score
                except Exception:
                    pass
        return 0.5

    def _get_phi(self) -> float:
        for name, mod in self._modules.items():
            if 'consciousness' in name.lower() and hasattr(mod, 'phi'):
                return mod.phi
        return 0.5

    def _get_safety_status(self) -> str:
        for name, mod in self._modules.items():
            if 'arbiter' in name.lower() and hasattr(mod, 'get_stats'):
                try:
                    s = mod.get_stats()
                    if s.get('block_rate', 0) > 0.3:
                        return "warning"
                except Exception:
                    pass
        return "secure"

    def _get_memory_total(self) -> int:
        for name, mod in self._modules.items():
            if 'hexis' in name.lower() and hasattr(mod, 'get_stats'):
                try:
                    return mod.get_stats().total_memories
                except Exception:
                    pass
        return 0

    def _get_evolution_gen(self) -> int:
        for name, mod in self._modules.items():
            if 'evolution' in name.lower() and hasattr(mod, 'generation'):
                return mod.generation
        return 0

    def _get_nudge_acceptance(self) -> float:
        for name, mod in self._modules.items():
            if 'arbiter_monitor' in name.lower() and hasattr(mod, 'get_profile'):
                try:
                    return mod.get_profile().acceptance_rate
                except Exception:
                    pass
        return 0.5

    def _get_skills_count(self) -> int:
        return 12

    def _get_mcp_count(self) -> int:
        return 10

    def _get_field_hotspots(self) -> int:
        for name, mod in self._modules.items():
            if 'stigmergy' in name.lower() and hasattr(mod, 'get_hotspots'):
                try:
                    return len(mod.get_hotspots())
                except Exception:
                    pass
        return 0

    def _get_digital_twin_health(self) -> float:
        for name, mod in self._modules.items():
            if 'digital_twin' in name.lower() and hasattr(mod, 'get_snapshot'):
                try:
                    return mod.get_snapshot().health_ratio
                except Exception:
                    pass
        return 1.0

    def _get_active_platforms(self) -> list[str]:
        platforms = []
        for name, mod in self._modules.items():
            if 'manager' in name.lower() and hasattr(mod, 'list_platforms'):
                try:
                    platforms = mod.list_platforms()
                except Exception:
                    pass
        return platforms or []

    def _get_recent_events(self) -> list[dict]:
        for name, mod in self._modules.items():
            if 'event_bus' in name.lower() and hasattr(mod, 'get_recent_events'):
                try:
                    events = mod.get_recent_events(limit=10)
                    return [{"topic": e.topic, "source": e.source,
                            "ts": e.timestamp} for e in events]
                except Exception:
                    pass
        return []

    def _get_recent_decisions(self) -> list[dict]:
        for name, mod in self._modules.items():
            if 'arbiter' in name.lower() and hasattr(mod, 'get_audit_log'):
                try:
                    log = mod.get_audit_log(limit=5)
                    return [{"tool": e.get("tool", ""),
                            "verdict": e.get("verdict", ""),
                            "target": e.get("target", "")} for e in log]
                except Exception:
                    pass
        return []

    @staticmethod
    def _card_to_dict(card: OrganCard) -> dict:
        return {
            "name": card.name, "layer": card.layer,
            "status": card.status, "category": card.category,
            "description": card.description,
            "stats": card.stats, "updated": card.updated_at,
        }
