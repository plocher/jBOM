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
    fabricator_id: str = "generic",
    fabricator_presets: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Parse field argument with sophisticated fabricator-aware logic.

    Implements the complex jBOM field selection rules:
    1. If no --fields: use fabricator's default preset
    2. If --fields provided: parse presets and custom fields
    3. Smart fabricator preset injection: if no +fabricator preset in --fields,
       silently append +fabricator preset with deduplication
    4. Support I:/C: prefixes for inventory/component field disambiguation

    Args:
        fields_arg: Field argument string or None
        available_fields: Dict of available field names and descriptions
        fabricator_id: Current fabricator ID (affects default and auto-injection)
        fabricator_presets: Optional fabricator-specific presets from config

    Returns:
        List of normalized field names (deduplicated, preserving order)

    Raises:
        ValueError: If unknown preset or field name is encountered
    """
    # Merge global presets with fabricator-specific presets
    all_presets = FIELD_PRESETS.copy()
    if fabricator_presets:
        all_presets.update(fabricator_presets)

    # Case 1: No fields argument - use fabricator's default preset
    if not fields_arg:
        default_preset = "default"  # Fabricator's default preset
        if fabricator_presets and default_preset in fabricator_presets:
            preset_fields = fabricator_presets[default_preset].get("fields")
            if preset_fields:
                return preset_fields.copy()

        # Fall back to standard preset if fabricator has no default
        standard_preset = all_presets.get("standard")
        if standard_preset and standard_preset.get("fields"):
            return standard_preset["fields"].copy()

        # Ultimate fallback
        return ["reference", "quantity", "value", "footprint"]

    # Case 2: Parse explicit fields argument
    tokens = [t.strip() for t in fields_arg.split(",") if t.strip()]
    result: List[str] = []
    has_fabricator_preset = False

    # Check if fabricator preset is already specified
    fabricator_preset_name = f"+{fabricator_id}"
    for tok in tokens:
        if tok.lower() == fabricator_preset_name.lower():
            has_fabricator_preset = True
            break

    # Process each token
    for tok in tokens:
        if tok.startswith("+"):
            # Preset expansion
            preset_name = tok[1:].lower()
            preset_def = all_presets.get(preset_name)

            if not preset_def:
                # Create helpful error message
                all_preset_names = sorted(
                    set(
                        list(FIELD_PRESETS.keys())
                        + (
                            list(fabricator_presets.keys())
                            if fabricator_presets
                            else []
                        )
                    )
                )
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
                # Try to provide helpful error
                available_list = sorted(available_fields.keys())
                raise ValueError(
                    f"Unknown field: '{tok}' (normalized: '{normalized}'). "
                    f"Available fields: {', '.join(available_list[:10])}..."
                    if len(available_list) > 10
                    else f"Available fields: {', '.join(available_list)}"
                )
            result.append(normalized)

    # Case 3: Smart fabricator preset injection
    # If no fabricator preset was explicitly specified, append it silently
    if not has_fabricator_preset and fabricator_presets:
        fabricator_preset_def = fabricator_presets.get(
            "default"
        ) or fabricator_presets.get(fabricator_id)
        if fabricator_preset_def and fabricator_preset_def.get("fields"):
            result.extend(fabricator_preset_def["fields"])

    # Deduplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for f in result:
        if f not in seen:
            seen.add(f)
            deduped.append(f)

    return deduped if deduped else ["reference", "quantity", "value", "footprint"]


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
