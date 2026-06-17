"""Custom Model Provider Gateway — 自定义模型API。

支持任意 OpenAI-compatible API 端点:
  - 自部署模型 (vLLM, Ollama, llama.cpp, LocalAI)
  - 第三方代理 (OpenRouter, OneAPI, LiteLLM Proxy)
  - 企业私有部署 (Azure, AWS Bedrock 自定义)
  - 个人 API 端点

特性:
  - 自动模型发现 (GET /v1/models)
  - API Key 验证 (GET /v1/models 带认证)
  - 多端点管理 (同时连接多个自定义API)
  - 配置持久化 (JSON文件)
  - 一键切换 (与内置100+提供商同等优先级)

使用方式:
    # 添加自定义提供商
    gateway = CustomProviderGateway()
    gateway.add_provider("my_vllm", "http://localhost:8000/v1",
                        api_key="sk-xxx", models=["llama-3-70b"])
    gateway.add_provider("openrouter", "https://openrouter.ai/api/v1",
                        api_key="sk-or-xxx")  # 自动发现模型

    # 使用
    models = gateway.list_models()
    client = gateway.get_client("my_vllm")
    response = client.chat("llama-3-70b", messages=[...])
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("sclerotium.custom_provider")

# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CustomModel:
    """自定义模型信息。"""
    name: str
    provider: str = ""
    context_window: int = 128000
    max_tokens: int = 4096
    supports_vision: bool = False
    supports_tools: bool = True
    pricing_per_1k: float = 0.0     # $/1K tokens


@dataclass(frozen=True)
class CustomProvider:
    """自定义提供商配置。"""
    name: str                       # 唯一标识
    base_url: str                   # API 端点 (如 http://localhost:8000/v1)
    api_key: str = ""               # API 密钥
    models: tuple[str, ...] = ()    # 已知模型列表
    enabled: bool = True
    is_openai_compatible: bool = True
    description: str = ""
    added_at: float = field(default_factory=time.time)
    last_checked: float = 0.0


# ═══════════════════════════════════════════════════════════════
# CustomProviderGateway
# ═══════════════════════════════════════════════════════════════

class CustomProviderGateway:
    """自定义模型API管理器。

    管理用户添加的所有自定义 OpenAI-compatible API 端点。
    支持自动模型发现、连接验证、配置持久化。

    使用方式:
        gateway = CustomProviderGateway()
        gateway.add("ollama", "http://localhost:11434/v1", models=["qwen2.5:7b"])
        gateway.add("openrouter", "https://openrouter.ai/api/v1", api_key="sk-xxx")
        providers = gateway.list_providers()
    """

    CONFIG_FILE = "custom_providers.json"

    def __init__(self, config_dir: str = "./data") -> None:
        self._providers: dict[str, CustomProvider] = {}
        self._models: dict[str, CustomModel] = {}  # provider:model → CustomModel
        self._config_path = Path(config_dir) / self.CONFIG_FILE
        self._lock = threading.RLock()
        self._load_config()

        # 预注册已知的自部署/免费提供商
        self._register_known_free_providers()

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def add(
        self,
        name: str,
        base_url: str,
        api_key: str = "",
        models: list[str] | None = None,
        description: str = "",
        auto_discover: bool = True,
    ) -> CustomProvider:
        """添加自定义提供商。

        Args:
            name: 唯一名称 (如 "my_ollama")
            base_url: API 端点地址 (如 "http://localhost:11434/v1")
            api_key: API 密钥 (可选, 本地部署不需要)
            models: 已知模型列表
            description: 描述
            auto_discover: 是否自动从 /v1/models 发现模型

        Returns:
            CustomProvider 配置
        """
        provider = CustomProvider(
            name=name,
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            models=tuple(models or []),
            description=description,
        )

        with self._lock:
            self._providers[name] = provider

            # 注册模型
            for m in (models or []):
                full_name = f"{name}/{m}"
                self._models[full_name] = CustomModel(
                    name=m, provider=name,
                )

        # 自动发现
        if auto_discover and not models:
            discovered = self._discover_models(provider)
            if discovered:
                self._update_models(name, discovered)

        self._save_config()
        logger.info("Added custom provider: %s (%s)", name, base_url)
        return provider

    def remove(self, name: str) -> bool:
        """移除提供商。"""
        with self._lock:
            if name not in self._providers:
                return False
            del self._providers[name]
            # 移除相关模型
            keys_to_del = [k for k in self._models if k.startswith(f"{name}/")]
            for k in keys_to_del:
                del self._models[k]
        self._save_config()
        return True

    def list_providers(self) -> list[CustomProvider]:
        """列出所有自定义提供商。"""
        with self._lock:
            return list(self._providers.values())

    def list_models(self) -> list[CustomModel]:
        """列出所有自定义模型。"""
        with self._lock:
            return list(self._models.values())

    def find_model(self, name: str) -> CustomModel | None:
        """按名称查找模型 (支持 provider/model 格式)。"""
        with self._lock:
            # 精确匹配
            if name in self._models:
                return self._models[name]
            # 按模型名匹配
            for full, model in self._models.items():
                if model.name == name:
                    return model
            return None

    def get_provider(self, name: str) -> CustomProvider | None:
        """获取提供商配置。"""
        with self._lock:
            return self._providers.get(name)

    def test_connection(self, name: str) -> dict[str, Any]:
        """测试提供商连接。"""
        provider = self.get_provider(name)
        if not provider:
            return {"ok": False, "error": "Provider not found"}

        try:
            import urllib.request
            req = urllib.request.Request(
                f"{provider.base_url}/models",
                headers={"Authorization": f"Bearer {provider.api_key}"}
                if provider.api_key else {},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                models = [m.get("id", "") for m in data.get("data", [])]
                return {"ok": True, "models_found": len(models),
                       "sample": models[:5]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "providers": len(self._providers),
                "models": len(self._models),
                "enabled": sum(1 for p in self._providers.values() if p.enabled),
            }

    # ═══════════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════════

    def _register_known_free_providers(self) -> None:
        """注册已知的免费/开源提供商模板。"""
        known = {
            "ollama": ("http://localhost:11434/v1", "本地 Ollama 服务"),
            "vllm": ("http://localhost:8000/v1", "本地 vLLM 推理服务"),
            "lmstudio": ("http://localhost:1234/v1", "LM Studio 本地推理"),
            "localai": ("http://localhost:8080/v1", "LocalAI 兼容端点"),
            "text-generation-webui": ("http://localhost:5000/v1", "oobabooga text-generation-webui"),
            "llamacpp": ("http://localhost:8081/v1", "llama.cpp server"),
            "openrouter": ("https://openrouter.ai/api/v1", "OpenRouter — 400+模型聚合"),
            "deepinfra": ("https://api.deepinfra.com/v1", "DeepInfra — 开源模型托管"),
            "groq": ("https://api.groq.com/openai/v1", "Groq — LPU 极速推理"),
            "together": ("https://api.together.xyz/v1", "Together AI — 100+开源模型"),
            "fireworks": ("https://api.fireworks.ai/inference/v1", "Fireworks — 快速推理"),
            "cerebras": ("https://api.cerebras.ai/v1", "Cerebras — 晶圆级推理"),
            "novita": ("https://api.novita.ai/v3/openai", "Novita AI — 低成本GPU推理"),
            "nvidia_nim": ("https://integrate.api.nvidia.com/v1", "NVIDIA NIM 微服务"),
        }
        for name, (url, desc) in known.items():
            if name not in self._providers:
                self._providers[name] = CustomProvider(
                    name=name, base_url=url, description=desc,
                    enabled=False,  # 默认禁用, 用户需手动启用
                )

    def _discover_models(self, provider: CustomProvider) -> list[str]:
        """从 /v1/models 端点自动发现模型。"""
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{provider.base_url}/models",
                headers={"Authorization": f"Bearer {provider.api_key}"}
                if provider.api_key else {},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = [m.get("id", "") for m in data.get("data", [])]
                return models
        except Exception:
            return []

    def _update_models(self, provider_name: str, models: list[str]) -> None:
        """更新提供商的模型列表。"""
        with self._lock:
            provider = self._providers.get(provider_name)
            if provider:
                self._providers[provider_name] = CustomProvider(
                    name=provider.name, base_url=provider.base_url,
                    api_key=provider.api_key, models=tuple(models),
                    enabled=provider.enabled, description=provider.description,
                    last_checked=time.time(),
                )
            for m in models:
                full = f"{provider_name}/{m}"
                self._models[full] = CustomModel(name=m, provider=provider_name)

    def _save_config(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            config = {
                name: {
                    "base_url": p.base_url, "api_key": p.api_key,
                    "models": list(p.models), "enabled": p.enabled,
                    "description": p.description,
                }
                for name, p in self._providers.items()
            }
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Save config failed: %s", e)

    def _load_config(self) -> None:
        if not self._config_path.exists():
            return
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            for name, cfg in config.items():
                provider = CustomProvider(
                    name=name,
                    base_url=cfg.get("base_url", ""),
                    api_key=cfg.get("api_key", ""),
                    models=tuple(cfg.get("models", [])),
                    enabled=cfg.get("enabled", True),
                    description=cfg.get("description", ""),
                )
                self._providers[name] = provider
                for m in cfg.get("models", []):
                    self._models[f"{name}/{m}"] = CustomModel(
                        name=m, provider=name,
                    )
        except Exception as e:
            logger.warning("Load config failed: %s", e)
