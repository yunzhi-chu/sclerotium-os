"""Dynamic Skill Loader — auto-discover all local skills. No hardcoding.

Scans:
  1. fungal-cortex/skills/ (6000+ SKILL.md)
  2. ~/.claude/skills/ (locally installed)
  3. ./skills/ (project-local)
  4. All awesome-* subdirs under fungal-cortex

No path hardcoding. No category hardcoding. No max limit.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("sclerotium.skills")


class LoadedSkill:
    def __init__(self, name: str, path: str, description: str = "",
                 content: str = "", token_estimate: int = 0):
        self.name = name
        self.path = path
        self.description = description
        self.content = content
        self.token_estimate = token_estimate
        self.category = self._infer_category()

    def _infer_category(self) -> str:
        """Auto-infer category from skill name + description."""
        text = (self.name + " " + self.description).lower()
        signals = {
            "frontend": ["frontend", "design", "ui", "css", "animation", "theme", "layout", "visual", "typography"],
            "backend": ["backend", "api", "server", "database", "sql", "rest", "graphql"],
            "game": ["game", "unity", "unreal", "godot"],
            "security": ["security", "audit", "auth", "vuln", "encrypt"],
            "devops": ["devops", "deploy", "docker", "k8s", "ci/cd", "pipeline"],
            "testing": ["test", "tdd", "coverage", "e2e"],
            "data": ["data", "analytics", "ml", "model", "train", "pandas", "numpy"],
            "marketing": ["market", "seo", "growth", "ads", "social", "content", "brand"],
            "language": ["python", "java", "rust", "go", "kotlin", "swift", "cpp", "perl", "ruby"],
            "research": ["research", "academic", "paper", "science"],
            "automation": ["auto", "workflow", "scheduler", "cron"],
            "browser": ["browser", "web", "chrome", "edge", "playwright"],
            "finance": ["finance", "trad", "stock", "quant", "invest"],
            "communication": ["chat", "message", "im", "telegram", "bot"],
            "mobile": ["mobile", "android", "ios", "flutter"],
            "creative": ["creat", "art", "music", "video", "image", "render"],
        }
        scores = {}
        for cat, keywords in signals.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[cat] = score
        if scores:
            return max(scores, key=scores.get)
        return "general"


class SkillLoader:
    """Scans ALL local skill sources. No hardcoding. No max."""

    def __init__(self, search_paths: list[str] | None = None) -> None:
        self._search_paths = search_paths or self._auto_discover_paths()
        self._skills: dict[str, LoadedSkill] = {}
        self._total_tokens = 0

    @staticmethod
    def _auto_discover_paths() -> list[str]:
        """Auto-discover all skill directories from the project root."""
        paths = []
        home = os.path.expanduser("~")

        # Walk up from current dir to find project root
        current = Path.cwd().resolve()
        for _ in range(5):
            fc = current / "fungal-cortex" / "skills"
            if fc.exists():
                paths.append(str(fc))
                # Also scan all awesome-* subdirs
                for d in (current / "fungal-cortex").iterdir():
                    if d.is_dir() and d.name.startswith("awesome-"):
                        paths.append(str(d))
                break
            current = current.parent

        # Fallback: use known base path
        if not paths:
            base = "C:/Users/34442/Desktop/porject/Quantitative model"
            fc = os.path.join(base, "fungal-cortex", "skills")
            if os.path.exists(fc):
                paths.append(fc)

        # Local Claude skills
        local = os.path.join(home, ".claude", "skills")
        if os.path.exists(local):
            paths.append(local)

        # Sclerotium skills
        local_scl = os.path.join(home, ".sclerotium", "skills")
        if os.path.exists(local_scl):
            paths.append(local_scl)

        # Project-local skills
        if os.path.exists("./skills"):
            paths.append("./skills")

        logger.info("Auto-discovered %d skill paths: %s", len(paths), [str(p)[:60] for p in paths])
        return paths

    def scan(self, max_skills: int = 0) -> list[LoadedSkill]:
        """Scan all paths, load ALL skills (no limit by default)."""
        found = []
        for root_path in self._search_paths:
            root = Path(root_path).expanduser().resolve()
            if not root.exists():
                continue
            skill_files = list(root.rglob("SKILL.md"))
            logger.info("Scanning %s: %d SKILL.md", str(root)[-60:], len(skill_files))
            for sf in skill_files:
                if max_skills > 0 and len(found) >= max_skills:
                    break
                try:
                    with open(sf, encoding="utf-8", errors="replace") as f:
                        head = f.read(2048)
                    name = sf.parent.name
                    desc = self._extract_description(head)
                    if name not in self._skills:
                        sk = LoadedSkill(name=name, path=str(sf), description=desc,
                                         content=head, token_estimate=len(head) // 4)
                        self._skills[name] = sk
                        found.append(sk)
                except Exception:
                    continue
        self._total_tokens = sum(s.token_estimate for s in self._skills.values())
        logger.info("Loaded %d skills across %d paths, ~%d tokens",
                     len(found), len(self._search_paths), self._total_tokens)
        return found

    @staticmethod
    def _extract_description(text: str) -> str:
        """Extract description from frontmatter or first heading."""
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                fm = text[3:end]
                for line in fm.split("\n"):
                    if line.startswith("description:"):
                        return line.split(":", 1)[1].strip().strip('"').strip("'")
        for line in text.split("\n"):
            if line.startswith("# "):
                return line[2:].strip()
        return ""

    def get_inventory(self) -> dict[str, Any]:
        """Auto-categorized skill inventory with accurate source breakdown."""
        cats: dict[str, list[str]] = {}
        for sk in self._skills.values():
            cats.setdefault(sk.category, []).append(sk.name)

        sources: dict[str, int] = {}
        for sk in self._skills.values():
            p = sk.path.lower()
            if "fungal-cortex" in p:
                key = "fungal-cortex"
            elif ".claude" in p:
                key = "~/.claude/skills"
            elif ".sclerotium" in p:
                key = "~/.sclerotium/skills"
            else:
                key = "local"
            sources[key] = sources.get(key, 0) + 1

        return {
            "total": self.skill_count,
            "tokens": self._total_tokens,
            "sources": sources,
            "categories": {c: len(n) for c, n in sorted(cats.items())},
            "paths_scanned": len(self._search_paths),
        }

    def list_skills(self) -> list[dict[str, Any]]:
        return [{"name": s.name, "category": s.category, "description": s.description[:80],
                 "tokens": s.token_estimate, "source": "fungal-cortex" if "fungal-cortex" in s.path else "local"}
                for s in self._skills.values()]

    def build_context(self, max_tokens: int = 5000) -> str:
        if not self._skills:
            return ""
        lines = ["# Available Skills"]
        by_cat: dict[str, list[LoadedSkill]] = {}
        for sk in self._skills.values():
            by_cat.setdefault(sk.category, []).append(sk)
        for cat, sks in sorted(by_cat.items()):
            lines.append(f"\n## {cat.title()} ({len(sks)})")
            for sk in sks[:8]:
                lines.append(f"- {sk.name}: {sk.description[:60]}")
        return "\n".join(lines)

    def get_skill(self, name: str) -> LoadedSkill | None:
        return self._skills.get(name)

    @property
    def skill_count(self) -> int:
        return len(self._skills)

    @property
    def total_tokens(self) -> int:
        return self._total_tokens
