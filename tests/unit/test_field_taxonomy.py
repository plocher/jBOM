"""Unit tests for jbom.common.field_taxonomy."""

from __future__ import annotations

import pytest

from jbom.common.constants import ComponentType
from jbom.common.field_taxonomy import (
    CATEGORY_BEST_PRACTICE,
    UNIVERSAL_REQUIRED_FIELDS,
    FieldSeverity,
    FieldSpec,
    get_best_practice_fields,
    get_field_specs,
    get_required_fields,
)


# ---------------------------------------------------------------------------
# FieldSpec dataclass
# ---------------------------------------------------------------------------


def test_fieldspec_is_frozen() -> None:
    spec = FieldSpec("Value", FieldSeverity.REQUIRED)
    with pytest.raises((AttributeError, TypeError)):
        spec.name = "Changed"  # type: ignore[misc]


def test_fieldspec_default_suggestion_is_empty() -> None:
    spec = FieldSpec("Value", FieldSeverity.REQUIRED)
    assert spec.suggestion == ""


def test_fieldspec_with_suggestion() -> None:
    spec = FieldSpec("Tolerance", FieldSeverity.BEST_PRACTICE, "e.g. 1%, 5%")
    assert spec.suggestion == "e.g. 1%, 5%"


# ---------------------------------------------------------------------------
# Universal required fields
# ---------------------------------------------------------------------------


def test_universal_required_contains_value() -> None:
    names = [s.name for s in UNIVERSAL_REQUIRED_FIELDS]
    assert "Value" in names


def test_universal_required_contains_footprint() -> None:
    names = [s.name for s in UNIVERSAL_REQUIRED_FIELDS]
    assert "Footprint" in names


def test_universal_required_all_have_required_severity() -> None:
    for spec in UNIVERSAL_REQUIRED_FIELDS:
        assert (
            spec.severity == FieldSeverity.REQUIRED
        ), f"{spec.name} should be REQUIRED"


# ---------------------------------------------------------------------------
# get_required_fields()
# ---------------------------------------------------------------------------


def test_get_required_fields_returns_copy() -> None:
    r1 = get_required_fields()
    r2 = get_required_fields()
    assert r1 is not r2


def test_get_required_fields_contains_value_and_footprint() -> None:
    names = [s.name for s in get_required_fields()]
    assert "Value" in names
    assert "Footprint" in names


# ---------------------------------------------------------------------------
# get_field_specs() — structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "category",
    [
        ComponentType.RESISTOR,
        ComponentType.CAPACITOR,
        ComponentType.INDUCTOR,
        ComponentType.LED,
        ComponentType.INTEGRATED_CIRCUIT,
        ComponentType.CONNECTOR,
        ComponentType.TRANSISTOR,
        ComponentType.OSCILLATOR,
        ComponentType.FUSE,
        None,
        "",
        "UNKNOWN_CATEGORY",
    ],
)
def test_get_field_specs_always_includes_required_fields(category: str) -> None:
    specs = get_field_specs(category)
    names = [s.name for s in specs]
    assert "Value" in names, f"Value missing for category={category!r}"
    assert "Footprint" in names, f"Footprint missing for category={category!r}"


@pytest.mark.parametrize(
    "category",
    [
        ComponentType.RESISTOR,
        ComponentType.CAPACITOR,
        ComponentType.INTEGRATED_CIRCUIT,
        None,
    ],
)
def test_get_field_specs_always_includes_universal_best_practice(category: str) -> None:
    specs = get_field_specs(category)
    names = [s.name for s in specs]
    assert "Manufacturer" in names, f"Manufacturer missing for category={category!r}"
    assert "MFGPN" in names, f"MFGPN missing for category={category!r}"


def test_get_field_specs_required_before_best_practice() -> None:
    """Required fields should come before best-practice fields in the list."""
    specs = get_field_specs(ComponentType.RESISTOR)
    required_indices = [
        i for i, s in enumerate(specs) if s.severity == FieldSeverity.REQUIRED
    ]
    best_practice_indices = [
        i for i, s in enumerate(specs) if s.severity == FieldSeverity.BEST_PRACTICE
    ]
    assert required_indices, "No REQUIRED specs found"
    assert best_practice_indices, "No BEST_PRACTICE specs found"
    assert max(required_indices) < min(
        best_practice_indices
    ), "All REQUIRED specs should appear before any BEST_PRACTICE spec"


# ---------------------------------------------------------------------------
# get_field_specs() — category-specific best-practice fields
# ---------------------------------------------------------------------------


def test_resistor_has_tolerance_best_practice() -> None:
    specs = get_field_specs(ComponentType.RESISTOR)
    bp_names = {s.name for s in specs if s.severity == FieldSeverity.BEST_PRACTICE}
    assert "Tolerance" in bp_names


