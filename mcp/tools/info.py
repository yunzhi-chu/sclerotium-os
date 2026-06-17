"""MCP Info Tools — 实时信息聚合。从调度器/记忆/进化引擎聚合真实数据。"""

from __future__ import annotations

from typing import Any

from mcp.server import ToolRegistry


async def _info_daily_digest() -> dict:
    """实时日报 — 从系统各组件聚合真实状态。"""
    digest = {}
    now = __import__("datetime").datetime.now()

    # 进化状态
    try:
        from evolution.full_body_genome import FullBodyGenome
        genome = FullBodyGenome("./data/genome.json")
        digest["evolution"] = {
            "generation": genome.generation,
            "fitness": round(genome.fitness, 4),
            "top_tools": [{"name": t, "weight": round(w, 3)} for t, w in genome.get_top_tools(3)],
        }
    except Exception as e:
        digest["evolution"] = {"error": str(e)[:80]}

    # 记忆统计
    try:
        from kernel.hexis_memory import HexisMemoryStore
        store = HexisMemoryStore(chroma_path="./data/chroma", sqlite_path="./data/memory.db")
        stats = store.get_stats()
        digest["memory"] = {
            "total": getattr(stats, "total_memories", 0) if hasattr(stats, "total_memories") else 0,
            "by_level": getattr(stats, "by_level", {}) if hasattr(stats, "by_level") else {},
        }
    except Exception as e:
        digest["memory"] = {"error": str(e)[:80]}

    # 定时任务
    try:
        from scheduler.engine import SchedulerEngine
        engine = SchedulerEngine()
        await engine.initialize()
        jobs = engine.list_jobs()
        digest["scheduled_tasks"] = {
            "total": len(jobs),
            "pending": [{"name": j.name, "next_run": j.next_run_time} for j in jobs if j.status == "pending"][:5],
        }
    except Exception as e:
        digest["scheduled_tasks"] = {"error": str(e)[:80]}

    # 系统资源
    try:
        import psutil
        digest["resources"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "disk_free_gb": round(psutil.disk_usage("/").free / (1024**3), 1),
            "processes": len(psutil.pids()),
        }
    except ImportError:
        digest["resources"] = {"status": "psutil not installed"}

    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "digest": digest,
    }


async def _info_calendar_today() -> dict:
    """今日日程 — 从调度器获取今天要执行的定时任务作为日历事件。"""
    try:
        from scheduler.engine import SchedulerEngine
        engine = SchedulerEngine()
        await engine.initialize()
        jobs = engine.list_jobs()
        events = []
        for j in jobs:
            if j.next_run_time:
                events.append({
                    "title": j.name,
                    "time": j.next_run_time,
                    "trigger": j.trigger_description,
                    "status": j.status,
                })
        return {"date": __import__("datetime").datetime.now().strftime("%Y-%m-%d"), "events": events, "total": len(events), "source": "scheduler"}
    except Exception as e:
        return {"date": __import__("datetime").datetime.now().strftime("%Y-%m-%d"), "events": [], "source": "scheduler", "error": str(e)[:80]}


async def _info_mail_check() -> dict:
    """消息检查 — 从会话管理器获取最近未读消息/会话。"""
    try:
        from agent.session import SessionManager
        mgr = SessionManager("./data/sessions")
        sessions = mgr.list_sessions()
        # BUG-002修复: SessionInfo 是 dataclass 对象, 用属性访问而非 .get()
        recent = []
        for s in sessions[:10]:
            if isinstance(s, dict):
                recent.append({
                    "session_id": s.get("session_id", ""),
                    "title": s.get("title", ""),
                    "message_count": s.get("message_count", 0),
                    "model": s.get("model", ""),
                })
            else:
                recent.append({
                    "session_id": getattr(s, "session_id", ""),
                    "title": getattr(s, "title", ""),
                    "message_count": getattr(s, "message_count", 0),
                    "model": getattr(s, "model", ""),
                })
        return {"source": "session_manager", "recent_sessions": recent, "total": len(recent)}
    except Exception as e:
        return {"source": "session_manager", "recent_sessions": [], "error": str(e)[:80]}


def register_info_tools(registry: ToolRegistry) -> None:
    for name, desc, params, handler in [
        ("info_daily_digest", "Generate REAL daily digest from evolution, memory, scheduler, and system resources.", {"type": "object", "properties": {}, "required": []}, _info_daily_digest),
        ("info_calendar_today", "Today's calendar from scheduled tasks (real scheduler jobs).", {"type": "object", "properties": {}, "required": []}, _info_calendar_today),
        ("info_mail_check", "Check recent sessions/messages from SessionManager.", {"type": "object", "properties": {}, "required": []}, _info_mail_check),
    ]:
        registry.register(name=name, description=desc, parameters=params, handler=handler, category="info")
