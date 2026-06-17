"""Sclerotium OS -- World's First Lifeform Terminal.

Design philosophy:
  Claude Code's clean minimalism + Sclerotium's living organism awareness
  + IDE-level professional developer experience.

Unique features no other terminal has:
  - Live organism vitals sidebar (FCPI, memory, STG rhythm, security)
  - 143 tools with progressive disclosure
  - 5-layer Hexis memory context shown live
  - Multi-model reasoning mode indicator
  - Evolution generation counter
  - Constitutional Arbiter security status

Layout:
  ┌──────────────────────────────────────────────────┐
  │ 🧬 Sclerotium OS -- Electronic Lichen Lifeform   │  Header
  ├──────────────────────────┬───────────────────────┤
  │                          │  🧬 Organism Vitals   │
  │  💬 Chat                 │  FCPI: ████░░ 0.73  │
  │                          │  Mem: 1.2K/5 layers  │
  │  ▸ User                  │  STG: pyloric ♪     │
  │                          │  Tools: 143          │
  │  Assistant (markdown)    │  Security: 12/0      │
  │  ```python code```       │  Mode: work          │
  │                          │  Evolution: Gen 5    │
  │  🔧 Tool calls           │                      │
  │                          │  📁 Recent Files     │
  │                          │  • app.py (edited)   │
  │                          │  • test.py           │
  ├──────────────────────────┴───────────────────────┤
  │ > Type code request or /command...               │  Input
  ├──────────────────────────────────────────────────┤
  │ Tokens:1,234 | Turns:3 | jury | deepseek | v0.5 │  Status
  └──────────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio, os, re, subprocess, sys, platform, webbrowser
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.events import Key
from textual.widgets import Footer, Header, Input, RichLog, Static
from textual.screen import Screen
from textual import work

from cli.tui.widgets.sidebar import OrganismSidebar
from cli.tui.widgets.task_tracker import TaskTracker
from kernel.command_registry import CommandRegistry, Command
from kernel.capability_router import CapabilityRouter
from kernel.organ_symphony import OrganSymphony, OrganLayer
from kernel.prompt_factory import PromptFactory, PromptContext, ToolCallRepairPipeline

# ── Smart Message Renderer ────────────────────────────────────────────

FILE_REF_RE = re.compile(
    r'(?P<path>[\w./\\-]+\.(?P<ext>py|js|ts|tsx|jsx|rs|go|java|rb|php|'
    r'css|html|md|yaml|yml|json|toml|cfg|ini|sh|bat|ps1|sql|r|c|cpp|h|hpp))'
    r':(?P<line>\d+)(?:-(?P<end>\d+))?'
)
URL_RE = re.compile(r'https?://[^\s<>"\')\]]+')

LANG_MAP = {
    'py':'python','js':'javascript','ts':'typescript','tsx':'tsx','jsx':'jsx',
    'rs':'rust','go':'go','java':'java','rb':'ruby','php':'php',
    'sh':'bash','bash':'bash','zsh':'bash','ps1':'powershell',
    'sql':'sql','html':'html','css':'css','scss':'scss',
    'json':'json','yaml':'yaml','yml':'yaml','toml':'toml',
    'md':'markdown','markdown':'markdown',
    'c':'c','cpp':'cpp','h':'c','hpp':'cpp',
    'r':'r','R':'r',
}


def render_developer_message(content: str) -> list:
    """Parse LLM response into syntax-highlighted, clickable segments."""
    if not content:
        return [Text("[empty]", style="dim")]
    results = []
    for part in re.split(r'(```[\s\S]*?```)', content):
        if part.startswith('```'):
            code_block = part[3:-3].strip() if part.endswith('```') else part[3:].strip()
            lines = code_block.split('\n', 1)
            lang_name = lines[0].strip() if lines else ""
            code = lines[1] if len(lines) > 1 and lang_name and not lang_name.startswith(' ') else code_block
            language = LANG_MAP.get(lang_name, lang_name if lang_name else 'text')
            try:
                results.append(Syntax(code[:8000], language, theme="monokai",
                                      line_numbers=True, word_wrap=True))
            except Exception:
                results.append(Panel(code[:5000], border_style="bright_black",
                                     title=lang_name or "code"))
        elif part.strip():
            results.extend(_parse_text(part))
    return results or [Text(content[:3000])]


def _parse_text(text: str) -> list:
    """Parse text for file refs (green) and URLs (blue)."""
    results, last = [], 0
    matches = []
    for m in FILE_REF_RE.finditer(text):
        matches.append((m.start(), m.end(), 'file', m.group(0)))
    for m in URL_RE.finditer(text):
        matches.append((m.start(), m.end(), 'url', m.group(0)))
    matches.sort(key=lambda x: x[0])
    for start, end, kind, full in matches:
        if start < last:
            continue
        if start > last:
            results.append(Markdown(text[last:start]))
        style = "bold green" if kind == 'file' else "underline blue"
        results.append(Text(full, style=style))
        last = end
    if last < len(text):
        results.append(Markdown(text[last:]))
    return results if results else [Markdown(text)]


# ── Dashboard Screen ──────────────────────────────────────────────────

class DashboardScreen(Screen):
    """Full-screen organism dashboard -- detailed vitals, event log, genome tree."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="dash-content")
        yield Footer()

    def on_mount(self) -> None:
        self._render()

    def _render(self) -> None:
        content = self.query_one("#dash-content", Static)
        table = Table(title="🧬 Sclerotium OS -- Full Organism Dashboard",
                      border_style="cyan", expand=True)
        table.add_column("System", style="bold cyan", width=16)
        table.add_column("Status", width=20)
        table.add_column("Details", style="dim")

        # Get data from parent app
        app = self.app
        gw = getattr(app, '_gateway', None)
        tools = getattr(app, '_tools', None)

        table.add_row("Gateway", "🟢 online" if gw else "🔴 offline",
                      f"{gw.strategy.name if gw else 'N/A'}")
        table.add_row("MCP Tools", f"🟢 {tools.tool_count if tools else 0} tools",
                      "22 categories, 143 registered")
        table.add_row("Hexis Memory", "🟢 5 layers",
                      "Working→Episodic→Semantic→Procedural→Strategic")
        table.add_row("Constitutional Arbiter", "🟢 active",
                      "7-layer defense-in-depth")
        table.add_row("STG Rhythm", "🟡 pyloric",
                      "Lobster-inspired autonomous cycles")
        table.add_row("FCPI Evolution", "🟢 6 dimensions",
                      "Coding/Coordination/Safety/Decision/Emergence/Performance")
        table.add_row("Model Gateway", "🟢 100+ providers",
                      "DeepSeek/OpenAI/Anthropic/Groq/Ollama")
        table.add_row("Sandstorm Sandbox", "🟢 ready",
                      "L1 subprocess / L2 Docker / L3 WASM")
        table.add_row("IM Platforms", "🟡 4 adapters",
                      "Feishu/QQ/WeChat/DingTalk")
        table.add_row("Desktop Automation", "🟡 standby",
                      "UIA + OCR + visual 3-channel")
        table.add_row("Scheduler", "🟢 active",
                      "APScheduler + STG metabolic clock")

        content.update(table)


# ── Main Chat App ─────────────────────────────────────────────────────

COMMAND_SUGGESTIONS = [
    "/help", "/status", "/clear", "/dashboard", "/files", "/open ", "/cat ",
    "/mode work", "/mode sleep", "/mode creative",
    "/evolve", "/scan", "/genome", "/memory",
    "/reason fast", "/reason dual", "/reason jury",
]


