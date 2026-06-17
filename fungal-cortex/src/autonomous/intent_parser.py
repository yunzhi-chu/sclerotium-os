"""L4 M1a: IntentParser — "丘脑中继站"(Thalamus) 意图解析器.

Biological Metaphor:
  丘脑(Thalamus)是大脑的感觉中继站——所有感官信息(除嗅觉外)都在丘脑
  中继后才到达皮层。丘脑不只是"转发"，而是主动过滤和优先级排序。

  9大金融领域关键词映射 = 丘脑核团的特异性投射:
    视觉→LGN→V1, 听觉→MGN→A1
  动作识别(backtest/screen/analyze/recommend) = 丘脑对"威胁/奖励"信号的预判
  约束提取(regime/count/compare) = 丘脑对信号强度的门控(gating)
  数字约束(正则\\d+[类种个套只]) = 数量感知(数感, number sense)

Reference: Thalamus model of sensory gating
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class IntentType(str, Enum):
    BACKTEST = "backtest"
    SCREEN = "screen"
    ANALYZE = "analyze"
    RECOMMEND = "recommend"
    MONITOR = "monitor"
    CONFIGURE = "configure"
    QUERY = "query"
    ALERT = "alert"


# 9 financial domain keyword mappings (thalamic nucleus projections)
_INTENT_KEYWORDS: dict[IntentType, list[str]] = {
    IntentType.BACKTEST: ["回测", "backtest", "历史模拟", "复盘"],
    IntentType.SCREEN: ["筛选", "选股", "screen", "scan", "扫描"],
    IntentType.ANALYZE: ["分析", "诊断", "analyze", "评估", "评测"],
    IntentType.RECOMMEND: ["推荐", "建议", "recommend", "策略", "方案"],
    IntentType.MONITOR: ["监控", "预警", "monitor", "watch", "追踪"],
    IntentType.CONFIGURE: ["配置", "设置", "参数", "config", "调优"],
    IntentType.QUERY: ["查询", "搜索", "query", "search", "查找", "检索"],
    IntentType.ALERT: ["告警", "报警", "alert", "警告", "异常"],
}

_ACTION_PATTERNS: dict[str, list[str]] = {
    "execute": ["执行", "运行", "run", "execute", "启动"],
    "stop": ["停止", "暂停", "stop", "halt", "中断"],
    "compare": ["对比", "比较", "compare", "vs", "versus"],
    "export": ["导出", "下载", "export", "download", "保存"],
}


@dataclass
class Intent:
    """A structured intention parsed from user/system input."""

    intent_id: str
    intent_type: IntentType
    description: str
    action: str  # "execute", "stop", "compare", "export", ""
    constraints: dict[str, Any]  # regime, count, compare targets, etc.
    confidence: float = 0.5
    priority: float = 0.5
    source: str = "user"
    created_at: float = field(default_factory=time.time)

    def summary(self) -> str:
        return f"Intent({self.intent_type.value}, action={self.action}, pri={self.priority:.2f})"


class IntentParser:
    """Thalamic relay station — parses raw text into structured intents."""

    def __init__(self, min_confidence: float = 0.3) -> None:
        self._min_conf = min_confidence
        self._logger = CortexLogger("intent_parser")
        self._parse_count = 0

    def parse(self, text: str, source: str = "user") -> Intent | None:
        """Parse text into a structured Intent. Returns None if confidence is too low."""
        if not text or not text.strip():
            return None

        text_lower = text.lower()

        # Step 1: Classify intent type (thalamic nucleus routing)
        intent_type, type_conf = self._classify_type(text_lower)

        # Step 2: Identify action
        action, action_conf = self._identify_action(text_lower)

        # Step 3: Extract constraints
        constraints = self._extract_constraints(text_lower, text)

        # Step 4: Compute confidence and priority
        confidence = (type_conf + action_conf) / 2
        priority = self._compute_priority(intent_type, constraints)

        if confidence < self._min_conf:
            return None

        self._parse_count += 1
        intent = Intent(
            intent_id=IntentParser._gen_id(text),
            intent_type=intent_type,
            description=text[:200],
            action=action,
            constraints=constraints,
            confidence=min(confidence, 1.0),
            priority=min(priority, 1.0),
            source=source,
        )
        self._logger.debug("intent_parsed", type=intent_type.value, action=action)
        return intent

    def parse_batch(self, texts: list[str], source: str = "batch") -> list[Intent]:
        results: list[Intent] = []
        for text in texts:
            intent = self.parse(text, source)
            if intent is not None:
                results.append(intent)
        return results

    def _classify_type(self, text_lower: str) -> tuple[IntentType, float]:
        """Classify by keyword matching — thalamic nucleus-specific projection."""
        scores: dict[IntentType, float] = {}
        for intent_type, keywords in _INTENT_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits > 0:
                scores[intent_type] = min(1.0, hits / 3)

        if not scores:
            return IntentType.QUERY, 0.3

        best_type = max(scores, key=scores.get)
        return best_type, scores[best_type]

    def _identify_action(self, text_lower: str) -> tuple[str, float]:
        """Identify action — threat/reward pre-judgment."""
        for action, keywords in _ACTION_PATTERNS.items():
            if any(kw in text_lower for kw in keywords):
                return action, 0.8
        return "", 0.4

    def _extract_constraints(self, text_lower: str, original: str) -> dict[str, Any]:
        """Extract structured constraints — thalamic signal gating."""
        constraints: dict[str, Any] = {}

        # Regime constraint
        regime_match = re.search(r"(牛市|熊市|震荡|猴市|bull|bear|range)", text_lower)
        if regime_match:
            constraints["regime"] = regime_match.group(1)

        # Count constraint (number sense)
        count_match = re.search(r"(\d+)\s*[类种个套只支持]", text_lower)
        if count_match:
            constraints["count"] = int(count_match.group(1))

        # Compare constraint
        if "对比" in text_lower or "compare" in text_lower or "vs" in text_lower:
            symbols = re.findall(r"[A-Z]{2,6}\.\w{2}|\d{6}", text_lower.upper())
            if len(symbols) >= 2:
                constraints["compare"] = symbols[:2]

        # Time constraint
        time_match = re.search(r"(\d+)\s*(天|日|周|月|年|min|hour|day)", text_lower)
        if time_match:
            constraints["time_range"] = int(time_match.group(1))
            constraints["time_unit"] = time_match.group(2)

        return constraints

    def _compute_priority(self, intent_type: IntentType, constraints: dict[str, Any]) -> float:
        """Priority based on type urgency."""
        base = {
            IntentType.ALERT: 0.9, IntentType.RECOMMEND: 0.7,
            IntentType.MONITOR: 0.6, IntentType.BACKTEST: 0.5,
            IntentType.ANALYZE: 0.5, IntentType.SCREEN: 0.4,
            IntentType.CONFIGURE: 0.3, IntentType.QUERY: 0.2,
        }
        priority = base.get(intent_type, 0.5)
        if constraints.get("count", 0) > 100:
            priority = min(1.0, priority + 0.1)
        return priority

    @staticmethod
    def _gen_id(text: str) -> str:
        return hashlib.md5(f"{text}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, int]:
        return {"parse_count": self._parse_count}
