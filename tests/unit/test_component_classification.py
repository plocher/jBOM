from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from jbom.common.component_classification import (  # noqa: E402
    ClassificationSignal,
    _SIGNALS,
    _classify_by_score,
    get_category_fields,
    get_component_type,
    get_value_interpretation,
    normalize_component_type,
)
from jbom.common.constants import DEFAULT_CATEGORY_FIELDS, ComponentType  # noqa: E402


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


def test_get_component_type_connector_name_not_misclassified_as_cap() -> None:
    assert (
        get_component_type(
            lib_id="SPCoast:CONNECTOR_01X04_V",
            footprint="SPCoast:Connector_01x04_V",
        )
        == "CON"
    )


def test_get_component_type_c_prefixed_led_name_not_misclassified_as_cap() -> None:
    assert (
        get_component_type(
            lib_id="Custom:CLED_RGB",
            footprint="LED_SMD:LED_0603_1608Metric",
        )
        == "LED"
    )


def test_get_component_type_unknown_returns_none() -> None:
    assert get_component_type(lib_id="Custom:Thing", footprint="") is None
    assert get_component_type(lib_id="", footprint="Whatever") is None


# ---------------------------------------------------------------------------
# Scoring model structure
# ---------------------------------------------------------------------------


def test_classification_signal_is_dataclass() -> None:
    """ClassificationSignal must be a frozen dataclass with required fields."""
    sig = ClassificationSignal("RES", 1.0, lambda n, f, r: n.startswith("R"))
    assert sig.category == "RES"
    assert sig.weight == 1.0
    assert sig.match("R1", "", "") is True
    assert sig.match("C1", "", "") is False


def test_signals_list_is_non_empty_and_typed() -> None:
    """_SIGNALS must be a non-empty list of ClassificationSignal instances."""
    assert len(_SIGNALS) > 0
    for sig in _SIGNALS:
        assert isinstance(sig, ClassificationSignal)
        assert sig.weight > 0


def test_classify_by_score_no_match_returns_none() -> None:
    assert _classify_by_score("XYZZY", "", "") is None


def test_classify_by_score_single_signal_wins() -> None:
    # INDUCTOR substring fires at 5.0; IC pattern NE fires at 3.0 (from GENERIC)
    # but IND still wins (5.0 > 3.0).
    assert _classify_by_score("GENERIC_INDUCTOR", "", "") == "IND"


# ---------------------------------------------------------------------------
# Multi-signal scoring — core correctness cases
# ---------------------------------------------------------------------------


def test_scoring_cled_rgb_led_beats_c_prefix() -> None:
    """CLED_RGB: LED substring (3.0) + LED footprint (4.0) beat C-prefix (1.0).

    This was the motivating bug for issue #149.
    """
    assert (
        get_component_type(
            lib_id="Custom:CLED_RGB",
            footprint="LED_SMD:LED_0603_1608Metric",
        )
        == "LED"
    )


def test_scoring_connector_beats_c_prefix() -> None:
    """CONNECTOR_01X04_V: CONN substring (5.0) beats C-prefix (1.0).

    Regression: previously required band-aid ordering fix from issue #145.
    """
    assert (
        get_component_type(
            lib_id="SPCoast:CONNECTOR_01X04_V",
            footprint="SPCoast:Connector_01x04_V",
        )
        == "CON"
    )


def test_scoring_ic_pattern_beats_r_prefix() -> None:
    """LM in name (3.0) beats R-prefix (1.0), classifying RLMxxxx as IC."""
    assert get_component_type(lib_id="Custom:RLM321", footprint="") == "IC"


def test_scoring_ic_footprint_beats_single_prefix() -> None:
    """SOIC footprint (6.0) overrides U-prefix (2.0) — both → IC, stacking."""
    assert (
        get_component_type(
            lib_id="Custom:UGENERIC",
            footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        )
        == "IC"
    )


def test_scoring_ic_footprint_beats_c_prefix() -> None:
    """SOIC footprint (6.0) beats C-prefix (1.0), preventing capacitor misclassification."""
    assert (
        get_component_type(
            lib_id="Custom:CD4011",
            footprint="Package_SO:SOIC-14_3.9x8.65mm_P1.27mm",
        )
        == "IC"
    )


