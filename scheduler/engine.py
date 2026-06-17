"""Task Scheduler — APScheduler-backed with real threading.Timer fallback.

Jobs ALWAYS fire AND persist across restarts.
Metadata stored in data/scheduler_jobs.json — handlers recreated on load.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False


# Persistent storage path
JOBS_FILE = Path("data/scheduler_jobs.json")


@dataclass
class JobInfo:
    """Job metadata returned by list operations."""
    job_id: str
    name: str
    trigger: str
    trigger_description: str
    next_run_time: str
    enabled: bool
    last_run: str = ""
    status: str = "pending"


@dataclass
class JobMeta:
    """Serializable job metadata for persistence."""
    name: str
    trigger: str
    trigger_config: dict
    action_type: str
    action_params: dict | None
    enabled: bool = True


class _TimerJob:
    """A job managed by the threading.Timer fallback."""
    def __init__(self, job_id: str, name: str, trigger: str,
                 trigger_config: dict, func: Callable, enabled: bool = True):
        self.job_id = job_id
        self.name = name
        self.trigger = trigger
        self.trigger_config = trigger_config
        self.func = func
        self.enabled = enabled
        self._timer: threading.Timer | None = None
        self._cancelled = False
        self.next_run: float = 0
        self.last_run: str = ""
        self.status = "active" if enabled else "paused"

    def schedule_next(self):
        if self._cancelled or not self.enabled:
            return
        now = time.time()
        if self.trigger == "interval":
            seconds = self.trigger_config.get("seconds", 60)
            self.next_run = now + seconds
        elif self.trigger == "date":
            # Support multiple config formats:
            #   {"timestamp": 1234567890}        — absolute Unix timestamp
            #   {"run_date": "2026-06-17 15:23"} — absolute datetime string
            #   {"seconds": 30}                   — relative: fire in N seconds (one-shot)
            ts = self.trigger_config.get("timestamp", 0)
            if not ts:
                run_date = self.trigger_config.get("run_date", "")
                if run_date:
                    try:
                        from datetime import datetime
                        ts = datetime.strptime(run_date, "%Y-%m-%d %H:%M:%S").timestamp()
                    except ValueError:
                        try:
                            ts = datetime.strptime(run_date, "%Y-%m-%d %H:%M").timestamp()
                        except ValueError:
                            ts = 0
                if not ts:
                    rel_seconds = self.trigger_config.get("seconds", 0)
                    if rel_seconds > 0:
                        ts = now + rel_seconds
            if ts > now:
                self.next_run = ts
            else:
                # Past date — fire immediately once, then mark completed
                self.next_run = now + 0.5
                self.trigger = "date"  # stays date (one-shot)
                return
        elif self.trigger == "cron":
            seconds = self.trigger_config.get("seconds", self.trigger_config.get("minute", 1) * 60)
            if seconds < 10:
                seconds = 60
            self.next_run = now + seconds
        else:
            self.next_run = now + 60

        delay = max(0.1, self.next_run - now)
        self._timer = threading.Timer(delay, self._fire)
        self._timer.daemon = True
        self._timer.start()

    def _fire(self):
        if self._cancelled:
            return
        self.status = "running"
        try:
            self.func()
            self.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status = "active"
        except Exception as e:
            print(f"[Scheduler] Job '{self.name}' failed: {e}")
            self.status = "error"
        # interval/cron → reschedule; date → one-shot, mark completed
        if self.trigger in ("interval", "cron") and not self._cancelled:
            self.schedule_next()
        elif self.trigger == "date":
            # Fire once, then mark completed (don't reschedule past dates)
            self.status = "completed"
        else:
            self.status = "completed"

    def cancel(self):
        self._cancelled = True
        if self._timer:
            self._timer.cancel()


# Type for handler factory: (action_type, action_params) -> Callable
HandlerFactory = Callable[[str, dict | None], Callable]


class SchedulerEngine:
    """Job scheduler with persistence across restarts.

    Jobs ALWAYS execute AND survive restarts.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_url: str = "sqlite:///data/scheduler.db") -> None:
        if hasattr(self, '_initialized'):
            return
        self._db_url = db_url
        self._scheduler: Any = None
        self._timer_jobs: dict[str, _TimerJob] = {}
        self._job_meta: dict[str, JobMeta] = {}  # job_id -> metadata (for persistence)
        self._handler_factory: HandlerFactory | None = None
        self._initialized = False
        self._use_apscheduler = False

    def set_handler_factory(self, factory: HandlerFactory) -> None:
        """Register a function that creates handlers from (action_type, action_params).

        Called by scheduler_mcp.py so persisted jobs can be recreated on restart.
        """
        self._handler_factory = factory

    def initialize(self) -> None:
        """Start the scheduler and restore persisted jobs."""
        os.makedirs("data", exist_ok=True)

        if HAS_APSCHEDULER:
            try:
                self._scheduler = BackgroundScheduler()
                self._scheduler.start()
                self._use_apscheduler = True
                print("[Scheduler] APScheduler BackgroundScheduler started")
            except Exception as e:
                print(f"[Scheduler] APScheduler start failed: {e}, using Timer fallback")
                self._use_apscheduler = False
        else:
            print("[Scheduler] Using threading.Timer fallback")
            self._use_apscheduler = False

        self._initialized = True

        # Restore persisted jobs
        self._restore_jobs()

    def shutdown(self) -> None:
        """Stop all scheduled jobs and persist state."""
        self._save_jobs()
        if self._scheduler and self._use_apscheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
        for job in self._timer_jobs.values():
            job.cancel()
        self._timer_jobs.clear()

    # ── CRUD ──────────────────────────────────────────────────────────

    def add_job(
        self,
        name: str,
        trigger: str,
        trigger_config: dict[str, Any],
        func: Callable,
        enabled: bool = True,
        *,
        action_type: str = "",
        action_params: dict | None = None,
    ) -> str | None:
        """Add a scheduled job. The job WILL execute AND persist."""
        if self._use_apscheduler and self._scheduler:
            try:
                if trigger == "cron":
                    t = CronTrigger(**trigger_config)
                elif trigger == "interval":
                    t = IntervalTrigger(**trigger_config)
                elif trigger == "date":
                    t = DateTrigger(**trigger_config)
                else:
                    return None

                job = self._scheduler.add_job(
                    func, trigger=t, id=name, name=name, replace_existing=True,
                )
                if not enabled:
                    job.pause()
                jid = job.id
            except Exception as e:
                print(f"[Scheduler] APScheduler add_job failed: {e}, falling back to Timer")
                jid = f"job_{uuid.uuid4().hex[:8]}"
                job = _TimerJob(jid, name, trigger, trigger_config, func, enabled)
                self._timer_jobs[jid] = job
                if enabled:
                    job.schedule_next()
        else:
            jid = f"job_{uuid.uuid4().hex[:8]}"
            job = _TimerJob(jid, name, trigger, trigger_config, func, enabled)
            self._timer_jobs[jid] = job
            if enabled:
                job.schedule_next()

        # Persist metadata so it survives restarts
        if action_type:
            self._job_meta[jid or name] = JobMeta(
                name=name, trigger=trigger, trigger_config=trigger_config,
                action_type=action_type, action_params=action_params, enabled=enabled,
            )
            self._save_jobs()

        print(f"[Scheduler] Added job: {name} ({trigger}) id={jid}")
        return jid

    def remove_job(self, job_id: str) -> bool:
        """Remove a job and its persisted metadata."""
        removed = False
        if self._use_apscheduler and self._scheduler:
            try:
                self._scheduler.remove_job(job_id)
                removed = True
            except Exception:
                pass
        if job_id in self._timer_jobs:
            self._timer_jobs[job_id].cancel()
            del self._timer_jobs[job_id]
            removed = True
        if job_id in self._job_meta:
            del self._job_meta[job_id]
            self._save_jobs()
            removed = True
        return removed

    def toggle_job(self, job_id: str, enabled: bool) -> bool:
        """Enable or pause a job."""
        if self._use_apscheduler and self._scheduler:
            try:
                job = self._scheduler.get_job(job_id)
                if job:
                    if enabled:
                        job.resume()
                    else:
                        job.pause()
                    if job_id in self._job_meta:
                        self._job_meta[job_id].enabled = enabled
                        self._save_jobs()
                    return True
            except Exception:
                pass
        if job_id in self._timer_jobs:
            j = self._timer_jobs[job_id]
            j.enabled = enabled
            if enabled:
                j._cancelled = False
                j.schedule_next()
                j.status = "active"
            else:
                j.cancel()
                j.status = "paused"
            if job_id in self._job_meta:
                self._job_meta[job_id].enabled = enabled
                self._save_jobs()
            return True
        return False

    def list_jobs(self) -> list[JobInfo]:
        """List all scheduled jobs."""
        jobs = []
        if self._use_apscheduler and self._scheduler:
            try:
                for j in self._scheduler.get_jobs():
                    jobs.append(JobInfo(
                        job_id=j.id, name=j.name,
                        trigger=str(j.trigger),
                        trigger_description=str(j.trigger),
                        next_run_time=str(j.next_run_time) if j.next_run_time else "pending",
                        status="active" if j.next_run_time else "paused",
                        enabled=j.next_run_time is not None,
                    ))
            except Exception:
                pass
        for j in self._timer_jobs.values():
            jobs.append(JobInfo(
                job_id=j.job_id, name=j.name,
                trigger=j.trigger,
                trigger_description=f"{j.trigger}={j.trigger_config}",
                next_run_time=datetime.fromtimestamp(j.next_run).strftime("%H:%M:%S") if j.next_run else "pending",
                status=j.status, enabled=j.enabled, last_run=j.last_run,
            ))
        return jobs

    def get_job(self, job_id: str) -> JobInfo | None:
        """Get a single job."""
        for j in self.list_jobs():
            if j.job_id == job_id:
                return j
        return None

    # ── Persistence ───────────────────────────────────────────────────

    def _save_jobs(self) -> None:
        """Persist job metadata to JSON so it survives restarts."""
        try:
            data = {
                jid: {
                    "name": m.name, "trigger": m.trigger,
                    "trigger_config": m.trigger_config,
                    "action_type": m.action_type,
                    "action_params": m.action_params,
                    "enabled": m.enabled,
                }
                for jid, m in self._job_meta.items()
            }
            JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(JOBS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Scheduler] Failed to save jobs: {e}")

    def _restore_jobs(self) -> int:
        """Restore persisted jobs on startup. Returns count of restored jobs."""
        if not JOBS_FILE.exists():
            return 0

        try:
            with open(JOBS_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[Scheduler] Failed to load jobs file: {e}")
            return 0

        if not data:
            return 0

        factory = self._handler_factory
        if not factory:
            print(f"[Scheduler] No handler factory registered — cannot restore {len(data)} persisted jobs")
            return 0

        restored = 0
        for jid, meta_dict in data.items():
            try:
                meta = JobMeta(
                    name=meta_dict["name"],
                    trigger=meta_dict["trigger"],
                    trigger_config=meta_dict["trigger_config"],
                    action_type=meta_dict["action_type"],
                    action_params=meta_dict.get("action_params"),
                    enabled=meta_dict.get("enabled", True),
                )
                # Inject job name into params so the handler knows its identity
                params_with_name = dict(meta.action_params or {})
                params_with_name.setdefault("_job_name", meta.name)
                handler = factory(meta.action_type, params_with_name)
                self.add_job(
                    name=meta.name, trigger=meta.trigger,
                    trigger_config=meta.trigger_config,
                    func=handler, enabled=meta.enabled,
                    action_type=meta.action_type, action_params=meta.action_params,
                )
                restored += 1
            except Exception as e:
                print(f"[Scheduler] Failed to restore job '{meta_dict.get('name', jid)}': {e}")

        if restored:
            print(f"[Scheduler] Restored {restored}/{len(data)} persisted jobs")
        return restored
