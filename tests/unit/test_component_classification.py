from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from jbom.common.component_classification import (  # noqa: E402
    get_category_fields,
    get_component_type,
    get_value_interpretation,
    normalize_component_type,
)
from jbom.common.constants import DEFAULT_CATEGORY_FIELDS  # noqa: E402


def test_normalize_component_type_direct_and_mapped() -> None:
    assert normalize_component_type("res") == "RES"
    assert normalize_component_type("r") == "RES"
    assert normalize_component_type("resistor") == "RES"

    assert normalize_component_type("cap") == "CAP"
    assert normalize_component_type("c") == "CAP"
    assert normalize_component_type("capacitor") == "CAP"


def test_get_category_fields_known_type_is_not_default() -> None:
    fields = get_category_fields("RES")
    # Resistors have category-specific fields like "Power".
    assert "Power" in fields


def test_get_category_fields_unknown_type_returns_default() -> None:
    assert get_category_fields("NOT_A_REAL_TYPE") == DEFAULT_CATEGORY_FIELDS


def test_get_value_interpretation() -> None:
    assert get_value_interpretation("RES") == "Resistance"
    assert get_value_interpretation("IC") is None


@pytest.mark.parametrize(
    ("lib_id", "footprint", "expected"),
    [
        ("Device:R", "Resistor_SMD:R_0603_1608Metric", "RES"),
        ("Device:C", "Capacitor_SMD:C_0603_1608Metric", "CAP"),
        ("Device:L", "Inductor_SMD:L_0603_1608Metric", "IND"),
        ("Device:D", "Diode_SMD:D_SOD-123", "DIO"),
        ("Device:LED", "LED_SMD:LED_0603_1608Metric", "LED"),
        ("Device:Q", "Package_TO_SOT_SMD:SOT-23", "Q"),
    ],
)
def test_get_component_type_basic(lib_id: str, footprint: str, expected: str) -> None:
    assert get_component_type(lib_id=lib_id, footprint=footprint) == expected


def test_get_component_type_uses_footprint_for_ic_detection() -> None:
    assert (
        get_component_type(
            lib_id="Custom:Thing",
            footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        )
        == "IC"
    )


def test_get_component_type_detects_lm_prefix_as_ic() -> None:
    assert (
        get_component_type(
            lib_id="Custom:LMV358",
            footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        )
        == "IC"
    )


def test_get_component_type_unknown_returns_none() -> None:
    assert get_component_type(lib_id="Custom:Thing", footprint="") is None
    assert get_component_type(lib_id="", footprint="Whatever") is None