def test_resistor_has_power_best_practice() -> None:
    specs = get_field_specs(ComponentType.RESISTOR)
    bp_names = {s.name for s in specs if s.severity == FieldSeverity.BEST_PRACTICE}
    assert "Power" in bp_names


def test_capacitor_has_voltage_best_practice() -> None:
    specs = get_field_specs(ComponentType.CAPACITOR)
    bp_names = {s.name for s in specs if s.severity == FieldSeverity.BEST_PRACTICE}
    assert "Voltage" in bp_names


def test_capacitor_has_tolerance_best_practice() -> None:
    specs = get_field_specs(ComponentType.CAPACITOR)
    bp_names = {s.name for s in specs if s.severity == FieldSeverity.BEST_PRACTICE}
    assert "Tolerance" in bp_names


def test_inductor_has_current_best_practice() -> None:
    specs = get_field_specs(ComponentType.INDUCTOR)
    bp_names = {s.name for s in specs if s.severity == FieldSeverity.BEST_PRACTICE}
    assert "Current" in bp_names


def test_led_has_wavelength_best_practice() -> None:
    specs = get_field_specs(ComponentType.LED)
    bp_names = {s.name for s in specs if s.severity == FieldSeverity.BEST_PRACTICE}
    assert "Wavelength" in bp_names


def test_connector_has_pitch_best_practice() -> None:
    specs = get_field_specs(ComponentType.CONNECTOR)
    bp_names = {s.name for s in specs if s.severity == FieldSeverity.BEST_PRACTICE}
    assert "Pitch" in bp_names


def test_oscillator_has_frequency_best_practice() -> None:
    specs = get_field_specs(ComponentType.OSCILLATOR)
    bp_names = {s.name for s in specs if s.severity == FieldSeverity.BEST_PRACTICE}
    assert "Frequency" in bp_names


def test_fuse_has_current_best_practice() -> None:
    specs = get_field_specs(ComponentType.FUSE)
    bp_names = {s.name for s in specs if s.severity == FieldSeverity.BEST_PRACTICE}
    assert "Current" in bp_names


def test_unknown_category_returns_only_universal_fields() -> None:
    specs = get_field_specs("COMPLETELY_UNKNOWN")
    # Should have universal required + universal best-practice only
    names = {s.name for s in specs}
    assert names == {"Value", "Footprint", "Manufacturer", "MFGPN"}


# ---------------------------------------------------------------------------
# get_best_practice_fields()
# ---------------------------------------------------------------------------


def test_get_best_practice_fields_returns_only_best_practice_severity() -> None:
    for category in [ComponentType.RESISTOR, ComponentType.CAPACITOR, None]:
        specs = get_best_practice_fields(category)
        for spec in specs:
            assert (
                spec.severity == FieldSeverity.BEST_PRACTICE
            ), f"Expected BEST_PRACTICE, got {spec.severity} for {spec.name}"


def test_get_best_practice_fields_excludes_required_fields() -> None:
    specs = get_best_practice_fields(ComponentType.RESISTOR)
    names = {s.name for s in specs}
    assert "Value" not in names
    assert "Footprint" not in names


# ---------------------------------------------------------------------------
# Suggestions are populated for best-practice fields
# ---------------------------------------------------------------------------


def test_resistor_tolerance_has_non_empty_suggestion() -> None:
    specs = get_field_specs(ComponentType.RESISTOR)
    tol = next((s for s in specs if s.name == "Tolerance"), None)
    assert tol is not None
    assert tol.suggestion.strip() != ""


def test_capacitor_voltage_has_non_empty_suggestion() -> None:
    specs = get_field_specs(ComponentType.CAPACITOR)
    v = next((s for s in specs if s.name == "Voltage"), None)
    assert v is not None
    assert v.suggestion.strip() != ""


# ---------------------------------------------------------------------------
# CATEGORY_BEST_PRACTICE dict completeness
# ---------------------------------------------------------------------------


def test_category_best_practice_covers_major_categories() -> None:
    """All commonly-used categories should be in the mapping (even if empty list)."""
    expected = {
        ComponentType.RESISTOR,
        ComponentType.CAPACITOR,
        ComponentType.INDUCTOR,
        ComponentType.DIODE,
        ComponentType.LED,
        ComponentType.INTEGRATED_CIRCUIT,
        ComponentType.TRANSISTOR,
        ComponentType.CONNECTOR,
        ComponentType.REGULATOR,
        ComponentType.OSCILLATOR,
        ComponentType.FUSE,
        ComponentType.SWITCH,
        ComponentType.RELAY,
        ComponentType.ANALOG,
    }
    missing = expected - set(CATEGORY_BEST_PRACTICE.keys())
    assert not missing, f"Missing categories in CATEGORY_BEST_PRACTICE: {missing}"
