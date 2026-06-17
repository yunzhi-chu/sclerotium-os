"""MCP Tools for codebase search — beats Claude Code's Grep/Glob."""

from __future__ import annotations

import threading
from typing import Any

_INDEXER: Any = None
_INDEXER_LOCK = threading.Lock()


def get_indexer():
    """线程安全的索引器获取。ChromaDB/SQLite 要求同一线程内使用连接对象。"""
    global _INDEXER

    # Fast path: already initialized and this thread's connection works
    if _INDEXER is not None:
        try:
            # Quick smoke test - if this fails, we need to re-init for this thread
            _INDEXER.get_stats()
            return _INDEXER
        except Exception:
            pass  # Thread mismatch - reinitialize

    # Slow path: create or recreate indexer (thread-safe)
    with _INDEXER_LOCK:
        from kernel.codebase_indexer import CodebaseIndexer
        try:
            _INDEXER = CodebaseIndexer()
            # BUG#7修复: 检测项目根目录 (而非当前工作目录)
            # 从当前文件位置推导项目根 → 索引整个项目
            import os as _os
            proj_root = _os.environ.get("SCLEROTIUM_HOME", ".")
            if proj_root == ".":
                # 尝试从常见标志文件推断项目根
                for marker in ["pyproject.toml", "setup.py", ".git", "mcp/__init__.py"]:
                    for depth in range(5):
                        prefix = "../" * depth
                        if _os.path.exists(prefix + marker):
                            proj_root = prefix.rstrip("/") or "."
                            break
                    if proj_root != ".":
                        break
            _INDEXER.index_project(proj_root)
        except Exception:
            pass
        return _INDEXER


def codebase_search(query: str, max_results: int = 20,
                    file_pattern: str = "*",
                    scope: str = "auto") -> dict[str, Any]:
    """Full-text search across ALL indexed project files.

    BUG#5 修复: 明确标注搜索范围 (search_scope), 当索引仅覆盖当前目录时
    提示用户使用 codebase_index(project_root=".") 扩展索引范围。
    """
    import os as _os
    idx = get_indexer()
    results = idx.search(query, max_results=max_results, file_pattern=file_pattern)
    stats = idx.get_stats()

    # 确定实际搜索范围
    files_indexed = stats.get("files_indexed", 0) if isinstance(stats, dict) else 0
    cwd = _os.getcwd()

    # 检测是否仅索引了当前目录 (而非整个项目)
    scope_note = ""
    if isinstance(stats, dict):
        project_root = stats.get("project_root", cwd)
        if files_indexed <= 3:
            scope_note = (
                f"索引仅覆盖 {files_indexed} 个文件 (当前目录)。"
                f"要搜索整个项目, 先调用 codebase_index(project_root='.') 扩展索引。"
            )
            search_scope = f"current directory only ({project_root})"
        else:
            search_scope = f"project: {project_root} ({files_indexed} files)"
    else:
        search_scope = f"indexed ({files_indexed} files)"

    result = {
        "query": query,
        "results": results,
        "total": len(results),
        "search_scope": search_scope,
        "files_indexed": files_indexed,
        "index_stats": stats,
    }
    if scope_note:
        result["scope_note"] = scope_note
    return result


def codebase_symbols(name: str, kind: str = "all",
                     max_results: int = 30) -> dict[str, Any]:
    """Find function/class/variable definitions by name."""
    idx = get_indexer()
    results = idx.search_symbols(name, kind=kind, max_results=max_results)
    return {"query": name, "kind": kind, "results": results, "total": len(results)}


def codebase_callers(symbol: str, max_results: int = 20) -> dict[str, Any]:
    """Find all callers of a function."""
    idx = get_indexer()
    results = idx.find_callers(symbol, max_results=max_results)
    return {"symbol": symbol, "callers": results, "total": len(results)}


def codebase_callees(symbol: str, max_results: int = 20) -> dict[str, Any]:
    """Find all functions called by a function."""
    idx = get_indexer()
    results = idx.find_callees(symbol, max_results=max_results)
    return {"symbol": symbol, "callees": results, "total": len(results)}


def codebase_files(pattern: str = "*", sort_by: str = "path") -> dict[str, Any]:
    """List indexed files."""
    idx = get_indexer()
    results = idx.list_files(pattern=pattern, sort_by=sort_by)
    return {"pattern": pattern, "files": results, "total": len(results)}


def codebase_index(project_root: str = ".") -> dict[str, Any]:
    """Index a project (or all projects if no path given)."""
    idx = get_indexer()
    if project_root == "all":
        stats = idx.index_all_projects()
    else:
        stats = {"project": idx.index_project(project_root)}
    stats["overall"] = idx.get_stats()
    return stats


def register_codebase_tools(tools_registry: Any) -> None:
    tools_registry.register(
        name="codebase_search",
        description="Full-text search across project files. Shows search scope + index stats. Use codebase_index first to index the project.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 20, "description": "Max results"},
                "file_pattern": {"type": "string", "default": "*", "description": "File glob pattern (e.g. '*.py')"},
                "scope": {"type": "string", "default": "auto", "description": "Search scope: auto (detect from index), project (force project root)"},
            },
            "required": ["query"],
        },
        handler=codebase_search, category="codebase",
    )
    tools_registry.register(
        name="codebase_symbols",
        description="Find function/class/variable definitions by name across the entire codebase.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Symbol name (partial match supported)"},
                "kind": {"type": "string", "default": "all", "description": "function, class, method, or all"},
                "max_results": {"type": "integer", "default": 30},
            },
            "required": ["name"],
        },
        handler=codebase_symbols, category="codebase",
    )
    tools_registry.register(
        name="codebase_callers",
        description="Find all callers of a function — who calls this?",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Function/class name"},
                "max_results": {"type": "integer", "default": 20},
            },
            "required": ["symbol"],
        },
        handler=codebase_callers, category="codebase",
    )
    tools_registry.register(
        name="codebase_callees",
        description="Find all functions called by a function — what does this call?",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Function/class name"},
                "max_results": {"type": "integer", "default": 20},
            },
            "required": ["symbol"],
        },
        handler=codebase_callees, category="codebase",
    )
    tools_registry.register(
        name="codebase_files",
        description="List project files with metadata (lines, size, symbols count).",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "default": "*", "description": "File glob pattern"},
                "sort_by": {"type": "string", "default": "path", "description": "Sort: path, lines, symbols"},
            },
        },
        handler=codebase_files, category="codebase",
    )
    tools_registry.register(
        name="codebase_index",
        description="Index the project for fast search. Run after major code changes.",
        parameters={
            "type": "object",
            "properties": {
                "project_root": {"type": "string", "default": ".", "description": "Project to index, or 'all'"},
            },
        },
        handler=codebase_index, category="codebase",
    )
