"""Service-level tests for adapter-neutral BOM orchestration flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from jbom.application import pcb_project_loader
from jbom.application.bom_workflow import (
    BOMWorkflow,
    BOMMode,
    BOMRequest,
)
from jbom.services.bom_generator import BOMData, BOMEntry


@dataclass(frozen=True)
class _FakeProjectContext:
    """Minimal project-context fixture used by orchestration tests."""

    project_base_name: str
    project_directory: Path
    pcb_file: Path | None


class _FakeResolvedInput:
    """Minimal resolved-input fixture used by orchestration tests."""

    def __init__(
        self,
        *,
        resolved_path: Path,
        is_schematic: bool,
        project_context: _FakeProjectContext | None,
        hierarchical_files: list[Path],
    ) -> None:
        self.resolved_path = resolved_path
        self.is_schematic = is_schematic
        self.project_context = project_context
        self._hierarchical_files = list(hierarchical_files)

    def get_hierarchical_files(self) -> list[Path]:
        """Return hierarchical schematic file fixtures."""

        return list(self._hierarchical_files)


def test_list_fields_orchestration_returns_known_contract_fields(monkeypatch) -> None:
    """List-fields mode should still return stable known fields if runtime discovery fails."""

    def _failing_resolve(_input_path, *, artifact_name="BOM", options=None):
        raise RuntimeError("resolver failed")

    monkeypatch.setattr(
        "jbom.application.bom_workflow.resolve_pcb_input", _failing_resolve
    )

    service = BOMWorkflow()
    request = BOMRequest(
        input_path=".",
        fabricator="generic",
        list_fields=True,
    )
    result = service.run(request)

    assert result.mode == BOMMode.LIST_FIELDS
    assert result.field_listing is not None
    assert "reference" in result.field_listing.known_fields
    assert "fabricator_part_number" in result.field_listing.known_fields


@patch("jbom.application.bom_workflow.InventoryOverlayService")
@patch("jbom.application.bom_workflow.parse_fields_argument")
@patch("jbom.application.bom_workflow.get_fabricator_presets")
@patch("jbom.application.bom_workflow.run_component_merge")
@patch("jbom.application.bom_workflow.BOMGenerator")
@patch("jbom.application.bom_workflow.load_board")
@patch("jbom.application.bom_workflow.load_schematic_components")
@patch("jbom.application.bom_workflow.list_hierarchical_schematic_files")
@patch("jbom.application.bom_workflow.resolve_pcb_input")
def test_generation_orchestration_handles_cross_resolution_and_returns_payload(
    mock_resolve_pcb_input: MagicMock,
    mock_list_hier: MagicMock,
    mock_load_schematic: MagicMock,
    mock_load_board: MagicMock,
    mock_generator_cls: MagicMock,
    mock_run_component_merge: MagicMock,
    mock_get_fabricator_presets: MagicMock,
    mock_parse_fields_argument: MagicMock,
    mock_overlay_service_cls: MagicMock,
) -> None:
    """Generation mode is PCB-first and surfaces the BOM diagnostic trio."""

    from jbom.common.types import Diagnostic

    project_context = _FakeProjectContext(
        project_base_name="project",
        project_directory=Path("/tmp/project-dir"),
        pcb_file=Path("project.kicad_pcb"),
    )
    pcb_path = Path("project.kicad_pcb")
    resolved_input = _FakeResolvedInput(
        resolved_path=pcb_path,
        is_schematic=False,
        project_context=project_context,
        hierarchical_files=[],
    )
    mock_resolve_pcb_input.return_value = pcb_project_loader.ResolvedPcbProject(
        resolved_input=resolved_input,
        pcb_path=pcb_path,
        project_context=project_context,
        diagnostics=(
            Diagnostic(
                "info",
                "Note: BOM generation requires a PCB file. Found .kicad_sch file, trying to find matching PCB.",
            ),
            Diagnostic("info", "found matching PCB project.kicad_pcb"),
            Diagnostic("info", "Using PCB: project.kicad_pcb"),
        ),
    )
    mock_list_hier.return_value = []
    mock_load_schematic.return_value = ([], ())
    mock_load_board.return_value = SimpleNamespace(footprints=[])

    bom_data = BOMData(
        project_name="project",
        entries=[
            BOMEntry(
                references=["R1"],
                value="10k",
                footprint="Resistor_SMD:R_0603_1608Metric",
                quantity=1,
                attributes={},
            )
        ],
        metadata={},
    )
    generator = mock_generator_cls.return_value
    generator.generate_bom_data.return_value = bom_data

    mock_run_component_merge.return_value = (None, ())
    mock_get_fabricator_presets.return_value = {}
    mock_parse_fields_argument.return_value = ["reference", "quantity"]

    overlay_service = mock_overlay_service_cls.return_value
    overlay_service.overlay_bom_data.return_value = SimpleNamespace(bom_data=bom_data)

    request = BOMRequest(
        input_path=".",
        fabricator="generic",
        fields_argument="reference,quantity",
        filter_config={"exclude_dnp": True},
        verbose=True,
        list_fields=False,
    )
    result = BOMWorkflow().run(request)

    assert result.mode == BOMMode.GENERATE
    assert result.generation is not None
    assert result.generation.default_output_path == Path(
        "/tmp/project-dir/project.bom.csv"
    )
    assert result.generation.selected_fields == ("reference", "quantity")
    assert any(
        "found matching PCB project.kicad_pcb" in d.message for d in result.diagnostics
    )


# ---------------------------------------------------------------------------
# synthesize_bom_components_from_pcb
# ---------------------------------------------------------------------------


def test_synthesize_uses_pcb_footprint_and_schematic_value() -> None:
    """PCB footprint wins; schematic value wins."""
    from jbom.application.bom_workflow import synthesize_bom_components_from_pcb
    from jbom.common.pcb_types import PcbComponent
    from jbom.common.types import Component

    board = SimpleNamespace(
        footprints=[
            PcbComponent(
                reference="R1",
                footprint_name="Resistor_SMD:R_0603_1608Metric",
                package_token="0603",
                center_x_mm=10.0,
                center_y_mm=20.0,
                rotation_deg=0.0,
                side="TOP",
                attributes={"mount_type": "smd", "Value": "4.7k"},
            ),
        ]
    )
    schematic_components = [
        Component(
            reference="R1",
            lib_id="Device:R",
            value="10k",
            footprint="Resistor_SMD:R_0603",  # schematic wildcard, will be ignored
        )
    ]
    components = synthesize_bom_components_from_pcb(
        board=board, schematic_components=schematic_components
    )
    assert len(components) == 1
    assert components[0].reference == "R1"
    assert components[0].value == "10k"  # schematic-biased
    assert components[0].footprint == "Resistor_SMD:R_0603_1608Metric"  # PCB-biased
    assert components[0].properties.get("smd") == "true"
    assert components[0].properties.get("Package") == "0603"
    assert components[0].properties.get("Side") == "TOP"


def test_synthesize_skips_schematic_only_references() -> None:
    """References present only in the schematic are invisible to BOM by design."""
    from jbom.application.bom_workflow import synthesize_bom_components_from_pcb
    from jbom.common.pcb_types import PcbComponent
    from jbom.common.types import Component

    board = SimpleNamespace(
        footprints=[
            PcbComponent(
                reference="R1",
                footprint_name="Resistor_SMD:R_0603",
                package_token="0603",
                center_x_mm=0.0,
                center_y_mm=0.0,
                rotation_deg=0.0,
                side="TOP",
            )
        ]
    )
    schematic_components = [
        Component(reference="R1", lib_id="Device:R", value="10k", footprint=""),
        Component(
            reference="MH1",  # mounting hole symbol, no PCB footprint
            lib_id="Mechanical:MountingHole",
            value="",
            footprint="",
        ),
    ]
    components = synthesize_bom_components_from_pcb(
        board=board, schematic_components=schematic_components
    )
    refs = [c.reference for c in components]
    assert refs == ["R1"]


def test_synthesize_falls_back_to_pcb_value_when_schematic_silent() -> None:
    """When schematic has no record, PCB attributes supply the value."""
    from jbom.application.bom_workflow import synthesize_bom_components_from_pcb
    from jbom.common.pcb_types import PcbComponent

    board = SimpleNamespace(
        footprints=[
            PcbComponent(
                reference="R9",
                footprint_name="Resistor_SMD:R_0805",
                package_token="0805",
                center_x_mm=0.0,
                center_y_mm=0.0,
                rotation_deg=0.0,
                side="TOP",
                attributes={"Value": "22k"},
            )
        ]
    )
    components = synthesize_bom_components_from_pcb(
        board=board, schematic_components=[]
    )
    assert components[0].value == "22k"
    assert components[0].footprint == "Resistor_SMD:R_0805"


def test_synthesize_propagates_schematic_dnp() -> None:
    """Schematic DNP propagates to the synthesized PCB-first Component."""
    from jbom.application.bom_workflow import synthesize_bom_components_from_pcb
    from jbom.common.pcb_types import PcbComponent
    from jbom.common.types import Component

    board = SimpleNamespace(
        footprints=[
            PcbComponent(
                reference="C2",
                footprint_name="Capacitor_SMD:C_0402",
                package_token="0402",
                center_x_mm=0.0,
                center_y_mm=0.0,
                rotation_deg=0.0,
                side="TOP",
            )
        ]
    )
    schematic_components = [
        Component(
            reference="C2",
            lib_id="Device:C",
            value="100nF",
            footprint="",
            dnp=True,
        )
    ]
    components = synthesize_bom_components_from_pcb(
        board=board, schematic_components=schematic_components
    )
    assert components[0].dnp is True
