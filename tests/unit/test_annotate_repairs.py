"""Tests for the annotate --repairs workflow (Issue #154 PR 2).

These tests cover:
- Action=SET rows are applied to schematic symbols by UUID
- Non-SET action rows (SKIP / IGNORE / blank) are counted as skipped
- Blank ApprovedValue is silently skipped
- UUID not found in schematic is a hard failure (failed count, errors list)
- Malformed SET row (blank UUID or Field) is a hard failure
- dry_run=True reports changes without writing files
- Multiple SET rows in one repairs file
- Normalize (--normalize) behavior preserved in annotation_service
"""

from __future__ import annotations

import csv
from pathlib import Path

from jbom.services.annotation_service import (
    annotate_from_repairs,
    normalize_schematic_properties,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_schematic(path: Path, uuid: str = "uuid-r1", value: str = "10K") -> None:
    """Write a minimal schematic with one UUID-addressable symbol."""
    content = f"""(kicad_sch (version 20211123) (generator eeschema)
  (symbol (lib_id "Device:R") (at 50 50 0)
    (uuid "{uuid}")
    (property "Reference" "R1" (id 0) (at 52 48 0))
    (property "Value" "{value}" (id 1) (at 52 52 0))
    (property "Footprint" "Resistor_SMD:R_0603" (id 2) (at 52 54 0))
    (property "Manufacturer" "" (id 3) (at 52 56 0))
    (property "MFGPN" "" (id 4) (at 52 58 0))
  )
)
"""
    path.write_text(content, encoding="utf-8")


def _write_repairs(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    """Write an audit report.csv with the given rows."""
    fieldnames = [
        "CheckType",
        "Severity",
        "ProjectPath",
        "RefDes",
        "UUID",
        "CatalogFile",
        "IPN",
        "Category",
        "Field",
        "CurrentValue",
        "SuggestedValue",
        "ApprovedValue",
        "Action",
        "Supplier",
        "SupplierPN",
        "Description",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


# ---------------------------------------------------------------------------
# Core repairs behaviour
# ---------------------------------------------------------------------------


def test_repairs_set_row_applies_to_schematic(tmp_path: Path) -> None:
    sch = tmp_path / "proj.kicad_sch"
    _write_schematic(sch)
    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "uuid-r1",
                "RefDes": "R1",
                "Field": "Value",
                "ApprovedValue": "22K",
                "Action": "SET",
            }
        ],
    )

    result = annotate_from_repairs(repairs, [sch], dry_run=False)

    assert result.applied == 1
    assert result.failed == 0
    assert result.skipped == 0
    assert '"Value" "22K"' in sch.read_text(encoding="utf-8")


def test_repairs_multiple_set_rows_all_applied(tmp_path: Path) -> None:
    sch = tmp_path / "proj.kicad_sch"
    _write_schematic(sch)
    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "uuid-r1",
                "RefDes": "R1",
                "Field": "Value",
                "ApprovedValue": "33K",
                "Action": "SET",
            },
            {
                "UUID": "uuid-r1",
                "RefDes": "R1",
                "Field": "Manufacturer",
                "ApprovedValue": "Yageo",
                "Action": "SET",
            },
        ],
    )

    result = annotate_from_repairs(repairs, [sch], dry_run=False)

    assert result.applied == 2
    assert result.failed == 0
    updated = sch.read_text(encoding="utf-8")
    assert '"Value" "33K"' in updated
    assert '"Manufacturer" "Yageo"' in updated


def test_repairs_non_set_actions_are_skipped(tmp_path: Path) -> None:
    sch = tmp_path / "proj.kicad_sch"
    original = sch.read_text(encoding="utf-8") if sch.exists() else ""
    _write_schematic(sch)
    original = sch.read_text(encoding="utf-8")
    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "uuid-r1",
                "RefDes": "R1",
                "Field": "Value",
                "ApprovedValue": "99K",
                "Action": "SKIP",
            },
            {
                "UUID": "uuid-r1",
                "RefDes": "R1",
                "Field": "Value",
                "ApprovedValue": "99K",
                "Action": "IGNORE",
            },
            {
                "UUID": "uuid-r1",
                "RefDes": "R1",
                "Field": "Value",
                "ApprovedValue": "99K",
                "Action": "",
            },
        ],
    )

    result = annotate_from_repairs(repairs, [sch], dry_run=False)

    assert result.applied == 0
    assert result.skipped == 3
    assert result.failed == 0
    # Schematic should be unchanged.
    assert sch.read_text(encoding="utf-8") == original


