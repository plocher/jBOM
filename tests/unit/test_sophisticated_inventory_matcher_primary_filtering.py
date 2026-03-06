"""Unit tests for sophisticated matcher primary filtering (Task 1.5b)."""

from __future__ import annotations

from jbom.common.types import Component, InventoryItem
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)


def _make_component(
    *,
    lib_id: str,
    value: str = "",
    footprint: str = "",
) -> Component:
    return Component(reference="R1", lib_id=lib_id, value=value, footprint=footprint)


def _make_inventory_item(
    *,
    category: str,
    value: str = "",
    package: str = "",
) -> InventoryItem:
    return InventoryItem(
        ipn="IPN-1",
        keywords="",
        category=category,
        description="",
        smd="",
        value=value,
        type="",
        tolerance="",
        voltage="",
        amperage="",
        wattage="",
        lcsc="",
        manufacturer="",
        mfgpn="",
        datasheet="",
        package=package,
    )


def test_type_filter_rejects_mismatched_category() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R", value="10K", footprint="R_0603_1608Metric"
    )
    item = _make_inventory_item(category="CAP", value="10K", package="0603")

    assert matcher._passes_primary_filters(component, item) is False


def test_type_filter_skipped_when_component_type_unknown() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(lib_id="Foo:ABC")
    item = _make_inventory_item(category="CAP")

    assert matcher._passes_primary_filters(component, item) is True


def test_package_filter_rejects_when_extracted_package_not_in_inventory_package() -> (
    None
):
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R", value="10K", footprint="R_0603_1608Metric"
    )
    item = _make_inventory_item(category="RES", value="10K", package="0805")

    assert matcher._passes_primary_filters(component, item) is False


def test_resistor_value_filter_numeric_equality() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R", value="10K", footprint="R_0603_1608Metric"
    )

    ok = _make_inventory_item(category="RES", value="10k", package="0603")
    bad = _make_inventory_item(category="RES", value="11K", package="0603")

    assert matcher._passes_primary_filters(component, ok) is True
    assert matcher._passes_primary_filters(component, bad) is False


def test_tilde_component_value_is_treated_as_blank_constraint() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R", value="~", footprint="R_0603_1608Metric"
    )
    item = _make_inventory_item(category="RES", value="47K", package="0603")

    # "~" means no value constraint from component side, so this passes
    # even though item.value differs.
    assert matcher._passes_primary_filters(component, item) is True


def test_capacitor_value_filter_numeric_equivalence_across_units() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:C", value="100nF", footprint="C_0603_1608Metric"
    )

    ok = _make_inventory_item(category="CAP", value="0.1uF", package="0603")
    bad = _make_inventory_item(category="CAP", value="10nF", package="0603")

    assert matcher._passes_primary_filters(component, ok) is True
    assert matcher._passes_primary_filters(component, bad) is False


def test_non_passive_value_filter_uses_normalized_string_comparison() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:U", value="ATmega328", footprint="TQFP-32"
    )

    ok = _make_inventory_item(category="IC", value=" atmega328 ", package="tqfp")
    bad = _make_inventory_item(category="IC", value="ATmega328P", package="tqfp")

    assert matcher._passes_primary_filters(component, ok) is True
    assert matcher._passes_primary_filters(component, bad) is False
