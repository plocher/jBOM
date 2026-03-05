"""Unit tests for Issue #127 Scope C no-aggregate inventory output.

Updated for Issue #133: schema now includes ProjectName, SourceFile, Refs
as the 2nd, 4th, and 5th columns respectively.
"""

from __future__ import annotations

from pathlib import Path

from jbom.cli.inventory import _generate_no_aggregate_inventory_rows
from jbom.common.types import Component

_SOURCE_A = Path("/tmp/example-project/top.kicad_sch").resolve()
_SOURCE_B = Path("/tmp/example-project/sub.kicad_sch").resolve()


def _sample_components() -> list[Component]:
    """Build sample components spanning two categories with deterministic UUIDs."""

    return [
        Component(
            reference="R2",
            lib_id="Device:R",
            value="10K",
            footprint="Resistor_SMD:R_0603_1608Metric",
            uuid="uuid-r2",
            properties={"Tolerance": "5%"},
            source_file=_SOURCE_A,
        ),
        Component(
            reference="C1",
            lib_id="Device:C",
            value="100nF",
            footprint="Capacitor_SMD:C_0603_1608Metric",
            uuid="uuid-c1",
            properties={},
            source_file=_SOURCE_B,
        ),
        Component(
            reference="R1",
            lib_id="Device:R",
            value="10K",
            footprint="Resistor_SMD:R_0603_1608Metric",
            uuid="uuid-r1",
            properties={"Tolerance": "5%"},
            source_file=_SOURCE_A,
        ),
    ]


def test_no_aggregate_schema_starts_with_required_leading_columns() -> None:
    """Schema prefix is Project, ProjectName, UUID, SourceFile, Refs, Category, IPN."""
    rows, field_names = _generate_no_aggregate_inventory_rows(
        _sample_components(),
        project_directory=Path("/tmp/example-project"),
        project_name="example-project",
    )

    assert field_names[:7] == [
        "Project",
        "ProjectName",
        "UUID",
        "SourceFile",
        "Refs",
        "Category",
        "IPN",
    ]

    data_rows = [row for row in rows if row["Project"] != "Project"]
    assert len(data_rows) == 3
    assert {row["UUID"] for row in data_rows} == {"uuid-r1", "uuid-r2", "uuid-c1"}
    expected_project_path = str(Path("/tmp/example-project").resolve())
    assert all(row["Project"] == expected_project_path for row in data_rows)
    assert all(row["ProjectName"] == "example-project" for row in data_rows)


def test_no_aggregate_source_file_and_refs_populated() -> None:
    """SourceFile and Refs columns are populated from Component.source_file and .reference."""
    rows, _ = _generate_no_aggregate_inventory_rows(
        _sample_components(),
        project_directory=Path("/tmp/example-project"),
    )
    data_rows = {row["UUID"]: row for row in rows if row["Project"] != "Project"}

    assert data_rows["uuid-r1"]["SourceFile"] == str(_SOURCE_A)
    assert data_rows["uuid-r1"]["Refs"] == "R1"
    assert data_rows["uuid-c1"]["SourceFile"] == str(_SOURCE_B)
    assert data_rows["uuid-c1"]["Refs"] == "C1"


def test_no_aggregate_rows_are_grouped_by_category_with_subheaders() -> None:
    rows, _ = _generate_no_aggregate_inventory_rows(
        _sample_components(),
        project_directory=Path("/tmp/example-project"),
    )

    # Expect pattern: subheader, CAP data..., subheader, RES data...
    assert rows[0]["Project"] == "Project"
    assert rows[1]["Category"] == "CAP"

    # Find second subheader and verify it starts RES group.
    second_subheader_index = next(
        index
        for index, row in enumerate(rows[2:], start=2)
        if row["Project"] == "Project"
    )
    assert rows[second_subheader_index + 1]["Category"] == "RES"


def test_subheader_row_uses_minimal_deterministic_markers() -> None:
    rows, field_names = _generate_no_aggregate_inventory_rows(
        _sample_components(),
        project_directory=Path("/tmp/example-project"),
    )

    subheader = next(row for row in rows if row["Project"] == "Project")
    # Five required leading columns use the field name as sentinel (always populated)
    assert subheader["Project"] == "Project"
    assert subheader["ProjectName"] == "ProjectName"
    assert subheader["UUID"] == "UUID"
    assert subheader["SourceFile"] == "SourceFile"
    assert subheader["Refs"] == "Refs"
    assert subheader["Category"] == "Category"
    assert subheader["IPN"] == "(Optional)\nIPN"
    assert subheader["Value"] == "Value"
    assert subheader["Package"] == "Package"

    _required_populated = {
        "Project",
        "ProjectName",
        "UUID",
        "SourceFile",
        "Refs",
        "Category",
        "IPN",
        "Value",
        "Package",
    }
    for field_name in field_names:
        if field_name in _required_populated:
            continue
        assert subheader[field_name] == ""
