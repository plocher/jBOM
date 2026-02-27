"""Field preset registry and parsing system for generators.

Provides centralized field selection and preset management shared across
all generators (BOM, placement, etc).
"""
from __future__ import annotations
from typing import Dict, List, Optional

from .fields import normalize_field_name

__all__ = [
    "FieldPresetRegistry",
    "parse_fields_argument",
]


class FieldPresetRegistry:
    """Registry for field presets across all generators.

    Manages preset definitions and provides parsing of field arguments
    that support both preset names (+preset) and custom field lists.
    """

    def __init__(self):
        """Initialize empty preset registry."""
        self._presets: Dict[str, Dict[str, any]] = {}

    def register_preset(
        self, name: str, fields: Optional[List[str]], description: str
    ) -> None:
        """Register a field preset.

        Args:
            name: Preset name (used with + prefix in CLI)
            fields: List of field names, or None for 'all fields'
            description: Human-readable description of preset
        """
        self._presets[name.lower()] = {
            "fields": fields,
            "description": description,
        }

    def get_preset(self, name: str) -> Optional[List[str]]:
        """Get field list for a preset.

        Args:
            name: Preset name

        Returns:
            List of field names, or None if preset not found or is 'all'
        """
        preset = self._presets.get(name.lower())
        return preset["fields"] if preset else None

    def list_presets(self) -> List[str]:
        """List all registered preset names.

        Returns:
            List of preset names
        """
        return sorted(self._presets.keys())

    def parse_fields_argument(
        self,
        fields_arg: Optional[str],
        available_fields: Dict[str, str],
        default_preset: str = "standard",
    ) -> List[str]:
        """Parse field argument that may contain presets and custom fields.

        Supports:
        - Preset names with + prefix: +jlc, +standard, +minimal, +all
        - Custom field names: Reference,Value,LCSC
        - Mixed: +jlc,CustomField,I:Tolerance

        Args:
            fields_arg: Field argument string or None
            available_fields: Dict of available field names and descriptions
            default_preset: Default preset to use if fields_arg is None

        Returns:
            List of normalized field names (deduplicated, in order)

        Raises:
            ValueError: If unknown preset or field name is encountered
        """
        if not fields_arg:
            # Use default preset
            preset_fields = self.get_preset(default_preset)
            if preset_fields is None:
                # 'all' preset - return all available fields
                return list(available_fields.keys())
            return preset_fields

        tokens = [t.strip() for t in fields_arg.split(",") if t.strip()]
        result: List[str] = []

        for tok in tokens:
            if tok.startswith("+"):
                # Preset expansion
                preset_name = tok[1:].lower()
                if preset_name not in self._presets:
                    valid = ", ".join(f"+{p}" for p in self.list_presets())
                    raise ValueError(f"Unknown preset: {tok} (valid: {valid})")

                preset_fields = self.get_preset(preset_name)
                if preset_fields is None:
                    # 'all' preset
                    result.extend(available_fields.keys())
                else:
                    result.extend(preset_fields)
            else:
                # Custom field name
                normalized = normalize_field_name(tok)
                if normalized not in available_fields:
                    raise ValueError(f"Unknown field: {tok}")
                result.append(normalized)

        # Deduplicate while preserving order
        seen = set()
        deduped: List[str] = []
        for f in result:
            if f not in seen:
                seen.add(f)
                deduped.append(f)

        return deduped or self.parse_fields_argument(
            None, available_fields, default_preset
        )


def parse_fields_argument(
    fields_arg: Optional[str],
    available_fields: Dict[str, str],
    presets: Dict[str, Dict],
    default_preset: str = "standard",
) -> List[str]:
    """Standalone function to parse field arguments.

    This is a convenience function that creates a temporary registry
    and uses it to parse the field argument.

    Args:
        fields_arg: Field argument string or None
        available_fields: Dict of available field names
        presets: Dict of preset definitions
        default_preset: Default preset name

    Returns:
        List of normalized field names
    """
    registry = FieldPresetRegistry()
    for name, preset_def in presets.items():
        registry.register_preset(
            name, preset_def.get("fields"), preset_def.get("description", "")
        )

    return registry.parse_fields_argument(fields_arg, available_fields, default_preset)
