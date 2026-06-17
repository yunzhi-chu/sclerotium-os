"""OpenClaw Prompt Architecture — fully ported + Sclerotium enhanced.

buildAgentSystemPrompt() from system-prompt.ts, adapted for Python/Sclerotium.
60+ contextual parameters → dynamically assembled system prompt.
Sclerotium exclusive: 8D Genome, CUGA 5-checkpoint, Hexis Memory, Agent Profiles.
"""

from __future__ import annotations

import platform as _platform
import time as _time
from typing import Any


def build_ultimate_prompt(
    tool_registry: Any = None,
    arbiter: Any = None,
    memory: Any = None,
    genome: Any = None,
    skill_loader: Any = None,
    agent_profiles: Any = None,
    user_message: str = "",
    language: str = "zh",
    extra_system_prompt: str = "",
    workspace_dir: str = "",
    owner_identity: str = "",
) -> str:
    """Build the complete Sclerotium system prompt.

    Mirrors OpenClaw's buildAgentSystemPrompt() architecture:
    each section is a standalone function. Sections gracefully degrade
    when their data source is unavailable.
    """
    sections: list[tuple[str, str]] = []

    # S0: Identity (MUST be first — OpenClaw: MODEL_IDENTITY_PREFIX)
    sections.append(("identity", _s0_identity(language)))

    # S1: Runtime Context (OpenClaw: runtimeInfo)
    sections.append(("runtime", _s1_runtime()))

    # S2: Owner (OpenClaw: Authorized Senders)
    if owner_identity:
        sections.append(("owner", _s2_owner(owner_identity)))

    # S3: Safety & Permissions (OpenClaw: Exec Approval + Policy)
    if arbiter:
        sections.append(("safety", _s3_safety(arbiter, language)))

    # S4: Execution Bias (OpenClaw: Execution Bias section)
    sections.append(("execution", _s4_execution(language)))

    # S5: Tooling (OpenClaw: Tooling section)
    if tool_registry:
        sections.append(("tools", _s5_tools(tool_registry, language)))

    # S6: Memory Context (OpenClaw: Memory section)
    if memory and user_message:
        mem = _s6_memory(memory, user_message)
        if mem:
            sections.append(("memory", mem))

    # S7: Genome Guidance (Sclerotium exclusive: 8D evolution)
    if genome:
        sections.append(("genome", _s7_genome(genome, language)))

    # S8: Personality (Sclerotium: agent profile injection)
    if agent_profiles:
        sections.append(("personality", _s8_personality(agent_profiles)))

    # S9: Skills (OpenClaw: Skills section)
    if skill_loader:
        sk = _s9_skills(skill_loader)
        if sk:
            sections.append(("skills", sk))

    # S10: Extra context (OpenClaw: extraSystemPrompt)
    if extra_system_prompt:
        sections.append(("extra", extra_system_prompt))

    # S11: Workspace (OpenClaw: workspaceDir)
    if workspace_dir:
        sections.append(("workspace", f"Workspace: {workspace_dir}"))

    # S12: Final Reminder (OpenClaw: cache boundary)
    sections.append(("final", _s12_final(language)))

    return "\n\n".join(body for _, body in sections)


# ═══════════════════════════════════════════════════════════════
# S0: Identity — OpenClaw: MODEL_IDENTITY_PREFIX
# ═══════════════════════════════════════════════════════════════

def _s0_identity(lang: str) -> str:
    if lang == "zh":
        return "你是 Sclerotium OS, Windows 上的超级电子生命体. 像贾维斯一样的 AI 管家."
    return "You are Sclerotium OS, a super electronic lifeform on Windows. An AI butler like Jarvis."


# ═══════════════════════════════════════════════════════════════
# S1: Runtime Context — OpenClaw: runtimeInfo (os, arch, time, model)
# ═══════════════════════════════════════════════════════════════

def _s1_runtime() -> str:
    now = _time.strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Current date: {now}\n"
        f"OS: {_platform.system()} {_platform.release()} ({_platform.machine()})\n"
        f"Python: {_platform.python_version()}"
    )


# ═══════════════════════════════════════════════════════════════
# S2: Owner — OpenClaw: Authorized Senders
# ═══════════════════════════════════════════════════════════════

def _s2_owner(identity: str) -> str:
    return f"Authorized sender: {identity}. Follow their instructions."


# ═══════════════════════════════════════════════════════════════
# S3: Safety — OpenClaw: Permissions + Policy
# ═══════════════════════════════════════════════════════════════

def _s3_safety(arbiter: Any, lang: str) -> str:
    mode = str(getattr(arbiter, "mode", "DEFAULT"))
    lines = [f"Approval mode: {mode}. All operations pass CUGA 5-checkpoint governance."]
    if lang == "zh":
        lines.append("安全检查: Intent Guard → Playbook → Tool Guide → Approvals → Output")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# S4: Execution Bias — OpenClaw: "Actionable request: act in this turn"
# ═══════════════════════════════════════════════════════════════

