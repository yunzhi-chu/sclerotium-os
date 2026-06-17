"""Sclerotium MCP Tools — 143 tools across 23 categories."""
from mcp.tools.system import register_system_tools
from mcp.tools.advanced import register_advanced_tools
from mcp.tools.sovereign import register_sovereign_tools
from mcp.tools.genesis import register_genesis_tools
from mcp.tools.cosmic import register_cosmic_tools
from mcp.tools.omega import register_omega_tools
from mcp.tools.innovation import register_innovation_tools
from mcp.tools.apotheosis import register_apotheosis_tools
from mcp.tools.cache_engine import register_cache_tools
from mcp.tools.evolution_bridge import register_evolution_bridge_tools
from mcp.tools.benchmark import register_benchmark_tools
from mcp.tools.evolution import register_evolution_tools
from mcp.tools.memory import register_memory_tools
from mcp.tools.sandbox import register_sandbox_tools
from mcp.tools.skills import register_skills_tools
from mcp.tools.code_analysis import register_code_analysis_tools
from mcp.tools.im import register_im_tools
from mcp.tools.desktop import register_desktop_tools
from mcp.tools.scheduler_mcp import register_scheduler_mcp_tools
from mcp.tools.files import register_files_tools
from mcp.tools.info import register_info_tools
from mcp.tools.mode import register_mode_tools
from mcp.tools.gateways import register_gateway_tools

__all__ = [
    "register_system_tools", "register_evolution_tools",
    "register_memory_tools", "register_sandbox_tools",
    "register_skills_tools", "register_code_analysis_tools",
    "register_im_tools", "register_desktop_tools",
    "register_scheduler_mcp_tools", "register_files_tools",
    "register_info_tools", "register_mode_tools",
    "register_gateway_tools", "register_benchmark_tools",
]
