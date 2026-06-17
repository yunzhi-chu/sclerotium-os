"""MiroFish Full-Body Genome — 三系统统一进化引擎。

整合 sclerotium-os (191工具) + fungal-cortex (6007技能) + MiroFish (6D FCPI)
的进化数据，实现跨系统统一进化。

进化维度 (8D):
  1. Coding        (MiroFish) — 代码质量
  2. Coordination  (sclerotium) — 工具链成功率
  3. Safety        (sclerotium) — 操作安全性
  4. Decision      (MiroFish) — 决策质量
  5. Emergence     (MiroFish) — 涌现行为
  6. Performance   (sclerotium) — 响应速度
  7. Tool Fitness  (sclerotium) — 用进废退 — NEW
  8. System Health (fungal) — 器官健康度 — NEW

数据流:
  sclerotium → mirofish_bridge → this genome ← mycelium_bridge ← fungal-cortex
                    ↓
              MiroFish REST API → dashboard_scifi.py
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("mirofish.genome")

# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class GenomeSnapshot:
    generation: int = 0
    total_fitness: float = 0.0
    total_mutations: int = 0
    improvements: int = 0
    dimensions: dict[str, Any] = field(default_factory=dict)
    top_tools: list[dict] = field(default_factory=list)
    best_personality: dict = field(default_factory=dict)
    best_provider: dict = field(default_factory=dict)
    organ_health: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class FullBodyGenome:
    """MiroFish 三系统统一进化基因组。

    接收来自三个系统的进化信号，统一评估适应度，
    输出优化建议供各系统采纳。
    """

    def __init__(self, data_path: str = "./data/mirofish_genome.json") -> None:
        self._data_path = Path(data_path)
        self._generation = 0
        self._total_mutations = 0
        self._improvements = 0

        # ── 8维适应度 ──
        self._fitness: dict[str, float] = {
            "coding": 0.82,
            "coordination": 0.76,
            "safety": 0.91,
            "decision": 0.79,
            "emergence": 0.68,
            "performance": 0.85,
            "tool_fitness": 0.5,      # 用进废退
            "system_health": 0.80,     # 器官健康
        }

        # ── 跨系统数据 ──
        self._tool_weights: dict[str, float] = {}
        self._tool_usage: dict[str, int] = {}
        self._tool_success: dict[str, int] = {}
        self._personality_scores: dict[str, float] = {}
        self._provider_scores: dict[str, float] = {}
        self._organ_health: dict[str, float] = {}
        self._skill_effectiveness: dict[str, float] = {}
        self._event_count: int = 0

        self._history: list[dict] = []
        self._load()

    # ── Data ingestion (from all 3 systems) ────────────────────────────────

    def feed_sclerotium_data(self, data: dict) -> None:
        """接收来自 sclerotium-os 的进化数据。"""
        # 工具用进废退
        if "tool_calls" in data:
            for tc in data["tool_calls"]:
                name = tc.get("name", "")
                success = tc.get("success", True)
                self._tool_usage[name] = self._tool_usage.get(name, 0) + 1
                if success:
                    self._tool_success[name] = self._tool_success.get(name, 0) + 1
                    self._tool_weights[name] = min(1.0, self._tool_weights.get(name, 0.5) + 0.02)
                else:
                    self._tool_weights[name] = max(0.0, self._tool_weights.get(name, 0.5) - 0.05)

        # 人格匹配
        if "personality" in data:
            p = data["personality"]
            score = p.get("score", 0.5)
            old = self._personality_scores.get(p["name"], 0.5)
            self._personality_scores[p["name"]] = old * 0.8 + score * 0.2

        # 提供商表现
        if "provider" in data:
            p = data["provider"]
            lat = p.get("latency_ms", 1000)
            ok = p.get("success", True)
            speed_score = max(0, 1.0 - lat / 5000)
            combined = speed_score * 0.4 + (1.0 if ok else 0.0) * 0.6
            old = self._provider_scores.get(p["name"], 0.5)
            self._provider_scores[p["name"]] = old * 0.85 + combined * 0.15

        # 协调性
        if "coordination_success" in data:
            old = self._fitness["coordination"]
            self._fitness["coordination"] = old * 0.9 + (1.0 if data["coordination_success"] else 0.0) * 0.1

        self._event_count += 1

    def feed_fungal_data(self, data: dict) -> None:
        """接收来自 fungal-cortex 的进化数据。"""
        # 器官健康
        if "organ_health" in data:
            for org, health in data["organ_health"].items():
                old = self._organ_health.get(org, 0.5)
                self._organ_health[org] = old * 0.9 + health * 0.1

        # 技能有效性
        if "skill_usage" in data:
            for skill in data["skill_usage"]:
                name = skill.get("name", "")
                effective = skill.get("effective", False)
                old = self._skill_effectiveness.get(name, 0.3)
                delta = 0.03 if effective else -0.02
                self._skill_effectiveness[name] = max(0.0, min(1.0, old + delta))

        # 计算系统健康
        if self._organ_health:
            self._fitness["system_health"] = sum(self._organ_health.values()) / len(self._organ_health)

    def feed_mirofish_fcpi(self, fcpi_vector: dict) -> None:
        """接收 MiroFish 自身的 FCPI 数据。"""
        for dim in ["coding", "decision", "emergence"]:
            if dim in fcpi_vector:
                old = self._fitness[dim]
                self._fitness[dim] = old * 0.85 + fcpi_vector[dim] * 0.15

    # ── Evolution cycle ────────────────────────────────────────────────────

    def evolve(self) -> GenomeSnapshot:
        """执行一代跨系统进化。"""
        self._generation += 1
        mutations = 0

        # 突变
        mutation_rate = 0.1 + 0.05 * math.sin(self._generation * 0.5)  # Oscillating rate
        for dim in self._fitness:
            if random.random() < mutation_rate:
                delta = random.gauss(0, 0.03)
                self._fitness[dim] = max(0.0, min(1.0, self._fitness[dim] + delta))
                mutations += 1

        self._total_mutations += mutations

        # 计算综合适应度
        total_fitness = self._calculate_total()

        # 记录改进
        if self._history:
            prev = self._history[-1].get("total_fitness", 0)
            if total_fitness > prev:
                self._improvements += 1

        # 计算工具适应度
        tool_fitness = 0.5
        if self._tool_weights:
            rates = []
            for name, w in self._tool_weights.items():
                usage = self._tool_usage.get(name, 0)
                if usage > 0:
                    rate = self._tool_success.get(name, 0) / usage
                    rates.append(rate * w)
            if rates:
                tool_fitness = sum(rates) / len(rates)
        self._fitness["tool_fitness"] = tool_fitness

        snap = self.snapshot()
        self._history.append({
            "generation": self._generation,
            "total_fitness": total_fitness,
            "mutations": mutations,
        })
        if len(self._history) > 200:
            self._history = self._history[-200:]

        self._save()
        logger.info("MiroFish Genome Gen %d: fitness=%.4f, mutations=%d",
                     self._generation, total_fitness, mutations)
        return snap

    def _calculate_total(self) -> float:
        weights = {
            "coding": 0.15, "coordination": 0.15, "safety": 0.12,
            "decision": 0.12, "emergence": 0.10, "performance": 0.10,
            "tool_fitness": 0.15, "system_health": 0.11,
        }
        total = 0.0
        for dim, w in weights.items():
            total += self._fitness.get(dim, 0.5) * w
        return round(total, 4)

    # ── Snapshot ───────────────────────────────────────────────────────────

    def snapshot(self) -> GenomeSnapshot:
        top_tools = sorted(self._tool_weights.items(), key=lambda x: x[1], reverse=True)[:8]
        best_p = max(self._personality_scores.items(), key=lambda x: x[1]) if self._personality_scores else ("sclerotium", 0.5)
        best_prov = max(self._provider_scores.items(), key=lambda x: x[1]) if self._provider_scores else ("deepseek", 0.5)

        return GenomeSnapshot(
            generation=self._generation,
            total_fitness=self._calculate_total(),
            total_mutations=self._total_mutations,
            improvements=self._improvements,
            dimensions={
                "coding": {"value": round(self._fitness["coding"], 3), "color": "#22d3ee"},
                "coordination": {"value": round(self._fitness["coordination"], 3), "color": "#a3e635"},
                "safety": {"value": round(self._fitness["safety"], 3), "color": "#fb7185"},
                "decision": {"value": round(self._fitness["decision"], 3), "color": "#fbbf24"},
                "emergence": {"value": round(self._fitness["emergence"], 3), "color": "#a78bfa"},
                "performance": {"value": round(self._fitness["performance"], 3), "color": "#34d399"},
                "tool_fitness": {"value": round(self._fitness["tool_fitness"], 3), "color": "#e879f9"},
                "system_health": {"value": round(self._fitness["system_health"], 3), "color": "#fb923c"},
            },
            top_tools=[{"name": t, "weight": round(w, 3)} for t, w in top_tools],
            best_personality={"name": best_p[0], "score": round(best_p[1], 3)},
            best_provider={"name": best_prov[0], "score": round(best_prov[1], 3)},
            organ_health=dict(self._organ_health),
        )

    def get_api_data(self) -> dict:
        """返回前端仪表盘所需的完整基因组数据。"""
        s = self.snapshot()
        return {
            "generation": s.generation,
            "total_fitness": s.total_fitness,
            "total_mutations": s.total_mutations,
            "improvements": s.improvements,
            "dimensions": [
                {"name": "Coding", "genes": 1, "fitness": self._fitness["coding"], "color": "#22d3ee", "icon": "💻"},
                {"name": "Coordination", "genes": 1, "fitness": self._fitness["coordination"], "color": "#a3e635", "icon": "🔗"},
                {"name": "Safety", "genes": 1, "fitness": self._fitness["safety"], "color": "#fb7185", "icon": "🛡️"},
                {"name": "Decision", "genes": 1, "fitness": self._fitness["decision"], "color": "#fbbf24", "icon": "🧠"},
                {"name": "Emergence", "genes": 1, "fitness": self._fitness["emergence"], "color": "#a78bfa", "icon": "✨"},
                {"name": "Performance", "genes": 1, "fitness": self._fitness["performance"], "color": "#34d399", "icon": "⚡"},
                {"name": "Tool Fitness", "genes": len(self._tool_weights), "fitness": self._fitness["tool_fitness"], "color": "#e879f9", "icon": "🔧"},
                {"name": "Sys Health", "genes": len(self._organ_health), "fitness": self._fitness["system_health"], "color": "#fb923c", "icon": "❤️"},
            ],
            "top_tools": s.top_tools,
            "best_personality": s.best_personality,
            "best_provider": s.best_provider,
            "organ_health": s.organ_health,
            "event_count": self._event_count,
        }

    # ── Persistence ────────────────────────────────────────────────────────

    def _save(self) -> None:
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._data_path, "w", encoding="utf-8") as f:
            json.dump(self.get_api_data(), f, ensure_ascii=False, indent=2, default=str)

    def _load(self) -> None:
        if not self._data_path.exists():
            return
        try:
            with open(self._data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._generation = data.get("generation", 0)
            self._total_mutations = data.get("total_mutations", 0)
            self._improvements = data.get("improvements", 0)
            if "dimensions" in data:
                for d in data["dimensions"]:
                    key = d["name"].lower().replace(" ", "_")
                    if key in self._fitness:
                        self._fitness[key] = d.get("fitness", 0.5)
        except Exception:
            pass


# ── Global singleton ────────────────────────────────────────────────────────

_genome_instance: FullBodyGenome | None = None

def get_genome() -> FullBodyGenome:
    global _genome_instance
    if _genome_instance is None:
        _genome_instance = FullBodyGenome()
    return _genome_instance
