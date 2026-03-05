"""Unit tests for Issue #127 annotation behavior in v7."""

from __future__ import annotations

import csv
from pathlib import Path

from jbom.services.annotation_service import annotate_schematic, triage_inventory


def _write_schematic(path: Path) -> str:
    """Write a minimal schematic with one UUID-addressable symbol."""

    content = """(kicad_sch (version 20211123) (generator eeschema)
  (symbol (lib_id "Device:R") (at 50 50 0)
    (uuid "uuid-r1")
    (property "Reference" "R1" (id 0) (at 52 48 0))
    (property "Value" "10K" (id 1) (at 52 52 0))
    (property "Footprint" "R_0603" (id 2) (at 52 54 0))
    (property "Package" "0603" (id 3) (at 52 56 0))
    (property "LCSC" "C1234" (id 4) (at 52 58 0))
  )
)
"""
    path.write_text(content, encoding="utf-8")
    return content


def _write_inventory(path: Path, rows: list[dict[str, str]]) -> None:
    """Write annotation inventory rows to CSV."""

    fieldnames = ["Project", "UUID", "Value", "Package", "Footprint", "LCSC"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_annotate_writes_explicit_values_for_matching_uuid(tmp_path: Path) -> None:
    schematic = tmp_path / "project.kicad_sch"
    _write_schematic(schematic)
    inventory = tmp_path / "fixit.csv"
    _write_inventory(
        inventory,
        [
            {
                "Project": str(tmp_path),
                "UUID": "uuid-r1",
                "Value": "11K",
                "Package": "0805",
                "Footprint": "R_0805",
                "LCSC": "C9999",
            }
        ],
    )

    result = annotate_schematic(schematic, inventory, dry_run=False)
    updated = schematic.read_text(encoding="utf-8")

    assert result.updated_components == 1
    assert '"Value" "11K"' in updated
    assert '"Package" "0805"' in updated
    assert '"Footprint" "R_0805"' in updated
    assert '"LCSC" "C9999"' in updated


def test_annotate_skips_blank_cells_and_keeps_existing_values(tmp_path: Path) -> None:
    schematic = tmp_path / "project.kicad_sch"
    original = _write_schematic(schematic)
    inventory = tmp_path / "fixit.csv"
    _write_inventory(
        inventory,
        [
            {
                "Project": str(tmp_path),
                "UUID": "uuid-r1",
                "Value": "",
                "Package": "",
                "Footprint": "",
                "LCSC": "",
            }
        ],
    )

    result = annotate_schematic(schematic, inventory, dry_run=False)
    assert result.updated_components == 0
    assert schematic.read_text(encoding="utf-8") == original


def test_annotate_writes_tilde_literal_to_schematic_properties(tmp_path: Path) -> None:
    schematic = tmp_path / "project.kicad_sch"
    _write_schematic(schematic)
    inventory = tmp_path / "fixit.csv"
    _write_inventory(
        inventory,
        [
            {
                "Project": str(tmp_path),
                "UUID": "uuid-r1",
                "Value": "",
                "Package": "~",
                "Footprint": "",
                "LCSC": "",
            }
        ],
    )

    result = annotate_schematic(schematic, inventory, dry_run=False)
    updated = schematic.read_text(encoding="utf-8")

    assert result.updated_components == 1
    assert '"Package" "~"' in updated


def test_annotate_skips_subheader_rows_where_project_equals_project(
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "project.kicad_sch"
    original = _write_schematic(schematic)
    inventory = tmp_path / "fixit.csv"
    _write_inventory(
        inventory,
        [
            {
                "Project": "Project",
                "UUID": "uuid-r1",
                "Value": "SHOULD_NOT_APPLY",
                "Package": "SHOULD_NOT_APPLY",
                "Footprint": "SHOULD_NOT_APPLY",
                "LCSC": "SHOULD_NOT_APPLY",
            }
        ],
    )

    result = annotate_schematic(schematic, inventory, dry_run=False)
    assert result.updated_components == 0
    assert schematic.read_text(encoding="utf-8") == original


def test_annotate_dry_run_reports_changes_without_writing_file(tmp_path: Path) -> None:
    schematic = tmp_path / "project.kicad_sch"
    original = _write_schematic(schematic)
    inventory = tmp_path / "fixit.csv"
    _write_inventory(
        inventory,
        [
            {
                "Project": str(tmp_path),
                "UUID": "uuid-r1",
                "Value": "22K",
                "Package": "1206",
                "Footprint": "R_1206",
                "LCSC": "C8888",
            }
        ],
    )

    result = annotate_schematic(schematic, inventory, dry_run=True)

    assert result.updated_components == 1
    assert result.dry_run is True
    assert len(result.changes) >= 1
    assert schematic.read_text(encoding="utf-8") == original


def test_triage_reports_only_required_blank_fields_value_and_package(
    tmp_path: Path,
) -> None:
    inventory = tmp_path / "fixit.csv"
    _write_inventory(
        inventory,
        [
            {
                "Project": "Project",
                "UUID": "UUID",
                "Value": "Value",
                "Package": "Package",
                "Footprint": "Footprint",
                "LCSC": "LCSC",
            },
            {
                "Project": str(tmp_path),
                "UUID": "uuid-r1",
                "Value": "",
                "Package": "0603",
                "Footprint": "R_0603",
                "LCSC": "",
            },
            {
                "Project": str(tmp_path),
                "UUID": "uuid-r2",
                "Value": "10K",
                "Package": "",
                "Footprint": "R_0603",
                "LCSC": "",
            },
            {
                "Project": str(tmp_path),
                "UUID": "uuid-r3",
                "Value": "10K",
                "Package": "0603",
                "Footprint": "R_0603",
                "LCSC": "",
            },
        ],
    )

    report = triage_inventory(inventory)
    assert report.total_data_rows == 3
    assert len(report.rows_with_required_blanks) == 2
    assert report.rows_with_required_blanks[0].missing_required_fields == ["Value"]
    assert report.rows_with_required_blanks[1].missing_required_fields == ["Package"]
