"""Unit tests for Issue #127 Scope C no-aggregate inventory output."""

from __future__ import annotations

from pathlib import Path

from jbom.cli.inventory import _generate_no_aggregate_inventory_rows
from jbom.common.types import Component


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
        ),
        Component(
            reference="C1",
            lib_id="Device:C",
            value="100nF",
            footprint="Capacitor_SMD:C_0603_1608Metric",
            uuid="uuid-c1",
            properties={},
        ),
        Component(
            reference="R1",
            lib_id="Device:R",
            value="10K",
            footprint="Resistor_SMD:R_0603_1608Metric",
            uuid="uuid-r1",
            properties={"Tolerance": "5%"},
        ),
    ]


def test_no_aggregate_schema_starts_with_project_uuid_category_ipn() -> None:
    rows, field_names = _generate_no_aggregate_inventory_rows(
        _sample_components(),
        project_directory=Path("/tmp/example-project"),
    )

    assert field_names[:4] == ["Project", "UUID", "Category", "IPN"]

    data_rows = [row for row in rows if row["Project"] != "Project"]
    assert len(data_rows) == 3
    assert {row["UUID"] for row in data_rows} == {"uuid-r1", "uuid-r2", "uuid-c1"}
    expected_project_path = str(Path("/tmp/example-project").resolve())
    assert all(row["Project"] == expected_project_path for row in data_rows)


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
    assert subheader["Project"] == "Project"
    assert subheader["UUID"] == "UUID"
    assert subheader["Category"] == "Category"
    assert subheader["IPN"] == "(Optional)\nIPN"
    assert subheader["Value"] == "Value"
    assert subheader["Package"] == "Package"

    for field_name in field_names:
        if field_name in {"Project", "UUID", "Category", "IPN", "Value", "Package"}:
            continue
        assert subheader[field_name] == ""
