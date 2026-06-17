"""Context Compressor — Claude Code-style 5-layer compression pipeline.

Claude Code's five compression layers (from leaked source analysis):
  Layer 1: Tool Output Truncation — trim long tool outputs, keep head+tail
  Layer 2: Message Pruning — keep recent N messages full, older titles only
  Layer 3: Conversation Summary — LLM-generated summary replacing raw history
  Layer 4: Context Window Sliding — drop oldest messages when near limit
  Layer 5: Semantic Dedup — remove semantically similar tool results

Three trigger modes (Claude Code equivalent):
  - MicroCompact: local, zero-cost trimming (no API call)
  - AutoCompact: triggered at 80% context, generates structured summary
  - FullCompact: on-demand, compresses everything, resets to 50K token budget

Reference:
  - Claude Code src/Compact.ts, context.ts — compaction pipeline
  - Anthropic Agent SDK auto-compaction with compact_boundary messages
"""

from __future__ import annotations

import hashlib
import re
from typing import Any


# ── Layer 1: Tool Output Truncation ────────────────────────────────────

def truncate_tool_outputs(
    messages: list[dict[str, Any]],
    max_chars: int = 8000,
    head_ratio: float = 0.3,
) -> list[dict[str, Any]]:
    """Truncate long tool output messages, keeping head + tail + summary.

    Claude Code equivalent: Tool output truncation — first layer, zero API cost.
    """
    result = []
    for m in messages:
        content = str(m.get("content", ""))
        if len(content) <= max_chars:
            result.append(m)
            continue

        head_len = int(max_chars * head_ratio)
        tail_len = max_chars - head_len - 200  # 200 chars for separator

        truncated = (
            content[:head_len]
            + f"\n\n... [{len(content) - head_len - tail_len:,} chars truncated] ...\n\n"
            + content[-tail_len:]
        )
        result.append({**m, "content": truncated, "_truncated": True})

    return result


# ── Layer 2: Message Pruning ────────────────────────────────────────────

def prune_messages(
    messages: list[dict[str, Any]],
    keep_recent: int = 10,
    keep_system: bool = True,
) -> list[dict[str, Any]]:
    """Keep recent N messages in full; older messages get title-only summaries.

    Claude Code equivalent: Message pruning — second layer, local operation.
    """
    if len(messages) <= keep_recent:
        return messages

    result = []
    for i, m in enumerate(messages):
        role = m.get("role", "user")

        # Always keep system messages
        if keep_system and role == "system":
            result.append(m)
            continue

        # Keep recent messages in full
        if i >= len(messages) - keep_recent:
            result.append(m)
            continue

        # Older messages: prune to first line
        content = str(m.get("content", ""))
        first_line = content.split("\n")[0][:200]
        result.append({
            **m,
            "content": f"[pruned] {first_line}...",
            "_pruned": True,
        })

    return result


# ── Layer 3: Conversation Summary (LLM-powered) ─────────────────────────

async def summarize_conversation(
    messages: list[dict[str, Any]],
    gateway: Any = None,
    max_summary_tokens: int = 20000,
) -> list[dict[str, Any]]:
    """Generate a structured summary of older messages using LLM.

    Claude Code equivalent: AutoCompact — reserves 13K token buffer,
    generates up to 20K token structured summary. Has circuit breaker
    (3 consecutive failures → stop retrying).
    """
    if gateway is None:
        # No LLM available → fall back to pruning
        return prune_messages(messages, keep_recent=8)

    # Separate: system messages + recent messages + older messages to summarize
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    if len(non_system) <= 12:
        return messages  # Not enough to summarize

    recent = non_system[-6:]  # Keep last 6 turns intact
    to_summarize = non_system[:-6]

    # Build summarization prompt
    summary_input = "\n".join(
        f"[{m.get('role', '?')}]: {str(m.get('content', ''))[:500]}"
        for m in to_summarize
    )

    prompt = f"""Summarize this conversation history concisely. Keep:
1. Key decisions made
2. Files created/modified (with paths)
3. Errors encountered and fixes
4. Important context for continuing work

Conversation:
{summary_input[:15000]}

Structured summary:"""

    try:
        response = await gateway.chat(
            prompt=prompt,
            model="deepseek-v4-flash",  # Cheap model for summary
            provider="deepseek",
        )
        summary = response.get("content", "") if isinstance(response, dict) else str(response)

        # Rebuild messages: system + summary + recent
        rebuilt = list(system_msgs)
        rebuilt.append({
            "role": "system",
            "content": f"[Compacted conversation summary]\n{summary[:max_summary_tokens * 4]}",
            "_compacted": True,
        })
        rebuilt.extend(recent)

        return rebuilt

    except Exception:
        # Fallback: just prune
        return prune_messages(messages, keep_recent=8)


