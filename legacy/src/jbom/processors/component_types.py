"""
Component type detection and categorization utilities.

Provides functions to identify component types from KiCad library IDs and footprints,
and to retrieve category-specific field mappings.
"""

from typing import List, Optional
from jbom.processors.classifier import get_engine

from jbom.common.constants import (
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
    Delegates to the configuration-driven ClassificationEngine.

    Args:
        lib_id: Component library identifier (e.g., "Device:R", "SPCoast:resistor")
        footprint: PCB footprint name (e.g., "PCM_SPCoast:0603-RES")

    Returns:
        Component type string (RES, CAP, IND, etc.) or None if unrecognized
    """
    return get_engine().classify(lib_id, footprint)
