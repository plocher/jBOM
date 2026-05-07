"""Service-level tests for adapter-neutral POS orchestration."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from jbom.application.pos_orchestration import (
    POSOrchestrationRequest,
    POSOrchestrationService,
    resolve_pos_output_projection,
)


def test_pos_orchestration_service_runs_without_cli_import(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """POS orchestration should execute without importing CLI modules."""

    class _FakeProjectContext:
        project_base_name = "demo"
        project_directory = tmp_path

        @staticmethod
        def get_hierarchical_schematic_files() -> list[Path]:
            return []

    class _FakeResolvedInput:
        is_pcb = True
        resolved_path = tmp_path / "demo.kicad_pcb"
        project_context = _FakeProjectContext()

    class _FakeResolver:
        def __init__(self, **_kwargs) -> None:
            pass

        @staticmethod
        def resolve_input(_input_path: str) -> _FakeResolvedInput:
            return _FakeResolvedInput()

        @staticmethod
        def resolve_for_wrong_file_type(_resolved_input, _target: str):
            raise AssertionError("Cross-resolution should not be used in this test")

    class _FakeReader:
        @staticmethod
        def read_pcb_file(_pcb_path: Path):
            return SimpleNamespace(footprints=[])

    class _FakeGenerator:
        def __init__(self, _options) -> None:
            pass

        @staticmethod
        def generate_pos_data(_board) -> list[dict[str, object]]:
            return [
                {
                    "reference": "U1",
                    "s:dnp": "yes",
                    "x_mm": 1.0,
                    "y_mm": 1.0,
                    "rotation": 0.0,
                    "side": "TOP",
                },
                {
                    "reference": "U2",
                    "x_mm": 2.0,
                    "y_mm": 2.0,
                    "rotation": 90.0,
                    "side": "TOP",
                },
            ]

    monkeypatch.setattr(
        "jbom.application.pos_orchestration.ProjectFileResolver", _FakeResolver
    )
    monkeypatch.setattr(
        "jbom.application.pos_orchestration.DefaultKiCadReaderService",
        _FakeReader,
    )
    monkeypatch.setattr(
        "jbom.application.pos_orchestration.POSGenerator", _FakeGenerator
    )
    monkeypatch.setattr(
        "jbom.application.pos_orchestration.run_pos_component_merge",
        lambda **_kwargs: (None, ()),
    )

    service = POSOrchestrationService()
    result = service.orchestrate(
        POSOrchestrationRequest(
            input_path=str(tmp_path),
            fields="reference,x,y",
            include_dnp=False,
            fabricator="generic",
        )
    )

    assert result.generation is not None
    references = [row["reference"] for row in result.generation.pos_data]
    assert references == ["U2"]
    assert result.generation.default_output_path == tmp_path / "demo.pos.csv"


def test_pos_orchestration_list_fields_falls_back_when_discovery_errors(
    monkeypatch,
) -> None:
    """Field listing should still succeed when runtime discovery fails."""

    class _FailingResolver:
        def __init__(self, **_kwargs) -> None:
            pass

        @staticmethod
        def resolve_input(_input_path: str):
            raise RuntimeError("resolver failed")

    monkeypatch.setattr(
        "jbom.application.pos_orchestration.ProjectFileResolver",
        _FailingResolver,
    )

    service = POSOrchestrationService()
    result = service.orchestrate(
        POSOrchestrationRequest(
            input_path=".",
            list_fields=True,
            fabricator="jlc",
        )
    )

    assert result.field_listing is not None
    assert "reference" in result.field_listing.known_fields
    assert "x" in result.field_listing.known_fields
    assert result.field_listing.default_fields
    assert result.generation is None


def test_pos_projection_service_preserves_user_headers() -> None:
    """Service projection should keep natural headers for user-selected generic fields."""

    selected_fields, headers, _config = resolve_pos_output_projection(
        selected_fields=["reference", "x", "y", "side"],
        fabricator="generic",
        user_specified_fields=True,
    )

    assert selected_fields == ["reference", "x", "y", "side"]
    assert headers == ["Reference", "X", "Y", "Side"]
