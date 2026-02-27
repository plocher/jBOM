"""Field normalization and formatting utilities.

Provides functions to normalize field names to canonical format and convert
them back to human-readable headers for CSV output.
"""
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
    """Normalize field names to canonical snake_case format.

    Accepts: snake_case, Title Case, CamelCase, spaces, mixed formats.
    Examples: 'match_quality', 'Match Quality', 'MatchQuality', 'MATCH_QUALITY' -> 'match_quality'

    Args:
        field: Field name to normalize

    Returns:
        Normalized field name in snake_case
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
    """Convert normalized field name to human-readable header for CSV.

    Uses Title Case with special handling for known acronyms.
    Examples:
        'match_quality' -> 'Match Quality'
        'lcsc' -> 'LCSC'
        'i:package' -> 'I:Package'
        'mfgpn' -> 'MFGPN'

    Args:
        field: Normalized field name

    Returns:
        Human-readable header string
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
    "default": {
        "fields": [
            "reference",
            "quantity",
            "description",
            "value",
            "footprint",
            "manufacturer",
            "mfgpn",
            "fabricator",
            "fabricator_part_number",
            "datasheet",
            "smd",
        ],
        "description": "Default BOM fields including Manufacturer, MFGPN, and Fabricator info",
    },
    "standard": {
        "fields": [
            "reference",
            "quantity",
            "description",
            "value",
            "footprint",
            "manufacturer",
            "mfgpn",
            "fabricator",
            "fabricator_part_number",
            "datasheet",
            "smd",
        ],
        "description": "Legacy alias for default preset",
    },
    "generic": {
        "fields": [
            "reference",
            "quantity",
            "description",
            "value",
            "footprint",
            "manufacturer",
            "mfgpn",
            "fabricator",
            "fabricator_part_number",
            "smd",
        ],
        "description": "Generic fabricator format with manufacturer information",
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


def preset_fields(
    preset: str, include_verbose: bool = False, any_notes: bool = False
) -> List[str]:
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
    preset = (preset or "default").lower()

    if preset not in FIELD_PRESETS:
        available = ", ".join(FIELD_PRESETS.keys())
        raise ValueError(f"Unknown preset '{preset}'. Available: {available}")

    preset_def = FIELD_PRESETS[preset]
    if preset_def["fields"] is None:
        # Special case for "all" - would need to be populated by caller
        # with all available fields from the component data
        raise ValueError(
            "'all' preset requires component data to determine available fields"
        )

    fields = preset_def["fields"].copy()

    # Add optional fields
    if include_verbose:
        if "match_quality" not in fields:
            fields.append("match_quality")
        if "priority" not in fields:
            fields.append("priority")

    if any_notes and "notes" not in fields:
        fields.append("notes")

    return fields


def get_available_presets() -> Dict[str, str]:
    """Get all available preset names and descriptions.

    Returns:
        Dict mapping preset names to their descriptions
    """
    return {name: info["description"] for name, info in FIELD_PRESETS.items()}
