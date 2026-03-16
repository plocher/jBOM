"""Unit tests for POS CLI projection and field resolution helpers."""

from jbom.cli.pos import (
    _enrich_pos_with_merge_namespaces,
    _get_pos_field_value,
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


def test_get_pos_field_value_respects_source_requirements() -> None:
    entry = {
        "s:value": "10k",
        "p:footprint": "R_0603",
    }

    assert _get_pos_field_value(entry, "s:value") == ""
    assert _get_pos_field_value(entry, "p:footprint") == "R_0603"
