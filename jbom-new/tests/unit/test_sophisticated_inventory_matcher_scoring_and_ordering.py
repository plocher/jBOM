"""Unit tests for sophisticated matcher scoring + ordering (Task 1.5c)."""

from __future__ import annotations

from jbom.common.types import Component, InventoryItem
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)


def _make_component(
    *,
    lib_id: str,
    value: str,
    footprint: str,
    properties: dict[str, str] | None = None,
) -> Component:
    return Component(
        reference="R1",
        lib_id=lib_id,
        value=value,
        footprint=footprint,
        properties=properties or {},
    )


def _make_inventory_item(
    *,
    ipn: str,
    category: str,
    value: str,
    package: str,
    priority: int,
    keywords: str = "",
    tolerance: str = "",
    voltage: str = "",
    wattage: str = "",
) -> InventoryItem:
    return InventoryItem(
        ipn=ipn,
        keywords=keywords,
        category=category,
        description="",
        smd="",
        value=value,
        type="",
        tolerance=tolerance,
        voltage=voltage,
        amperage="",
        wattage=wattage,
        lcsc="",
        manufacturer="",
        mfgpn="",
        datasheet="",
        package=package,
        priority=priority,
    )


def test_calculate_match_score_weights_include_type_value_package_properties_keywords() -> (
    None
):
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R",
        value="10K",
        footprint="R_0603_1608Metric",
        properties={"Tolerance": "5%"},
    )
    item = _make_inventory_item(
        ipn="IPN-1",
        category="RES",
        value="10k",
        package="0603",
        priority=2,
        keywords="foo 10K bar",
        tolerance="5%",
    )

    # Expected legacy weights:
    # - type match: 50
    # - value match: 40
    # - package match: 30
    # - tolerance exact: 15
    # - keyword match: 10
    assert matcher._calculate_match_score(component, item) == 145


def test_find_matches_orders_by_priority_then_score_desc() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R",
        value="10K",
        footprint="R_0603_1608Metric",
        properties={"Tolerance": "5%"},
    )

    high_score_low_priority = _make_inventory_item(
        ipn="HIGH-SCORE",
        category="RES",
        value="10k",
        package="0603",
        priority=2,
        keywords="foo 10K bar",
        tolerance="5%",
    )

    lower_score_high_priority = _make_inventory_item(
        ipn="LOWER-SCORE",
        category="RES",
        value="10k",
        package="0603",
        priority=1,
        keywords="",
        tolerance="",
    )

    results = matcher.find_matches(
        component, [high_score_low_priority, lower_score_high_priority]
    )

    assert [r.inventory_item.ipn for r in results] == ["LOWER-SCORE", "HIGH-SCORE"]


def test_debug_info_optional() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions(include_debug_info=True))

    component = _make_component(
        lib_id="Device:R",
        value="10K",
        footprint="R_0603_1608Metric",
    )
    item = _make_inventory_item(
        ipn="IPN-1",
        category="RES",
        value="10k",
        package="0603",
        priority=99,
    )

    results = matcher.find_matches(component, [item])
    assert results
    assert results[0].debug_info
