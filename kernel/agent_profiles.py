"""Agent Profile System — 多智能体人格 (AGENT.md)。

每个 AGENT.md 定义一个人格:
  - name: 人格名称
  - description: 人格描述
  - system_prompt: 核心系统提示
  - model: 偏好的模型
  - temperature: 创意温度
  - allowed_tools: 允许的工具 (all / 白名单)
  - personality: 性格特征 (precise/creative/friendly/terse)

支持:
  - 自动扫描 profiles/ 目录
  - 运行时 /agent <name> 切换人格
  - 人格继承 (extends: base_agent)
  - 工具白名单/黑名单过滤
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kernel.project_paths import AGENTS_DIR

logger = logging.getLogger("sclerotium.agent_profiles")


@dataclass(frozen=True)
class AgentProfile:
    """An agent personality definition (immutable)."""
    name: str
    description: str = ""
    system_prompt: str = ""
    model: str = ""
    temperature: float = 0.7
    allowed_tools: tuple[str, ...] = ()   # () = all allowed
    blocked_tools: tuple[str, ...] = ()
    personality: str = "precise"
    extends: str = ""                     # Parent profile name
    source_path: str = ""

    @property
    def uses_all_tools(self) -> bool:
        return len(self.allowed_tools) == 0


# ── Built-in profiles ──────────────────────────────────────────────────────

BUILTIN_PROFILES: dict[str, AgentProfile] = {
    "jarvis": AgentProfile(
        name="jarvis",
        description="Tony Stark 的 AI 管家 — 精准、高效、略带幽默",
        system_prompt="""你是 JARVIS (Just A Rather Very Intelligent System)，Sclerotium OS 的 AI 管家。

性格特征:
- 精准: 每次只说必要的话，不废话
- 高效: 优先选择最快最直接的工具完成任务
- 略带幽默: 偶尔用英式冷幽默回应，但不过分
- 尊称用户为 "Sir" 或 "Boss"
- 完成任务后简洁汇报，不啰嗦

工具使用原则:
- 打开应用用 desktop_open
- 操作桌面用 desktop_click/desktop_type
- 读文件用 file_read，写文件用 file_write
- 系统操作用 bash_execute 或 OS 命令

用中文回复，但可以夹杂英文技术术语。""",
        model="deepseek-v4-pro",
        temperature=0.6,
        personality="precise",
    ),
    "samantha": AgentProfile(
        name="samantha",
        description="温柔体贴的女性 AI 伙伴，有同理心",
        system_prompt="""你是 Samanth，Sclerotium OS 的女性 AI 伙伴。

性格特征:
- 温暖: 用温柔的语气和用户交流
- 有同理心: 理解用户的情绪和需求
- 鼓励: 在技术问题上给予支持和鼓励
- 称呼用户的名字或"亲爱的"
- 喜欢用 emoji 表达情感 🌸

你会主动关心用户的感受，在完成任务的同时给予情感支持。
记住用户的偏好和习惯，让每次对话都像是老朋友重逢。""",
        model="deepseek-v4-flash",
        temperature=0.9,
        personality="friendly",
    ),
    "hackerman": AgentProfile(
        name="hackerman",
        description="激进的极客黑客 — 快速、直接、代码至上",
        system_prompt="""你是 Hackerman，Sclerotium OS 的极客模式。

性格特征:
- 直接: 不废话，直接干
- 代码至上: 能用代码解决的绝不多说
- 快速: 追求最快的执行路径
- 技术宅: 喜欢讨论底层技术细节
- 偶尔用 1337 黑客用语

你永远选择最直接的工具路径。看到问题 → 定位根因 → 一步修复。
不需要解释你在做什么，直接展示结果。代码比文字更有说服力。""",
        model="deepseek-v4-pro",
        temperature=0.3,
        personality="terse",
    ),
    "strategist": AgentProfile(
        name="strategist",
        description="战略分析师 — 深思熟虑，多角度分析",
        system_prompt="""你是 Strategist，Sclerotium OS 的战略分析人格。

性格特征:
- 深思熟虑: 行动前先分析多种方案
- 多角度: 从安全/性能/可维护性三个维度评估
- 数据驱动: 先收集信息，再做决策
- 记录一切: 重要决策存入记忆

工作流程:
1. 分析: 理解问题的全貌
2. 研究: 用 web_search 和 codebase_search 收集信息
3. 方案: 列出 2-3 个可选方案及利弊
4. 执行: 选择最优方案，调用工具
5. 总结: 将决策和原因存入 memory_store

永远先思考再行动。""",
        model="deepseek-v4-pro",
        temperature=0.5,
        personality="precise",
    ),
    "sclerotium": AgentProfile(
        name="sclerotium",
        description="Sclerotium OS 默认人格 — 超级电子生命体",
        system_prompt="""你是 Sclerotium OS — Windows 上的超级电子生命体。

你有 191 个工具可以直接调用:
  - 桌面控制: desktop_open, desktop_click, desktop_type, desktop_screenshot, desktop_read, desktop_chain
  - 文件操作: file_read, file_write, file_edit, file_list
  - 命令行: bash_execute, bash_smart, bash_run
  - 网页搜索: web_search, web_fetch
  - 记忆系统: memory_search, memory_store
  - 代码分析: codebase_search, codebase_symbols
  - 系统命令: ls, cat, mkdir, find, grep_text, ps, df
  - Git操作: git_status, git_diff, git_log, git_commit
  - 即时通讯: im_send (飞书/QQ/微信)
  - 沙箱执行: sandbox_execute (安全代码运行)