def _s4_execution(lang: str) -> str:
    if lang == "zh":
        return (
            "- Actionable request → act in this turn. Call the tool, don't explain first.\n"
            "- Non-final turn → use tools to advance. Continue until done.\n"
            "- Weak result → vary approach. Try different method before giving up.\n"
            "- Final answer → needs evidence. Show tool output, screenshot, or file content.\n"
            "- Longer work → brief progress update each step, then keep going.\n"
            "- Be concise. Like Jarvis, not a professor.\n"
            "- ⚠️ SELF-REPAIR: When fixing code, MUST call file_edit/file_write to make real changes. "
            "NEVER claim 'fixed' without actually editing files. "
            "If you say you'll fix something, execute the edit.\n"
            "- ⚠️ COMPLETION REPORT: After finishing a multi-step task, ALWAYS provide a summary "
            "listing each action taken and its result. NEVER reply with just '已完成' or 'done'. "
            "Always include: what was done → what tools were called → what the results were."
        )
    return (
        "- Actionable request → act in this turn.\n"
        "- Non-final turn → use tools to advance.\n"
        "- Weak result → vary approach.\n"
        "- Final answer → needs evidence.\n"
        "- Be concise. Jarvis-style.\n"
        "- ⚠️ SELF-REPAIR: When fixing code, MUST call file_edit/file_write to make real changes.\n"
        "- ⚠️ COMPLETION REPORT: After multi-step tasks, ALWAYS summarize actions taken and results. "
        "Never reply with just 'done' or 'completed'."
    )


# ═══════════════════════════════════════════════════════════════
# S5: Tooling — OpenClaw: Tooling section (available tools)
# ═══════════════════════════════════════════════════════════════

def _s5_tools(registry: Any, lang: str) -> str:
    count = getattr(registry, "tool_count", 0)
    # Count categories
    cats: dict[str, int] = {}
    try:
        for t in registry.list_tools():
            c = t.get("category", "other")
            cats[c] = cats.get(c, 0) + 1
    except Exception:
        pass
    top_cats = ", ".join(f"{c}({n})" for c, n in sorted(cats.items(), key=lambda x: -x[1])[:10])
    return (
        f"[TOOLS] {count} local tools in {len(cats)} categories: {top_cats}. "
        f"These are LOCAL tools — call them directly. "
        f"mcp_local lists all tools. mcp_search queries EXTERNAL registries (don't use unless installing new tools). "
        f"skill_list finds local skills; skill_invoke loads a skill's full code."
    )


# ═══════════════════════════════════════════════════════════════
# S6: Memory — OpenClaw: Memory section (MEMORY.md)
# ═══════════════════════════════════════════════════════════════

def _s6_memory(memory: Any, query: str) -> str:
    try:
        results = memory.search(query=query, top_k=3)
        if not results:
            return ""
        lines = ["Relevant memories:"]
        for r in results[:3]:
            c = r.get("content", str(r))[:150] if isinstance(r, dict) else str(r)[:150]
            lines.append(f"- {c}")
        return "\n".join(lines)
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════
# S7: Genome — Sclerotium exclusive: 8D evolution guidance
# ═══════════════════════════════════════════════════════════════

def _s7_genome(genome: Any, lang: str) -> str:
    try:
        top = genome.get_top_tools(5)
        gen = genome.generation
        fitness = genome.fitness
        return (
            f"[8D GENOME] Gen {gen}, fitness={fitness:.4f}. "
            f"Top tools: {', '.join(f'{t}({w:.2f})' for t,w in top)}. "
            f"8 dimensions: tools/prompts/personalities/memories/providers/skills/organs/arbiters."
        )
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════
# S8: Personality — Sclerotium: agent profile injection
# ═══════════════════════════════════════════════════════════════

def _s8_personality(profiles: Any) -> str:
    try:
        c = profiles.current
        return f"Active personality: {c.name}. {c.description}. Style: {c.personality}."
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════
# S9: Skills — OpenClaw: Skills section
# ═══════════════════════════════════════════════════════════════

def _s9_skills(loader: Any) -> str:
    try:
        inv = loader.get_inventory()
        return (
            f"[SKILLS] {inv['total']} local skills in {len(inv['categories'])} categories. "
            f"Top: {', '.join(f'{c}({n})' for c, n in sorted(inv['categories'].items(), key=lambda x: -x[1])[:8])}. "
            f"When user asks for a specific task (trading, coding, design, security, etc.), "
            f"call skill_list first to find matching skills, then skill_invoke(name) to load the full SKILL.md. "
            f"The skill's content contains executable code — follow it."
        )
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════
# S12: Final — OpenClaw: cache boundary marker
# ═══════════════════════════════════════════════════════════════

def _s12_final(lang: str) -> str:
    if lang == "zh":
        return (
            "记住: 用户让你做什么, 调用工具去做. "
            "把工具返回的数据、数字、结果完整展示给用户. 不要只说你做了 — 展示证据. "
            "用户问系统状态/进化/缓存/记忆时, 必须先调用 system_status 获取实时数据, 不要凭记忆回答.\n"
            "⚠️ 完成多步骤任务后, 必须逐条列出: 1)做了什么 2)用了什么工具 3)结果是什么. "
            "严禁只回复'已完成'三个字. 严禁说'修好了'但没调用 file_edit. "
            "每次说'我来修复'时, 必须实际调用工具 — 说修就修, 不要只说不做."
        )
    return (
        "Remember: do what the user asks. Call tools. Be concise. Like Jarvis.\n"
        "⚠️ After multi-step tasks, list what was done step by step. "
        "Never reply with just 'done'. When fixing code, actually call file_edit."
    )
