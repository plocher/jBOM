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

    # Direct mapping lookup
    if component_upper in COMPONENT_TYPE_MAPPING:
        return COMPONENT_TYPE_MAPPING[component_upper]

    # Pattern-based detection
    if component_upper.startswith("R"):
        return ComponentType.RESISTOR
    elif component_upper.startswith("C"):
        return ComponentType.CAPACITOR
    elif component_upper.startswith("L"):
        return ComponentType.INDUCTOR
    elif component_upper.startswith("D"):
        return ComponentType.DIODE
    elif component_upper.startswith("Q"):
        return ComponentType.TRANSISTOR
    elif component_upper.startswith("U"):
        return ComponentType.INTEGRATED_CIRCUIT
    elif "LED" in component_upper:
        return ComponentType.LED
    elif "CONN" in component_upper or "J" in component_upper:
        return ComponentType.CONNECTOR
    elif "SW" in component_upper:
        return ComponentType.SWITCH

    return None
