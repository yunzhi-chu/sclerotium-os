"""Immune Gateway — 三层人工免疫系统 (AIS) 安全审查链。

生命体的"免疫系统" — 检测异常、学习正常、自适应防御。

三层免疫:
  1. 负选择 (Negative Selection) — "不应该匹配的东西"
     → 已知危险模式黑名单
     → 检测器在"自我"集上训练, 不匹配"自我"的视为异常

  2. 克隆选择 (Clonal Selection) — "曾经有效的东西"
     → 用户批准的操作 → 自动白名单 (亲和力成熟)
     → 高亲和力检测器增殖, 低亲和力淘汰

  3. 危险信号 (Danger Signals) — "看起来不对劲的东西"
     → 不依赖模式匹配, 检测环境异常
     → 例如: 短时间内大量文件操作/非工作时间敏感操作

使用方式:
    gateway = ImmuneGateway()
    gateway.train_self(historical_safe_events)

    request = ActionRequest(tool="file_write", target="config.yaml")
    result = gateway.scan(request)
    if result.threat_level >= 0.7:
        block(request)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("sclerotium.immune")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class ImmuneDecision(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    QUARANTINE = "quarantine"


@dataclass(frozen=True)
class ImmuneResult:
    """免疫扫描结果 (不可变)。"""
    threat_level: float          # 0.0(安全) — 1.0(确定威胁)
    decision: ImmuneDecision
    layer: str = ""              # 触发决策的层
    matched_rule: str = ""       # 匹配的规则
    confidence: float = 0.0      # 检测置信度
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SelfPattern:
    """"自我"模式 (不可变)。"""
    pattern: str                 # 特征字符串
    category: str = ""           # 类别
    count: int = 1               # 出现次数
    last_seen: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# ImmuneGateway
# ═══════════════════════════════════════════════════════════════

class ImmuneGateway:
    """三层人工免疫系统安全审查。

    使用方式:
        gateway = ImmuneGateway()
        gateway.add_self_pattern("file_read:*.py", category="safe_file_read")
        result = gateway.scan("file_write", "config.yaml", {})
        if result.decision == ImmuneDecision.BLOCK:
            deny_request()
    """

    # 默认危险关键词 (负选择)
    DEFAULT_DANGEROUS_KEYWORDS = [
        "rm -rf", "format", "del /f", "shutdown",
        "drop table", "truncate", ":(){ :|:& };:",  # fork bomb
        "eval(", "exec(", "__import__", "os.system",
        "write /etc/passwd", "chmod 777 /",
    ]

    def __init__(self) -> None:
        self._lock = threading.RLock()

        # Layer 1: 负选择 — 危险模式黑名单
        self._dangerous_patterns: list[str] = list(
            self.DEFAULT_DANGEROUS_KEYWORDS
        )

        # Layer 2: 克隆选择 — 批准的模式白名单 (高亲和力)
        self._approved_patterns: dict[str, SelfPattern] = {}

        # Layer 3: 危险信号 — 环境异常检测
        self._recent_events: list[dict[str, Any]] = []
        self._anomaly_count: int = 0
        self._total_scans: int = 0

        # 历史
        self._results: list[ImmuneResult] = []

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def scan(
        self, tool: str, target: str, params: dict[str, Any] | None = None,
    ) -> ImmuneResult:
        """三层免疫扫描。

        Args:
            tool: 工具名
            target: 目标
            params: 参数

        Returns:
            ImmuneResult
        """
        params = params or {}
        self._total_scans += 1

        # Layer 1: 负选择 — 匹配危险模式?
        l1_result = self._negative_selection(tool, target, params)
        if l1_result is not None:
            return l1_result

        # Layer 2: 克隆选择 — 匹配已批准模式?
        l2_result = self._clonal_selection(tool, target, params)
        if l2_result is not None and l2_result.decision == ImmuneDecision.ALLOW:
            return l2_result

        # Layer 3: 危险信号 — 环境异常?
        l3_result = self._danger_signals(tool, target, params)
        if l3_result is not None:
            return l3_result

        # 默认放行
        result = ImmuneResult(
            threat_level=0.1,
            decision=ImmuneDecision.ALLOW,
            layer="default",
            confidence=0.3,
        )
        self._record(result)
        return result

    def add_dangerous_pattern(self, pattern: str) -> None:
        """添加危险模式 (负选择)。"""
        with self._lock:
            if pattern not in self._dangerous_patterns:
                self._dangerous_patterns.append(pattern)

    def approve_pattern(self, pattern: str, category: str = "") -> None:
        """批准一个模式 (克隆选择 — 亲和力提升)。"""
        with self._lock:
            if pattern in self._approved_patterns:
                sp = self._approved_patterns[pattern]
                self._approved_patterns[pattern] = SelfPattern(
                    pattern=pattern, category=sp.category,
                    count=sp.count + 1, last_seen=time.time(),
                )
            else:
                self._approved_patterns[pattern] = SelfPattern(
                    pattern=pattern, category=category, count=1,
                )

    def record_event(self, event: dict[str, Any]) -> None:
        """记录事件 (用于危险信号检测)。"""
        with self._lock:
            self._recent_events.append(event)
            if len(self._recent_events) > 100:
                self._recent_events = self._recent_events[-100:]

    def get_stats(self) -> dict[str, Any]:
        """获取免疫统计。"""
        with self._lock:
            recent = self._results[-50:]
            return {
                "total_scans": self._total_scans,
                "dangerous_patterns": len(self._dangerous_patterns),
                "approved_patterns": len(self._approved_patterns),
                "anomaly_count": self._anomaly_count,
                "block_rate": sum(
                    1 for r in recent if r.decision == ImmuneDecision.BLOCK
                ) / max(len(recent), 1),
            }

    def clear(self) -> None:
        with self._lock:
            self._recent_events.clear()
            self._results.clear()
            self._total_scans = 0
            self._anomaly_count = 0

    # ═══════════════════════════════════════════════════════
    # Layer 1: 负选择 (Negative Selection)
    # ═══════════════════════════════════════════════════════

    def _negative_selection(
        self, tool: str, target: str, params: dict[str, Any],
    ) -> ImmuneResult | None:
        """检测已知危险模式。"""
        import json
        combined = f"{tool}:{target}:{json.dumps(params)}".lower()

        for pattern in self._dangerous_patterns:
            if pattern.lower() in combined:
                result = ImmuneResult(
                    threat_level=0.9,
                    decision=ImmuneDecision.BLOCK,
                    layer="negative_selection",
                    matched_rule=pattern,
                    confidence=0.85,
                )
                self._record(result)
                logger.warning("Immune BLOCK: %s matched '%s'", tool, pattern)
                return result
        return None

    # ═══════════════════════════════════════════════════════
    # Layer 2: 克隆选择 (Clonal Selection)
    # ═══════════════════════════════════════════════════════

    def _clonal_selection(
        self, tool: str, target: str, params: dict[str, Any],
    ) -> ImmuneResult | None:
        """匹配已批准的安全模式。"""
        import json
        combined = f"{tool}:{target}:{json.dumps(params)}".lower()

        # 精确匹配
        for pattern, sp in self._approved_patterns.items():
            if pattern.lower() in combined:
                return ImmuneResult(
                    threat_level=0.05,
                    decision=ImmuneDecision.ALLOW,
                    layer="clonal_selection",
                    matched_rule=pattern,
                    confidence=0.7 + min(0.3, sp.count * 0.05),
                )

        # 模糊匹配 (同类操作)
        for pattern, sp in self._approved_patterns.items():
            if pattern.startswith(tool + ":"):
                return ImmuneResult(
                    threat_level=0.1,
                    decision=ImmuneDecision.ALLOW,
                    layer="clonal_selection(fuzzy)",
                    matched_rule=pattern,
                    confidence=0.5 + min(0.3, sp.count * 0.05),
                )

        return None

    # ═══════════════════════════════════════════════════════
    # Layer 3: 危险信号 (Danger Signals)
    # ═══════════════════════════════════════════════════════

    def _danger_signals(
        self, tool: str, target: str, params: dict[str, Any],
    ) -> ImmuneResult | None:
        """检测环境异常 - 不需要模式匹配。"""

        # 信号1: 短时间内大量操作
        with self._lock:
            recent_10s = [
                e for e in self._recent_events[-20:]
                if time.time() - e.get("timestamp", 0) < 10.0
            ]
            if len(recent_10s) > 10:
                self._anomaly_count += 1
                return ImmuneResult(
                    threat_level=0.6,
                    decision=ImmuneDecision.WARN,
                    layer="danger_signal(rate)",
                    matched_rule=f"{len(recent_10s)} events in 10s",
                    confidence=0.5,
                )

            # 信号2: 非工作时间 + 敏感操作
            hour = int(time.strftime("%H"))
            is_night = hour < 6 or hour >= 23
            if is_night:
                high_risk = ["file_delete", "bash_exec", "im_send",
                            "system_config", "git_push"]
                if any(t in tool.lower() for t in high_risk):
                    self._anomaly_count += 1
                    return ImmuneResult(
                        threat_level=0.5,
                        decision=ImmuneDecision.WARN,
                        layer="danger_signal(night)",
                        matched_rule=f"Night operation: {tool}",
                        confidence=0.4,
                    )

        return None

    def _record(self, result: ImmuneResult) -> None:
        with self._lock:
            self._results.append(result)
            if len(self._results) > 500:
                self._results = self._results[-500:]