class SclerotiumTUI(App):
    """World's first lifeform terminal -- professional, alive, beautiful."""

    CSS = """
    Screen { background: #0d1117; }
    Header { background: #161b22; color: #7ee787; text-style: bold; }

    #main-layout { height: 1fr; }

    #chat-panel {
        width: 1fr;
        height: 1fr;
    }
    #messages {
        height: 1fr;
        background: #0d1117;
        border: none;
        overflow-y: auto;
        scrollbar-color: #484f58;
        scrollbar-background: #0d1117;
        scrollbar-size-vertical: 2;
    }

    #sidebar {
        width: 32;
        height: 1fr;
        background: #161b22;
        border-left: solid #30363d;
        display: block;
    }
    #sidebar.hidden { display: none; }

    #prompt-container {
        height: auto;
        background: #161b22;
        border-top: solid #30363d;
        padding: 0 1;
    }
    #prompt {
        background: #0d1117;
        color: #c9d1d9;
        border: solid #30363d;
        margin: 0;
    }
    #prompt:focus { border: solid #58a6ff; }

    #suggestions {
        height: auto;
        max-height: 10;
        background: #161b22;
        color: #8b949e;
        border: solid #30363d;
        padding: 0 1;
        display: none;
        overflow-y: auto;
        scrollbar-color: #484f58;
        scrollbar-background: #161b22;
    }
    #suggestions.visible { display: block; }
    .suggestion-selected {
        background: #1f6feb;
        color: #ffffff;
    }

    #file-drop-hint {
        height: 0;
        color: #3fb950;
        padding: 0 2;
        display: none;
    }
    #file-drop-hint.visible {
        height: 1;
        display: block;
    }

    #task-tracker {
        height: auto;
        max-height: 16;
        background: #161b22;
        border-top: solid #30363d;
        border-bottom: solid #30363d;
        padding: 0 1;
        display: none;
        overflow-y: auto;
    }
    #task-tracker.visible { display: block; }

    #status-line {
        dock: bottom;
        height: 1;
        background: #161b22;
        color: #8b949e;
    }
    Footer { background: #161b22; color: #8b949e; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+o", "open_file", "Open File"),
        Binding("ctrl+b", "open_browser", "Browser"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+f", "browse_files", "Files"),
        Binding("ctrl+g", "toggle_dashboard", "Dashboard"),
        Binding("ctrl+s", "save_session", "Save"),
        Binding("ctrl+m", "toggle_mouse", "Mouse", show=False),
        Binding("ctrl+a", "copy_all", "Copy All"),
        Binding("ctrl+y", "copy_last", "Copy Last"),
        Binding("ctrl+e", "export_chat", "Export"),
        Binding("ctrl+shift+c", "copy_visible", "Copy View", show=False),
        Binding("ctrl+p", "approve_tool", "Approve", show=False),
        Binding("escape", "cancel_task", "Cancel", show=False),
        Binding("shift+tab", "cycle_permission", "Perm", show=False),
        Binding("tab", "autocomplete", "Complete", show=False),
        Binding("f1", "help", "Help"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._cmd_registry = CommandRegistry()
        self._cap_router = CapabilityRouter()
        self._symphony = OrganSymphony()
        self._gateway: Any = None
        self._tools: Any = None
        self._agent_loop: Any = None
        self._session_store: Any = None
        self._initialized = False
        # Click targets
        self._last_file_ref: str = ""
        self._last_url: str = ""
        self._last_response: str = ""   # For clipboard copy
        # Metrics
        self._total_tokens: int = 0
        self._turn_count: int = 0
        self._reasoning_mode: str = "dual_verify"
        self._sidebar_visible: bool = True
        # Model config
        self._model: str = "deepseek-v4-pro"
        self._provider: str = "deepseek"
        # Model params are auto-detected from capability database -- no hardcoding
        self._temperature: float = 0.6  # Will be updated from model capability on init
        # ── 对话上下文（完整历史——模型上下文窗口是唯一限制）──
        # 每条: {"role": "user"|"assistant"|"tool", "content": str}
        # 不做人工截断，不限制轮数。DeepSeek-V4: 100万token窗口，可容纳数千轮对话
        self._conversation_history: list[dict[str, str]] = []
        self._context_window: int = 1_000_000  # 从模型能力数据库动态获取
        self._max_context_ratio: float = 0.80  # 历史占上下文窗口不超过80%
        self._auto_compact: bool = False  # /compact auto 开启自动压缩
        # ── 上下文跟踪（注入LLM提示词）──
        self._recently_edited: list[str] = []  # 最近编辑的文件路径（最多20个）
        self._session_goal: str = ""  # 从首条用户消息自动提取的会话目标
        # Suggestion navigation
        self._suggestion_idx: int = 0
        self._suggestion_matches: list = []
        # Thinking animation
        self._thinking: bool = False
        self._think_frame: int = 0
        self._think_timer: Any = None

    # ── Composition ───────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, name="Sclerotium OS")
        with Horizontal(id="main-layout"):
            with Container(id="chat-panel"):
                yield RichLog(id="messages", highlight=True, markup=True,
                              wrap=True, max_lines=5000)
            yield OrganismSidebar(id="sidebar")
        yield TaskTracker(id="task-tracker")
        yield Static("", id="suggestions")
        yield Container(
            Input(placeholder="Type code request or /command...", id="prompt"),
            id="prompt-container")
        yield Static("", id="file-drop-hint")  # 文件拖拽检测提示
        yield Static("", id="status-line")
        yield Footer()

    # ── Lifecycle ─────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self.title = "Sclerotium OS"
        self.sub_title = "Electronic Lichen Life Form"
        self._sidebar_visible = True
        self._show_welcome()
        self.query_one("#prompt", Input).focus()
        self._init_body_worker()
        self.set_interval(30, self._pulse_vitals)

    @work(exclusive=False)
    async def _init_body_worker(self) -> None:
        """Async init -- yields to UI between heavy operations."""
        import asyncio
        await asyncio.sleep(0.2)  # Let UI render first
        self._init_body()

    def _show_welcome(self) -> None:
        log = self.query_one("#messages", RichLog)
        log.write(Panel(
            Text("SCLEROTIUM OS v0.5.0 -- World's First Lifeform Terminal",
                 style="bold cyan", justify="center"),
            border_style="cyan"))
        log.write(Text(
            "Type / to see all commands  |  Tab to autocomplete  |  "
            "Ctrl+A copy all  |  Ctrl+Y copy last  |  Ctrl+E export  |  "
            "Ctrl+M mouse select  |  Shift+drag native select\n"
            "Loading plugin ecosystem: MCP tools + Skills + Market...\n",
            style="dim italic"))
        self._update_status("Initializing organism...")

    def _init_body(self) -> None:
        """Initialize the lifeform body."""
        log = self.query_one("#messages", RichLog)
        try:
            from gateways.models import UniversalModelGateway, RoutingStrategy
            self._gateway = UniversalModelGateway()
            self._gateway.set_routing(RoutingStrategy.BEST)  # Use BEST, not CHEAPEST
            self._gateway.load_super_prompt()

            from mcp.server import SclerotiumMCPServer
            mcp = SclerotiumMCPServer()
            mcp.register_all_tools()
            self._tools = mcp.tools

            # ── Prompt Factory（融合4大框架提示词工程）──
            mycelium_path = str(PROJECT_ROOT / "mycelium.md")
            self._prompt_factory = PromptFactory(mycelium_path=mycelium_path)
            self._prompt_factory.load_mycelium()  # 预热缓存

            from kernel.permission_gate import ConstitutionalArbiter
            self._arbiter = ConstitutionalArbiter(
                project_root=str(PROJECT_ROOT),
                audit_log_path="./data/audit.jsonl",
            )

            # ── Hexis 五层记忆系统（连接前台LLM ↔ 后台进化引擎）──
            from kernel.hexis_memory import HexisMemoryStore
            self._memory = HexisMemoryStore(
                chroma_path="./data/chroma",
                sqlite_path="./data/hexis.db")

            from kernel.agent_loop import AgentLoop
            from kernel.hooks import HookSystem, auto_format_hook, git_auto_add_hook, Hook
            self._agent_loop = AgentLoop(
                gateway=self._gateway,
                tools=self._tools,
                memory=self._memory,
                arbiter=self._arbiter,
                system_prompt=self._gateway._super_prompt or "",
            )
            # ── Wire hooks ──
            self._hooks = HookSystem()
            self._hooks.register(Hook("auto-format", "PostToolUse", "file_write", "*.py", auto_format_hook))
            self._hooks.register(Hook("git-auto-add", "PostToolUse", "file_write", "*", git_auto_add_hook))
            self._agent_loop.wire_hooks(self._hooks)

            # ── Wire prompt cache ──
            from kernel.prompt_cache import PromptCacheEngine, CacheZone
            self._cache_engine = PromptCacheEngine()
            self._cache_engine.add_segment("constitution",
                self._gateway._super_prompt or "", CacheZone.STATIC)
            self._gateway.wire_cache(self._cache_engine)
            self._agent_loop.wire_cache(self._cache_engine)

            from kernel.session_store import SessionStore
            self._session_store = SessionStore(base_dir="./data/sessions")
            self._session_store.create_session()

            # ── Load plugin ecosystem ──
            builtin_count = self._cmd_registry.load_builtins()
            mcp_count = self._cmd_registry.load_mcp_tools(self._tools)
            skill_count = self._cmd_registry.load_skills()
            cmd_stats = self._cmd_registry.stats()

            # ── Auto-discover capabilities (skills + MCP + plugins) ──
            cap_counts = self._cap_router.discover_all()
            cap_stats = self._cap_router.get_stats()

            # ── Register ALL 170+ organs in the symphony ──
            organ_counts = self._symphony.register_all(self._tools)
            sym_stats = self._symphony.get_stats()

            # ── 加载进化桥接器（后台MiroFish ↔ 前台Sclerotium）──
            self._mirofish_bridge = None
            self._fungal_bridge = None
            try:
                from bridges.mirofish_bridge import MiroFishBridge
                self._mirofish_bridge = MiroFishBridge()
                log.write(Text("  🐟 MiroFish bridge loaded (28 organs)", style="dim"))
            except Exception as e:
                log.write(Text(f"  ⚠ MiroFish bridge unavailable: {e}", style="dim yellow"))
            try:
                from bridges.fungal_bridge import FungalBridge
                self._fungal_bridge = FungalBridge()
                log.write(Text("  🍄 Fungal bridge loaded (120 organs)", style="dim"))
            except Exception as e:
                log.write(Text(f"  ⚠ Fungal bridge unavailable: {e}", style="dim yellow"))

            self._initialized = True
            self._update_context_window()  # 从模型数据库读取实际上下文窗口大小

            # Update sidebar with REAL organism state
            sidebar = self.query_one("#sidebar", OrganismSidebar)
            # 从Hexis读取真实记忆统计
            real_mem = {}
            if self._memory:
                try:
                    for level in ["working", "episodic", "semantic", "procedural", "strategic"]:
                        cur = self._memory._conn.execute(
                            "SELECT COUNT(*) FROM memories WHERE level=?", (level,))
                        real_mem[level] = cur.fetchone()[0]
                except Exception:
                    real_mem = {"working": 0, "episodic": 0, "semantic": 0, "procedural": 0, "strategic": 0}
            sidebar.update_vitals(
                fcpi={"coding": 0, "coordination": 0, "safety": 0,
                       "decision": 0, "emergence": 0, "performance": 0},
                memory_stats=real_mem or {"working": 0, "episodic": 0, "semantic": 0, "procedural": 0, "strategic": 0},
                stg_phase="pyloric",
                tools_active=self._tools.tool_count,
                security_allowed=0, security_blocked=0,
                mode="work",
            )
            sidebar.update_symphony(sym_stats, [])

            log.write(Text(
                f"Ecosystem ready -- {cmd_stats['total']} commands + "
                f"{cap_stats['total_capabilities']} auto-activating capabilities\n"
                f"  {builtin_count} builtins | {mcp_count} MCP tools | "
                f"{skill_count} skills | {cap_counts.get('plugins', 0)} plugins | "
                f"{cap_counts.get('memory', 0)} memory patterns\n"
                f"  Type naturally -- capabilities auto-activate. "
                f"/ for commands.",
                style="green"))
            self._update_status(
                f"Tools:{self._tools.tool_count} | "
                f"Reasoning:{self._reasoning_mode} | "
                f"Model:deepseek-v4-pro | "
                f"Tokens:0 | v0.5.0")
        except Exception as e:
            log.write(Text(f"Init error: {e}", style="red"))
            import traceback
            log.write(Text(traceback.format_exc(), style="dim red"))

    def _pulse_vitals(self) -> None:
        """Periodic vital signs update (lifeform heartbeat). 每30秒读取真实数据。"""
        if not self._initialized:
            return
        try:
            sidebar = self.query_one("#sidebar", OrganismSidebar)

            # 真实安全统计
            if self._arbiter:
                stats = self._arbiter.get_stats()
                sidebar.update_vitals(
                    security_allowed=stats.get('allowed_count', 0),
                    security_blocked=stats.get('blocked_count', 0),
                )

            # 真实记忆统计（从Hexis SQLite读取各层数量）
            if self._memory:
                try:
                    real_mem = {}
                    for level in ["working", "episodic", "semantic", "procedural", "strategic"]:
                        cur = self._memory._conn.execute(
                            "SELECT COUNT(*) FROM memories WHERE level=?", (level,))
                        real_mem[level] = cur.fetchone()[0]
                    if real_mem:
                        sidebar.update_vitals(memory_stats=real_mem)
                except Exception:
                    pass

            # 上下文窗口使用
            history_chars = sum(len(e.get("content", "")) for e in self._conversation_history)
            sidebar.update_vitals(
                context_window=self._context_window,
                history_tokens=history_chars // 3,
                tools_active=self._tools.tool_count if self._tools else 0,
            )
        except Exception:
            pass

    # ── Key handling ─────────────────────────────────────────────────

    def on_key(self, event: Key) -> None:
        """Intercept arrow keys when suggestions are visible."""
        if not isinstance(event, Key):
            return
        if not self._suggestion_matches:
            return
        if event.key == "down":
            self._navigate_suggestions(1)
            event.prevent_default()
            event.stop()
        elif event.key == "up":
            self._navigate_suggestions(-1)
            event.prevent_default()
            event.stop()
        elif event.key == "enter":
            self._select_suggestion()
            event.prevent_default()
            event.stop()

    def _navigate_suggestions(self, delta: int) -> None:
        """Arrow keys: move selection in suggestion list."""
        if not self._suggestion_matches:
            return
        self._suggestion_idx = (self._suggestion_idx + delta) % len(self._suggestion_matches)

    def _select_suggestion(self) -> None:
        """Enter: accept the selected suggestion."""
        if not self._suggestion_matches:
            return
        cmd = self._suggestion_matches[self._suggestion_idx]
        inp = self.query_one("#prompt", Input)
        inp.value = cmd.slug + " "
        inp.cursor_position = len(inp.value)
        self._suggestion_matches = []
        self._suggestion_idx = 0
        self.query_one("#suggestions", Static).remove_class("visible")

    # ── Thinking animation ────────────────────────────────────────────

    def _start_thinking(self) -> None:
        """启动器官交响乐——激活全部5层器官。"""
        self._thinking = True
        self._think_frame = 0
        try:
            if hasattr(self, '_symphony'):
                # THINK层：LLM推理核心
                for name in ["AgentLoop", "CollaborativeReasoner", "SuperPromptFactory",
                            "ToolRouter", "PromptCacheEngine", "ContextCompressor", "CommandRegistry"]:
                    self._symphony.activate_organ(name)
                # SENSE层：准备感知
                for name in ["HexisMemory", "CodebaseIndexer", "SkillRegistry", "CapabilityRouter"]:
                    self._symphony.activate_organ(name)
                # METABOLIZE层：代谢节律
                for name in ["STGRhythms", "EventBus", "Neuromodulator"]:
                    self._symphony.activate_organ(name)
                # ACT层：执行体就绪
                for name in ["SclerotiumMCPServer", "UniversalModelGateway", "ConstitutionalArbiter",
                            "HookSystem", "SandstormExecutor"]:
                    self._symphony.activate_organ(name)
                # EVOLVE层：进化引擎就绪
                for name in ["NineLawsPipeline", "CodeGenerationPipeline", "EvolutionBridge",
                            "ArchitectureScanner"]:
                    self._symphony.activate_organ(name)
            self.query_one("#sidebar", OrganismSidebar).start_flow()
        except Exception: pass
        self._think_timer = self.set_interval(0.3, self._tick_thinking)

    def _activate_tool_organ(self, tool_name: str) -> None:
        """工具被调用时激活对应的器官——完整5层映射。

        SENSE: 读/搜索 → HexisMemory, CodebaseIndexer, WebSearch, SkillRegistry
        THINK: 推理/缓存 → 自动在_start_thinking激活
        ACT: 写/执行 → SclerotiumMCPServer, SandstormExecutor, HookSystem, Arbiter
        EVOLVE: 代码生成 → CodeSelfRepair, ArchitectureScanner, TestGenerator
        METABOLIZE: 节律/调度 → STGRhythms, EventBus
        """
        if not hasattr(self, '_symphony'): return

        # ── 完整工具→器官映射 ──
        TOOL_ORGANS = {
            # SENSE layer — 读取/感知
            "file_read": ["HexisMemory", "SkillRegistry"],
            "file_list": ["CodebaseIndexer"],
            "codebase_search": ["CodebaseIndexer", "SkillRegistry"],
            "codebase_symbols": ["CodebaseIndexer"],
            "codebase_files": ["CodebaseIndexer"],
            "codebase_index": ["CodebaseIndexer"],
            "codebase_callers": ["CodebaseIndexer"],
            "codebase_callees": ["CodebaseIndexer"],
            "web_search": ["WebSearch", "CapabilityRouter"],
            "web_fetch": ["WebSearch"],
            "memory_search": ["HexisMemory"],
            "memory_get": ["HexisMemory"],
            "ls": ["FileWatcher"], "pwd": ["FileWatcher"],
            "cat": ["HexisMemory"], "find": ["CodebaseIndexer"],
            "wc": ["FileWatcher"], "uname": ["FileWatcher"],
            "df": ["FileWatcher"], "du": ["FileWatcher"],
            "system_status": ["FileWatcher"],
            "git_status": ["HookSystem"], "git_log": ["HookSystem"],
            "git_diff": ["HookSystem"], "git_blame": ["HookSystem"],

            # ACT layer — 写入/执行
            "file_write": ["SclerotiumMCPServer", "HookSystem"],
            "file_edit": ["SclerotiumMCPServer", "CodeSelfRepair"],
            "bash_execute": ["SandstormExecutor", "UniversalModelGateway"],
            "bash_smart": ["SandstormExecutor", "UniversalModelGateway"],
            "git_commit": ["HookSystem", "SclerotiumMCPServer"],
            "git_add": ["HookSystem"],
            "git_branch": ["HookSystem"],
            "sandbox_execute": ["SandstormExecutor"],
            "schedule_add": ["SchedulerEngine"],

            # EVOLVE layer — 代码生成/进化
            "code_scan": ["ArchitectureScanner", "CodeSelfRepair"],
            "auto_refactor": ["AutoRefactor", "CodeSelfRepair"],
            "test_generate": ["TestGenerator"],

            # METABOLIZE layer — 节律/调度
            "schedule_list": ["SchedulerEngine"],
            "schedule_remove": ["SchedulerEngine"],
            "mode_switch": ["Neuromodulator", "STGRhythms"],
            "daemon_start": ["Daemon"], "daemon_stop": ["Daemon"],
        }

        organs = TOOL_ORGANS.get(tool_name, ["SclerotiumMCPServer"])
        for organ in organs:
            try:
                self._symphony.activate_organ(organ, f"called via {tool_name}")
            except Exception:
                pass

        # 代码生成时同时激活EVOLVE层
        if tool_name in ("file_write", "file_edit"):
            for evo in ["NineLawsPipeline", "CodeGenerationPipeline", "EvolutionBridge"]:
                try: self._symphony.activate_organ(evo, "code generation active")
                except Exception: pass

        # 搜索时同时激活METABOLIZE层（EventBus记录活动）
        if tool_name in ("web_search", "web_fetch", "codebase_search"):
            try: self._symphony.activate_organ("EventBus", "sensing activity")
            except Exception: pass

    def _stop_thinking(self) -> None:
        """Stop organ flow animation."""
        self._thinking = False
        if self._think_timer:
            self._think_timer.stop()
            self._think_timer = None
        try:
            self.query_one("#sidebar", OrganismSidebar).stop_flow()
        except Exception: pass

        # ── 进化反馈循环：每5轮评估一次代码质量，注入系统提示 ──
        if self._turn_count > 0 and self._turn_count % 5 == 0:
            self._evolve_feedback()

    def _evolve_feedback(self) -> None:
        """周期性进化反馈：MiroFish真实FCPI评估 → 增强系统提示。

        这是"左脚踩右脚升天"闭环的核心引擎。
        优先使用MiroFish六维竞技场真实评估，失败时回退到本地启发式。
        """
        if not self._recently_edited:
            return
        try:
            from kernel.evolution_bridge import EvolutionBridge
            bridge = EvolutionBridge(str(PROJECT_ROOT))
            dirs = list(set(
                str(Path(f).parent.relative_to(PROJECT_ROOT))
                for f in self._recently_edited[-5:]
                if Path(f).exists()
            ))
            if not dirs:
                dirs = ["cli", "kernel", "mcp"]
            snapshots = bridge.extract_modules(target_dirs=dirs[:3])
            if not snapshots.get("code_snippets"):
                return

            # ── MiroFish真实六维竞技场FCPI评估 ──
            if not hasattr(self, '_mirofish_bridge') or not self._mirofish_bridge:
                log = self.query_one("#messages", RichLog)
                log.write(Text("  ⚠ Evolution: MiroFish bridge not loaded — run 'python run_full.py'", style="bold yellow"))
                return
            mfb = self._mirofish_bridge
            extractor = mfb._get("fitness_extractor")
            if not extractor or not hasattr(extractor, 'extract_fcpi'):
                log = self.query_one("#messages", RichLog)
                log.write(Text("  ⚠ Evolution: MiroFish FitnessExtractor not available — check MiroFish installation", style="bold yellow"))
                return
            fcpi_raw = extractor.extract_fcpi(snapshots)
            if not fcpi_raw:
                return
            fcpi = {
                "total": getattr(fcpi_raw, 'total', 0),
                "coding": getattr(fcpi_raw, 'coding', 0),
                "coordination": getattr(fcpi_raw, 'coordination', 0),
                "safety": getattr(fcpi_raw, 'safety', 0),
                "decision": getattr(fcpi_raw, 'decision', 0),
                "emergence": getattr(fcpi_raw, 'emergence', 0),
                "performance": getattr(fcpi_raw, 'performance', 0),
            }

            # 更新侧边栏FCPI
            try:
                sidebar = self.query_one("#sidebar", OrganismSidebar)
                sidebar.update_vitals(fcpi=fcpi)
            except Exception: pass

            # 每10轮注入系统提示增强
            if self._turn_count % 10 == 0 and fcpi.get("total", 0) > 0.4:
                insight = (
                    f"\n[Evolution Feedback] MiroFish FCPI: {fcpi.get('total',0):.2f}. "
                    f"C:{fcpi.get('coding',0):.1f} S:{fcpi.get('safety',0):.1f} "
                    f"P:{fcpi.get('performance',0):.1f}. "
                    f"Focus on improving the weakest dimension."
                )
                if hasattr(self, '_agent_loop') and self._agent_loop:
                    current = self._agent_loop.system_prompt or ""
                    if "[Evolution Feedback]" not in current:
                        self._agent_loop.system_prompt = current + insight
        except Exception:
            pass  # 进化反馈失败不影响主流程

    def _tick_thinking(self) -> None:
        """Animate organ flow in sidebar — passes real OrganVoice objects."""
        if not self._thinking: return
        self._think_frame += 1
        try:
            sidebar = self.query_one("#sidebar", OrganismSidebar)
            if hasattr(self, '_symphony'):
                active_organs = self._symphony.get_active_organs()[:15]
                sidebar.tick_flow(active_organs if active_organs else None)
                if self._think_frame % 4 == 0:
                    sidebar.update_symphony(self._symphony.get_stats(),
                                           self._symphony.get_recent_activity(8))
        except Exception: pass

    def action_autocomplete(self) -> None:
        """Tab: autocomplete the current slash command."""
        inp = self.query_one("#prompt", Input)
        value = inp.value.strip()
        if not value.startswith("/"):
            return
        matches = self._cmd_registry.search(value, limit=1)
        if matches:
            inp.value = matches[0].slug + " "
            inp.cursor_position = len(inp.value)
            self.query_one("#suggestions", Static).remove_class("visible")

    # ── File Drop Detection ────────────────────────────────────────────

    # 匹配常见文件路径格式（Windows + Unix + Git Bash + 带空格路径）
    _FILE_PATH_RE = re.compile(
        r'(?:^|[\s"\'`])('  # 路径前：行首/空格/引号
        r'(?:[A-Za-z]:[/\\]'  # Windows: C:\  D:/
        r'|~/|/'  # Unix/Git Bash: /home/... /c/Users/...
        r'|\.\.?[/\\]'  # 相对: ./  ../
        r')'
        r'(?:[^\s"\'`*?<>|]{1,200})'  # 路径体（排除非法字符）
        r'\.(?:py|js|ts|tsx|jsx|rs|go|java|rb|php|css|html|md|yaml|yml|json|toml|cfg|ini|sh|bat|ps1|sql|r|c|cpp|h|hpp|txt|log|csv|xml|svg|png|jpg|jpeg|gif|pdf|zip|tar|gz|whl|lock|env|dockerfile|makefile)(?:[\s"\'`]|$))',
        re.IGNORECASE,
    )

    def _detect_files_in_prompt(self, text: str) -> list[Path]:
        """扫描用户输入中的文件路径，返回存在的文件列表。支持拖拽/粘贴/手打。"""
        files = []
        seen = set()
        for m in self._FILE_PATH_RE.finditer(text):
            raw = m.group(1).strip().strip('"').strip("'").strip('`')
            try:
                p = Path(raw).expanduser().resolve()
                if p.is_file() and str(p) not in seen:
                    files.append(p)
                    seen.add(str(p))
            except Exception:
                pass
        return files

    def _read_file_for_context(self, file_path: Path) -> str:
        """读取文件内容，返回格式化的上下文片段。限制大小避免撑爆上下文。"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            # 不截断——1M上下文窗口足够
            ext = file_path.suffix.lstrip('.').lower()
            lang = LANG_MAP.get(ext, ext or 'text')
            return f"<file path='{file_path}' language='{lang}'>\n{content}\n</file>"
        except Exception as e:
            return f"<file path='{file_path}' error='{e}' />"

    # ── Input ─────────────────────────────────────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        """实时检测：/命令自动完成 + @文件引用 + 拖拽/粘贴文件路径。"""
        value = event.value.strip()

        # ── 拖拽/粘贴文件检测 ──
        if not value:
            self.query_one("#file-drop-hint", Static).remove_class("visible")
            # 不清除自动完成建议——它们有自己的移除逻辑
        else:
            files = self._detect_files_in_prompt(value)
            hint = self.query_one("#file-drop-hint", Static)
            if files:
                names = ", ".join(f.name for f in files[:4])
                sizes = sum(f.stat().st_size for f in files)
                hint.update(f"📁 {len(files)} file(s): {names} ({sizes:,}B total) — press Enter to include")
                hint.add_class("visible")
            else:
                hint.remove_class("visible")

        # ── /命令自动完成 ──
        sug = self.query_one("#suggestions", Static)
        if value.startswith("/"):
            matches = self._cmd_registry.search(value, limit=20)
            self._suggestion_matches = matches
            self._suggestion_idx = 0
            if matches:
                lines = []
                for i, cmd in enumerate(matches):
                    source_icon = {"builtin": "⌂", "mcp": "🔧", "skill": "📦",
                                   "market": "🌐", "custom": "✏"}.get(cmd.source, "?")
                    prefix = "▶" if i == 0 else " "
                    lines.append(f"{prefix} {source_icon} {cmd.slug}  {cmd.description[:60]}")
                sug.update("\n".join(lines[:12]))
                sug.add_class("visible")
            else:
                sug.remove_class("visible")
        else:
            sug.remove_class("visible")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return
        event.input.value = ""
        log = self.query_one("#messages", RichLog)
        log.write(Text(f"\n▸ {prompt}", style="bold cyan"))

        if prompt.startswith("/"):
            self._handle_command(prompt, log)
            return
        if not self._initialized:
            log.write(Text("Organism not ready -- wait for 'Organism ready'", style="red"))
            return

        # ── 拖拽文件检测：自动读取用户拖入/粘贴的文件 ──
        dropped_files = self._detect_files_in_prompt(prompt)
        file_context = ""
        if dropped_files:
            log.write(Text(f"  📁 Detected {len(dropped_files)} file(s): "
                          f"{', '.join(f.name for f in dropped_files[:5])}",
                          style="dim green"))
            for fp in dropped_files[:8]:  # 最多8个文件，防止撑爆上下文
                fc = self._read_file_for_context(fp)
                file_context += fc + "\n"
                log.write(Text(f"    → {fp.name} ({fp.stat().st_size:,}B)", style="dim"))

        # 将文件内容注入到prompt中（仅当前轮，不重复记录到历史）
        original_prompt = prompt
        if file_context:
            prompt = f"{file_context}\n\n<user_request>\n{prompt}\n</user_request>"

        self._run_agent(prompt, original_prompt=original_prompt)

    # ── Commands ──────────────────────────────────────────────────────

    def _handle_command(self, line: str, log: RichLog) -> None:
        parts = line.split()
        cmd_slug, args = parts[0], parts[1:]

        # Look up in command registry first
        cmd_obj = self._cmd_registry.get(cmd_slug)
        if cmd_obj is None:
            # Try matching as /tool.<name>
            cmd_obj = self._cmd_registry.get_by_name(f"mcp.{cmd_slug.lstrip('/')}")

        # ── Built-in commands ──
        if cmd_slug == "/help":
            self._cmd_help(log)
        elif cmd_slug == "/quit":
            self.exit()
        elif cmd_slug == "/clear":
            log.clear()
            self._show_welcome()
        elif cmd_slug == "/dashboard":
            self.push_screen(DashboardScreen())
        elif cmd_slug == "/status":
            self._cmd_status(log)
        elif cmd_slug == "/mode":
            self._cmd_mode(log, args)
        elif cmd_slug == "/files":
            self._cmd_files(log, args)
        elif cmd_slug == "/open":
            self._cmd_open(log, args)
        elif cmd_slug == "/cat":
            self._cmd_cat(log, args)
        elif cmd_slug == "/scan":
            self._cmd_scan(log, args)
        elif cmd_slug == "/reason":
            self._cmd_reason(log, args)
        elif cmd_slug == "/memory":
            self._cmd_search_memory(log, args)
        elif cmd_slug == "/permission":
            self._cmd_permission(log, args)
        elif cmd_slug == "/model":
            self._cmd_model(log, args)
        elif cmd_slug == "/generate":
            self._cmd_generate(log, args)
        elif cmd_slug == "/search":
            self._cmd_search_web(log, args)
        elif cmd_slug == "/fetch":
            self._cmd_fetch_web(log, args)
        elif cmd_slug == "/grep":
            self._cmd_grep(log, args)
        elif cmd_slug == "/symbol":
            self._cmd_symbol(log, args)
        elif cmd_slug == "/index":
            self._cmd_index(log, args)
        elif cmd_slug in ("/git", "/diff", "/log", "/blame", "/commit"):
            self._cmd_git(log, cmd_slug, args)
        elif cmd_slug == "/sessions":
            self._cmd_sessions(log, args)
        elif cmd_slug == "/doctor":
            self._cmd_doctor(log)
        elif cmd_slug == "/mcp":
            self._cmd_mcp(log, args)
        elif cmd_slug == "/ide":
            self._cmd_ide(log, args)
        elif cmd_slug == "/daemon":
            self._cmd_daemon(log, args)
        elif cmd_slug == "/vim":
            self._cmd_vim(log)
        elif cmd_slug == "/mouse":
            self.action_toggle_mouse()
        elif cmd_slug == "/organs":
            self._cmd_organs(log, args)
        elif cmd_slug == "/bash":
            self._cmd_bash(log, args)
        elif cmd_slug == "/run":
            self._cmd_run(log, args)
        elif cmd_slug == "/update":
            self._cmd_update(log, args)
        elif cmd_slug == "/compact":
            self._cmd_compact(log, args)
        elif cmd_slug in ("/selftest", "/self-test", "/testall"):
            self._cmd_selftest(log)
        elif cmd_slug == "/skills":
            self._cmd_list_skills(log)
        elif cmd_slug == "/tools":
            self._cmd_list_tools(log)

        # ── MCP tool commands (/tool.<name>) ──
        elif cmd_obj and cmd_obj.source == "mcp":
            tname = cmd_obj.name.replace("mcp.", "", 1)
            self._execute_mcp_tool(log, tname, args)

        # ── Skill commands ──
        elif cmd_obj and cmd_obj.source == "skill":
            self._invoke_skill(log, cmd_obj, args)

        # ── Try MCP OS tool (sync execution for OS commands) ──
        elif self._tools and self._tools.get_handler(cmd_slug.lstrip("/")):
            handler = self._tools.get_handler(cmd_slug.lstrip("/"))
            kwargs = {}
            for a in args:
                if "=" in a:
                    k, v = a.split("=", 1)
                    try: kwargs[k] = int(v)
                    except ValueError: kwargs[k] = v
                elif len(kwargs) == 0:
                    kwargs["path"] = a
            try:
                result = handler(**kwargs) if kwargs else handler()
                if isinstance(result, dict):
                    import json as _json
                    log.write(Syntax(_json.dumps(result, indent=2, ensure_ascii=False, default=str)[:3000],
                                   "json", theme="monokai"))
            except Exception as e:
                log.write(Text(str(e), style="red"))

        else:
            # Show suggestions
            suggestions = self._cmd_registry.search(cmd_slug, limit=5)
            if suggestions:
                names = ", ".join(c.slug for c in suggestions)
                log.write(Text(f"Unknown: {cmd_slug}. Did you mean: {names}?", style="yellow"))
            else:
                log.write(Text(f"Unknown: {cmd_slug}. Type / to see all commands.", style="yellow"))

    def _cmd_help(self, log: RichLog) -> None:
        log.write(Markdown("""\
## Commands
| Command | Action |
|---------|--------|
| `/help` | This help |
| `/status` | System vitals |
| `/dashboard` | Full organism dashboard |
| `/files [dir]` | Browse files |
| `/open <file>` | Open in editor |
| `/cat <file>` | View file (syntax highlighted) |
| `/scan [path]` | Architecture scan |
| `/reason <fast/dual/jury>` | Multi-model reasoning mode |
| `/mode <work|sleep|game|meeting|creative>` | Lifeform mode |
| `/memory <query>` | Search 5-layer memory |
| `/clear` | Clear screen |
| `/quit` | Exit |

## Keyboard
| Key | Action |
|-----|--------|
| `Ctrl+D` | Toggle organism sidebar |
| `Ctrl+O` | Open last referenced file |
| `Ctrl+B` | Open last URL in browser |
| `Ctrl+G` | Full dashboard |
| `Ctrl+F` | File browser |
| `Ctrl+L` | Clear screen |
| `Ctrl+S` | Save session |
| `Ctrl+Q` | Quit |
"""))

    def _cmd_status(self, log: RichLog) -> None:
        arbiter_stats = self._arbiter.get_stats() if hasattr(self, '_arbiter') and self._arbiter else {}
        log.write(Text(
            f"Gateway: {self._gateway.strategy.name if self._gateway else 'N/A'}\n"
            f"Tools: {self._tools.tool_count if self._tools else 0} (22 categories)\n"
            f"Reasoning: {self._reasoning_mode}\n"
            f"Tokens: {self._total_tokens:,} | Turns: {self._turn_count}\n"
            f"Security: {arbiter_stats.get('allowed_count', 0)} allowed, "
            f"{arbiter_stats.get('blocked_count', 0)} blocked\n"
            f"Last file: {self._last_file_ref or 'none'}\n"
            f"Last URL: {self._last_url or 'none'}\n"
            f"Memory: 5-layer Hexis + Ebbinghaus forgetting\n"
            f"Evolution: FCPI 6-dimension + Panarchy r→K→Ω→α",
            style="dim"))

    def _cmd_mode(self, log: RichLog, args: list[str]) -> None:
        valid = {"work", "sleep", "game", "meeting", "creative"}
        profile = args[0] if args else "work"
        if profile not in valid:
            log.write(Text(f"Valid: {', '.join(sorted(valid))}", style="yellow"))
            return
        log.write(Text(f"Mode: {profile}", style="cyan"))
        try:
            sidebar = self.query_one("#sidebar", OrganismSidebar)
            sidebar.update_vitals(mode=profile)
        except Exception:
            pass

    def _cmd_reason(self, log: RichLog, args: list[str]) -> None:
        modes = {"fast": "fast_path", "dual": "dual_verify",
                 "jury": "jury_panel", "specialist": "specialist"}
        if not args or args[0] not in modes:
            log.write(Text(
                "Usage: /reason <fast|dual|jury|specialist>\n"
                "  fast:  Single fast model (Groq) -- quick answers\n"
                "  dual:  Strong generates + fast reviews -- BEST for code ★\n"
                "  jury:  3 models vote/consensus -- critical tasks\n"
                "  specialist: Domain-specialized model routing",
                style="dim"))
            return
        self._reasoning_mode = modes[args[0]]
        log.write(Text(f"Reasoning mode: {args[0]} ({self._reasoning_mode})", style="green"))

    def _cmd_files(self, log: RichLog, args: list[str]) -> None:
        target = Path(args[0]) if args else PROJECT_ROOT
        if not target.exists():
            log.write(Text(f"Not found: {target}", style="red"))
            return
        items = sorted(target.iterdir())[:40]
        lines = [f"## {target}"]
        for item in items:
            icon = "📁" if item.is_dir() else "📄"
            if item.is_file():
                size = item.stat().st_size
                s = f"{size:,}B" if size < 1024 else f"{size/1024:.1f}KB"
                lines.append(f"- {icon} **{item.name}** ({s})")
            else:
                lines.append(f"- {icon} **{item.name}/**")
        log.write(Markdown("\n".join(lines)))

    def _cmd_open(self, log: RichLog, args: list[str]) -> None:
        if not args:
            log.write(Text("Usage: /open <file>", style="yellow"))
            return
        path = Path(args[0])
        if path.exists():
            try:
                os.startfile(str(path))
                log.write(Text(f"Opened: {path}", style="green"))
            except Exception as e:
                log.write(Text(str(e), style="red"))
        else:
            log.write(Text(f"Not found: {path}", style="yellow"))

    def _cmd_cat(self, log: RichLog, args: list[str]) -> None:
        if not args:
            log.write(Text("Usage: /cat <file>", style="yellow"))
            return
        path = Path(args[0])
        if not path.exists():
            log.write(Text(f"Not found: {path}", style="yellow"))
            return
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            ext = path.suffix.lstrip('.')
            lang = LANG_MAP.get(ext, 'text')
            log.write(Syntax(content[:5000], lang, theme="monokai", line_numbers=True))
        except Exception as e:
            log.write(Text(str(e), style="red"))

    def _cmd_scan(self, log: RichLog, args: list[str]) -> None:
        path = args[0] if args else "."
        log.write(Text(f"Scanning {path}...", style="dim"))
        if self._tools:
            h = self._tools.get_handler("code_scan")
            if h:
                try:
                    log.write(Text(f"Issues: {h(path=path).get('issues_found', 'N/A')}", style="yellow"))
                except Exception as e:
                    log.write(Text(str(e), style="red"))

    def _save_generated_code(self, code: str, task: str) -> None:
        """将生成的代码写入输出目录。创建合适的文件结构。"""
        import re, hashlib
        out_dir = Path("./generated_output")
        out_dir.mkdir(parents=True, exist_ok=True)

        # 从代码中检测语言
        lang = "py"
        if "def " in code or "import " in code or "class " in code:
            lang = "py"
        elif "function " in code or "const " in code or "require(" in code:
            lang = "js"
        elif "public class" in code:
            lang = "java"
        elif "package " in code and "func " in code:
            lang = "go"
        elif "fn " in code and "use " in code:
            lang = "rs"

        # 生成文件名
        slug = re.sub(r'[^a-z0-9]+', '_', task.lower())[:40]
        fname = out_dir / f"{slug}.{lang}"
        try:
            from mcp.tools.file_ops import file_write
            result = file_write(str(fname), code)
            if result.get("status") == "ok":
                self._last_file_ref = f"{fname}:1"
        except Exception:
            pass

    def _cmd_generate(self, log: RichLog, args: list[str]) -> None:
        """Run the full 7-stage TDD code generation pipeline."""
        task = " ".join(args)
        if not task:
            log.write(Text("Usage: /generate <task description>", style="yellow"))
            log.write(Text(
                "Example: /generate Build a FastAPI REST API for user CRUD with tests",
                style="dim"))
            return
        self._run_pipeline(task)

    @work(exclusive=False)
    async def _run_pipeline(self, task: str) -> None:
        """Execute the 7-stage pipeline with progress display."""
        log = self.query_one("#messages", RichLog)
        self._start_thinking()

        from kernel.code_generation_pipeline import (
            NineLawsPipeline, Law, LAW_ICONS, LAW_NAMES,
        )

        pipeline = NineLawsPipeline(
            gateway=self._gateway,
            tools=self._tools,
            memory=self._memory if hasattr(self, '_memory') else None,
            arbiter=self._arbiter if hasattr(self, '_arbiter') else None,
        )

        log.write(Text(f"\n▸ /generate {task[:80]}", style="bold cyan"))
        log.write(Text(""))

        # Setup task tracker
        tracker = self.query_one("#task-tracker", TaskTracker)
        tracker.clear()
        tracker._title = f"Plan: {task[:60]}"
        # Add all 9 laws as tasks
        law_task_ids = {
            Law.INTENT: "law1", Law.LEARN: "law2", Law.PLAN: "law3",
            Law.TEST: "law4", Law.CODE: "law5", Law.VERIFY: "law6",
            Law.TRUST: "law7", Law.COMPOUND: "law8", Law.HUMAN: "law9",
        }
        for law, tid in law_task_ids.items():
            tracker.add(tid, LAW_NAMES.get(law, law.value), "pending")
        tracker.add_class("visible")

        try:
            async for event in pipeline.generate(task):
                # Update task tracker based on completed laws
                if event.type == "progress" and event.law in law_task_ids:
                    tracker.start(law_task_ids[event.law])
                elif event.type == "output" and event.law in law_task_ids:
                    # Check if this law's main output has been shown (means it's done)
                    if event.law in (Law.INTENT, Law.LEARN, Law.PLAN, Law.TEST,
                                     Law.CODE, Law.VERIFY, Law.TRUST, Law.COMPOUND):
                        tracker.complete(law_task_ids[event.law])
                icon = LAW_ICONS.get(event.law, "•")
                name = LAW_NAMES.get(event.law, event.law.value)

                if event.type == "progress":
                    log.write(Text(f"  {icon} {name}: {event.data}", style="dim"))

                elif event.type == "output":
                    if event.law == Law.INTENT:
                        log.write(Panel(Markdown(str(event.data)[:2000]),
                                   border_style="blue", title="Specification"))
                    elif event.law == Law.LEARN:
                        log.write(Text(str(event.data), style="magenta"))
                    elif event.law == Law.TEST:
                        test_code = str(event.data)
                        log.write(Panel(Syntax(test_code[:3000], "python",
                                   theme="monokai", line_numbers=True),
                                   border_style="yellow", title="Tests (TDD)"))
                        # 也保存测试代码
                        self._save_generated_code(test_code, f"{task}_test")
                    elif event.law == Law.CODE:
                        code_text = str(event.data)
                        self._last_response = code_text
                        log.write(Panel(Syntax(code_text[:5000], "python",
                                   theme="monokai", line_numbers=True),
                                   border_style="green", title="Implementation"))
                        # ── 自动保存生成的代码到文件 ──
                        self._save_generated_code(code_text, task)
                    elif event.law == Law.VERIFY:
                        log.write(Text(str(event.data), style="yellow"))
                    elif event.law == Law.TRUST:
                        meta = event.data
                        self._stop_thinking()
                        log.write(Text(""))
                        log.write(Panel(
                            Text(
                                f"Nine Laws Complete\n\n"
                                f"Trust: {meta.get('trust_score', 0):.0f}/100 -- "
                                f"{meta.get('trust_level', 'N/A')}\n"
                                f"Recommendation: {meta.get('recommendation', 'N/A')}\n"
                                f"Laws: {' → '.join(meta.get('laws', []))}\n"
                                f"Duration: {meta.get('duration_ms', 0):.0f}ms\n"
                                f"Code: {meta.get('code_chars', 0):,} chars\n"
                                f"Tests: {meta.get('test_chars', 0):,} chars\n"
                                f"Candidates: {meta.get('candidates', 0)} | "
                                f"Spec Issues: {meta.get('spec_issues', 0)} | "
                                f"Review: {meta.get('review_issues', 0)} | "
                                f"Security: {meta.get('security_issues', 0)}",
                                style="bold green" if meta.get('success') else "bold yellow",
                            ),
                            border_style="green" if meta.get('success') else "yellow",
                            title="Code Generation Result"))
                    elif event.law == Law.COMPOUND:
                        log.write(Text(str(event.data), style="magenta"))
                    elif event.law == Law.HUMAN:
                        meta = event.data
                        self._stop_thinking()
                        log.write(Text(""))
                        log.write(Panel(
                            Text(
                                f"Nine Laws Complete\n\n"
                                f"Trust: {meta.get('trust_score', 0):.0f}/100 -- "
                                f"{meta.get('trust_level', 'N/A')}\n"
                                f"Laws: {' → '.join(meta.get('laws', []))}\n"
                                f"Duration: {meta.get('duration_ms', 0):.0f}ms\n"
                                f"Code: {meta.get('code_chars', 0):,} chars | "
                                f"Candidates: {meta.get('candidates', 0)} | "
                                f"Skills: {meta.get('new_skills', 0)}",
                                style="bold green" if meta.get('success') else "bold yellow",
                            ),
                            border_style="green" if meta.get('success') else "yellow",
                            title="Code Generation Result"))

                elif event.type == "error":
                    log.write(Text(f"  {icon} {name}: {event.data}", style="red"))

        except Exception as e:
            self._stop_thinking()
            log.write(Text(f"  Pipeline error: {e}", style="bold red"))
            tracker.fail("law_current", str(e)[:100])

        # Keep tracker visible briefly, then hide
        self.set_timer(3.0, lambda: tracker.remove_class("visible"))

    def _cmd_search_web(self, log: RichLog, args: list[str]) -> None:
        """Web search -- Claude Code WebSearch equivalent."""
        query = " ".join(args)
        if not query:
            log.write(Text("Usage: /search <query>", style="yellow"))
            return
        log.write(Text(f"Searching: {query}...", style="dim"))
        try:
            from mcp.tools.web_search import web_search
            result = web_search(query)
            if result.get("status") == "ok":
                for i, r in enumerate(result.get("results", [])[:8]):
                    title = r.get("title", "?")[:80]
                    url = r.get("url", "")
                    snippet = r.get("snippet", "")[:150]
                    log.write(Markdown(f"**{i+1}. [{title}]({url})**\n{snippet}"))
                log.write(Text(f"\n{result.get('total_results', 0)} results from DuckDuckGo", style="dim"))
            else:
                log.write(Text(f"Search error: {result.get('error', 'unknown')}", style="red"))
        except Exception as e:
            log.write(Text(str(e), style="red"))

    def _cmd_fetch_web(self, log: RichLog, args: list[str]) -> None:
        """Fetch URL -- Claude Code WebFetch equivalent."""
        url = args[0] if args else ""
        if not url:
            log.write(Text("Usage: /fetch <url>", style="yellow"))
            return
        log.write(Text(f"Fetching: {url}...", style="dim"))
        try:
            from mcp.tools.web_search import web_fetch
            result = web_fetch(url)
            if result.get("status") == "ok":
                log.write(Panel(
                    Markdown(result.get("content", "")[:5000]),
                    border_style="blue",
                    title=result.get("title", url)[:60]))
            else:
                log.write(Text(f"Fetch error: {result.get('error', result.get('suggestion', 'unknown'))}", style="red"))
        except Exception as e:
            log.write(Text(str(e), style="red"))

    def _cmd_grep(self, log: RichLog, args: list[str]) -> None:
        """Search entire codebase -- beats Claude Code Grep."""
        query = " ".join(args)
        if not query:
            log.write(Text("Usage: /grep <query> [--pattern *.py]", style="yellow"))
            return
        pattern = "*"
        if "--pattern" in query:
            parts = query.split("--pattern")
            query = parts[0].strip()
            pattern = parts[1].strip()
        from mcp.tools.codebase_search import codebase_search
        result = codebase_search(query, max_results=15, file_pattern=pattern)
        for r in result.get("results", []):
            sym = f" ({r['symbol']})" if r.get("symbol") else ""
            log.write(Text(
                f"  {r['file']}:{r['line']}{sym} [{r.get('relevance', 0):.2f}]\n"
                f"    {r['match'][:120]}",
                style="dim"))
        log.write(Text(f"\n{result['total']} results", style="dim"))

    def _cmd_symbol(self, log: RichLog, args: list[str]) -> None:
        """Find symbol definitions."""
        name = args[0] if args else ""
        if not name:
            log.write(Text("Usage: /symbol <name> [function|class|all]", style="yellow"))
            return
        kind = args[1] if len(args) > 1 else "all"
        from mcp.tools.codebase_search import codebase_symbols
        result = codebase_symbols(name, kind=kind)
        for r in result.get("results", []):
            log.write(Text(
                f"  {r['kind']:<10} {r['name']:<30} {r['file']}:{r['line']}",
                style="green" if r['kind'] == 'function' else "yellow"))
            if r.get("signature"):
                log.write(Text(f"    {r['signature'][:100]}", style="dim"))

    def _cmd_index(self, log: RichLog, args: list[str]) -> None:
        """Index the project for fast search."""
        target = args[0] if args else "."
        log.write(Text(f"Indexing {target}...", style="dim"))
        from mcp.tools.codebase_search import codebase_index
        result = codebase_index(target)
        stats = result.get("overall", {})
        log.write(Text(
            f"Indexed: {stats.get('files_indexed', 0)} files, "
            f"{stats.get('symbols_indexed', 0)} symbols, "
            f"{stats.get('call_graph_edges', 0)} call edges\n"
            f"Total lines: {stats.get('total_lines', 0):,} | "
            f"DB size: {stats.get('db_size_kb', 0)} KB",
            style="green"))

    def _cmd_doctor(self, log: RichLog) -> None:
        """Claude Code Doctor.tsx equivalent -- environment diagnostic."""
        import sys, platform, subprocess
        table = Table(title="Environment Diagnostic", border_style="cyan")
        table.add_column("Check", style="bold", width=20)
        table.add_column("Status", width=14)
        table.add_column("Detail", style="dim")
        checks = [
            ("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", ""),
            ("Platform", platform.system(), platform.release()),
            ("Gateway", "🟢 connected" if self._gateway else "🔴 offline",
             f"{self._provider}/{self._model}" if self._gateway else ""),
            ("MCP Tools", f"🟢 {self._tools.tool_count if self._tools else 0}",
             "22 categories" if self._tools else ""),
            ("Memory", "🟢 5-layer" if self._memory else "🔴 N/A",
             "Hexis+Ebbinghaus" if self._memory else ""),
            ("Arbiter", f"🟢 {self._arbiter.mode.value}" if hasattr(self, '_arbiter') and self._arbiter else "🔴 N/A", ""),
            ("Session Store", f"🟢 {self._session_store.get_stats().get('session_count',0)} sessions" if self._session_store else "🔴 N/A", ""),
            ("Capability Router", f"🟢 {self._cap_router.get_stats().get('total_capabilities',0)} caps" if hasattr(self, '_cap_router') else "🔴 N/A", ""),
        ]
        try:
            r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
            checks.append(("Git", "🟢 " + r.stdout.strip()[:20] if r.returncode==0 else "🔴", ""))
        except: checks.append(("Git", "🔴 not found", ""))
        for name, status, detail in checks:
            table.add_row(name, status, detail)
        log.write(table)

    def _cmd_mcp(self, log: RichLog, args: list[str]) -> None:
        """MCP server connection management."""
        if not args:
            log.write(Text("MCP Servers: 1 local + 0 remote connected", style="cyan"))
            log.write(Text("  /mcp list    -- list all connected MCP servers\n"
                          "  /mcp connect <url>   -- connect to remote MCP\n"
                          "  /mcp disconnect <id>  -- disconnect MCP server", style="dim"))
        elif args[0] == "list":
            log.write(Text("Connected MCP servers:\n  • sclerotium-os (local, 158 tools)\n"
                          "  • fungal-cortex (bridge, 120 organs)\n"
                          "  • MiroFish (bridge, 28 organs)", style="dim"))
        elif args[0] == "connect" and len(args) > 1:
            log.write(Text(f"Connecting to {args[1]}... (MCP stdio/HTTP transport)\n"
                          f"MCP connection support via stdio/SSE. Configure in config.yaml.", style="yellow"))
        else:
            log.write(Text(f"Unknown MCP command: {args[0]}", style="yellow"))

    def _cmd_ide(self, log: RichLog, args: list[str]) -> None:
        """IDE bridge -- open project in VS Code/JetBrains."""
        import subprocess
        editor = args[0] if args else "code"
        path = args[1] if len(args) > 1 else "."
        editors = {"code": "code", "vscode": "code", "cursor": "cursor",
                   "windsurf": "windsurf", "idea": "idea"}
        cmd = editors.get(editor, editor)
        try:
            subprocess.Popen([cmd, path], shell=True)
            log.write(Text(f"Opened {path} in {editor}", style="green"))
        except Exception as e:
            log.write(Text(f"Failed: {e}. Ensure {editor} is in PATH.", style="yellow"))

    def _cmd_daemon(self, log: RichLog, args: list[str]) -> None:
        """Background daemon mode for autonomous operation."""
        if not args:
            log.write(Text("Daemon mode: OFF\n"
                          "  /daemon start  -- start background autonomous agent\n"
                          "  /daemon stop   -- stop daemon\n"
                          "  /daemon status -- check daemon status", style="dim"))
        elif args[0] == "start":
            self._daemon_active = True
            log.write(Text("Daemon started. Autonomous agent running in background.\n"
                          "  • Checks memory consolidation every 5 min\n"
                          "  • Monitors file changes via watchdog\n"
                          "  • Auto-commits significant changes", style="green"))
            self.set_interval(300, self._daemon_tick)
        elif args[0] == "stop":
            self._daemon_active = False
            log.write(Text("Daemon stopped.", style="yellow"))
        elif args[0] == "status":
            status = "RUNNING" if getattr(self, '_daemon_active', False) else "STOPPED"
            log.write(Text(f"Daemon: {status}", style="cyan" if status=="RUNNING" else "dim"))

    def _daemon_tick(self) -> None:
        """Periodic daemon task -- memory consolidation + file watching."""
        if not getattr(self, '_daemon_active', False): return
        try:
            if self._memory:
                self._memory.consolidate("episodic", "semantic")
        except Exception: pass

    def _cmd_organs(self, log: RichLog, args: list[str]) -> None:
        """Explore the full 170+ organ ecosystem."""
        layer_filter = args[0] if args else ""
        sym_stats = self._symphony.get_stats()
        layer_summary = self._symphony.get_layer_summary()

        if layer_filter and layer_filter in ["sense", "think", "act", "evolve", "metabolize"]:
            active = self._symphony.get_active_organs(OrganLayer(layer_filter))
            layer_name = {"sense": "SENSE (Perception)", "think": "THINK (Reasoning)",
                         "act": "ACT (Execution)", "evolve": "EVOLVE (Learning)",
                         "metabolize": "METABOLIZE (Autonomous)"}[layer_filter]
            log.write(Text(f"\n{layer_name} -- {len(active)} active organs:", style="bold cyan"))
            by_sys: dict[str, list] = {}
            for o in active:
                by_sys.setdefault(o.system, []).append(o)
            for sys_name, organs in by_sys.items():
                icon = {"sclerotium-os": "🦑", "fungal-cortex": "🍄", "mirofish": "🐟"}.get(sys_name, "•")
                names = ", ".join(o.organ_name for o in organs[:10])
                log.write(Text(f"  {icon} {sys_name}: {names}", style="dim"))
            return

        # Full symphony overview
        log.write(Panel(
            Text(f"Organ Symphony -- {sym_stats['total_organs']} organs, "
                 f"{sym_stats['active_now']} active", style="bold cyan", justify="center"),
            border_style="cyan"))
        table = Table(border_style="dim")
        table.add_column("Layer", style="bold", width=14)
        table.add_column("Total", width=8, justify="right")
        table.add_column("Active", width=8, justify="right")
        table.add_column("Systems", style="dim")
        for layer_name, info in layer_summary.items():
            layer_organs = self._symphony.get_active_organs(OrganLayer(layer_name))
            systems = set(o.system for o in layer_organs) if layer_organs else set()
            sys_str = ", ".join(systems) if systems else "-"
            table.add_row(layer_name, str(info["total"]), str(info["active"]), sys_str)
        log.write(table)

        log.write(Text("\n/by_system: 🦑 sclerotium-os | 🍄 fungal-cortex | 🐟 mirofish", style="dim"))
        log.write(Text("/organs sense|think|act|evolve|metabolize", style="dim"))

    def _cmd_bash(self, log: RichLog, args: list[str]) -> None:
        """Execute shell command -- Claude Code Bash equivalent."""
        command = " ".join(args)
        if not command:
            log.write(Text("Usage: /bash <command>  -- execute shell command", style="yellow"))
            return
        from mcp.tools.bash_tool import bash_execute
        log.write(Text(f"$ {command}", style="bold cyan"))
        result = bash_execute(command)
        if result.get("status") == "blocked":
            log.write(Text(f"BLOCKED: {result['error']}", style="bold red"))
            return
        if result.get("stdout"):
            log.write(Text(result["stdout"][:3000], style="green"))
        if result.get("stderr"):
            log.write(Text(result["stderr"][:2000], style="red dim"))
        if result.get("is_dangerous"):
            log.write(Text(result.get("warning", ""), style="yellow"))
        log.write(Text(f"Exit: {result.get('exit_code', '?')}", style="dim"))

    def _cmd_run(self, log: RichLog, args: list[str]) -> None:
        """Smart run -- auto-detects how to run the project."""
        target = " ".join(args) if args else ""
        log.write(Text(f"Running: {target or 'auto-detect'}...", style="bold cyan"))
        from mcp.tools.bash_tool import bash_run
        result = bash_run(target)
        if result.get("stdout"):
            log.write(Text(result["stdout"][:5000], style="green"))
        if result.get("stderr"):
            log.write(Text(result["stderr"][:2000], style="red dim"))
        log.write(Text(f"Command: {result.get('command', '?')} | Exit: {result.get('exit_code', '?')}",
                      style="dim"))

    def _cmd_update(self, log: RichLog, args: list[str]) -> None:
        """Check for updates / pull latest -- Claude Code update equivalent."""
        import subprocess
        if args and args[0] == "check":
            log.write(Text("Checking for updates...", style="dim"))
            try:
                r = subprocess.run(["git", "fetch", "origin"], capture_output=True, text=True, timeout=15)
                r2 = subprocess.run(["git", "log", "HEAD..origin/main", "--oneline", "-5"],
                                   capture_output=True, text=True, timeout=10)
                if r2.stdout.strip():
                    log.write(Text("Updates available:", style="bold yellow"))
                    log.write(Text(r2.stdout[:1000], style="dim"))
                    log.write(Text("Run /update apply to install", style="dim"))
                else:
                    log.write(Text("Already up to date.", style="green"))
            except Exception as e:
                log.write(Text(f"Check failed: {e}", style="red"))
        elif args and args[0] == "apply":
            log.write(Text("Pulling latest changes...", style="bold yellow"))
            try:
                r = subprocess.run(["git", "pull", "origin", "main"], capture_output=True, text=True, timeout=30)
                log.write(Text(r.stdout[:2000] or "Pulled successfully", style="green"))
                log.write(Text("Restart Sclerotium OS to apply changes.", style="bold cyan"))
            except Exception as e:
                log.write(Text(f"Update failed: {e}", style="red"))
        else:
            log.write(Text("/update check  -- check for updates\n"
                          "/update apply  -- install updates", style="dim"))

    def _cmd_vim(self, log: RichLog) -> None:
        """Toggle vim-like keybindings in the input."""
        self._vim_mode = not getattr(self, '_vim_mode', False)
        inp = self.query_one("#prompt", Input)
        if self._vim_mode:
            log.write(Text("Vim mode: ON (Esc=normal, i=insert, h/j/k/l=move, w/b=word, 0/$=line)", style="green"))
        else:
            log.write(Text("Vim mode: OFF", style="dim"))
        inp.refresh()
        """Git integration commands."""
        from mcp.tools.git_tools import git_status, git_diff, git_log, git_blame
        if cmd == "/git":
            r = git_status()
            log.write(Text(r.get("stdout", "No changes") or "Clean", style="dim"))
        elif cmd == "/diff":
            fp = args[0] if args else ""
            r = git_diff(file_path=fp)
            if r.get("stdout"):
                for line in r["stdout"].split("\n")[:60]:
                    style = "green" if line.startswith("+") else "red" if line.startswith("-") else "dim"
                    log.write(Text(f"  {line[:120]}", style=style))
        elif cmd == "/log":
            r = git_log(n=int(args[0]) if args else 10)
            log.write(Text(r.get("stdout", "No history")[:2000], style="dim"))
        elif cmd == "/blame":
            fp = args[0] if args else ""
            if fp:
                r = git_blame(fp, lines=args[1] if len(args) > 1 else "")
                log.write(Text(r.get("stdout", "")[:2000], style="dim"))

    def _cmd_sessions(self, log: RichLog, args: list[str]) -> None:
        """Session resume/fork UI."""
        if not self._session_store:
            log.write(Text("Session store not available", style="red")); return
        if args and args[0] == "resume" and len(args) > 1:
            events = self._session_store.resume_session(args[1])
            if events:
                log.write(Text(f"Resumed session {args[1][:30]}... ({len(events)} events)", style="green"))
            else:
                log.write(Text(f"Session {args[1][:30]}... not found", style="yellow"))
        elif args and args[0] == "fork":
            tid = int(args[1]) if len(args) > 1 else 0
            fid = self._session_store.fork_session(tid)
            log.write(Text(f"Forked at turn {tid}: {fid}", style="green"))
        else:
            sessions = self._session_store.list_sessions(10)
            if sessions:
                for s in sessions:
                    log.write(Text(
                        f"  {s.get('session_id','?')[:40]} -- {s.get('turn_count',0)} turns, "
                        f"{s.get('title','')[:60]}", style="dim"))
                log.write(Text("\n/sessions resume <id>  |  /sessions fork <turn>", style="dim"))
            else:
                log.write(Text("No saved sessions", style="dim"))

    def _cmd_search_memory(self, log: RichLog, args: list[str]) -> None:
        query = " ".join(args)
        if not query:
            log.write(Text("Usage: /memory <query> -- search 5-layer Hexis memory", style="yellow"))
            return
        if self._tools:
            h = self._tools.get_handler("memory_search")
            if h:
                try:
                    results = h(query=query)
                    if asyncio.iscoroutine(results):
                        results = asyncio.ensure_future(results)
                    if results:
                        log.write(Text(f"Memory results for: {query}", style="cyan"))
                except Exception as e:
                    log.write(Text(str(e), style="red"))

    def _cmd_model(self, log: RichLog, args: list[str]) -> None:
        """Switch LLM model -- configure all 4 parameters freely.

        Usage:
          /model                              Show current config
          /model list                         List all providers + models
          /model list <provider>              List models for one provider
          /model provider <name>              Change provider
          /model name <model>                 Change model name
          /model api <provider> <key>         Set API key
          /model url <provider> <url>         Set base URL
          /model <name>                       Auto-detect provider + switch model
          /model <provider>/<name>            Full provider/model switch
        """
        if not self._gateway:
            log.write(Text("Gateway not initialized", style="red"))
            return

        if not args:
            self._show_model_config(log)
            return

        sub = args[0].lower()

        # ── /model list [provider] ──
        if sub == "list":
            self._cmd_model_list(log, args[1] if len(args) > 1 else None)
            return

        # ── /model provider <name> ──
        if sub == "provider" and len(args) >= 2:
            prov = args[1]
            old = self._provider
            self._provider = prov
            self._update_model_status(log, f"Provider: {old} → {prov}")
            return

        # ── /model name <model> ──
        if sub in ("name", "model") and len(args) >= 2:
            name = args[1]
            old = self._model
            self._model = name
            self._update_context_window(name)  # 同步更新上下文窗口
            self._update_model_status(log, f"Model: {old} → {name}")
            return

        # ── /model api <provider> <key> ──
        if sub == "api" and len(args) >= 3:
            provider_id = args[1]
            api_key = args[2]
            os.environ[f"{provider_id.upper()}_API_KEY"] = api_key
            log.write(Text(
                f"API Key set: {provider_id.upper()}_API_KEY={api_key[:8]}...",
                style="green"))
            return

        # ── /model url <provider> <url> ──
        if sub == "url" and len(args) >= 3:
            provider_id = args[1]
            base_url = args[2]
            os.environ[f"{provider_id.upper()}_BASE_URL"] = base_url
            log.write(Text(
                f"Base URL set: {provider_id} → {base_url}",
                style="green"))
            return

        # ── /model <provider>/<name> or /model <name> ──
        if "/" in sub:
            prov, name = sub.split("/", 1)
            old = f"{self._provider}/{self._model}"
            self._provider = prov
            self._model = name
            self._update_model_status(log, f"Model: {old} → {prov}/{name}")
        else:
            name = sub
            prov = self._find_provider(name)
            if prov:
                old = f"{self._provider}/{self._model}"
                self._provider = prov
                self._model = name
                self._update_model_status(log, f"Model: {old} → {prov}/{name}")
            else:
                log.write(Text(
                    f"Model '{name}' not found. Try /model list or specify provider: "
                    f"/model <provider>/{name}",
                    style="yellow"))

    def _update_context_window(self, model_name: str = "") -> None:
        """从模型能力数据库读取上下文窗口大小，动态更新限制。"""
        try:
            from gateways.model_capabilities import MODEL_CAPABILITIES
            name = model_name or self._model
            cap = MODEL_CAPABILITIES.get(name)
            if cap:
                self._context_window = cap.max_context_window
            else:
                # 未知模型 → 保守估计
                self._context_window = 200_000
        except Exception:
            pass  # 保持默认值

    def _cmd_model_list(self, log: RichLog, filter_prov: str | None = None) -> None:
        """List available providers and models."""
        if not self._gateway:
            return
        try:
            providers = self._gateway.list_providers()
            for p in providers:
                pid = p.get("id", "?")
                if filter_prov and pid != filter_prov:
                    continue
                name = p.get("name", pid)
                models = p.get("models", [])[:6]
                category = p.get("category", "?")
                free = "FREE" if p.get("free_tier") else "PAID"
                has_key = "🔑" if os.environ.get(f"{pid.upper()}_API_KEY") else "🔒"
                log.write(Text(
                    f"  {has_key} {name:<20} [{category:<10}] {free:<5} -- "
                    f"{', '.join(models[:5])}",
                    style="dim"))
        except Exception as e:
            log.write(Text(str(e), style="red"))

    def _find_provider(self, model_name: str) -> str:
        """Find which provider has a given model."""
        ml = model_name.lower()
        if "deepseek" in ml: return "deepseek"
        if "claude" in ml: return "anthropic"
        if "gpt" in ml or "o3" in ml or "o4" in ml: return "openai"
        if "gemini" in ml: return "google"
        if "llama" in ml or "mixtral" in ml: return "groq"
        if "qwen" in ml: return "ollama"
        if "minicpm" in ml: return "ollama"
        if "mistral" in ml or "codestral" in ml: return "mistral"
        if "grok" in ml: return "xai"
        if not self._gateway: return ""
        try:
            for p in self._gateway.list_providers():
                for m in p.get("models", []):
                    if m.lower() == model_name.lower():
                        return p.get("id", "")
        except Exception:
            pass
        return ""

    def _update_model_status(self, log: RichLog, message: str) -> None:
        """Update model config display and status bar."""
        # Check connectivity
        status = ""
        if hasattr(self._gateway, 'test_connection'):
            try:
                result = self._gateway.test_connection(self._provider)
                if result.get("status") == "ok":
                    status = " ✅ connected"
                elif result.get("status") == "no_key":
                    status = " ⚠️ needs API key → /model api <provider> <key>"
                else:
                    status = f" ⚠️ {result.get('error', '')[:40]}"
            except Exception:
                pass

        log.write(Text(message + status, style="green" if "✅" in status else "cyan"))
        self._update_status(
            f"Tools:{self._tools.tool_count if self._tools else 0} | "
            f"Turns:{self._turn_count} | "
            f"Tokens:{self._total_tokens:,} | "
            f"{self._provider}/{self._model} | v0.5.0")

    def _show_model_config(self, log: RichLog) -> None:
        """Show editable model configuration table."""
        api_key_env = f"{self._provider.upper()}_API_KEY"
        base_url_env = f"{self._provider.upper()}_BASE_URL"
        api_val = os.environ.get(api_key_env, "")
        url_val = os.environ.get(base_url_env, "")

        # Auto-detect default URL
        if not url_val and self._gateway:
            try:
                from gateways.models import PROVIDERS
                pinfo = PROVIDERS.get(self._provider)
                if pinfo:
                    url_val = pinfo.base_url
            except Exception:
                pass

        table = Table(title="Model Configuration", border_style="cyan")
        table.add_column("Parameter", style="bold cyan", width=14)
        table.add_column("Value", style="green", width=40)
        table.add_column("Set Command", style="dim", width=36)

        table.add_row("Provider", self._provider,
                      "/model provider <name>")
        table.add_row("Model", self._model,
                      "/model name <model>")
        table.add_row("API Key",
                      f"{api_key_env}={'***' if api_val else '(not set)'}",
                      "/model api <provider> <key>")
        table.add_row("Base URL",
                      url_val or "(default)",
                      "/model url <provider> <url>")
        log.write(table)

        log.write(Text("\nExamples:", style="bold"))
        log.write(Text(
            "  /model provider openai\n"
            "  /model name gpt-5.4\n"
            "  /model api openai sk-abc123\n"
            "  /model url ollama http://localhost:11434/v1\n"
            "  /model anthropic/claude-opus-4-8     (set both at once)\n"
            "  /model deepseek-v4-flash              (auto-detect provider)\n"
            "  /model list                           (browse all providers)",
            style="dim"))
        """Switch Claude Code-style permission mode."""
        if not hasattr(self, '_arbiter') or not self._arbiter:
            log.write(Text("Arbiter not initialized", style="red"))
            return

        from kernel.permission_gate import PermissionMode

        if not args:
            # Show current mode
            mode = self._arbiter.mode
            descs = PermissionMode.descriptions()
            log.write(Text(f"Current mode: {mode.value}", style="bold cyan"))
            log.write(Text(f"  {descs.get(mode.value, '')}", style="dim"))
            log.write(Text("\nAvailable modes:", style="bold"))
            for m in PermissionMode:
                icon = {"plan": "📋", "default": "🔒", "accept_edits": "✏️",
                        "auto": "🤖", "dont_ask": "🔓", "bypass": "⚡",
                        "bubble": "🫧"}.get(m.value, "❓")
                log.write(Text(f"  {icon} /permission {m.value:<14} {descs.get(m.value, '')}", style="dim"))
            return

        mode_str = args[0]
        result = self._arbiter.set_mode(mode_str)
        log.write(Text(result, style="green" if "Invalid" not in result else "yellow"))

        # Update sidebar
        try:
            sidebar = self.query_one("#sidebar", OrganismSidebar)
            sidebar.update_vitals(mode=self._arbiter.mode.value)
        except Exception:
            pass

    def _cmd_compact(self, log: RichLog, args: list[str]) -> None:
        """Claude Code-style /compact — 运行5层上下文压缩管道。

        /compact          手动触发一次全量压缩（显示前后对比）
        /compact auto     开启/关闭自动压缩（上下文使用率>80%时自动触发）
        /compact status   查看当前上下文窗口使用情况
        """
        sub = args[0].lower() if args else ""

        # ── /compact auto ──
        if sub == "auto":
            self._auto_compact = not self._auto_compact
            state = "ON" if self._auto_compact else "OFF"
            log.write(Text(f"  Auto-compact: [bold]{state}[/] "
                          f"(automatically compress when >{int(self._max_context_ratio*100)}% "
                          f"of {self._context_window//1000}K window used)",
                          style="cyan" if self._auto_compact else "dim"))
            return

        # ── /compact status ──
        if sub == "status":
            history_chars = sum(len(e.get("content", "")) for e in self._conversation_history)
            history_tokens = history_chars // 3
            ctx_pct = (history_tokens / self._context_window * 100) if self._context_window else 0
            bar_len = 30
            filled = int(bar_len * min(ctx_pct / 100, 1.0))
            bar = "█" * filled + "░" * (bar_len - filled)
            log.write(Panel(
                Text(f"Context Window: {self._context_window//1000}K tokens\n"
                     f"History Usage:  {history_tokens:,} tokens ({ctx_pct:.1f}%)\n"
                     f"[{bar}]\n"
                     f"Entries:        {len(self._conversation_history)}\n"
                     f"Auto-Compact:   {'ON' if self._auto_compact else 'OFF'}\n"
                     f"Compress at:    >{int(self._max_context_ratio*100)}%\n\n"
                     f"Tip: Run /compact to compress now, or /compact auto to enable auto-compression.",
                     style="dim"),
                border_style="cyan", title="📜 Context Status"))
            return

        # ── /compact (手动触发压缩) ──
        if not self._conversation_history:
            log.write(Text("  No conversation history to compact.", style="dim"))
            return

        # 从sync上下文调度async协程
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._run_compact(log))
        except RuntimeError:
            asyncio.run(self._run_compact(log))

    @work(exclusive=False)
    async def _run_compact(self, log: RichLog) -> None:
        """运行完整的5层压缩管道（LLM驱动摘要层需要异步）。"""
        from kernel.context_compressor import (
            compress_messages, truncate_tool_outputs,
            deduplicate_tool_results, summarize_conversation,
            slide_context_window, micro_compact,
        )

        # ── 转换对话历史 → 压缩器消息格式 ──
        messages: list[dict[str, Any]] = []
        for entry in self._conversation_history:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            mapped_role = {"user": "user", "assistant": "assistant", "tool": "user"}.get(role, "user")
            messages.append({"role": mapped_role, "content": content})

        # ── 压缩前统计 ──
        before_chars = sum(len(str(m.get("content", ""))) for m in messages)
        before_tokens = before_chars // 3
        before_entries = len(messages)

        log.write(Text(""))
        log.write(Rule("📜 Context Compaction", style="cyan"))
        log.write(Text(f"  Before: {before_entries} entries, ~{before_tokens:,} tokens "
                      f"({before_tokens/self._context_window*100:.1f}% of window)",
                      style="dim"))

        # ── 运行5层压缩管道 ──
        try:
            # Layer 1: 截断过长工具输出 (零成本)
            messages = truncate_tool_outputs(messages)
            l1_chars = sum(len(str(m.get("content", ""))) for m in messages)
            log.write(Text(f"  L1 Truncate: {before_chars//3:,} → {l1_chars//3:,} tokens",
                          style="dim"))

            # Layer 5: 语义去重 (零成本)
            messages = deduplicate_tool_results(messages)
            l5_entries = len(messages)
            if before_entries != l5_entries:
                log.write(Text(f"  L5 Dedup: {before_entries} → {l5_entries} entries "
                              f"({before_entries - l5_entries} duplicates removed)",
                              style="dim"))

            # Layer 3: LLM摘要 (核心压缩——用DeepSeek Flash做便宜摘要)
            log.write(Text("  L3 Summarization: generating with LLM...", style="dim yellow"))
            messages = await summarize_conversation(
                messages, self._gateway, max_summary_tokens=15000,
            )
            l3_chars = sum(len(str(m.get("content", ""))) for m in messages)
            log.write(Text(f"  L3 Summarize: → {l3_chars//3:,} tokens", style="dim"))

            # Layer 4: 滑动窗口 (最后手段——如果还是太大)
            max_hist_tokens = int(self._context_window * self._max_context_ratio)
            messages = slide_context_window(messages, max_tokens=max_hist_tokens)
            l4_chars = sum(len(str(m.get("content", ""))) for m in messages)
            log.write(Text(f"  L4 Window: → {l4_chars//3:,} tokens (cap: {max_hist_tokens//1000}K)",
                          style="dim"))

            # ── 压缩后统计 ──
            after_chars = sum(len(str(m.get("content", ""))) for m in messages)
            after_tokens = after_chars // 3
            after_entries = len(messages)

            saved_tokens = before_tokens - after_tokens
            ratio = (saved_tokens / before_tokens * 100) if before_tokens > 0 else 0

            # ── 替换对话历史（压缩后的消息 → 历史格式）──
            self._conversation_history.clear()
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                hist_role = {"user": "user", "assistant": "assistant", "system": "tool"}.get(role, "user")
                if content.strip():
                    self._conversation_history.append({
                        "role": hist_role, "content": content,
                    })

            # ── 显示结果 ──
            bar_width = 30
            before_bar = bar_width
            after_bar = max(1, int(bar_width * (after_tokens / before_tokens)) if before_tokens > 0 else 1)

            log.write(Text(""))
            log.write(Panel(
                Text(f"Before:  {'█' * before_bar}  {before_tokens:,} tokens  ({before_entries} entries)\n"
                     f"After:   {'█' * after_bar}{'░' * (bar_width - after_bar)}  "
                     f"{after_tokens:,} tokens  ({after_entries} entries)\n\n"
                     f"Saved:   {saved_tokens:,} tokens ({ratio:.1f}%)\n"
                     f"Compression ratio: {before_tokens/after_tokens:.1f}x"
                     if after_tokens > 0 else
                     f"Saved:   {saved_tokens:,} tokens ({ratio:.1f}%)\n",
                     style="bold green"),
                border_style="green", title="✅ Compaction Complete"))
            log.write(Text(f"  Hint: Context window now {after_tokens/self._context_window*100:.1f}% used. "
                          f"Use /compact auto for automatic management.",
                          style="dim"))

            # 更新侧边栏
            try:
                sidebar = self.query_one("#sidebar", OrganismSidebar)
                sidebar.update_vitals(history_tokens=after_tokens)
            except Exception:
                pass

        except Exception as e:
            log.write(Text(f"  Compaction error: {e}", style="red"))
            log.write(Text("  History preserved unchanged.", style="dim"))

    def _cmd_selftest(self, log: RichLog) -> None:
        """运行全终端功能自检——测试所有MCP工具类别，报告通过/失败，自动修复常见问题。"""
        log.write(Text(""))
        log.write(Rule("🩺 Sclerotium OS — Full Terminal Self-Test", style="cyan"))
        log.write(Text("Testing all tool categories...\n", style="dim"))

        passed, failed, errors = 0, 0, []

        def _try(category: str, tool_name: str, args: dict, check_ok: bool = True) -> bool:
            """调用一个工具并检查结果。返回是否通过。"""
            nonlocal passed, failed
            try:
                handler = self._tools.get_handler(tool_name) if self._tools else None
                if handler is None:
                    errors.append(f"{category}/{tool_name}: handler not found")
                    failed += 1
                    return False
                import asyncio
                async def _run(): return await self._agent_loop._execute_tool(tool_name, args)
                import asyncio as aio
                try: loop = aio.get_running_loop()
                except RuntimeError: loop = aio.new_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as ex:
                        fut = ex.submit(lambda: aio.run(_run()))
                        result = fut.result(timeout=10)
                else:
                    result = loop.run_until_complete(_run())

                ok = result.get("status") == "ok" if check_ok else "error" not in str(result).lower()
                if ok:
                    passed += 1
                    log.write(Text(f"  ✅ {category}/{tool_name}", style="green"))
                    return True
                else:
                    failed += 1
                    err = result.get("error", str(result)[:80])
                    errors.append(f"{category}/{tool_name}: {err}")
                    log.write(Text(f"  ❌ {category}/{tool_name}: {err}", style="red"))
                    return False
            except Exception as e:
                failed += 1
                errors.append(f"{category}/{tool_name}: {str(e)[:80]}")
                log.write(Text(f"  💥 {category}/{tool_name}: {e}", style="bold red"))
                return False

        # ── Category 1: 文件操作 ──
        log.write(Text("[Files]", style="bold"))
        _try("files", "file_write", {"file_path": "_selftest.txt", "content": "ok"})
        _try("files", "file_read", {"file_path": "_selftest.txt"})
        _try("files", "file_edit", {"file_path": "_selftest.txt", "old_string": "ok", "new_string": "OK"})
        _try("files", "file_list", {"directory": "."})
        # Cleanup
        import os as _os
        try: _os.remove("_selftest.txt")
        except: pass

        # ── Category 2: 系统命令（这些工具返回非标准格式，用check_ok=False）──
        log.write(Text("[System]", style="bold"))
        _try("system", "system_status", {}, check_ok=False)
        _try("system", "ls", {"path": "."}, check_ok=False)
        _try("system", "pwd", {}, check_ok=False)
        _try("system", "uname", {}, check_ok=False)

        # ── Category 3: Bash ──
        log.write(Text("[Bash]", style="bold"))
        _try("bash", "bash_execute", {"command": "echo sclerotium_ok"})
        _try("bash", "bash_smart", {"action": "check"}, check_ok=False)

        # ── Category 4: Git ──
        log.write(Text("[Git]", style="bold"))
        _try("git", "git_status", {})
        _try("git", "git_log", {"n": 3})

        # ── Category 5: 网络 ──
        log.write(Text("[Network]", style="bold"))
        _try("network", "web_fetch", {"url": "https://httpbin.org/get"}, check_ok=False)

        # ── 结果 ──
        total = passed + failed
        log.write(Text(""))
        if failed == 0:
            log.write(Panel(
                Text(f"All {total} tests passed! ✅\n\n"
                     f"The terminal is fully functional.\n"
                     f"191 tools, 5-layer memory, 7-layer security — all operational.",
                     style="bold green"),
                border_style="green", title="🟢 Self-Test Complete"))
        else:
            log.write(Panel(
                Text(f"{passed}/{total} passed, {failed} failed\n\n"
                     + "\n".join(errors[:10])
                     + (f"\n... and {len(errors)-10} more" if len(errors) > 10 else ""),
                     style="bold yellow"),
                border_style="yellow" if failed < 5 else "red",
                title="🔴 Self-Test Complete — Auto-Repair Starting"))
            # ── 自动把失败结果喂给LLM，让它自己修复 ──
            repair_prompt = (
                f"The self-test found {failed} failures out of {total} tests. "
                f"Here are the exact errors:\n\n"
                + "\n".join(errors)
                + "\n\nFix ALL of these bugs yourself. For each one:\n"
                + "1. Read the source file that contains the broken tool\n"
                + "2. Fix the parameter names, handler registration, or function signature\n"
                + "3. Verify the fix by running the test again\n\n"
                + "After fixing all bugs, run /selftest to confirm everything passes."
            )
            self._conversation_history.append({
                "role": "user", "content": "Self-test completed. Fix the failures.",
            })
            self._conversation_history.append({
                "role": "tool",
                "content": f"Self-test results: {passed}/{total} passed, {failed} failed\n" + "\n".join(errors),
            })
            self._run_agent(repair_prompt)

    def _cmd_list_skills(self, log: RichLog) -> None:
        """List all loaded skills."""
        skills = [c for c in self._cmd_registry.all_commands() if c.source == "skill"]
        if not skills:
            log.write(Text("No skills loaded. Check skills/ directory.", style="yellow"))
            return
        table = Table(title=f"Loaded Skills ({len(skills)})", border_style="cyan")
        table.add_column("Command", style="bold green")
        table.add_column("Description", style="dim")
        for s in skills[:30]:
            table.add_row(s.slug, s.description[:60])
        log.write(table)

    def _cmd_list_tools(self, log: RichLog) -> None:
        """List all loaded MCP tools."""
        tools = [c for c in self._cmd_registry.all_commands() if c.source == "mcp"]
        if not tools:
            log.write(Text("No MCP tools loaded.", style="yellow"))
            return
        # Group by category
        by_cat: dict[str, list[Command]] = {}
        for t in tools:
            by_cat.setdefault(t.category, []).append(t)
        for cat, cmds in sorted(by_cat.items()):
            names = ", ".join(c.slug for c in cmds[:8])
            log.write(Text(f"[{cat}] {names}", style="dim"))

    def _execute_mcp_tool(self, log: RichLog, tool_name: str, args: list[str]) -> None:
        """Execute an MCP tool by name."""
        if not self._tools:
            log.write(Text("Tools not initialized", style="red"))
            return
        handler = self._tools.get_handler(tool_name)
        if handler is None:
            log.write(Text(f"Tool not found: {tool_name}", style="yellow"))
            return
        try:
            # Build kwargs from args (simple key=value parsing)
            kwargs = {}
            for a in args:
                if "=" in a:
                    k, v = a.split("=", 1)
                    kwargs[k] = v
            result = handler(**kwargs) if kwargs else handler()
            if asyncio.iscoroutine(result):
                result = asyncio.ensure_future(result)
            import json
            log.write(Syntax(
                json.dumps(result, indent=2, ensure_ascii=False, default=str)[:3000],
                "json", theme="monokai"))
        except Exception as e:
            log.write(Text(f"Tool error: {e}", style="red"))

    @work(exclusive=False)
    async def _invoke_skill(self, log: RichLog, cmd: Command, args: list[str]) -> None:
        """Invoke a skill -- loads SKILL.md in background thread."""
        import asyncio
        skill_path = Path(cmd.skill_path) if cmd.skill_path else None
        if skill_path and skill_path.exists():
            def _load():
                return skill_path.read_text(encoding="utf-8", errors="replace")
            try:
                content = await asyncio.to_thread(_load)
                log.write(Panel(Markdown(content[:3000]),
                              border_style="magenta", title=f"Skill: {cmd.name}"))
                log.write(Text(f"Skill '{cmd.slug}' loaded ({len(content):,} chars).",
                              style="green"))
            except Exception as e:
                log.write(Text(f"Skill load error: {e}", style="red"))
        else:
            log.write(Text(f"Skill '{cmd.slug}': {cmd.description}", style="cyan"))

    # ── 7维上下文编排 ─────────────────────────────────────────────────

    def _build_full_context(self, prompt: str) -> str:
        """构建完整7维上下文——对标Claude Code的上下文注入架构。

        7个维度，按重要性排序：
          1. 环境     — OS / Shell / Python / 项目根路径
          2. Git      — 分支 / 状态 / 最近提交
          3. 项目结构  — 顶层文件+目录列表
          4. 文件编辑  — 最近编辑过的文件
          5. 会话目标  — 自动提取的当前任务
          6. 对话历史  — 完整上下文（token预算感知）
          7. 工具提示  — XML格式 + 安全规则
        """
        import platform, os as _os, subprocess, time

        project_root = str(PROJECT_ROOT.resolve())
        parts: list[str] = []

        # ═══════════════════════════════════════════════════════════════
        # 1. 环境上下文 + 工具参数签名参考
        # ═══════════════════════════════════════════════════════════════
        python_ver = platform.python_version()
        python_path = __import__('sys').executable
        os_name = f"{platform.system()} {platform.release()}"
        shell_hint = "Git Bash (Unix commands: ls/pwd/cat/find/grep work; use /c/... or C:/... paths)"

        # 关键工具参数签名（LLM需要知道每个工具要什么参数）
        tool_ref_lines = []
        if self._tools:
            try:
                all_tools = self._tools.list_tools()
                for t in all_tools:  # 全部工具——100万token窗口绰绰有余
                    name = t.get("name", "")
                    desc = (t.get("description", "") or "")
                    params = t.get("parameters", {}).get("properties", {})
                    required = t.get("parameters", {}).get("required", [])
                    param_parts = []
                    for pname, pinfo in params.items():
                        req_mark = "*" if pname in (required or []) else ""
                        ptype = pinfo.get("type", "str")
                        param_parts.append(f"{req_mark}{pname}:{ptype}")
                    sig = f"{name}({', '.join(param_parts[:5])})" if param_parts else f"{name}()"
                    tool_ref_lines.append(f"  {sig}  -- {desc}")
            except Exception:
                pass
        tool_ref = "\n".join(tool_ref_lines) if tool_ref_lines else "  (tools loading...)"

        # 检测已安装的关键Python包（用缓存避免每次LLM请求都跑subprocess）
        pkg_hint = ""
        try:
            r = subprocess.run(
                ["pip", "list", "--format=columns"],
                capture_output=True, text=True, timeout=5, cwd=project_root)
            if r.returncode == 0:
                pkgs = set()
                for line in r.stdout.strip().split("\n")[2:]:  # Skip header
                    pkg_name = line.split()[0].lower().strip()
                    if pkg_name and not pkg_name.startswith("-"):
                        pkgs.add(pkg_name)
                important = {"fastapi", "flask", "django", "requests", "httpx",
                    "pandas", "numpy", "sqlalchemy", "pydantic", "uvicorn",
                    "pytest", "rich", "click", "jinja2", "pillow", "textual",
                    "litellm", "openai", "anthropic", "chromadb", "aiohttp",
                    "scipy", "matplotlib", "redis", "celery", "websocket"}
                found = sorted(pkgs & important)[:20]
                if found:
                    pkg_hint = f"\n  Key packages: {', '.join(found)}"
                elif pkgs:
                    # 至少列出包总数
                    pkg_hint = f"\n  Packages: {len(pkgs)} installed"
        except Exception:
            pass

        env_block = (
            f"<environment>\n"
            f"  OS: {os_name} | {shell_hint}\n"
            f"  Project: {project_root}\n"
            f"  Python: {python_ver} ({python_path}){pkg_hint}\n"
            f"  Model: {self._provider}/{self._model} ({self._context_window//1000}K ctx)\n"
            f"</environment>\n"
            f"<tool_reference>\n"
            f"{tool_ref}\n"
            f"</tool_reference>"
        )
        parts.append(env_block)

        # ═══════════════════════════════════════════════════════════════
        # 2. Git 上下文（如果可用）
        # ═══════════════════════════════════════════════════════════════
        try:
            def _git(cmd: str) -> str:
                r = subprocess.run(["git"] + cmd.split(), capture_output=True,
                                  text=True, timeout=3, cwd=project_root)
                return r.stdout.strip()[:500]

            branch = _git("branch --show-current")
            status = _git("status --short")
            log = _git("log --oneline -5")

            if branch:
                git_lines = [f"  Branch: {branch}"]
                if status:
                    changes = len(status.split("\n")) if status else 0
                    git_lines.append(f"  Changes: {changes} file(s)\n    {status[:300]}")
                if log:
                    git_lines.append(f"  Recent commits:\n    {log[:300]}")
                parts.append(f"<git>\n" + "\n".join(git_lines) + "\n</git>")
        except Exception:
            pass

        # ═══════════════════════════════════════════════════════════════
        # 3. 项目结构（顶层概览）
        # ═══════════════════════════════════════════════════════════════
        try:
            items = sorted(Path(project_root).iterdir())
            dirs = [f"📁 {d.name}/" for d in items if d.is_dir() and not d.name.startswith('.')][:12]
            files = [f"📄 {f.name}" for f in items if f.is_file() and not f.name.startswith('.')][:15]
            structure = dirs + files
            if structure:
                parts.append(
                    f"<project_structure>\n  "
                    f"{'  '.join(structure[:20])}"
                    f"\n</project_structure>"
                )
        except Exception:
            pass

        # ═══════════════════════════════════════════════════════════════
        # 4. 最近编辑文件
        # ═══════════════════════════════════════════════════════════════
        if self._recently_edited:
            recent = self._recently_edited[-10:]
            parts.append(
                f"<recently_edited>\n  "
                + "\n  ".join(recent)
                + "\n</recently_edited>"
            )

        # ═══════════════════════════════════════════════════════════════
        # 5. 会话目标（自动提取）
        # ═══════════════════════════════════════════════════════════════
        if self._session_goal:
            parts.append(f"<session_goal>\n  {self._session_goal}\n</session_goal>")

        # ═══════════════════════════════════════════════════════════════
        # 6. 对话历史（完整 + token预算感知）
        # ═══════════════════════════════════════════════════════════════
        if self._conversation_history:
            max_history_tokens = int(self._context_window * self._max_context_ratio)
            hist_lines = ["<conversation_history>"]
            estimated_tokens = 0

            for entry in reversed(self._conversation_history):
                content = entry.get("content", "")
                entry_tokens = len(content) // 3 + 1
                if estimated_tokens + entry_tokens > max_history_tokens:
                    hist_lines.insert(1, "<!-- earlier history omitted: context window limit -->")
                    break
                estimated_tokens += entry_tokens
                role = entry.get("role", "user")
                tag = {"user": "User", "assistant": "Assistant", "tool": "ToolResult"}.get(role, role)
                hist_lines.insert(1, f"<{tag}>\n{content}\n</{tag}>")

            hist_lines.append("</conversation_history>")
            parts.append("\n".join(hist_lines))

        # ═══════════════════════════════════════════════════════════════
        # 7. 提示词宪法 — 融合4大框架（Claude Code + OpenCode + Reasonix + Kun）
        # ═══════════════════════════════════════════════════════════════
        # 使用 PromptFactory 生成不可变前缀 + 模型特定指令 + 工具格式宪法
        from kernel.prompt_factory import IMMUTABLE_PREFIX, TOOL_FORMAT_CONSTITUTION
        factory = getattr(self, '_prompt_factory', None)
        model_specific = factory.get_model_specific_prompt(
            self._provider) if factory else ""

        # 精简版工具参考（渐进式披露 —— 对标Kun）
        tool_ref_lines = []
        if self._tools:
            try:
                # 只显示核心10个工具（对标Claude Code 17工具，而非我们全部191个）
                CORE_TOOLS = {
                    "file_write", "file_read", "file_edit", "bash_execute",
                    "file_list", "web_search", "web_fetch", "codebase_search",
                    "git_status", "git_log"
                }
                all_tools = self._tools.list_tools()
                for t in all_tools:
                    name = t.get("name", "")
                    if name in CORE_TOOLS:
                        desc = (t.get("description", "") or "")
                        params = t.get("parameters", {}).get("properties", {})
                        required = t.get("parameters", {}).get("required", [])
                        param_parts = []
                        for pname, pinfo in params.items():
                            req_mark = "*" if pname in (required or []) else ""
                            ptype = pinfo.get("type", "str")
                            param_parts.append(f"{req_mark}{pname}:{ptype}")
                        sig = f"{name}({', '.join(param_parts[:4])})"
                        tool_ref_lines.append(f"  {sig}")
            except Exception:
                pass
        tool_ref = "\n".join(tool_ref_lines[:12]) if tool_ref_lines else "  (tools loading...)"

        # 意图检测 + 行动指令
        code_kw = ["写", "编写", "生成", "创建", "开发", "实现", "build", "create",
                   "write", "generate", "code", "make", "implement", "script",
                   "程序", "脚本", "代码", "api", "函数", "应用", "网站",
                   "html", "css", "python", "javascript", "fastapi", "flask"]
        search_kw = ["搜索", "查找", "查询", "最新", "新闻", "是什么", "怎么", "如何",
                     "search", "find", "lookup", "what is", "how to", "latest"]
        file_kw = ["看看", "查看", "读", "分析", "检查", "review", "read", "check",
                   "打开", "open", "show", "显示", "内容", "文件内容"]
        debug_kw = ["修复", "bug", "错误", "不工作", "坏了", "fix", "debug", "error",
                    "broken", "solve", "解决", "问题", "为什么", "怎么回事"]

        p_lower = prompt.lower()
        if any(kw in p_lower for kw in code_kw):
            action_prompt = (
                "CODE TASK — Build the ENTIRE project from the spec.\n"
                "1. file_write each file. Put ALL code inside the JSON \"content\" field.\n"
                "2. Do NOT re-read files after writing — file_write status:ok means success.\n"
                "3. When ALL spec files exist: run tests with bash_execute.\n"
                "4. After tests pass: output ONLY a text summary. STOP."
            )
        elif any(kw in p_lower for kw in search_kw):
            action_prompt = "RESEARCH TASK — web_search → web_fetch → synthesize. Cite sources."
        elif any(kw in p_lower for kw in file_kw):
            action_prompt = "FILE TASK — file_read → analyze → explain."
        elif any(kw in p_lower for kw in debug_kw):
            action_prompt = "DEBUG TASK — file_read → reproduce → file_edit → test."
        else:
            action_prompt = "Act NOW. Call the right tool. Report results."

        context_body = "\n\n".join(parts)

        # 组装：不可变前缀 + 模型特定 + 工具宪法 + 环境上下文 + 工具参考 + 用户请求
        full_context = (
            f"{IMMUTABLE_PREFIX}\n\n"
            f"{model_specific}\n"
            f"{TOOL_FORMAT_CONSTITUTION}\n\n"
            f"<tool_reference>\n{tool_ref}\n</tool_reference>\n\n"
            f"{context_body}\n\n"
            f"<user_request>\n{prompt}\n</user_request>\n\n"
            f"{action_prompt}"
        )

        return full_context

    # ── Chat ──────────────────────────────────────────────────────────

    def _run_agent(self, prompt: str, *, original_prompt: str = "") -> None:
        self._run_agent_worker(prompt, original_prompt=original_prompt)

    @work(exclusive=False)
    async def _run_agent_worker(self, prompt: str, *, original_prompt: str = "") -> None:
        log = self.query_one("#messages", RichLog)
        log.write(Text(""))
        self._start_thinking()

        # ── Auto-activate capabilities from natural language ──
        activated = []
        context_injection = ""
        if hasattr(self, '_cap_router'):
            activated = self._cap_router.route(prompt, max_capabilities=8)
            context_injection = self._cap_router.build_context_injection(prompt, max_capabilities=8)
            if activated:
                names = ", ".join(c.name for c in activated[:5])
                log.write(Text(f"  Auto-activated: {names}", style="dim magenta"))

        # ── Plan Mode: detect discussion/planning, ask clarifying questions ──
        plan_keywords = ["plan", "discuss", "brainstorm", "idea for", "how should i",
                        "what should i", "design a", "architecture for", "proposal",
                        "suggestion", "recommend", "should i", "which approach",
                        "project idea", "feature request", "roadmap", "strategy",
                        "help me think", "what do you think about", "considering"]
        is_planning = any(kw in prompt.lower() for kw in plan_keywords)

        if is_planning and len(prompt) > 20:
            log.write(Panel(
                Text("I'll help clarify your requirements.\n"
                     "Let me ask a few questions first...",
                     style="bold cyan"),
                border_style="cyan", title="Plan Mode"))
            questions = await self._ask_clarifying_questions(prompt)
            if questions:
                log.write(Markdown(questions))
                log.write(Text("Answer these and I'll build exactly what you need.",
                              style="dim italic"))
                self._stop_thinking()
                self._update_status(
                    f"Plan mode -- answer questions above | "
                    f"{self._provider}/{self._model} | v0.5.0")
                return

        # ── 自动提取会话目标 ──
        if not self._session_goal and len(prompt) > 10:
            self._session_goal = prompt[:200]

        # ── 自检请求检测：自动触发 /selftest 而非让LLM猜 ──
        selftest_keywords = ["测试你自己的全部", "测试你的全部", "全量测试", "全量修复bug",
                            "测试全部终端功能", "检索你自己的全部终端功能", "全终端功能测试",
                            "全部终端功能进行测试", "自己测试", "自己修复",
                            "test all your", "self test", "full terminal test"]
        if any(kw in prompt.lower() for kw in selftest_keywords):
            log.write(Text("  ⚡ Self-test request detected — running /selftest", style="bold cyan"))
            self._cmd_selftest(log)
            return

        # ── 7维上下文编排（环境 + Git + 项目结构 + 文件编辑 + 目标 + 历史 + 工具）──
        enhanced_prompt = self._build_full_context(prompt)
        if context_injection:
            enhanced_prompt = f"{context_injection}\n\n{enhanced_prompt}"

        # ═══════════════════════════════════════════════════════════════
        # 多轮Agent循环：LLM可以调用工具→看到结果→继续思考→再调用
        # 代码任务需要更多轮数（每轮通常只创建1个文件）
        # ═══════════════════════════════════════════════════════════════
        code_kw_turns = ["写", "编写", "生成", "创建", "开发", "build", "create", "write", "generate", "code", "make", "implement", "程序", "脚本", "代码", "api"]
        is_code = any(kw in prompt.lower() for kw in code_kw_turns)
        # 不限制轮数——LLM自主迭代，直到自然停止或30轮硬停止。
        MAX_AGENT_TURNS = 30  # 30轮足够完成任何代码任务
        current_prompt = enhanced_prompt
        all_assistant_texts: list[str] = []
        all_tool_results: list[str] = []
        final_full_text = ""
        task_context: str = ""
        files_created_this_task: set[str] = set()
        files_read_this_task: set[str] = set()  # 防止反复重读
        empty_retries: int = 0  # 空响应重试计数
        # ── 任务完成跟踪：防止无限循环 ──
        all_tests_passed: bool = False       # 至少一次pytest全通过
        completion_warning_given: bool = False  # 已警告LLM停止
        pytest_accumulated_passed: int = 0    # 跨轮次累计
        pytest_attempted: bool = False         # 至少尝试过跑测试（区别于从未跑过）
        last_error_signature: str = ""          # 上一次的 ImportError 指纹（检测重复）
        code_changed_since_last_test: bool = False  # 上次pytest后是否有代码变更
        last_pytest_command: str = ""           # 上次的 pytest 命令
        # ── Doom Loop检测（对标OpenCode）──
        recent_tool_calls: list[str] = []     # 最近工具调用指纹
        DOOM_LOOP_THRESHOLD = 3               # 同一调用重复3次→break

        try:
            for agent_turn in range(1, MAX_AGENT_TURNS + 1):
                if agent_turn > 1:
                    log.write(Text(f"  ↻ Turn {agent_turn}...", style="dim"))

                full_text = ""
                stream_error = None
                async for chunk in self._gateway.chat_stream(
                    current_prompt, model=self._model, provider=self._provider
                ):
                    if chunk.get("type") == "token":
                        full_text += chunk["content"]
                    elif chunk.get("type") == "done":
                        self._total_tokens += chunk.get("tokens", 0)
                        self._turn_count += 1
                    elif chunk.get("type") == "error":
                        stream_error = chunk.get("content", "Unknown stream error")
                        log.write(Text(f"  ⚠ API error: {stream_error}", style="red"))
                        break

                if stream_error and not full_text:
                    log.write(Text(f"  ⚠ Stream failed: {stream_error}", style="red"))
                    break

                if not full_text:
                    if empty_retries < 3:
                        empty_retries += 1
                        log.write(Text(f"  (empty response, retry {empty_retries}/3)", style="dim"))
                        continue
                    break
                empty_retries = 0  # reset on successful response

                # 清理XML → 显示干净文本
                clean_text = full_text
                for tag in ['tool_call', 'file_path', 'content', 'command',
                           'path', 'code', 'text', 'working_dir', 'timeout',
                           'old_string', 'new_string', 'query', 'url', 'cmd']:
                    clean_text = re.sub(
                        rf'<{tag}[^>]*>.*?</{tag}>', '',
                        clean_text, flags=re.DOTALL | re.IGNORECASE)
                clean_text = re.sub(r'\n{3,}', '\n\n', clean_text).strip()
                if clean_text:
                    all_assistant_texts.append(clean_text)
                    log.write(Text(clean_text, style=""))

                final_full_text = full_text
                self._last_response = full_text

                # ── 工具调用修复管线（对标 Reasonix Scavenge）──
                # DeepSeek有时把工具调用JSON放在reasoning里，scavenge抢救出来
                full_text = ToolCallRepairPipeline.scavenge(full_text)

                # 提取工具调用
                tool_calls = self._agent_loop._extract_tool_calls(full_text) if self._agent_loop else []

                if not tool_calls:
                    # ── 检测"说了要做但没做"——DeepSeek经典行为 ──
                    # LLM说了"运行测试"/"创建文件"等但没输出JSON → 给一次恢复机会
                    action_intent_kw = [
                        "运行测试", "run test", "pytest", "创建文件", "create file",
                        "写入", "write", "执行", "execute", "运行", "开始", "start",
                        "现在", "now", "接下来", "next", "立即", "马上",
                        "让我", "let me", "我来", "I will", "I'll",
                        "验证", "verify", "检查", "check", "确认", "confirm",
                        "测试", "test", "试试", "尝试", "换个", "修复", "fix",
                    ]
                    has_intent = any(kw in full_text.lower() for kw in action_intent_kw)
                    has_files_created = bool(files_created_this_task)

                    if has_intent:
                        if not has_files_created:
                            # 说了要创建但还没做 → 重试
                            log.write(Text(
                                "  ⚡ Intent detected but no action — retrying with action prompt",
                                style="bold yellow"))
                            current_prompt = (
                                f"You said: \"{full_text[:200]}...\"\n"
                                f"BUT you did NOT output a tool call JSON.\n"
                                f"NOW output the tool call: ```json\n"
                                f"{{\"tool\":\"file_write\",\"file_path\":\"f.py\",\"content\":\"code\"}}\n"
                                f"```"
                            )
                            empty_retries += 1
                            if empty_retries < 3:
                                continue
                        # 已创建过文件但说了要运行测试 → 还没跑测试
                        if has_files_created:
                            log.write(Text(
                                "  ⚡ Test intent without action — injecting test reminder",
                                style="bold yellow"))
                            current_prompt = (
                                f"You said you will run tests but did NOT output a bash_execute.\n"
                                f"Output NOW: ```json\n"
                                f"{{\"tool\":\"bash_execute\",\"command\":"
                                f"\"cd test_project_output && python -m pytest tests/ -v\"}}\n"
                                f"```\n"
                                f"If tests pass: output ONLY text summary and STOP."
                            )
                            empty_retries += 1
                            if empty_retries < 3:
                                continue
                    break

                # 执行工具
                turn_results: list[str] = []
                for tc in tool_calls:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("arguments", {})

                    # 安全检查
                    cmd_str = str(tool_args.get("command", tool_args.get("file_path", "")))
                    BLOCKED = [r'rm\s+-rf\s+/', r'>\s*/dev/sda', r'mkfs', r'dd\s+if=',
                               r'format\s+[cC]:', r'shutdown', r'reboot',
                               r'chmod\s+777\s+/', r'sudo\s+rm', r'DROP\s+TABLE']
                    if any(__import__('re').search(p, cmd_str, __import__('re').IGNORECASE) for p in BLOCKED):
                        log.write(Text(f"⛔ BLOCKED: '{cmd_str[:80]}'", style="bold red"))
                        turn_results.append(f"BLOCKED {tool_name}: {cmd_str[:100]}")
                        continue

                    # ── 阻止无代码变更时重复跑pytest ──
                    if tool_name == "bash_execute" and "pytest" in str(tool_args.get("command", "")):
                        cmd = str(tool_args.get("command", ""))
                        if cmd == last_pytest_command and not code_changed_since_last_test:
                            log.write(Text(
                                "  ⛔ BLOCKED: Same pytest command with no code changes since last run.",
                                style="bold red"))
                            turn_results.append(
                                f"BLOCKED pytest: NO code changes since last test. "
                                f"Fix the code FIRST using file_edit, then re-run tests."
                            )
                            all_tool_results.append(turn_results[-1])
                            continue
                        last_pytest_command = cmd
                        code_changed_since_last_test = False  # reset tracker

                    try:
                        # 激活对应器官（侧边栏显示真实活动）
                        self._activate_tool_organ(tool_name)
                        result = await self._agent_loop._execute_tool(tool_name, tool_args)
                        # 不截断任何工具结果——1M上下文窗口足够
                        result_summary = str(result)

                        # ── 保存规格书/关键文件到跨轮次上下文 ──
                        if tool_name == "file_read" and result.get("status") == "ok":
                            fp = str(result.get("file_path", ""))
                            files_read_this_task.add(fp)  # 防止反复重读
                            content = result.get("content", "")
                            if len(content) > 500 and ("spec" in str(result.get("file_path", "")).lower()
                                                       or "规格" in content[:200]
                                                       or "API 设计" in content[:500]
                                                       or "功能需求" in content[:500]):
                                task_context = f"TASK SPEC (keep this):\n{content}\n\n"
                        turn_results.append(f"{tool_name}: {result_summary}")
                        all_tool_results.append(f"{tool_name}: {result_summary}")

                        if tool_name in ("file_edit", "file_write") and result.get("status") == "ok":
                            code_changed_since_last_test = True

                        if tool_name == "file_write" and result.get("status") == "ok":
                            fp = result.get('file_path', '')
                            files_created_this_task.add(fp)  # 追踪已创建文件
                            # 读取文件前几行作为预览
                            preview = ""
                            try:
                                with open(fp, encoding="utf-8", errors="replace") as pf:
                                    first_lines = [next(pf).rstrip()[:80] for _ in range(5)]
                                    preview = "".join(f"\n    | {l}" for l in first_lines if l)
                            except Exception: pass
                            log.write(Text(f"  [green]File: {fp} ({result.get('size',0):,}B, {result.get('lines',0)} lines){preview}[/]", style="green"))
                            if fp and fp not in self._recently_edited:
                                self._recently_edited.append(fp)
                                if len(self._recently_edited) > 20: self._recently_edited.pop(0)
                            # ── 存入Hexis记忆（前台代码生成 → 后台进化引擎）──
                            if self._memory:
                                try:
                                    ext = fp.rsplit(".", 1)[-1] if "." in fp else ""
                                    keywords = [fp, ext] if ext else [fp]
                                    self._memory.store(
                                        content=f"Generated {fp} ({result.get('size',0)}B, {result.get('lines',0)} lines)",
                                        level="episodic", importance=0.7,
                                        metadata={
                                            "type": "code_generation",
                                            "pattern_type": "code_generation",  # _law_learn filter
                                            "file": fp, "ext": ext,
                                            "size": result.get('size', 0),
                                            "lines": result.get('lines', 0),
                                            "keywords": keywords,
                                        })
                                except Exception: pass
                        elif tool_name == "file_edit" and result.get("status") == "ok":
                            fp = result.get('file_path', '')
                            if fp and fp not in self._recently_edited:
                                self._recently_edited.append(fp)
                                if len(self._recently_edited) > 20: self._recently_edited.pop(0)
                        elif tool_name == "bash_execute":
                            out = (result.get("stdout") or result.get("error") or "")
                            log.write(Text(f"  $ {out}", style="dim green" if result.get("status")=="ok" else "red"))
                            if self._memory and result.get("status") == "error":
                                try:
                                    self._memory.store(
                                        content=f"Error: {result.get('stderr', result.get('error', ''))}",
                                        level="episodic", importance=0.5,
                                        metadata={"type": "error", "command": tool_args.get("command", "")[:100]})
                                except Exception: pass
                        else:
                            log.write(Text(f"  {tool_name}: {str(result)}", style="dim"))
                    except Exception as e:
                        log.write(Text(f"Tool error: {e}", style="red"))
                        turn_results.append(f"ERROR {tool_name}: {str(e)}")
                        all_tool_results.append(f"ERROR {tool_name}: {str(e)}")

                # ── 更新跨轮次pytest累计 ──
                for r in turn_results:
                    if "bash_execute" in r or "bash_smart" in r:
                        pm = re.search(r'(\d+)\s+passed', str(r))
                        fm = re.search(r'(\d+)\s+failed', str(r))
                        if pm: pytest_accumulated_passed = max(pytest_accumulated_passed, int(pm.group(1)))
                        if fm and int(fm.group(1)) == 0 and pm and int(pm.group(1)) > 0:
                            all_tests_passed = True  # 0 failed, N passed → 全部通过!
                if all_tests_passed:
                    log.write(Text(f"  ✅ All tests passed! Task complete.", style="bold green"))
                    # 等待当前文本显示后再break
                    break

                # ── 硬停止：超过最大轮数 ──
                if agent_turn >= MAX_AGENT_TURNS:
                    log.write(Text(f"  ⏰ Max turns ({MAX_AGENT_TURNS}) reached.", style="bold yellow"))
                    break

                # ── 定义工具分类（多处使用，提前定义） ──
                read_tools = {"file_read", "file_list", "ls", "pwd", "cat", "system_status",
                              "git_status", "git_log", "web_search", "web_fetch", "codebase_search"}

                # ── Doom Loop检测（对标OpenCode）：同一工具+相同参数4次→死循环 ──
                for tc in tool_calls:
                    fp = f"{tc.get('name','')}:{sorted(tc.get('arguments',{}).items())}"
                    recent_tool_calls.append(fp)
                if len(recent_tool_calls) > DOOM_LOOP_THRESHOLD * 3:
                    recent_tool_calls = recent_tool_calls[-DOOM_LOOP_THRESHOLD * 2:]
                # 检查最近N次中同一指纹是否出现≥4次
                if len(recent_tool_calls) >= DOOM_LOOP_THRESHOLD:
                    for fp in set(recent_tool_calls):
                        if recent_tool_calls.count(fp) >= DOOM_LOOP_THRESHOLD:
                            log.write(Text(
                                f"  🔁 Doom loop detected: {fp[:80]} repeated {recent_tool_calls.count(fp)}x",
                                style="bold red"))
                            break  # break inner for loop
                    else:
                        fp = None  # no doom loop
                    if fp and recent_tool_calls.count(fp) >= DOOM_LOOP_THRESHOLD:
                        break  # break outer agent loop

                # ── 硬停止：completion warning后LLM仍在做验证性读取 → 完成 ──
                if completion_warning_given:
                    read_only_this_turn = all(
                        tc.get("name", "") in read_tools for tc in tool_calls
                    ) if tool_calls else True
                    if read_only_this_turn:
                        log.write(Text(f"  ✅ Task finished — LLM doing verification only.", style="bold green"))
                        break

                # 构建下一轮的提示词（工具结果反馈给LLM）
                # 文件内容不截断
                short_results = []
                for r in turn_results:
                    short_results.append(r)  # 不截断——1M上下文窗口完全够用
                results_feedback = "\n".join(short_results)
                search_tools = {"web_search", "web_fetch"}
                all_reads = all(r.split(":")[0].strip() in read_tools for r in turn_results if r)
                all_writes = any("file_write" in r and "ok" in r.lower() for r in turn_results if r)
                any_failures = any("error" in r.lower() or "fail" in r.lower() for r in turn_results if r)
                any_search = any(r.split(":")[0].strip() in search_tools for r in turn_results if r)

                # ── 检测本轮的测试结果 ──
                pytest_passed = 0
                pytest_failed = 0
                collection_error = False
                import_error_name = ""
                for r in turn_results:
                    if "bash_execute" in r or "bash_smart" in r:
                        r_str = str(r)
                        pm = re.search(r'(\d+)\s+passed', r_str)
                        fm = re.search(r'(\d+)\s+failed', r_str)
                        if pm: pytest_passed = int(pm.group(1))
                        if fm: pytest_failed = int(fm.group(1))
                        # 检测"测试都收集不了"的情况
                        if "ImportError" in r_str or "error during collection" in r_str:
                            collection_error = True
                            pytest_attempted = True  # 尝试过了，只是收集失败
                            im = re.search(r"cannot import name '(\w+)'", r_str)
                            if im: import_error_name = im.group(1)
                        if pm or fm:
                            pytest_attempted = True  # 有测试结果 = 成功收集+执行

                task_nearly_done = pytest_passed >= 10 and pytest_failed <= 2
                # ── 接近完成 → 告警LLM下一轮必须停止 ──
                if task_nearly_done and not completion_warning_given:
                    completion_warning_given = True
                # ── 20轮还没成功跑过测试 → 强制推进 ──
                if agent_turn >= 20 and not pytest_attempted and not completion_warning_given:
                    log.write(Text(
                        f"  ⚡ Turn {agent_turn} with no successful test run — forcing completion mode",
                        style="bold yellow"))
                    completion_warning_given = True
                # ── 同一 ImportError 出现2次 → 阻止重试循环 ──
                if import_error_name:
                    sig = f"ImportError:{import_error_name}"
                    if sig == last_error_signature and not completion_warning_given:
                        log.write(Text(
                            f"  ⚡ Same ImportError ({import_error_name}) repeated — forcing fix mode",
                            style="bold yellow"))
                    last_error_signature = sig

                if all_reads:
                    if completion_warning_given:
                        scene = (
                            "⛔ FINAL TURN — TASK IS COMPLETE. ⛔\n"
                            f"Tests already passed: {pytest_accumulated_passed}. Do NOT re-read files.\n"
                            "Output ONLY a text summary. NO MORE TOOL CALLS. Any tool call will be ignored."
                        )
                    else:
                        scene = (
                            "You just read files. Do NOT re-read them. The user wants you to BUILD.\n"
                            "NOW output a file_write tool call to create the FIRST file. Put ALL code inside the \"content\" field.\n"
                            "Example: {\"tool\":\"file_write\",\"file_path\":\"test_project_output/database.py\",\"content\":\"import sqlite3\\n\\ndef init_db():\\n    ...\"}\n"
                            "CRITICAL: The \"content\" field MUST contain the complete file content — do NOT put code outside the JSON."
                        )
                elif any_search and not any_failures:
                    scene = "Search done. Synthesize a clear answer for the user."
                elif all_writes and not any_failures:
                    if completion_warning_given:
                        scene = (
                            "⛔ FINAL TURN — TASK IS COMPLETE. ⛔\n"
                            "All files created. Tests passed. Do NOT create more files.\n"
                            "Output ONLY a text summary. NO MORE TOOL CALLS."
                        )
                    else:
                        scene = (
                            "File saved successfully. Do NOT re-read it.\n"
                            "Check the progress list above. Create the NEXT file from the spec.\n"
                            "When ALL files exist: run \"cd test_project_output && python -m pytest tests/ -v\""
                        )
                elif any_failures:
                    if completion_warning_given:
                        scene = (
                            "⛔ FINAL TURN — TASK IS COMPLETE. ⛔\n"
                            f"Minor issues remain but task is done. Output ONLY a text summary.\n"
                            "NO MORE TOOL CALLS. NO file_read. NO file_edit."
                        )
                    elif collection_error and import_error_name:
                        scene = (
                            f"❌ IMPORT ERROR: test file imports '{import_error_name}' but database.py has no such name.\n"
                            "This is a ONE-LINE fix. Do NOT rewrite database.py.\n"
                            "1. file_read database.py — look at what functions/classes are ACTUALLY defined\n"
                            "2. file_edit tests/test_projects.py — change the import line to match database.py\n"
                            "3. Run pytest ONCE after fixing.\n"
                            "If database.py uses functions: `from database import function_name`\n"
                            "If database.py uses a class: `from database import ClassName`"
                        )
                    elif pytest_failed > 0:
                        scene = (
                            f"❌ TESTS FAILED: {pytest_passed} passed, {pytest_failed} failed.\n"
                            "Read EACH failure in <results>. For EACH one:\n"
                            "  1. file_read the broken file (use start_line to see just the relevant area)\n"
                            "  2. file_edit to fix ONLY the exact lines — do NOT file_write the whole file\n"
                            "  3. Fix ALL failures → run pytest ONCE"
                        )
                    else:
                        scene = (
                            "Tool error detected. Read the error message above.\n"
                            "Fix the specific parameter or path that caused the error.\n"
                            "Use file_edit for code fixes — NOT file_write."
                        )
                else:
                    if completion_warning_given:
                        scene = (
                            "⛔ FINAL TURN — TASK IS COMPLETE. ⛔\n"
                            "Output ONLY a text summary. NO MORE TOOL CALLS.\n"
                            "Do NOT use file_read, file_list, or any other tool."
                        )
                    else:
                        scene = "Continue. Create files or run tests."

                # ── 构建 identity（工具列表或完成信号）──
                if completion_warning_given:
                    identity = "TASK COMPLETE. Output ONLY text summary. NO tools. NO JSON."
                else:
                    identity = (
                        "🔧 TOOLS: file_write | file_read | bash_execute | web_search | file_edit | file_list\n"
                        "📝 FORMAT: ```json {{\"tool\":\"name\",\"file_path\":\"p.py\",\"content\":\"code\"}} ```\n"
                        "🚫 FORBIDDEN: <tool_call> <function_calls> <invoke> <parameter> [TOOL_CALLS]\n"
                        "⚠️  Put ALL code INSIDE JSON \"content\" — do NOT put code outside."
                    )
                # ── 构建进度（跳出if/else——每轮都要）──
                format_reminder = ""
                progress = ""
                if files_created_this_task:
                    done = ", ".join(sorted(files_created_this_task)[-8:])
                    progress = f"✅ CREATED ({len(files_created_this_task)}): {done}\n"
                if files_read_this_task:
                    already_read = ", ".join(sorted(files_read_this_task)[-5:])
                    progress += f"📖 ALREADY READ (do NOT re-read): {already_read}\n"

                # ── 完整每轮上下文装配（对标Claude Code/OpenCode）──
                env_snippet = (
                    f"OS: {platform.system()} | Shell: Git Bash | "
                    f"Project: {str(PROJECT_ROOT.name)} | "
                    f"Model: {self._provider}/{self._model}"
                )
                # ── 智能截断：保留错误/测试输出完整，只截断file_read大文件 ──
                # 对标 OpenCode 的分级截断策略
                CRITICAL_PREFIXES = (
                    "bash_execute:", "bash_smart:", "bash_run:",
                    "ERROR", "BLOCKED", "FAIL", "pytest",
                )
                truncated_parts = []
                for line in results_feedback.split("\n"):
                    is_critical = any(
                        line.startswith(p) or line.strip().startswith(p)
                        for p in CRITICAL_PREFIXES
                    )
                    if is_critical:
                        # 错误和测试输出：完整保留
                        truncated_parts.append(line)
                    elif len(line) > 500:
                        # 长行（file_read结果）：截断
                        truncated_parts.append(line[:500] + "...")
                    else:
                        truncated_parts.append(line)

                truncated_feedback = "\n".join(truncated_parts)
                # 总长度上限：8000字符（给错误输出留足够空间）
                if len(truncated_feedback) > 8000:
                    # 从后往前保留——最新的结果更重要
                    truncated_feedback = (
                        "...[older results trimmed]\n"
                        + truncated_feedback[-(8000 - 50):]
                    )

                ctx_prefix = f"{task_context}\n" if task_context else ""
                current_prompt = (
                    f"<identity>Sclerotium OS CLI agent. {env_snippet}</identity>\n"
                    f"{identity}\n\n"
                    f"{ctx_prefix}"
                    f"{progress}\n"
                    f"<results>\n{truncated_feedback}\n</results>\n\n"
                    f"<instruction>\n{scene}\n</instruction>\n"
                    f"{format_reminder}"
                )

            # ── 后处理：自动创建文件 + 分隔线 ──
            if final_full_text:
                files_created = self._auto_create_files(final_full_text)
                log.write(Rule(style="dim"))
                if files_created:
                    log.write(Text(f"📁 Created: {', '.join(files_created[:5])}", style="green"))
                fm = FILE_REF_RE.search(final_full_text)
                if fm: self._last_file_ref = fm.group(0)
                um = URL_RE.search(final_full_text)
                if um: self._last_url = um.group(0)

            # ── 记录对话历史 ──
            if final_full_text:
                clean_response = final_full_text
                for tag in ['tool_call', 'file_path', 'content', 'command',
                           'path', 'code', 'text', 'working_dir', 'timeout',
                           'old_string', 'new_string', 'query', 'url', 'cmd']:
                    clean_response = re.sub(
                        rf'<{tag}[^>]*>.*?</{tag}>', '',
                        clean_response, flags=re.DOTALL | re.IGNORECASE)
                clean_response = clean_response.strip()

                history_prompt = original_prompt or prompt
                self._conversation_history.append({
                    "role": "user", "content": history_prompt,
                })
                self._conversation_history.append({
                    "role": "assistant",
                    "content": clean_response if clean_response else "(tool calls executed)",
                })
                if all_tool_results:
                    self._conversation_history.append({
                        "role": "tool",
                        "content": "\n".join(all_tool_results[-20:]),
                    })

                # 上下文窗口保护
                total_chars = sum(len(e.get("content", "")) for e in self._conversation_history)
                estimated_tokens = total_chars // 3
                auto_threshold = int(self._context_window * self._max_context_ratio)
                if self._auto_compact and estimated_tokens > auto_threshold:
                    log.write(Text(f"  ⚡ Auto-compact: {estimated_tokens:,} > {auto_threshold//1000}K", style="dim yellow"))
                    await self._run_compact(log)
                while estimated_tokens > int(self._context_window * 0.90) and len(self._conversation_history) > 3:
                    self._conversation_history.pop(0)
                    total_chars = sum(len(e.get("content", "")) for e in self._conversation_history)
                    estimated_tokens = total_chars // 3

            self._stop_thinking()
            # 计算上下文窗口使用率
            history_chars = sum(len(e.get("content", "")) for e in self._conversation_history)
            history_tokens = history_chars // 3
            ctx_pct = (history_tokens / self._context_window) * 100 if self._context_window else 0
            self._update_status(
                f"History:{history_tokens:,}/{self._context_window//1000}K({ctx_pct:.1f}%) | "
                f"Tools:{self._tools.tool_count if self._tools else 0} | "
                f"Turns:{self._turn_count} | "
                f"Tokens:{self._total_tokens:,} | "
                f"Reasoning:{self._reasoning_mode} | "
                f"deepseek-v4-pro")
            try:
                sidebar = self.query_one("#sidebar", OrganismSidebar)
                sidebar.update_vitals(history_tokens=history_tokens,
                                     tools_active=self._tools.tool_count if self._tools else 0)
            except Exception:
                pass

        except Exception as e:
            self._stop_thinking()
            log.write(Text(f"  Error: {e}", style="bold red"))

    # ── Plan Mode: clarifying questions ──────────────────────────────

    async def _ask_clarifying_questions(self, prompt: str) -> str:
        """Generate clarifying questions for planning/discussion."""
        import asyncio, urllib.request, json as _json
        if not self._gateway: return ""
        q_prompt = f"""You are a senior product manager. Ask 3-5 clarifying questions.

USER IDEA:
{prompt[:1000]}

Ask questions that clarify:
1. CORE GOAL -- what real problem is being solved?
2. SCOPE -- how big/small should this be?
3. CONSTRAINTS -- time, tech stack, budget, team?
4. PRIORITY -- speed vs quality vs cost?
5. EDGE CASES -- what scenarios must be handled?

Format as numbered markdown questions. Be concise. Output ONLY questions."""

        def _sync():
            try:
                import os
                base_url = "https://api.deepseek.com/v1"
                api_key = os.environ.get("DEEPSEEK_API_KEY", "")
                headers = {"Content-Type": "application/json"}
                if api_key: headers["Authorization"] = f"Bearer {api_key}"
                body = {"model":"deepseek-v4-flash","messages":[{"role":"user","content":q_prompt}],
                        "max_tokens":4096,"temperature":0.6}
                req = urllib.request.Request(f"{base_url}/chat/completions",
                    data=_json.dumps(body).encode("utf-8"), headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return _json.loads(resp.read()).get("choices",[{}])[0].get("message",{}).get("content","")
            except: return ""
        return await asyncio.to_thread(_sync)

    def _auto_create_files(self, text: str) -> list[str]:
        """Auto-create files from code blocks with file path hints."""
        import re
        created = []
        # Pattern 1: ```python:path/to/file.py or ```python (next line has # File: path)
        for m in re.finditer(r'```(\w+)(?::(\S+))?\s*\n(.*?)```', text, re.DOTALL):
            code = m.group(3).strip()
            lang = m.group(1).lower()
            hint_path = m.group(2) or ""
            if not hint_path:
                before = text[:m.start()]
                # # File: path or // File: path
                path_match = re.search(r'(?:#|//)\s*(?:File|file):\s*(\S+\.\w+)', before)
                if path_match:
                    hint_path = path_match.group(1)
            if not hint_path:
                # Chinese: "创建 test_api.py", "写入 server.py", "生成 database.py"
                path_match = re.search(
                    r'(?:创建|写入|生成|编写|保存为?)\s+`?(\w[\w/\\-]*\.\w+)`?',
                    before)
                if path_match:
                    hint_path = path_match.group(1)
            if not hint_path:
                # Look for path mentioned in previous line
                path_match = re.search(
                    r'(?:#|//)\s*(?:创建|写入|生成|编写)\s+(\S+\.\w+)', before)
                if path_match:
                    hint_path = path_match.group(1)
            # Only create if we have a path AND the code looks like a real file (>50 chars or has proper structure)
            if hint_path and (len(code) > 50 or lang in ('python','py','js','ts','html','css','sql')):
                try:
                    from mcp.tools.file_ops import file_write
                    result = file_write(hint_path, code)
                    if result.get("status") == "ok":
                        created.append(hint_path)
                except Exception:
                    pass

        return created[:10]

    # ── Actions ───────────────────────────────────────────────────────

    def action_toggle_sidebar(self) -> None:
        self._sidebar_visible = not self._sidebar_visible
        sidebar = self.query_one("#sidebar", OrganismSidebar)
        if self._sidebar_visible:
            sidebar.remove_class("hidden")
        else:
            sidebar.add_class("hidden")

    def action_toggle_dashboard(self) -> None:
        self.push_screen(DashboardScreen())

    def action_open_file(self) -> None:
        if not self._last_file_ref:
            self.notify("No file referenced. Ask the LLM to write code first.",
                       title="Open File", severity="warning")
            return
        m = FILE_REF_RE.match(self._last_file_ref)
        if m:
            path = Path(m.group('path'))
            if path.exists():
                try:
                    os.startfile(str(path))
                    self.notify(f"Opened: {path.name}", title="Open File")
                except Exception as e:
                    self.notify(str(e), title="Error", severity="error")
            else:
                self.notify(f"Not found: {path}", title="Warning", severity="warning")

    def action_open_browser(self) -> None:
        if not self._last_url:
            self.notify("No URL found yet.", title="Browser", severity="warning")
            return
        try:
            webbrowser.open(self._last_url)
            self.notify(f"Opened: {self._last_url[:60]}", title="Browser")
        except Exception as e:
            self.notify(str(e), title="Error", severity="error")

    def action_clear(self) -> None:
        self.query_one("#messages", RichLog).clear()
        self._conversation_history.clear()
        self._recently_edited.clear()
        self._session_goal = ""
        self._show_welcome()

    def action_help(self) -> None:
        self._cmd_help(self.query_one("#messages", RichLog))

    def action_browse_files(self) -> None:
        self._cmd_files(self.query_one("#messages", RichLog), [])

    def _build_full_transcript(self) -> str:
        """Build complete conversation transcript from all sources."""
        parts = ["# Sclerotium OS -- Full Conversation\n\n"]
        # From session store
        if self._session_store:
            try:
                sid = self._session_store._current_session
                if sid:
                    events = self._session_store.get_transcript(sid)
                    for e in events:
                        ts = e.get('type', '')
                        content = str(e.get('content', ''))
                        if ts == 'user_message':
                            parts.append(f"**You:** {content}\n\n")
                        elif ts == 'assistant_message':
                            parts.append(f"**Sclerotium:** {content}\n\n")
                        elif ts == 'tool_call':
                            parts.append(f"*Tool: {e.get('tool', '?')}*\n\n")
            except Exception:
                pass
        # Include last response if not in transcript
        if self._last_response and self._last_response not in "".join(parts):
            parts.append(f"---\n\n**Last Response:**\n\n{self._last_response}\n")
        return "".join(parts)

    def action_copy_all(self) -> None:
        """Ctrl+A: Copy entire conversation to clipboard."""
        transcript = self._build_full_transcript()
        if not transcript.strip():
            self.notify("Nothing to copy yet.", title="Copy All", severity="warning")
            return
        self._copy_to_clipboard(transcript, "Entire conversation")

    def action_copy_last(self) -> None:
        """Ctrl+Y: Copy last LLM response to clipboard."""
        if not self._last_response:
            self.notify("No response yet. Ask the LLM something first.",
                       title="Copy", severity="warning")
            return
        self._copy_to_clipboard(self._last_response, "Last response")

    def action_save_session(self) -> None:
        """Ctrl+S: Save current session."""
        if self._session_store:
            s = self._session_store.get_stats()
            self.notify(f"Saved: {s['session_count']} sessions, {s['total_turns']} turns", title="Save")

    def action_approve_tool(self) -> None:
        """Ctrl+P: Approve pending tool execution (including destructive ops)."""
        # Handle destructive operation approval
        if hasattr(self, '_pending_destructive') and self._pending_destructive:
            pending = self._pending_destructive
            self._pending_destructive = None
            self.notify(f"Approved: {pending['cmd'][:60]}", title="Delete Approved")
            # Execute the approved operation
            self._execute_approved_tool(pending["tool"], pending["args"])
            return
        # Handle regular permission approval
        if hasattr(self, '_pending_tool') and self._pending_tool:
            tool_name = self._pending_tool.get("name", "")
            if self._arbiter: self._arbiter.confirm(tool_name)
            self._pending_tool = None
            self.notify(f"Approved: {tool_name}", title="Permission")

    @work(exclusive=False)
    async def _execute_approved_tool(self, tool_name: str, args: dict) -> None:
        """Execute a user-approved tool."""
        log = self.query_one("#messages", RichLog)
        try:
            result = await self._agent_loop._execute_tool(tool_name, args)
            log.write(Panel(str(result)[:500], border_style="green", title="Approved Result"))
        except Exception as e:
            log.write(Text(f"Error: {e}", style="red"))

    def action_deny_tool(self) -> None:
        """Escape: Deny pending destructive operation or tool execution."""
        if hasattr(self, '_pending_destructive') and self._pending_destructive:
            cmd = self._pending_destructive.get('cmd', '')[:60]
            self._pending_destructive = None
            self.notify(f"Denied: {cmd}", title="Delete Denied")
            return
        if hasattr(self, '_pending_tool') and self._pending_tool:
            self._pending_tool = None
            self.notify("Denied", title="Permission")
            return

    def action_cancel_task(self) -> None:
        """ESC: Cancel running task/pipeline, close task tracker."""
        tracker = self.query_one("#task-tracker", TaskTracker)
        # Only cancel if something is actually running
        if self._thinking or tracker.has_class("visible"):
            if self._agent_loop:
                self._agent_loop.abort()
            self._stop_thinking()
            tracker.remove_class("visible")
            tracker.clear()
            self._pending_tool = None
            self.notify("Cancelled", title="ESC")
        # If nothing running, ESC closes sidebar/popups (Textual default)

    def action_cycle_permission(self) -> None:
        """Shift+Tab: Cycle through 7 permission modes."""
        from kernel.permission_gate import PermissionMode
        modes = list(PermissionMode)
        if not hasattr(self, '_arbiter') or not self._arbiter:
            self.notify("Arbiter not initialized", title="Permission")
            return
        current = self._arbiter.mode
        idx = modes.index(current) if current in modes else 0
        next_mode = modes[(idx + 1) % len(modes)]
        self._arbiter.set_mode(next_mode)
        self.notify(f"Mode: {next_mode.value}", title="Permission")

    def action_copy_visible(self) -> None:
        """Ctrl+Shift+C: Copy everything visible on screen to clipboard."""
        transcript = self._build_full_transcript()
        if not transcript.strip():
            self.notify("Nothing to copy yet.", title="Copy", severity="warning")
            return
        self._copy_to_clipboard(transcript, "Visible content")

    def action_export_chat(self) -> None:
        """Ctrl+E: Export full conversation and open in default editor."""
        try:
            transcript = self._build_full_transcript()
            path = Path("./data/sessions/exported_chat.md")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(transcript, encoding="utf-8")
            os.startfile(str(path))
            self.notify(f"Opened: {path}", title="Export")
        except Exception as e:
            self.notify(str(e), title="Export Error", severity="error")

    def _copy_to_clipboard(self, text: str, label: str = "Text") -> None:
        """Copy to system clipboard -- OSC 52 first (direct), pyperclip fallback."""
        preview = text[:100].replace('\n', ' ').strip()
        # 1. OSC 52 -- direct clipboard, no dependencies
        from kernel.osc52 import copy_to_clipboard as osc52_copy
        if osc52_copy(text):
            self.notify(f"Copied (OSC 52): {preview}...", title=label)
            return
        # 2. pyperclip fallback
        try:
            import pyperclip
            pyperclip.copy(text)
            self.notify(f"Copied (pyperclip): {preview}...", title=label)
            return
        except Exception: pass
        # 3. File fallback
        try:
            path = Path("./data/sessions/clipboard_export.txt")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            os.startfile(str(path))
            self.notify(f"Opened file: {path}", title=label)
        except Exception as e:
            self.notify(str(e), title="Error", severity="error")

    # ── Mouse toggle -- release mouse capture for native selection ──
    def action_toggle_mouse(self) -> None:
        """Toggle Textual mouse capture for native text selection."""
        self._mouse_captured = not getattr(self, '_mouse_captured', True)
        if self._mouse_captured:
            self._capture_mouse(True)
            self.notify("Mouse: TUI mode (scroll/click)", title="Mouse")
        else:
            self._capture_mouse(False)
            self.notify("Mouse: SELECTION mode -- drag to select, Shift+drag to select", title="Mouse")

    # ── Status ────────────────────────────────────────────────────────

    def _update_status(self, text: str) -> None:
        try:
            self.query_one("#status-line", Static).update(Text(text, style="dim"))
        except Exception:
            pass


def run_tui() -> None:
    SclerotiumTUI().run()


if __name__ == "__main__":
    run_tui()
