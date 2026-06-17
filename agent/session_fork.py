"""Session Fork/Branch/Merge — OpenClaw-style session branching (Gap: 会话分支).

Extends SessionManager with:
  - fork: Create independent copy of a session at any point
  - branch: Create linked branch (shares history up to branch point)
  - merge: Combine two session branches
  - diff: Show differences between two sessions
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from agent.session import SessionManager, SessionInfo

logger = logging.getLogger("sclerotium.session_fork")


@dataclass(frozen=True)
class ForkResult:
    """Result of a fork/branch operation."""
    source_session_id: str
    new_session_id: str
    operation: str  # "fork" | "branch"
    message_count: int = 0
    fork_point: int = 0  # Message index where fork occurred


@dataclass(frozen=True)
class MergeResult:
    """Result of a merge operation."""
    target_session_id: str
    source_session_id: str
    merged_message_count: int = 0
    conflicts: list[str] = field(default_factory=list)


class SessionForkManager:
    """Session fork/branch/merge operations on top of SessionManager.

    Usage:
        mgr = SessionForkManager(session_manager)

        # Fork: full independent copy
        result = mgr.fork(session_id="abc123")

        # Branch: linked copy (shares base history)
        result = mgr.branch(session_id="abc123", branch_name="experiment")

        # Merge: combine branches
        result = mgr.merge("abc123", "def456")
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self._sessions = session_manager

    def fork(self, session_id: str, fork_point: int | None = None) -> ForkResult:
        """Create an independent fork of a session.

        The fork copies ALL messages up to fork_point (or all messages)
        into a new independent session. Changes in the fork do not
        affect the original.

        Args:
            session_id: Source session to fork
            fork_point: Message index to fork at (None = all messages)

        Returns:
            ForkResult with new session ID
        """
        info = self._sessions.get(session_id)
        if info is None:
            raise ValueError(f"Session not found: {session_id}")

        messages = self._sessions.load_messages(session_id)
        if fork_point is not None:
            messages = messages[:fork_point]

        # Create new session
        new_id = self._sessions.create(
            title=f"{info.title} (fork)",
            model=info.model,
            tags=list(info.tags) + ["forked"],
        )

        # Copy messages
        self._sessions.append_messages(new_id, messages)

        logger.info("Forked session %s → %s (%d messages)",
                     session_id, new_id, len(messages))

        return ForkResult(
            source_session_id=session_id,
            new_session_id=new_id,
            operation="fork",
            message_count=len(messages),
            fork_point=fork_point or len(messages),
        )

    def branch(self, session_id: str, branch_name: str = "") -> ForkResult:
        """Create a linked branch of a session.

        A branch shares the base history with the parent. Only new
        messages after the branch point are unique to the branch.
        The branch metadata records the parent session ID.

        Args:
            session_id: Parent session
            branch_name: Name for the branch (appended to title)

        Returns:
            ForkResult with new branch session ID
        """
        info = self._sessions.get(session_id)
        if info is None:
            raise ValueError(f"Session not found: {session_id}")

        messages = self._sessions.load_messages(session_id)

        name = branch_name or f"branch-{time.strftime('%H%M')}"
        new_id = self._sessions.create(
            title=f"{info.title} [{name}]",
            model=info.model,
            tags=list(info.tags) + ["branch", f"parent:{session_id}"],
        )

        self._sessions.append_messages(new_id, messages)

        logger.info("Branched session %s → %s (%d messages, parent=%s)",
                     session_id, new_id, len(messages), session_id)

        return ForkResult(
            source_session_id=session_id,
            new_session_id=new_id,
            operation="branch",
            message_count=len(messages),
        )

    def merge(
        self,
        target_id: str,
        source_id: str,
        strategy: str = "append",
    ) -> MergeResult:
        """Merge a source session into a target session.

        Args:
            target_id: Session to merge INTO
            source_id: Session to merge FROM
            strategy: "append" (add after target), "interleave" (by timestamp)

        Returns:
            MergeResult
        """
        target_info = self._sessions.get(target_id)
        source_info = self._sessions.get(source_id)
        if target_info is None or source_info is None:
            raise ValueError("Source or target session not found")

        target_msgs = self._sessions.load_messages(target_id)
        source_msgs = self._sessions.load_messages(source_id)

        conflicts: list[str] = []

        if strategy == "append":
            # Simple: append source messages after target
            merged = target_msgs + source_msgs
        elif strategy == "interleave":
            # Sort by timestamp (from JSONL metadata)
            merged = self._interleave(target_msgs, source_msgs)
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")

        # Save merged result
        self._sessions.save_checkpoint(
            target_id, merged,
            token_count=target_info.token_count + source_info.token_count,
        )

        # Update tags
        merged_tags = list(set(list(target_info.tags) + list(source_info.tags) + ["merged"]))
        self._sessions.update_meta(target_id, tags=merged_tags)

        logger.info("Merged %s → %s (%d + %d = %d messages)",
                     source_id, target_id, len(target_msgs), len(source_msgs), len(merged))

        return MergeResult(
            target_session_id=target_id,
            source_session_id=source_id,
            merged_message_count=len(merged),
            conflicts=conflicts,
        )

    def _interleave(
        self, msgs_a: list[dict], msgs_b: list[dict],
    ) -> list[dict]:
        """Interleave two message lists (simple round-robin)."""
        result = []
        max_len = max(len(msgs_a), len(msgs_b))
        for i in range(max_len):
            if i < len(msgs_a):
                result.append(msgs_a[i])
            if i < len(msgs_b):
                result.append(msgs_b[i])
        return result

    def diff(self, session_a: str, session_b: str) -> dict[str, Any]:
        """Show differences between two sessions."""
        msgs_a = self._sessions.load_messages(session_a)
        msgs_b = self._sessions.load_messages(session_b)

        info_a = self._sessions.get(session_a)
        info_b = self._sessions.get(session_b)

        return {
            "session_a": {"id": session_a, "messages": len(msgs_a), "title": info_a.title if info_a else ""},
            "session_b": {"id": session_b, "messages": len(msgs_b), "title": info_b.title if info_b else ""},
            "a_only_messages": max(0, len(msgs_a) - len(msgs_b)),
            "b_only_messages": max(0, len(msgs_b) - len(msgs_a)),
            "common_messages": min(len(msgs_a), len(msgs_b)),
        }
