"""Unit tests for _enrich_items_with_supplier (Issue #117 Path B).

Covers:
- Items that already carry a PN are skipped
- Items without a PN are enriched with the best candidate's distributor_pn
- LCSC supplier writes pn to item.lcsc
- Generic supplier writes pn to item.raw_data[inventory_column]
- Supplier column is added to field_names when absent
- Supplier column unchanged when already present in field_names
- manufacturer and mfgpn are backfilled when blank
- Items without candidates remain un-enriched
- Both ITEM and COMPONENT row types are enriched
- HEADER rows are ignored
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from jbom.cli.inventory import _enrich_items_with_supplier
from jbom.common.types import InventoryItem
from jbom.services.search.inventory_search_service import (
    InventorySearchCandidate,
    InventorySearchRecord,
    InventorySearchService,
)
from jbom.services.search.models import SearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(
    *,
    ipn: str = "RES_10K_0603",
    category: str = "RES",
    value: str = "10K",
    package: str = "0603",
    row_type: str = "ITEM",
    supplier_pn: str = "",
    lcsc: str = "",
    manufacturer: str = "",
    mfgpn: str = "",
) -> InventoryItem:
    return InventoryItem(
        ipn=ipn,
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
        lcsc=lcsc,
        manufacturer=manufacturer,
        mfgpn=mfgpn,
        datasheet="",
        package=package,
        row_type=row_type,
        raw_data={"Supplier": supplier_pn} if supplier_pn else {},
    )


def _make_result(
    *, pn: str = "S25804", mfr: str = "Yageo", mpn: str = "RC0603"
) -> SearchResult:
    return SearchResult(
        manufacturer=mfr,
        mpn=mpn,
        description="RES 10K 1% 0603",
        datasheet="",
        distributor="generic",
        distributor_part_number=pn,
        availability="500 In Stock",
        price="0.01",
        details_url="",
        raw_data={},
        stock_quantity=500,
    )


def _candidate(
    pn: str = "S25804", mfr: str = "Yageo", mpn: str = "RC0603"
) -> InventorySearchCandidate:
    return InventorySearchCandidate(
        result=_make_result(pn=pn, mfr=mfr, mpn=mpn), match_score=80
    )


def _record_with_candidate(
    item: InventoryItem, pn: str = "S25804"
) -> InventorySearchRecord:
    return InventorySearchRecord(
        inventory_item=item,
        query="10K resistor",
        candidates=[_candidate(pn=pn)],
    )


def _record_no_candidates(item: InventoryItem) -> InventorySearchRecord:
    return InventorySearchRecord(
        inventory_item=item,
        query="10K resistor",
        candidates=[],
    )


def _supplier_config(inventory_column: str = "Supplier") -> MagicMock:
    cfg = MagicMock()
    cfg.inventory_column = inventory_column
    cfg.id = "generic"
    return cfg


def _mock_service(records: list[InventorySearchRecord]) -> MagicMock:
    service = MagicMock(spec=InventorySearchService)
    service.search.return_value = records
    return service


# ---------------------------------------------------------------------------
# Helper to run _enrich_items_with_supplier with filter_searchable_items mocked
# ---------------------------------------------------------------------------


def _enrich(
    items: list[InventoryItem],
    field_names: list[str],
    service: MagicMock,
    supplier_config=None,
    supplier_id: str = "generic",
    *,
    verbose: bool = False,
    filter_returns: list[InventoryItem] | None = None,
) -> tuple[list[InventoryItem], list[str]]:
    """Run _enrich_items_with_supplier with filter_searchable_items controlled."""
    if supplier_config is None:
        supplier_config = _supplier_config()

    # filter_searchable_items is a static method — patch at the class level.
    with patch.object(
        InventorySearchService,
        "filter_searchable_items",
        return_value=filter_returns if filter_returns is not None else items,
    ):
        return _enrich_items_with_supplier(
            items, field_names, service, supplier_config, supplier_id, verbose=verbose
        )


# ---------------------------------------------------------------------------
# Field-name management
# ---------------------------------------------------------------------------


class TestEnrichFieldNames:
    def test_supplier_column_added_when_absent(self) -> None:
        item = _make_item()
        service = _mock_service([_record_no_candidates(item)])
        _, names = _enrich([item], ["IPN", "Value"], service, filter_returns=[item])
        assert "Supplier" in names

    def test_supplier_column_not_duplicated_when_present(self) -> None:
        item = _make_item()
        service = _mock_service([_record_no_candidates(item)])
        _, names = _enrich(
            [item], ["IPN", "Supplier", "Value"], service, filter_returns=[item]
        )
        assert names.count("Supplier") == 1

    def test_existing_field_order_preserved_except_appended(self) -> None:
        item = _make_item()
        service = _mock_service([_record_no_candidates(item)])
        _, names = _enrich([item], ["IPN", "Value"], service, filter_returns=[item])
        assert names[0] == "IPN"
        assert names[1] == "Value"
        assert names[-1] == "Supplier"


# ---------------------------------------------------------------------------
# Skipping already-enriched items
# ---------------------------------------------------------------------------


class TestEnrichSkipsExistingPn:
    def test_item_with_existing_pn_is_not_overwritten(self) -> None:
        item = _make_item(supplier_pn="S_EXISTING")
        service = _mock_service([])  # search should not be called

        items_out, _ = _enrich([item], ["IPN"], service, filter_returns=[])

        service.search.assert_not_called()
        # Raw data should be unchanged
        assert items_out[0].raw_data.get("Supplier") == "S_EXISTING"

    def test_lcsc_item_with_existing_lcsc_is_not_overwritten(self) -> None:
        item = _make_item(lcsc="C_EXISTING", row_type="ITEM")
        cfg = _supplier_config("LCSC")
        service = _mock_service([])

        with patch.object(
            InventorySearchService, "filter_searchable_items", return_value=[]
        ):
            items_out, _ = _enrich_items_with_supplier(
                [item], ["IPN"], service, cfg, "lcsc"
            )

        service.search.assert_not_called()
        assert items_out[0].lcsc == "C_EXISTING"


# ---------------------------------------------------------------------------
# Successful enrichment
# ---------------------------------------------------------------------------


class TestEnrichSuccessful:
    def test_generic_supplier_writes_to_raw_data(self) -> None:
        item = _make_item()
        service = _mock_service([_record_with_candidate(item, "S25804")])

        items_out, _ = _enrich([item], ["IPN"], service, filter_returns=[item])

        assert items_out[0].raw_data.get("Supplier") == "S25804"

    def test_lcsc_supplier_writes_to_lcsc_field(self) -> None:
        item = _make_item(lcsc="")
        cfg = _supplier_config("LCSC")
        record = InventorySearchRecord(
            inventory_item=item,
            query="10K",
            candidates=[_candidate("C25804")],
        )
        service = _mock_service([record])

        with patch.object(
            InventorySearchService, "filter_searchable_items", return_value=[item]
        ):
            items_out, _ = _enrich_items_with_supplier(
                [item], ["IPN"], service, cfg, "lcsc"
            )

        assert items_out[0].lcsc == "C25804"

    def test_manufacturer_backfilled_when_blank(self) -> None:
        item = _make_item(manufacturer="")
        record = InventorySearchRecord(
            inventory_item=item,
            query="10K",
            candidates=[_candidate("S25804", mfr="Yageo", mpn="RC0603")],
        )
        service = _mock_service([record])
        items_out, _ = _enrich([item], ["IPN"], service, filter_returns=[item])

        assert items_out[0].manufacturer == "Yageo"

    def test_mfgpn_backfilled_when_blank(self) -> None:
        item = _make_item(mfgpn="")
        record = InventorySearchRecord(
            inventory_item=item,
            query="10K",
            candidates=[_candidate("S25804", mpn="RC0603FR-0710KL")],
        )
        service = _mock_service([record])
        items_out, _ = _enrich([item], ["IPN"], service, filter_returns=[item])

        assert items_out[0].mfgpn == "RC0603FR-0710KL"

    def test_manufacturer_not_overwritten_when_present(self) -> None:
        item = _make_item(manufacturer="Original Mfr")
        record = InventorySearchRecord(
            inventory_item=item,
            query="10K",
            candidates=[_candidate("S25804", mfr="Yageo")],
        )
        service = _mock_service([record])
        items_out, _ = _enrich([item], ["IPN"], service, filter_returns=[item])

        assert items_out[0].manufacturer == "Original Mfr"

    def test_mfgpn_not_overwritten_when_present(self) -> None:
        item = _make_item(mfgpn="RC0402FR-07100KL")
        record = InventorySearchRecord(
            inventory_item=item,
            query="10K",
            candidates=[_candidate("S25804", mpn="RC0603FR-0710KL")],
        )
        service = _mock_service([record])
        items_out, _ = _enrich([item], ["IPN"], service, filter_returns=[item])

        assert items_out[0].mfgpn == "RC0402FR-07100KL"


# ---------------------------------------------------------------------------
# No-candidates path
# ---------------------------------------------------------------------------


class TestEnrichNoCandidates:
    def test_no_candidates_leaves_item_unchanged(self) -> None:
        item = _make_item()
        service = _mock_service([_record_no_candidates(item)])

        items_out, _ = _enrich([item], ["IPN"], service, filter_returns=[item])

        assert items_out[0].raw_data.get("Supplier", "") == ""

    def test_empty_pn_in_candidate_leaves_item_unchanged(self) -> None:
        item = _make_item()
        # Candidate exists but distributor_part_number is ""
        result = SearchResult(
            manufacturer="",
            mpn="",
            description="",
            datasheet="",
            distributor="generic",
            distributor_part_number="",
            availability="",
            price="",
            details_url="",
            raw_data={},
            stock_quantity=0,
        )
        record = InventorySearchRecord(
            inventory_item=item,
            query="10K",
            candidates=[InventorySearchCandidate(result=result, match_score=80)],
        )
        service = _mock_service([record])
        items_out, _ = _enrich([item], ["IPN"], service, filter_returns=[item])

        assert items_out[0].raw_data.get("Supplier", "") == ""


# ---------------------------------------------------------------------------
# Row type handling
# ---------------------------------------------------------------------------


class TestEnrichRowTypes:
    def test_component_row_is_enriched(self) -> None:
        item = _make_item(row_type="COMPONENT")
        service = _mock_service([_record_with_candidate(item, "S25804")])

        items_out, _ = _enrich([item], ["IPN"], service, filter_returns=[item])

        assert items_out[0].raw_data.get("Supplier") == "S25804"

    def test_item_row_is_enriched(self) -> None:
        item = _make_item(row_type="ITEM")
        service = _mock_service([_record_with_candidate(item, "S25804")])

        items_out, _ = _enrich([item], ["IPN"], service, filter_returns=[item])

        assert items_out[0].raw_data.get("Supplier") == "S25804"

    def test_header_row_is_ignored(self) -> None:
        header = _make_item(row_type="HEADER")
        normal = _make_item(ipn="RES_4K7_0603", row_type="ITEM")
        service = _mock_service([_record_with_candidate(normal, "S99001")])

        items_out, _ = _enrich(
            [header, normal],
            ["IPN"],
            service,
            filter_returns=[normal],  # filter_searchable_items skips header
        )

        # header row untouched; normal item enriched
        assert items_out[0].raw_data.get("Supplier", "") == ""
        assert items_out[1].raw_data.get("Supplier") == "S99001"


# ---------------------------------------------------------------------------
# No-op path (nothing to enrich)
# ---------------------------------------------------------------------------


class TestEnrichNoOp:
    def test_all_items_already_have_pn_no_search(self) -> None:
        items = [
            _make_item(supplier_pn="S001"),
            _make_item(ipn="CAP_100N_0402", supplier_pn="S002"),
        ]
        service = _mock_service([])

        # filter_searchable_items returns [] because needs_pn is empty
        items_out, _ = _enrich(items, ["IPN"], service, filter_returns=[])

        service.search.assert_not_called()

    def test_no_searchable_items_after_filter(self) -> None:
        item = _make_item(category="SLK")  # typically filtered out
        service = _mock_service([])

        items_out, _ = _enrich([item], ["IPN"], service, filter_returns=[])

        service.search.assert_not_called()

    def test_empty_items_list(self) -> None:
        service = _mock_service([])
        items_out, names = _enrich([], ["IPN"], service, filter_returns=[])

        assert items_out == []
        assert "Supplier" in names  # column is still added to field list
