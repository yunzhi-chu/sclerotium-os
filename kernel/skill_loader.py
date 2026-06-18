"""Dynamic Skill Loader — auto-discover all local skills. No hardcoding.

Scans:
  1. fungal-cortex/skills/ (installed skills)
  2. ~/.claude/skills/ (locally installed)
  3. ./skills/ (project-local)

Lazy-load: 技能不存在时自动从 manifest 安装（git clone 或 submodule）。
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from kernel.project_paths import FUNGAL_CORTEX

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
        self._manifest: dict[str, Any] | None = None

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

        # Fallback: use fungal-cortex/skills
        if not paths:
            fc = str(FUNGAL_CORTEX / "skills")
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
        """获取技能，不存在时自动尝试按需加载。"""
        sk = self._skills.get(name)
        if sk:
            return sk
        return self._lazy_load_skill(name)

    # ── 按需加载（manifest + git clone / submodule） ────────────

    def _load_manifest(self) -> dict[str, Any] | None:
        if self._manifest is not None:
            return self._manifest
        manifest_path = FUNGAL_CORTEX / "skills" / "skill_manifest.json"
        if not manifest_path.exists():
            self._manifest = {}
            return self._manifest
        try:
            self._manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            return self._manifest
        except Exception:
            self._manifest = {}
            return self._manifest

    def _lazy_load_skill(self, name: str) -> LoadedSkill | None:
        """按技能名查找 manifest 并尝试安装。"""
        manifest = self._load_manifest()
        if not manifest:
            return None

        skills = manifest.get("skills", {})
        # 尝试精确匹配
        info = skills.get(name)
        if not info:
            # 尝试模糊匹配（去掉 -main 后缀等）
            for key, val in skills.items():
                if val.get("dir", "").startswith(name) or key == name:
                    info = val
                    break
        if not info:
            return None

        target_dir = FUNGAL_CORTEX / "skills" / info["dir"]
        if target_dir.exists():
            # 已安装，重新扫描
            self._scan_single(target_dir)
            return self._skills.get(name)

        print(f"[技能] 按需加载: {name} ({info.get('description', '')})")
        repo_url = info.get("url", "")

        # 优先 submodule
        root = FUNGAL_CORTEX.parent
        sub_path = f"fungal-cortex/skills/{info['dir']}"
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "submodule", "update", "--init", "--depth", "1", sub_path],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                print(f"  [✓] 通过 submodule 安装: {name}")
                self._scan_single(target_dir)
                return self._skills.get(name)
        except Exception:
            pass

        # fallback: git clone 到本地
        if repo_url:
            try:
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", repo_url, str(target_dir)],
                    capture_output=True, text=True, timeout=120,
                )
                if result.returncode == 0:
                    print(f"  [✓] 已克隆: {name}")
                    self._scan_single(target_dir)
                    return self._skills.get(name)
                print(f"  [✗] 克隆失败: {result.stderr[:200]}")
            except Exception as e:
                print(f"  [✗] {e}")

        print(f"  [!] 未安装可用: {name}。运行: scripts/install_skill.ps1 -Name {name}")
        return None

    def _scan_single(self, skill_dir: Path) -> None:
        """扫描单个技能目录并注册找到的 SKILL.md。"""
        if not skill_dir.exists():
            return
        for sf in skill_dir.rglob("SKILL.md"):
            try:
                with open(sf, encoding="utf-8", errors="replace") as f:
                    head = f.read(2048)
                sname = sf.parent.name
                desc = SkillLoader._extract_description(head)
                self._skills[sname] = LoadedSkill(
                    name=sname, path=str(sf), description=desc,
                    content=head, token_estimate=len(head) // 4,
                )
            except Exception:
                continue

    @property
    def skill_count(self) -> int:
        return len(self._skills)

    @property
    def total_tokens(self) -> int:
        return self._total_tokens
