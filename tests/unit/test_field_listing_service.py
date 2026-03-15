"""Unit tests for FieldListingService namespace matrix generation."""

from jbom.services.field_listing_service import (
    FieldListingService,
    FieldSourceRequirements,
    is_namespace_applicable,
)


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


def test_build_namespace_matrix_respects_source_requirements() -> None:
    service = FieldListingService()
    rows = service.build_namespace_matrix(
        ["s:value", "p:value", "i:value", "c:value", "a:value"],
        requirements=FieldSourceRequirements(
            require_sch=True,
            require_pcb=False,
            require_inv=False,
        ),
    )
    value_row = {row.name: row for row in rows}["value"]

    assert value_row.s_token == "s:value"
    assert value_row.p_token == ""
    assert value_row.i_token == ""
    assert value_row.c_token == "c:value"
    assert value_row.a_token == "a:value"


def test_is_namespace_applicable_matches_requirements_contract() -> None:
    requirements = FieldSourceRequirements(
        require_sch=False,
        require_pcb=True,
        require_inv=False,
    )

    assert is_namespace_applicable("s", requirements=requirements) is False
    assert is_namespace_applicable("p", requirements=requirements) is True
    assert is_namespace_applicable("i", requirements=requirements) is False
    assert is_namespace_applicable("c", requirements=requirements) is True
    assert is_namespace_applicable("a", requirements=requirements) is True
