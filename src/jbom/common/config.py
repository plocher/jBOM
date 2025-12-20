"""Configuration loader for jBOM fabricator and distributor settings.

Supports hierarchical configuration loading with precedence:
built-in → system → user → project
"""

import yaml
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from copy import deepcopy


@dataclass
class FabricatorConfig:
    """Configuration for a PCB fabricator."""

    name: str
    id: str = ""
    description: str = ""
    based_on: str = ""

    # Manufacturing and assembly info
    pcb_manufacturing: Dict[str, Any] = field(default_factory=dict)
    pcb_assembly: Dict[str, Any] = field(default_factory=dict)

    # Part number configuration
    part_number: Dict[str, Any] = field(default_factory=dict)

    # BOM column mappings (fab_header: jbom_field)
    bom_columns: Dict[str, str] = field(default_factory=dict)

    # Advanced configuration options
    dynamic_name: bool = False  # Use dynamic names based on data
    name_source: Optional[str] = None  # Source for dynamic names ("manufacturer")

    # Derived properties for backward compatibility
    @property
    def part_number_header(self) -> str:
        return self.part_number.get("header", "Fabricator Part Number")

    @property
    def part_number_fields(self) -> List[str]:
        return self.part_number.get("priority_fields", [])

    @property
    def cli_flags(self) -> List[str]:
        if not self.id:
            return []
        return [f"--{self.id}"]

    @property
    def cli_presets(self) -> List[str]:
        if not self.id:
            return []
        return [f"+{self.id}"]

    def __post_init__(self):
        # Auto-generate id from name if not provided
        if not self.id and self.name:
            self.id = self.name.lower().replace(" ", "").replace("-", "")


@dataclass
class DistributorConfig:
    """Configuration for a component distributor/search provider."""

    name: str
    id: str
    website: str = ""
    api_endpoint: str = ""
    api_token_env: str = ""
    search_capabilities: List[str] = field(default_factory=list)
    rate_limits: Dict[str, int] = field(default_factory=dict)


@dataclass
class JBOMConfig:
    """Complete jBOM configuration."""

    version: str = "1.0.0"
    schema_version: str = "2025.12.20"
    metadata: Dict[str, Any] = field(default_factory=dict)

    fabricators: List[FabricatorConfig] = field(default_factory=list)
    distributors: List[DistributorConfig] = field(default_factory=list)
    global_presets: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Configuration loading metadata
    config_sources: List[str] = field(default_factory=list)

    def get_fabricator(self, fab_id: str) -> Optional[FabricatorConfig]:
        """Get fabricator config by ID."""
        for fab in self.fabricators:
            if fab.id.lower() == fab_id.lower():
                return fab
        return None

    def get_fabricator_by_cli_flag(self, flag: str) -> Optional[FabricatorConfig]:
        """Get fabricator config by CLI flag (e.g., '--jlc')."""
        for fab in self.fabricators:
            if flag in fab.cli_flags:
                return fab
        return None

    def get_fabricator_by_preset(self, preset: str) -> Optional[FabricatorConfig]:
        """Get fabricator config by preset name (e.g., '+jlc')."""
        for fab in self.fabricators:
            if preset in fab.cli_presets:
                return fab
        return None

    def get_distributor(self, dist_id: str) -> Optional[DistributorConfig]:
        """Get distributor config by ID."""
        for dist in self.distributors:
            if dist.id.lower() == dist_id.lower():
                return dist
        return None


