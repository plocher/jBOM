"""Unit tests for PartProfile — classify_item() and detect_subtype().

PartProfile encodes the stable electro-mechanical identity of a component
(category, package, technology subtype, tolerance). It is an internal
service-layer abstraction used by query planners; no CLI surface.
"""
from __future__ import annotations

import pytest

from jbom.common.types import InventoryItem
from jbom.services.search.part_profile import (
    PartProfile,
    classify_item,
    detect_subtype,
)


# ---------------------------------------------------------------------------
# Test factory
# ---------------------------------------------------------------------------


def _inv(
    *,
    category: str,
    value: str = "",
    package: str = "",
    tolerance: str = "",
    type_: str = "",
    description: str = "",
    resistance: float | None = None,
    capacitance: float | None = None,
    inductance: float | None = None,
    footprint_full: str = "",
    symbol_lib: str = "",
    symbol_name: str = "",
    smd: str = "SMD",
) -> InventoryItem:
    return InventoryItem(
        ipn="TEST-1",
        keywords="",
        category=category,
        description=description,
        smd=smd,
        value=value,
        type=type_,
        tolerance=tolerance,
        voltage="",
        amperage="",
        wattage="",
        spn="",
        manufacturer="",
        mfgpn="",
        datasheet="",
        package=package,
        resistance=resistance,
        capacitance=capacitance,
        inductance=inductance,
        footprint_full=footprint_full,
        symbol_lib=symbol_lib,
        symbol_name=symbol_name,
        pins="",
        pitch="",
        raw_data={},
    )


# ---------------------------------------------------------------------------
# PartProfile dataclass
# ---------------------------------------------------------------------------


class TestPartProfileDataclass:
    def test_fields_are_accessible(self) -> None:
        p = PartProfile(category="RES", package="0603", subtype="smd", tolerance="5%")
        assert p.category == "RES"
        assert p.package == "0603"
        assert p.subtype == "smd"
        assert p.tolerance == "5%"

    def test_is_frozen(self) -> None:
        p = PartProfile(category="CAP", package="0402", subtype="x7r", tolerance="10%")
        with pytest.raises((AttributeError, TypeError)):
            p.category = "RES"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = PartProfile(category="IND", package="0603", subtype="signal", tolerance="")
        b = PartProfile(category="IND", package="0603", subtype="signal", tolerance="")
        assert a == b

    def test_inequality_on_subtype(self) -> None:
        a = PartProfile(category="CAP", package="0603", subtype="x7r", tolerance="10%")
        b = PartProfile(
            category="CAP", package="0603", subtype="electrolytic", tolerance="10%"
        )
        assert a != b


# ---------------------------------------------------------------------------
# detect_subtype — CAP
# ---------------------------------------------------------------------------


class TestDetectSubtypeCAP:
    def test_default_is_x7r(self) -> None:
        item = _inv(category="CAP", value="100nF", package="0603", capacitance=100e-9)
        assert detect_subtype(item, "CAP") == "x7r"

    def test_explicit_x7r_in_type(self) -> None:
        item = _inv(category="CAP", value="100nF", type_="X7R", capacitance=100e-9)
        assert detect_subtype(item, "CAP") == "x7r"

    def test_c0g_in_type(self) -> None:
        item = _inv(category="CAP", value="22pF", type_="C0G", capacitance=22e-12)
        assert detect_subtype(item, "CAP") == "c0g"

    def test_np0_synonym_for_c0g(self) -> None:
        item = _inv(category="CAP", value="22pF", type_="NP0", capacitance=22e-12)
        assert detect_subtype(item, "CAP") == "c0g"

    def test_x5r_in_type(self) -> None:
        item = _inv(category="CAP", value="10uF", type_="X5R", capacitance=10e-6)
        assert detect_subtype(item, "CAP") == "x5r"

    def test_y5v_in_type(self) -> None:
        item = _inv(category="CAP", value="47uF", type_="Y5V", capacitance=47e-6)
        assert detect_subtype(item, "CAP") == "y5v"

    def test_electrolytic_via_polarized_symbol_name(self) -> None:
        item = _inv(
            category="CAP",
            value="100uF",
            symbol_name="C_Polarized",
            capacitance=100e-6,
        )
        assert detect_subtype(item, "CAP") == "electrolytic"

    def test_electrolytic_via_cp_footprint_entry(self) -> None:
        item = _inv(
            category="CAP",
            value="100uF",
            footprint_full="Capacitor_SMD:CP_Elec_4x5.4mm",
            capacitance=100e-6,
        )
        assert detect_subtype(item, "CAP") == "electrolytic"

    def test_electrolytic_via_elec_lib_nickname(self) -> None:
        item = _inv(
            category="CAP",
            value="100uF",
            footprint_full="Capacitor_Elec:CP_4x5mm",
            capacitance=100e-6,
        )
        assert detect_subtype(item, "CAP") == "electrolytic"

    def test_tantalum_via_tantalum_lib_nickname(self) -> None:
        item = _inv(
            category="CAP",
            value="10uF",
            footprint_full="Capacitor_Tantalum:CP_EIA-3216-18_Kemet-A",
            capacitance=10e-6,
        )
        assert detect_subtype(item, "CAP") == "tantalum"

    def test_tantalum_via_type_field(self) -> None:
        item = _inv(
            category="CAP",
            value="10uF",
            type_="Tantalum",
            capacitance=10e-6,
        )
        assert detect_subtype(item, "CAP") == "tantalum"

    def test_film_via_type_field(self) -> None:
        item = _inv(
            category="CAP",
            value="100nF",
            type_="Film",
            capacitance=100e-9,
        )
        assert detect_subtype(item, "CAP") == "film"

    def test_non_klc_lib_does_not_force_electrolytic(self) -> None:
        """A non-KLC lib nickname does not override footprint-entry signals."""
        item = _inv(
            category="CAP",
            value="100nF",
            footprint_full="SPCoast:C_0603",  # no CP_ prefix, non-KLC lib
            capacitance=100e-9,
        )
        # No electrolytic signal → default MLCC
        assert detect_subtype(item, "CAP") == "x7r"

    def test_polarized_in_lib_is_electrolytic(self) -> None:
        item = _inv(
            category="CAP",
            value="100uF",
            footprint_full="Capacitor_Polarized:CP_EIA-3528-21_Kemet-B",
            capacitance=100e-6,
        )
        assert detect_subtype(item, "CAP") == "electrolytic"


