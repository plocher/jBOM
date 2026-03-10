"""Tests for the audit --supplier validation tier (Issue #154 PR 2).

All supplier API calls are mocked via a fake InventorySearchService so no
network access is required.

Covers:
- SUPPLIER_MISS (ERROR) when supplier returns no candidates
- Silent (no row) when supplier finds component and no local inventory to check
- INVENTORY_GAP (INFO) when supplier finds component but it's absent from local inventory
- Silent when supplier finds component and it IS already in local inventory
- Supplier rows populate the Supplier column
- Supplier rows populate the SupplierPN column when a candidate is found
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from jbom.common.types import Component, InventoryItem
from jbom.services.audit_service import AuditService, CheckType, Severity
from jbom.services.search.inventory_search_service import (
    InventorySearchCandidate,
    InventorySearchRecord,
    InventorySearchService,
)
from jbom.services.search.models import SearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_component(
    *,
    ref: str = "R1",
    lib_id: str = "Device:R",
    value: str = "10K",
    footprint: str = "Resistor_SMD:R_0603",
    uuid: str = "uuid-r1",
    props: dict[str, str] | None = None,
) -> Component:
    return Component(
        reference=ref,
        lib_id=lib_id,
        value=value,
        footprint=footprint,
        uuid=uuid,
        properties=props or {},
    )


def _make_inventory_item(
    *,
    ipn: str = "R-10K-0603",
    category: str = "RES",
    value: str = "10K",
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
        lcsc="",
        manufacturer="",
        mfgpn=mfgpn,
        datasheet="",
        row_type="ITEM",
    )


def _make_search_result(*, distributor_pn: str = "M-12345") -> SearchResult:
    return SearchResult(
        manufacturer="Yageo",
        mpn="RC0603FR-0710KL",
        description="RES 10K 1% 0603",
        datasheet="",
        distributor="mouser",
        distributor_part_number=distributor_pn,
        availability="500 In Stock",
        price="$0.01",
        details_url="",
        raw_data={},
        lifecycle_status="Active",
        min_order_qty=1,
        category="",
        attributes={},
        stock_quantity=500,
    )


def _mock_service(
    *,
    candidates: list[InventorySearchCandidate] | None = None,
    error: str | None = None,
) -> InventorySearchService:
    """Return an InventorySearchService whose search() returns one record."""
    service = MagicMock(spec=InventorySearchService)
    record = InventorySearchRecord(
        inventory_item=MagicMock(),
        query="10K resistor",
        candidates=candidates or [],
        error=error,
    )
    service.search.return_value = [record]
    return service


def _candidate(*, pn: str = "M-12345") -> InventorySearchCandidate:
    return InventorySearchCandidate(
        result=_make_search_result(distributor_pn=pn),
        match_score=80,
    )


# ---------------------------------------------------------------------------
# AuditService._check_supplier_coverage unit tests
# ---------------------------------------------------------------------------


class TestSupplierCoverage:
    """Direct tests of AuditService._check_supplier_coverage via audit_project."""

    def _run(
        self,
        comp: Component,
        *,
        supplier_service: InventorySearchService,
        supplier_id: str = "mouser",
        inventory_items: list[InventoryItem] | None = None,
    ):
        """Call _check_supplier_coverage directly."""
        svc = AuditService()
        return svc._check_supplier_coverage(
            comp,
            "RES",
            "/proj",
            supplier_service,
            supplier_id,
            inventory_items or [],
        )

    def test_supplier_miss_when_no_candidates(self) -> None:
        comp = _make_component()
        mock_svc = _mock_service(candidates=[])

        row = self._run(comp, supplier_service=mock_svc)

        assert row is not None
        assert row.check_type == CheckType.SUPPLIER_MISS
        assert row.severity == Severity.ERROR
        assert row.ref_des == "R1"
        assert row.supplier == "mouser"

    def test_supplier_miss_description_contains_supplier_id(self) -> None:
        comp = _make_component()
        mock_svc = _mock_service(candidates=[])

        row = self._run(comp, supplier_service=mock_svc, supplier_id="lcsc")

        assert row is not None
        assert "lcsc" in row.description

    def test_silent_when_supplier_finds_component_no_inventory(self) -> None:
        """With no local inventory to compare, a found component is silent."""
        comp = _make_component()
        mock_svc = _mock_service(candidates=[_candidate()])

        row = self._run(comp, supplier_service=mock_svc, inventory_items=[])

        assert row is None

    def test_inventory_gap_when_found_in_supplier_but_not_local(self) -> None:
        comp = _make_component()
        mock_svc = _mock_service(candidates=[_candidate(pn="M-99999")])
        # Local inventory has a different component — no match for R1.
        local_item = _make_inventory_item(ipn="CAP-100N", category="CAP", value="100nF")

        row = self._run(comp, supplier_service=mock_svc, inventory_items=[local_item])

        assert row is not None
        assert row.check_type == CheckType.INVENTORY_GAP
        assert row.severity == Severity.INFO
        assert row.supplier_pn == "M-99999"

    def test_silent_when_found_in_supplier_and_in_local_by_ipn(self) -> None:
        """Component with matching IPN in local inventory produces no row."""
        comp = _make_component(props={"IPN": "R-10K-0603"})
        mock_svc = _mock_service(candidates=[_candidate()])
        local_item = _make_inventory_item(ipn="R-10K-0603")

        row = self._run(comp, supplier_service=mock_svc, inventory_items=[local_item])

        assert row is None

    def test_silent_when_found_in_supplier_and_in_local_by_mfgpn(self) -> None:
        comp = _make_component(props={"MFGPN": "RC0603FR-0710KL"})
        mock_svc = _mock_service(candidates=[_candidate()])
        local_item = _make_inventory_item(ipn="R-YAG-10K", mfgpn="RC0603FR-0710KL")

        row = self._run(comp, supplier_service=mock_svc, inventory_items=[local_item])

        assert row is None


# ---------------------------------------------------------------------------
# audit_project integration — supplier tier wired in correctly
# ---------------------------------------------------------------------------


class TestAuditProjectWithSupplier:
    """Integration-level: audit_project routes supplier rows to the report."""

    def _minimal_project(self, tmp_path: Path) -> Path:
        """Write a minimal schematic and return its .kicad_sch path."""
        sch = tmp_path / "proj.kicad_sch"
        sch.write_text(
            """(kicad_sch (version 20211123) (generator eeschema)
  (symbol (lib_id "Device:R") (at 50 50 0)
    (uuid "uuid-r1")
    (property "Reference" "R1" (id 0) (at 52 48 0))
    (property "Value" "10K" (id 1) (at 52 52 0))
    (property "Footprint" "Resistor_SMD:R_0603" (id 2) (at 52 54 0))
    (in_bom yes) (on_board yes)
  )
)
""",
            encoding="utf-8",
        )
        return sch  # pass the .kicad_sch file directly

    def test_no_supplier_service_produces_no_supplier_rows(
        self, tmp_path: Path
    ) -> None:
        proj = self._minimal_project(tmp_path)
        svc = AuditService()
        report = svc.audit_project([proj])

        supplier_rows = [
            r
            for r in report.rows
            if r.check_type in (CheckType.SUPPLIER_MISS, CheckType.INVENTORY_GAP)
        ]
        assert supplier_rows == []

    def test_supplier_service_miss_appears_in_report(self, tmp_path: Path) -> None:
        proj = self._minimal_project(tmp_path)
        mock_svc = _mock_service(candidates=[])

        svc = AuditService()
        report = svc.audit_project(
            [proj],
            supplier_service=mock_svc,
            supplier_id="mouser",
        )

        supplier_miss = [
            r for r in report.rows if r.check_type == CheckType.SUPPLIER_MISS
        ]
        assert len(supplier_miss) >= 1
        assert supplier_miss[0].severity == Severity.ERROR
        assert report.error_count >= 1

    def test_supplier_service_called_once_per_component(self, tmp_path: Path) -> None:
        proj = self._minimal_project(tmp_path)
        mock_svc = _mock_service(candidates=[_candidate()])

        svc = AuditService()
        svc.audit_project([proj], supplier_service=mock_svc, supplier_id="mouser")

        # One component in the schematic → one search call.
        assert mock_svc.search.call_count == 1
