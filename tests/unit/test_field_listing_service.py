"""Unit tests for FieldListingService namespace matrix generation."""

from jbom.services.field_listing_service import FieldListingService


def test_build_namespace_matrix_groups_tokens_by_canonical_name() -> None:
    service = FieldListingService()

    rows = service.build_namespace_matrix(
        [
            "value",
            "s:value",
            "p:value",
            "c:value",
            "reference",
            "i:voltage",
        ]
    )
    as_dict = {row.name: row for row in rows}

    assert as_dict["value"].name == "value"
    assert as_dict["value"].s_token == "s:value"
    assert as_dict["value"].p_token == "p:value"
    assert as_dict["value"].c_token == "c:value"
    assert as_dict["value"].i_token == ""
    assert as_dict["reference"].name == "reference"
    assert as_dict["voltage"].i_token == "i:voltage"


def test_build_namespace_matrix_normalizes_tokens_and_deduplicates() -> None:
    service = FieldListingService()

    rows = service.build_namespace_matrix(
        [
            " Value ",
            "S:Value",
            "s:value",
            "P:Foot Print",
        ]
    )
    as_dict = {row.name: row for row in rows}

    assert as_dict["value"].name == "value"
    assert as_dict["value"].s_token == "s:value"
    assert as_dict["foot_print"].p_token == "p:foot_print"


def test_matrix_row_to_console_row_exposes_fixed_columns() -> None:
    row = FieldListingService().build_namespace_matrix(["value", "s:value"])[0]
    console = row.to_console_row()

    assert set(console.keys()) == {"Name", "s:", "p:", "i:", "c:", "a:"}
    assert console["Name"] == "value"
    assert console["s:"] == "s:value"
