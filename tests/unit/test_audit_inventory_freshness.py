"""Unit tests for AuditService inventory freshness checks (Issue #117 Path A).

Covers:
- _check_item_freshness: STALE_PART when no candidates
- _check_item_freshness: BETTER_AVAILABLE when best PN differs from existing
- _check_item_freshness: silent when best PN matches existing
- _check_item_freshness: skips items with no supplier PN (empty → [])
- _get_supplier_pn_for_item: returns item.lcsc for 'lcsc' supplier
- _get_supplier_pn_for_item: reads raw_data[inventory_column] for others
- audit_inventory: freshness runs even without --requirements
- audit_inventory: early-return guard fixed (requirements_path=None + supplier_service given)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from jbom.common.types import InventoryItem
from jbom.services.audit_service import (
    AuditService,
    CheckType,
    Severity,
    _get_supplier_pn_for_item,
)
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
    supplier_pn: str = "",
    lcsc: str = "",
) -> InventoryItem:
    item = InventoryItem(
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
        manufacturer="",
        mfgpn="",
        datasheet="",
        package=package,
        row_type="ITEM",
        raw_data={"Supplier": supplier_pn} if supplier_pn else {},
    )
    return item


def _make_search_result(pn: str = "S25804") -> SearchResult:
    return SearchResult(
        manufacturer="Yageo",
        mpn="RC0603FR-0710KL",
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


def _candidate(pn: str = "S25804") -> InventorySearchCandidate:
    return InventorySearchCandidate(result=_make_search_result(pn), match_score=80)


def _mock_service_returning(pn: str | None) -> InventorySearchService:
    """Mock service that returns one candidate with given PN, or no candidates."""
    service = MagicMock(spec=InventorySearchService)
    if pn is not None:
        record = InventorySearchRecord(
            inventory_item=MagicMock(),
            query="10K resistor",
            candidates=[_candidate(pn)],
        )
    else:
        record = InventorySearchRecord(
            inventory_item=MagicMock(),
            query="10K resistor",
            candidates=[],
        )
    service.search.return_value = [record]
    return service


# ---------------------------------------------------------------------------
# _get_supplier_pn_for_item
# ---------------------------------------------------------------------------


class TestGetSupplierPnForItem:
    def test_returns_lcsc_for_lcsc_supplier(self) -> None:
        item = _make_item(lcsc="C25804")
        result = _get_supplier_pn_for_item(item, "lcsc")
        assert result == "C25804"

    def test_empty_lcsc_returns_empty_string(self) -> None:
        item = _make_item()  # lcsc=""
        result = _get_supplier_pn_for_item(item, "lcsc")
        assert result == ""

    def test_returns_raw_data_column_for_generic(self) -> None:
        item = _make_item(supplier_pn="S99999")
        # generic supplier has inventory_column = "Supplier"
        result = _get_supplier_pn_for_item(item, "generic")
        assert result == "S99999"

    def test_empty_raw_data_returns_empty_string(self) -> None:
        item = _make_item()  # no Supplier in raw_data
        result = _get_supplier_pn_for_item(item, "generic")
        assert result == ""

    def test_unknown_supplier_returns_empty_string(self) -> None:
        item = _make_item(supplier_pn="X99")
        result = _get_supplier_pn_for_item(item, "completely_unknown_supplier_xyz")
        assert result == ""


# ---------------------------------------------------------------------------
# AuditService._check_item_freshness
# ---------------------------------------------------------------------------


class TestCheckItemFreshness:
    """Direct tests of AuditService._check_item_freshness."""

    def _run(
        self,
        item: InventoryItem,
        *,
        supplier_service: InventorySearchService,
        supplier_id: str = "generic",
    ) -> list:
        svc = AuditService()
        return svc._check_item_freshness(
            item, "catalog.csv", supplier_service, supplier_id
        )

    def test_stale_part_when_no_candidates(self) -> None:
        item = _make_item(supplier_pn="S99999")
        service = _mock_service_returning(None)  # no candidates

        rows = self._run(item, supplier_service=service)

        assert len(rows) == 1
        row = rows[0]
        assert row.check_type == CheckType.STALE_PART
        assert row.severity == Severity.WARN
        assert row.ipn == "RES_10K_0603"
        assert row.supplier == "generic"
        assert row.current_value == "S99999"
        assert row.supplier_pn == "S99999"
        assert "S99999" in row.description

    def test_better_available_when_different_best_pn(self) -> None:
        item = _make_item(supplier_pn="S99001")  # existing PN
        service = _mock_service_returning("S25804")  # better PN

        rows = self._run(item, supplier_service=service)

        assert len(rows) == 1
        row = rows[0]
        assert row.check_type == CheckType.BETTER_AVAILABLE
        assert row.severity == Severity.INFO
        assert row.current_value == "S99001"
        assert row.suggested_value == "S25804"
        assert row.supplier_pn == "S25804"
        assert "S99001" in row.description
        assert "S25804" in row.description

    def test_silent_when_existing_pn_matches_best(self) -> None:
        item = _make_item(supplier_pn="S25804")  # matches best result
        service = _mock_service_returning("S25804")

        rows = self._run(item, supplier_service=service)

        assert rows == []

    def test_skips_item_with_no_supplier_pn(self) -> None:
        item = _make_item()  # no Supplier in raw_data
        service = _mock_service_returning(None)

        rows = self._run(item, supplier_service=service)

        # Service should not be called since there's no existing PN to check.
        assert rows == []
        service.search.assert_not_called()

    def test_description_includes_supplier_id(self) -> None:
        item = _make_item(supplier_pn="S99999")
        service = _mock_service_returning(None)

        rows = self._run(item, supplier_service=service, supplier_id="generic")

        assert len(rows) == 1
        assert "generic" in rows[0].description

    def test_catalog_file_set_on_row(self) -> None:
        item = _make_item(supplier_pn="S99999")
        service = _mock_service_returning(None)

        svc = AuditService()
        rows = svc._check_item_freshness(item, "my_catalog.csv", service, "generic")

        assert len(rows) == 1
        assert rows[0].catalog_file == "my_catalog.csv"


# ---------------------------------------------------------------------------
# audit_inventory integration: early-return guard + freshness
# ---------------------------------------------------------------------------


class TestAuditInventoryFreshnessIntegration:
    """Test audit_inventory() with supplier_service and no requirements_path."""

    def _make_catalog_item(self, supplier_pn: str = "S99999") -> InventoryItem:
        return _make_item(supplier_pn=supplier_pn)

    def test_freshness_runs_without_requirements(self) -> None:
        """audit_inventory runs freshness even when requirements_path is None."""
        from pathlib import Path

        service = _mock_service_returning(None)  # no candidates → STALE_PART

        svc = AuditService()

        # Patch InventoryReader to return our catalog item.
        catalog_item = self._make_catalog_item("S99999")
        with patch("jbom.services.audit_service.InventoryReader") as MockReader:
            mock_reader = MagicMock()
            mock_reader.load.return_value = ([catalog_item], [])
            MockReader.return_value = mock_reader

            report = svc.audit_inventory(
                catalog_paths=[Path("catalog.csv")],
                requirements_path=None,
                supplier_service=service,
                supplier_id="generic",
            )

        stale_rows = [r for r in report.rows if r.check_type == CheckType.STALE_PART]
        assert len(stale_rows) == 1
        assert stale_rows[0].current_value == "S99999"

    def test_no_freshness_rows_when_no_supplier_service(self) -> None:
        """Without supplier_service, freshness block is not entered."""
        from pathlib import Path

        svc = AuditService()
        catalog_item = self._make_catalog_item("S99999")
        with patch("jbom.services.audit_service.InventoryReader") as MockReader:
            mock_reader = MagicMock()
            mock_reader.load.return_value = ([catalog_item], [])
            MockReader.return_value = mock_reader

            report = svc.audit_inventory(
                catalog_paths=[Path("catalog.csv")],
                requirements_path=None,
                supplier_service=None,
            )

        # No supplier service → returns empty report early
        assert report.rows == []

    def test_better_available_without_requirements(self) -> None:
        from pathlib import Path

        service = _mock_service_returning("S25804")
        svc = AuditService()

        catalog_item = self._make_catalog_item("S99001")
        with patch("jbom.services.audit_service.InventoryReader") as MockReader:
            mock_reader = MagicMock()
            mock_reader.load.return_value = ([catalog_item], [])
            MockReader.return_value = mock_reader

            report = svc.audit_inventory(
                catalog_paths=[Path("catalog.csv")],
                requirements_path=None,
                supplier_service=service,
                supplier_id="generic",
            )

        better_rows = [
            r for r in report.rows if r.check_type == CheckType.BETTER_AVAILABLE
        ]
        assert len(better_rows) == 1
        assert better_rows[0].current_value == "S99001"
        assert better_rows[0].suggested_value == "S25804"
