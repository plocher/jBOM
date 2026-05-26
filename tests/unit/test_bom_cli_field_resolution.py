"""Unit tests for BOM CLI field resolution helpers."""

from jbom.cli.bom import (
    _enrich_bom_with_merge_namespaces,
    _entry_smd_from_reference_lookup,
    _filter_inventory_dnp_entries,
    _get_field_value,
)
from jbom.services.bom_generator import BOMData, BOMEntry
from jbom.services.component_merge_service import (
    ComponentMergeResult,
    MergedReferenceRecord,
)


def _make_entry(
    attributes: dict[str, object],
    *,
    footprint: str = "Resistor_SMD:R_0603_1608Metric",
) -> BOMEntry:
    """Create a minimal BOM entry for field resolution tests."""
    return BOMEntry(
        references=["R1"],
        value="10k",
        footprint=footprint,
        quantity=1,
        attributes=attributes,
    )


def test_fabricator_part_number_resolves_from_jlc_lcsc_attribute() -> None:
    entry = _make_entry({"lcsc": "C25585"})
    assert (
        _get_field_value(entry, "fabricator_part_number", fabricator_id="jlc")
        == "C25585"
    )


def test_fabricator_part_number_resolves_from_jlc_lcsc_attribute_v2() -> None:
    entry = _make_entry({"lcsc": "C965799"})
    assert (
        _get_field_value(entry, "fabricator_part_number", fabricator_id="jlc")
        == "C965799"
    )


def test_fabricator_part_number_prefers_explicit_value() -> None:
    entry = _make_entry(
        {
            "fabricator_part_number": "JLC-OVERRIDE-123",
            "lcsc": "C25585",
            "jlcpcb_part_#": "C965799",
        }
    )
    assert (
        _get_field_value(entry, "fabricator_part_number", fabricator_id="jlc")
        == "JLC-OVERRIDE-123"
    )


def test_smd_field_uses_footprint_inference_when_attribute_missing() -> None:
    entry = _make_entry({})
    assert _get_field_value(entry, "smd", fabricator_id="jlc") == "Yes"


def test_smd_field_honors_explicit_false_attribute() -> None:
    entry = _make_entry({"smd": False})
    assert _get_field_value(entry, "smd", fabricator_id="jlc") == "No"


def test_entry_smd_lookup_returns_none_without_known_references() -> None:
    entry = _make_entry({})
    assert _entry_smd_from_reference_lookup(entry, {}) is None


def test_entry_smd_lookup_requires_all_known_references_smd() -> None:
    entry = BOMEntry(
        references=["R1", "R2"],
        value="10k",
        footprint="Resistor_SMD:R_0603_1608Metric",
        quantity=2,
        attributes={},
    )
    assert _entry_smd_from_reference_lookup(entry, {"R1": True, "R2": True}) is True
    assert _entry_smd_from_reference_lookup(entry, {"R1": True, "R2": False}) is False


def test_inventory_package_field_uses_namespaced_value_when_present() -> None:
    entry = _make_entry({"inv:package": "0603-LED"})
    assert _get_field_value(entry, "inv:package", fabricator_id="jlc") == "0603-LED"


def test_inventory_package_field_is_strict_namespace_only() -> None:
    entry = _make_entry({"package": "0603-LED"})
    assert _get_field_value(entry, "inv:package", fabricator_id="jlc") == ""


def test_inventory_package_field_is_blank_without_overlay_projection() -> None:
    entry = _make_entry({}, footprint="SignalMast-ColorLight-SingleHead:0603-LED")
    assert _get_field_value(entry, "inv:package", fabricator_id="jlc") == ""


def test_sch_namespace_field_is_strict_source_namespace() -> None:
    entry = _make_entry({"description": "Pull-up resistor", "sch:value": "9k99"})
    assert _get_field_value(entry, "sch:value", fabricator_id="jlc") == "9k99"
    assert _get_field_value(entry, "sch:description", fabricator_id="jlc") == ""


def test_pcb_namespace_field_returns_explicit_value_only() -> None:
    explicit_entry = _make_entry({"pcb:footprint": "PCB:0603"})
    assert (
        _get_field_value(explicit_entry, "pcb:footprint", fabricator_id="jlc")
        == "PCB:0603"
    )

    fallback_entry = _make_entry({})
    assert _get_field_value(fallback_entry, "pcb:footprint", fabricator_id="jlc") == ""


def test_unqualified_value_prefers_p_then_i_then_s_sources() -> None:
    entry = _make_entry(
        {
            "sch:value": "10K",
            "pcb:value": "9K99",
            "inv:value": "10K-INV",
        }
    )

    assert _get_field_value(entry, "value", fabricator_id="jlc") == "9K99"


def test_unqualified_value_uses_inventory_when_pcb_value_missing() -> None:
    entry = _make_entry(
        {
            "sch:value": "10K",
            "inv:value": "10K-INV",
        }
    )

    assert _get_field_value(entry, "value", fabricator_id="jlc") == "10K-INV"