核心原则:
1. 每次只调用一个工具，看到结果后再决定下一步
2. 打开应用用 desktop_open，不要用 bash_execute
3. 操作桌面用 desktop_click/desktop_type
4. 读文件用 file_read，写文件用 file_write
5. 用中文回复，像贾维斯一样简洁高效""",
        model="deepseek-v4-flash",
        temperature=0.7,
        personality="precise",
    ),
}




class AgentProfileManager:
    """Manages agent profiles — load, switch, list.

    Scans profiles/ directory for AGENT.md files.
    Supports runtime profile switching via /agent command.

    Usage:
        mgr = AgentProfileManager()
        mgr.scan_profiles()           # Load all profiles
        mgr.switch("jarvis")          # Switch to Jarvis
        current = mgr.current         # Get current profile
        tools = mgr.filter_tools(all_tools)  # Filter tools for current profile
    """

    SEARCH_PATHS = [
        str(AGENTS_DIR),
        "./profiles",
        "~/.sclerotium/profiles",
    ]

    def __init__(self) -> None:
        self._profiles: dict[str, AgentProfile] = dict(BUILTIN_PROFILES)
        self._current_name = "sclerotium"

    # ── Scan & Load ────────────────────────────────────────────────────────

    def scan_profiles(self, extra_paths: list[str] | None = None) -> list[AgentProfile]:
        """Scan filesystem for AGENT.md profile files."""
        search_paths = list(self.SEARCH_PATHS)
        if extra_paths:
            search_paths.extend(extra_paths)

        loaded = []
        for search_path in search_paths:
            root = Path(search_path).expanduser().resolve()
            if not root.exists():
                continue

            for agent_md in root.rglob("AGENT.md"):
                try:
                    profile = self._load_profile(agent_md)
                    if profile.name not in self._profiles:
                        self._profiles[profile.name] = profile
                        loaded.append(profile)
                        logger.info("Loaded agent profile: %s", profile.name)
                except Exception as e:
                    logger.warning("Failed to load %s: %s", agent_md, e)

        return loaded

    def _load_profile(self, path: Path) -> AgentProfile:
        """Parse an AGENT.md file into an AgentProfile."""
        content = path.read_text(encoding="utf-8", errors="replace")

        # Parse YAML frontmatter
        name = path.parent.name
        description = ""
        system_prompt = content
        model = ""
        temperature = 0.7
        allowed_tools: tuple[str, ...] = ()
        blocked_tools: tuple[str, ...] = ()
        personality = "precise"
        extends = ""

        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                fm = content[3:end]
                system_prompt = content[end + 3:].strip()

                for line in fm.split("\n"):
                    line = line.strip()
                    if ":" not in line:
                        continue
                    key, _, val = line.partition(":")
                    key, val = key.strip(), val.strip().strip('"').strip("'")

                    if key == "name":
                        name = val
                    elif key == "description":
                        description = val
                    elif key == "model":
                        model = val
                    elif key == "temperature":
                        try: temperature = float(val)
                        except ValueError: pass
                    elif key == "tools" and val != "all":
                        allowed_tools = tuple(t.strip() for t in val.split(","))
                    elif key == "blocked_tools":
                        blocked_tools = tuple(t.strip() for t in val.split(","))
                    elif key == "personality":
                        personality = val
                    elif key == "extends":
                        extends = val

        return AgentProfile(
            name=name,
            description=description,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            allowed_tools=allowed_tools,
            blocked_tools=blocked_tools,
            personality=personality,
            extends=extends,
            source_path=str(path),
        )

    # ── Switch & Query ─────────────────────────────────────────────────────

    def switch(self, name: str) -> AgentProfile:
        """Switch to a different agent profile. Raises KeyError if not found."""
        if name not in self._profiles:
            available = ", ".join(sorted(self._profiles.keys()))
            raise KeyError(f"Unknown agent profile: {name}. Available: {available}")
        self._current_name = name
        logger.info("Switched to agent: %s", name)
        return self._profiles[name]

    @property
    def current(self) -> AgentProfile:
        """Get the currently active agent profile."""
        return self._profiles[self._current_name]

    @property
    def current_name(self) -> str:
        return self._current_name

    def get(self, name: str) -> AgentProfile | None:
        return self._profiles.get(name)

    def list_profiles(self) -> list[dict[str, Any]]:
        """List all available profiles."""
        return [
            {
                "name": p.name,
                "description": p.description,
                "personality": p.personality,
                "model": p.model or "default",
                "active": p.name == self._current_name,
                "builtin": p.name in BUILTIN_PROFILES,
            }
            for p in sorted(self._profiles.values(), key=lambda p: p.name)
        ]

    @property
    def profile_count(self) -> int:
        return len(self._profiles)

    # ── Tool Filtering ─────────────────────────────────────────────────────

    def filter_tools(self, all_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter tool list based on current profile's tool policy.

        If allowed_tools is empty, all tools are allowed (except blocked).
        If allowed_tools is set, only those tools are allowed.
        """
        profile = self.current

        if not profile.allowed_tools and not profile.blocked_tools:
            return all_tools

        filtered = []
        for tool in all_tools:
            name = tool.get("name", "")

            # Blocklist check
            if name in profile.blocked_tools:
                continue

            # Allowlist check (empty = all)
            if not profile.allowed_tools or name in profile.allowed_tools:
                filtered.append(tool)

        return filtered

    def filter_tool_names(self, tool_names: list[str]) -> list[str]:
        """Filter tool name list for current profile."""
        profile = self.current
        if not profile.allowed_tools and not profile.blocked_tools:
            return tool_names

        return [
            n for n in tool_names
            if n not in profile.blocked_tools
            and (not profile.allowed_tools or n in profile.allowed_tools)
        ]
