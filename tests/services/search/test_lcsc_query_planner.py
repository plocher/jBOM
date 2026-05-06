from __future__ import annotations

from jbom.common.types import InventoryItem
from jbom.config.defaults import get_defaults
from jbom.suppliers.lcsc.query_planner import (
    build_parametric_query_plan,
)


def _inv_item(
    *,
    category: str,
    value: str,
    package: str = "",
    tolerance: str = "",
    voltage: str = "",
    smd: str = "SMD",
    type_: str = "",
    description: str = "",
    resistance: float | None = None,
    capacitance: float | None = None,
    inductance: float | None = None,
    footprint_full: str = "",
    symbol_lib: str = "",
    symbol_name: str = "",
    pins: str = "",
    pitch: str = "",
) -> InventoryItem:
    return InventoryItem(
        ipn="I-1",
        keywords="",
        category=category,
        description=description,
        smd=smd,
        value=value,
        type=type_,
        tolerance=tolerance,
        voltage=voltage,
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
        pins=pins,
        pitch=pitch,
        raw_data={},
    )


def test_generic_defaults_profile_has_expected_parametric_fields() -> None:
    cfg = get_defaults("generic")
    assert cfg.get_parametric_query_fields("resistor") == [
        "resistance",
        "tolerance",
        "package",
        "power_rating",
        "technology",
    ]
    assert cfg.get_parametric_query_fields("capacitor") == [
        "capacitance",
        "tolerance",
        "package",
        "voltage_rating",
        "dielectric",
    ]


def test_resistor_plan_uses_static_default_tolerance_and_routing() -> None:
    item = _inv_item(
        category="RES",
        value="10K",
        package="0603",
        tolerance="",
        smd="SMD",
        resistance=10_000.0,
    )
    plan = build_parametric_query_plan(item, base_query="10K resistor 0603")

    assert plan.use_parametric is True
    assert plan.first_sort_name == "Resistors"
    assert plan.second_sort_name == "Chip Resistor - Surface Mount"
    assert plan.component_specification_list == ("0603",)
    assert ("Tolerance", ("5%",)) in plan.component_attribute_list


def test_capacitor_plan_uses_static_defaults_in_keyword_context() -> None:
    item = _inv_item(
        category="CAP",
        value="100nF",
        package="0603",
        tolerance="",
        voltage="",
        type_="",
        capacitance=100e-9,
    )
    plan = build_parametric_query_plan(item, base_query="100nF capacitor 0603")

    assert plan.use_parametric is True
    assert plan.first_sort_name == "Capacitors"
    assert "X7R" in plan.keyword_query
    assert "25V" in plan.keyword_query
    assert ("Tolerance", ("10%",)) in plan.component_attribute_list


def test_unknown_category_returns_keyword_fallback_plan() -> None:
    item = _inv_item(category="IC", value="LM358D")
    plan = build_parametric_query_plan(item, base_query="LM358D IC")

    assert plan.use_parametric is False
    assert plan.keyword_query == "LM358D IC"


# ---------------------------------------------------------------------------
# CAP — technology detection (electrolytic vs MLCC)
# ---------------------------------------------------------------------------


def test_cap_mlcc_default_gets_mlcc_second_sort() -> None:
    """CAP with no electrolytic signal routes to MLCC second sort."""
    item = _inv_item(
        category="CAP",
        value="100nF",
        package="0603",
        capacitance=100e-9,
    )
    plan = build_parametric_query_plan(item, base_query="100nF cap 0603")

    assert plan.use_parametric is True
    assert plan.first_sort_name == "Capacitors"
    assert plan.second_sort_name == "Multilayer Ceramic Capacitors (MLCC)"
    assert "X7R" in plan.keyword_query  # dielectric retained for MLCC


def test_cap_electrolytic_via_symbol_name() -> None:
    """C_Polarized in symbol_name routes to electrolytic second sort."""
    item = _inv_item(
        category="CAP",
        value="100uF",
        symbol_name="C_Polarized",
        capacitance=100e-6,
    )
    plan = build_parametric_query_plan(item, base_query="100uF cap")

    assert plan.use_parametric is True
    assert plan.second_sort_name == "Aluminum Electrolytic Capacitors"
    assert "X7R" not in plan.keyword_query  # no dielectric for electrolytics


def test_cap_electrolytic_via_footprint_entry_name() -> None:
    """CP_ prefix in footprint entry name routes to electrolytic."""
    item = _inv_item(
        category="CAP",
        value="100uF",
        footprint_full="Capacitor_SMD:CP_Elec_4x5.4mm",
        capacitance=100e-6,
    )
    plan = build_parametric_query_plan(item, base_query="100uF cap")

    assert plan.second_sort_name == "Aluminum Electrolytic Capacitors"


