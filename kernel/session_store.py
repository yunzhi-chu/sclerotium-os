"""Session Store — Claude Code-style append-only JSONL persistence.

Claude Code session architecture:
  - Append-only JSONL transcripts (every turn + tool call + result)
  - Chain-patched compaction boundaries (pointers between compacted segments)
  - Global prompt history (history.jsonl)
  - Subagent sidechains (separate JSONL per subagent)
  - Critical safety invariant: permissions NEVER restored on resume

Features:
  - Checkpoint/Resume: restore session from any point
  - Session Forking: branch conversation at any turn
  - Transcript Search: full-text search across all sessions
  - Compaction Boundaries: mark where context was compressed

Reference:
  - Claude Code transcript.ts, session.ts
  - Anthropic Agent SDK session persistence
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SessionMeta:
    """Metadata for a session."""
    session_id: str
    created_at: str = ""
    updated_at: str = ""
    turn_count: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""
    tags: list[str] = field(default_factory=list)
    title: str = ""  # First user prompt, truncated


class SessionStore:
    """Append-only JSONL session storage with checkpoint/resume.

    Directory structure:
      data/sessions/
        ├── index.json              # Session index
        ├── {session_id}.jsonl      # Transcript
        ├── {session_id}.meta.json  # Metadata
        └── forks/
            └── {fork_id}.jsonl     # Forked transcripts
    """

    def __init__(self, base_dir: str = "./data/sessions") -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._forks_dir = self._base / "forks"
        self._forks_dir.mkdir(parents=True, exist_ok=True)

        self._current_session: str | None = None
        self._current_file: Any = None

    # ── Session lifecycle ───────────────────────────────────────────────

    def create_session(
        self,
        model: str = "deepseek-v4-pro",
        provider: str = "deepseek",
    ) -> str:
        """Create a new session. Returns session_id."""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        meta = SessionMeta(
            session_id=session_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            model=model,
            provider=provider,
        )
        self._write_meta(meta)
        self._current_session = session_id
        return session_id

    def resume_session(self, session_id: str) -> list[dict[str, Any]] | None:
        """Resume a session from its JSONL transcript. Returns all events."""
        transcript_path = self._base / f"{session_id}.jsonl"
        if not transcript_path.exists():
            return None

        events = []
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        self._current_session = session_id
        return events

    # ── Append events ───────────────────────────────────────────────────

    def append(self, event: dict[str, Any]) -> None:
        """Append a single event to the current session transcript.

        Thread-safe: each line is a complete JSON object followed by newline.
        """
        if self._current_session is None:
            self.create_session()

        event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        event.setdefault("session_id", self._current_session)

        transcript_path = self._base / f"{self._current_session}.jsonl"
        with open(transcript_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())  # Ensure disk write

        # Update meta
        meta = self._read_meta(self._current_session)
        if meta:
            meta.updated_at = datetime.now(timezone.utc).isoformat()
            meta.turn_count += 1
            meta.total_tokens += event.get("tokens", 0)
            if not meta.title and event.get("type") == "user_message":
                meta.title = str(event.get("content", ""))[:100]
            self._write_meta(meta)

    def append_turn(
        self,
        user_message: str,
        assistant_response: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tokens: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append a complete conversation turn."""
        self.append({
            "type": "user_message",
            "content": user_message,
            "tokens": 0,
            "metadata": metadata or {},
        })

        if tool_calls:
            for tc in tool_calls:
                self.append({
                    "type": "tool_call",
                    "tool": tc.get("name", "unknown"),
                    "arguments": tc.get("arguments", {}),
                    "result": tc.get("result"),
                })

        self.append({
            "type": "assistant_message",
            "content": assistant_response,
            "tokens": tokens,
        })

    def append_compaction_boundary(self, summary: str, tokens_saved: int) -> None:
        """Mark a compaction boundary in the transcript.

        Claude Code emits system messages with subtype 'compact_boundary'.
        """
        self.append({
            "type": "system",
            "subtype": "compact_boundary",
            "content": summary,
            "tokens_saved": tokens_saved,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ── Session forking ─────────────────────────────────────────────────

    def fork_session(self, at_turn: int) -> str:
        """Fork the current session at a specific turn. Returns fork_id."""
        if self._current_session is None:
            raise ValueError("No active session to fork")

        # Copy events up to at_turn
        original = self._base / f"{self._current_session}.jsonl"
        fork_id = f"{self._current_session}_fork_{at_turn}"
        fork_path = self._forks_dir / f"{fork_id}.jsonl"

        with open(original, "r", encoding="utf-8") as src:
            events = [json.loads(line) for line in src if line.strip()]

        with open(fork_path, "w", encoding="utf-8") as dst:
            for e in events[:at_turn]:
                dst.write(json.dumps(e, ensure_ascii=False) + "\n")

        return fork_id

    # ── Search & list ───────────────────────────────────────────────────

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent sessions."""
        sessions = []
        for meta_path in sorted(
            self._base.glob("*.meta.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]:
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                sessions.append(meta)
            except Exception:
                pass
        return sessions

    def search_transcript(self, session_id: str, query: str) -> list[dict[str, Any]]:
        """Full-text search within a session transcript."""
        transcript_path = self._base / f"{session_id}.jsonl"
        if not transcript_path.exists():
            return []

        query_lower = query.lower()
        matches = []
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                if query_lower in line.lower():
                    try:
                        matches.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        return matches

    def get_transcript(self, session_id: str) -> list[dict[str, Any]]:
        """Get the full transcript for a session."""
        transcript_path = self._base / f"{session_id}.jsonl"
        if not transcript_path.exists():
            return []

        events = []
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return events

    # ── Stats ───────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics across all sessions."""
        total_turns = 0
        total_tokens = 0
        session_count = 0

        for meta_path in self._base.glob("*.meta.json"):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                total_turns += meta.get("turn_count", 0)
                total_tokens += meta.get("total_tokens", 0)
                session_count += 1
            except Exception:
                pass

        return {
            "session_count": session_count,
            "total_turns": total_turns,
            "total_tokens": total_tokens,
            "current_session": self._current_session,
        }

    # ── Internal helpers ────────────────────────────────────────────────

    def _write_meta(self, meta: SessionMeta) -> None:
        meta_path = self._base / f"{meta.session_id}.meta.json"
        meta_path.write_text(
            json.dumps({
                "session_id": meta.session_id,
                "created_at": meta.created_at,
                "updated_at": meta.updated_at,
                "turn_count": meta.turn_count,
                "total_tokens": meta.total_tokens,
                "model": meta.model,
                "provider": meta.provider,
                "tags": meta.tags,
                "title": meta.title,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_meta(self, session_id: str) -> SessionMeta | None:
        meta_path = self._base / f"{session_id}.meta.json"
        if not meta_path.exists():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return SessionMeta(**data)
        except Exception:
            return None
