"""MCP Skill Tools — skill_list, skill_invoke, skill_register.

Uses the local SkillLoader (5,826 skills from fungal-cortex + ~/.claude)
NOT the unreachable fungal-cortex internal SkillRegistry.
"""

from __future__ import annotations

from typing import Any

from mcp.server import ToolRegistry


def _get_skill_loader() -> Any:
    """Get the local SkillLoader with all scanned skills."""
    from kernel.skill_loader import SkillLoader
    loader = SkillLoader()
    if loader.skill_count == 0:
        loader.scan()
    return loader


async def _skill_list(status: str = "active") -> dict[str, Any]:
    """List all locally loaded skills with categories."""
    loader = _get_skill_loader()
    skills = loader.list_skills()
    inventory = loader.get_inventory()
    return {
        "total": len(skills),
        "categories": inventory.get("categories", {}),
        "sources": inventory.get("sources", {}),
        "skills": skills[:100],  # First 100, full list too large
        "note": f"Showing 100 of {len(skills)} total. Use skill_invoke to use a specific skill.",
    }


async def _skill_invoke(skill_name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Invoke a skill by name — returns its content and metadata."""
    import time
    start = time.monotonic()
    params = params or {}

    loader = _get_skill_loader()
    skill = loader.get_skill(skill_name)
    if skill is None:
        return {
            "skill_name": skill_name,
            "found": False,
            "error": f"Skill '{skill_name}' not found in {loader.skill_count} loaded skills",
            "hint": "Use skill_list to see available skills",
        }

    # Read full SKILL.md content to give LLM complete instructions
    full_content = ""
    try:
        with open(skill.path, encoding="utf-8", errors="replace") as f:
            full_content = f.read()
    except Exception:
        full_content = skill.content

    return {
        "skill_name": skill_name,
        "found": True,
        "category": skill.category,
        "description": skill.description,
        "path": skill.path,
        "content": full_content,  # FULL skill instructions for LLM to follow
        "instruction": f"READ THE CONTENT ABOVE. It contains executable Python code to fetch A-stock data. Use bash_execute to run the code snippets. Complete ALL steps before responding.",
        "token_estimate": skill.token_estimate,
        "duration_ms": round((time.monotonic() - start) * 1000, 1),
    }


async def _skill_register(name: str, code: str = "", description: str = "",
                          dependencies: list[str] | None = None,
                          validated_by: str = "human") -> dict[str, Any]:
    """Register a new skill."""
    # Store in local skills directory
    import os
    skills_dir = os.path.expanduser("~/.sclerotium/skills")
    skill_dir = os.path.join(skills_dir, name)
    os.makedirs(skill_dir, exist_ok=True)

    skill_md = f"""---
name: {name}
description: {description or name}
category: user_registered
validated_by: {validated_by}
---
# {name}

{description or 'Custom skill registered via Sclerotium OS.'}
"""
    with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_md)

    # Re-scan to pick up new skill
    loader = _get_skill_loader()
    loader.scan()

    return {
        "skill_name": name,
        "status": "registered",
        "path": skill_dir,
    }


def register_skills_tools(registry: ToolRegistry) -> None:
    registry.register(
        name="skill_list",
        description="List all locally loaded skills (5,826 from fungal-cortex + ~/.claude/skills). Shows count, categories, and first 100 skills.",
        parameters={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter: active, deprecated, or all",
                    "enum": ["active", "deprecated", "all"],
                    "default": "active",
                },
            },
            "required": [],
        },
        handler=_skill_list,
        category="skills",
    )

    registry.register(
        name="skill_invoke",
        description="Get a skill's full metadata and content by name.",
        parameters={
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill to look up",
                },
                "params": {
                    "type": "object",
                    "description": "Parameters for the skill (optional)",
                },
            },
            "required": ["skill_name"],
        },
        handler=_skill_invoke,
        category="skills",
    )

    registry.register(
        name="skill_register",
        description="Register a new skill locally. Creates SKILL.md in ~/.sclerotium/skills/.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Unique skill name"},
                "description": {"type": "string", "description": "What the skill does", "default": ""},
                "code": {"type": "string", "description": "Skill code", "default": ""},
                "dependencies": {"type": "array", "items": {"type": "string"}},
                "validated_by": {"type": "string", "description": "arena/crystallizer/human", "default": "human"},
            },
            "required": ["name"],
        },
        handler=_skill_register,
        category="skills",
    )
