"""Field normalization and formatting utilities."""
from __future__ import annotations
from typing import List, Dict

# Known acronyms in PCB/electronics domain (lowercase for matching)
KNOWN_ACRONYMS = {
    "lcsc",
    "smd",
    "pcb",
    "bom",
    "dnp",
    "pth",
    "ipn",
    "mfgpn",
    "jlc",
    "jlcpcb",
    "csv",
    "xlsx",
    "usb",
    "uart",
    "i2c",
    "spi",
    "led",
    "pwm",
    "adc",
    "dac",
    "ic",
    "rf",
    "esd",
    "emi",
    "emc",
    "url",
    "pdf",
    "png",
    "jpg",
    "via",
    "gnd",
    "vcc",
    "can",
    "psu",
}


def normalize_field_name(field: str) -> str:
    """
    Normalize field names to canonical snake_case format.
    Accepts: snake_case, Title Case, CamelCase, spaces, mixed formats.
    Examples: 'match_quality', 'Match Quality', 'MatchQuality', 'MATCH_QUALITY' -> 'match_quality'
    """
    if not field:
        return ""

    # Handle prefixes (I: and C:) separately
    prefix = ""
    if field.lower().startswith("i:"):
        prefix = "i:"
        field = field[2:]
    elif field.lower().startswith("c:"):
        prefix = "c:"
        field = field[2:]

    # Replace spaces and hyphens with underscores
    field = field.replace(" ", "_").replace("-", "_")

    # Insert underscores before uppercase letters (for CamelCase like MatchQuality -> match_quality)
    # But avoid double underscores
    result = []
    for i, char in enumerate(field):
        if i > 0 and char.isupper() and field[i - 1].islower():
            result.append("_")
        result.append(char.lower())

    # Clean up multiple underscores
    normalized = "".join(result)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")

    return prefix + normalized.strip("_")


def field_to_header(field: str) -> str:
    """
    Convert normalized field name to human-readable header for CSV.
    Uses Title Case with special handling for known acronyms.
    Examples:
        'match_quality' -> 'Match Quality'
        'lcsc' -> 'LCSC'
        'i:package' -> 'I:Package'
        'mfgpn' -> 'MFGPN'
    """
    if not field:
        return ""

    # Handle prefixes
    prefix = ""
    if field.lower().startswith("i:"):
        prefix = "I:"
        field = field[2:]
    elif field.lower().startswith("c:"):
        prefix = "C:"
        field = field[2:]

    # Split on underscores and handle each part
    parts = field.split("_")
    result_parts = []

    for part in parts:
        if not part:
            continue
        lower_part = part.lower()
        # Check if this part is a known acronym
        if lower_part in KNOWN_ACRONYMS:
            result_parts.append(part.upper())
        else:
            result_parts.append(part.capitalize())

    header_part = " ".join(result_parts)
    return prefix + header_part if prefix else header_part


# Field presets - easily extensible data structure
# All field names stored in normalized snake_case internally
# Standard BOM fields don't need qualification (reference, quantity, value, etc.)
# Inventory-specific fields are qualified with i: to avoid ambiguity
FIELD_PRESETS = {
    "standard": {
        "fields": [
            "reference",
            "quantity",
            "description",
            "value",
            "footprint",
            "lcsc",
            "datasheet",
            "smd",
        ],
        "description": "Comprehensive set with all standard BOM fields",
    },
    "jlc": {
        "fields": ["reference", "quantity", "value", "i:package", "lcsc", "smd"],
        "description": "JLCPCB requirements: Reference Designator, Quantity, Value, Package, LCSC Part Number",
    },
    "minimal": {
        "fields": ["reference", "quantity", "value", "lcsc"],
        "description": "Bare minimum: reference, qty, value, and LCSC part number",
    },
    "all": {
        "fields": None,  # Special case: means "include all available fields"
        "description": "All available fields from inventory and components",
    },
}


def preset_fields(preset: str, include_verbose: bool, any_notes: bool) -> List[str]:
    """Build a preset field list with optional verbose/notes fields.

    Args:
        preset: Preset name (key from FIELD_PRESETS)
        include_verbose: Add match_quality and priority columns
        any_notes: Add notes column if there are notes in BOM

    Returns:
        List of field names for the preset (normalized snake_case)

    Raises:
        ValueError: If preset name is unknown
    """
    preset = (preset or "standard").lower()

    if preset not in FIELD_PRESETS:
        raise ValueError(
            f"Unknown preset: {preset} (valid: {', '.join(FIELD_PRESETS.keys())})"
        )

    preset_def = FIELD_PRESETS[preset]

    # Special case: 'all' preset is handled later when we know available fields
    if preset_def["fields"] is None:
        return []  # Placeholder, will be expanded in parse_fields_argument

    result = list(preset_def["fields"])

    if include_verbose:
        result.append("match_quality")
    if any_notes:
        result.append("notes")
    if include_verbose:
        result.append("priority")

    return result


def parse_fields_argument(
    fields_arg: str,
    available_fields: Dict[str, str],
    include_verbose: bool,
    any_notes: bool,
) -> List[str]:
    """
    Parse --fields argument which can contain:
    1. Preset names with + prefix: +jlc, +standard, +minimal, +all
    2. Comma-separated field names (case-insensitive, various formats)
    3. Mix of presets and fields: +jlc,CustomField1,CustomField2

    User input is normalized: snake_case, Title Case, CamelCase, spaces all accepted.
    Returns expanded field list (normalized snake_case) or raises ValueError for invalid fields/presets.
    """
    if not fields_arg:
        return preset_fields("standard", include_verbose, any_notes)

    tokens = [t.strip() for t in fields_arg.split(",") if t.strip()]
    result = []
    known_presets = set(FIELD_PRESETS.keys())

    for token in tokens:
        if token.startswith("+"):
            # This is a preset expansion
            preset_name = token[1:].lower()
            if preset_name not in known_presets:
                raise ValueError(
                    f"Unknown preset: +{preset_name} (valid: {', '.join('+' + p for p in sorted(known_presets))})"
                )

            # Handle special case: +all expands to all available fields
            if preset_name == "all":
                result.extend(sorted(available_fields.keys()))
            else:
                # Expand preset inline
                preset_fields_list = preset_fields(
                    preset_name, include_verbose, any_notes
                )
                result.extend(preset_fields_list)
        else:
            # This is a field name - normalize and validate it
            normalized_token = normalize_field_name(token)
            if normalized_token not in available_fields:
                raise ValueError(
                    f"Unknown field: {token}. Use --list-fields to see available fields."
                )
            result.append(normalized_token)

    # Remove duplicates while preserving order
    seen = set()
    deduped = []
    for f in result:
        if f not in seen:
            seen.add(f)
            deduped.append(f)

    return deduped if deduped else preset_fields("standard", include_verbose, any_notes)


__all__ = [
    "KNOWN_ACRONYMS",
    "normalize_field_name",
    "field_to_header",
    "FIELD_PRESETS",
    "preset_fields",
    "parse_fields_argument",
]
