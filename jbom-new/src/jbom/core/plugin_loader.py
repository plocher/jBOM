"""Plugin discovery and loading infrastructure."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class PluginMetadata:
    """Metadata about a discovered plugin."""

    name: str
    version: str
    description: str = ""
    path: Optional[Path] = None


class PluginLoader:
    """Discovers and loads plugins from the plugins directory."""

    def __init__(self, plugins_dir: Path):
        """Initialize the plugin loader.

        Args:
            plugins_dir: Path to the plugins directory to scan
        """
        self.plugins_dir = plugins_dir
        self._discovered_plugins: List[PluginMetadata] = []

    def discover_plugins(self) -> List[PluginMetadata]:
        """Discover all plugins in the plugins directory.

        Returns:
            List of discovered plugin metadata
        """
        self._discovered_plugins = []

        if not self.plugins_dir.exists():
            return self._discovered_plugins

        # Scan for plugin directories
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith((".", "_")):
                metadata = self._load_plugin_metadata(item)
                if metadata:
                    self._discovered_plugins.append(metadata)

        return self._discovered_plugins

    def _load_plugin_metadata(self, plugin_dir: Path) -> Optional[PluginMetadata]:
        """Load metadata for a single plugin.

        Args:
            plugin_dir: Path to the plugin directory

        Returns:
            PluginMetadata if valid, None otherwise
        """
        # Check for plugin.json
        metadata_file = plugin_dir / "plugin.json"
        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, "r") as f:
                data = json.load(f)

            return PluginMetadata(
                name=data.get("name", plugin_dir.name),
                version=data.get("version", "unknown"),
                description=data.get("description", ""),
                path=plugin_dir,
            )
        except (json.JSONDecodeError, OSError):
            return None

    def get_plugins(self) -> List[PluginMetadata]:
        """Get the list of discovered plugins.

        Returns:
            List of plugin metadata
        """
        return self._discovered_plugins
