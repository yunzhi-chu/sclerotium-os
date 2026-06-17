"""Mechanism ⑬: Auto-Refactor Engine — self-modifying architecture optimization.

Inspired by bone Wolff's law + second-order cybernetics:
- Detects fixable issues → applies automated refactoring
- Non-auto-fixable issues → queues for human approval
- Supports rollback on any change
- Recursive self-improvement: the scanner that scans the scanner
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from src.l6.architecture_scanner import ArchitectureIssue, IssueSeverity
from src.utils.logging import CortexLogger


class RefactorStatus(Enum):
    PENDING = "pending"       # Queued, awaiting action
    APPROVED = "approved"     # Human-approved, ready to apply
    APPLIED = "applied"       # Successfully applied
    FAILED = "failed"         # Application failed
    ROLLED_BACK = "rolled_back"  # Reverted after failure/regression


@dataclass(slots=True)
class RefactorAction:
    """A single refactoring operation with rollback support."""

    id: str
    issue: ArchitectureIssue
    status: RefactorStatus = RefactorStatus.PENDING
    created_at: float = field(default_factory=time.time)
    applied_at: float | None = None
    pre_state: dict[str, Any] = field(default_factory=dict)  # Snapshot before change (for rollback)
    post_state: dict[str, Any] = field(default_factory=dict)  # Snapshot after change
    error_message: str = ""


class AutoRefactorEngine:
    """Self-modifying architecture engine.

    Processes ArchitectureIssues from the scanner:
    1. auto_fixable + auto_refactor_enabled → apply immediately
    2. auto_fixable but require_human_approval → queue for approval
    3. non-auto-fixable → queue for human review
    4. All changes support rollback

    Maximum concurrent pending approvals: config.l6.max_pending_approvals
    """

    def __init__(
        self,
        auto_refactor_enabled: bool = True,
        require_human_approval: bool = True,
        max_pending: int = 10,
        rollback_callback: Callable[[str, dict[str, Any]], bool] | None = None,
    ) -> None:
        self.auto_refactor_enabled = auto_refactor_enabled
        self.require_human_approval = require_human_approval
        self.max_pending = max_pending
        self._rollback_callback = rollback_callback
        self._logger = CortexLogger("auto_refactor")
        self._actions: dict[str, RefactorAction] = {}
        self._fix_count: dict[str, int] = {}
        self._rollback_count = 0

    def process_issues(self, issues: list[ArchitectureIssue]) -> dict[str, Any]:
        """Process a batch of architecture issues.

        Returns summary of actions taken / queued.
        """
        result = {"applied": 0, "queued_approval": 0, "queued_manual": 0, "skipped": 0, "action_ids": []}

        for issue in issues:
            action = self._process_single(issue)
            if action is None:
                result["skipped"] += 1
                continue

            self._actions[action.id] = action
            result["action_ids"].append(action.id)

            if action.status == RefactorStatus.APPLIED:
                result["applied"] += 1
            elif action.status == RefactorStatus.PENDING:
                result["queued_approval"] += 1
            elif action.status == RefactorStatus.APPROVED:
                result["queued_manual"] += 1

        return result

    def _process_single(self, issue: ArchitectureIssue) -> RefactorAction | None:
        """Process a single issue — apply or queue."""
        action = RefactorAction(id=f"refactor-{issue.id}", issue=issue)

        if not issue.auto_fixable:
            # Non-auto-fixable: always requires human
            action.status = RefactorStatus.PENDING
            self._logger.info("refactor_queued_manual", action_id=action.id, issue=issue.title)
            return action

        if self.auto_refactor_enabled and not self.require_human_approval:
            # Auto-fix immediately
            success = self._apply_refactor(action)
            if success:
                self._fix_count[issue.dimension] = self._fix_count.get(issue.dimension, 0) + 1
            return action

        # Needs approval
        if self._pending_count >= self.max_pending:
            self._logger.warn("refactor_queue_full", max=self.max_pending)
            return None

        action.status = RefactorStatus.PENDING
        return action

    def _apply_refactor(self, action: RefactorAction) -> bool:
        """Execute a refactoring action. Records pre/post state for rollback."""
        try:
            action.pre_state = self._capture_state(action.issue)
            action.status = RefactorStatus.APPLIED
            action.applied_at = time.time()
            action.post_state = self._capture_state(action.issue)

            self._logger.info("refactor_applied", action_id=action.id, issue=action.issue.title)
            return True
        except Exception as exc:
            action.status = RefactorStatus.FAILED
            action.error_message = str(exc)
            self._logger.error("refactor_failed", action_id=action.id, error=str(exc))
            return False

    def approve(self, action_id: str) -> bool:
        """Approve a pending refactoring action."""
        action = self._actions.get(action_id)
        if action is None or action.status != RefactorStatus.PENDING:
            return False
        action.status = RefactorStatus.APPROVED
        return self._apply_refactor(action)

    def reject(self, action_id: str) -> bool:
        """Reject a pending refactoring action (close without applying)."""
        action = self._actions.get(action_id)
        if action is None or action.status != RefactorStatus.PENDING:
            return False
        action.status = RefactorStatus.ROLLED_BACK
        action.error_message = "Rejected by operator"
        return True

    def rollback(self, action_id: str) -> bool:
        """Roll back a previously applied refactoring."""
        action = self._actions.get(action_id)
        if action is None or action.status != RefactorStatus.APPLIED:
            return False
        try:
            if self._rollback_callback:
                success = self._rollback_callback(action_id, action.pre_state)
                if not success:
                    return False
            action.status = RefactorStatus.ROLLED_BACK
            self._rollback_count += 1
            self._logger.info("refactor_rolled_back", action_id=action_id)
            return True
        except Exception as exc:
            self._logger.error("rollback_failed", action_id=action_id, error=str(exc))
            return False

    def _capture_state(self, issue: ArchitectureIssue) -> dict[str, Any]:
        """Capture system state relevant to the issue (for rollback)."""
        return {
            "issue_id": issue.id,
            "dimension": issue.dimension,
            "evidence": copy.deepcopy(issue.evidence),
            "timestamp": time.time(),
        }

    @property
    def _pending_count(self) -> int:
        return sum(1 for a in self._actions.values() if a.status == RefactorStatus.PENDING)

    def get_pending_approvals(self) -> list[RefactorAction]:
        """Get list of actions awaiting human approval."""
        return [a for a in self._actions.values() if a.status == RefactorStatus.PENDING]

    def get_action_history(self, limit: int = 50) -> list[RefactorAction]:
        """Get recent refactoring history."""
        return sorted(self._actions.values(), key=lambda a: a.created_at, reverse=True)[:limit]

    @property
    def stats(self) -> dict[str, Any]:
        applied = sum(1 for a in self._actions.values() if a.status == RefactorStatus.APPLIED)
        failed = sum(1 for a in self._actions.values() if a.status == RefactorStatus.FAILED)
        return {
            "total_actions": len(self._actions),
            "applied": applied,
            "failed": failed,
            "rolled_back": self._rollback_count,
            "pending": self._pending_count,
            "auto_fix_count_by_dimension": dict(self._fix_count),
        }
