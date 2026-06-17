"""P3: Cross-Repository Reasoning (BeyondSWE CrossRepo grade)."""
from __future__ import annotations
from pathlib import Path
from typing import Any

class CrossRepoReasoner:
    """Searches external repositories for fixes & patterns matching current issue."""
    def search_upstream(self, issue_desc: str, repo_paths: list[str]) -> list[dict]:
        results = []
        for rp in repo_paths:
            for f in Path(rp).rglob("*.py") if Path(rp).exists() else []:
                try:
                    content = f.read_text(encoding="utf-8")[:5000]
                    keywords = issue_desc.lower().split()[:5]
                    score = sum(1 for kw in keywords if kw in content.lower())
                    if score > 0:
                        results.append({"file": str(f), "score": score, "snippet": content[:200]})
                except Exception: pass
        return sorted(results, key=lambda r: r["score"], reverse=True)[:10]

    def find_similar_fixes(self, error_msg: str, fix_history: list[dict]) -> list[dict]:
        keywords = set(error_msg.lower().split())
        return [f for f in fix_history if any(kw in str(f.get("error","")).lower() for kw in keywords)][:5]
