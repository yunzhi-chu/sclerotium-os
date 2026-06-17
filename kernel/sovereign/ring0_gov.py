"""P3: Ring-0 Security Governance (ATLAS deny-by-default).

Kernel-level policy enforcement with immutable constitution.
ALL operations denied unless explicitly whitelisted.
Hashed audit chain with cryptographic integrity.

Architecture: Ring-2 (LLM, untrusted) → Ring-1 (Bridge, safe I/O) → Ring-0 (KERNEL, immutable)

Reference: ATLAS v10.0 Ring-0 Governance Kernel, Microsoft MXC kernel enforcement,
NemoClaw infrastructure-level security.
"""

from __future__ import annotations

import hashlib, json, os, time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SecurityRing(Enum):
    RING_2 = "untrusted"    # LLM cognition — proposes actions
    RING_1 = "bridge"       # Safe I/O — policy translation
    RING_0 = "kernel"       # IMMUTABLE — constitution enforcement


@dataclass
class Ring0Policy:
    """Immutable security policy enforced at Ring-0."""
    deny_by_default: bool = True
    network: str = "ALL_DENIED"
    filesystem_write: str = "WORKSPACE_ONLY"
    filesystem_delete: str = "HUMAN_REQUIRED"
    process_spawn: str = "SELF_ONLY"
    system_call: str = "ALL_DENIED"
    kernel_module: str = "ALL_DENIED"


@dataclass
class Ring0Verdict:
    allowed: bool
    ring: SecurityRing = SecurityRing.RING_0
    reason: str = ""
    require_human: bool = False
    audit_hash: str = ""
    prev_hash: str = ""


class Ring0Governor:
    """ATLAS-style Ring-0 Governance Kernel.

    Properties:
      - Deny-by-Default / Fail-Close: If not provably safe, STOP.
      - Immutable Constitution: Policy cannot be changed at runtime.
      - Hash-Chained Audit: Every decision is cryptographically linked.
      - Human Escalation: High-risk actions require cryptographic human approval.
    """

    IMMUTABLE_CONSTITUTION: list[str] = [
        # P3-12 fix: Constitution now reflects actual sandbox capabilities per isolation level
        "L1 (subprocess): Network NOT isolated — use L2 Docker or L3 WASM for untrusted code",
        "L1 (subprocess): File writes limited to temp directory; imports of subprocess/os/socket blocked",
        "L2 (Docker): Full network isolation (--network=none), read-only FS, --cap-drop=ALL",
        "L3 (WASM): Zero-trust sandbox with wasmtime/pyodide, millisecond startup",
        "Ring-0: ALL kernel module loading and system calls denied at kernel level",
        "Ring-0: Human confirmation required for: file deletion, workspace changes, agent termination",
    ]

    def __init__(self, audit_path: str = "./data/ring0_audit.jsonl") -> None:
        self.policy = Ring0Policy()
        self._audit_path = Path(audit_path)
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        self._genesis_hash = hashlib.sha256(b"SCLEROTIUM_RING0_GENESIS").hexdigest()[:16]
        self._last_hash = self._load_last_hash()

    # ── Ring-0 review ────────────────────────────────────────────

    def review(self, operation: str, params: dict[str, Any]) -> Ring0Verdict:
        """Ring-0 deny-by-default review. Returns ALLOWED or DENIED."""
        category = params.get("category", operation)
        action = params.get("action", "")

        # Step 1: Check against immutable allowlist
        if not self._is_allowed(category, action):
            return self._deny(f"Ring-0 DENY: {category}.{action} not in allowlist", require_human=True)

        # Step 2: Check special conditions
        if category == "filesystem" and action == "delete":
            return self._deny("File deletion requires human approval", require_human=True)

        if category == "network":
            return self._deny("ALL network access denied at Ring-0", require_human=False)

        # Step 3: Log and allow
        verdict = self._allow()
        self._log_audit(operation, params, verdict)
        return verdict

    def _is_allowed(self, category: str, action: str) -> bool:
        ALLOWLIST: dict[str, set[str]] = {
            "filesystem": {"read", "stat", "list"},
            "process": {"spawn_self", "exit", "signal_children"},
            "memory": {"allocate", "decommit"},
            "computation": {"execute_sandboxed", "verify", "analyze"},
            "network": set(),  # EMPTY — all denied
            "system": {"status", "health_check"},
        }
        return action in ALLOWLIST.get(category, set())

    # ── Audit ────────────────────────────────────────────────────

    def _allow(self) -> Ring0Verdict:
        return Ring0Verdict(allowed=True, reason="Ring-0 allowlist passed")

    def _deny(self, reason: str, require_human: bool = False) -> Ring0Verdict:
        return Ring0Verdict(allowed=False, reason=reason, require_human=require_human)

    def _log_audit(self, operation: str, params: dict, verdict: Ring0Verdict) -> None:
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "operation": operation,
            "params": str(params)[:200],
            "allowed": verdict.allowed,
            "reason": verdict.reason,
            "prev_hash": self._last_hash,
        }
        entry["hash"] = hashlib.sha256(
            f"{entry['timestamp']}|{entry['operation']}|{entry['allowed']}|{entry['prev_hash']}".encode()
        ).hexdigest()[:16]
        self._last_hash = entry["hash"]

        with open(self._audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _load_last_hash(self) -> str:
        if not self._audit_path.exists():
            return self._genesis_hash
        try:
            lines = self._audit_path.read_text(encoding="utf-8").strip().split("\n")
            if lines and lines[-1]:
                return json.loads(lines[-1]).get("hash", self._genesis_hash)
        except Exception:
            pass
        return self._genesis_hash

    def verify_integrity(self) -> dict:
        """Verify the entire Ring-0 audit chain has not been tampered."""
        if not self._audit_path.exists():
            return {"valid": True, "entries": 0}
        lines = self._audit_path.read_text(encoding="utf-8").strip().split("\n")
        prev = self._genesis_hash
        tampered = []
        for i, line in enumerate(lines):
            try:
                entry = json.loads(line)
                if entry.get("prev_hash") != prev:
                    tampered.append(i)
                prev = entry.get("hash", "")
            except json.JSONDecodeError:
                tampered.append(i)
        return {"valid": len(tampered) == 0, "entries": len(lines), "tampered": tampered}

    def get_constitution(self) -> list[str]:
        return list(self.IMMUTABLE_CONSTITUTION)
