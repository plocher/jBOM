"""Unit tests for BOM CLI field resolution helpers."""

from jbom.cli.bom import (
    _enforce_bom_device_footprints,
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


def test_fabricator_part_number_resolves_from_jlc_synonym_alias() -> None:
    entry = _make_entry({"jlcpcb_part_#": "C965799"})
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
    entry = _make_entry({"i:package": "0603-LED"})
    assert _get_field_value(entry, "i:package", fabricator_id="jlc") == "0603-LED"


def test_inventory_package_field_is_strict_namespace_only() -> None:
    entry = _make_entry({"package": "0603-LED"})
    assert _get_field_value(entry, "i:package", fabricator_id="jlc") == ""


def test_inventory_package_field_is_blank_without_overlay_projection() -> None:
    entry = _make_entry({}, footprint="SignalMast-ColorLight-SingleHead:0603-LED")
    assert _get_field_value(entry, "i:package", fabricator_id="jlc") == ""


def test_s_namespace_field_is_strict_source_namespace() -> None:
    entry = _make_entry({"description": "Pull-up resistor", "s:value": "9k99"})
    assert _get_field_value(entry, "s:value", fabricator_id="jlc") == "9k99"
    assert _get_field_value(entry, "s:description", fabricator_id="jlc") == ""


def test_p_namespace_field_returns_explicit_value_only() -> None:
    explicit_entry = _make_entry({"p:footprint": "PCB:0603"})
    assert (
        _get_field_value(explicit_entry, "p:footprint", fabricator_id="jlc")
        == "PCB:0603"
    )

    fallback_entry = _make_entry({})
    assert _get_field_value(fallback_entry, "p:footprint", fabricator_id="jlc") == ""


def test_unqualified_value_prefers_p_then_i_then_s_sources() -> None:
    entry = _make_entry(
        {
            "s:value": "10K",
            "p:value": "9K99",
            "i:value": "10K-INV",
        }
    )

    assert _get_field_value(entry, "value", fabricator_id="jlc") == "9K99"


def test_unqualified_value_uses_inventory_when_pcb_value_missing() -> None:
    entry = _make_entry(
        {
            "s:value": "10K",
            "i:value": "10K-INV",
        }
    )

    assert _get_field_value(entry, "value", fabricator_id="jlc") == "10K-INV"


def test_a_namespace_field_renders_source_annotation_lines_on_mismatch() -> None:
    entry = _make_entry(
        {"s:footprint": "SCH:0603", "p:footprint": "PCB:0402"},
        footprint="SCH:0603",
    )
    assert (
        _get_field_value(entry, "a:footprint", fabricator_id="jlc")
        == "s:SCH:0603\np:PCB:0402"
    )


def test_a_namespace_field_prefers_explicit_annotation_value() -> None:
    entry = _make_entry({"a:value": "s:10k\np:9k99"})
    assert _get_field_value(entry, "a:value", fabricator_id="jlc") == "s:10k\np:9k99"


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
                    "s:footprint": "SCH:0603",
                    "p:footprint": "PCB:0603",
                },
                annotated_fields={"a:footprint": "s:SCH:0603\np:PCB:0603"},
            ),
            "R2": MergedReferenceRecord(
                reference="R2",
                source_fields={
                    "s:footprint": "SCH:0603",
                    "p:footprint": "PCB:0603",
                },
                annotated_fields={"a:footprint": "s:SCH:0603\np:PCB:0603"},
            ),
        },
        mismatches=tuple(),
        metadata={},
    )

    enriched = _enrich_bom_with_merge_namespaces(bom_data, merge_result)

    attrs = enriched.entries[0].attributes
    assert attrs["s:footprint"] == "SCH:0603"
    assert attrs["p:footprint"] == "PCB:0603"
    assert attrs["a:footprint"] == "S: and P: differ\ns:SCH:0603\np:PCB:0603"
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
                    "s:footprint": "SCH:0603",
                    "p:footprint": "PCB:0402",
                },
                annotated_fields={"a:footprint": "s:SCH:0603\np:PCB:0402"},
            ),
            "R2": MergedReferenceRecord(
                reference="R2",
                source_fields={
                    "s:footprint": "PCB:0603",
                    "p:footprint": "PCB:0603",
                },
            ),
            "R10": MergedReferenceRecord(
                reference="R10",
                source_fields={
                    "s:footprint": "SCH:0603",
                    "p:footprint": "PCB:0402",
                },
                annotated_fields={"a:footprint": "s:SCH:0603\np:PCB:0402"},
            ),
        },
        mismatches=tuple(),
        metadata={"precedence_profile": "generic"},
    )

    enriched = _enrich_bom_with_merge_namespaces(bom_data, merge_result)

    assert (
        enriched.entries[0].attributes["a:footprint"]
        == "R1,R10 -> S: and P: differ\ns:SCH:0603\np:PCB:0402 || "
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
                source_fields={"s:value": "10k", "p:rotation": "0"},
            ),
            "R2": MergedReferenceRecord(
                reference="R2",
                source_fields={"s:value": "10k", "p:rotation": "90"},
            ),
        },
        mismatches=tuple(),
        metadata={"precedence_profile": "generic"},
    )

    enriched = _enrich_bom_with_merge_namespaces(bom_data, merge_result)

    attrs = enriched.entries[0].attributes
    assert attrs["s:value"] == "10k"
    assert "p:rotation" not in attrs


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


