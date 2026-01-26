"""Component utility functions."""
from typing import Optional

from jbom.common.constants import ComponentType, COMPONENT_TYPE_MAPPING


def get_component_type(lib_id: str, footprint: str = "") -> Optional[str]:
    """Determine component type from library ID and footprint.

    Args:
        lib_id: KiCad library ID (e.g., "Device:R")
        footprint: Component footprint (e.g., "R_0603")

    Returns:
        Component type string or None if unknown
    """
    if not lib_id:
        return None

    # Extract the component part from lib_id (after colon)
    if ":" in lib_id:
        component_part = lib_id.split(":", 1)[1]
    else:
        component_part = lib_id

    # Try to match against known component type mappings
    component_upper = component_part.upper()
    footprint_upper = footprint.upper() if footprint else ""

    # Direct mapping lookup first
    if component_upper in COMPONENT_TYPE_MAPPING:
        return COMPONENT_TYPE_MAPPING[component_upper]

    # Footprint-based detection for ICs (check before generic patterns)
    if _is_ic_footprint(footprint_upper):
        return ComponentType.INTEGRATED_CIRCUIT

    # Pattern-based detection - check specific patterns before generic prefixes
    if "LED" in component_upper:  # Check LED before L prefix
        return ComponentType.LED
    elif component_upper.startswith("LM"):  # Common IC prefix (LM358, etc.)
        return ComponentType.INTEGRATED_CIRCUIT
    elif "IC" in component_upper:  # Generic IC designation
        return ComponentType.INTEGRATED_CIRCUIT
    elif component_upper.startswith("74"):  # Logic IC family (74HC00, etc.)
        return ComponentType.INTEGRATED_CIRCUIT
    elif component_upper.startswith("R") and not _has_ic_indicators(
        component_upper, footprint_upper
    ):
        return ComponentType.RESISTOR
    elif component_upper.startswith("C") and not _has_ic_indicators(
        component_upper, footprint_upper
    ):
        return ComponentType.CAPACITOR
    elif component_upper.startswith("L") and not _has_ic_indicators(
        component_upper, footprint_upper
    ):
        return ComponentType.INDUCTOR
    elif component_upper.startswith("D") and not _has_ic_indicators(
        component_upper, footprint_upper
    ):
        return ComponentType.DIODE
    elif component_upper.startswith("Q"):
        return ComponentType.TRANSISTOR
    elif component_upper.startswith("U"):  # U prefix typically means IC
        return ComponentType.INTEGRATED_CIRCUIT
    elif "CONN" in component_upper or "J" in component_upper:
        return ComponentType.CONNECTOR
    elif "SW" in component_upper:
        return ComponentType.SWITCH

    return None


def _is_ic_footprint(footprint_upper: str) -> bool:
    """Check if footprint indicates an integrated circuit."""
    ic_footprint_patterns = [
        "SOIC",
        "QFP",
        "QFN",
        "BGA",
        "DIP",
        "PDIP",
        "PLCC",
        "LGA",
        "TQFP",
        "LQFP",
        "SSOP",
        "TSSOP",
        "MSOP",
        "SOT23-5",
        "SOT23-6",
        "SC70",
        "WLCSP",
        "UFBGA",
        "VQFN",
        "HVQFN",
        "DFQFN",
        "UDFN",
    ]
    return any(pattern in footprint_upper for pattern in ic_footprint_patterns)


def _has_ic_indicators(component_upper: str, footprint_upper: str) -> bool:
    """Check if component has indicators suggesting it's an IC despite prefix."""
    # IC part number patterns
    ic_patterns = [
        "LM",
        "TL",
        "NE",
        "MC",
        "CD",
        "SN",
        "74",
        "40",
        "AD",
        "MAX",
        "LT",
        "MCP",
        "PIC",
        "ATMEGA",
        "STM32",
        "ESP",
    ]

    # Check for IC-like part numbers
    for pattern in ic_patterns:
        if pattern in component_upper:
            return True

    # Check footprint
    return _is_ic_footprint(footprint_upper)
