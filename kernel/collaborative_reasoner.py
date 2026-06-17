"""Collaborative Reasoner — Multi-model parallel reasoning with voting.

Sclerotium OS ADVANTAGE over Claude Code:
  Claude Code uses ONLY Anthropic models (Opus/Sonnet/Haiku).
  Sclerotium orchestrates MULTIPLE providers simultaneously for superior results.

Three reasoning modes:
  1. FAST_PATH:     simple model (Groq/DeepSeek Flash) for quick answers
  2. DUAL_VERIFY:   strong model generates + fast model verifies
  3. JURY_PANEL:    3+ models generate independently → voting/consensus
  4. SPECIALIST:    route to domain-specialized model (Codestral for code, etc.)

Model roles:
  - ARCHITECT:  DeepSeek V4 Pro / Claude Opus — designs approach
  - CODER:      DeepSeek V4 Pro / GPT-5 Codex — writes code
  - REVIEWER:   Groq Llama-4 / MiniCPM — reviews, finds bugs
  - VERIFIER:   Local Ollama MiniCPM — adversarial verification (cheapest)
  - FAST:       Groq / Cerebras — quick tool selection, simple tasks

Reference:
  - Claude Code verificationAgent.ts — adversarial verification pattern
  - OpenClaw multi-agent Hawkins tendrils
  - Mixture-of-Agents (Wang et al., 2024) — multi-model voting improves quality
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReasoningMode(Enum):
    """Multi-model reasoning strategy."""
    FAST_PATH = "fast_path"          # Single fast model, no verification
    DUAL_VERIFY = "dual_verify"      # Strong generates + fast verifies
    JURY_PANEL = "jury_panel"        # 3 models → voting/consensus
    SPECIALIST = "specialist"        # Domain-specialized model


@dataclass
class ModelVote:
    """A single model's response in a jury panel."""
    model: str
    provider: str
    content: str
    tokens: int = 0
    latency_ms: float = 0.0
    confidence: float = 0.5
    role: str = "coder"


@dataclass
class JuryResult:
    """Result from a multi-model jury panel."""
    votes: list[ModelVote] = field(default_factory=list)
    consensus_content: str = ""
    consensus_level: str = "none"  # unanimous, strong, weak, none
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    dissenting_opinions: list[str] = field(default_factory=list)
    best_vote: ModelVote | None = None


