"""Unit tests for POS CLI projection and field resolution helpers."""
import io
from contextlib import redirect_stdout
from unittest.mock import patch

from jbom.cli.pos import (
    _apply_pos_dnp_filter,
    _build_pos_console_columns,
    _enrich_pos_with_merge_namespaces,
    _get_pos_field_value,
    _print_console_table,
    _resolve_pos_output_projection,
)
from jbom.services.component_merge_service import (
    ComponentMergeResult,
    MergedReferenceRecord,
)


def test_resolve_pos_output_projection_uses_jlc_defaults() -> None:
    selected_fields, headers, config = _resolve_pos_output_projection(
        selected_fields=None,
        fabricator="jlc",
        user_specified_fields=False,
    )

    assert config is not None
    assert selected_fields == ["reference", "x", "y", "side", "rotation", "package"]
    assert headers == ["Designator", "Mid X", "Mid Y", "Layer", "Rotation", "Package"]


def test_resolve_pos_output_projection_keeps_generic_user_headers() -> None:
    selected_fields, headers, config = _resolve_pos_output_projection(
        selected_fields=["reference", "x", "y", "side"],
        fabricator="generic",
        user_specified_fields=True,
    )

    assert config is not None
    assert selected_fields == ["reference", "x", "y", "side"]
    assert headers == ["Reference", "X", "Y", "Side"]


def test_fabricator_part_number_resolves_from_jlc_synonym_attribute() -> None:
    entry = {"jlcpcb_part_#": "C965799"}
    assert (
        _get_pos_field_value(
            entry,
            "fabricator_part_number",
            fabricator_id="jlc",
        )
        == "C965799"
    )


def test_fabricator_part_number_prefers_explicit_value() -> None:
    entry = {
        "fabricator_part_number": "JLC-OVERRIDE-777",
        "jlcpcb_part_#": "C965799",
    }
    assert (
        _get_pos_field_value(
            entry,
            "fabricator_part_number",
            fabricator_id="jlc",
        )
        == "JLC-OVERRIDE-777"
    )


def test_enrich_pos_with_merge_namespaces_adds_namespaced_fields() -> None:
    pos_rows = [{"reference": "R1", "x_mm": 1.0, "y_mm": 2.0, "rotation": 0.0}]
    merge_result = ComponentMergeResult(
        records={
            "R1": MergedReferenceRecord(
                reference="R1",
                source_fields={"s:value": "10k", "p:value": "9k99"},
                annotated_fields={"a:value": "s:10k\np:9k99"},
            )
        },
        mismatches=tuple(),
        metadata={},
    )

    enriched = _enrich_pos_with_merge_namespaces(pos_rows, merge_result)

    assert enriched[0]["s:value"] == "10k"
    assert enriched[0]["p:value"] == "9k99"
    assert enriched[0]["a:value"] == "s:10k\np:9k99"


def test_enrich_pos_with_merge_namespaces_keeps_rows_without_reference_match() -> None:
    pos_rows = [{"reference": "R1", "x_mm": 1.0, "y_mm": 2.0, "rotation": 0.0}]
    merge_result = ComponentMergeResult(
        records={
            "R2": MergedReferenceRecord(
                reference="R2",
                source_fields={"s:value": "1k"},
            )
        },
        mismatches=tuple(),
        metadata={},
    )

    enriched = _enrich_pos_with_merge_namespaces(pos_rows, merge_result)

    assert "s:value" not in enriched[0]


def test_get_pos_field_value_reads_explicit_namespaced_fields() -> None:
    entry = {
        "s:value": "10k",
        "p:footprint": "R_0603",
    }

    assert _get_pos_field_value(entry, "s:value") == "10k"
    assert _get_pos_field_value(entry, "p:footprint") == "R_0603"


def test_unqualified_pos_value_prefers_p_then_i_then_s() -> None:
    entry = {
        "value": "",
        "s:value": "10K",
        "p:value": "9K99",
        "i:value": "10K-INV",
    }

    assert _get_pos_field_value(entry, "value") == "9K99"


def test_unqualified_pos_value_uses_inventory_when_pcb_missing() -> None:
    entry = {
        "value": "",
        "s:value": "10K",
        "i:value": "10K-INV",
    }

    assert _get_pos_field_value(entry, "value") == "10K-INV"


def test_pos_dnp_filter_excludes_schematic_dnp_rows_by_default() -> None:
    rows = [
        {"reference": "U1", "s:dnp": "Yes"},
        {"reference": "U2", "s:dnp": "No"},
    ]
    filtered = _apply_pos_dnp_filter(rows, component_filters={"exclude_dnp": True})
    assert [row["reference"] for row in filtered] == ["U2"]


def test_pos_dnp_filter_respects_include_dnp_flag() -> None:
    rows = [{"reference": "U1", "s:dnp": "Yes"}]
    filtered = _apply_pos_dnp_filter(rows, component_filters={"exclude_dnp": False})
    assert [row["reference"] for row in filtered] == ["U1"]


def test_build_pos_console_columns_uses_data_aware_widths() -> None:
    rows = [
        {
            "Designator": "J1",
            "Package": "Connector_Generic:Conn_01x03",
        }
    ]
    columns = _build_pos_console_columns(
        selected_fields=["reference", "package"],
        headers=["Designator", "Package"],
        rows=rows,
    )

    package_column = next(column for column in columns if column.key == "Package")
    assert package_column.preferred_width == len("Connector_Generic:Conn_01x03") + 1


def test_build_pos_console_columns_does_not_pad_non_final_columns() -> None:
    rows = [
        {
            "Designator": "J1",
            "Package": "Connector_Generic:Conn_01x03",
        }
    ]
    columns = _build_pos_console_columns(
        selected_fields=["package", "reference"],
        headers=["Package", "Designator"],
        rows=rows,
    )

    package_column = next(column for column in columns if column.key == "Package")
    assert package_column.preferred_width == len("Connector_Generic:Conn_01x03")


def test_pos_console_table_respects_terminal_width_shrinking() -> None:
    pos_data = [
        {
            "reference": "J1",
            "x_mm": 123.4567,
            "y_mm": 89.0123,
            "rotation": 90.0,
            "side": "TOP",
            "package": "Connector_Generic:Conn_01x03",
        }
    ]
    selected_fields = ["reference", "x", "y", "side", "rotation", "package"]
    headers = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation", "Package"]

    output = io.StringIO()
    with patch("jbom.cli.pos.get_terminal_width", return_value=70):
        with redirect_stdout(output):
            _print_console_table(
                pos_data,
                selected_fields,
                headers,
                fabricator_id="generic",
                fabricator_config=None,
            )

    lines_with_columns = [
        line for line in output.getvalue().splitlines() if " | " in line
    ]
    assert lines_with_columns
    assert all(len(line) <= 70 for line in lines_with_columns)


def test_pos_console_table_adds_trailing_padding_to_last_column() -> None:
    pos_data = [
        {
            "reference": "J1",
            "package": "Connector_Generic:Conn_01x03",
        }
    ]
    selected_fields = ["reference", "package"]
    headers = ["Designator", "Package"]

    output = io.StringIO()
    with patch("jbom.cli.pos.get_terminal_width", return_value=200):
        with redirect_stdout(output):
            _print_console_table(
                pos_data,
                selected_fields,
                headers,
                fabricator_id="generic",
                fabricator_config=None,
            )

    data_line = next(
        line
        for line in output.getvalue().splitlines()
        if "Connector_Generic:Conn_01x03" in line
    )
    assert data_line.endswith(" ")
