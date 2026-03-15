"""Unit tests for Phase-1 ComponentMergeService scaffolding."""

from __future__ import annotations

from jbom.common.pcb_types import PcbComponent
from jbom.common.types import Component
from jbom.services.component_merge_service import ComponentMergeService
from jbom.services.project_component_collector import (
    ProjectComponentCollector,
    ProjectComponentGraph,
)


def _make_component(
    reference: str, *, value: str = "10k", footprint: str = "SCH:0603"
) -> Component:
    """Create a minimal schematic component fixture."""

    return Component(
        reference=reference,
        lib_id="Device:R",
        value=value,
        footprint=footprint,
        properties={},
    )


def _make_pcb_component(
    reference: str,
    *,
    footprint_name: str = "PCB:0402",
    package_token: str = "0402",
) -> PcbComponent:
    """Create a minimal PCB component fixture."""

    return PcbComponent(
        reference=reference,
        footprint_name=footprint_name,
        package_token=package_token,
        center_x_mm=0.0,
        center_y_mm=0.0,
        rotation_deg=0.0,
        side="TOP",
    )


def _make_graph_with_footprint_mismatch() -> ProjectComponentGraph:
    """Build a minimal graph fixture with one footprint mismatch."""

    collector = ProjectComponentCollector()
    return collector.collect(
        schematic_components=[_make_component("R1", footprint="SCH:0603")],
        pcb_components=[_make_pcb_component("R1", footprint_name="PCB:0402")],
    )


def test_merge_service_loads_precedence_policy_from_defaults() -> None:
    service = ComponentMergeService()
    policy = service.precedence_policy

    assert policy.profile_name == "generic"
    assert "value" in policy.schematic_biased_fields
    assert "footprint" in policy.pcb_biased_fields
    assert "lcsc" in policy.inventory_biased_fields


def test_merge_creates_namespaced_records_and_mismatch_annotations() -> None:
    service = ComponentMergeService()
    graph = _make_graph_with_footprint_mismatch()

    result = service.merge(graph)

    assert result.reference_count == 1
    assert len(result.mismatches) == 1
    mismatch = result.mismatches[0]
    assert mismatch.field_key == "footprint"
    assert mismatch.decision_reason == "pcb_biased_precedence"
    assert mismatch.source_values == {"s": "SCH:0603", "p": "PCB:0402"}
    merged = result.records["R1"]
    assert merged.source_fields["s:footprint"] == "SCH:0603"
    assert merged.source_fields["p:footprint"] == "PCB:0402"
    assert merged.canonical_fields["c:footprint"] == "PCB:0402"
    assert merged.canonical_fields["c:package"] == "0402"
    assert (
        merged.annotated_fields["a:footprint"] == "s:SCH:0603\np:PCB:0402\nc:PCB:0402"
    )


def test_merge_without_pcb_record_still_produces_canonical_schematic_fields() -> None:
    collector = ProjectComponentCollector()
    graph = collector.collect(
        schematic_components=[_make_component("R2", value="1k", footprint="SCH:0805")],
        pcb_components=[],
    )
    service = ComponentMergeService()

    result = service.merge(graph)

    merged = result.records["R2"]
    assert merged.canonical_fields["c:value"] == "1k"
    assert merged.canonical_fields["c:footprint"] == "SCH:0805"
    assert merged.mismatches == tuple()
