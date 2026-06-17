"""MCP Memory Tools — memory_search, memory_store, memory_consolidate, memory_forget.

Backed by kernel/hexis_memory.py: ChromaDB + SQLite 5-layer memory
with Ebbinghaus adaptive forgetting.
"""

from __future__ import annotations

from typing import Any

from mcp.server import ToolRegistry
from kernel.hexis_memory import HexisMemoryStore

_store: HexisMemoryStore | None = None


def _get_store() -> HexisMemoryStore:
    global _store
    if _store is None:
        # BUG#3修复: 使用 ~/.sclerotium/ 作为持久化路径 (而非 ./data/)
        # 这样数据在用户主目录下, 不会因切换工作目录而丢失
        import os as _os, pathlib as _pl
        base = _pl.Path(_os.environ.get("SCLEROTIUM_HOME",
                     _pl.Path.home() / ".sclerotium"))
        base.mkdir(parents=True, exist_ok=True)
        _store = HexisMemoryStore(
            chroma_path=str(base / "chroma"),
            sqlite_path=str(base / "memory.db"),
        )
    return _store


async def _memory_search(
    query: str, top_k: int = 10, memory_level: str = "all",
) -> list[dict[str, Any]]:
    result = _get_store().search(query=query, level=memory_level, top_k=top_k)
    # 自动记录访问模式 → ProactiveMemoryEngine 学习 (修复 Bug #2)
    _record_access(query)
    return result


async def _memory_store(
    content: str, memory_level: str = "episodic",
    metadata: dict[str, Any] | None = None, importance: float = 0.5,
) -> dict[str, Any]:
    mem_id = _get_store().store(
        content=content, level=memory_level,
        importance=importance, metadata=metadata,
    )
    # 自动记录访问模式 (修复 Bug #2)
    _record_access(content)
    return {"memory_id": mem_id, "stored_at": "now"}


def _record_access(text: str) -> None:
    """通知 ProactiveMemoryEngine 记录本次访问 (自动学习访问模式)。"""
    try:
        from mcp.tools.advanced import record_memory_access
        # 提取关键词作为 topics
        keywords = [w for w in text.lower().split() if len(w) > 3][:5]
        record_memory_access(text, keywords if keywords else None)
    except Exception:
        pass


async def _memory_consolidate(
    from_level: str, to_level: str, force: bool = False,
) -> dict[str, Any]:
    return _get_store().consolidate(
        from_level=from_level, to_level=to_level, force=force,
    )


async def _memory_forget(level: str, threshold_days: int = 30, decay_threshold: float = 0.2) -> dict[str, Any]:
    return _get_store().forget(level=level, threshold_days=threshold_days, decay_threshold=decay_threshold)


def register_memory_tools(registry: ToolRegistry) -> None:
    registry.register(
        name="memory_search",
        description="Search memories across five levels (working, episodic, semantic, procedural, strategic). Uses ChromaDB vector search with SQLite fallback.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "top_k": {"type": "integer", "description": "Number of results", "default": 10},
                "memory_level": {
                    "type": "string",
                    "enum": ["working", "episodic", "semantic", "procedural", "strategic", "all"],
                    "default": "all",
                },
            },
            "required": ["query"],
        },
        handler=_memory_search, category="memory",
    )
    registry.register(
        name="memory_store",
        description="Store a new memory entry with importance weighting. Persisted to SQLite + ChromaDB vector index.",
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "memory_level": {"type": "string", "enum": ["working","episodic","semantic","procedural","strategic"], "default": "episodic"},
                "metadata": {"type": "object"},
                "importance": {"type": "number", "default": 0.5},
            },
            "required": ["content"],
        },
        handler=_memory_store, category="memory",
    )
    registry.register(
        name="memory_consolidate",
        description="Consolidate memories from one level to next higher level. Extracts cross-memory patterns.",
        parameters={
            "type": "object",
            "properties": {
                "from_level": {"type": "string", "enum": ["working","episodic","semantic","procedural","strategic"]},
                "to_level": {"type": "string", "enum": ["episodic","semantic","procedural","strategic"]},
                "force": {"type": "boolean", "default": False},
            },
            "required": ["from_level", "to_level"],
        },
        handler=_memory_consolidate, category="memory",
    )
    registry.register(
        name="memory_forget",
        description="Apply Ebbinghaus adaptive forgetting — remove low-importance memories past half-life. Updates decay factors before checking.",
        parameters={
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["working","episodic","semantic","procedural","strategic"]},
                "threshold_days": {"type": "integer", "default": 30, "description": "Minimum days before a memory can be forgotten"},
                "decay_threshold": {"type": "number", "default": 0.2, "description": "Decay factor threshold (0-1). Lower = more aggressive forgetting. Set to 0.5 for testing."},
            },
            "required": ["level"],
        },
        handler=_memory_forget, category="memory",
    )