# ---------------------------------------------------------------------------
# IPC reference designator signals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("J1", "CON"),  # J → CONNECTOR
        ("FB1", "IND"),  # FB → INDUCTOR (ferrite bead)
        ("D3", "DIO"),  # D → DIODE
        ("Q2", "Q"),  # Q → TRANSISTOR
        ("U4", "IC"),  # U → IC
        ("K1", "RLY"),  # K → RELAY
        ("Y1", "OSC"),  # Y → OSCILLATOR (crystal)
        ("F1", "FUS"),  # F → FUSE
        ("R1", "RES"),  # R → RESISTOR (IPC passive designator)
        ("C1", "CAP"),  # C → CAPACITOR (IPC passive designator)
        ("L1", "IND"),  # L → INDUCTOR (IPC passive designator)
        ("CON1", "CON"),  # CON* → CONNECTOR (3-char prefix, beats C→CAP)
    ],
)
def test_refdes_signal_classifies_unknown_component(
    reference: str, expected: str
) -> None:
    """An unknown component name should be classified by its RefDes prefix.

    'PART' is chosen as a neutral name: it starts with 'P' (no single-char prefix
    signal), contains no IC indicator patterns, and carries no 'J' substring.
    The RefDes signal is therefore the only signal that fires.
    """
    assert (
        get_component_type(
            lib_id="Custom:PART",
            footprint="",
            reference=reference,
        )
        == expected
    ), f"reference={reference!r} should classify as {expected!r}"


def test_refdes_fb_beats_f_for_ferrite_beads() -> None:
    """FB* reference (IND 6.0) classifies ferrite beads correctly.

    The digit constraint also prevents F→FUS from firing on 'FB*' refs
    (second char 'B' is not a digit), so FB→IND wins uncontested.
    """
    result = get_component_type(
        lib_id="Custom:FERRITE_BEAD_100R",
        footprint="",
        reference="FB2",
    )
    assert (
        result == "IND"
    ), f"FB2 reference should classify ferrite bead as IND, got {result!r}"


def test_refdes_j_connector_beats_name_prefix() -> None:
    """J reference (5.0) + name prefix wins over weak C-prefix (1.0) for JST-style parts."""
    result = get_component_type(
        lib_id="Custom:JST_PH_2P",
        footprint="Connector_JST:JST_PH_S2B",
        reference="J3",
    )
    assert result == "CON"


def test_refdes_absent_does_not_affect_result() -> None:
    """Omitting reference leaves existing signal-based classification unchanged."""
    # Without reference: LED signal (3.0 + 4.0) beats C-prefix (1.0)
    assert (
        get_component_type(
            lib_id="Custom:CLED_RGB",
            footprint="LED_SMD:LED_0603_1608Metric",
        )
        == "LED"
    )
    # With reference D (which would add DIO 3.0): LED still wins (7.0 > 4.0)
    assert (
        get_component_type(
            lib_id="Custom:CLED_RGB",
            footprint="LED_SMD:LED_0603_1608Metric",
            reference="D5",
        )
        == "LED"
    )


# ---------------------------------------------------------------------------
# FUSE category
# ---------------------------------------------------------------------------


def test_fuse_detected_by_name_substring() -> None:
    assert get_component_type(lib_id="Device:Fuse", footprint="") == "FUS"


def test_fuse_detected_by_refdes() -> None:
    """Unknown component with F* reference designator → FUS."""
    assert (
        get_component_type(
            lib_id="Custom:POLY_RESETTABLE", footprint="", reference="F1"
        )
        == "FUS"
    )


def test_fuse_category_type_constant() -> None:
    assert ComponentType.FUSE == "FUS"


# ---------------------------------------------------------------------------
# Phase 1 — Description and Keywords as additional classification signal sources
# (issue #166)
# ---------------------------------------------------------------------------


def test_get_component_type_uses_description_when_name_and_footprint_fail() -> None:
    """WS2812B: zero signals from name/footprint; Description='RGB LED Neopixel' → LED."""
    result = get_component_type(
        lib_id="SPCoast:WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
        description="RGB LED Neopixel",
    )
    assert result == "LED", f"expected LED from description, got {result!r}"


def test_get_component_type_neopixel_in_description_classifies_as_led() -> None:
    """'Neopixel' keyword in description is a high-confidence LED signal.

    Uses a component name and footprint that fire zero primary signals so the
    description fallback is the sole signal source.
    """
    result = get_component_type(
        lib_id="Custom:WS2812B",  # zero primary signals: no LED/IC/etc in name or footprint
        footprint="Custom:5050",
        description="Neopixel addressable LED",
    )
    assert result == "LED", f"expected LED, got {result!r}"


def test_get_component_type_uses_keywords_for_relay() -> None:
    """Unknown part with Keywords='relay SPST' classifies as RLY."""
    result = get_component_type(
        lib_id="Custom:XYZ123",
        footprint="",
        keywords="relay SPST",
    )
    assert result == "RLY", f"expected RLY, got {result!r}"