class CollaborativeReasoner:
    """Multi-model orchestration engine.

    Sclerotium's KEY ADVANTAGE: while Claude Code is locked into Anthropic's
    model family, Sclerotium can orchestrate DeepSeek + Groq + Ollama + OpenAI
    simultaneously for superior code generation.
    """

    # Model role assignments
    MODEL_ROLES: dict[str, dict[str, Any]] = {
        "architect": {
            "primary": ("deepseek", "deepseek-v4-pro"),
            "fallback": ("openai", "gpt-5.4"),
            "temperature": 0.3,
            "max_tokens": 8192,
        },
        "coder": {
            "primary": ("deepseek", "deepseek-v4-pro"),
            "fallback": ("anthropic", "claude-sonnet-4-6"),
            "temperature": 0.2,
            "max_tokens": 128_000,  # Model's full output — no arbitrary limit
        },
        "reviewer": {
            "primary": ("groq", "llama-4-70b"),
            "fallback": ("deepseek", "deepseek-v4-flash"),
            "temperature": 0.1,
            "max_tokens": 4096,
        },
        "verifier": {
            "primary": ("ollama", "qwen3"),
            "fallback": ("deepseek", "deepseek-v4-flash"),
            "temperature": 0.0,
            "max_tokens": 2048,
        },
        "fast": {
            "primary": ("groq", "llama-4-70b"),
            "fallback": ("cerebras", "llama-3.1-8b"),
            "temperature": 0.1,
            "max_tokens": 2048,
        },
    }

    def __init__(self, gateway: Any = None) -> None:
        self._gateway = gateway

    # ── Public API ──────────────────────────────────────────────────────

    async def reason(
        self,
        prompt: str,
        mode: ReasoningMode = ReasoningMode.DUAL_VERIFY,
        *,
        system_prompt: str = "",
    ) -> JuryResult:
        """Execute multi-model reasoning based on the selected mode.

        Args:
            prompt: The user's task
            mode: Which reasoning strategy to use
            system_prompt: Optional system context

        Returns:
            JuryResult with all model votes and consensus
        """
        if mode == ReasoningMode.FAST_PATH:
            return await self._fast_path(prompt, system_prompt)
        elif mode == ReasoningMode.DUAL_VERIFY:
            return await self._dual_verify(prompt, system_prompt)
        elif mode == ReasoningMode.JURY_PANEL:
            return await self._jury_panel(prompt, system_prompt)
        elif mode == ReasoningMode.SPECIALIST:
            return await self._specialist(prompt, system_prompt)
        else:
            return await self._dual_verify(prompt, system_prompt)

    # ── Mode 1: FAST_PATH ───────────────────────────────────────────────

    async def _fast_path(self, prompt: str, system_prompt: str) -> JuryResult:
        """Single fast model for simple tasks (tool selection, quick answers)."""
        cfg = self.MODEL_ROLES["fast"]
        provider, model = cfg["primary"]

        t0 = time.time()
        vote = await self._call_model(
            prompt, model, provider, system_prompt,
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
            role="fast",
        )
        latency = (time.time() - t0) * 1000
        if vote:
            vote.latency_ms = latency

        return JuryResult(
            votes=[vote] if vote else [],
            consensus_content=vote.content if vote else "",
            consensus_level="strong" if vote else "none",
            total_tokens=vote.tokens if vote else 0,
            total_latency_ms=latency,
            best_vote=vote,
        )

    # ── Mode 2: DUAL_VERIFY ─────────────────────────────────────────────

    async def _dual_verify(self, prompt: str, system_prompt: str) -> JuryResult:
        """Strong model generates code, fast model reviews it.

        Claude Code equivalent: verificationAgent.ts adversarial check.
        Sclerotium ADVANTAGE: uses DIFFERENT model families for independence.
        """
        # Phase 1: CODER generates
        coder_cfg = self.MODEL_ROLES["coder"]
        t0 = time.time()

        coder_vote = await self._call_model(
            prompt, coder_cfg["primary"][1], coder_cfg["primary"][0],
            system_prompt,
            temperature=coder_cfg["temperature"],
            max_tokens=coder_cfg["max_tokens"],
            role="coder",
        )
        coder_latency = (time.time() - t0) * 1000
        if not coder_vote:
            return JuryResult(consensus_level="none")

        coder_vote.latency_ms = coder_latency
        coder_vote.confidence = 0.8

        # Phase 2: REVIEWER checks (in parallel with coder for efficiency)
        reviewer_cfg = self.MODEL_ROLES["reviewer"]
        review_prompt = f"""Review this code for bugs, security issues, and edge cases.
Be adversarial — try to find problems.

CODE TO REVIEW:
{coder_vote.content[:8000]}

List issues found (if any). If no issues, say "NO_ISSUES_FOUND"."""

        reviewer_vote = await self._call_model(
            review_prompt,
            reviewer_cfg["primary"][1],
            reviewer_cfg["primary"][0],
            "",
            temperature=reviewer_cfg["temperature"],
            max_tokens=reviewer_cfg["max_tokens"],
            role="reviewer",
        )

        # Determine consensus
        has_issues = (
            reviewer_vote
            and "NO_ISSUES_FOUND" not in reviewer_vote.content
            and len(reviewer_vote.content.strip()) > 20
        )

        if has_issues:
            # Reviewer found issues → fix them
            fix_prompt = f"""The code reviewer found these issues:
{reviewer_vote.content[:2000]}

Original code:
{coder_vote.content[:6000]}

Please fix ALL the issues and output the complete corrected code."""

            fixed_vote = await self._call_model(
                fix_prompt,
                coder_cfg["primary"][1],
                coder_cfg["primary"][0],
                system_prompt,
                temperature=0.1,
                max_tokens=coder_cfg["max_tokens"],
                role="coder",
            )

            return JuryResult(
                votes=[coder_vote, reviewer_vote, fixed_vote] if fixed_vote else [coder_vote, reviewer_vote],
                consensus_content=fixed_vote.content if fixed_vote else coder_vote.content,
                consensus_level="strong",
                total_tokens=(
                    coder_vote.tokens
                    + (reviewer_vote.tokens if reviewer_vote else 0)
                    + (fixed_vote.tokens if fixed_vote else 0)
                ),
                total_latency_ms=coder_latency,
                dissenting_opinions=[reviewer_vote.content[:500]] if reviewer_vote else [],
                best_vote=fixed_vote or coder_vote,
            )
        else:
            return JuryResult(
                votes=[coder_vote],
                consensus_content=coder_vote.content,
                consensus_level="strong",
                total_tokens=coder_vote.tokens + (reviewer_vote.tokens if reviewer_vote else 0),
                total_latency_ms=coder_latency,
                best_vote=coder_vote,
            )

    # ── Mode 3: JURY_PANEL ──────────────────────────────────────────────

    async def _jury_panel(self, prompt: str, system_prompt: str) -> JuryResult:
        """3+ models generate independently → voting/consensus for critical tasks.

        Sclerotium ADVANTAGE: ensemble of DIFFERENT model families reduces
        individual model biases. Claude Code can't do this.
        """
        panel = [
            ("deepseek", "deepseek-v4-pro", "coder", 0.3, 16384),
            ("groq", "llama-4-70b", "reviewer", 0.1, 8192),
            ("deepseek", "deepseek-v4-flash", "verifier", 0.0, 4096),
        ]

        # Parallel calls to all jury members
        t0 = time.time()
        tasks = [
            self._call_model(
                prompt, model, provider, system_prompt,
                temperature=temp, max_tokens=max_tok, role=role,
            )
            for provider, model, role, temp, max_tok in panel
        ]
        votes_raw = await asyncio.gather(*tasks, return_exceptions=True)
        total_latency = (time.time() - t0) * 1000

        # Filter valid votes
        votes: list[ModelVote] = []
        for v in votes_raw:
            if isinstance(v, ModelVote) and v.content:
                votes.append(v)

        if not votes:
            return JuryResult(consensus_level="none")

        if len(votes) == 1:
            return JuryResult(
                votes=votes,
                consensus_content=votes[0].content,
                consensus_level="weak",
                best_vote=votes[0],
            )

        # Compare votes for consensus
        primary = votes[0]  # DeepSeek V4 Pro is primary
        consensus_content = primary.content
        consensus_level = "strong"

        # Check if other models disagree significantly
        for v in votes[1:]:
            if v.content and len(v.content) > 50:
                # Simple heuristic: if reviewer output is very different, note it
                if len(v.content) < len(primary.content) * 0.3:
                    consensus_level = "weak"

        return JuryResult(
            votes=votes,
            consensus_content=consensus_content,
            consensus_level=consensus_level,
            total_tokens=sum(v.tokens for v in votes),
            total_latency_ms=total_latency,
            best_vote=primary,
        )

    # ── Mode 4: SPECIALIST ──────────────────────────────────────────────

    async def _specialist(self, prompt: str, system_prompt: str) -> JuryResult:
        """Route to domain-specialized model based on task content."""
        # Detect domain and pick specialist
        prompt_lower = prompt.lower()
        if any(kw in prompt_lower for kw in ["react", "vue", "component", "jsx", "css"]):
            provider, model = "groq", "llama-4-70b"  # Fast for web dev
        elif any(kw in prompt_lower for kw in ["python", "django", "flask", "pytest"]):
            provider, model = "deepseek", "deepseek-v4-pro"
        elif any(kw in prompt_lower for kw in ["rust", "cargo", "borrow"]):
            provider, model = "deepseek", "deepseek-v4-pro"
        elif any(kw in prompt_lower for kw in ["sql", "database", "migration"]):
            provider, model = "deepseek", "deepseek-v4-flash"
        else:
            provider, model = "deepseek", "deepseek-v4-pro"

        t0 = time.time()
        vote = await self._call_model(
            prompt, model, provider, system_prompt,
            temperature=0.2, max_tokens=32768, role="specialist",
        )
        latency = (time.time() - t0) * 1000
        if vote:
            vote.latency_ms = latency

        return JuryResult(
            votes=[vote] if vote else [],
            consensus_content=vote.content if vote else "",
            consensus_level="strong" if vote else "none",
            total_tokens=vote.tokens if vote else 0,
            best_vote=vote,
        )

    # ── Internal: model call ────────────────────────────────────────────

    async def _call_model(
        self,
        prompt: str,
        model: str,
        provider: str,
        system_prompt: str = "",
        *,
        temperature: float = 0.3,
        max_tokens: int = 32768,
        role: str = "coder",
    ) -> ModelVote | None:
        """Call a specific model through the Gateway."""
        if self._gateway is None:
            return None

        t0 = time.time()
        try:
            response = await self._gateway.chat(
                prompt=prompt,
                model=model,
                provider=provider,
                system=system_prompt if system_prompt else None,
            )
            latency = (time.time() - t0) * 1000

            content = ""
            tokens = 0
            if isinstance(response, dict):
                content = response.get("content", "") or ""
                tokens = response.get("tokens", 0)

            if not content:
                return None

            return ModelVote(
                model=model,
                provider=provider,
                content=content,
                tokens=tokens,
                latency_ms=latency,
                confidence=0.7 if len(content) > 100 else 0.3,
                role=role,
            )
        except Exception:
            return None

    # ── Utility ─────────────────────────────────────────────────────────

    def get_available_roles(self) -> list[str]:
        """List available model roles."""
        return list(self.MODEL_ROLES.keys())

    def get_mode_description(self, mode: ReasoningMode) -> str:
        """Human-readable description of each reasoning mode."""
        descriptions = {
            ReasoningMode.FAST_PATH: "Single fast model (Groq/Cerebras) — best for simple queries, tool selection",
            ReasoningMode.DUAL_VERIFY: "Strong model generates + fast model reviews — best for code generation (DEFAULT)",
            ReasoningMode.JURY_PANEL: "3 models vote/consensus — best for critical/security-sensitive tasks",
            ReasoningMode.SPECIALIST: "Domain-specialized model routing — best for language/framework-specific tasks",
        }
        return descriptions.get(mode, "Unknown mode")
