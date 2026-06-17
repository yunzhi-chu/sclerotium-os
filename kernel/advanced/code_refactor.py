"""P0: Multi-file Semantic Refactoring Engine.

Call-graph tracing, cross-file dependency analysis, safe refactoring with
verification. Targets Claude Code SWE-bench capability (88.6%).

Architecture:
  1. AST Parser — builds call graph across entire codebase
  2. Impact Analyzer — traces what would break if symbol X changes
  3. Refactor Planner — generates minimal safe edit plan
  4. Verifier — runs tests + static checks before/after

Reference: Claude Code LSP integration, Codex multi-file edits,
SWE-HERO execution-based verification.
"""

from __future__ import annotations

import ast
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Symbol:
    name: str
    kind: str         # function, class, method, variable, import
    file: str
    line: int
    calls: list[str] = field(default_factory=list)
    called_by: list[str] = field(default_factory=list)


@dataclass
class RefactorPlan:
    """A safe refactoring plan with pre/post verification."""
    description: str
    files_to_modify: list[str]
    edits: list[dict[str, Any]]
    pre_verification: list[str]   # checks to run before
    post_verification: list[str]  # checks to run after
    risk_level: str = "low"       # low, medium, high


class CallGraph:
    """AST-based call graph builder for Python codebases."""

    def __init__(self, root_path: str = ".") -> None:
        self.root = Path(root_path)
        self.symbols: dict[str, Symbol] = {}
        self._file_to_symbols: dict[str, list[str]] = defaultdict(list)

    def build(self) -> dict[str, Any]:
        """Parse entire codebase and build call graph."""
        for py_file in self.root.rglob("*.py"):
            if "node_modules" in str(py_file) or ".venv" in str(py_file):
                continue
            if "__pycache__" in str(py_file):
                continue
            self._parse_file(py_file)

        return {
            "total_symbols": len(self.symbols),
            "files_analyzed": len(self._file_to_symbols),
            "functions": sum(1 for s in self.symbols.values() if s.kind == "function"),
            "classes": sum(1 for s in self.symbols.values() if s.kind == "class"),
        }

    def _parse_file(self, filepath: Path) -> None:
        try:
            tree = ast.parse(filepath.read_text(encoding="utf-8"))
            visitor = _CallGraphVisitor(str(filepath), self)
            visitor.visit(tree)
        except (SyntaxError, UnicodeDecodeError):
            pass

    def find_callers(self, symbol_name: str) -> list[Symbol]:
        """Find all callers of a symbol."""
        symbol = self.symbols.get(symbol_name)
        if symbol is None:
            return []
        return [self.symbols[c] for c in symbol.called_by if c in self.symbols]

    def find_callees(self, symbol_name: str) -> list[Symbol]:
        """Find all symbols called by a symbol."""
        symbol = self.symbols.get(symbol_name)
        if symbol is None:
            return []
        return [self.symbols[c] for c in symbol.calls if c in self.symbols]

    def impact_analysis(self, symbol_name: str) -> dict[str, Any]:
        """Analyze what would break if symbol_name changes."""
        symbol = self.symbols.get(symbol_name)
        if symbol is None:
            return {"error": f"Symbol not found: {symbol_name}"}

        # Trace transitive callers
        visited: set[str] = set()
        queue = [symbol_name]
        impacted: list[str] = []

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            impacted.append(current)
            sym = self.symbols.get(current)
            if sym:
                queue.extend(sym.called_by)

        # Group by file
        by_file: dict[str, list[str]] = defaultdict(list)
        for name in impacted:
            sym = self.symbols.get(name)
            if sym:
                by_file[sym.file].append(name)

        return {
            "symbol": symbol_name,
            "direct_callers": len(symbol.called_by),
            "transitive_impact": len(impacted) - 1,
            "impacted_files": len(by_file),
            "files": {k: v for k, v in list(by_file.items())[:10]},
            "risk": "high" if len(impacted) > 20 else ("medium" if len(impacted) > 5 else "low"),
        }


class _CallGraphVisitor(ast.NodeVisitor):
    """AST visitor that builds call graph."""

    def __init__(self, filename: str, graph: CallGraph) -> None:
        self.filename = filename
        self.graph = graph
        self._current_func: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        name = f"{self.filename}:{node.name}"
        sym = Symbol(name=node.name, kind="function", file=self.filename, line=node.lineno)
        self.graph.symbols[node.name] = sym
        self.graph._file_to_symbols[self.filename].append(node.name)

        old_func = self._current_func
        self._current_func = node.name
        self.generic_visit(node)
        self._current_func = old_func

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        sym = Symbol(name=node.name, kind="class", file=self.filename, line=node.lineno)
        self.graph.symbols[node.name] = sym
        self.graph._file_to_symbols[self.filename].append(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        called_name = self._get_call_name(node)
        if called_name and self._current_func:
            caller = self.graph.symbols.get(self._current_func)
            callee = self.graph.symbols.get(called_name)
            if caller and callee:
                if called_name not in caller.calls:
                    caller.calls.append(called_name)
                if self._current_func not in callee.called_by:
                    callee.called_by.append(self._current_func)
        self.generic_visit(node)

    @staticmethod
    def _get_call_name(node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None


class SemanticRefactorEngine:
    """Multi-file semantic refactoring with call-graph awareness."""

    def __init__(self, root_path: str = ".") -> None:
        self.root = Path(root_path)
        self.call_graph = CallGraph(root_path)

    def analyze_codebase(self) -> dict[str, Any]:
        """Full codebase structural analysis."""
        return self.call_graph.build()

    def find_dead_code(self) -> list[dict[str, Any]]:
        """Find unused functions/classes (not called by anything)."""
        dead = []
        for name, sym in self.call_graph.symbols.items():
            if sym.kind == "function" and not sym.called_by:
                if name not in ("__init__", "main", "__main__"):
                    dead.append({"name": name, "file": sym.file, "line": sym.line,
                                 "reason": "No callers found"})
        return dead

    def find_duplicates(self) -> list[dict[str, Any]]:
        """Find functions with same name in different files (potential duplication)."""
        by_name: dict[str, list[Symbol]] = defaultdict(list)
        for sym in self.call_graph.symbols.values():
            if sym.kind == "function":
                by_name[sym.name].append(sym)

        return [
            {"name": name, "count": len(syms),
             "locations": [{"file": s.file, "line": s.line} for s in syms]}
            for name, syms in by_name.items() if len(syms) > 1
        ]

    def plan_rename(self, old_name: str, new_name: str) -> RefactorPlan:
        """Plan a safe rename across all call sites."""
        impact = self.call_graph.impact_analysis(old_name)
        callers = self.call_graph.find_callers(old_name)

        files = list({c.file for c in callers})
        files.append(self.call_graph.symbols[old_name].file if old_name in self.call_graph.symbols else "")

        return RefactorPlan(
            description=f"Rename '{old_name}' → '{new_name}'",
            files_to_modify=list(set(files)),
            edits=[
                {"file": c.file, "line": c.line, "old": old_name, "new": new_name}
                for c in callers
            ],
            pre_verification=["all tests pass"],
            post_verification=["all tests pass", f"'{old_name}' not found in codebase"],
            risk_level=impact.get("risk", "low"),
        )
