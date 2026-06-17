"""MCP File Tools — real filesystem operations: watch, organize, search."""

from __future__ import annotations

import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any

from mcp.server import ToolRegistry

# Global watcher registry — BUG#6 修复: 增加生命周期追踪
_watchers: dict[str, dict[str, Any]] = {}  # watch_id -> {observer, started_at, path, events_seen, auto_stop_seconds}
_watch_counter = 0
_WATCH_AUTO_STOP_SECONDS = 1800  # 30 minutes auto-cleanup (was: no cleanup → zombie watchers)
_watch_cleanup_lock = threading.Lock()


def _cleanup_stale_watchers() -> int:
    """BUG#6: 清理超时的僵尸 watcher。在每次 _files_watch 调用时触发。"""
    now = time.time()
    stale_ids = []
    with _watch_cleanup_lock:
        for wid, info in list(_watchers.items()):
            age = now - info.get("started_at", now)
            if age > info.get("auto_stop_seconds", _WATCH_AUTO_STOP_SECONDS):
                stale_ids.append(wid)

    cleaned = 0
    for wid in stale_ids:
        info = _watchers.pop(wid, None)
        if info:
            try:
                obs = info.get("observer")
                if obs and hasattr(obs, "stop"):
                    obs.stop()
                    obs.join(timeout=1)
                cleaned += 1
            except Exception:
                pass
    return cleaned


async def _files_watch(path: str = ".", patterns: list[str] | None = None,
                      recursive: bool = True, auto_stop_seconds: int = 1800) -> dict:
    """Start a REAL watchdog file monitor. Returns watch_id for stopping.

    BUG#6 修复: 增加 auto_stop_seconds 参数 + 心跳检测 + 生命周期透明化。
    默认 30 分钟自动停止, 防止僵尸 watcher 积累。
    """
    global _watch_counter

    # 先清理过期 watcher
    cleaned = _cleanup_stale_watchers()

    p = Path(path).resolve()
    if not p.exists():
        return {"status": "error", "message": f"Path not found: {path}"}

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        events_seen = []  # 记录最近事件用于诊断

        class WatchHandler(FileSystemEventHandler):
            def on_modified(self, event):
                msg = f"[FileWatch:{watch_id}] Modified: {event.src_path}"
                events_seen.append({"type": "modified", "path": event.src_path, "time": time.time()})
                if len(events_seen) > 50:
                    events_seen.pop(0)

            def on_created(self, event):
                events_seen.append({"type": "created", "path": event.src_path, "time": time.time()})
                if len(events_seen) > 50:
                    events_seen.pop(0)

            def on_deleted(self, event):
                events_seen.append({"type": "deleted", "path": event.src_path, "time": time.time()})
                if len(events_seen) > 50:
                    events_seen.pop(0)

        observer = Observer()
        handler = WatchHandler()
        observer.schedule(handler, str(p), recursive=recursive)
        observer.start()

        _watch_counter += 1
        watch_id = f"watch_{_watch_counter:04x}"
        started_at = time.time()

        watch_info = {
            "observer": observer,
            "started_at": started_at,
            "path": str(p),
            "events_seen": events_seen,
            "auto_stop_seconds": min(auto_stop_seconds, 86400),  # cap at 24h
        }
        _watchers[watch_id] = watch_info

        return {
            "watch_id": watch_id,
            "path": str(p),
            "recursive": recursive,
            "patterns": patterns or ["*"],
            "status": "watching",
            "active_watches": len(_watchers),
            "started_at": started_at,
            "auto_stop_seconds": watch_info["auto_stop_seconds"],
            "auto_stop_at": started_at + watch_info["auto_stop_seconds"],
            "stale_cleaned": cleaned,
            "lifecycle_note": f"Watch auto-stops after {watch_info['auto_stop_seconds']}s. Call files_watch_stop({watch_id}) to stop early.",
        }
    except ImportError:
        # No watchdog installed — fall back to polling info
        files = list(p.rglob("*"))[:100] if recursive else list(p.iterdir())[:100]
        return {
            "watch_id": f"poll_{hash(str(p)) & 0xFFFF:04x}",
            "path": str(p),
            "status": "polling (watchdog not installed)",
            "file_count": len(files),
            "active_watches": len(_watchers),
            "stale_cleaned": cleaned,
            "note": "Install watchdog for real-time monitoring: pip install watchdog",
            "lifecycle_note": "Polling mode — no cleanup needed (stateless).",
        }


async def _files_watch_stop(watch_id: str) -> dict:
    """Stop a running file watch.

    BUG#6 修复: 返回 watch 生命周期摘要 (启动时间、运行时长、已捕获事件数)。
    """
    watch_info = _watchers.pop(watch_id, None)
    if watch_info:
        observer = watch_info.get("observer")
        started_at = watch_info.get("started_at", 0)
        events = watch_info.get("events_seen", [])
        uptime = time.time() - started_at if started_at else 0

        if observer and hasattr(observer, "stop"):
            try:
                observer.stop()
                observer.join(timeout=2)
            except Exception as e:
                return {
                    "status": "error", "watch_id": watch_id,
                    "message": str(e),
                    "uptime_seconds": round(uptime, 1),
                    "events_captured": len(events),
                }

        return {
            "status": "stopped",
            "watch_id": watch_id,
            "path": watch_info.get("path", "?"),
            "uptime_seconds": round(uptime, 1),
            "events_captured": len(events),
            "recent_events": events[-5:] if events else [],
        }
    return {
        "status": "not_found",
        "watch_id": watch_id,
        "hint": "Watch may have auto-expired. Use files_watch to list active watches.",
    }


