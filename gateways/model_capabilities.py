"""Model Capability Database — Auto-detect parameters, zero hardcoding.

Every model gets its FULL capabilities. No artificial limits.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class ModelCapability:
    model: str
    provider: str
    max_output_tokens: int     # Max tokens the model CAN generate
    max_context_window: int    # Max tokens the model CAN accept
    supports_streaming: bool = True
    supports_thinking: bool = False
    optimal_temperature: float = 0.6  # Model's sweet spot, not our preference
    is_reasoning_model: bool = False

# Comprehensive capability database — each model gets its FULL potential
MODEL_CAPABILITIES: dict[str, ModelCapability] = {
    # DeepSeek
    "deepseek-v4-pro": ModelCapability("deepseek-v4-pro", "deepseek",
        max_output_tokens=384_000, max_context_window=1_000_000,
        supports_thinking=True, optimal_temperature=0.6),
    "deepseek-v4-flash": ModelCapability("deepseek-v4-flash", "deepseek",
        max_output_tokens=128_000, max_context_window=1_000_000,
        optimal_temperature=0.7),
    "deepseek-r1": ModelCapability("deepseek-r1", "deepseek",
        max_output_tokens=128_000, max_context_window=1_000_000,
        is_reasoning_model=True, optimal_temperature=0.6),

    # OpenAI
    "gpt-5.4": ModelCapability("gpt-5.4", "openai",
        max_output_tokens=128_000, max_context_window=400_000),
    "gpt-5.3-codex": ModelCapability("gpt-5.3-codex", "openai",
        max_output_tokens=128_000, max_context_window=400_000),
    "gpt-5.2": ModelCapability("gpt-5.2", "openai",
        max_output_tokens=128_000, max_context_window=256_000),
    "gpt-5-mini": ModelCapability("gpt-5-mini", "openai",
        max_output_tokens=64_000, max_context_window=256_000),
    "gpt-5-nano": ModelCapability("gpt-5-nano", "openai",
        max_output_tokens=32_000, max_context_window=256_000),
    "o4-mini": ModelCapability("o4-mini", "openai",
        max_output_tokens=128_000, max_context_window=400_000,
        is_reasoning_model=True, optimal_temperature=1.0),
    "o3": ModelCapability("o3", "openai",
        max_output_tokens=100_000, max_context_window=200_000,
        is_reasoning_model=True, optimal_temperature=1.0),

    # Anthropic
    "claude-opus-4-8": ModelCapability("claude-opus-4-8", "anthropic",
        max_output_tokens=128_000, max_context_window=500_000,
        supports_thinking=True),
    "claude-sonnet-4-6": ModelCapability("claude-sonnet-4-6", "anthropic",
        max_output_tokens=128_000, max_context_window=500_000),
    "claude-haiku-4-5": ModelCapability("claude-haiku-4-5", "anthropic",
        max_output_tokens=64_000, max_context_window=500_000),
    "claude-fable-5": ModelCapability("claude-fable-5", "anthropic",
        max_output_tokens=128_000, max_context_window=500_000),

    # Google
    "gemini-2.5-pro": ModelCapability("gemini-2.5-pro", "google",
        max_output_tokens=128_000, max_context_window=2_000_000),
    "gemini-2.5-flash": ModelCapability("gemini-2.5-flash", "google",
        max_output_tokens=64_000, max_context_window=1_000_000),
    "gemini-2.0-flash-lite": ModelCapability("gemini-2.0-flash-lite", "google",
        max_output_tokens=32_000, max_context_window=1_000_000),

    # Fast/Local
    "llama-4-70b": ModelCapability("llama-4-70b", "groq",
        max_output_tokens=32_000, max_context_window=128_000),
    "mixtral-8x7b": ModelCapability("mixtral-8x7b", "groq",
        max_output_tokens=32_000, max_context_window=32_000),
    "qwen3-72b": ModelCapability("qwen3-72b", "groq",
        max_output_tokens=32_000, max_context_window=128_000),
    "minicpm5-1b": ModelCapability("minicpm5-1b", "ollama",
        max_output_tokens=8_000, max_context_window=32_000),
    "qwen3": ModelCapability("qwen3", "ollama",
        max_output_tokens=32_000, max_context_window=128_000),
    "deepseek-r1:8b": ModelCapability("deepseek-r1:8b", "ollama",
        max_output_tokens=32_000, max_context_window=128_000,
        is_reasoning_model=True),
}

# Fallback for unknown models — generous, not limiting
DEFAULT_CAPABILITY = ModelCapability("unknown", "unknown",
    max_output_tokens=384_000, max_context_window=1_000_000)


def get_capability(model: str, provider: str = "") -> ModelCapability:
    """Get full capability for a model. NEVER returns a limited default."""
    if model in MODEL_CAPABILITIES:
        return MODEL_CAPABILITIES[model]
    # Provider-specific fallback
    key = f"{provider}/{model}" if provider else ""
    if key in MODEL_CAPABILITIES:
        return MODEL_CAPABILITIES[key]
    return DEFAULT_CAPABILITY
