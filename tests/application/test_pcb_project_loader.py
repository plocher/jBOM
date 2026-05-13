"""Tests for ``jbom.application.pcb_project_loader``."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from jbom.application import pcb_project_loader as loader


# ---------------------------------------------------------------------------
# resolve_pcb_input
# ---------------------------------------------------------------------------


class _FakeResolvedInput:
    """Stand-in for ProjectFileResolver's ``ResolvedInput`` result."""

    def __init__(
        self,
        *,
        is_pcb: bool,
        resolved_path: Path,
        project_context: Any,
    ) -> None:
        self.is_pcb = is_pcb
        self.resolved_path = resolved_path
        self.project_context = project_context


class _FakeProjectContext:
    project_base_name = "demo"
    project_directory = Path("/tmp/demo")

    @staticmethod
    def get_hierarchical_schematic_files() -> list[Path]:
        return []


class _FakeResolver:
    """Stand-in for ProjectFileResolver."""

    def __init__(
        self,
        *,
        starts_as_pcb: bool,
        starting_path: Path,
        pcb_path: Path,
        project_context: Any,
    ) -> None:
        self.starts_as_pcb = starts_as_pcb
        self.starting_path = starting_path
        self.pcb_path = pcb_path
        self.project_context = project_context
        self.resolve_for_wrong_file_type_calls = 0

    def resolve_input(self, _input_path: str) -> _FakeResolvedInput:
        return _FakeResolvedInput(
            is_pcb=self.starts_as_pcb,
            resolved_path=self.starting_path,
            project_context=self.project_context,
        )

    def resolve_for_wrong_file_type(
        self, _resolved_input: Any, _target: str
    ) -> _FakeResolvedInput:
        self.resolve_for_wrong_file_type_calls += 1
        return _FakeResolvedInput(
            is_pcb=True,
            resolved_path=self.pcb_path,
            project_context=self.project_context,
        )


