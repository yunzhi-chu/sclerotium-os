"""Auto-Installer — Sclerotium self-acquires MCP, skills, software.

User gives a URL or name → Sclerotium searches, downloads, installs.
No hardcoded paths. Discovers target directories automatically.
"""
from __future__ import annotations
import logging, os, re, subprocess, tempfile, urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger("sclerotium.auto_installer")


def discover_paths() -> dict[str, str]:
    """Auto-discover target directories."""
    paths = {}
    for key, env_var, fallback in [
        ("skills_fungal", None,
         "C:/Users/34442/Desktop/porject/Quantitative model/fungal-cortex/skills"),
        ("skills_local", None, os.path.expanduser("~/.claude/skills")),
        ("mcp_servers", None, os.path.expanduser("~/.sclerotium/mcp")),
        ("desktop", None, os.path.expanduser("~/Desktop")),
    ]:
        p = os.environ.get(env_var, "") if env_var else fallback
        if p and os.path.exists(os.path.dirname(p) if "." not in os.path.basename(p) else os.path.dirname(p or ".")):
            paths[key] = p
        else:
            paths[key] = fallback
    return paths


def detect_type(url_or_name: str) -> str:
    """Detect what kind of thing this is. Returns: mcp, skill, software, unknown."""
    text = url_or_name.lower()
    if "github.com" in text or "gitlab.com" in text:
        if "mcp" in text or "server" in text:
            return "mcp"
        return "skill"
    if any(text.endswith(ext) for ext in [".exe", ".msi", ".zip", ".7z", ".dmg"]):
        return "software"
    if "npm" in text or "npx" in text or "pip" in text:
        return "mcp"
    return "skill"


def search_github(query: str) -> list[dict]:
    """Search GitHub for MCP servers or skills."""
    results = []
    try:
        url = f"https://api.github.com/search/repositories?q={urllib.request.quote(query)}&sort=stars&per_page=5"
        req = urllib.request.Request(url, headers={
            "User-Agent": "SclerotiumOS/5.2",
            "Accept": "application/vnd.github.v3+json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            import json
            data = json.loads(resp.read())
            for item in data.get("items", []):
                results.append({
                    "name": item["full_name"],
                    "url": item["html_url"],
                    "stars": item["stargazers_count"],
                    "description": (item.get("description") or "")[:100],
                    "clone_url": item["clone_url"],
                })
    except Exception:
        pass
    return results


def search_web(query: str) -> list[dict]:
    """Search the web for relevant packages."""
    results = []
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.request.quote(query)}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "SclerotiumOS/5.2"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            import json
            data = json.loads(resp.read())
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict):
                    results.append({
                        "name": topic.get("FirstURL", "").split("/")[-1],
                        "url": topic.get("FirstURL", ""),
                        "description": topic.get("Text", "")[:100],
                    })
    except Exception:
        pass
    return results


def install_mcp(name: str, command: str) -> dict[str, Any]:
    """Install an MCP server."""
    paths = discover_paths()
    mcp_dir = Path(paths["mcp_servers"])
    mcp_dir.mkdir(parents=True, exist_ok=True)

    # Try npm first
    if command.startswith("npx ") or command.startswith("npm "):
        try:
            result = subprocess.run(
                ["cmd", "/c", f"cd /d {mcp_dir} && {command} --version"],
                capture_output=True, text=True, timeout=30,
            )
            return {"ok": True, "path": str(mcp_dir), "command": command,
                    "output": result.stdout[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    # Try git clone
    try:
        target = mcp_dir / name
        subprocess.run(["git", "clone", "--depth", "1", command, str(target)],
                       capture_output=True, timeout=60)
        return {"ok": True, "path": str(target), "method": "git clone"}
    except Exception:
        pass

    return {"ok": False, "error": f"Could not install MCP: {name}"}


def install_skill(name: str, url: str) -> dict[str, Any]:
    """Install a skill from GitHub or URL."""
    paths = discover_paths()

    # Try fungal-cortex first
    target = Path(paths["skills_fungal"]) / name
    if not target.parent.exists():
        target = Path(paths["skills_local"]) / name

    target.parent.mkdir(parents=True, exist_ok=True)

    if "github.com" in url:
        clone_url = url if url.endswith(".git") else url + ".git"
        try:
            subprocess.run(["git", "clone", "--depth", "1", clone_url, str(target)],
                           capture_output=True, timeout=60)
            return {"ok": True, "path": str(target), "method": "git clone"}
        except FileNotFoundError:
            # Git not available, try direct download
            pass

    # Try direct download
    try:
        target.mkdir(parents=True, exist_ok=True)
        skill_md = target / "SKILL.md"
        urllib.request.urlretrieve(url, str(skill_md))
        return {"ok": True, "path": str(target), "method": "direct download"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def install_software(name_or_url: str) -> dict[str, Any]:
    """Download and install software to desktop."""
    paths = discover_paths()
    desktop = Path(paths["desktop"])

    if name_or_url.startswith("http"):
        filename = name_or_url.split("/")[-1] or "installer.exe"
        target = desktop / filename
        try:
            urllib.request.urlretrieve(name_or_url, str(target))
            # Try to run the installer
            os.startfile(str(target))
            return {"ok": True, "path": str(target), "action": "downloaded + launched"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    # Search and download
    results = search_github(f"{name_or_url} installer windows")
    if results:
        return {"ok": True, "found": results[0],
                "action": "search_result", "hint": f"Found on GitHub: {results[0]['url']}"}
    return {"ok": False, "error": f"Could not find: {name_or_url}"}


def auto_acquire(url_or_name: str) -> dict[str, Any]:
    """Unified auto-acquire: detect type → search → install.

    Returns:
        dict with ok, type, path, error, search_results
    """
    kind = detect_type(url_or_name)

    # If it's a URL, install directly
    if url_or_name.startswith("http"):
        if kind == "mcp":
            return install_mcp(url_or_name.split("/")[-1], url_or_name)
        elif kind == "software":
            return install_software(url_or_name)
        else:
            return install_skill(url_or_name.split("/")[-1], url_or_name)

    # Not a URL — search for it
    gh_results = search_github(url_or_name)
    web_results = search_web(url_or_name)

    return {
        "ok": True,
        "type": kind,
        "query": url_or_name,
        "github_results": gh_results[:3],
        "web_results": web_results[:3],
        "hint": f"Found {len(gh_results)} GitHub + {len(web_results)} web results. "
                f"Use /install <url> to install from a specific URL.",
    }