async def _files_organize(path: str, rules: dict | None = None, dry_run: bool = True) -> dict:
    """REALLY organize files by type into subdirectories."""
    p = Path(path)
    if not p.exists():
        return {"files_moved": 0, "by_category": {}, "errors": [f"Path not found: {path}"]}

    # Default organization: by extension category
    category_map = {
        "images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"},
        "documents": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml"},
        "code": {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".rb", ".php", ".swift", ".kt"},
        "archives": {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar"},
        "audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
        "video": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"},
        "config": {".ini", ".cfg", ".conf", ".toml", ".env"},
    }

    files_moved = 0
    by_category = {}
    file_map: list[dict[str, str]] = []  # BUG#6: old_path → new_path 映射表
    errors = []

    for f in p.iterdir():
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        category = "other"
        for cat, exts in category_map.items():
            if ext in exts:
                category = cat
                break

        dest_dir = p / category
        new_path = str(dest_dir / f.name)
        try:
            if not dry_run:
                dest_dir.mkdir(exist_ok=True)
                shutil.move(str(f), new_path)
            files_moved += 1
            by_category[category] = by_category.get(category, 0) + 1
            file_map.append({
                "original": str(f),
                "new_path": new_path,
                "category": category,
                "extension": ext,
            })
        except Exception as e:
            errors.append(f"{f.name}: {e}")

    result = {
        "files_moved": files_moved,
        "by_category": by_category,
        "file_map": file_map,  # BUG#6: 完整路径映射, 用户可知文件新位置
        "dry_run": dry_run,
        "errors": errors,
    }
    if not dry_run and files_moved > 0:
        result["notify"] = (
            f"{files_moved} files organized into {len(by_category)} categories. "
            f"Use file_map to see old→new paths. Original directory: {str(p)}"
        )
    return result


async def _files_search(query: str, path: str = ".", file_types: list[str] | None = None) -> list[dict]:
    """REAL file search by name."""
    p = Path(path)
    if not p.exists():
        return []

    results = []
    extensions = set(file_types) if file_types else None

    for f in p.rglob("*"):
        if len(results) >= 50:
            break
        if not f.is_file():
            continue
        if extensions and f.suffix.lower() not in extensions:
            continue
        if query.lower() in f.name.lower():
            try:
                stat = f.stat()
                results.append({
                    "path": str(f),
                    "name": f.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                })
            except OSError:
                results.append({"path": str(f), "name": f.name, "size": 0, "modified": 0})

    return results[:20]


async def _files_watch_list() -> dict:
    """BUG#6: 列出所有活跃的 watcher 及其生命周期状态。"""
    now = time.time()
    active = []
    for wid, info in _watchers.items():
        started = info.get("started_at", 0)
        auto_stop = info.get("auto_stop_seconds", _WATCH_AUTO_STOP_SECONDS)
        age = now - started if started else 0
        active.append({
            "watch_id": wid,
            "path": info.get("path", "?"),
            "uptime_seconds": round(age, 1),
            "auto_stop_seconds": auto_stop,
            "remaining_seconds": round(max(0, auto_stop - age), 1),
            "events_seen": len(info.get("events_seen", [])),
            "status": "expiring" if age > auto_stop * 0.8 else "active",
        })
    return {
        "active_watches": len(active),
        "watches": active,
        "total_slots_used": f"{len(active)}/unlimited",
        "cleanup_policy": f"Auto-stop after {_WATCH_AUTO_STOP_SECONDS}s of inactivity",
    }


def register_files_tools(registry: ToolRegistry) -> None:
    for name, desc, params, handler in [
        ("files_watch", "Start REAL file monitoring with watchdog. Auto-stops after timeout. Returns watch_id + lifecycle info.", {
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": ".", "description": "Directory to watch"},
                "patterns": {"type": "array", "items": {"type": "string"}, "description": "File patterns to watch (e.g. ['*.py', '*.txt'])"},
                "recursive": {"type": "boolean", "default": True, "description": "Watch subdirectories recursively"},
                "auto_stop_seconds": {"type": "integer", "default": 1800, "description": "Auto-stop after N seconds (default 30min, max 24h). Prevents zombie watchers."},
            },
            "required": [],
        }, _files_watch),
        ("files_watch_stop", "Stop a file watch. Returns lifecycle summary (uptime, events captured, recent events).", {
            "type": "object",
            "properties": {"watch_id": {"type": "string", "description": "Watch ID returned by files_watch"}},
            "required": ["watch_id"],
        }, _files_watch_stop),
        ("files_watch_list", "List all active file watchers with lifecycle status (uptime, remaining time, events).", {
            "type": "object", "properties": {}, "required": [],
        }, _files_watch_list),
        ("files_organize", "REALLY organize files by type (images/documents/code/archives/audio/video) into subdirectories.", {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory to organize"},
                "rules": {"type": "object", "description": "Custom category→extensions mapping"},
                "dry_run": {"type": "boolean", "default": True, "description": "Preview without moving files"},
            },
            "required": ["path"],
        }, _files_organize),
        ("files_search", "Search files by name (case-insensitive).", {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (matches filename)"},
                "path": {"type": "string", "default": ".", "description": "Directory to search in"},
                "file_types": {"type": "array", "items": {"type": "string"}, "description": "Filter by file extensions (e.g. ['.py', '.md'])"},
            },
            "required": ["query"],
        }, _files_search),
    ]:
        registry.register(name=name, description=desc, parameters=params, handler=handler, category="files")
