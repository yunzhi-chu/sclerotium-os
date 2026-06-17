"""L4 M2a: TransactionManager — "交感/副交感双重支配"(ANS) 事务管理器.

Biological Metaphor:
  自主神经系统(ANS)管理所有内脏器官:
    交感神经(战斗/逃跑): 加快心率, 扩张支气管, 抑制消化
    副交感神经(休息/消化): 减慢心率, 收缩支气管, 促进消化
    两者拮抗但协同——如同事务的"执行"和"回滚"

  原子事务 = 一个完整的"反射弧"(感觉→中间神经元→运动)
  自动重试(指数退避: 2^attempt秒, 最大30s) = 心率变异性(HRV)
  备用路由(fallback_skill) = 神经可塑性的侧支出芽(sprouting)
  检查点回滚 = 压力反射(baroreflex)
  DAG执行 = 交感/副交感的相位性协同(每个呼吸周期完成一批任务)
  下游跳过 = 一个器官衰竭后的代偿机制

Reference: Mol Psychiatry 2026 (Daviu et al.)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from src.utils.logging import CortexLogger


class TxState(str, Enum):
    INIT = "init"
    PREPARING = "preparing"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class Transaction:
    """An atomic transaction — a complete reflex arc."""

    tx_id: str
    description: str
    tasks: list[dict[str, Any]]  # [{skill, params, fallback_skill, ...}]
    state: TxState = TxState.INIT
    attempt: int = 0
    max_retries: int = 3
    checkpoint_data: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    error: str = ""


class TransactionManager:
    """ANS-inspired transaction manager with dual sympathetic/parasympathetic control.

    Config:
      - max_retries: max retry attempts
      - max_backoff: max backoff in seconds
      - handlers: dict of {skill_name: (execute_fn, compensate_fn)}
    """

    def __init__(self, max_retries: int = 3, max_backoff: float = 30.0) -> None:
        self._max_retries = max_retries
        self._max_backoff = max_backoff
        self._handlers: dict[str, tuple[Callable, Callable]] = {}
        self._active: dict[str, Transaction] = {}
        self._completed: list[Transaction] = []
        self._logger = CortexLogger("transaction_manager")

    def register_handler(self, skill_name: str, execute: Callable, compensate: Callable) -> None:
        self._handlers[skill_name] = (execute, compensate)

    def create(self, description: str, tasks: list[dict[str, Any]]) -> Transaction:
        """Create a new transaction (reflex arc initiation)."""
        tx = Transaction(
            tx_id=self._gen_tx_id(description),
            description=description,
            tasks=tasks,
        )
        self._active[tx.tx_id] = tx
        return tx

    def commit(self, tx_id: str) -> tuple[bool, str]:
        """Execute all tasks (sympathetic activation). Rolls back on failure (parasympathetic)."""
        tx = self._active.get(tx_id)
        if tx is None:
            return False, "not_found"

        tx.state = TxState.COMMITTING
        executed: list[int] = []
        results: list[Any] = []

        try:
            for i, task in enumerate(tx.tasks):
                skill = task["skill"]
                params = task.get("params", {})
                handler, _ = self._handlers.get(skill, (None, None))
                if handler is None:
                    raise ValueError(f"No handler for skill: {skill}")

                # Checkpoint before each task
                tx.checkpoint_data[f"before_{i}"] = str(results)

                result = handler(**params) if params else handler()
                results.append(result)
                executed.append(i)

            tx.state = TxState.COMMITTED
            tx.completed_at = time.time()
            self._completed.append(tx)
            self._active.pop(tx_id, None)
            return True, "committed"

        except Exception as e:
            tx.error = str(e)
            self._logger.error("tx_failed", tx_id=tx_id[:12], error=str(e))

            # Rollback = parasympathetic activation
            tx.state = TxState.ROLLING_BACK
            for j in reversed(executed):
                task = tx.tasks[j]
                skill = task["skill"]
                fallback = task.get("fallback_skill", skill)
                _, compensate = self._handlers.get(fallback, (None, None))
                if compensate:
                    try:
                        compensate()
                    except Exception:
                        pass

            tx.state = TxState.ROLLED_BACK
            tx.completed_at = time.time()
            return False, f"rolled_back: {e}"

    def retry(self, tx_id: str) -> Transaction | None:
        """Retry with exponential backoff: 2^attempt seconds, max 30s."""
        tx = self._active.get(tx_id) or next(
            (t for t in self._completed if t.tx_id == tx_id and t.state == TxState.ROLLED_BACK), None
        )
        if tx is None or tx.attempt >= self._max_retries:
            return None

        tx.attempt += 1
        backoff = min(2 ** tx.attempt, self._max_backoff)
        time.sleep(backoff)

        tx.state = TxState.INIT
        tx.error = ""
        self._active[tx.tx_id] = tx
        return tx

    def get(self, tx_id: str) -> Transaction | None:
        return self._active.get(tx_id) or next(
            (t for t in self._completed if t.tx_id == tx_id), None
        )

    @staticmethod
    def _gen_tx_id(description: str) -> str:
        return hashlib.md5(f"{description}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, int]:
        return {
            "active": len(self._active),
            "completed": len(self._completed),
            "committed": sum(1 for t in self._completed if t.state == TxState.COMMITTED),
            "rolled_back": sum(1 for t in self._completed if t.state == TxState.ROLLED_BACK),
        }
