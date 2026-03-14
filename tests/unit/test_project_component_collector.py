"""Unit tests for Phase-1 ProjectComponentCollector scaffolding."""

from __future__ import annotations

from pathlib import Path

from jbom.common.pcb_types import PcbComponent
from jbom.common.types import Component
from jbom.services.project_component_collector import ProjectComponentCollector


def _make_component(
    reference: str, *, value: str = "10k", footprint: str = "R_0603"
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
    footprint_name: str = "Resistor_SMD:R_0603_1608Metric",
    package_token: str = "0603",
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


def test_collect_groups_components_by_reference() -> None:
    collector = ProjectComponentCollector()
    schematic_components = [
        _make_component("R1"),
        _make_component("R1"),
        _make_component("R2", value="1k"),
    ]
    pcb_components = [
        _make_pcb_component("R1"),
        _make_pcb_component("C1", package_token="0402"),
    ]

    graph = collector.collect(
        schematic_components=schematic_components,
        pcb_components=pcb_components,
        schematic_files=[Path("/tmp/top.kicad_sch")],
        pcb_file=Path("/tmp/top.kicad_pcb"),
    )

    assert graph.reference_count == 3
    assert tuple(graph.references.keys()) == ("C1", "R1", "R2")
    assert len(graph.references["R1"].schematic_components) == 2
    assert len(graph.references["R1"].pcb_components) == 1
    assert len(graph.references["C1"].schematic_components) == 0
    assert graph.metadata["schematic_component_count"] == 3
    assert graph.metadata["pcb_component_count"] == 2
    assert graph.metadata["reference_count"] == 3


def test_collect_ignores_blank_references() -> None:
    collector = ProjectComponentCollector()
    schematic_components = [_make_component(""), _make_component("R5")]
    pcb_components = [_make_pcb_component(" "), _make_pcb_component("R5")]

    graph = collector.collect(
        schematic_components=schematic_components,
        pcb_components=pcb_components,
    )

    assert graph.reference_count == 1
    assert "R5" in graph.references