class ConfigLoader:
    """Hierarchical configuration loader for jBOM."""

    def __init__(self):
        self.config_paths = self._get_config_paths()

    def _get_config_paths(self) -> List[Path]:
        """Get ordered list of configuration file paths to check."""
        paths = []
        system = platform.system()

        # System-wide configs (OS-specific)
        if system == "Windows":
            # Windows: %PROGRAMDATA%\jbom\config.yaml
            import os

            programdata = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
            system_paths = [Path(programdata) / "jbom" / "config.yaml"]
        elif system == "Darwin":  # macOS
            # macOS: /Library/Application Support/jbom/config.yaml
            system_paths = [Path("/Library/Application Support/jbom/config.yaml")]
        else:  # Linux and other Unix-like
            # Linux: /etc/jbom/config.yaml, /usr/local/etc/jbom/config.yaml
            system_paths = [
                Path("/etc/jbom/config.yaml"),
                Path("/usr/local/etc/jbom/config.yaml"),
            ]

        for path in system_paths:
            if path.exists():
                paths.append(path)

        # User configs (OS-specific)
        home = Path.home()
        if system == "Windows":
            # Windows: %APPDATA%\jbom\config.yaml
            import os

            appdata = os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
            user_paths = [Path(appdata) / "jbom" / "config.yaml"]
        elif system == "Darwin":  # macOS
            # macOS: ~/Library/Application Support/jbom/config.yaml
            user_paths = [
                home / "Library" / "Application Support" / "jbom" / "config.yaml",
                home / ".config" / "jbom" / "config.yaml",  # XDG fallback
            ]
        else:  # Linux and other Unix-like
            # Linux: ~/.config/jbom/config.yaml (XDG), ~/.jbom/config.yaml (legacy)
            user_paths = [
                home / ".config" / "jbom" / "config.yaml",
                home / ".jbom" / "config.yaml",
            ]

        for path in user_paths:
            if path.exists():
                paths.append(path)

        # Project configs (same across all OS)
        cwd = Path.cwd()
        project_paths = [
            cwd / ".jbom" / "config.yaml",
            cwd / "jbom.yaml",
        ]
        for path in project_paths:
            if path.exists():
                paths.append(path)

        return paths

    def load_config(self) -> JBOMConfig:
        """Load complete configuration with hierarchical merging."""

        # Start with built-in defaults
        config = self._get_builtin_config()
        config.config_sources.append("built-in")

        # Load and merge external config files
        for config_path in self.config_paths:
            try:
                external_config = self._load_config_file(config_path)
                config = self._merge_configs(config, external_config)
                config.config_sources.append(str(config_path))
            except Exception as e:
                # Log warning but continue - don't let config errors break jBOM
                print(f"Warning: Failed to load config from {config_path}: {e}")

        return config

    def _load_fabricator(self, fab_data: Dict[str, Any]) -> Optional[FabricatorConfig]:
        """Load a fabricator, handling external files and based_on inheritance."""
        try:
            # Check if this references an external file
            if "file" in fab_data:
                file_path = fab_data["file"]
                # Try to load from package resources first
                package_path = Path(__file__).parent / "../config" / file_path
                if package_path.exists():
                    external_data = self._load_yaml_file(package_path)
                else:
                    # Try relative to current config file location
                    # For now, assume package location
                    return None

                # Merge external data with any overrides in fab_data
                merged_data = deepcopy(external_data)
                for key, value in fab_data.items():
                    if key != "file":
                        merged_data[key] = value
                fab_data = merged_data

            # Handle based_on inheritance
            if "based_on" in fab_data:
                base_name = fab_data["based_on"]
                base_config = self._find_base_fabricator(base_name)
                if base_config:
                    # Start with base config and overlay changes
                    merged_data = self._fabricator_to_dict(base_config)
                    for key, value in fab_data.items():
                        if key != "based_on":
                            merged_data[key] = value
                    fab_data = merged_data

            # Create fabricator config
            fabricator = FabricatorConfig(
                name=fab_data.get("name", ""),
                id=fab_data.get("id", ""),
                description=fab_data.get("description", ""),
                based_on=fab_data.get("based_on", ""),
                pcb_manufacturing=fab_data.get("pcb_manufacturing", {}),
                pcb_assembly=fab_data.get("pcb_assembly", {}),
                part_number=fab_data.get("part_number", {}),
                bom_columns=fab_data.get("bom_columns", {}),
            )

            return fabricator

        except Exception as e:
            print(
                f"Warning: Failed to load fabricator {fab_data.get('name', 'unknown')}: {e}"
            )
            return None

    def _load_yaml_file(self, path: Path) -> Dict[str, Any]:
        """Load YAML file and return data."""
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _find_base_fabricator(self, base_name: str) -> Optional[FabricatorConfig]:
        """Find a base fabricator configuration for inheritance."""
        # For now, return None - this would need to search loaded fabricators
        # This is a placeholder for the inheritance system
        return None

    def _fabricator_to_dict(self, fabricator: FabricatorConfig) -> Dict[str, Any]:
        """Convert fabricator config back to dict for inheritance."""
        return {
            "name": fabricator.name,
            "id": fabricator.id,
            "description": fabricator.description,
            "pcb_manufacturing": fabricator.pcb_manufacturing,
            "pcb_assembly": fabricator.pcb_assembly,
            "part_number": fabricator.part_number,
            "bom_columns": fabricator.bom_columns,
        }

    def _load_config_file(self, path: Path) -> JBOMConfig:
        """Load configuration from a YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return self._dict_to_config(data)

    def _dict_to_config(self, data: Dict[str, Any]) -> JBOMConfig:
        """Convert dictionary data to JBOMConfig object."""
        config = JBOMConfig()

        # Basic metadata
        config.version = data.get("version", "1.0.0")
        config.schema_version = data.get("schema_version", "2025.12.20")
        config.metadata = data.get("metadata", {})

        # Fabricators
        fabricators_data = data.get("fabricators", [])
        for fab_data in fabricators_data:
            fabricator = self._load_fabricator(fab_data)
            if fabricator:
                config.fabricators.append(fabricator)

        # Distributors
        distributors_data = data.get("distributors", [])
        for dist_data in distributors_data:
            distributor = DistributorConfig(
                name=dist_data["name"],
                id=dist_data["id"],
                website=dist_data.get("website", ""),
                api_endpoint=dist_data.get("api_endpoint", ""),
                api_token_env=dist_data.get("api_token_env", ""),
                search_capabilities=dist_data.get("search_capabilities", []),
                rate_limits=dist_data.get("rate_limits", {}),
            )
            config.distributors.append(distributor)

        # Global presets
        config.global_presets = data.get("global_presets", {})

        return config

    def _merge_configs(self, base: JBOMConfig, overlay: JBOMConfig) -> JBOMConfig:
        """Merge two configurations, with overlay taking precedence."""
        merged = deepcopy(base)

        # Merge fabricators (by ID)
        for overlay_fab in overlay.fabricators:
            # Find existing fabricator with same ID
            existing_idx = None
            for idx, base_fab in enumerate(merged.fabricators):
                if base_fab.id == overlay_fab.id:
                    existing_idx = idx
                    break

            if existing_idx is not None:
                # Merge with existing
                merged.fabricators[existing_idx] = self._merge_fabricator_configs(
                    merged.fabricators[existing_idx], overlay_fab
                )
            else:
                # Add new fabricator
                merged.fabricators.append(overlay_fab)

        # Merge distributors (by ID)
        for overlay_dist in overlay.distributors:
            existing_idx = None
            for idx, base_dist in enumerate(merged.distributors):
                if base_dist.id == overlay_dist.id:
                    existing_idx = idx
                    break

            if existing_idx is not None:
                merged.distributors[existing_idx] = overlay_dist
            else:
                merged.distributors.append(overlay_dist)

        # Merge global presets
        merged.global_presets.update(overlay.global_presets)

        # Update metadata
        merged.version = overlay.version or merged.version
        merged.schema_version = overlay.schema_version or merged.schema_version
        merged.metadata.update(overlay.metadata)

        return merged

    def _merge_fabricator_configs(
        self, base: FabricatorConfig, overlay: FabricatorConfig
    ) -> FabricatorConfig:
        """Merge two fabricator configurations."""
        merged = deepcopy(base)

        # Simple field updates
        if overlay.name:
            merged.name = overlay.name
        if overlay.description:
            merged.description = overlay.description
        if overlay.based_on:
            merged.based_on = overlay.based_on

        # Dictionary merging
        if overlay.pcb_manufacturing:
            merged.pcb_manufacturing.update(overlay.pcb_manufacturing)
        if overlay.pcb_assembly:
            merged.pcb_assembly.update(overlay.pcb_assembly)
        if overlay.part_number:
            merged.part_number.update(overlay.part_number)
        if overlay.bom_columns:
            merged.bom_columns.update(overlay.bom_columns)

        return merged

    def _get_builtin_config(self) -> JBOMConfig:
        """Get built-in default configuration from package files."""
        try:
            # Try to load from package defaults
            defaults_path = Path(__file__).parent / "../config/defaults.yaml"
            if defaults_path.exists():
                return self._load_config_file(defaults_path)
        except Exception as e:
            print(f"Warning: Could not load package defaults: {e}")

        # Fallback to minimal built-in config if package files can't be loaded
        config = JBOMConfig()
        config.version = "3.0.0"
        config.schema_version = "2025.12.20"
        config.metadata = {
            "description": "Fallback built-in configuration",
            "source": "fallback",
        }

        # Add minimal generic fabricator as fallback
        generic_fabricator = FabricatorConfig(
            name="Generic",
            id="generic",
            description="Generic fabricator for custom BOM formats",
            part_number={
                "header": "Part Number",
                "priority_fields": ["Part Number", "P/N", "MPN", "MFGPN"],
            },
            bom_columns={
                "Reference": "reference",
                "Quantity": "quantity",
                "Description": "description",
                "Part Number": "fabricator_part_number",
            },
        )

        config.fabricators = [generic_fabricator]
        config.global_presets = {
            "minimal": {
                "description": "Minimal BOM fields",
                "fields": ["reference", "quantity", "description"],
            }
        }

        return config


# Global configuration instance
_config_instance: Optional[JBOMConfig] = None


def get_config() -> JBOMConfig:
    """Get the global jBOM configuration instance."""
    global _config_instance
    if _config_instance is None:
        loader = ConfigLoader()
        _config_instance = loader.load_config()
    return _config_instance


def reload_config() -> JBOMConfig:
    """Reload the global configuration (for testing or config changes)."""
    global _config_instance
    _config_instance = None
    return get_config()