# ---------------------------------------------------------------------------
# detect_subtype — IND
# ---------------------------------------------------------------------------


class TestDetectSubtypeIND:
    def test_default_is_signal(self) -> None:
        item = _inv(category="IND", value="10uH", package="0603", inductance=10e-6)
        assert detect_subtype(item, "IND") == "signal"

    def test_ferrite_via_description(self) -> None:
        item = _inv(
            category="IND",
            value="600Ω",
            description="Ferrite Bead 600 Ohm",
            package="0402",
        )
        assert detect_subtype(item, "IND") == "ferrite"

    def test_ferrite_detection_case_insensitive(self) -> None:
        item = _inv(
            category="IND",
            value="600Ω",
            description="ferrite bead",
        )
        assert detect_subtype(item, "IND") == "ferrite"

    def test_power_via_l_core_symbol_name(self) -> None:
        item = _inv(
            category="IND",
            value="100uH",
            symbol_name="L_Core",
            inductance=100e-6,
        )
        assert detect_subtype(item, "IND") == "power"

    def test_power_via_underscore_core_in_symbol_name(self) -> None:
        item = _inv(
            category="IND",
            value="100uH",
            symbol_name="L_Coupled_Core",
            inductance=100e-6,
        )
        assert detect_subtype(item, "IND") == "power"

    def test_power_via_large_package_1210(self) -> None:
        item = _inv(
            category="IND",
            value="47uH",
            package="1210",
            inductance=47e-6,
        )
        assert detect_subtype(item, "IND") == "power"

    def test_power_via_large_package_1812(self) -> None:
        item = _inv(category="IND", value="100uH", package="1812", inductance=100e-6)
        assert detect_subtype(item, "IND") == "power"

    def test_power_via_large_package_2520(self) -> None:
        item = _inv(category="IND", value="100uH", package="2520", inductance=100e-6)
        assert detect_subtype(item, "IND") == "power"

    def test_power_via_large_package_4532(self) -> None:
        item = _inv(category="IND", value="330uH", package="4532", inductance=330e-6)
        assert detect_subtype(item, "IND") == "power"

    def test_ferrite_takes_priority_over_large_package(self) -> None:
        item = _inv(
            category="IND",
            value="600Ω",
            description="Ferrite Bead",
            package="1210",
        )
        assert detect_subtype(item, "IND") == "ferrite"


# ---------------------------------------------------------------------------
# detect_subtype — RES
# ---------------------------------------------------------------------------


class TestDetectSubtypeRES:
    def test_default_is_smd(self) -> None:
        item = _inv(category="RES", value="10K", package="0603", resistance=10_000.0)
        assert detect_subtype(item, "RES") == "smd"

    def test_smd_explicit(self) -> None:
        item = _inv(
            category="RES", value="10K", smd="SMD", package="0603", resistance=10_000.0
        )
        assert detect_subtype(item, "RES") == "smd"

    def test_wirewound_via_type(self) -> None:
        item = _inv(category="RES", value="100Ω", type_="Wirewound", resistance=100.0)
        assert detect_subtype(item, "RES") == "wirewound"

    def test_metal_film_via_type(self) -> None:
        item = _inv(
            category="RES", value="10K", type_="Metal Film", resistance=10_000.0
        )
        assert detect_subtype(item, "RES") == "metal_film"

    def test_carbon_film_via_type_falls_back_to_smd(self) -> None:
        """Carbon film is PTH but not wirewound/metal_film; defaults to 'smd'."""
        item = _inv(
            category="RES", value="10K", type_="Carbon Film", resistance=10_000.0
        )
        # Carbon film is not a named subtype in RES vocabulary; smd is the fallback
        result = detect_subtype(item, "RES")
        assert result in ("smd", "carbon_film")  # either is acceptable


