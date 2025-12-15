"""
Component type detection and categorization utilities.

Provides functions to identify component types from KiCad library IDs and footprints,
and to retrieve category-specific field mappings.
"""

from typing import List, Optional

from jbom.common.constants import (
    ComponentType,
    CATEGORY_FIELDS,
    DEFAULT_CATEGORY_FIELDS,
    COMPONENT_TYPE_MAPPING,
    VALUE_INTERPRETATION,
)


def normalize_component_type(component_type: str) -> str:
    """Normalize component type string to standard category using global mapping"""
    category = component_type.upper() if component_type else ""

    # Try direct lookup first, then mapped lookup
    if category in CATEGORY_FIELDS:
        return category
    elif category in COMPONENT_TYPE_MAPPING:
        return COMPONENT_TYPE_MAPPING[category]
    else:
        return category  # Return as-is if not found


def get_category_fields(component_type: str) -> List[str]:
    """Get relevant fields for a component category"""
    normalized_type = normalize_component_type(component_type)

    if normalized_type in CATEGORY_FIELDS:
        return CATEGORY_FIELDS[normalized_type]
    else:
        # Default to common fields plus some general ones
        return DEFAULT_CATEGORY_FIELDS


def get_value_interpretation(component_type: str) -> Optional[str]:
    """Get what the Value field represents for a given component category"""
    normalized_type = normalize_component_type(component_type)
    return VALUE_INTERPRETATION.get(normalized_type, None)


def get_component_type(lib_id: str, footprint: str) -> Optional[str]:
    """Determine component type from lib_id or footprint.

    This is used by InventoryMatcher to ensure consistent component type detection.

    Args:
        lib_id: Component library identifier (e.g., "Device:R", "SPCoast:resistor")
        footprint: PCB footprint name (e.g., "PCM_SPCoast:0603-RES")

    Returns:
        Component type string (RES, CAP, IND, etc.) or None if unrecognized
    """
    lib_id = lib_id.lower()
    footprint = footprint.lower()

    if "resistor" in lib_id or "r" == lib_id.split(":")[-1] or "res" in footprint:
        return ComponentType.RESISTOR
    elif "capacitor" in lib_id or "c" == lib_id.split(":")[-1] or "cap" in footprint:
        return ComponentType.CAPACITOR
    elif "diode" in lib_id or "d" == lib_id.split(":")[-1] or "diode" in footprint:
        return ComponentType.DIODE
    elif "led" in lib_id or "led" in footprint:
        return ComponentType.LED
    elif "inductor" in lib_id or "l" == lib_id.split(":")[-1]:
        return ComponentType.INDUCTOR
    elif "connector" in lib_id or "conn" in lib_id:
        return ComponentType.CONNECTOR
    elif "switch" in lib_id or "sw" in lib_id:
        return ComponentType.SWITCH
    elif "transistor" in lib_id or lib_id.split(":")[-1].startswith("q"):
        return ComponentType.TRANSISTOR
    elif (
        "ic" in lib_id
        or "mcu" in lib_id
        or "microcontroller" in lib_id
        or lib_id.split(":")[-1].startswith("u")
        or lib_id.split(":")[-1] == "ic"
    ):
        return ComponentType.INTEGRATED_CIRCUIT

    return None
