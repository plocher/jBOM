"""Unit tests for FabricatorInventorySelector (Phase 2 / Task 2.2)."""

from __future__ import annotations

from jbom.common.types import InventoryItem
from jbom.config.fabricators import load_fabricator
from jbom.services.fabricator_inventory_selector import (
    EligibleInventoryItem,
    FabricatorInventorySelector,
)


def _make_item(
    *,
    ipn: str,
    fabricator: str,
    raw_data: dict[str, str],
) -> InventoryItem:
    # Only a subset of fields matter for selector behavior; others are placeholders.
    return InventoryItem(
        ipn=ipn,
        keywords="",
        category="",
        description="",
        smd="",
        value="",
        type="",
        tolerance="",
        voltage="",
        amperage="",
        wattage="",
        lcsc="",
        manufacturer="",
        mfgpn="",
        datasheet="",
        package="",
        distributor="",
        distributor_part_number="",
        uuid="",
        fabricator=fabricator,
        raw_data=raw_data,
    )


def test_selector_does_not_filter_by_item_fabricator_field_preserves_order() -> None:
    config = load_fabricator("jlc")
    selector = FabricatorInventorySelector(config)

    items = [
        _make_item(
            ipn="GEN",
            fabricator="",
            raw_data={"LCSC Part #": "C123"},
        ),
        _make_item(
            ipn="JLC",
            fabricator="jlc",
            raw_data={"LCSC": "C234"},
        ),
        _make_item(
            ipn="OTHER",
            fabricator="pcbway",
            raw_data={"LCSC": "C345"},
        ),
    ]

    eligible = selector.select_eligible(items)

    assert [e.item.ipn for e in eligible] == ["GEN", "JLC", "OTHER"]
    assert all(isinstance(e, EligibleInventoryItem) for e in eligible)

    # Selector must not mutate raw_data.
    assert "fab_pn" not in items[0].raw_data


def test_project_filter_allows_unrestricted_items() -> None:
    config = load_fabricator("generic")
    selector = FabricatorInventorySelector(config)

    unrestricted = _make_item(
        ipn="U",
        fabricator="",
        raw_data={"Part Number": "PN-1"},
    )

    assert selector.select_eligible([unrestricted], project_name=None)


def test_project_filter_requires_project_when_restricted_and_normalizes_basename() -> (
    None
):
    config = load_fabricator("generic")
    selector = FabricatorInventorySelector(config)

    restricted = _make_item(
        ipn="R",
        fabricator="",
        raw_data={
            "Projects": "CustomerA.kicad_pcb, CustomerB",
            "Part Number": "PN-2",
        },
    )

    # Restricted items require a project_name.
    assert selector.select_eligible([restricted], project_name=None) == []

    # Basename normalization: .kicad_sch and .kicad_pcb should match the same project.
    assert selector.select_eligible([restricted], project_name="CustomerA.kicad_sch")

    # Case-sensitive: different project name should fail.
    assert (
        selector.select_eligible([restricted], project_name="customera.kicad_sch") == []
    )


def test_tier_assignment_consigned_preferred_catalog_and_order_preserved() -> None:
    config = load_fabricator("jlc")
    selector = FabricatorInventorySelector(config)

    items = [
        # Tier 2: catalog part number exists (via synonym normalization)
        _make_item(
            ipn="T2",
            fabricator="jlc",
            raw_data={"LCSC": "C1"},
        ),
        # Tier 0: consigned beats everything
        _make_item(
            ipn="T0",
            fabricator="jlc",
            raw_data={"Consigned": "yes"},
        ),
        # Tier 1: preferred + catalog
        _make_item(
            ipn="T1",
            fabricator="jlc",
            raw_data={"Preferred": "1", "LCSC Part #": "C2"},
        ),
    ]

    eligible = selector.select_eligible(items)
    assert [e.item.ipn for e in eligible] == ["T2", "T0", "T1"]
    assert [e.preference_tier for e in eligible] == [2, 0, 1]


def test_items_with_no_matching_tier_are_ineligible() -> None:
    config = load_fabricator("jlc")
    selector = FabricatorInventorySelector(config)

    bad = _make_item(
        ipn="BAD",
        fabricator="",
        raw_data={"Unrelated": "value"},
    )

    assert selector.select_eligible([bad]) == []
