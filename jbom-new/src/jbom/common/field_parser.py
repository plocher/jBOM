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
    context: str = "bom",  # "bom" or "pos"
) -> List[str]:
    """Parse field argument with simple, predictable logic.

    Simple rules:
    1. If no --fields: use fabricator's default preset
    2. If --fields provided: use exactly what user specified (presets + custom)
    3. Always apply fabricator column mapping to final fields

    Args:
        fields_arg: Field argument string or None
        available_fields: Dict of available field names and descriptions
        fabricator_id: Current fabricator ID (used for default preset)
        fabricator_presets: Optional fabricator-specific presets from config
        context: Context for field selection ("bom" or "pos")

    Returns:
        List of normalized field names (deduplicated, preserving order)

    Raises:
        ValueError: If unknown preset or field name is encountered
    """
    # Merge global presets with fabricator-specific presets
    all_presets = FIELD_PRESETS.copy()
    if fabricator_presets:
        all_presets.update(fabricator_presets)

    # Case 1: No fields argument (None) - use context-appropriate defaults
    if fields_arg is None:
        if context == "pos":
            # For POS, use fabricator's column mapping to determine defaults
            from jbom.config.fabricators import get_fabricator_default_fields

            default_fields = get_fabricator_default_fields(fabricator_id, context)
            if default_fields:
                return default_fields.copy()

            # Fallback for POS if no fabricator mapping exists
            return ["reference", "x", "y", "rotation", "side", "footprint", "package"]
        else:
            # For BOM, use fabricator presets first, then global presets
            if fabricator_presets and "default" in fabricator_presets:
                preset_fields = fabricator_presets["default"].get("fields")
                if preset_fields:
                    return preset_fields.copy()

            # Fall back to standard preset for BOM
            standard_preset = all_presets.get("standard")
            if standard_preset and standard_preset.get("fields"):
                return standard_preset["fields"].copy()

            # Ultimate fallback for BOM
            return ["reference", "quantity", "value", "footprint"]

    # Case 2: User provided fields - parse exactly what they specified
    # Build tokens, trimming whitespace and surrounding quotes per token
    raw = [t.strip() for t in fields_arg.split(",")]
    tokens: List[str] = []
    for tok in raw:
        if not tok:
            continue
        if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
            tok = tok[1:-1].strip()
        if tok:
            tokens.append(tok)

    # If no valid tokens after filtering, this means empty/quoted-empty/whitespace-only
    if not tokens:
        raise ValueError("--fields parameter cannot be empty")

    result: List[str] = []

    for tok in tokens:
        if tok.startswith("+"):
            # Try preset expansion first
            preset_name = tok[1:].lower()
            preset_def = all_presets.get(preset_name)

            if preset_def:
                # It's a valid preset
                preset_fields = preset_def.get("fields")
                if preset_fields is None:
                    # 'all' preset
                    result.extend(available_fields.keys())
                else:
                    result.extend(preset_fields)
            else:
                # Try as a field addition - normalize and check if it's a valid field
                field_name = normalize_field_name(tok[1:])
                if field_name in available_fields:
                    # It's a field addition - add appropriate context defaults first if result is empty
                    if not result:
                        # For + syntax with non-generic fabricator, use fabricator defaults
                        # For + syntax with generic fabricator, use standard field sets
                        if fabricator_id != "generic":
                            # Use fabricator-specific defaults
                            from jbom.config.fabricators import (
                                get_fabricator_default_fields,
                            )

                            fabricator_defaults = get_fabricator_default_fields(
                                fabricator_id, context
                            )
                            if fabricator_defaults:
                                result.extend(fabricator_defaults)
                            else:
                                # Fallback to standard if fabricator has no defaults
                                if context == "pos":
                                    result.extend(
                                        [
                                            "reference",
                                            "x",
                                            "y",
                                            "rotation",
                                            "side",
                                            "footprint",
                                            "package",
                                        ]
                                    )
                                else:
                                    result.extend(
                                        ["reference", "quantity", "value", "footprint"]
                                    )
                        else:
                            # For generic fabricator, use standard field sets for predictable behavior
                            if context == "pos":
                                result.extend(
                                    [
                                        "reference",
                                        "x",
                                        "y",
                                        "rotation",
                                        "side",
                                        "footprint",
                                        "package",
                                    ]
                                )
                            else:
                                result.extend(
                                    ["reference", "quantity", "value", "footprint"]
                                )

                    # Add the requested field
                    result.append(field_name)
                else:
                    # Not a preset or field - show error with both options
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
                    available_fields_list = sorted(available_fields.keys())
                    valid_presets = ", ".join(f"+{p}" for p in all_preset_names)
                    valid_fields = ", ".join(f"+{f}" for f in available_fields_list[:5])
                    raise ValueError(
                        f"Unknown preset or field: {tok}. Available presets: {valid_presets}. "
                        f"Available fields for addition: {valid_fields}..."
                    )
        else:
            # Custom field name
            normalized = normalize_field_name(tok)
            if normalized not in available_fields:
                available_list = sorted(available_fields.keys())
                # Format field names as proper headers for user-friendly error messages
                from .fields import field_to_header

                available_headers = [field_to_header(field) for field in available_list]
                raise ValueError(
                    f"Invalid field: {tok}. Available fields: {', '.join(available_headers)}"
                )
            result.append(normalized)

    # Deduplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for f in result:
        if f not in seen:
            seen.add(f)
            deduped.append(f)

    # Final fallback if no fields were selected
    if not deduped:
        if context == "pos":
            return ["reference", "x", "y", "rotation", "side", "footprint", "package"]
        else:
            return ["reference", "quantity", "value", "footprint"]

    return deduped


def check_fabricator_field_completeness(
    selected_fields: List[str],
    fabricator_id: str,
    fabricator_presets: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Check if selected fields are missing important fabricator-specific fields.

    Args:
        selected_fields: Fields selected by user
        fabricator_id: Current fabricator ID
        fabricator_presets: Fabricator-specific presets

    Returns:
        Warning message if important fields are missing, None otherwise
    """
    if not fabricator_presets:
        return None

    # Get fabricator's default/recommended fields
    default_preset = fabricator_presets.get("default")
    if not default_preset or not default_preset.get("fields"):
        return None

    recommended_fields = set(default_preset["fields"])
    selected_fields_set = set(selected_fields)

    # Check for critical missing fields (fabricator part number, etc.)
    critical_missing = recommended_fields - selected_fields_set
    important_missing = [
        f
        for f in critical_missing
        if f in ["fabricator_part_number", "reference", "quantity", "value"]
    ]

    if important_missing:
        return f"Warning: Missing important {fabricator_id} fields: {', '.join(important_missing)}"

    return None


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
        # Format field names as proper headers for user-friendly error messages
        from .fields import field_to_header

        available_headers = [field_to_header(field) for field in available_list]
        # Use singular form for single invalid field to match test expectations
        if len(invalid_fields) == 1:
            raise ValueError(
                f"Invalid field: {invalid_fields[0]}. "
                f"Available fields: {', '.join(available_headers)}"
            )
        else:
            raise ValueError(
                f"Invalid fields: {', '.join(invalid_fields)}. "
                f"Available fields: {', '.join(available_headers)}"
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
