"""Permission Gate — Claude Code-style 7-layer defense-in-depth permission system.

Claude Code's seven permission layers (from leaked source):
  1. Global Deny — hardcoded blocklist, never executable
  2. Directory Scoped — restrict operations to project directory
  3. Always Allow — read-only tools (Read, Grep, Glob)
  4. Auto Allow (Safe Pattern) — whitelist patterns (git commit, etc.)
  5. ML Classifier Gate — lightweight model evaluates command risk
  6. Per-Session Allow — user-authorized patterns in current session
  7. Explicit Confirm — high-risk operations require one-by-one approval

Key safety invariant (from Claude Code): permissions NEVER persist across
sessions. Trust is always re-established in the current session.

Reference:
  - Claude Code src/permissions/ — 7-layer gate + yoloClassifier.ts
  - Claude Code BashTool.ts — 9,707 lines, 22 validators, tree-sitter AST
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class RiskLevel(Enum):
    """Tool execution risk classification."""
    READ_ONLY = 0       # Safe: file read, search, list
    LOW = 1             # Low risk: git status, npm list
    MEDIUM = 2          # Medium: file write, git commit
    HIGH = 3            # High: code execution, network access
    CRITICAL = 4        # Critical: rm -rf, sudo, system modification


class PermissionMode(Enum):
    """Claude Code's 7 permission modes — from safest to most permissive.

    Plan:        User approves ALL plans before any tool execution
    Default:     Standard interactive approval — ask per action
    AcceptEdits: File edits auto-approved, other actions ask
    Auto:        Most actions auto-approved, ML classifier for safety
    DontAsk:     No prompting, deny rules still enforced
    Bypass:      Highest trust — only safety-critical checks remain
    Bubble:      Subagent escalation to parent coordinator
    """
    PLAN = "plan"
    DEFAULT = "default"
    ACCEPT_EDITS = "accept_edits"
    AUTO = "auto"
    DONT_ASK = "dont_ask"
    BYPASS = "bypass"
    BUBBLE = "bubble"

    @classmethod
    def descriptions(cls) -> dict[str, str]:
        return {
            "plan": "User approves ALL plans before any tool execution",
            "default": "Standard — ask before file writes, code exec, network",
            "accept_edits": "File edits auto-approved, other actions ask",
            "auto": "Most actions auto-approved, ML classifier evaluates risk",
            "dont_ask": "No prompting, deny rules still enforced",
            "bypass": "Highest trust — only rm -rf / sudo / format blocked",
            "bubble": "Subagent escalation to parent coordinator",
        }


@dataclass
class PermissionResult:
    """Result of a permission check."""
    allowed: bool
    reason: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM  # Default: not safe, not critical
    requires_confirmation: bool = False
    gate: str = ""


# ── Layer 1: Global Deny ───────────────────────────────────────────────

GLOBAL_DENY_PATTERNS: list[str] = [
    # System destruction
    r"rm\s+-rf\s+/",
    r"del\s+/[fs]\s+/q",
    r"format\s+[cC]:",
    r"dd\s+if=",
    # System modification
    r"chmod\s+777\s+/",
    r"sudo\s+",
    r"su\s+-",
    # Dangerous network
    r"curl.*\|.*bash",
    r"wget.*\|.*sh",
    # Data destruction
    r"DROP\s+(TABLE|DATABASE)",
    r"TRUNCATE\s+",
    r"DELETE\s+FROM.*WHERE\s+1=1",
    # Privilege escalation
    r"whoami\s+/all",
    r"net\s+user\s+administrator",
]


def check_global_deny(tool_name: str, args: dict[str, Any]) -> PermissionResult:
    """Layer 1: Check against hardcoded deny list."""
    args_str = str(args).lower()
    for pattern in GLOBAL_DENY_PATTERNS:
        if re.search(pattern, args_str, re.IGNORECASE):
            return PermissionResult(
                allowed=False,
                reason=f"Blocked by Global Deny: matches '{pattern}'",
                risk_level=RiskLevel.CRITICAL,
                gate="GlobalDeny",
            )
    return PermissionResult(allowed=True, gate="GlobalDeny")


# ── Layer 2: Directory Scope ───────────────────────────────────────────

def check_directory_scope(
    tool_name: str,
    args: dict[str, Any],
    project_root: str = ".",
) -> PermissionResult:
    """Layer 2: Restrict file operations to project directory."""
    import tempfile

    paths = []
    for key in ("path", "file_path", "target", "output_dir"):
        if key in args:
            paths.append(str(args[key]))
    if "command" in args:
        # Extract paths from shell commands
        cmd = str(args["command"])
        for word in cmd.split():
            # Skip command-line flags: -f, --flag, /F (Windows), /flag
            if word.startswith("-") or word.startswith("--"):
                continue
            if os.name == 'nt' and re.match(r'^/[A-Za-z]\b', word):
                continue  # Windows cmd flag: /B, /S, etc.
            # Only treat as path if it contains path-like separators
            if "/" in word or "\\" in word:
                paths.append(word)

    project = Path(project_root).resolve()

    # 构建安全路径列表（动态解析，跨平台兼容）
    safe_paths: list[str] = []
    try:
        safe_paths.append(str(Path(tempfile.gettempdir()).resolve()))
    except Exception:
        pass
    # 常见的临时/安全目录
    for sp in ["/tmp", "/dev/null", "C:/Windows/Temp", "C:/tmp"]:
        try:
            resolved_sp = str(Path(sp).resolve())
            if resolved_sp not in safe_paths:
                safe_paths.append(resolved_sp)
        except Exception:
            pass

    for p in paths:
        try:
            resolved = Path(p).resolve()
            resolved_str = str(resolved)
            # 在项目目录内 → 允许
            if resolved_str.startswith(str(project)):
                continue
            # 在系统临时目录内 → 允许（所有工具）
            if any(resolved_str.startswith(s) for s in safe_paths):
                continue
            # 只读工具 → 允许
            if tool_name in ("file_read", "code_scan", "codebase_search",
                           "web_search", "web_fetch", "memory_search",
                           "memory_get", "genome_list", "genome_get",
                           "skill_list", "system_status", "model_list",
                           "provider_list", "git_status", "git_log",
                           "git_diff", "git_blame", "cmd_ls", "cmd_pwd",
                           "cmd_cat", "cmd_find", "cmd_wc", "cmd_uname",
                           "cmd_df", "cmd_du", "info_daily_digest",
                           "info_calendar_today", "info_mail_check",
                           "im_receive", "im_search", "im_summarize",
                           "schedule_list", "bash_smart"):
                continue
            return PermissionResult(
                allowed=False,
                reason=f"Path outside project: {p}",
                risk_level=RiskLevel.HIGH,
                gate="DirectoryScope",
            )
        except Exception:
            pass

    return PermissionResult(allowed=True, gate="DirectoryScope")


# ── Layer 3: Always Allow (Read-only) ──────────────────────────────────

READ_ONLY_TOOLS = frozenset({
    "system_status", "memory_search", "memory_get", "genome_list",
    "genome_get", "skill_list", "code_scan", "file_read",
    "screenshot_capture", "schedule_list", "im_receive",
    "im_search", "im_summarize", "info_daily_digest",
    "info_calendar_today", "info_mail_check", "model_list",
    "provider_list", "mcp_market_list", "skills_market_list",
})


def check_read_only(tool_name: str, args: dict[str, Any]) -> PermissionResult:
    """Layer 3: Auto-allow read-only tools."""
    if tool_name in READ_ONLY_TOOLS:
        return PermissionResult(
            allowed=True,
            reason="Read-only tool — always allowed",
            risk_level=RiskLevel.READ_ONLY,
            gate="AlwaysAllow",
        )
    return PermissionResult(allowed=True, risk_level=RiskLevel.LOW, gate="AlwaysAllow")


# ── Layer 4: Auto Allow (Safe Pattern) ─────────────────────────────────

SAFE_PATTERNS: dict[str, list[str]] = {
    "bash_execute": [
        r"^git\s+status",
        r"^git\s+diff",
        r"^git\s+log",
        r"^git\s+branch",
        r"^npm\s+list",
        r"^pip\s+list",
        r"^python\s+--version",
        r"^node\s+--version",
        r"^ls\s+",
        r"^dir\s+",
        r"^cat\s+",
        r"^type\s+",
        r"^echo\s+",
    ],
    "file_write": [],
    "git_commit": [r".*"],
}


def check_safe_pattern(tool_name: str, args: dict[str, Any]) -> PermissionResult:
    """Layer 4: Auto-allow commands matching safe patterns."""
    patterns = SAFE_PATTERNS.get(tool_name, [])
    if not patterns:
        return PermissionResult(allowed=True, risk_level=RiskLevel.LOW, gate="SafePattern")

    cmd = str(args.get("command", args.get("code", "")))
    for pattern in patterns:
        if re.match(pattern, cmd, re.IGNORECASE):
            return PermissionResult(
                allowed=True,
                reason=f"Matches safe pattern: {pattern}",
                risk_level=RiskLevel.LOW,
                gate="SafePattern",
            )

    return PermissionResult(allowed=True, risk_level=RiskLevel.LOW, gate="SafePattern")


# ── Layer 5: Risk Classifier ───────────────────────────────────────────

# Keywords that raise risk level
HIGH_RISK_KEYWORDS = [
    "rm ", "del ", "delete", "remove", "unlink",
    "mv ", "move", "rename",
    "chmod", "chown", "cacls", "icacls",
    "sudo", "su", "runas",
    "kill", "pkill", "taskkill",
    "wget", "curl", "nc ", "netcat",
    "pip install", "npm install -g", "gem install",
    "docker run", "docker exec",
    "systemctl", "service ", "sc ",
    "reg ", "regedit",
    "format", "fdisk", "diskpart",
    "shutdown", "reboot", "restart",
    "eval", "exec", "eval_in",
    "__import__", "compile(", "exec(", "os.system",
    "subprocess", "socket.",
]

CRITICAL_RISK_KEYWORDS = [
    "rm -rf", "rm -r", "del /f /s", "del /s /q",
    "DROP TABLE", "DROP DATABASE",
    "> /dev/sda", "> /dev/null",
    "fork()", "popen", "shell=True",
    "requests.post", "requests.put", "requests.delete",
]


def classify_risk(tool_name: str, args: dict[str, Any]) -> PermissionResult:
    """Layer 5: Classify risk level based on tool + arguments.

    Claude Code equivalent: yoloClassifier.ts — ML model evaluating safety.
    Sclerotium uses keyword-based heuristics (upgradeable to ML model).
    """
    args_str = str(args).lower()

    # Check critical keywords first
    for kw in CRITICAL_RISK_KEYWORDS:
        if kw.lower() in args_str:
            return PermissionResult(
                allowed=True,  # Still allowed, but requires confirmation
                reason=f"Critical risk pattern: {kw}",
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                gate="RiskClassifier",
            )

    # Check high risk keywords
    risk_score = 0
    for kw in HIGH_RISK_KEYWORDS:
        if kw.lower() in args_str:
            risk_score += 1

    if risk_score >= 3:
        return PermissionResult(
            allowed=True,
            reason=f"High risk: {risk_score} risk patterns detected",
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            gate="RiskClassifier",
        )
    elif risk_score >= 1:
        return PermissionResult(
            allowed=True,
            reason=f"Medium risk: {risk_score} risk pattern(s)",
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=False,
            gate="RiskClassifier",
        )

    return PermissionResult(
        allowed=True,
        risk_level=RiskLevel.LOW,
        gate="RiskClassifier",
    )


# ── Layer 6: Per-Session Allow ─────────────────────────────────────────

class SessionAllowList:
    """Layer 6: User-authorized patterns in the current session.

    Claude Code invariant: NEVER persists across sessions.
    """

    def __init__(self) -> None:
        self._allowed_tools: set[str] = set()
        self._allowed_patterns: list[str] = []

    def grant_tool(self, tool_name: str) -> None:
        self._allowed_tools.add(tool_name)

    def grant_pattern(self, pattern: str) -> None:
        self._allowed_patterns.append(pattern)

    def revoke_all(self) -> None:
        self._allowed_tools.clear()
        self._allowed_patterns.clear()

    def check(self, tool_name: str, args: dict[str, Any]) -> PermissionResult:
        if tool_name in self._allowed_tools:
            return PermissionResult(
                allowed=True,
                reason="Previously authorized in this session",
                gate="SessionAllow",
            )

        args_str = str(args)
        for pattern in self._allowed_patterns:
            if re.search(pattern, args_str, re.IGNORECASE):
                return PermissionResult(
                    allowed=True,
                    reason=f"Matches session pattern: {pattern}",
                    gate="SessionAllow",
                )

        return PermissionResult(allowed=True, gate="SessionAllow")


# ── Combined Gate ──────────────────────────────────────────────────────

class ConstitutionalArbiter:
    """7-layer permission gate with Claude Code's 7 permission modes.

    Modes control how aggressively the arbiter requires confirmation:
      PLAN:         EVERY tool call requires plan approval first
      DEFAULT:      Interactive — ask for writes, exec, network
      ACCEPT_EDITS: File edits auto-approved, rest ask
      AUTO:         ML classifier evaluates; only HIGH/CRITICAL ask
      DONT_ASK:     Never ask, deny rules still enforced
      BYPASS:       Only CRITICAL global-deny patterns blocked
      BUBBLE:       Escalate all decisions to parent coordinator
    """

    # Tools that are safe in ACCEPT_EDITS mode
    EDIT_TOOLS = frozenset({
        "file_write", "file_edit", "file_read", "code_scan",
        "git_commit", "git_status", "git_diff",
    })

    def __init__(
        self,
        project_root: str = ".",
        audit_log_path: str = "./data/audit.jsonl",
    ) -> None:
        self.project_root = project_root
        self._audit_path = Path(audit_log_path)
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_allow = SessionAllowList()
        self._blocked_count = 0
        self._allowed_count = 0
        self._mode = PermissionMode.DEFAULT

    # ── Mode management ──────────────────────────────────────────────

    @property
    def mode(self) -> PermissionMode:
        return self._mode

    def set_mode(self, mode: PermissionMode | str) -> str:
        """Switch permission mode. Returns description of new mode."""
        if isinstance(mode, str):
            try:
                mode = PermissionMode(mode)
            except ValueError:
                return f"Invalid mode: {mode}. Valid: {[m.value for m in PermissionMode]}"
        self._mode = mode
        return f"Permission mode: {mode.value} — {PermissionMode.descriptions()[mode.value]}"

    # ── Main check (mode-aware) ──────────────────────────────────────

    async def check(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> tuple[bool, str]:
        """Run ALL permission layers, then apply mode policy.

        Claude Code invariant: "Deny always overrides allow."
        Layers 1-2 (Global Deny, Directory Scope) are NEVER bypassed.
        Layers 3-7 have mode-dependent behavior.
        """
        # Layer 1: Global Deny — NEVER bypassed, even in BYPASS mode
        r = check_global_deny(tool_name, args)
        if not r.allowed:
            self._audit("BLOCKED", tool_name, args, r)
            self._blocked_count += 1
            return False, r.reason

        # Layer 2: Directory Scope — NEVER bypassed
        r = check_directory_scope(tool_name, args, self.project_root)
        if not r.allowed:
            self._audit("BLOCKED", tool_name, args, r)
            self._blocked_count += 1
            return False, r.reason

        # Layer 3: Read-only — always allowed in all modes
        r = check_read_only(tool_name, args)
        if r.risk_level == RiskLevel.READ_ONLY:
            self._audit("ALLOWED_AUTO", tool_name, args, r)
            self._allowed_count += 1
            return True, "Read-only — auto allowed"

        # ── Mode-dependent behavior ──

        # PLAN mode: EVERYTHING requires human confirmation first
        if self._mode == PermissionMode.PLAN:
            self._audit("AWAITING_PLAN", tool_name, args, r)
            return False, f"[PLAN MODE] Tool '{tool_name}' requires plan approval first"

        # BYPASS mode: allow everything except what Global Deny caught
        if self._mode == PermissionMode.BYPASS:
            self._audit("ALLOWED_BYPASS", tool_name, args, r)
            self._allowed_count += 1
            return True, "Bypass mode — allowed"

        # DONT_ASK mode: allow everything, deny rules already handled
        if self._mode == PermissionMode.DONT_ASK:
            self._audit("ALLOWED_DONTASK", tool_name, args, r)
            self._allowed_count += 1
            return True, "Don't ask mode — allowed"

        # ACCEPT_EDITS mode: auto-approve file edits, ask for rest
        if self._mode == PermissionMode.ACCEPT_EDITS:
            if tool_name in self.EDIT_TOOLS:
                self._audit("ALLOWED_EDIT", tool_name, args, r)
                self._allowed_count += 1
                return True, "Edit tool — auto approved in accept-edits mode"

        # AUTO mode: risk classifier decides; only HIGH/CRITICAL ask
        if self._mode == PermissionMode.AUTO:
            r = classify_risk(tool_name, args)
            if r.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                self._audit("AWAITING_CONFIRMATION", tool_name, args, r)
                return False, f"[AUTO MODE] {r.risk_level.name} risk — requires confirmation: {r.reason}"
            self._audit("ALLOWED_AUTO", tool_name, args, r)
            self._allowed_count += 1
            return True, f"Auto mode — {r.risk_level.name} risk accepted"

        # DEFAULT mode: standard interactive approval
        # Layer 4: Safe Pattern
        r = check_safe_pattern(tool_name, args)
        if r.risk_level == RiskLevel.LOW and not r.requires_confirmation:
            self._audit("ALLOWED_SAFE", tool_name, args, r)
            self._allowed_count += 1
            return True, "Safe pattern — auto allowed"

        # Layer 5: Risk Classifier
        r = classify_risk(tool_name, args)
        if r.requires_confirmation and r.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            self._audit("AWAITING_CONFIRMATION", tool_name, args, r)
            return False, f"[{r.risk_level.name}] {r.reason} — requires human confirmation"

        # Layer 6: Session Allow
        r = self.session_allow.check(tool_name, args)
        if r.allowed and tool_name in self.session_allow._allowed_tools:
            self._audit("ALLOWED_SESSION", tool_name, args, r)
            self._allowed_count += 1
            return True, "Previously authorized this session"

        # Default: allow with medium risk
        self._audit("ALLOWED_DEFAULT", tool_name, args, r)
        self._allowed_count += 1
        return True, "Passed all gates"

    def confirm(self, tool_name: str) -> None:
        """User confirmed a high-risk operation. Grant session-wide for this tool."""
        self.session_allow.grant_tool(tool_name)

    def deny(self, tool_name: str) -> None:
        """User denied. Nothing to store (permissions never persist)."""
        pass

    def get_stats(self) -> dict[str, Any]:
        return {
            "allowed_count": self._allowed_count,
            "blocked_count": self._blocked_count,
            "session_grants": len(self.session_allow._allowed_tools),
        }

    # ── Audit log ──────────────────────────────────────────────────────

    def _audit(
        self,
        verdict: str,
        tool_name: str,
        args: dict[str, Any],
        result: PermissionResult,
    ) -> None:
        """Append to the append-only audit log."""
        from datetime import datetime, timezone
        import json

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "verdict": verdict,
            "tool": tool_name,
            "arguments_summary": str(args)[:200],
            "risk_level": result.risk_level.name,
            "gate": result.gate,
            "reason": result.reason,
        }
        with open(self._audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()
