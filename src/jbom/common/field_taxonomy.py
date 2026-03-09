"""Field taxonomy for jBOM audit diagnostics.

Defines which schematic component fields are REQUIRED, BEST_PRACTICE, or
OPTIONAL per component category.  This module has no CLI dependencies and
is safe to import from the KiCad Python plugin scripting environment.

Severity levels
---------------
REQUIRED
    Hard error when absent.  The component will produce poor or no matches
    and cannot be reliably sourced without this field.
BEST_PRACTICE
    Informational warning when absent.  Missing this field is not fatal
    but weakens match quality and supplier search accuracy.  The taxonomy
    provides a human-readable suggestion for each best-practice field.
OPTIONAL
    Silent.  Useful when present but not checked by the auditor.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from jbom.common.constants import ComponentType


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------


class FieldSeverity(str, Enum):
    """Severity level for a component field in the jBOM taxonomy."""

    REQUIRED = "REQUIRED"
    BEST_PRACTICE = "BEST_PRACTICE"
    OPTIONAL = "OPTIONAL"


@dataclass(frozen=True)
class FieldSpec:
    """A single field specification in the taxonomy.

    Attributes:
        name: Canonical KiCad property name (case-sensitive, matches the schematic).
        severity: How important this field is for the given category.
        suggestion: Human-readable hint shown in ``BEST_PRACTICE`` audit rows.
            Empty for ``REQUIRED`` and ``OPTIONAL`` specs.
    """

    name: str
    severity: FieldSeverity
    suggestion: str = ""


# ---------------------------------------------------------------------------
# Universal required fields (apply to every component, every category)
# ---------------------------------------------------------------------------

UNIVERSAL_REQUIRED_FIELDS: list[FieldSpec] = [
    FieldSpec("Value", FieldSeverity.REQUIRED),
    FieldSpec("Footprint", FieldSeverity.REQUIRED),
]

# ---------------------------------------------------------------------------
# Universal best-practice fields (apply to every component)
# ---------------------------------------------------------------------------

_UNIVERSAL_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec(
        "Manufacturer",
        FieldSeverity.BEST_PRACTICE,
        "e.g. Vishay, Murata, Texas Instruments",
    ),
    FieldSpec(
        "MFGPN",
        FieldSeverity.BEST_PRACTICE,
        "Manufacturer part number; enables unambiguous supplier search",
    ),
]

# ---------------------------------------------------------------------------
# Category-specific best-practice fields
# ---------------------------------------------------------------------------

_RESISTOR_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec("Tolerance", FieldSeverity.BEST_PRACTICE, "e.g. 1%, 5%, 10%"),
    FieldSpec("Power", FieldSeverity.BEST_PRACTICE, "e.g. 0.1W, 0.25W, 0.5W, 1W"),
]

_CAPACITOR_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec("Voltage", FieldSeverity.BEST_PRACTICE, "e.g. 10V, 16V, 25V, 50V"),
    FieldSpec("Tolerance", FieldSeverity.BEST_PRACTICE, "e.g. 10%, 20%"),
]

_INDUCTOR_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec("Current", FieldSeverity.BEST_PRACTICE, "e.g. 100mA, 1A, 3A"),
    FieldSpec("Power", FieldSeverity.BEST_PRACTICE, "e.g. 0.5W, 1W"),
]

_DIODE_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec("Voltage", FieldSeverity.BEST_PRACTICE, "e.g. 30V, 60V, 100V"),
    FieldSpec("Current", FieldSeverity.BEST_PRACTICE, "e.g. 100mA, 1A, 3A"),
]

_LED_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec(
        "Voltage", FieldSeverity.BEST_PRACTICE, "Forward voltage, e.g. 2.0V, 3.2V"
    ),
    FieldSpec("Current", FieldSeverity.BEST_PRACTICE, "e.g. 5mA, 20mA"),
    FieldSpec("Wavelength", FieldSeverity.BEST_PRACTICE, "e.g. 470nm, 625nm"),
]

_IC_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec("Voltage", FieldSeverity.BEST_PRACTICE, "Supply voltage, e.g. 3.3V, 5V"),
]

_TRANSISTOR_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec("Voltage", FieldSeverity.BEST_PRACTICE, "Vce/Vds max, e.g. 30V, 60V"),
    FieldSpec("Current", FieldSeverity.BEST_PRACTICE, "Ic/Id max, e.g. 100mA, 1A"),
]

_CONNECTOR_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec("Pitch", FieldSeverity.BEST_PRACTICE, "e.g. 2.54mm, 1.25mm"),
]

_REGULATOR_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec("Voltage", FieldSeverity.BEST_PRACTICE, "Output voltage, e.g. 3.3V, 5V"),
    FieldSpec(
        "Current", FieldSeverity.BEST_PRACTICE, "Max output current, e.g. 1A, 3A"
    ),
]

_OSCILLATOR_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec("Frequency", FieldSeverity.BEST_PRACTICE, "e.g. 8MHz, 16MHz, 25MHz"),
    FieldSpec("Stability", FieldSeverity.BEST_PRACTICE, "e.g. ±20ppm, ±50ppm"),
]

_FUSE_BEST_PRACTICE: list[FieldSpec] = [
    FieldSpec(
        "Current", FieldSeverity.BEST_PRACTICE, "Rated current, e.g. 500mA, 1A, 3A"
    ),
    FieldSpec("Voltage", FieldSeverity.BEST_PRACTICE, "Rated voltage, e.g. 32V, 125V"),
]

# ---------------------------------------------------------------------------
# Mapping: category -> extra best-practice fields (in addition to universal)
# ---------------------------------------------------------------------------

CATEGORY_BEST_PRACTICE: dict[str, list[FieldSpec]] = {
    ComponentType.RESISTOR: _RESISTOR_BEST_PRACTICE,
    ComponentType.CAPACITOR: _CAPACITOR_BEST_PRACTICE,
    ComponentType.INDUCTOR: _INDUCTOR_BEST_PRACTICE,
    ComponentType.DIODE: _DIODE_BEST_PRACTICE,
    ComponentType.LED: _LED_BEST_PRACTICE,
    ComponentType.INTEGRATED_CIRCUIT: _IC_BEST_PRACTICE,
    ComponentType.MICROCONTROLLER: _IC_BEST_PRACTICE,
    ComponentType.TRANSISTOR: _TRANSISTOR_BEST_PRACTICE,
    ComponentType.CONNECTOR: _CONNECTOR_BEST_PRACTICE,
    ComponentType.REGULATOR: _REGULATOR_BEST_PRACTICE,
    ComponentType.OSCILLATOR: _OSCILLATOR_BEST_PRACTICE,
    ComponentType.FUSE: _FUSE_BEST_PRACTICE,
    ComponentType.SWITCH: [],
    ComponentType.RELAY: [],
    ComponentType.ANALOG: _IC_BEST_PRACTICE,
    ComponentType.SILK_SCREEN: [],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_field_specs(category: Optional[str]) -> list[FieldSpec]:
    """Return all field specs applicable to the given component category.

    The returned list starts with the universal required fields, followed by
    universal best-practice fields, then category-specific best-practice
    fields.  The ordering puts the most critical fields first.

    Args:
        category: Component category string (e.g. ``ComponentType.RESISTOR``).
            ``None`` or unrecognised categories return only the universal fields.

    Returns:
        Ordered list of :class:`FieldSpec` objects.
    """
    specs: list[FieldSpec] = list(UNIVERSAL_REQUIRED_FIELDS)
    specs.extend(_UNIVERSAL_BEST_PRACTICE)

    cat_key = (category or "").upper()
    extra = CATEGORY_BEST_PRACTICE.get(cat_key, [])
    specs.extend(extra)

    return specs


def get_required_fields() -> list[FieldSpec]:
    """Return the universal required field specs (Value + Footprint).

    Returns:
        List of :class:`FieldSpec` objects with ``severity=REQUIRED``.
    """
    return list(UNIVERSAL_REQUIRED_FIELDS)


def get_best_practice_fields(category: Optional[str]) -> list[FieldSpec]:
    """Return only best-practice field specs for the given category.

    Includes both universal best-practice fields (Manufacturer, MFGPN) and
    category-specific best-practice fields.

    Args:
        category: Component category string.

    Returns:
        List of :class:`FieldSpec` objects with ``severity=BEST_PRACTICE``.
    """
    specs: list[FieldSpec] = list(_UNIVERSAL_BEST_PRACTICE)
    cat_key = (category or "").upper()
    specs.extend(CATEGORY_BEST_PRACTICE.get(cat_key, []))
    return specs


__all__ = [
    "FieldSeverity",
    "FieldSpec",
    "UNIVERSAL_REQUIRED_FIELDS",
    "CATEGORY_BEST_PRACTICE",
    "get_field_specs",
    "get_required_fields",
    "get_best_practice_fields",
]
