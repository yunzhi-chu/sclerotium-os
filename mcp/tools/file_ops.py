"""File Operations — Read, Write, Edit. The most fundamental coding tools."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from kernel.security import check_path_safe


def file_read(file_path: str, start_line: int = 0, end_line: int = 0) -> dict[str, Any]:
    """Read a file. Claude Code FileReadTool equivalent."""
    check = check_path_safe(file_path)
    if not check["pass"]:
        return {"status": "error", "error": check["error"]}
    p = check["resolved"]
    if not p.exists():
        return {"status": "error", "error": f"File not found: {file_path}"}
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        if start_line > 0 or end_line > 0:
            s = max(0, start_line - 1)
            e = min(len(lines), end_line) if end_line > 0 else len(lines)
            content = "\n".join(lines[s:e])
        return {"status": "ok", "file_path": str(p), "content": content,
                "total_lines": len(lines), "size": p.stat().st_size,
                "language": p.suffix.lstrip(".")}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}

def file_write(file_path: str, content: str, mode: str = "w") -> dict[str, Any]:
    """Write content to a file. Creates parent directories automatically."""
    check = check_path_safe(file_path, write=True)
    if not check["pass"]:
        return {"status": "error", "error": check["error"]}
    p = check["resolved"]
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        old_size = p.stat().st_size if existed else 0
        old_lines = 0
        if existed:
            try:
                old_lines = len(p.read_text(encoding="utf-8").splitlines())
            except Exception:
                pass
        p.write_text(content, encoding="utf-8")
        new_size = p.stat().st_size
        new_lines = content.count("\n") + 1
        # BUG#2 修复: 区分 created(新建) vs appended(追加) vs overwritten(覆盖)
        is_append = (mode == "a")
        result = {
            "status": "ok", "file_path": str(p),
            "size": new_size, "lines": new_lines,
            "mode": mode,
        }
        if not existed:
            result["created"] = True
        elif is_append:
            result["appended"] = True
            result["new_size"] = new_size
            result["previous_size"] = old_size
            result["note"] = f"Content appended. File now {new_lines} lines ({new_size} bytes)."
        else:
            result["created"] = False
            result["overwritten"] = True
            result["warning"] = (
                f"⚠️  OVERWROTE existing file ({old_lines}→{new_lines} lines, {old_size}→{new_size} bytes). "
                f"If you were fixing a bug, use file_edit next time to change only the broken lines."
            )
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}

def file_edit(file_path: str, old_string: str, new_string: str,
              replace_all: bool = False) -> dict[str, Any]:
    """Replace text in a file."""
    check = check_path_safe(file_path)
    if not check["pass"]:
        return {"status": "error", "error": check["error"]}
    p = check["resolved"]
    if not p.exists():
        return {"status": "error", "error": f"File not found: {file_path}"}
    try:
        content = p.read_text(encoding="utf-8")
        matched = old_string in content
        fuzzy_matched = False

        if not matched:
            # Fuzzy fallback: try matching with normalized whitespace
            def _norm(s):
                return '\n'.join(line.rstrip() for line in s.splitlines())
            old_norm = _norm(old_string)
            content_norm = _norm(content)
            if old_norm in content_norm:
                matched = True
                fuzzy_matched = True
                # Find the actual un-normalized match in original content
                lines = content.splitlines(True)
                norm_lines = content_norm.splitlines(True)
                old_norm_lines = old_norm.splitlines(True)
                for i in range(len(norm_lines) - len(old_norm_lines) + 1):
                    if ''.join(norm_lines[i:i+len(old_norm_lines)]) == ''.join(old_norm_lines):
                        actual_start = sum(len(l) for l in lines[:i])
                        actual_end = sum(len(l) for l in lines[:i+len(old_norm_lines)])
                        old_string = content[actual_start:actual_end]
                        break

        if not matched:
            # Build helpful error: show lines around where old_string MIGHT be
            old_first_line = old_string.split('\n')[0].strip()
            hint_lines = []
            for i, line in enumerate(content.splitlines(), 1):
                if old_first_line and old_first_line[:30] in line:
                    start = max(0, i - 2)
                    end = min(len(content.splitlines()), i + 3)
                    for j in range(start, end):
                        prefix = ">>>" if j == i - 1 else "   "
                        hint_lines.append(f"{prefix} {j+1}: {content.splitlines()[j]}")
                    hint_lines.append("...")
            hint = "\n".join(hint_lines[:12]) if hint_lines else "old_string not found anywhere in file"
            return {"status": "error", "error": "old_string not found in file",
                    "hint": hint,
                    "tip": "Use file_read to see the exact text. Copy the lines you want to change verbatim."}

        count = content.count(old_string) if replace_all else 1
        new_content = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)
        p.write_text(new_content, encoding="utf-8")
        result = {"status": "ok", "file_path": str(p), "replacements": count,
                  "new_size": p.stat().st_size}
        if fuzzy_matched:
            result["note"] = "Used fuzzy match (whitespace differences ignored)"
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}

def file_list(directory: str = ".", pattern: str = "*", max_results: int = 50) -> dict[str, Any]:
    """List files in a directory. Claude Code LS equivalent."""
    # Coerce types — LLM may pass strings for int params
    try:
        max_results = int(max_results)
    except (TypeError, ValueError):
        max_results = 50
    d = Path(directory)
    check = check_path_safe(directory)
    if not check["pass"]:
        return {"status": "error", "error": check["error"]}
    d = check["resolved"]
    if not d.exists():
        return {"status": "error", "error": f"Directory not found: {directory}"}
    try:
        items = sorted(d.rglob(pattern))[:max_results]
        files = []
        for item in items:
            if item.is_file():
                files.append({"name": str(item), "size": item.stat().st_size,
                             "suffix": item.suffix})
        return {"status": "ok", "directory": str(d), "count": len(files), "files": files}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}

def register_file_ops(registry: Any) -> None:
    registry.register(name="file_read", description="Read a file. Returns content, line count, size, language.",
        parameters={"type":"object","properties":{
            "file_path":{"type":"string","description":"Path to the file"},
            "start_line":{"type":"integer","default":0,"description":"Start line (1-based, 0=beginning)"},
            "end_line":{"type":"integer","default":0,"description":"End line (0=end of file)"},
        },"required":["file_path"]}, handler=file_read, category="files")

    registry.register(name="file_write", description="Write content to a file. Creates parent directories if needed.",
        parameters={"type":"object","properties":{
            "file_path":{"type":"string","description":"Path to the file"},
            "content":{"type":"string","description":"Content to write"},
            "mode":{"type":"string","default":"w","enum":["w","a"],"description":"Write mode: w=overwrite, a=append"},
        },"required":["file_path","content"]}, handler=file_write, category="files")

    registry.register(name="file_edit", description="Replace exact string in a file. Claude Code EditTool equivalent.",
        parameters={"type":"object","properties":{
            "file_path":{"type":"string","description":"Path to the file"},
            "old_string":{"type":"string","description":"Exact text to replace"},
            "new_string":{"type":"string","description":"Text to replace with"},
            "replace_all":{"type":"boolean","default":False,"description":"Replace all occurrences"},
        },"required":["file_path","old_string","new_string"]}, handler=file_edit, category="files")

    registry.register(name="file_list", description="List files in a directory. Claude Code LS equivalent.",
        parameters={"type":"object","properties":{
            "directory":{"type":"string","default":".","description":"Directory to list"},
            "pattern":{"type":"string","default":"*","description":"Glob pattern"},
        }}, handler=file_list, category="files")
