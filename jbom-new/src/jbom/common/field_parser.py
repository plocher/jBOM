"""Field argument parser with preset support.

Handles parsing of field arguments that support both preset names (+preset)
and custom field lists, including mixed syntax like +preset,custom,I:field.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any

from .fields import normalize_field_name, FIELD_PRESETS


def parse_fields_argument(
    fields_arg: Optional[str],
    available_fields: Dict[str, str],
    fabricator_presets: Optional[Dict[str, Any]] = None,
    default_preset: str = "standard",
) -> List[str]:
    """Parse field argument that may contain presets and custom fields.

    Supports:
    - Preset names with + prefix: +jlc, +standard, +minimal, +all
    - Custom field names: Reference,Value,LCSC
    - Mixed: +jlc,CustomField,I:Tolerance
    - Fabricator-specific presets from fabricator configs

    Args:
        fields_arg: Field argument string or None
        available_fields: Dict of available field names and descriptions
        fabricator_presets: Optional fabricator-specific presets from config
        default_preset: Default preset to use if fields_arg is None

    Returns:
        List of normalized field names (deduplicated, in order)

    Raises:
        ValueError: If unknown preset or field name is encountered
    """
    # Merge global presets with fabricator-specific presets
    all_presets = FIELD_PRESETS.copy()
    if fabricator_presets:
        all_presets.update(fabricator_presets)

    if not fields_arg:
        # Use default preset
        preset_def = all_presets.get(default_preset)
        if not preset_def:
            # Fall back to global default if fabricator-specific default doesn't exist
            preset_def = FIELD_PRESETS.get(default_preset)

        if preset_def and preset_def.get("fields"):
            return preset_def["fields"].copy()
        else:
            # 'all' preset or missing - return all available fields
            return list(available_fields.keys())

    tokens = [t.strip() for t in fields_arg.split(",") if t.strip()]
    result: List[str] = []

    for tok in tokens:
        if tok.startswith("+"):
            # Preset expansion
            preset_name = tok[1:].lower()
            preset_def = all_presets.get(preset_name)

            if not preset_def:
                # Create helpful error message with available presets
                global_presets = list(FIELD_PRESETS.keys())
                fab_presets = (
                    list(fabricator_presets.keys()) if fabricator_presets else []
                )
                all_preset_names = sorted(set(global_presets + fab_presets))
                valid = ", ".join(f"+{p}" for p in all_preset_names)
                raise ValueError(f"Unknown preset: {tok} (available: {valid})")

            preset_fields = preset_def.get("fields")
            if preset_fields is None:
                # 'all' preset - expand to all available fields
                result.extend(available_fields.keys())
            else:
                result.extend(preset_fields)
        else:
            # Custom field name
            normalized = normalize_field_name(tok)
            if normalized not in available_fields:
                # Try to find a close match or provide helpful error
                available_list = sorted(available_fields.keys())
                raise ValueError(
                    f"Unknown field: '{tok}' (normalized: '{normalized}'). "
                    f"Available fields: {', '.join(available_list[:10])}..."
                    if len(available_list) > 10
                    else f"Available fields: {', '.join(available_list)}"
                )
            result.append(normalized)

    # Deduplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for f in result:
        if f not in seen:
            seen.add(f)
            deduped.append(f)

    # If we ended up with no fields, fall back to default
    if not deduped:
        return parse_fields_argument(
            None, available_fields, fabricator_presets, default_preset
        )

    return deduped


def validate_fields_against_available(
    fields: List[str], available_fields: Dict[str, str]
) -> List[str]:
    """Validate that all fields in the list are available.

    Args:
        fields: List of field names to validate
        available_fields: Dict of available fields

    Returns:
        List of validated field names

    Raises:
        ValueError: If any field is not available
    """
    invalid_fields = []
    for field in fields:
        if field not in available_fields:
            invalid_fields.append(field)

    if invalid_fields:
        available_list = sorted(available_fields.keys())
        raise ValueError(
            f"Invalid fields: {', '.join(invalid_fields)}. "
            f"Available: {', '.join(available_list)}"
        )

    return fields


def expand_all_preset(available_fields: Dict[str, str]) -> List[str]:
    """Expand the special 'all' preset to include all available fields.

    Args:
        available_fields: Dict of available field names

    Returns:
        List of all available field names
    """
    return list(available_fields.keys())


def get_preset_fields(
    preset_name: str, fabricator_presets: Optional[Dict[str, Any]] = None
) -> Optional[List[str]]:
    """Get fields for a specific preset by name.

    Args:
        preset_name: Name of preset to look up
        fabricator_presets: Optional fabricator-specific presets

    Returns:
        List of fields for the preset, or None if not found
    """
    # Check fabricator presets first, then global presets
    if fabricator_presets and preset_name in fabricator_presets:
        preset_def = fabricator_presets[preset_name]
    else:
        preset_def = FIELD_PRESETS.get(preset_name)

    if preset_def:
        return preset_def.get("fields")
    return None


def list_available_presets(
    fabricator_presets: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """List all available presets with descriptions.

    Args:
        fabricator_presets: Optional fabricator-specific presets

    Returns:
        Dict mapping preset names to descriptions
    """
    result = {}

    # Add global presets
    for name, preset in FIELD_PRESETS.items():
        result[name] = preset.get("description", "")

    # Add fabricator-specific presets
    if fabricator_presets:
        for name, preset in fabricator_presets.items():
            result[name] = preset.get("description", "Fabricator-specific preset")

    return result
