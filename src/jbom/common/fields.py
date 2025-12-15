"""Field normalization and formatting utilities."""
from __future__ import annotations

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


__all__ = ["KNOWN_ACRONYMS", "normalize_field_name", "field_to_header"]
