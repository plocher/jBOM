"""Service-level tests for adapter-neutral BOM orchestration flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from jbom.application.bom_orchestration import (
    BOMOrchestrationService,
    BOMOrchestrationMode,
    BOMOrchestrationRequest,
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


def test_list_fields_orchestration_returns_known_contract_fields() -> None:
    """List-fields mode should still return stable known fields if runtime discovery fails."""

    service = BOMOrchestrationService()
    request = BOMOrchestrationRequest(
        input_path=".",
        fabricator="generic",
        list_fields=True,
    )

    with patch(
        "jbom.application.bom_orchestration.ProjectFileResolver"
    ) as resolver_cls:
        resolver_cls.return_value.resolve_input.side_effect = ValueError("boom")
        result = service.orchestrate(request)

    assert result.mode == BOMOrchestrationMode.LIST_FIELDS
    assert result.field_listing is not None
    assert "reference" in result.field_listing.known_fields
    assert "fabricator_part_number" in result.field_listing.known_fields


@patch("jbom.application.bom_orchestration.enrich_bom_smd_from_project_pcb")
@patch("jbom.application.bom_orchestration.InventoryOverlayService")
@patch("jbom.application.bom_orchestration.parse_fields_argument")
@patch("jbom.application.bom_orchestration.get_fabricator_presets")
@patch("jbom.application.bom_orchestration.run_component_merge")
@patch("jbom.application.bom_orchestration.BOMGenerator")
@patch("jbom.application.bom_orchestration.SchematicReader")
@patch("jbom.application.bom_orchestration.ProjectFileResolver")
def test_generation_orchestration_handles_cross_resolution_and_returns_payload(
    mock_resolver_cls: MagicMock,
    mock_reader_cls: MagicMock,
    mock_generator_cls: MagicMock,
    mock_run_component_merge: MagicMock,
    mock_get_fabricator_presets: MagicMock,
    mock_parse_fields_argument: MagicMock,
    mock_overlay_service_cls: MagicMock,
    mock_enrich_smd: MagicMock,
) -> None:
    """Generation mode should sequence cross-resolution and payload assembly in service layer."""

    project_context = _FakeProjectContext(
        project_base_name="project",
        project_directory=Path("/tmp/project-dir"),
        pcb_file=None,
    )
    wrong_type_input = _FakeResolvedInput(
        resolved_path=Path("project.kicad_pcb"),
        is_schematic=False,
        project_context=project_context,
        hierarchical_files=[Path("project.kicad_sch")],
    )
    corrected_input = _FakeResolvedInput(
        resolved_path=Path("project.kicad_sch"),
        is_schematic=True,
        project_context=project_context,
        hierarchical_files=[Path("project.kicad_sch")],
    )

    resolver = mock_resolver_cls.return_value
    resolver.resolve_input.return_value = wrong_type_input
    resolver.resolve_for_wrong_file_type.return_value = corrected_input

    reader = mock_reader_cls.return_value
    reader.load_components.return_value = [object()]

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
    mock_enrich_smd.return_value = (bom_data, ())

    request = BOMOrchestrationRequest(
        input_path=".",
        fabricator="generic",
        fields_argument="reference,quantity",
        filter_config={"exclude_dnp": True},
        verbose=True,
        list_fields=False,
    )
    result = BOMOrchestrationService().orchestrate(request)

    assert result.mode == BOMOrchestrationMode.GENERATE
    assert result.generation is not None
    assert result.generation.default_output_path == Path(
        "/tmp/project-dir/project.bom.csv"
    )
    assert result.generation.selected_fields == ("reference", "quantity")
    assert "found matching schematic project.kicad_sch" in result.diagnostics
