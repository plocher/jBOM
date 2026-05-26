"""Unit tests for parts CLI field projection and merge namespace enrichment."""

from jbom.cli.parts import (
    _enrich_parts_with_merge_namespaces,
    _get_parts_field_value,
    _resolve_parts_output_projection,
)
from jbom.common.field_parser import parse_fields_argument
from jbom.services.component_merge_service import (
    ComponentMergeResult,
    MergedReferenceRecord,
)
from jbom.services.parts_list_generator import PartsListData, PartsListEntry


def test_parse_fields_argument_uses_parts_defaults() -> None:
    selected = parse_fields_argument(
        None,
        {"refs": "refs"},
        fabricator_id="generic",
        context="parts",
    )

    assert selected == [
        "refs",
        "value",
        "footprint",
        "package",
        "part_type",
        "tolerance",
        "voltage",
        "dielectric",
    ]


def test_resolve_parts_output_projection_uses_legacy_default_headers() -> None:
    fields, headers, widths = _resolve_parts_output_projection(None)

    assert fields == [
        "refs",
        "value",
        "footprint",
        "package",
        "part_type",
        "tolerance",
        "voltage",
        "dielectric",
    ]
    assert headers == [
        "Refs",
        "Value",
        "Footprint",
        "Package",
        "Type",
        "Tolerance",
        "Voltage",
        "Dielectric",
    ]
    assert widths == [20, 12, 20, 14, 10, 10, 8, 10]


def test_get_parts_field_value_reads_namespaced_attributes() -> None:
    entry = PartsListEntry(
        refs=["R1"],
        value="10k",
        footprint="R_0603",
        attributes={"sch:value": "9k99"},
    )

    assert _get_parts_field_value(entry, "refs") == "R1"
    assert _get_parts_field_value(entry, "sch:value") == "9k99"


def test_get_parts_field_value_reads_explicit_namespaced_fields() -> None:
    entry = PartsListEntry(
        refs=["R1"],
        value="10k",
        footprint="R_0603",
        attributes={
            "sch:footprint": "R_0603",
            "pcb:footprint": "R_0603",
            "inv:voltage": "25V",
        },
    )

    assert _get_parts_field_value(entry, "sch:footprint") == "R_0603"
    assert _get_parts_field_value(entry, "pcb:footprint") == "R_0603"
    assert _get_parts_field_value(entry, "inv:voltage") == "25V"


def test_unqualified_parts_value_prefers_s_then_i_then_p() -> None:
    entry = PartsListEntry(
        refs=["R1"],
        value="",
        footprint="R_0603",
        attributes={
            "sch:value": "10K",
            "inv:value": "10K-INV",
            "pcb:value": "9K99",
        },
    )

    assert _get_parts_field_value(entry, "value") == "10K"


def test_unqualified_parts_value_uses_inventory_when_schematic_missing() -> None:
    entry = PartsListEntry(
        refs=["R1"],
        value="",
        footprint="R_0603",
        attributes={
            "inv:value": "10K-INV",
            "pcb:value": "9K99",
        },
    )

    assert _get_parts_field_value(entry, "value") == "10K-INV"


def test_enrich_parts_with_merge_namespaces_adds_uniform_fields() -> None:
    parts_data = PartsListData(
        project_name="Project",
        entries=[
            PartsListEntry(
                refs=["R1", "R2"],
                value="10k",
                footprint="R_0603",
                attributes={},
            )
        ],
        metadata={},
    )
    merge_result = ComponentMergeResult(
        records={
            "R1": MergedReferenceRecord(
                reference="R1",
                source_fields={"sch:value": "10k", "pcb:value": "9k99"},
                annotated_fields={"ann:value": "sch:10k\npcb:9k99"},
            ),
            "R2": MergedReferenceRecord(
                reference="R2",
                source_fields={"sch:value": "10k", "pcb:value": "9k99"},
                annotated_fields={"ann:value": "sch:10k\npcb:9k99"},
            ),
        },
        mismatches=tuple(),
        metadata={},
    )

    enriched = _enrich_parts_with_merge_namespaces(parts_data, merge_result)

    attrs = enriched.entries[0].attributes
    assert attrs["sch:value"] == "10k"
    assert attrs["pcb:value"] == "9k99"
    assert attrs["ann:value"] == "sch: and pcb: differ\nsch:10k\npcb:9k99"
    assert enriched.metadata["merge_model_enabled"] is True
    assert enriched.metadata["merge_model_reference_count"] == 2
    assert enriched.metadata["merge_model_mismatch_count"] == 0


def test_enrich_parts_with_merge_namespaces_summarizes_divergent_annotations() -> None:
    parts_data = PartsListData(
        project_name="Project",
        entries=[
            PartsListEntry(
                refs=["R1", "R2", "R10"],
                value="10k",
                footprint="R_0603",
                attributes={},
            )
        ],
        metadata={},
    )
    merge_result = ComponentMergeResult(
        records={
            "R1": MergedReferenceRecord(
                reference="R1",
                source_fields={
                    "sch:footprint": "SCH:0603",
                    "pcb:footprint": "PCB:0402",
                },
                annotated_fields={"ann:footprint": "sch:SCH:0603\npcb:PCB:0402"},
            ),
            "R2": MergedReferenceRecord(
                reference="R2",
                source_fields={
                    "sch:footprint": "PCB:0603",
                    "pcb:footprint": "PCB:0603",
                },
            ),
            "R10": MergedReferenceRecord(
                reference="R10",
                source_fields={
                    "sch:footprint": "SCH:0603",
                    "pcb:footprint": "PCB:0402",
                },
                annotated_fields={"ann:footprint": "sch:SCH:0603\npcb:PCB:0402"},
            ),
        },
        mismatches=tuple(),
        metadata={},
    )

    enriched = _enrich_parts_with_merge_namespaces(parts_data, merge_result)
    assert (
        enriched.entries[0].attributes["ann:footprint"]
        == "R1,R10 -> sch: and pcb: differ\nsch:SCH:0603\npcb:PCB:0402 || "
        "R2 -> PCB:0603"
    )


def test_enrich_parts_with_merge_namespaces_skips_conflicting_grouped_values() -> None:
    parts_data = PartsListData(
        project_name="Project",
        entries=[
            PartsListEntry(
                refs=["R1", "R2"],
                value="10k",
                footprint="R_0603",
                attributes={},
            )
        ],
        metadata={},
    )
    merge_result = ComponentMergeResult(
        records={
            "R1": MergedReferenceRecord(
                reference="R1",
                source_fields={"sch:value": "9k99", "pcb:rotation": "0"},
            ),
            "R2": MergedReferenceRecord(
                reference="R2",
                source_fields={"sch:value": "9k99", "pcb:rotation": "90"},
            ),
        },
        mismatches=tuple(),
        metadata={"precedence_profile": "generic"},
    )

    enriched = _enrich_parts_with_merge_namespaces(parts_data, merge_result)
    attrs = enriched.entries[0].attributes
    assert attrs["sch:value"] == "9k99"
    assert "pcb:rotation" not in attrs
