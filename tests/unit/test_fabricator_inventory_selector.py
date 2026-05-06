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
    fabricator: str = "",
    supplier: str = "",
    spn: str = "",
    mfgpn: str = "",
    raw_data: dict[str, str] | None = None,
) -> InventoryItem:
    # Only a subset of fields matter for selector behavior; others are placeholders.
    _raw = dict(raw_data or {})
    # Propagate supplier/spn into raw_data for backward compat with raw_data checks.
    if supplier or spn:
        _raw.setdefault("Supplier", supplier)
        _raw.setdefault("SPN", spn)
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
        supplier=supplier,
        spn=spn,
        manufacturer="",
        mfgpn=mfgpn,
        datasheet="",
        package="",
        uuid="",
        fabricator=fabricator,
        raw_data=_raw,
    )


def test_selector_does_not_filter_by_item_fabricator_field_preserves_order() -> None:
    """Selector uses supplier/spn; fabricator field on items is irrelevant."""
    config = load_fabricator("jlc")
    selector = FabricatorInventorySelector(config)

    # All items have LCSC supplier PN → all get tier 1 (fab_pn for JLC).
    items = [
        _make_item(ipn="GEN", fabricator="", supplier="LCSC", spn="C123"),
        _make_item(ipn="JLC", fabricator="jlc", supplier="LCSC", spn="C234"),
        _make_item(ipn="OTHER", fabricator="pcbway", supplier="LCSC", spn="C345"),
    ]

    eligible = selector.select_eligible(items)

    assert [e.item.ipn for e in eligible] == ["GEN", "JLC", "OTHER"]
    assert all(isinstance(e, EligibleInventoryItem) for e in eligible)

    # Selector must not mutate raw_data.
    assert "fab_pn" not in items[0].raw_data


def test_project_filter_allows_unrestricted_items() -> None:
    config = load_fabricator("generic")
    selector = FabricatorInventorySelector(config)

    # Item has MPN → eligible via tier 3.
    unrestricted = _make_item(ipn="U", mfgpn="PN-1")

    assert selector.select_eligible([unrestricted], project_name=None)


def test_project_filter_requires_project_when_restricted_and_normalizes_basename() -> (
    None
):
    config = load_fabricator("generic")
    selector = FabricatorInventorySelector(config)

    restricted = _make_item(
        ipn="R",
        mfgpn="PN-2",
        raw_data={"Projects": "CustomerA.kicad_pcb, CustomerB"},
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
        # Tier 3 (fab_pn exists): has LCSC SPN — maps to fab_pn for JLC.
        _make_item(ipn="T2", supplier="LCSC", spn="C1"),
        # Tier 1 (consigned override): consigned beats everything
        _make_item(
            ipn="T0",
            raw_data={"Consigned": "yes", "Supplier": "LCSC", "SPN": "C0"},
            supplier="LCSC",
            spn="C0",
        ),
        # Tier 2 (preferred + fab_pn): preferred + has SPN
        _make_item(
            ipn="T1",
            supplier="LCSC",
            spn="C2",
            raw_data={"Preferred": "1", "Supplier": "LCSC", "SPN": "C2"},
        ),
    ]

    eligible = selector.select_eligible(items)
    ipns = [e.item.ipn for e in eligible]
    assert "T2" in ipns
    assert "T0" in ipns
    assert "T1" in ipns
    tiers = {e.item.ipn: e.preference_tier for e in eligible}
    # Consigned (T0) should be in tier 1, preferred+fab_pn (T1) in tier 2,
    # plain fab_pn (T2) in tier 3.
    assert tiers["T0"] < tiers["T1"] < tiers["T2"]


def test_items_with_no_matching_tier_are_ineligible() -> None:
    config = load_fabricator("jlc")
    selector = FabricatorInventorySelector(config)

    bad = _make_item(ipn="BAD")

    assert selector.select_eligible([bad]) == []
