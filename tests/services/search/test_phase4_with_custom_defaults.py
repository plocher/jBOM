"""Integration tests: Phase 4 heuristics with custom defaults profiles.

Verifies that build_phase4_parametric_query_plan() uses the provided
DefaultsConfig rather than hard-coded values, and that the defaults
profile system correctly influences query plan construction.
"""

from __future__ import annotations

from pathlib import Path

from jbom.common.types import InventoryItem
from jbom.config.defaults import load_defaults
from jbom.services.search.jlcpcb_phase4_heuristics import (
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


def test_custom_defaults_override_resistor_tolerance(tmp_path: Path) -> None:
    """A profile overriding resistor tolerance to 1% should be used in the plan."""
    jbom_dir = tmp_path / ".jbom"
    jbom_dir.mkdir()
    (jbom_dir / "tight.defaults.yaml").write_text(
        "extends: generic\n"
        "domain_defaults:\n"
        "  resistor:\n"
        "    tolerance: '1%'\n"
    )

    cfg = load_defaults("tight", cwd=tmp_path)
    item = _inv_item(
        category="RES",
        value="10K",
        package="0603",
        tolerance="",  # blank → use domain default
        resistance=10_000.0,
    )
    plan = build_phase4_parametric_query_plan(
        item, base_query="10K resistor 0603", defaults=cfg
    )

    assert plan.use_parametric is True
    assert ("Tolerance", ("1%",)) in plan.component_attribute_list
    assert ("Tolerance", ("5%",)) not in plan.component_attribute_list


def test_generic_defaults_resistor_tolerance_is_5pct() -> None:
    """Baseline: without override, resistor tolerance defaults to 5%."""
    cfg = load_defaults("generic")
    item = _inv_item(
        category="RES",
        value="10K",
        package="0603",
        tolerance="",
        resistance=10_000.0,
    )
    plan = build_phase4_parametric_query_plan(
        item, base_query="10K resistor 0603", defaults=cfg
    )

    assert plan.use_parametric is True
    assert ("Tolerance", ("5%",)) in plan.component_attribute_list


def test_custom_defaults_override_capacitor_dielectric(tmp_path: Path) -> None:
    """A profile overriding capacitor dielectric to C0G is used in keyword query."""
    jbom_dir = tmp_path / ".jbom"
    jbom_dir.mkdir()
    (jbom_dir / "precision.defaults.yaml").write_text(
        "extends: generic\n"
        "domain_defaults:\n"
        "  capacitor:\n"
        "    dielectric: 'C0G'\n"
        "    tolerance: '5%'\n"
    )

    cfg = load_defaults("precision", cwd=tmp_path)
    item = _inv_item(
        category="CAP",
        value="100nF",
        package="0603",
        tolerance="",
        voltage="",
        type_="",  # no dielectric hint → use domain default
        capacitance=100e-9,
    )
    plan = build_phase4_parametric_query_plan(
        item, base_query="100nF cap 0603", defaults=cfg
    )

    assert plan.use_parametric is True
    assert "C0G" in plan.keyword_query
    assert "X7R" not in plan.keyword_query  # generic default not used


def test_defaults_none_uses_generic_profile() -> None:
    """defaults=None should load the generic profile automatically."""
    item = _inv_item(
        category="RES",
        value="10K",
        package="0603",
        tolerance="",
        resistance=10_000.0,
    )
    plan = build_phase4_parametric_query_plan(
        item, base_query="10K resistor 0603", defaults=None
    )

    assert plan.use_parametric is True
    # Should use generic 5% default
    assert ("Tolerance", ("5%",)) in plan.component_attribute_list


def test_custom_defaults_routing_rules_respected(tmp_path: Path) -> None:
    """Category route rules from custom profile are used in plan."""
    jbom_dir = tmp_path / ".jbom"
    jbom_dir.mkdir()
    (jbom_dir / "custom_routes.defaults.yaml").write_text(
        "extends: generic\n"
        "category_route_rules:\n"
        "  resistor:\n"
        "    first_sort: 'Custom Resistors Category'\n"
        "    second_sort_smd: 'Custom SMD Resistors'\n"
        "    second_sort_pth: 'Custom PTH Resistors'\n"
    )

    cfg = load_defaults("custom_routes", cwd=tmp_path)
    item = _inv_item(
        category="RES",
        value="10K",
        package="0603",
        smd="SMD",
        resistance=10_000.0,
    )
    plan = build_phase4_parametric_query_plan(
        item, base_query="10K resistor 0603", defaults=cfg
    )

    assert plan.use_parametric is True
    assert plan.first_sort_name == "Custom Resistors Category"
    assert plan.second_sort_name == "Custom SMD Resistors"
