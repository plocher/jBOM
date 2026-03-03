from __future__ import annotations

from jbom.common.types import InventoryItem
from jbom.services.search.jlcpcb_phase4_heuristics import (
    PARAMETRIC_QUERY_FIELDS,
    build_phase4_parametric_query_plan,
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
    resistance: float | None = None,
    capacitance: float | None = None,
) -> InventoryItem:
    return InventoryItem(
        ipn="I-1",
        keywords="",
        category=category,
        description="",
        smd=smd,
        value=value,
        type=type_,
        tolerance=tolerance,
        voltage=voltage,
        amperage="",
        wattage="",
        lcsc="",
        manufacturer="",
        mfgpn="",
        datasheet="",
        package=package,
        resistance=resistance,
        capacitance=capacitance,
        raw_data={},
    )


def test_phase4_constants_are_yaml_shaped_for_resistor_and_capacitor() -> None:
    assert PARAMETRIC_QUERY_FIELDS["resistor"] == [
        "resistance",
        "tolerance",
        "package",
        "power_rating",
        "technology",
    ]
    assert PARAMETRIC_QUERY_FIELDS["capacitor"] == [
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
    plan = build_phase4_parametric_query_plan(item, base_query="10K resistor 0603")

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
    plan = build_phase4_parametric_query_plan(item, base_query="100nF capacitor 0603")

    assert plan.use_parametric is True
    assert plan.first_sort_name == "Capacitors"
    assert "X7R" in plan.keyword_query
    assert "25V" in plan.keyword_query
    assert ("Tolerance", ("10%",)) in plan.component_attribute_list


def test_unknown_category_returns_keyword_fallback_plan() -> None:
    item = _inv_item(category="IC", value="LM358D")
    plan = build_phase4_parametric_query_plan(item, base_query="LM358D IC")

    assert plan.use_parametric is False
    assert plan.keyword_query == "LM358D IC"
