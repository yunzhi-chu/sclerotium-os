"""P3: Global Dependency Migration (BeyondSWE DepMigrate grade)."""
from __future__ import annotations
import ast
from pathlib import Path
from typing import Any

class DependencyMigrator:
    """Global API migration across entire codebase (e.g., NumPy 1.x→2.0)."""
    def __init__(self): self._rules: dict[str, dict] = {}
    def add_rule(self, old_api: str, new_api: str, old_import: str = "", new_import: str = ""):
        self._rules[old_api] = {"new_api": new_api, "old_import": old_import, "new_import": new_import}
    def scan(self, root: str) -> list[dict]:
        """Scan entire codebase for deprecated API usages."""
        findings = []
        for f in Path(root).rglob("*.py"):
            if ".venv" in str(f) or "__pycache__" in str(f): continue
            try:
                content = f.read_text(encoding="utf-8")
                for old, rule in self._rules.items():
                    if old in content:
                        count = content.count(old)
                        findings.append({"file": str(f), "old_api": old, "new_api": rule["new_api"], "count": count,
                                         "old_import": rule.get("old_import",""), "new_import": rule.get("new_import","")})
            except Exception: pass
        return sorted(findings, key=lambda x: x["count"], reverse=True)
    def auto_fix(self, filepath: str, dry_run: bool = True) -> dict:
        """Auto-replace deprecated APIs in a file."""
        p = Path(filepath)
        if not p.exists(): return {"error": "File not found"}
        content = p.read_text(encoding="utf-8")
        changes = 0
        for old, rule in self._rules.items():
            if old in content:
                changes += content.count(old)
                content = content.replace(old, rule["new_api"])
        if not dry_run and changes > 0:
            p.write_text(content, encoding="utf-8")
        return {"file": filepath, "changes": changes, "dry_run": dry_run}
