"""Skill registry — hot-swappable skill loader with dependency resolution.

Maps 209 QuantMind skills into a unified registry with topological ordering.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class SkillMeta:
    """Metadata for a registered skill."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    module: str = ""  # e.g., "l6-cognition-platform", "adaptive-engine"
    category: str = ""  # e.g., "core", "alphaear", "agent-plugin", "vertical-plugin"
    keywords: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # skill names this depends on
    file_path: str = ""  # path to SKILL.md
    entry_point: str = ""  # importable Python path
    enabled: bool = True
    call_count: int = 0
    last_called: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "module": self.module,
            "category": self.category,
            "keywords": self.keywords,
            "dependencies": self.dependencies,
            "enabled": self.enabled,
            "call_count": self.call_count,
        }


class SkillRegistry:
    """Central registry for all 209 QuantMind skills.

    Supports:
    - Hot-reload (register / unregister at runtime)
    - Dependency validation (topological sort)
    - Skill lookup by name, keyword, module, category
    - Activation tracking (call_count, last_called)
    """

    def __init__(self) -> None:
        self._skills: dict[str, SkillMeta] = {}
        self._by_module: dict[str, list[str]] = {}
        self._by_keyword: dict[str, list[str]] = {}
        self._by_category: dict[str, list[str]] = {}
        self._logger = CortexLogger("skill_registry")

    def register(self, skill: SkillMeta) -> bool:
        """Register a new skill. Returns False if name already taken."""
        if skill.name in self._skills:
            self._logger.warn("skill_already_registered", name=skill.name)
            return False
        self._skills[skill.name] = skill
        self._by_module.setdefault(skill.module, []).append(skill.name)
        self._by_category.setdefault(skill.category, []).append(skill.name)
        for kw in skill.keywords:
            self._by_keyword.setdefault(kw, []).append(skill.name)
        self._logger.info("skill_registered", name=skill.name, module=skill.module)
        return True

    def unregister(self, name: str) -> bool:
        """Remove a skill. Fails if other skills depend on it."""
        dependents = [s.name for s in self._skills.values() if name in s.dependencies]
        if dependents:
            self._logger.warn("skill_unregister_blocked", name=name, dependents=dependents)
            return False
        skill = self._skills.pop(name, None)
        if skill is None:
            return False
        self._by_module[skill.module].remove(name)
        self._by_category[skill.category].remove(name)
        for kw in skill.keywords:
            self._by_keyword[kw].remove(name)
        self._logger.info("skill_unregistered", name=name)
        return True

    def get(self, name: str) -> SkillMeta | None:
        """Lookup a skill by name."""
        return self._skills.get(name)

    def list_all(self) -> list[SkillMeta]:
        """Return all registered skills."""
        return list(self._skills.values())

    def search(self, query: str) -> list[SkillMeta]:
        """Search by name, keyword, description (case-insensitive substring)."""
        q = query.lower()
        results: list[SkillMeta] = []
        for skill in self._skills.values():
            if q in skill.name.lower() or q in skill.description.lower():
                results.append(skill)
                continue
            if any(q in kw.lower() for kw in skill.keywords):
                results.append(skill)
        return results

    def by_module(self, module: str) -> list[SkillMeta]:
        """Get all skills in a module."""
        return [self._skills[n] for n in self._by_module.get(module, [])]

    def by_category(self, category: str) -> list[SkillMeta]:
        """Get all skills in a category."""
        return [self._skills[n] for n in self._by_category.get(category, [])]

    def resolve_dependencies(self, name: str) -> list[str]:
        """Topological sort of dependencies for a skill. Raises on cyclic deps."""
        resolved: list[str] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def dfs(n: str) -> None:
            if n in visited:
                return
            if n in visiting:
                raise ValueError(f"Circular dependency detected: {n}")
            visiting.add(n)
            skill = self._skills.get(n)
            if skill:
                for dep in skill.dependencies:
                    if dep in self._skills:
                        dfs(dep)
            visiting.discard(n)
            visited.add(n)
            if n != name:
                resolved.append(n)

        dfs(name)
        resolved.append(name)
        return resolved

    def get_load_order(self) -> list[str]:
        """Return all skills in topological dependency order."""
        all_names = list(self._skills)
        visited: set[str] = set()
        order: list[str] = []

        def visit(n: str, path: set[str]) -> None:
            if n in visited:
                return
            if n in path:
                raise ValueError(f"Circular dependency: {n}")
            path.add(n)
            skill = self._skills.get(n)
            if skill:
                for dep in skill.dependencies:
                    visit(dep, path)
            path.discard(n)
            visited.add(n)
            order.append(n)

        for name in all_names:
            visit(name, set())
        return order

    @property
    def count(self) -> int:
        return len(self._skills)

    @property
    def enabled_count(self) -> int:
        return sum(1 for s in self._skills.values() if s.enabled)

    def record_call(self, name: str) -> None:
        """Record a skill invocation for analytics."""
        import time
        skill = self._skills.get(name)
        if skill:
            skill.call_count += 1
            skill.last_called = time.time()

    def import_from_quantmind(self, skills_dir: Path) -> int:
        """Bulk-import skills from QuantMind skill directories."""
        imported = 0
        for skill_file in skills_dir.rglob("SKILL.md"):
            skill = self._parse_skill_file(skill_file)
            if skill and self.register(skill):
                imported += 1
        self._logger.info("bulk_import_complete", imported=imported, total=self.count)
        return imported

    def _parse_skill_file(self, file_path: Path) -> SkillMeta | None:
        """Parse a SKILL.md file into SkillMeta. Best-effort extraction."""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            name = file_path.parent.name
            description = ""
            version = "1.0.0"
            keywords: list[str] = []
            for line in lines[:50]:
                if line.startswith("# "):
                    name = line[2:].strip()
                elif line.startswith("description:") or line.startswith("Description:"):
                    description = line.split(":", 1)[1].strip()
                elif line.startswith("version:") or line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                elif line.startswith("tags:") or line.startswith("keywords:"):
                    kw_str = line.split(":", 1)[1].strip()
                    keywords = [k.strip() for k in kw_str.split(",") if k.strip()]

            module = file_path.parent.parent.name if file_path.parent.parent.name != "QuantAgent" else file_path.parent.name
            category = self._classify_category(file_path)

            return SkillMeta(
                name=name,
                version=version,
                description=description,
                module=module,
                category=category,
                keywords=keywords,
                file_path=str(file_path.absolute()),
                entry_point=f"quantmind.{module}.{name.lower().replace('-', '_')}",
            )
        except Exception:
            return None

    @staticmethod
    def _classify_category(file_path: Path) -> str:
        """Classify a skill file into its category based on path."""
        path_str = str(file_path).lower()
        if "agent-plugins" in path_str:
            return "agent-plugin"
        if "vertical-plugins" in path_str:
            return "vertical-plugin"
        if "alphaear" in path_str:
            return "alphaear"
        if "data-pack" in path_str:
            return "data-pack"
        if "l6-cognition" in path_str or "l5-cluster" in path_str or "l4-autonomous" in path_str:
            return "platform"
        if "adaptive-engine" in path_str:
            return "engine"
        return "core"