def test_bom_device_footprint_contract_prefers_pcb_footprint() -> None:
    bom_data = BOMData(
        project_name="Project",
        entries=[
            BOMEntry(
                references=["J1"],
                value="Conn_01x04",
                footprint="Connector:Conn_01x04",
                quantity=1,
                attributes={
                    "p:footprint": (
                        "Connector_PinHeader_2.54mm:" "PinHeader_1x04_P2.54mm_Vertical"
                    )
                },
            )
        ],
        metadata={},
    )

    enforced = _enforce_bom_device_footprints(bom_data)
    assert (
        enforced.entries[0].footprint
        == "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"
    )
    assert enforced.metadata["device_footprint_contract"] == "enforced"


def test_bom_device_footprint_contract_falls_back_to_concrete_schematic_footprint() -> (
    None
):
    bom_data = BOMData(
        project_name="Project",
        entries=[
            BOMEntry(
                references=["J2"],
                value="Conn_01x03",
                footprint="",
                quantity=1,
                attributes={
                    "s:footprint": (
                        "Connector_Phoenix_MC:PhoenixContact_MC_1,5_3-G-3.5_1x03_P3.50mm_Horizontal"
                    ),
                },
            )
        ],
        metadata={},
    )

    enforced = _enforce_bom_device_footprints(bom_data)
    assert (
        enforced.entries[0].footprint
        == "Connector_Phoenix_MC:PhoenixContact_MC_1,5_3-G-3.5_1x03_P3.50mm_Horizontal"
    )


def test_bom_device_footprint_contract_rejects_non_concrete_pcb_footprint() -> None:
    bom_data = BOMData(
        project_name="Project",
        entries=[
            BOMEntry(
                references=["J2"],
                value="Conn_01x03",
                footprint="",
                quantity=1,
                attributes={
                    "p:footprint": "~",
                    "s:footprint": (
                        "Connector_Phoenix_MC:PhoenixContact_MC_1,5_3-G-3.5_1x03_P3.50mm_Horizontal"
                    ),
                },
            )
        ],
        metadata={},
    )

    try:
        _enforce_bom_device_footprints(bom_data)
        assert False, "Expected ValueError for non-concrete explicit p:footprint"
    except ValueError as exc:
        assert "missing/unresolved footprint" in str(exc)
        assert "J2" in str(exc)


def test_bom_device_footprint_contract_raises_when_missing_footprint() -> None:
    bom_data = BOMData(
        project_name="Project",
        entries=[
            BOMEntry(
                references=["U1"],
                value="LM358",
                footprint="",
                quantity=1,
                attributes={},
            )
        ],
        metadata={},
    )

    try:
        _enforce_bom_device_footprints(bom_data)
        assert False, "Expected ValueError for missing footprint"
    except ValueError as exc:
        assert "requires concrete component footprints" in str(exc)
        assert "U1" in str(exc)


def test_bom_device_footprint_contract_rejects_wildcard_footprint() -> None:
    bom_data = BOMData(
        project_name="Project",
        entries=[
            BOMEntry(
                references=["J6"],
                value="Conn_6P6C",
                footprint="RJ12*",
                quantity=1,
                attributes={},
            )
        ],
        metadata={},
    )

    try:
        _enforce_bom_device_footprints(bom_data)
        assert False, "Expected ValueError for wildcard footprint"
    except ValueError as exc:
        assert "missing/unresolved footprint" in str(exc)
        assert "J6" in str(exc)