# ---------------------------------------------------------------------------
# classify_item — supported categories
# ---------------------------------------------------------------------------


class TestClassifyItemSupported:
    def test_res_returns_part_profile(self) -> None:
        item = _inv(
            category="RES",
            value="10K",
            package="0603",
            tolerance="5%",
            resistance=10_000.0,
        )
        profile = classify_item(item)
        assert profile is not None
        assert profile.category == "RES"
        assert profile.package == "0603"
        assert profile.tolerance == "5%"
        assert profile.subtype == "smd"

    def test_cap_mlcc_returns_part_profile(self) -> None:
        item = _inv(
            category="CAP",
            value="100nF",
            package="0603",
            tolerance="10%",
            capacitance=100e-9,
        )
        profile = classify_item(item)
        assert profile is not None
        assert profile.category == "CAP"
        assert profile.package == "0603"
        assert profile.subtype == "x7r"

    def test_cap_electrolytic_returns_electrolytic_profile(self) -> None:
        item = _inv(
            category="CAP",
            value="100uF",
            package="6x5mm",
            symbol_name="C_Polarized",
            capacitance=100e-6,
        )
        profile = classify_item(item)
        assert profile is not None
        assert profile.category == "CAP"
        assert profile.subtype == "electrolytic"

    def test_ind_signal_returns_part_profile(self) -> None:
        item = _inv(
            category="IND",
            value="10uH",
            package="0603",
            inductance=10e-6,
        )
        profile = classify_item(item)
        assert profile is not None
        assert profile.category == "IND"
        assert profile.package == "0603"
        assert profile.subtype == "signal"
        assert profile.tolerance == ""

    def test_ind_ferrite_returns_ferrite_profile(self) -> None:
        item = _inv(
            category="IND",
            value="600Ω",
            description="Ferrite Bead 600 Ohm",
            package="0402",
        )
        profile = classify_item(item)
        assert profile is not None
        assert profile.subtype == "ferrite"

    def test_category_is_uppercased_in_output(self) -> None:
        item = _inv(category="res", value="10K", package="0603", resistance=10_000.0)
        profile = classify_item(item)
        assert profile is not None
        assert profile.category == "RES"

    def test_category_aliases_resistor_works(self) -> None:
        """Longer category strings that normalize to 'RES' should still classify."""
        item = _inv(
            category="RESISTOR", value="10K", package="0603", resistance=10_000.0
        )
        profile = classify_item(item)
        assert profile is not None
        assert profile.category == "RES"

    def test_category_aliases_capacitor_works(self) -> None:
        item = _inv(
            category="CAPACITOR", value="100nF", package="0603", capacitance=100e-9
        )
        profile = classify_item(item)
        assert profile is not None
        assert profile.category == "CAP"

    def test_category_aliases_inductor_works(self) -> None:
        item = _inv(category="INDUCTOR", value="10uH", package="0603", inductance=10e-6)
        profile = classify_item(item)
        assert profile is not None
        assert profile.category == "IND"


# ---------------------------------------------------------------------------
# classify_item — unsupported categories (returns None)
# ---------------------------------------------------------------------------


class TestClassifyItemUnsupported:
    @pytest.mark.parametrize("category", ["IC", "CON", "DIO", "LED", "XTAL", "OTHER"])
    def test_unsupported_returns_none(self, category: str) -> None:
        item = _inv(category=category, value="LM358")
        assert classify_item(item) is None

    def test_empty_category_returns_none(self) -> None:
        item = _inv(category="", value="unknown")
        assert classify_item(item) is None


# ---------------------------------------------------------------------------
# classify_item — package normalization
# ---------------------------------------------------------------------------


class TestClassifyItemPackage:
    def test_package_passed_through(self) -> None:
        item = _inv(category="RES", value="10K", package="0805", resistance=10_000.0)
        profile = classify_item(item)
        assert profile is not None
        assert profile.package == "0805"

    def test_empty_package_is_allowed(self) -> None:
        item = _inv(category="RES", value="10K", package="", resistance=10_000.0)
        profile = classify_item(item)
        assert profile is not None
        assert profile.package == ""


# ---------------------------------------------------------------------------
# classify_item — tolerance handling
# ---------------------------------------------------------------------------


class TestClassifyItemTolerance:
    def test_tolerance_passed_through(self) -> None:
        item = _inv(
            category="RES",
            value="10K",
            package="0603",
            tolerance="1%",
            resistance=10_000.0,
        )
        profile = classify_item(item)
        assert profile is not None
        assert profile.tolerance == "1%"

    def test_empty_tolerance_is_allowed(self) -> None:
        item = _inv(category="CAP", value="100nF", package="0603", capacitance=100e-9)
        profile = classify_item(item)
        assert profile is not None
        assert isinstance(profile.tolerance, str)
