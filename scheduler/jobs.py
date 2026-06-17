"""Predefined job templates for common automation tasks."""

from __future__ import annotations

from typing import Any

JOB_TEMPLATES: dict[str, dict[str, Any]] = {
    "daily_digest": {
        "name": "Daily Information Digest",
        "trigger": "cron",
        "config": {"hour": 9, "minute": 0},
        "action": "info_daily_digest",
        "description": "Generate daily summary of mail, news, messages, calendar",
    },
    "weekly_report": {
        "name": "Weekly Evolution Report",
        "trigger": "cron",
        "config": {"day_of_week": "mon", "hour": 9, "minute": 0},
        "action": "evolution_status",
        "description": "Generate weekly evolution summary",
    },
    "code_scan": {
        "name": "Code Quality Scan",
        "trigger": "interval",
        "config": {"minutes": 30},
        "action": "scan_code",
        "description": "Periodic L6 architecture scan",
    },
    "memory_cleanup": {
        "name": "Memory Cleanup",
        "trigger": "cron",
        "config": {"hour": 3, "minute": 0},
        "action": "memory_forget",
        "description": "Nightly Ebbinghaus memory cleanup",
    },
    "im_check": {
        "name": "IM Message Check",
        "trigger": "interval",
        "config": {"seconds": 30},
        "action": "im_summarize",
        "description": "Poll IM platforms for unread messages",
    },
}