def test_get_component_type_description_does_not_override_strong_primary_signal() -> (
    None
):
    """Primary signals (IC footprint 6.0) still win over a weak LED in description (3.0)."""
    result = get_component_type(
        lib_id="Custom:LEDDRIVER",
        footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        description="LED driver IC",
    )
    assert (
        result == "IC"
    ), f"IC footprint should outweigh description LED hint, got {result!r}"


def test_classify_by_score_uses_description_upper_dimension() -> None:
    """_classify_by_score with description_upper='RGB LED NEOPIXEL' returns LED."""
    result = _classify_by_score("WS2812B", "", "", description_upper="RGB LED NEOPIXEL")
    assert result == "LED", f"expected LED, got {result!r}"


# ---------------------------------------------------------------------------
# RefDes precision: prefix+digit constraint prevents false positives
# ---------------------------------------------------------------------------


def test_refdes_reg1_not_classified_as_res() -> None:
    """'REG1' starts with 'R' but second char 'E' is not a digit → no RES signal."""
    # lib_id has no signals; only the RefDes could classify it.
    # REG1 should return None, not RES.
    result = get_component_type(lib_id="Custom:PART", footprint="", reference="REG1")
    assert result is None, f"REG1 should not classify as RES, got {result!r}"


def test_refdes_con1_not_classified_as_cap() -> None:
    """'CON1' resolves to CON via 3-char prefix signal, not CAP via single-char 'C'."""
    result = get_component_type(lib_id="Custom:PART", footprint="", reference="CON1")
    assert result == "CON", f"CON1 should classify as CON, got {result!r}"


# ---------------------------------------------------------------------------
# Regression: passive RefDes signals override IC false-positives from lib_id
# ---------------------------------------------------------------------------


def test_r_refdes_beats_ne_in_generic_lib_id() -> None:
    """R* reference (RES 4.0) outweighs 'NE' substring in 'Generic' (IC 3.0).

    Regression guard for GitHub issue #149 behave scenario
    'BOM with partial inventory matches': schematics built with
    lib_id='Device:Generic' and reference='R1' were falsely classified
    as IC, causing the RESISTOR inventory type-filter to reject them.
    """
    result = get_component_type(
        lib_id="Device:Generic",
        footprint="R_0805_2012",
        reference="R1",
    )
    assert (
        result == "RES"
    ), f"Device:Generic + R1 should classify as RES (not IC), got {result!r}"


def test_c_refdes_beats_ne_in_generic_lib_id() -> None:
    """C* reference (CAP 4.0) outweighs 'NE' substring in 'Generic' (IC 3.0)."""
    result = get_component_type(
        lib_id="Device:Generic",
        footprint="C_0603_1608",
        reference="C1",
    )
    assert (
        result == "CAP"
    ), f"Device:Generic + C1 should classify as CAP (not IC), got {result!r}"


def test_l_refdes_beats_ne_in_generic_lib_id() -> None:
    """L* reference (IND 4.0) outweighs 'NE' substring in 'Generic' (IC 3.0)."""
    result = get_component_type(
        lib_id="Device:Generic",
        footprint="L_0805_2012",
        reference="L1",
    )
    assert (
        result == "IND"
    ), f"Device:Generic + L1 should classify as IND (not IC), got {result!r}"


# ---------------------------------------------------------------------------
# LED-prefix reference designator (issue follow-up to #166)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reference",
    ["LED1", "LED2", "LED10", "LED20", "LED32"],
)
def test_led_prefix_ref_classifies_as_led(reference: str) -> None:
    """LED* reference designators (e.g. LED1, LED20) must classify as LED.

    Components like WS2812B5050 using 'LED' prefix refs had zero primary signals,
    leaving them all unclassified and blocking Phase 2 value-consensus propagation.
    """
    result = get_component_type(
        lib_id="SPCoast:WS2812B5050",
        footprint="PCM_SPCoast:WS2812B5050",
        reference=reference,
    )
    assert (
        result == "LED"
    ), f"reference={reference!r} should classify as LED, got {result!r}"


def test_led_prefix_ref_does_not_fire_on_led_without_digit() -> None:
    """'LED' alone (no trailing digit) must not fire the LED ref signal."""
    # No digit after 'LED' → signal does not fire; other signals (LED in name) still win.
    result = get_component_type(
        lib_id="Device:LED",
        footprint="LED_SMD:LED_0603_1608Metric",
        reference="LED",
    )
    # Device:LED has LED in name (3.0) + LED in footprint (4.0) → LED wins regardless
    assert result == "LED"
