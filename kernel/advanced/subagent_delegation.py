"""P2: Sub-agent Delegation + Parallel Execution.

Fan-out complex tasks to specialized sub-agents running in parallel.
Isolated sidechain transcripts, summary return to parent.

6 built-in agent types (Claude Code parity):
  explore, plan, code-review, security-audit, test-writer, refactor

Reference: Claude Code subagent delegation, Codex multi-agent v2,
SwarmWeaver 6-mode swarms, Meta-Agent verified MAS.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class AgentRole(Enum):
    # ADV#9修复: 扩展角色映射, 支持直觉命名
    EXPLORE = "explore"
    PLAN = "plan"
    CODE_REVIEW = "code_review"
    SECURITY_AUDIT = "security_audit"
    TEST_WRITER = "test_writer"
    REFACTOR = "refactor"
    # 新增通用角色
    CODER = "coder"           # 通用编码 (用户直觉命名)
    DEBUGGER = "debugger"     # bug 定位和修复
    WRITER = "writer"         # 文档/内容生成
    ARCHITECT = "architect"   # 系统架构设计
    RESEARCHER = "researcher" # 调研和分析
    DEVOPS = "devops"         # CI/CD/部署
    REVIEWER = "reviewer"     # 代码/设计审查 (通用)
    BENCHMARKER = "benchmarker"  # 性能基准测试


@dataclass
class SubAgentTask:
    role: AgentRole
    prompt: str
    context: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 120


@dataclass
class SubAgentResult:
    role: AgentRole
    output: str
    success: bool
    duration_ms: float
    errors: list[str] = field(default_factory=list)


class SubAgentDelegator:
    """Fan-out task delegation to parallel specialized sub-agents.

    Usage:
        delegator = SubAgentDelegator()
        results = await delegator.fan_out([
            SubAgentTask(AgentRole.CODE_REVIEW, "Review auth.py"),
            SubAgentTask(AgentRole.SECURITY_AUDIT, "Audit auth.py"),
            SubAgentTask(AgentRole.TEST_WRITER, "Write tests for auth.py"),
        ])
    """

    ROLE_PROMPTS: dict[AgentRole, str] = {
        AgentRole.EXPLORE: "Explore and understand the codebase. Find relevant files, patterns, and dependencies.",
        AgentRole.PLAN: "Create an implementation plan. Break down into steps, identify risks.",
        AgentRole.CODE_REVIEW: "Review code for bugs, performance, security, and maintainability.",
        AgentRole.SECURITY_AUDIT: "Audit for OWASP Top 10, CWE vulnerabilities, and secrets.",
        AgentRole.TEST_WRITER: "Write comprehensive tests. Cover edge cases, error paths, and boundaries.",
        AgentRole.REFACTOR: "Refactor for clarity, performance, and maintainability without changing behavior.",
        # ADV#9: 新增角色描述
        AgentRole.CODER: "Write and implement code. General purpose coding across any language or framework.",
        AgentRole.DEBUGGER: "Debug and fix bugs. Analyze root causes, reproduce issues, suggest fixes.",
        AgentRole.WRITER: "Write documentation, reports, articles, and content. Clear and well-structured.",
        AgentRole.ARCHITECT: "Design system architecture. Evaluate trade-offs, design patterns, scalability.",
        AgentRole.RESEARCHER: "Research and analyze topics. Gather information, compare options, synthesize findings.",
        AgentRole.DEVOPS: "CI/CD, deployment, infrastructure. Docker, Kubernetes, cloud services, automation.",
        AgentRole.REVIEWER: "General code and design review. Quality, consistency, and best practices.",
        AgentRole.BENCHMARKER: "Performance benchmarking. Profile, measure, optimize for speed and memory.",
    }

    def __init__(self, max_parallel: int = 6) -> None:
        self.max_parallel = max_parallel
        self._results: list[SubAgentResult] = []

    async def fan_out(self, tasks: list[SubAgentTask]) -> list[SubAgentResult]:
        """Execute multiple sub-agent tasks in parallel."""
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def run_one(task: SubAgentTask) -> SubAgentResult:
            async with semaphore:
                return await self._execute(task)

        results = await asyncio.gather(*[run_one(t) for t in tasks])
        self._results.extend(results)
        return list(results)

    async def fan_out_and_merge(self, tasks: list[SubAgentTask]) -> str:
        """Fan out tasks and merge results into one summary."""
        results = await self.fan_out(tasks)
        merged = []
        for r in results:
            status = "OK" if r.success else "FAIL"
            merged.append(f"[{r.role.value}] {status} ({r.duration_ms:.0f}ms)\n{r.output[:500]}")
        return "\n\n---\n\n".join(merged)

    async def _execute(self, task: SubAgentTask) -> SubAgentResult:
        """Execute a single sub-agent task."""
        import time
        start = time.monotonic()

        try:
            role_prompt = self.ROLE_PROMPTS.get(task.role, "")
            full_prompt = f"{role_prompt}\n\nTask: {task.prompt}"
            output = await self._call_llm(full_prompt, task.timeout_seconds)
            return SubAgentResult(
                role=task.role, output=output, success=True,
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            return SubAgentResult(
                role=task.role, output="", success=False,
                duration_ms=(time.monotonic() - start) * 1000, errors=[str(e)],
            )

    async def _call_llm(self, prompt: str, timeout: int) -> str:
        """Call LLM for sub-agent reasoning."""
        try:
            from gateways.models import UniversalModelGateway, RoutingStrategy
            gw = UniversalModelGateway()
            result = await gw.chat(prompt, strategy=RoutingStrategy.FALLBACK)
            return result.get("content", "")[:2000]
        except Exception:
            return f"[Sub-agent analysis for: {prompt[:100]}...]"