def test_ann_namespace_field_renders_source_annotation_lines_on_mismatch() -> None:
    entry = _make_entry(
        {"sch:footprint": "SCH:0603", "pcb:footprint": "PCB:0402"},
        footprint="SCH:0603",
    )
    assert (
        _get_field_value(entry, "ann:footprint", fabricator_id="jlc")
        == "sch:SCH:0603\npcb:PCB:0402"
    )


def test_ann_namespace_field_prefers_explicit_annotation_value() -> None:
    entry = _make_entry({"ann:value": "sch:10k\npcb:9k99"})
    assert (
        _get_field_value(entry, "ann:value", fabricator_id="jlc") == "sch:10k\npcb:9k99"
    )


def test_merge_namespace_enrichment_adds_uniform_values_to_grouped_entry() -> None:
    bom_data = BOMData(
        project_name="Project",
        entries=[
            BOMEntry(
                references=["R1", "R2"],
                value="10k",
                footprint="SCH:0603",
                quantity=2,
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
                    "pcb:footprint": "PCB:0603",
                },
                annotated_fields={"ann:footprint": "sch:SCH:0603\npcb:PCB:0603"},
            ),
            "R2": MergedReferenceRecord(
                reference="R2",
                source_fields={
                    "sch:footprint": "SCH:0603",
                    "pcb:footprint": "PCB:0603",
                },
                annotated_fields={"ann:footprint": "sch:SCH:0603\npcb:PCB:0603"},
            ),
        },
        mismatches=tuple(),
        metadata={},
    )

    enriched = _enrich_bom_with_merge_namespaces(bom_data, merge_result)

    attrs = enriched.entries[0].attributes
    assert attrs["sch:footprint"] == "SCH:0603"
    assert attrs["pcb:footprint"] == "PCB:0603"
    assert attrs["ann:footprint"] == "sch: and pcb: differ\nsch:SCH:0603\npcb:PCB:0603"
    assert enriched.metadata["merge_model_enabled"] is True
    assert enriched.metadata["merge_model_reference_count"] == 2
    assert enriched.metadata["merge_model_mismatch_count"] == 0


def test_merge_namespace_enrichment_summarizes_divergent_grouped_annotations() -> None:
    bom_data = BOMData(
        project_name="Project",
        entries=[
            BOMEntry(
                references=["R1", "R2", "R10"],
                value="10k",
                footprint="SCH:0603",
                quantity=3,
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
        metadata={"precedence_profile": "generic"},
    )

    enriched = _enrich_bom_with_merge_namespaces(bom_data, merge_result)

    assert (
        enriched.entries[0].attributes["ann:footprint"]
        == "R1,R10 -> sch: and pcb: differ\nsch:SCH:0603\npcb:PCB:0402 || "
        "R2 -> PCB:0603"
    )


def test_merge_namespace_enrichment_skips_conflicting_grouped_values() -> None:
    bom_data = BOMData(
        project_name="Project",
        entries=[
            BOMEntry(
                references=["R1", "R2"],
                value="10k",
                footprint="SCH:0603",
                quantity=2,
                attributes={},
            )
        ],
        metadata={},
    )
    merge_result = ComponentMergeResult(
        records={
            "R1": MergedReferenceRecord(
                reference="R1",
                source_fields={"sch:value": "10k", "pcb:rotation": "0"},
            ),
            "R2": MergedReferenceRecord(
                reference="R2",
                source_fields={"sch:value": "10k", "pcb:rotation": "90"},
            ),
        },
        mismatches=tuple(),
        metadata={"precedence_profile": "generic"},
    )

    enriched = _enrich_bom_with_merge_namespaces(bom_data, merge_result)

    attrs = enriched.entries[0].attributes
    assert attrs["sch:value"] == "10k"
    assert "pcb:rotation" not in attrs


def test_inventory_dnp_filter_excludes_rows_by_default() -> None:
    bom_data = BOMData(
        project_name="Project",
        entries=[
            BOMEntry(
                references=["U1"],
                value="MAX3485",
                footprint="Package_DIP:DIP-8",
                quantity=1,
                attributes={"inventory_dnp": True},
            ),
            BOMEntry(
                references=["U2"],
                value="NE555",
                footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                quantity=1,
                attributes={"inventory_dnp": False},
            ),
        ],
        metadata={},
    )

    filtered = _filter_inventory_dnp_entries(
        bom_data,
        include_inventory_dnp=False,
    )

    assert len(filtered.entries) == 1
    assert filtered.entries[0].references == ["U2"]
    assert filtered.metadata["inventory_dnp_filtered_entries"] == 1


def test_inventory_dnp_filter_respects_include_flag() -> None:
    bom_data = BOMData(
        project_name="Project",
        entries=[
            BOMEntry(
                references=["U1"],
                value="MAX3485",
                footprint="Package_DIP:DIP-8",
                quantity=1,
                attributes={"inventory_dnp": True},
            )
        ],
        metadata={},
    )

    filtered = _filter_inventory_dnp_entries(
        bom_data,
        include_inventory_dnp=True,
    )

    assert len(filtered.entries) == 1
    assert filtered.metadata == bom_data.metadata
