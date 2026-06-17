"""Plugin Manifest System — OpenClaw-style auto-discovery (Gap: 插件系统).

Every organ/plugin gets a sclerotium.plugin.json manifest.
Auto-discovered at startup via filesystem scanning.

Manifest format (sclerotium.plugin.json):
{
  "name": "desktop-automation",
  "version": "1.0.0",
  "description": "Windows desktop automation tools",
  "category": "automation",
  "tools": ["desktop_open", "desktop_click", "desktop_screenshot"],
  "dependencies": ["screen_agent", "uia_controller"],
  "config_schema": { ... },
  "enabled": true
}
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("sclerotium.plugins")


@dataclass(frozen=True)
class PluginManifest:
    """Parsed plugin manifest (immutable)."""
    name: str
    version: str = "0.1.0"
    description: str = ""
    category: str = "general"
    tools: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    config_schema: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    source_path: str = ""
    entry_point: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any], source_path: str = "") -> PluginManifest:
        return cls(
            name=data.get("name", "unknown"),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            tools=tuple(data.get("tools", [])),
            dependencies=tuple(data.get("dependencies", [])),
            config_schema=data.get("config_schema", {}),
            enabled=data.get("enabled", True),
            source_path=source_path,
            entry_point=data.get("entry_point", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "category": self.category,
            "tools": list(self.tools),
            "dependencies": list(self.dependencies),
            "config_schema": self.config_schema,
            "enabled": self.enabled,
            "entry_point": self.entry_point,
        }


class PluginDiscovery:
    """Auto-discovers plugins via sclerotium.plugin.json manifest files.

    Scans plugin directories recursively, parses manifests,
    resolves dependency order, and returns enabled plugins.

    Usage:
        discovery = PluginDiscovery()
        plugins = discovery.scan(["./plugins", "./extensions"])
        for p in plugins:
            print(f"Found: {p.name} v{p.version} ({len(p.tools)} tools)")
    """

    MANIFEST_FILENAME = "sclerotium.plugin.json"

    def __init__(self) -> None:
        self._plugins: dict[str, PluginManifest] = {}
        self._load_order: list[str] = []

    def scan(self, search_paths: list[str]) -> list[PluginManifest]:
        """Scan directories for plugin manifests."""
        found: list[PluginManifest] = []

        for search_path in search_paths:
            root = Path(search_path)
            if not root.exists():
                continue

            for manifest_path in root.rglob(self.MANIFEST_FILENAME):
                try:
                    manifest = self._load_manifest(manifest_path)
                    if manifest.enabled:
                        found.append(manifest)
                        self._plugins[manifest.name] = manifest
                        logger.info("Discovered plugin: %s v%s (%d tools)",
                                    manifest.name, manifest.version, len(manifest.tools))
                except Exception as e:
                    logger.warning("Failed to load manifest %s: %s", manifest_path, e)

        # Resolve dependency order
        self._load_order = self._topological_sort(found)
        return [self._plugins[name] for name in self._load_order]

    def _load_manifest(self, path: Path) -> PluginManifest:
        """Load and parse a single manifest file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return PluginManifest.from_dict(data, str(path.parent))

    def _topological_sort(self, plugins: list[PluginManifest]) -> list[str]:
        """Sort plugins by dependency order (dependencies first)."""
        name_to_plugin = {p.name: p for p in plugins}
        visited: set[str] = set()
        temp_mark: set[str] = set()
        order: list[str] = []

        def visit(name: str) -> None:
            if name in temp_mark:
                logger.warning("Circular dependency detected: %s", name)
                return
            if name in visited:
                return
            temp_mark.add(name)
            plugin = name_to_plugin.get(name)
            if plugin:
                for dep in plugin.dependencies:
                    visit(dep)
            temp_mark.discard(name)
            visited.add(name)
            order.append(name)

        for p in plugins:
            if p.name not in visited:
                visit(p.name)

        return order

    def get_plugin(self, name: str) -> PluginManifest | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginManifest]:
        return [self._plugins[n] for n in self._load_order if n in self._plugins]

    def get_all_tools(self) -> list[str]:
        """Get all tool names from all plugins."""
        tools: list[str] = []
        for name in self._load_order:
            p = self._plugins.get(name)
            if p:
                tools.extend(p.tools)
        return tools

    @property
    def plugin_count(self) -> int:
        return len(self._plugins)


def generate_manifest(
    name: str,
    tools: list[str],
    *,
    version: str = "0.1.0",
    description: str = "",
    category: str = "general",
    dependencies: list[str] | None = None,
    entry_point: str = "",
    output_dir: str = ".",
) -> Path:
    """Generate a sclerotium.plugin.json manifest file.

    Usage:
        generate_manifest(
            "desktop-automation",
            tools=["desktop_open", "desktop_click", "desktop_screenshot"],
            category="automation",
            dependencies=["screen_agent", "uia_controller"],
        )
    """
    manifest = {
        "name": name,
        "version": version,
        "description": description,
        "category": category,
        "tools": tools,
        "dependencies": dependencies or [],
        "config_schema": {},
        "enabled": True,
        "entry_point": entry_point,
    }

    output_path = Path(output_dir) / PluginDiscovery.MANIFEST_FILENAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    logger.info("Generated manifest: %s", output_path)
    return output_path
