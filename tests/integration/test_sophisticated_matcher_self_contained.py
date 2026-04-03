"""Self-contained integration tests for SophisticatedInventoryMatcher.

These tests are deterministic and do not depend on external inventory files.
They should fail only on code regressions.

Task: Phase 1 / Task 1.6.
"""

from __future__ import annotations

from jbom.common.types import Component, InventoryItem
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)


def _make_component(
    *,
    reference: str,
    lib_id: str,
    value: str,
    footprint: str,
    properties: dict[str, str] | None = None,
) -> Component:
    return Component(
        reference=reference,
        lib_id=lib_id,
        value=value,
        footprint=footprint,
        properties=properties or {},
    )


def _make_item(
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


def test_orders_by_priority_then_score_desc() -> None:
    """Ordering contract: priority dominates; score is a tie-breaker within priority.

    This tests the *what* (ordering behavior), not the exact score arithmetic.
    """

    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    comp = _make_component(
        reference="R1",
        lib_id="Device:R",
        value="10k",
        footprint="R_0603_1608Metric",
        properties={"Tolerance": "5%"},
    )

    # Better match quality but worse priority should sort after.
    better_match_worse_priority = _make_item(
        ipn="A",
        category="RES",
        value="10k",
        package="0603",
        priority=2,
        keywords="foo 10k bar",
        tolerance="5%",
    )
    weaker_match_better_priority = _make_item(
        ipn="B",
        category="RES",
        value="10k",
        package="0603",
        priority=1,
        keywords="",
        tolerance="",
    )

    results = matcher.find_matches(
        comp, [better_match_worse_priority, weaker_match_better_priority]
    )
    assert [r.inventory_item.ipn for r in results] == ["B", "A"]


def test_primary_filters_reject_wrong_category() -> None:
    """Correctness contract: mismatched categories are eliminated, not merely de-ranked."""

    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    comp = _make_component(
        reference="C1",
        lib_id="Device:C",
        value="0.1uF",
        footprint="C_0603_1608Metric",
    )

    wrong = _make_item(
        ipn="RES-10K",
        category="RES",
        value="10k",
        package="0603",
        priority=1,
    )

    assert matcher.find_matches(comp, [wrong]) == []


def test_primary_filters_reject_wrong_package() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    comp = _make_component(
        reference="R1",
        lib_id="Device:R",
        value="10k",
        footprint="R_0603_1608Metric",
    )

    wrong_pkg = _make_item(
        ipn="RES-10K-0805",
        category="RES",
        value="10k",
        package="0805",
        priority=1,
    )

    assert matcher.find_matches(comp, [wrong_pkg]) == []


def test_capacitor_numeric_equivalence_100nf_matches_0_1uf() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    comp = _make_component(
        reference="C1",
        lib_id="Device:C",
        value="100nF",
        footprint="C_0603_1608Metric",
    )

    item = _make_item(
        ipn="CAP-0.1uF-0603",
        category="CAP",
        value="0.1uF",
        package="0603",
        priority=1,
    )

    results = matcher.find_matches(comp, [item])
    assert results
    assert results[0].inventory_item.ipn == "CAP-0.1uF-0603"


def test_led_value_normalization_case_and_whitespace() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    comp = _make_component(
        reference="D1",
        lib_id="Device:LED",
        value="Red",
        footprint="LED_0603_1608Metric",
    )

    item = _make_item(
        ipn="LED-RED-0603",
        category="LED",
        value=" red ",
        package="0603",
        priority=1,
    )

    results = matcher.find_matches(comp, [item])
    assert results
    assert results[0].inventory_item.ipn == "LED-RED-0603"


def test_within_same_priority_prefers_better_electro_mechanical_fit() -> None:
    """Ranking goal: within the same priority bucket, better-fit items should rank first."""

    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    comp = _make_component(
        reference="R1",
        lib_id="Device:R",
        value="10k",
        footprint="R_0603_1608Metric",
        properties={"Tolerance": "10%"},
    )

    best_fit = _make_item(
        ipn="RES-10K-0603-1%",
        category="RES",
        value="10k",
        package="0603",
        priority=1,
        tolerance="1%",
        keywords="10k",
    )
    weaker_fit = _make_item(
        ipn="RES-10K-0603-5%",
        category="RES",
        value="10k",
        package="0603",
        priority=1,
        tolerance="5%",
        keywords="",
    )

    results = matcher.find_matches(comp, [weaker_fit, best_fit])
    assert [r.inventory_item.ipn for r in results] == [best_fit.ipn, weaker_fit.ipn]


def test_debug_info_optional() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions(include_debug_info=True))

    comp = _make_component(
        reference="R1",
        lib_id="Device:R",
        value="10k",
        footprint="R_0603_1608Metric",
    )

    item = _make_item(
        ipn="RES-10K-0603",
        category="RES",
        value="10k",
        package="0603",
        priority=99,
    )

    results = matcher.find_matches(comp, [item])
    assert results
    assert results[0].debug_info