def test_cap_electrolytic_via_non_klc_lib_nickname() -> None:
    """Non-KLC library nickname doesn't block detection from entry name."""
    item = _inv_item(
        category="CAP",
        value="100uF",
        footprint_full="SPCoast:CP_Elec_4x5.4mm",  # user lib, non-KLC nickname
        capacitance=100e-6,
    )
    plan = build_parametric_query_plan(item, base_query="100uF cap")

    assert plan.second_sort_name == "Aluminum Electrolytic Capacitors"


# ---------------------------------------------------------------------------
# IND — inductor subtype routing
# ---------------------------------------------------------------------------


def test_ind_signal_inductor_default_route() -> None:
    """IND with no special signals routes to signal/RF second sort."""
    item = _inv_item(
        category="IND",
        value="10uH",
        package="0603",
        inductance=10e-6,
    )
    plan = build_parametric_query_plan(item, base_query="10uH inductor 0603")

    assert plan.use_parametric is True
    assert plan.first_sort_name == "Inductors"
    assert plan.second_sort_name == "Inductors (SMD)"
    assert ("Inductance", ("10uH",)) in plan.component_attribute_list


def test_ind_power_inductor_via_symbol_name() -> None:
    """L_Core in symbol_name routes to power inductors."""
    item = _inv_item(
        category="IND",
        value="4.7uH",
        package="1210",
        symbol_name="L_Core",
        inductance=4.7e-6,
    )
    plan = build_parametric_query_plan(item, base_query="4.7uH inductor 1210")

    assert plan.second_sort_name == "Power Inductors"


def test_ind_power_inductor_via_large_package() -> None:
    """Power-class package size routes to power inductors."""
    item = _inv_item(
        category="IND",
        value="10uH",
        package="1812",
        inductance=10e-6,
    )
    plan = build_parametric_query_plan(item, base_query="10uH inductor 1812")

    assert plan.second_sort_name == "Power Inductors"


def test_ind_ferrite_bead_via_description() -> None:
    """'Ferrite' in description routes to ferrite bead second sort."""
    item = _inv_item(
        category="IND",
        value="600R@100MHz",
        description="Ferrite Bead 600R@100MHz",
        package="0805",
    )
    plan = build_parametric_query_plan(item, base_query="600R ferrite 0805")

    assert plan.use_parametric is True
    assert plan.first_sort_name == "Inductors"
    assert plan.second_sort_name == "Ferrite Beads"
    assert plan.component_attribute_list == ()  # ferrite: no inductance attribute


def test_ind_missing_inductance_returns_keyword_fallback() -> None:
    """IND with no inductance value and not ferrite → keyword fallback."""
    item = _inv_item(category="IND", value="")
    plan = build_parametric_query_plan(item, base_query="inductor")

    assert plan.use_parametric is False


# ---------------------------------------------------------------------------
# CON — connector parametric planning
# ---------------------------------------------------------------------------


def test_con_with_item_pins_and_pitch() -> None:
    """Direct pins/pitch fields build an enriched keyword query."""
    item = _inv_item(
        category="CON",
        value="Conn_01x04",
        pins="4",
        pitch="2.54mm",
    )
    plan = build_parametric_query_plan(item, base_query="connector")

    assert plan.use_parametric is True
    assert plan.first_sort_name == "Connectors"
    assert "2.54mm" in plan.keyword_query
    assert "4" in plan.keyword_query


def test_con_footprint_parsed_for_pitch_and_pins() -> None:
    """Footprint entry name parsed for pitch and pin count."""
    item = _inv_item(
        category="CON",
        value="Conn_01x04",
        footprint_full="Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    )
    plan = build_parametric_query_plan(item, base_query="connector")

    assert plan.use_parametric is True
    assert plan.first_sort_name == "Connectors"
    assert "2.54mm" in plan.keyword_query
    assert "4" in plan.keyword_query
    assert "PinHeader" in plan.keyword_query


def test_con_jst_series_detected_from_footprint() -> None:
    """JST_PH series detected from footprint entry name."""
    item = _inv_item(
        category="CON",
        value="JST 4-pin",
        footprint_full="Connector_JST:JST_PH_S4B-PH-K_1x04-1MP_P2.00mm_Vertical",
    )
    plan = build_parametric_query_plan(item, base_query="JST connector")

    assert plan.use_parametric is True
    assert "JST_PH" in plan.keyword_query


def test_con_no_structured_data_returns_keyword_fallback() -> None:
    """No pins, pitch, or footprint → keyword fallback with explanation."""
    item = _inv_item(category="CON", value="Connector")
    plan = build_parametric_query_plan(item, base_query="connector")

    assert plan.use_parametric is False
    assert "manual search required" in plan.reason