def test_resolve_pcb_input_emits_no_diagnostics_when_input_is_pcb(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A direct ``.kicad_pcb`` input passes through without the chatty trio."""
    pcb_path = tmp_path / "demo.kicad_pcb"
    fake_resolver = _FakeResolver(
        starts_as_pcb=True,
        starting_path=pcb_path,
        pcb_path=pcb_path,
        project_context=_FakeProjectContext(),
    )
    monkeypatch.setattr(loader, "ProjectFileResolver", lambda **_kwargs: fake_resolver)
    result = loader.resolve_pcb_input(str(pcb_path), artifact_name="BOM")
    assert result.pcb_path == pcb_path
    assert result.diagnostics == ()
    assert fake_resolver.resolve_for_wrong_file_type_calls == 0


def test_resolve_pcb_input_emits_diagnostic_trio_when_input_is_schematic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A schematic input gets resolved to the sibling PCB with three info notes."""
    schematic_path = tmp_path / "demo.kicad_sch"
    pcb_path = tmp_path / "demo.kicad_pcb"
    fake_resolver = _FakeResolver(
        starts_as_pcb=False,
        starting_path=schematic_path,
        pcb_path=pcb_path,
        project_context=_FakeProjectContext(),
    )
    monkeypatch.setattr(loader, "ProjectFileResolver", lambda **_kwargs: fake_resolver)
    result = loader.resolve_pcb_input(str(schematic_path), artifact_name="BOM")
    assert result.pcb_path == pcb_path
    assert fake_resolver.resolve_for_wrong_file_type_calls == 1
    severities = [d.severity for d in result.diagnostics]
    messages = [d.message for d in result.diagnostics]
    assert severities == ["info", "info", "info"]
    assert messages[0].startswith("Note: BOM generation requires a PCB file.")
    assert "found matching PCB" in messages[1]
    assert messages[2].startswith("Using PCB:")


def test_resolve_pcb_input_uses_artifact_name_in_diagnostic_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``artifact_name`` controls only the wording, not the resolution flow."""
    schematic_path = tmp_path / "demo.kicad_sch"
    pcb_path = tmp_path / "demo.kicad_pcb"
    fake_resolver = _FakeResolver(
        starts_as_pcb=False,
        starting_path=schematic_path,
        pcb_path=pcb_path,
        project_context=_FakeProjectContext(),
    )
    monkeypatch.setattr(loader, "ProjectFileResolver", lambda **_kwargs: fake_resolver)
    result = loader.resolve_pcb_input(str(schematic_path), artifact_name="POS")
    assert "POS generation requires a PCB file" in result.diagnostics[0].message


def test_resolve_pcb_input_raises_when_no_project_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A resolver result without project context is fatal."""

    class _ContextlessResolver:
        @staticmethod
        def resolve_input(_input_path: str) -> _FakeResolvedInput:
            return _FakeResolvedInput(
                is_pcb=True,
                resolved_path=tmp_path / "demo.kicad_pcb",
                project_context=None,
            )

    monkeypatch.setattr(
        loader, "ProjectFileResolver", lambda **_kwargs: _ContextlessResolver()
    )
    with pytest.raises(ValueError, match="No project context available"):
        loader.resolve_pcb_input(str(tmp_path), artifact_name="BOM")


# ---------------------------------------------------------------------------
# list_hierarchical_schematic_files
# ---------------------------------------------------------------------------


def test_list_hierarchical_schematic_files_filters_missing_and_non_kicad(
    tmp_path: Path,
) -> None:
    """Only existing ``.kicad_sch`` paths are returned."""
    existing = tmp_path / "root.kicad_sch"
    existing.write_text("(kicad_sch)", encoding="utf-8")
    missing = tmp_path / "missing.kicad_sch"
    wrong_suffix = tmp_path / "notes.txt"
    wrong_suffix.write_text("ignore me", encoding="utf-8")

    class _Ctx:
        @staticmethod
        def get_hierarchical_schematic_files() -> list[Path]:
            return [existing, missing, wrong_suffix]

    result = loader.list_hierarchical_schematic_files(_Ctx())
    assert result == [existing]


def test_list_hierarchical_schematic_files_returns_empty_on_error() -> None:
    """When the project context raises, return ``[]`` rather than crash."""

    class _BrokenCtx:
        @staticmethod
        def get_hierarchical_schematic_files() -> list[Path]:
            raise RuntimeError("intentional failure")

    assert loader.list_hierarchical_schematic_files(_BrokenCtx()) == []


# ---------------------------------------------------------------------------
# load_schematic_components
# ---------------------------------------------------------------------------


def test_load_schematic_components_returns_empty_when_no_files() -> None:
    """No files in, no components / diagnostics out."""
    components, diagnostics = loader.load_schematic_components([])
    assert components == []
    assert diagnostics == ()


def test_load_schematic_components_emits_warning_on_failure_when_verbose(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Per-file failures become warning diagnostics in verbose mode."""
    schematic = tmp_path / "broken.kicad_sch"
    schematic.write_text("(garbage)", encoding="utf-8")

    class _BrokenReader:
        def __init__(self, _options) -> None:
            pass

        @staticmethod
        def load_components(_path: Path) -> list[Any]:
            raise RuntimeError("parse exploded")

    monkeypatch.setattr(loader, "SchematicReader", _BrokenReader)
    components, diagnostics = loader.load_schematic_components(
        [schematic], verbose=True
    )
    assert components == []
    assert len(diagnostics) == 1
    assert "broken.kicad_sch" in diagnostics[0].message


def test_load_schematic_components_silent_failure_when_not_verbose(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Non-verbose runs swallow per-file failures."""
    schematic = tmp_path / "broken.kicad_sch"
    schematic.write_text("(garbage)", encoding="utf-8")

    class _BrokenReader:
        def __init__(self, _options) -> None:
            pass

        @staticmethod
        def load_components(_path: Path) -> list[Any]:
            raise RuntimeError("parse exploded")

    monkeypatch.setattr(loader, "SchematicReader", _BrokenReader)
    components, diagnostics = loader.load_schematic_components([schematic])
    assert components == []
    assert diagnostics == ()


# ---------------------------------------------------------------------------
# collect_project_graph
# ---------------------------------------------------------------------------


def test_collect_project_graph_uses_board_footprints_as_canonical_input(
    tmp_path: Path,
) -> None:
    """``collect_project_graph`` feeds ``board.footprints`` into the collector.

    Asserts the by-reference grouping seeded by the PCB plus schematic
    components produces the expected reference set.
    """
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
            ),
            PcbComponent(
                reference="R2",
                footprint_name="Resistor_SMD:R_0603_1608Metric",
                package_token="0603",
                center_x_mm=15.0,
                center_y_mm=20.0,
                rotation_deg=0.0,
                side="TOP",
            ),
        ]
    )
    schematic_components = [
        Component(
            reference="R1",
            value="10k",
            footprint="Resistor_SMD:R_0603",
            lib_id="Device:R",
        )
    ]
    pcb_file = tmp_path / "demo.kicad_pcb"
    pcb_file.write_text("(kicad_pcb)", encoding="utf-8")

    graph = loader.collect_project_graph(
        board=board,
        schematic_components=schematic_components,
        schematic_files=[],
        pcb_file=pcb_file,
    )
    assert set(graph.references) == {"R1", "R2"}
    assert graph.references[
        "R1"
    ].schematic_components, "R1 schematic component should be present"
    assert graph.references["R2"].schematic_components == ()
