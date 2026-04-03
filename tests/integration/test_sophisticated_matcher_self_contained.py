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


def test_issue_patterns_match_via_multi_signal_voting() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    connector_component = _make_component(
        reference="J10",
        lib_id="SPCoast:Conn_01x02_Socket",
        value="Conn_01x02_Socket",
        footprint="SPCoast:PinSocket_1x02_P2.54mm_Vertical",
    )
    connector_item = _make_item(
        ipn="CON_1x02-0.100-socket",
        category="CON",
        value="1x02-0.100-socket",
        package="",
        priority=1,
    )
    connector_item.raw_data = {"Footprint": "SPCoast:PinSocket_1x02_P2.54mm_Vertical"}
    connector_matches = matcher.find_matches(connector_component, [connector_item])
    assert connector_matches
    assert connector_matches[0].inventory_item.ipn == "CON_1x02-0.100-socket"

    ic_component = _make_component(
        reference="U2",
        lib_id="cpNode-ProMini-eagle-import:SparkFun_NE555P",
        value="NE555D",
        footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    )
    ic_item = _make_item(
        ipn="IC_NE555D_SOP-8",
        category="IC",
        value="NE555D",
        package="SOP-8",
        priority=1,
    )
    ic_matches = matcher.find_matches(ic_component, [ic_item])
    assert ic_matches
    assert ic_matches[0].inventory_item.ipn == "IC_NE555D_SOP-8"

    regulator_component = _make_component(
        reference="VR5.0",
        lib_id="Regulator_Linear:LM78M05_TO252",
        value="78M05",
        footprint="Package_TO_SOT_SMD:TO-252-2",
    )
    regulator_item = _make_item(
        ipn="REG_78M05_TO-252-2",
        category="REG",
        value="78M05",
        package="TO-252-2",
        priority=1,
    )
    regulator_item.raw_data = {"Footprint": "Package_TO_SOT_SMD:TO-252-2"}
    regulator_matches = matcher.find_matches(regulator_component, [regulator_item])
    assert regulator_matches
    assert regulator_matches[0].inventory_item.ipn == "REG_78M05_TO-252-2"


def test_lcsc_hard_accept_policy_can_validate_known_project_annotations() -> None:
    matcher = SophisticatedInventoryMatcher(
        MatchingOptions(
            lcsc_match_policy="hard_accept", non_passive_min_signal_score=999
        )
    )

    component = _make_component(
        reference="J1",
        lib_id="SPCoast:Conn_01x04",
        value="CON_1x04-0.100-screw",
        footprint="SPCoast:Connector_01x04_screw_V",
        properties={"LCSC": "C3816889"},
    )
    item = _make_item(
        ipn="CON_1x04-0.100-screw",
        category="CON",
        value="unrelated",
        package="",
        priority=1,
    )
    item.lcsc = "C3816889"

    matches = matcher.find_matches(component, [item])
    assert matches
    assert matches[0].inventory_item.ipn == "CON_1x04-0.100-screw"


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