def test_repairs_blank_approved_value_is_silently_skipped(tmp_path: Path) -> None:
    sch = tmp_path / "proj.kicad_sch"
    _write_schematic(sch)
    original = sch.read_text(encoding="utf-8")
    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "uuid-r1",
                "RefDes": "R1",
                "Field": "Manufacturer",
                "ApprovedValue": "",
                "Action": "SET",
            },
        ],
    )

    result = annotate_from_repairs(repairs, [sch], dry_run=False)

    assert result.applied == 0
    assert result.skipped == 1
    assert result.failed == 0
    assert sch.read_text(encoding="utf-8") == original


def test_repairs_missing_uuid_is_hard_failure(tmp_path: Path) -> None:
    sch = tmp_path / "proj.kicad_sch"
    _write_schematic(sch)
    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "uuid-does-not-exist",
                "RefDes": "R99",
                "Field": "Value",
                "ApprovedValue": "47K",
                "Action": "SET",
            },
        ],
    )

    result = annotate_from_repairs(repairs, [sch], dry_run=False)

    assert result.applied == 0
    assert result.failed == 1
    assert any("uuid-does-not-exist" in e for e in result.errors)


def test_repairs_malformed_set_row_blank_uuid_is_failure(tmp_path: Path) -> None:
    sch = tmp_path / "proj.kicad_sch"
    _write_schematic(sch)
    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "",
                "RefDes": "R1",
                "Field": "Value",
                "ApprovedValue": "100K",
                "Action": "SET",
            },
        ],
    )

    result = annotate_from_repairs(repairs, [sch], dry_run=False)

    assert result.failed == 1
    assert result.errors


def test_repairs_dry_run_does_not_write_file(tmp_path: Path) -> None:
    sch = tmp_path / "proj.kicad_sch"
    _write_schematic(sch)
    original = sch.read_text(encoding="utf-8")
    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "uuid-r1",
                "RefDes": "R1",
                "Field": "Value",
                "ApprovedValue": "1M",
                "Action": "SET",
            },
        ],
    )

    result = annotate_from_repairs(repairs, [sch], dry_run=True)

    assert result.dry_run is True
    assert result.applied == 1
    assert result.failed == 0
    # File must NOT have been modified.
    assert sch.read_text(encoding="utf-8") == original


def test_repairs_dry_run_records_changes(tmp_path: Path) -> None:
    sch = tmp_path / "proj.kicad_sch"
    _write_schematic(sch, value="10K")
    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "uuid-r1",
                "RefDes": "R1",
                "Field": "Value",
                "ApprovedValue": "470R",
                "Action": "SET",
            },
        ],
    )

    result = annotate_from_repairs(repairs, [sch], dry_run=True)

    assert len(result.changes) == 1
    change = result.changes[0]
    assert change.uuid == "uuid-r1"
    assert change.field == "Value"
    assert change.before == "10K"
    assert change.after == "470R"


def test_repairs_idempotent_when_value_already_set(tmp_path: Path) -> None:
    """A SET row that matches the current value is counted as applied (idempotent)."""
    sch = tmp_path / "proj.kicad_sch"
    _write_schematic(sch, value="10K")
    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "uuid-r1",
                "RefDes": "R1",
                "Field": "Value",
                "ApprovedValue": "10K",
                "Action": "SET",
            },
        ],
    )

    result = annotate_from_repairs(repairs, [sch], dry_run=False)

    assert result.applied == 1
    assert result.failed == 0
    # No changes recorded since value was already correct.
    assert len(result.changes) == 0


def test_repairs_failure_does_not_prevent_other_rows(tmp_path: Path) -> None:
    """A failing row does not abort processing of subsequent rows."""
    sch = tmp_path / "proj.kicad_sch"
    _write_schematic(sch)
    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "uuid-missing",
                "RefDes": "X1",
                "Field": "Value",
                "ApprovedValue": "bad",
                "Action": "SET",
            },
            {
                "UUID": "uuid-r1",
                "RefDes": "R1",
                "Field": "Value",
                "ApprovedValue": "560R",
                "Action": "SET",
            },
        ],
    )

    result = annotate_from_repairs(repairs, [sch], dry_run=False)

    assert result.failed == 1
    assert result.applied == 1
    assert '"Value" "560R"' in sch.read_text(encoding="utf-8")


