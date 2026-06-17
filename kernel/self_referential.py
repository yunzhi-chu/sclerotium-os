"""Self Referential Compiler — 全系统基因组快照 (L8)。

生命体的"DNA序列化" — 将全系统状态序列化为可恢复的快照。

功能:
  - checkpoint: 保存全系统状态到文件
  - restore: 从文件恢复系统状态
  - diff: 比较两个快照的差异
  - list_checkpoints: 列出所有快照

使用方式:
    compiler = SelfReferentialCompiler()
    compiler.checkpoint(genome, tracker, store)
    compiler.restore("checkpoint_001.json")
    diffs = compiler.diff("cp1.json", "cp2.json")
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("sclerotium.selfref")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GenomeSnapshot:
    """系统基因组快照 (不可变)。"""
    snapshot_id: str
    timestamp: float = field(default_factory=time.time)
    version: str = "4.0"
    genome: dict[str, Any] = field(default_factory=dict)
    fcpi: dict[str, float] = field(default_factory=dict)
    memory_stats: dict[str, Any] = field(default_factory=dict)
    evolution_state: dict[str, Any] = field(default_factory=dict)
    rhythm_state: dict[str, Any] = field(default_factory=dict)
    organ_health: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SnapshotDiff:
    """快照差异 (不可变)。"""
    snapshot_a: str
    snapshot_b: str
    changed_keys: tuple[str, ...]
    additions: tuple[str, ...]
    removals: tuple[str, ...]
    value_changes: tuple[tuple[str, Any, Any], ...]


# ═══════════════════════════════════════════════════════════════
# SelfReferentialCompiler
# ═══════════════════════════════════════════════════════════════

class SelfReferentialCompiler:
    """全系统基因组序列化/反序列化。

    使用方式:
        compiler = SelfReferentialCompiler(snapshot_dir="./data/snapshots")
        compiler.checkpoint(genome, fcpi_tracker, memory_store)
        snapshots = compiler.list_checkpoints()
        restored = compiler.restore("snapshot_001")
    """

    def __init__(self, snapshot_dir: str = "./data/snapshots") -> None:
        self._dir = Path(snapshot_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._counter: int = 0

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def checkpoint(
        self,
        genome: Any = None,
        fcpi_tracker: Any = None,
        memory_store: Any = None,
        evolution_loop: Any = None,
        rhythm_engine: Any = None,
        awareness: Any = None,
        label: str = "",
    ) -> GenomeSnapshot:
        """保存全系统状态快照。

        Args:
            genome: StrategyGenome 实例
            fcpi_tracker: FCPITracker 实例
            memory_store: HexisMemoryStore 实例
            evolution_loop: EvolutionLoop 实例
            rhythm_engine: RhythmEngine 实例
            awareness: SelfAwareness 实例
            label: 快照标签

        Returns:
            GenomeSnapshot
        """
        self._counter += 1
        sid = f"snapshot_{self._counter:04d}"

        snapshot = GenomeSnapshot(
            snapshot_id=sid,
            genome=genome.to_dict() if hasattr(genome, 'to_dict') else {},
            fcpi=fcpi_tracker.get_vector().to_dict()
                  if hasattr(fcpi_tracker, 'get_vector') else {},
            memory_stats=memory_store.get_stats()
                         if hasattr(memory_store, 'get_stats') else {},
            evolution_state=evolution_loop.get_state().__dict__
                           if hasattr(evolution_loop, 'get_state') else {},
            rhythm_state=rhythm_engine.get_state().__dict__
                        if hasattr(rhythm_engine, 'get_state') else {},
            organ_health=awareness.get_stats()
                        if hasattr(awareness, 'get_stats') else {},
        )

        # 持久化
        filename = f"{sid}_{label or 'auto'}.json"
        filepath = self._dir / filename
        data = {
            "snapshot_id": snapshot.snapshot_id,
            "timestamp": snapshot.timestamp,
            "version": snapshot.version,
            "genome": snapshot.genome,
            "fcpi": snapshot.fcpi,
            "memory_stats": snapshot.memory_stats,
            "evolution_state": snapshot.evolution_state,
            "rhythm_state": snapshot.rhythm_state,
            "organ_health": snapshot.organ_health,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("Checkpoint saved: %s", filepath)
        return snapshot

    def restore(self, snapshot_id: str) -> GenomeSnapshot | None:
        """从文件恢复系统状态。

        Args:
            snapshot_id: 快照ID或文件名

        Returns:
            GenomeSnapshot 或 None
        """
        # 搜索匹配的文件
        matches = list(self._dir.glob(f"*{snapshot_id}*"))
        if not matches:
            return None

        filepath = matches[0]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return GenomeSnapshot(
                snapshot_id=data.get("snapshot_id", ""),
                timestamp=data.get("timestamp", 0),
                version=data.get("version", ""),
                genome=data.get("genome", {}),
                fcpi=data.get("fcpi", {}),
                memory_stats=data.get("memory_stats", {}),
                evolution_state=data.get("evolution_state", {}),
                rhythm_state=data.get("rhythm_state", {}),
                organ_health=data.get("organ_health", {}),
            )
        except Exception as e:
            logger.error("Restore failed: %s", e)
            return None

    def diff(self, snapshot_a: str, snapshot_b: str) -> SnapshotDiff | None:
        """比较两个快照的差异。"""
        a = self.restore(snapshot_a)
        b = self.restore(snapshot_b)
        if not a or not b:
            return None

        changes: list[tuple[str, Any, Any]] = []
        for key in set(a.fcpi.keys()) | set(b.fcpi.keys()):
            va = a.fcpi.get(key, 0)
            vb = b.fcpi.get(key, 0)
            if abs(va - vb) > 0.01:
                changes.append((f"fcpi.{key}", va, vb))

        additions = tuple(
            k for k in b.genome if k not in a.genome
        )
        removals = tuple(
            k for k in a.genome if k not in b.genome
        )

        return SnapshotDiff(
            snapshot_a=snapshot_a,
            snapshot_b=snapshot_b,
            changed_keys=tuple(c[0] for c in changes),
            additions=additions,
            removals=removals,
            value_changes=tuple(changes),
        )

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """列出所有快照。"""
        files = sorted(self._dir.glob("snapshot_*.json"),
                      key=os.path.getmtime, reverse=True)
        result = []
        for f in files:
            stat = f.stat()
            result.append({
                "file": f.name,
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": stat.st_mtime,
            })
        return result

    def cleanup(self, keep: int = 10) -> int:
        """清理旧快照, 只保留最近 N 个。"""
        files = sorted(self._dir.glob("snapshot_*.json"),
                      key=os.path.getmtime)
        removed = 0
        for f in files[:-keep]:
            try:
                f.unlink()
                removed += 1
            except Exception:
                pass
        return removed
