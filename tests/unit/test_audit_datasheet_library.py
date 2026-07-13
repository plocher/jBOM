"""Unit tests for AuditService datasheet document-library hygiene checks (jBOM#357)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from jbom.common.types import InventoryItem
from jbom.services.audit_service import AuditService, CheckType
from jbom.services.datasheet_library import DATASHEET_NAME_COLUMN


def _make_item(
    *,
    ipn: str = "IPN1",
    category: str = "RES",
    manufacturer: str = "",
    datasheet: str = "",
    datasheet_name: str = "",
) -> InventoryItem:
    raw: dict[str, str] = {}
    if datasheet_name:
        raw[DATASHEET_NAME_COLUMN] = datasheet_name
    return InventoryItem(
        ipn=ipn,
        keywords="",
        category=category,
        description="",
        smd="",
        value="10K",
        type="",
        tolerance="",
        voltage="",
        amperage="",
        wattage="",
        manufacturer=manufacturer,
        datasheet=datasheet,
        row_type="ITEM",
        raw_data=raw,
    )


def _audit_catalog(items: list[InventoryItem], *, library_dir: Path | None = None):
    svc = AuditService()
    with patch("jbom.services.audit_service.InventoryReader") as MockReader:
        mock_reader = MagicMock()
        mock_reader.load.return_value = (items, [])
        MockReader.return_value = mock_reader
        return svc.audit_inventory(
            catalog_paths=[Path("catalog.csv")],
            library_dir=library_dir,
        )


class TestCleanCatalogIsSilent:
    def test_no_datasheet_rows_for_fully_curated_catalog(self, tmp_path: Path) -> None:
        datasheets = tmp_path / "datasheets"
        datasheets.mkdir()
        # Naming convention (jBOM#346) uses Title-Case tokens matching the
        # canonical manufacturer spelling, so this name's "Yageo" token
        # matches the Manufacturer column exactly and stays silent.
        (datasheets / "Resistor-ThickFilm-Yageo-RC0805-series.pdf").write_bytes(
            b"%PDF-1.4\n"
        )

        items = [
            _make_item(
                ipn="R1",
                manufacturer="Yageo",
                datasheet="https://example.com/rc0805.pdf",
                datasheet_name="Resistor-ThickFilm-Yageo-RC0805-series",
            ),
            _make_item(
                ipn="R2",
                manufacturer="Yageo",
                datasheet_name="Resistor-ThickFilm-Yageo-RC0805-series",  # sibling: no URL (provenance elsewhere)
            ),
        ]
        report = _audit_catalog(items, library_dir=tmp_path)
        datasheet_rows = [
            r for r in report.rows if r.check_type.startswith("DATASHEET_")
        ]
        assert datasheet_rows == []


class TestBacklog:
    def test_url_without_name_is_backlog(self) -> None:
        items = [_make_item(ipn="R1", datasheet="https://example.com/x.pdf")]
        report = _audit_catalog(items)
        backlog = [
            r for r in report.rows if r.check_type == CheckType.DATASHEET_BACKLOG
        ]
        assert len(backlog) == 1
        assert backlog[0].ipn == "R1"
        assert backlog[0].severity == "INFO"

    def test_no_backlog_when_url_and_name_present(self) -> None:
        items = [
            _make_item(
                ipn="R1", datasheet="https://example.com/x.pdf", datasheet_name="x"
            )
        ]
        report = _audit_catalog(items)
        backlog = [
            r for r in report.rows if r.check_type == CheckType.DATASHEET_BACKLOG
        ]
        assert backlog == []


class TestProvenance:
    def test_missing_provenance_when_no_row_has_url(self) -> None:
        items = [_make_item(ipn="R1", datasheet_name="shared-doc")]
        report = _audit_catalog(items)
        rows = [
            r
            for r in report.rows
            if r.check_type == CheckType.DATASHEET_PROVENANCE_MISSING
        ]
        assert len(rows) == 1
        assert rows[0].current_value == "shared-doc"

    def test_conflict_when_multiple_rows_carry_url(self) -> None:
        items = [
            _make_item(ipn="R1", datasheet="https://a", datasheet_name="shared-doc"),
            _make_item(ipn="R2", datasheet="https://b", datasheet_name="shared-doc"),
        ]
        report = _audit_catalog(items)
        rows = [
            r
            for r in report.rows
            if r.check_type == CheckType.DATASHEET_PROVENANCE_CONFLICT
        ]
        assert len(rows) == 1
        assert rows[0].severity == "ERROR"
        assert "R1" in rows[0].description and "R2" in rows[0].description

    def test_no_finding_when_exactly_one_row_carries_url(self) -> None:
        items = [
            _make_item(ipn="R1", datasheet="https://a", datasheet_name="shared-doc"),
            _make_item(ipn="R2", datasheet_name="shared-doc"),
        ]
        report = _audit_catalog(items)
        rows = [
            r
            for r in report.rows
            if r.check_type
            in (
                CheckType.DATASHEET_PROVENANCE_MISSING,
                CheckType.DATASHEET_PROVENANCE_CONFLICT,
            )
        ]
        assert rows == []


class TestNameCollisions:
    def test_case_mismatch_flagged(self) -> None:
        items = [
            _make_item(ipn="R1", datasheet="https://a", datasheet_name="Foo-Series"),
            _make_item(ipn="R2", datasheet_name="foo-series"),
        ]
        report = _audit_catalog(items)
        rows = [
            r
            for r in report.rows
            if r.check_type == CheckType.DATASHEET_NAME_CASE_MISMATCH
        ]
        assert len(rows) == 1
        assert rows[0].severity == "ERROR"

    def test_near_collision_flagged(self) -> None:
        items = [
            _make_item(
                ipn="R1",
                datasheet="https://a",
                datasheet_name="Resistor-ThickFilm-Uniroyal-0603WAJ",
            ),
            _make_item(
                ipn="R2",
                datasheet="https://b",
                datasheet_name="Resistor-ThickFilm-Univoyal-0603WAJ",
            ),
        ]
        report = _audit_catalog(items)
        rows = [
            r
            for r in report.rows
            if r.check_type == CheckType.DATASHEET_NAME_NEAR_COLLISION
        ]
        assert len(rows) == 1
        assert rows[0].severity == "WARN"

    def test_identical_names_not_flagged(self) -> None:
        items = [
            _make_item(ipn="R1", datasheet="https://a", datasheet_name="shared-doc"),
            _make_item(ipn="R2", datasheet_name="shared-doc"),
        ]
        report = _audit_catalog(items)
        rows = [
            r
            for r in report.rows
            if r.check_type
            in (
                CheckType.DATASHEET_NAME_CASE_MISMATCH,
                CheckType.DATASHEET_NAME_NEAR_COLLISION,
            )
        ]
        assert rows == []


class TestFilePresence:
    def test_missing_file_flagged_when_library_dir_given(self, tmp_path: Path) -> None:
        (tmp_path / "datasheets").mkdir()
        items = [
            _make_item(ipn="R1", datasheet="https://a", datasheet_name="missing-doc")
        ]
        report = _audit_catalog(items, library_dir=tmp_path)
        rows = [
            r for r in report.rows if r.check_type == CheckType.DATASHEET_FILE_MISSING
        ]
        assert len(rows) == 1
        assert rows[0].severity == "ERROR"
        assert "R1" in rows[0].description

    def test_no_file_checks_without_library_dir(self) -> None:
        items = [
            _make_item(ipn="R1", datasheet="https://a", datasheet_name="missing-doc")
        ]
        report = _audit_catalog(items, library_dir=None)
        rows = [
            r
            for r in report.rows
            if r.check_type
            in (CheckType.DATASHEET_FILE_MISSING, CheckType.DATASHEET_ORPHAN_FILE)
        ]
        assert rows == []

    def test_orphan_pdf_flagged(self, tmp_path: Path) -> None:
        datasheets = tmp_path / "datasheets"
        datasheets.mkdir()
        (datasheets / "orphan-doc.pdf").write_bytes(b"%PDF-1.4\n")
        items = [
            _make_item(ipn="R1", datasheet="https://a", datasheet_name="other-doc")
        ]
        # other-doc file also missing -> also produces DATASHEET_FILE_MISSING
        report = _audit_catalog(items, library_dir=tmp_path)
        orphan_rows = [
            r for r in report.rows if r.check_type == CheckType.DATASHEET_ORPHAN_FILE
        ]
        assert len(orphan_rows) == 1
        assert orphan_rows[0].current_value == "orphan-doc"
        assert orphan_rows[0].severity == "WARN"

    def test_case_insensitive_file_match(self, tmp_path: Path) -> None:
        datasheets = tmp_path / "datasheets"
        datasheets.mkdir()
        (datasheets / "Foo-Series.pdf").write_bytes(b"%PDF-1.4\n")
        items = [
            _make_item(ipn="R1", datasheet="https://a", datasheet_name="foo-series")
        ]
        report = _audit_catalog(items, library_dir=tmp_path)
        rows = [
            r
            for r in report.rows
            if r.check_type
            in (CheckType.DATASHEET_FILE_MISSING, CheckType.DATASHEET_ORPHAN_FILE)
        ]
        assert rows == []


class TestTokenNormalization:
    def test_manufacturer_spelling_drift_flagged(self) -> None:
        items = [
            _make_item(ipn="R1", manufacturer="Uniroyal"),
            _make_item(ipn="R2", manufacturer="Uniroyal"),
            _make_item(ipn="R3", manufacturer="UNI-ROYAL"),
        ]
        report = _audit_catalog(items)
        rows = [
            r for r in report.rows if r.check_type == CheckType.DATASHEET_TOKEN_MISMATCH
        ]
        assert len(rows) == 1
        assert rows[0].ipn == "R3"
        assert rows[0].current_value == "UNI-ROYAL"
        assert rows[0].suggested_value == "Uniroyal"

    def test_consistent_manufacturer_spelling_silent(self) -> None:
        items = [
            _make_item(ipn="R1", manufacturer="Yageo"),
            _make_item(ipn="R2", manufacturer="Yageo"),
        ]
        report = _audit_catalog(items)
        rows = [
            r for r in report.rows if r.check_type == CheckType.DATASHEET_TOKEN_MISMATCH
        ]
        assert rows == []

    def test_datasheet_name_token_drift_flagged(self) -> None:
        items = [
            _make_item(ipn="R1", manufacturer="Uniroyal"),
            _make_item(ipn="R2", manufacturer="Uniroyal"),
            _make_item(
                ipn="R3",
                datasheet="https://a",
                datasheet_name="Resistor-ThickFilm-UNIROYAL-0603WAJ-series",
            ),
        ]
        report = _audit_catalog(items)
        name_token_rows = [
            r
            for r in report.rows
            if r.check_type == CheckType.DATASHEET_TOKEN_MISMATCH
            and r.field == "Datasheet Name"
        ]
        assert len(name_token_rows) == 1
        assert name_token_rows[0].suggested_value == "Uniroyal"
