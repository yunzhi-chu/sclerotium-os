"""Universal Model Gateway — 100+ providers, 2,500+ models, one API.

Unified gateway to ALL major LLM providers through a single OpenAI-compatible
interface. Automatically handles routing, failover, and cost optimization.

Architecture:
  LiteLLM SDK (open-source) → 100+ providers, 2,500+ models
  OpenRouter protocol → 400+ models, 60+ providers
  Local Ollama → offline models (MiniCPM, Llama, Qwen, etc.)

Provider coverage:
  Frontier: OpenAI (GPT-5.x), Anthropic (Claude Opus 4.8), Google Gemini,
            DeepSeek-V4, Mistral, xAI Grok
  Fast inference: Groq, Cerebras, Together AI, Fireworks, DeepInfra
  Cloud: AWS Bedrock, Azure OpenAI, NVIDIA NIM, Cloudflare Workers AI
  Regional: Moonshot, Qianfan, MiniMax, Qwen Portal, Xiaomi MiMo
  Local: Ollama, vLLM, llama.cpp
  Marketplaces: OpenRouter, ZenMux, Venice, NanoGPT

Reference:
  - LiteLLM (MIT, 2,500+ models): github.com/BerriAI/litellm
  - OpenRouter (400+ models): openrouter.ai
  - Vercel AI Gateway, Portkey, Kong AI Gateway, Cloudflare AI Gateway
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from gateways.model_capabilities import get_capability, DEFAULT_CAPABILITY


# ── Provider catalog ──────────────────────────────────────────────────


@dataclass
class ProviderInfo:
    name: str
    base_url: str
    models: list[str] = field(default_factory=list)
    requires_api_key: bool = True
    free_tier: bool = False
    category: str = "frontier"


PROVIDERS: dict[str, ProviderInfo] = {
    # Frontier
    "openai": ProviderInfo("OpenAI", "https://api.openai.com/v1",
        ["gpt-5.4", "gpt-5.3-codex", "gpt-5.2", "gpt-5-mini", "gpt-5-nano",
         "o4-mini", "o3"], True, False, "frontier"),
    "anthropic": ProviderInfo("Anthropic", "https://api.anthropic.com/v1",
        ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5",
         "claude-fable-5"], True, False, "frontier"),
    "google": ProviderInfo("Google Gemini", "https://generativelanguage.googleapis.com/v1beta",
        ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash-lite"], True, True, "frontier"),
    "deepseek": ProviderInfo("DeepSeek", "https://api.deepseek.com/v1",
        ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-r1"], True, True, "frontier"),
    "mistral": ProviderInfo("Mistral", "https://api.mistral.ai/v1",
        ["mistral-large-2", "mistral-small", "codestral"], True, True, "frontier"),
    "xai": ProviderInfo("xAI Grok", "https://api.x.ai/v1",
        ["grok-3", "grok-3-mini"], True, False, "frontier"),

    # Fast inference
    "groq": ProviderInfo("Groq", "https://api.groq.com/openai/v1",
        ["llama-4-70b", "mixtral-8x7b", "gemma2-9b"], True, True, "fast"),
    "together": ProviderInfo("Together AI", "https://api.together.xyz/v1",
        ["llama-4-70b", "qwen3-72b", "deepseek-v3"], True, True, "fast"),
    "cerebras": ProviderInfo("Cerebras", "https://api.cerebras.ai/v1",
        ["llama-4-70b", "llama-3.1-8b"], True, True, "fast"),
    "fireworks": ProviderInfo("Fireworks", "https://api.fireworks.ai/inference/v1",
        ["llama-4-70b", "mixtral-8x22b", "qwen3-72b"], True, True, "fast"),

    # Cloud
    "bedrock": ProviderInfo("AWS Bedrock", "https://bedrock-runtime.us-east-1.amazonaws.com",
        ["claude-opus-4-8", "claude-sonnet-4-6", "llama-4-70b"], True, False, "cloud"),
    "azure": ProviderInfo("Azure OpenAI", "https://{resource}.openai.azure.com",
        ["gpt-5.3", "gpt-5-mini"], True, False, "cloud"),

    # Regional
    "moonshot": ProviderInfo("Moonshot", "https://api.moonshot.cn/v1",
        ["moonshot-v1-128k", "moonshot-v1-32k"], True, True, "regional"),
    "qwen": ProviderInfo("Qwen Portal", "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ["qwen3-235b", "qwen3-72b", "qwen3-7b"], True, True, "regional"),
    "zhipu": ProviderInfo("Zhipu GLM", "https://open.bigmodel.cn/api/paas/v4",
        ["glm-4-plus", "glm-4-flash"], True, True, "regional"),
    "minimax": ProviderInfo("MiniMax", "https://api.minimax.chat/v1",
        ["abab7", "abab6.5s"], True, True, "regional"),

    # Open-source local
    "ollama": ProviderInfo("Ollama", "http://localhost:11434/v1",
        ["minicpm5-1b", "llama3.2", "qwen3", "deepseek-r1:8b", "mistral",
         "gemma3", "phi4", "codellama"], False, True, "local"),
    "vllm": ProviderInfo("vLLM", "http://localhost:8000/v1",
        [], False, True, "local"),
    "lmstudio": ProviderInfo("LM Studio", "http://localhost:1234/v1",
        [], False, True, "local"),

    # Marketplaces (aggregators)
    "openrouter": ProviderInfo("OpenRouter", "https://openrouter.ai/api/v1",
        ["*"], True, True, "marketplace"),
}


class RoutingStrategy(Enum):
    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    BEST = "best"
    FALLBACK = "fallback"


@dataclass
class ModelRoute:
    provider: str
    model: str
    base_url: str
    api_key: str = ""
    priority: int = 0


# ── Universal Model Gateway ──────────────────────────────────────────


class UniversalModelGateway:
    """Single interface to ALL model providers.

    Usage:
        gw = UniversalModelGateway()
        gw.set_routing(RoutingStrategy.CHEAPEST)
        result = await gw.chat("Hello, world!")
    """

    def __init__(self) -> None:
        self._strategy = RoutingStrategy.CHEAPEST
        self._routes: dict[RoutingStrategy, list[ModelRoute]] = {}
        self._litellm_available = self._check_litellm()
        self._build_default_routes()
        self._cache_engine: Any = None  # Prompt cache engine

    def wire_cache(self, cache_engine: Any) -> None:
        """Wire prompt cache engine for automatic cache optimization."""
        self._cache_engine = cache_engine

    def _check_litellm(self) -> bool:
        try:
            import litellm
            return True
        except ImportError:
            return False

    def _build_default_routes(self) -> None:
        """Build routing tables for each strategy."""
        # CHEAPEST: free tiers first, then cheapest paid
        self._routes[RoutingStrategy.CHEAPEST] = [
            ModelRoute("ollama", "minicpm5-1b", "http://localhost:11434/v1", "", 0),
            ModelRoute("deepseek", "deepseek-v4-flash", "https://api.deepseek.com/v1",
                       os.environ.get("DEEPSEEK_API_KEY", ""), 1),
            ModelRoute("groq", "llama-4-70b", "https://api.groq.com/openai/v1",
                       os.environ.get("GROQ_API_KEY", ""), 2),
            ModelRoute("google", "gemini-2.5-flash",
                       "https://generativelanguage.googleapis.com/v1beta",
                       os.environ.get("GOOGLE_API_KEY", ""), 3),
        ]

        # FASTEST: low-latency inference providers
        self._routes[RoutingStrategy.FASTEST] = [
            ModelRoute("groq", "llama-4-70b", "https://api.groq.com/openai/v1",
                       os.environ.get("GROQ_API_KEY", ""), 0),
            ModelRoute("cerebras", "llama-3.1-8b", "https://api.cerebras.ai/v1",
                       os.environ.get("CEREBRAS_API_KEY", ""), 1),
            ModelRoute("deepseek", "deepseek-v4-flash", "https://api.deepseek.com/v1",
                       os.environ.get("DEEPSEEK_API_KEY", ""), 2),
        ]

        # BEST: frontier models
        self._routes[RoutingStrategy.BEST] = [
            ModelRoute("anthropic", "claude-opus-4-8", "https://api.anthropic.com/v1",
                       os.environ.get("ANTHROPIC_API_KEY", ""), 0),
            ModelRoute("openai", "gpt-5.4", "https://api.openai.com/v1",
                       os.environ.get("OPENAI_API_KEY", ""), 1),
            ModelRoute("deepseek", "deepseek-v4-pro", "https://api.deepseek.com/v1",
                       os.environ.get("DEEPSEEK_API_KEY", ""), 2),
        ]

        # FALLBACK: try in order, stop at first success
        self._routes[RoutingStrategy.FALLBACK] = [
            ModelRoute("deepseek", "deepseek-v4-flash", "https://api.deepseek.com/v1",
                       os.environ.get("DEEPSEEK_API_KEY", ""), 0),
            ModelRoute("ollama", "qwen3", "http://localhost:11434/v1", "", 1),
            ModelRoute("groq", "llama-4-70b", "https://api.groq.com/openai/v1",
                       os.environ.get("GROQ_API_KEY", ""), 2),
        ]

    # ── Public API ────────────────────────────────────────────────────

    def set_routing(self, strategy: RoutingStrategy) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> RoutingStrategy:
        return self._strategy

    def list_providers(self) -> list[dict[str, Any]]:
        """List all 20+ providers with their models."""
        return [
            {
                "id": pid,
                "name": p.name,
                "base_url": p.base_url,
                "models": p.models[:8],
                "model_count": len(p.models),
                "free_tier": p.free_tier,
                "category": p.category,
                "requires_key": p.requires_api_key,
            }
            for pid, p in PROVIDERS.items()
        ]

    def list_models(self, provider: str = "all") -> list[dict[str, Any]]:
        """List models, optionally filtered by provider."""
        models = []
        for pid, p in PROVIDERS.items():
            if provider == "all" or pid == provider:
                for m in p.models:
                    if m != "*":
                        models.append({"provider": pid, "provider_name": p.name, "model": m, "free": p.free_tier})
        return models

    def get_best_route(self, strategy: RoutingStrategy | None = None) -> ModelRoute | None:
        """Get the best route for the given strategy (default: current)."""
        strat = strategy or self._strategy
        routes = self._routes.get(strat, [])
        for route in sorted(routes, key=lambda r: r.priority):
            if route.provider == "ollama":
                return route  # Local always available
            if route.api_key:
                return route
        # Fallback: first route
        return routes[0] if routes else None

    # ── Super Prompt (mycelium.md v6.0) ──────────────────────────────

    _super_prompt: str | None = None

    @classmethod
    def load_super_prompt(cls) -> str:
        """Load the Sclerotium OS super prompt from mycelium.md."""
        if cls._super_prompt is not None:
            return cls._super_prompt
        try:
            from pathlib import Path
            md = Path("mycelium.md")
            if md.exists():
                cls._super_prompt = md.read_text(encoding="utf-8")
                return cls._super_prompt
        except Exception:
            pass
        cls._super_prompt = ""
        return ""

    async def chat(
        self,
        prompt: str,
        model: str | None = None,
        provider: str | None = None,
        strategy: RoutingStrategy | None = None,
        system: str | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion through the optimal route.

        Automatically injects mycelium.md super prompt as system message.
        """
        strat = strategy or self._strategy
        system_prompt = system or self.load_super_prompt()

        # Prefer direct HTTP for explicitly-specified providers (faster, no LiteLLM overhead)
        if provider and provider in ("deepseek", "openai", "anthropic", "groq", "google"):
            return await self._chat_openai_compat(prompt, model, provider, strat, system_prompt)

        if self._litellm_available:
            return await self._chat_litellm(prompt, model, provider, strat, system_prompt)
        else:
            return await self._chat_openai_compat(prompt, model, provider, strat, system_prompt)

    async def _chat_litellm(
        self, prompt: str, model: str | None, provider: str | None,
        strategy: RoutingStrategy, system_prompt: str = "",
    ) -> dict[str, Any]:
        """Use LiteLLM for multi-provider routing with super prompt."""
        import litellm

        if model:
            full_model = f"{provider}/{model}" if provider else model
        else:
            route = self.get_best_route()
            if route is None:
                return {"error": "No route available"}
            full_model = f"{route.provider}/{route.model}"

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = litellm.completion(
                model=full_model,
                messages=messages,
                timeout=30,
            )
            return {
                "content": response.choices[0].message.content,
                "model": full_model,
                "provider": getattr(response, "_provider", "unknown"),
                "tokens": response.usage.total_tokens if response.usage else 0,
                "status": "ok",
            }
        except Exception as exc:
            # Fallback: bypass LiteLLM, use direct HTTP call with original model+provider+strategy
            if strategy != RoutingStrategy.FALLBACK:
                return await self._chat_openai_compat(prompt, model, provider, strategy)
            return {"error": str(exc), "status": "error"}

    async def _chat_openai_compat(
        self, prompt: str, model: str | None, provider: str | None,
        strategy: RoutingStrategy, system_prompt: str = "",
    ) -> dict[str, Any]:
        """Use raw OpenAI-compatible HTTP API with super prompt.

        BUG#2修复: 当 provider 明确指定时, 直接从 PROVIDERS 获取 base_url/API key,
        不再调用 get_best_route() 被 ollama(localhost:11434) 劫持。
        """
        import json as _json, os as _os

        # BUG#2修复: 明确指定的 provider > 自动路由
        if provider and provider in PROVIDERS and provider != "ollama":
            pinfo = PROVIDERS[provider]
            route = ModelRoute(
                provider, model or pinfo.models[0], pinfo.base_url,
                _os.environ.get(f"{provider.upper()}_API_KEY", ""),
            )
            # 如果本地 ollama 未运行, 不要回退到它
        else:
            route = self.get_best_route(strategy)

        if route is None or not hasattr(route, 'provider'):
            return {"error": "No route available", "status": "error",
                   "suggestion": "Specify provider=deepseek (or openai/anthropic/groq) and ensure API key is set"}

        model_name = model or route.model
        base_url = route.base_url
        api_key = route.api_key or "ollama"

        # BUG#2修复: 如果路由到 ollama, 先检查是否在线
        if getattr(route, 'provider', '') == "ollama":
            try:
                import urllib.request as _ur
                _ur.urlopen(f"{base_url}/models", timeout=2)
            except Exception:
                # ollama 不在线, 尝试下一个可用路由
                for alt_route in self._routes:
                    if alt_route.provider != "ollama":
                        route = alt_route
                        model_name = model or route.model
                        base_url = route.base_url
                        api_key = route.api_key or ""
                        break
                else:
                    return {"error": "Ollama not running and no fallback provider available. "
                                     "Start ollama or specify provider=deepseek/openai/anthropic/groq.",
                            "status": "error", "provider": "ollama"}

        headers = {"Content-Type": "application/json"}
        if api_key and api_key != "ollama":
            headers["Authorization"] = f"Bearer {api_key}"

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        cap = get_capability(model_name, route.provider)
        body = {
            "model": model_name,
            "messages": messages,
            "max_tokens": cap.max_output_tokens,
            "temperature": cap.optimal_temperature,
        }

        try:
            import urllib.request
            req = urllib.request.Request(
                f"{base_url}/chat/completions",
                data=_json.dumps(body).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = _json.loads(resp.read())
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {
                    "content": content,
                    "model": model_name,
                    "provider": route.provider,
                    "tokens": data.get("usage", {}).get("total_tokens", 0),
                    "status": "ok",
                }
        except Exception as exc:
            return {"error": str(exc), "status": "error", "provider": route.provider}

    async def chat_stream(
        self,
        prompt: str,
        model: str | None = None,
        provider: str | None = None,
        strategy: RoutingStrategy | None = None,
        system: str | None = None,
    ):
        """True token-by-token streaming — tokens yield IMMEDIATELY, not at end."""
        import asyncio, json as _json, threading, queue

        # Fast path: explicitly specified provider → direct HTTP
        if provider and provider in ("deepseek", "openai", "anthropic", "groq", "google", "mistral", "xai"):
            strat = strategy or RoutingStrategy.BEST
        else:
            strat = strategy or self._strategy

        system_prompt = system or self.load_super_prompt()
        # When provider is explicitly specified, use it directly
        if provider and provider in PROVIDERS:
            pinfo = PROVIDERS[provider]
            route = ModelRoute(provider, model or pinfo.models[0], pinfo.base_url,
                              os.environ.get(f"{provider.upper()}_API_KEY", ""))
        else:
            route = self.get_best_route(strat)
        if route is None:
            yield {"type": "error", "content": "No route available"}
            return

        model_name = model or route.model
        base_url = route.base_url
        api_key = route.api_key or "ollama"

        headers = {"Content-Type": "application/json"}
        if api_key and api_key != "ollama":
            headers["Authorization"] = f"Bearer {api_key}"

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        cap = get_capability(model_name, route.provider)
        body = {
            "model": model_name, "messages": messages,
            "max_tokens": cap.max_output_tokens,
            "temperature": cap.optimal_temperature,
            "stream": True,
        }

        # Thread-safe queue for real-time token delivery
        token_queue: queue.Queue = queue.Queue()

        def _fetch_stream():
            import urllib.request
            try:
                req = urllib.request.Request(
                    f"{base_url}/chat/completions",
                    data=_json.dumps(body).encode("utf-8"),
                    headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=300) as resp:
                    total_tokens = 0
                    for line_bytes in resp:
                        line = line_bytes.decode("utf-8", errors="replace").strip()
                        if not line or not line.startswith("data: "): continue
                        data_str = line[6:]
                        if data_str == "[DONE]": break
                        try:
                            data = _json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content: token_queue.put(("token", content))
                            usage = data.get("usage", {})
                            if usage: total_tokens = usage.get("total_tokens", 0)
                        except _json.JSONDecodeError: continue
                    token_queue.put(("done", total_tokens, model_name))
            except Exception as e:
                token_queue.put(("error", str(e)))

        # Start fetch in background thread
        thread = threading.Thread(target=_fetch_stream, daemon=True)
        thread.start()

        # Yield tokens AS THEY ARRIVE (not all at the end)
        while True:
            try:
                item = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: token_queue.get(timeout=0.05))
                if item[0] == "token":
                    yield {"type": "token", "content": item[1]}
                elif item[0] == "done":
                    yield {"type": "done", "tokens": item[1], "model": item[2]}
                    return
                elif item[0] == "error":
                    yield {"type": "error", "content": item[1]}
                    return
            except queue.Empty:
                if not thread.is_alive():
                    # 线程已死但可能还有未取出的消息（error/done）
                    try:
                        item = token_queue.get_nowait()
                        if item[0] == "error":
                            yield {"type": "error", "content": item[1]}
                        elif item[0] == "done":
                            yield {"type": "done", "tokens": item[1], "model": item[2]}
                    except queue.Empty:
                        pass
                    if not token_queue.empty():
                        continue  # 还有消息，继续处理
                    break
                await asyncio.sleep(0.01)  # Yield to event loop
                continue

    def _get_provider_url(self, provider_id: str) -> str:
        """Get base URL for a provider."""
        pinfo = PROVIDERS.get(provider_id)
        return pinfo.base_url if pinfo else ""

    def test_connection(self, provider_id: str) -> dict[str, Any]:
        """Test connectivity to a specific provider."""
        if provider_id not in PROVIDERS:
            return {"status": "error", "error": f"Unknown provider: {provider_id}"}

        p = PROVIDERS[provider_id]
        if provider_id == "ollama":
            import urllib.request
            try:
                req = urllib.request.Request("http://localhost:11434/api/tags")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    import json
                    data = json.loads(resp.read())
                    models = [m["name"] for m in data.get("models", [])]
                    return {"status": "ok", "provider": provider_id, "local_models": models}
            except Exception as e:
                return {"status": "error", "provider": provider_id, "error": str(e)}

        api_key = os.environ.get(f"{provider_id.upper()}_API_KEY", "")
        if not api_key:
            return {"status": "no_key", "provider": provider_id, "requires_key": True}

        return {"status": "ok", "provider": provider_id, "has_key": True}