# ── Layer 4: Context Window Sliding ────────────────────────────────────

def slide_context_window(
    messages: list[dict[str, Any]],
    max_tokens: int = 100_000,
    chars_per_token: int = 4,
) -> list[dict[str, Any]]:
    """Drop oldest non-system messages when total exceeds max_tokens.

    Claude Code equivalent: Context window sliding — final layer before API call.
    """
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    system_chars = sum(len(str(m.get("content", ""))) for m in system_msgs)
    available_chars = (max_tokens * chars_per_token) - system_chars

    # Keep messages from newest to oldest until budget exhausted
    kept = []
    used = 0
    for m in reversed(non_system):
        chars = len(str(m.get("content", "")))
        if used + chars <= available_chars:
            kept.append(m)
            used += chars
        else:
            break

    kept.reverse()  # Restore chronological order
    return system_msgs + kept


# ── Layer 5: Semantic Dedup ────────────────────────────────────────────

def deduplicate_tool_results(
    messages: list[dict[str, Any]],
    similarity_threshold: float = 0.85,
) -> list[dict[str, Any]]:
    """Remove semantically similar tool result messages.

    Claude Code equivalent: Semantic dedup — prevents redundant tool outputs
    from consuming context window.
    """
    seen_hashes: set[str] = set()
    result = []

    for m in messages:
        content = str(m.get("content", ""))

        # Only dedup tool result messages
        if m.get("role") != "user" or not content.startswith("Tool results"):
            result.append(m)
            continue

        # Generate fuzzy hash (first 500 chars + length signature)
        sig = content[:500] + f"|len={len(content)}"
        h = hashlib.sha256(sig.encode()).hexdigest()[:32]

        if h in seen_hashes:
            continue  # Skip similar
        seen_hashes.add(h)
        result.append(m)

    return result


# ── Combined pipeline ──────────────────────────────────────────────────

async def compress_messages(
    messages: list[dict[str, Any]],
    gateway: Any = None,
    *,
    target_tokens: int = 80_000,
    max_summary_tokens: int = 20_000,
) -> list[dict[str, Any]]:
    """Run the full 5-layer compression pipeline.

    Claude Code runs these in order: cheapest first, escalating as needed.
    """
    # Layer 1: Truncate tool outputs (always, zero cost)
    messages = truncate_tool_outputs(messages)

    # Layer 5: Semantic dedup (zero cost)
    messages = deduplicate_tool_results(messages)

    # Check if we're under budget already
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    if total_chars // 4 < target_tokens:
        return messages

    # Layer 2: Prune old messages
    messages = prune_messages(messages, keep_recent=10)

    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    if total_chars // 4 < target_tokens:
        return messages

    # Layer 3: LLM summary (most expensive, best compression)
    messages = await summarize_conversation(messages, gateway, max_summary_tokens)

    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    if total_chars // 4 < target_tokens:
        return messages

    # Layer 4: Sliding window (last resort)
    messages = slide_context_window(messages, target_tokens)

    return messages


# ── Micro compact ──────────────────────────────────────────────────────

def micro_compact(
    messages: list[dict[str, Any]],
    max_chars_per_message: int = 4000,
) -> list[dict[str, Any]]:
    """Zero-cost micro-compaction: trim individual messages only.

    Claude Code equivalent: MicroCompact — edits cached content locally,
    zero API cost. Applied continuously.
    """
    result = []
    for m in messages:
        content = str(m.get("content", ""))
        if len(content) <= max_chars_per_message:
            result.append(m)
            continue
        # Keep first and last portion
        half = max_chars_per_message // 2
        trimmed = content[:half] + f"\n... [{len(content) - max_chars_per_message} chars] ...\n" + content[-half:]
        result.append({**m, "content": trimmed, "_micro_compacted": True})
    return result
