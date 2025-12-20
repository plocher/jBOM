"""Configuration-driven fabricator implementation.

Replaces hardcoded Fabricator classes with config-driven approach that supports
user customization via YAML configuration files.
"""

from typing import Dict, List, Optional
from jbom.common.types import InventoryItem
from jbom.common.config import FabricatorConfig, get_config
from jbom.common.fields import normalize_field_name


class ConfigurableFabricator:
    """Configuration-driven fabricator implementation."""

    def __init__(self, config: FabricatorConfig):
        self.config = config

    @property
    def name(self) -> str:
        """Get fabricator name."""
        return self.config.name

    @property
    def part_number_header(self) -> str:
        """Get the column header for fabricator part numbers."""
        return self.config.part_number_header

    def get_part_number(self, item: InventoryItem) -> str:
        """Get the part number for this fabricator from an inventory item."""
        # Try each priority field in order
        for field_name in self.config.part_number_fields:
            # Check first-class InventoryItem attributes
            if field_name == "lcsc" and item.lcsc:
                return item.lcsc
            elif field_name in ["mfgpn", "mpn"] and item.mfgpn:
                return item.mfgpn
            elif (
                field_name == "distributor_part_number" and item.distributor_part_number
            ):
                return item.distributor_part_number

            # Check raw data with normalized field matching
            for raw_key, value in item.raw_data.items():
                if not value:
                    continue
                if normalize_field_name(raw_key) == field_name:
                    return value

        return ""

    def get_name(self, item: InventoryItem) -> str:
        """Get the fabricator name for a specific item."""
        if self.config.dynamic_name and self.config.name_source:
            # Use dynamic name from item (e.g., manufacturer name for Generic)
            if self.config.name_source == "manufacturer" and item.manufacturer:
                return item.manufacturer

        # Use static fabricator name
        return self.config.name

    def get_bom_columns(self) -> Dict[str, str]:
        """Get mapping of fabricator column headers to jBOM internal fields."""
        return self.config.bom_columns

    def matches(self, item: InventoryItem) -> bool:
        """Check if inventory item is supported by this fabricator."""
        if self.config.id == "generic":
            # Generic always matches
            return True

        # For specific fabricators, require a valid part number
        return bool(self.get_part_number(item))

    def get_preset_fields(self, preset_name: str = "default") -> Optional[List[str]]:
        """Get field list for a fabricator-specific preset."""
        if preset_name in self.config.presets:
            preset = self.config.presets[preset_name]
            return preset.get("fields", [])
        return None


class FabricatorRegistry:
    """Registry for managing fabricators from configuration."""

    def __init__(self):
        self._fabricators: Dict[str, ConfigurableFabricator] = {}
        self._load_fabricators()

    def _load_fabricators(self):
        """Load fabricators from configuration."""
        config = get_config()
        self._fabricators.clear()

        for fab_config in config.fabricators:
            fabricator = ConfigurableFabricator(fab_config)
            self._fabricators[fab_config.id.lower()] = fabricator

    def get_fabricator(self, fab_id: str) -> Optional[ConfigurableFabricator]:
        """Get fabricator by ID."""
        return self._fabricators.get(fab_id.lower())

    def get_fabricator_by_cli_flag(self, flag: str) -> Optional[ConfigurableFabricator]:
        """Get fabricator by CLI flag (e.g., '--jlc')."""
        config = get_config()
        fab_config = config.get_fabricator_by_cli_flag(flag)
        if fab_config:
            return self._fabricators.get(fab_config.id.lower())
        return None

    def get_fabricator_by_preset(self, preset: str) -> Optional[ConfigurableFabricator]:
        """Get fabricator by preset name (e.g., '+jlc')."""
        config = get_config()
        fab_config = config.get_fabricator_by_preset(preset)
        if fab_config:
            return self._fabricators.get(fab_config.id.lower())
        return None

    def list_fabricators(self) -> List[str]:
        """Get list of available fabricator IDs."""
        return list(self._fabricators.keys())

    def get_default_fabricator(self) -> ConfigurableFabricator:
        """Get the default (Generic) fabricator."""
        generic = self.get_fabricator("generic")
        if generic:
            return generic

        # Fallback if no generic fabricator configured
        from jbom.common.config import FabricatorConfig

        fallback_config = FabricatorConfig(
            name="Generic",
            id="generic",
            description="Fallback generic fabricator",
            part_number={
                "header": "Manufacturer Part Number",
                "priority_fields": ["mfgpn", "mpn", "lcsc"],
            },
            dynamic_name=True,
            name_source="manufacturer",
        )
        return ConfigurableFabricator(fallback_config)

    def reload(self):
        """Reload fabricators from configuration (for config changes)."""
        self._load_fabricators()


# Global registry instance
_registry_instance: Optional[FabricatorRegistry] = None


def get_fabricator_registry() -> FabricatorRegistry:
    """Get the global fabricator registry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = FabricatorRegistry()
    return _registry_instance


def get_fabricator(fab_id: str) -> ConfigurableFabricator:
    """Get fabricator by ID, with fallback to generic."""
    registry = get_fabricator_registry()
    fabricator = registry.get_fabricator(fab_id)
    if fabricator:
        return fabricator
    return registry.get_default_fabricator()


def get_fabricator_by_cli_flag(flag: str) -> Optional[ConfigurableFabricator]:
    """Get fabricator by CLI flag."""
    registry = get_fabricator_registry()
    return registry.get_fabricator_by_cli_flag(flag)


def get_fabricator_by_preset(preset: str) -> Optional[ConfigurableFabricator]:
    """Get fabricator by preset name."""
    registry = get_fabricator_registry()
    return registry.get_fabricator_by_preset(preset)


def reload_fabricators():
    """Reload fabricators from configuration."""
    global _registry_instance
    if _registry_instance:
        _registry_instance.reload()
    else:
        _registry_instance = FabricatorRegistry()


# Backward compatibility aliases for existing code
class Fabricator:
    """Backward compatibility base class."""

    pass


def get_fabricator_legacy(name: str) -> ConfigurableFabricator:
    """Legacy compatibility function."""
    return get_fabricator(name)