def test_repairs_empty_repairs_file_returns_zero_counts(tmp_path: Path) -> None:
    sch = tmp_path / "proj.kicad_sch"
    _write_schematic(sch)
    repairs = tmp_path / "report.csv"
    _write_repairs(repairs, [])

    result = annotate_from_repairs(repairs, [sch], dry_run=False)

    assert result.applied == 0
    assert result.failed == 0
    assert result.skipped == 0


# ---------------------------------------------------------------------------
# Multi-project filtering
# ---------------------------------------------------------------------------


def test_repairs_rows_for_other_project_are_silently_skipped(tmp_path: Path) -> None:
    """ProjectPath rows not matching schematic's parent dir are skipped, not failed."""
    proj1 = tmp_path / "proj1"
    proj1.mkdir()
    proj2 = tmp_path / "proj2"
    proj2.mkdir()

    sch1 = proj1 / "proj1.kicad_sch"
    _write_schematic(sch1, uuid="uuid-p1")

    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "uuid-p1",
                "RefDes": "R1",
                "Field": "Value",
                "ApprovedValue": "47K",
                "Action": "SET",
                "ProjectPath": str(proj1),
            },
            {
                "UUID": "uuid-p2-does-not-exist",
                "RefDes": "C1",
                "Field": "Value",
                "ApprovedValue": "100nF",
                "Action": "SET",
                "ProjectPath": str(proj2),
            },
        ],
    )

    result = annotate_from_repairs(repairs, [sch1], dry_run=False)

    # proj1 row applied; proj2 row silently skipped (not a hard failure)
    assert result.applied == 1
    assert result.skipped == 1
    assert result.failed == 0
    assert '"Value" "47K"' in sch1.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# RefDes mismatch warning
# ---------------------------------------------------------------------------


def test_repairs_refdes_mismatch_emits_info_warning(tmp_path: Path) -> None:
    """UUID match with a changed RefDes generates an INFO warning but still applies."""
    sch = tmp_path / "proj.kicad_sch"
    _write_schematic(sch, uuid="uuid-r1")  # schematic has Reference=R1
    repairs = tmp_path / "report.csv"
    _write_repairs(
        repairs,
        [
            {
                "UUID": "uuid-r1",
                "RefDes": "R99",  # audit recorded R99, schematic now says R1
                "Field": "Value",
                "ApprovedValue": "22K",
                "Action": "SET",
            }
        ],
    )

    result = annotate_from_repairs(repairs, [sch], dry_run=False)

    # Change is still applied
    assert result.applied == 1
    assert result.failed == 0
    # Warning must mention the UUID and the mismatched RefDes values
    assert result.warnings
    assert any("uuid-r1" in w and "R99" in w and "R1" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# normalize_schematic_properties (kept in annotation_service — regression tests)
# ---------------------------------------------------------------------------


def test_normalize_renames_v_to_voltage(tmp_path: Path) -> None:
    sch = tmp_path / "proj.kicad_sch"
    content = """(kicad_sch (version 20211123) (generator eeschema)
  (symbol (lib_id "Device:C") (at 50 50 0)
    (uuid "uuid-c1")
    (property "Reference" "C1" (id 0) (at 52 48 0))
    (property "Value" "100nF" (id 1) (at 52 52 0))
    (property "V" "25V" (id 2) (at 52 54 0))
  )
)
"""
    sch.write_text(content, encoding="utf-8")

    result = normalize_schematic_properties([sch], dry_run=False)
    updated = sch.read_text(encoding="utf-8")

    assert result.conflicts == []
    assert '"Voltage" "25V"' in updated
    assert '"V" "25V"' not in updated


def test_normalize_conflict_aborts_and_does_not_write(tmp_path: Path) -> None:
    sch = tmp_path / "proj.kicad_sch"
    content = """(kicad_sch (version 20211123) (generator eeschema)
  (symbol (lib_id "Device:C") (at 50 50 0)
    (uuid "uuid-c1")
    (property "Reference" "C1" (id 0) (at 52 48 0))
    (property "Value" "100nF" (id 1) (at 52 52 0))
    (property "V" "25V" (id 2) (at 52 54 0))
    (property "Voltage" "50V" (id 3) (at 52 56 0))
  )
)
"""
    sch.write_text(content, encoding="utf-8")
    original = sch.read_text(encoding="utf-8")

    result = normalize_schematic_properties([sch], dry_run=False)

    assert result.conflicts
    assert sch.read_text(encoding="utf-8") == original
