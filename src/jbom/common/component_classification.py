"""Component classification and categorization utilities.

Phase 1 intent
This module is an extraction point for component classification logic.

We want:
- a clean, testable public API (pure functions)
- an explicit "component classifier" concept so more sophisticated approaches
  (rules/config-driven) can be introduced later without rewriting call sites

For now, the default classifier is a heuristic implementation that mirrors the
existing jbom-new POC behavior.
"""

from __future__ import annotations

from typing import Optional, Protocol

from jbom.common.constants import (
    CATEGORY_FIELDS,
    COMPONENT_TYPE_MAPPING,
    DEFAULT_CATEGORY_FIELDS,
    VALUE_INTERPRETATION,
    ComponentType,
)


class ComponentClassifier(Protocol):
    """Classify a schematic component into a standardized component type."""

    def classify(self, lib_id: str, footprint: str = "") -> Optional[str]:
        """Return a standardized component type (e.g., "RES", "CAP") or None."""


class HeuristicComponentClassifier:
    """Default component classifier.

    This is intentionally simple and pure (no file I/O, no global config).

    Notes:
        - Return values use jbom-new's canonical type identifiers from
          :class:`jbom.common.constants.ComponentType`.
        - This implementation is a direct extraction of the existing
          `jbom.common.component_utils.get_component_type` heuristic.
    """

    def classify(self, lib_id: str, footprint: str = "") -> Optional[str]:
        return _get_component_type_heuristic(lib_id=lib_id, footprint=footprint)


DEFAULT_COMPONENT_CLASSIFIER: ComponentClassifier = HeuristicComponentClassifier()


def normalize_component_type(component_type: str) -> str:
    """Normalize a component type string to a standard category.

    Args:
        component_type: A component type identifier (e.g., "RES", "resistor", "R").

    Returns:
        A normalized component type identifier.

    Notes:
        - If the input already matches a known category, it is returned.
        - Otherwise, the global mapping is applied (e.g., "R" -> "RES").
        - If no mapping exists, the upper-cased value is returned as-is.
    """

    category = component_type.upper() if component_type else ""

    if category in CATEGORY_FIELDS:
        return category
    if category in COMPONENT_TYPE_MAPPING:
        return COMPONENT_TYPE_MAPPING[category]

    return category


def get_category_fields(component_type: str) -> list[str]:
    """Get relevant inventory fields for a component category."""

    normalized_type = normalize_component_type(component_type)
    return CATEGORY_FIELDS.get(normalized_type, DEFAULT_CATEGORY_FIELDS)


def get_value_interpretation(component_type: str) -> Optional[str]:
    """Get what the inventory "Value" field represents for a given category."""

    normalized_type = normalize_component_type(component_type)
    return VALUE_INTERPRETATION.get(normalized_type)


def get_component_type(
    lib_id: str,
    footprint: str = "",
    *,
    classifier: ComponentClassifier = DEFAULT_COMPONENT_CLASSIFIER,
) -> Optional[str]:
    """Determine component type from library ID and footprint.

    Args:
        lib_id: KiCad library ID (e.g., "Device:R").
        footprint: KiCad footprint name.
        classifier: The classifier to use.

    Returns:
        A standardized component type identifier (e.g., "RES", "CAP", "IC")
        or None if unknown.
    """

    # Validation at intake point: callers sometimes pass None-ish values.
    if not lib_id:
        return None

    return classifier.classify(lib_id, footprint)


def _get_component_type_heuristic(lib_id: str, footprint: str = "") -> Optional[str]:
    """Heuristic implementation of component type detection."""

    if not lib_id:
        return None

    # Extract the component part from lib_id (after colon)
    if ":" in lib_id:
        component_part = lib_id.split(":", 1)[1]
    else:
        component_part = lib_id

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
    if component_upper.startswith("LM"):  # Common IC prefix (LM358, etc.)
        return ComponentType.INTEGRATED_CIRCUIT
    if (
        component_upper == "IC"
    ):  # Exact IC designation (avoid false positive in GENERIC, etc.)
        return ComponentType.INTEGRATED_CIRCUIT
    if component_upper.startswith("74"):  # Logic IC family (74HC00, etc.)
        return ComponentType.INTEGRATED_CIRCUIT
    if component_upper.startswith("R") and not _has_ic_indicators(
        component_upper, footprint_upper
    ):
        return ComponentType.RESISTOR
    if component_upper.startswith("C") and not _has_ic_indicators(
        component_upper, footprint_upper
    ):
        return ComponentType.CAPACITOR
    if component_upper.startswith("L") and not _has_ic_indicators(
        component_upper, footprint_upper
    ):
        return ComponentType.INDUCTOR
    if component_upper.startswith("D") and not _has_ic_indicators(
        component_upper, footprint_upper
    ):
        return ComponentType.DIODE
    if component_upper.startswith("Q"):
        return ComponentType.TRANSISTOR
    if component_upper.startswith("U"):  # U prefix typically means IC
        return ComponentType.INTEGRATED_CIRCUIT
    if "CONN" in component_upper or "J" in component_upper:
        return ComponentType.CONNECTOR
    if "SW" in component_upper:
        return ComponentType.SWITCH

    return None


def _is_ic_footprint(footprint_upper: str) -> bool:
    """Return True if the footprint indicates an integrated circuit."""

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
    """Return True if component likely represents an IC despite generic prefixes."""

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

    for pattern in ic_patterns:
        if pattern in component_upper:
            return True

    return _is_ic_footprint(footprint_upper)
