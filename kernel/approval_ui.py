"""Approval UI — IM channel-native approval buttons (Gap 14).

Injecting R6 (IETF AIGA Protocol T0-T4 risk model)
+ R7 (AG-UI HITL interrupts).

When the Arbiter flags a tool as NEEDS_HUMAN, an approval request
is sent to the user's preferred IM channel with interactive buttons:
  - Telegram: inline keyboard [Approve] [Reject] [Details]
  - Feishu: interactive card with confirm/deny
  - Console: y/n prompt (fallback)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("sclerotium.approval")


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class RiskLevel(str, Enum):
    """IETF AIGA T0-T4 risk tiers."""
    T0 = "t0"  # Read-only, no risk
    T1 = "t1"  # Low risk: file edit, search
    T2 = "t2"  # Medium: file write, bash exec
    T3 = "t3"  # High: network egress, system config
    T4 = "t4"  # Critical: self-modify, destructive


@dataclass(frozen=True)
class ApprovalRequest:
    """A pending approval request (immutable)."""
    request_id: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    risk_level: RiskLevel = RiskLevel.T1
    source: str = ""
    created_at: float = field(default_factory=time.time)
    status: ApprovalStatus = ApprovalStatus.PENDING

    @property
    def summary(self) -> str:
        args_str = ", ".join(f"{k}={v}" for k, v in list(self.args.items())[:3])
        return f"{self.tool}({args_str})"


class ApprovalUIManager:
    """Manages approval requests and dispatches to IM channels.

    Usage:
        mgr = ApprovalUIManager()
        mgr.set_platform_adapter(telegram_adapter)

        req = mgr.request("file_write", {"path": "config.yaml"}, risk=RiskLevel.T2)
        result = await mgr.wait_for_decision(req, timeout=60)
    """

    def __init__(self, default_timeout: float = 120.0) -> None:
        self._pending: dict[str, ApprovalRequest] = {}
        self._decisions: dict[str, ApprovalStatus] = {}
        self._events: dict[str, asyncio.Event] = {}
        self._platform_adapter: Any = None
        self._fallback_callback: Callable | None = None
        self._default_timeout = default_timeout

    def set_platform_adapter(self, adapter: Any) -> None:
        """Set the IM platform adapter for sending approval buttons."""
        self._platform_adapter = adapter

    def set_fallback_callback(self, cb: Callable[[ApprovalRequest], bool]) -> None:
        """Set fallback approval callback (e.g., console y/n prompt)."""
        self._fallback_callback = cb

    def request(
        self,
        tool: str,
        args: dict[str, Any],
        *,
        reason: str = "",
        risk: RiskLevel = RiskLevel.T2,
        source: str = "",
    ) -> ApprovalRequest:
        """Create an approval request and dispatch to IM."""
        req_id = f"apr_{uuid.uuid4().hex[:8]}"
        req = ApprovalRequest(
            request_id=req_id,
            tool=tool,
            args=args,
            reason=reason,
            risk_level=risk,
            source=source,
        )
        self._pending[req_id] = req
        self._events[req_id] = asyncio.Event()

        # Dispatch to IM platform
        asyncio.create_task(self._dispatch_approval(req))

        return req

    async def _dispatch_approval(self, req: ApprovalRequest) -> None:
        """Send approval request to the configured platform."""
        adapter = self._platform_adapter

        if adapter is None:
            # Fallback: console prompt
            if self._fallback_callback:
                approved = self._fallback_callback(req)
                await self.decide(req.request_id, approved)
            return

        # Build approval message based on platform
        platform = getattr(adapter, "platform_name", "unknown")

        if platform == "telegram":
            await self._send_telegram_approval(adapter, req)
        elif platform == "feishu":
            await self._send_feishu_approval(adapter, req)
        else:
            # Generic text-based approval
            await self._send_text_approval(adapter, req)

    async def _send_telegram_approval(self, adapter: Any, req: ApprovalRequest) -> None:
        """Send Telegram inline keyboard approval."""
        emoji = {"t1": "📝", "t2": "⚠️", "t3": "🔴", "t4": "🚫"}.get(req.risk_level.value, "❓")
        text = (
            f"{emoji} *Approval Required*\n\n"
            f"*Tool:* `{req.tool}`\n"
            f"*Reason:* {req.reason or 'No reason provided'}\n"
            f"*Risk:* {req.risk_level.value.upper()}\n"
            f"*ID:* `{req.request_id}`"
        )
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Approve", "callback_data": f"approve:{req.request_id}"},
                {"text": "❌ Reject", "callback_data": f"reject:{req.request_id}"},
            ]]
        }
        # Send via adapter's rich_content support
        await adapter.send_message(
            target=self._get_admin_chat_id(),
            content=text,
            rich_content={"keyboard": keyboard, "parse_mode": "Markdown"},
        )

    async def _send_feishu_approval(self, adapter: Any, req: ApprovalRequest) -> None:
        """Send Feishu interactive card."""
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"Approval: {req.tool}"},
                "template": "red" if req.risk_level in (RiskLevel.T3, RiskLevel.T4) else "blue",
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": f"**Reason:** {req.reason or 'N/A'}"}},
                {"tag": "div", "text": {"tag": "lark_md", "content": f"Risk: {req.risk_level.value.upper()} | ID: {req.request_id}"}},
                {"tag": "action", "actions": [
                    {"tag": "button", "text": {"tag": "plain_text", "content": "Approve"}, "type": "primary", "value": f"approve:{req.request_id}"},
                    {"tag": "button", "text": {"tag": "plain_text", "content": "Reject"}, "type": "danger", "value": f"reject:{req.request_id}"},
                ]},
            ],
        }
        await adapter.send_message(
            target=self._get_admin_chat_id(),
            content="Pending approval",
            rich_content={"card": card},
        )

    async def _send_text_approval(self, adapter: Any, req: ApprovalRequest) -> None:
        """Send plain-text approval request."""
        text = (
            f"[APPROVAL] {req.tool} | Risk: {req.risk_level.value.upper()}\n"
            f"Reason: {req.reason or 'N/A'}\n"
            f"Reply 'approve {req.request_id}' or 'reject {req.request_id}'"
        )
        await adapter.send_message(target=self._get_admin_chat_id(), content=text)

    def _get_admin_chat_id(self) -> str:
        """Get admin chat ID from config or env."""
        import os
        return os.environ.get("SCLEROTIUM_ADMIN_CHAT", "admin")

    async def decide(self, request_id: str, approved: bool) -> bool:
        """Record a decision (called from callback handler)."""
        req = self._pending.get(request_id)
        if req is None:
            return False

        status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        self._decisions[request_id] = status
        self._events[request_id].set()
        logger.info("Approval %s: %s (tool=%s)", request_id, status.value, req.tool)
        return True

    async def wait_for_decision(
        self, req: ApprovalRequest, timeout: float | None = None,
    ) -> ApprovalStatus:
        """Wait for a human decision on an approval request."""
        timeout = timeout or self._default_timeout

        try:
            await asyncio.wait_for(
                self._events[req.request_id].wait(),
                timeout=timeout,
            )
            return self._decisions.get(req.request_id, ApprovalStatus.TIMEOUT)
        except asyncio.TimeoutError:
            self._decisions[req.request_id] = ApprovalStatus.TIMEOUT
            logger.warning("Approval %s timed out after %.0fs", req.request_id, timeout)
            return ApprovalStatus.TIMEOUT

    def get_pending(self) -> list[ApprovalRequest]:
        return [r for r in self._pending.values() if r.status == ApprovalStatus.PENDING]

    def cleanup(self) -> None:
        """Clean up old decisions."""
        now = time.time()
        expired = [
            rid for rid, req in self._pending.items()
            if now - req.created_at > 3600  # 1 hour
        ]
        for rid in expired:
            self._pending.pop(rid, None)
            self._events.pop(rid, None)
            self._decisions.pop(rid, None)
