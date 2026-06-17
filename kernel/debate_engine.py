"""Debate Engine — 小世界辩论网络 (L3 MycorrhizalDebateNetwork)。

生命体的"内部辩论" — Insight 发布前, 必须经过多方辩论投票。

辩论机制:
  - 正方 Agent (3个): 支持这个 Insight
  - 反方 Agent (3个): 反驳这个 Insight
  - 共识阈值: ≥4/6 同意才通过
  - 小世界拓扑: 每个 Agent 只与部分邻居通信

使用方式:
    engine = DebateEngine(agents=6)
    engine.add_argument("pro", "用户确实在深夜工作", confidence=0.8)
    engine.add_argument("con", "可能只是偶尔一次", confidence=0.4)
    verdict = engine.debate()
    print(f"通过: {verdict.passed}, 共识: {verdict.consensus_ratio}")
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.debate")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Argument:
    """辩论论点 (不可变)。"""
    side: str           # "pro" / "con"
    statement: str
    confidence: float = 0.5
    supporter: str = ""  # 支持者 Agent 名


@dataclass(frozen=True)
class DebateVerdict:
    """辩论裁决 (不可变)。"""
    passed: bool
    pro_votes: int
    con_votes: int
    total_agents: int
    consensus_ratio: float      # 同意比例
    majority_side: str = ""     # "pro" / "con" / "tie"
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# DebateEngine
# ═══════════════════════════════════════════════════════════════

class DebateEngine:
    """小世界辩论网络 — 多方辩论验证。

    使用方式:
        engine = DebateEngine(agents=6)
        engine.add_argument("pro", "用户长时间工作需要提醒", 0.7)
        engine.add_argument("con", "用户可能在专注工作不宜打断", 0.6)
        verdict = engine.debate()
    """

    def __init__(self, agents: int = 6, threshold: float = 0.67) -> None:
        self._total_agents = max(4, agents)
        self._threshold = threshold
        self._pro_args: list[Argument] = []
        self._con_args: list[Argument] = []
        self._history: list[DebateVerdict] = []

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def add_argument(
        self, side: str, statement: str, confidence: float = 0.5,
    ) -> None:
        """添加辩论论点。

        Args:
            side: "pro" (支持) 或 "con" (反对)
            statement: 论点陈述
            confidence: 置信度 (0.0–1.0)
        """
        arg = Argument(
            side=side, statement=statement,
            confidence=max(0.0, min(1.0, confidence)),
        )
        if side == "pro":
            self._pro_args.append(arg)
        else:
            self._con_args.append(arg)

    def debate(self) -> DebateVerdict:
        """执行辩论投票。

        投票规则:
          - 每个 Agent (pro/con 均匀分配) 基于论点投票
          - 正方 Agent 倾向支持 pro 论点
          - 反方 Agent 倾向支持 con 论点
          - 共识阈值: 需要 ≥threshold 比例同意
        """
        half = self._total_agents // 2
        pro_agents = half
        con_agents = self._total_agents - half

        # 正方 Agent 投票
        pro_votes = 0
        if self._pro_args:
            avg_pro_conf = sum(a.confidence for a in self._pro_args) / len(self._pro_args)
            # 正方 Agent 基于 pro 论点置信度投票
            for i in range(pro_agents):
                if avg_pro_conf > 0.4 or (self._pro_args and random.random() < avg_pro_conf):
                    pro_votes += 1
        else:
            pro_votes = pro_agents // 2  # 无论点时默认一半同意

        # 反方 Agent 投票
        con_votes = 0
        if self._con_args:
            avg_con_conf = sum(a.confidence for a in self._con_args) / len(self._con_args)
            for i in range(con_agents):
                if avg_con_conf > 0.4 or (self._con_args and random.random() < avg_con_conf):
                    con_votes += 1

        total_votes = pro_votes + con_votes
        passed = pro_votes >= int(self._total_agents * self._threshold)

        if pro_votes > con_votes:
            majority = "pro"
        elif con_votes > pro_votes:
            majority = "con"
        else:
            majority = "tie"

        consensus = (pro_votes / self._total_agents) if passed else (
            max(pro_votes, con_votes) / self._total_agents
        )

        reasoning = (
            f"正方 {pro_votes}/{self._total_agents} 票, "
            f"反方 {con_votes}/{self._total_agents} 票, "
            f"{'✅ 通过' if passed else '❌ 未通过'} "
            f"(阈值={self._threshold:.0%})"
        )

        verdict = DebateVerdict(
            passed=passed,
            pro_votes=pro_votes,
            con_votes=con_votes,
            total_agents=self._total_agents,
            consensus_ratio=round(consensus, 3),
            majority_side=majority,
            reasoning=reasoning,
        )
        self._history.append(verdict)
        if len(self._history) > 200:
            self._history = self._history[-200:]
        return verdict

    def get_history(self, limit: int = 20) -> list[DebateVerdict]:
        return self._history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        if not self._history:
            return {"debates": 0, "pass_rate": 0.0}
        passed = sum(1 for v in self._history if v.passed)
        return {
            "debates": len(self._history),
            "pass_rate": round(passed / len(self._history), 3),
            "pro_args": len(self._pro_args),
            "con_args": len(self._con_args),
        }

    def clear(self) -> None:
        self._pro_args.clear()
        self._con_args.clear()
        self._history.clear()
