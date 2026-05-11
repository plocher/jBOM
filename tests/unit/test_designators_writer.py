"""Unit tests for DesignatorsWriter service and related integration points."""

from __future__ import annotations

from pathlib import Path

import pytest

from jbom.services.designators_writer import DesignatorsResult, DesignatorsWriter


# ---------------------------------------------------------------------------
# DesignatorsWriter.write — core behaviour
# ---------------------------------------------------------------------------


def test_write_basic_sorted(tmp_path: Path) -> None:
    """Designators are sorted naturally and written as REF:COUNT."""
    out = tmp_path / "designators.csv"
    result = DesignatorsWriter.write(["R2", "C1", "U1", "R1"], out, force=True)

    assert result.path == out
    assert result.designator_count == 4
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines == ["C1:1", "R1:1", "R2:1", "U1:1"]


def test_write_natural_sort_order(tmp_path: Path) -> None:
    """R10 sorts after R9, not after R1."""
    out = tmp_path / "designators.csv"
    DesignatorsWriter.write(["R10", "R2", "R1", "R9"], out, force=True)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines == ["R1:1", "R2:1", "R9:1", "R10:1"]


def test_write_duplicate_references_counted(tmp_path: Path) -> None:
    """Duplicate references produce count > 1."""
    out = tmp_path / "designators.csv"
    result = DesignatorsWriter.write(["R1", "R1", "C1"], out, force=True)
    assert result.designator_count == 2
    lines = out.read_text(encoding="utf-8").splitlines()
    assert "R1:2" in lines
    assert "C1:1" in lines


def test_write_empty_input_returns_none_path(tmp_path: Path) -> None:
    """Empty input produces no file and returns path=None."""
    out = tmp_path / "designators.csv"
    result = DesignatorsWriter.write([], out, force=True)

    assert result.path is None
    assert result.designator_count == 0
    assert not out.exists()
    assert any("skipped" in d.message for d in result.diagnostics)


def test_write_blank_references_skipped(tmp_path: Path) -> None:
    """Blank and whitespace-only references are ignored."""
    out = tmp_path / "designators.csv"
    result = DesignatorsWriter.write(["R1", "", "  ", "C1"], out, force=True)
    assert result.designator_count == 2
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines == ["C1:1", "R1:1"]


def test_write_no_force_existing_file_not_overwritten(tmp_path: Path) -> None:
    """Without force=True, an existing file is not overwritten."""
    out = tmp_path / "designators.csv"
    out.write_text("old content", encoding="utf-8")
    result = DesignatorsWriter.write(["R1"], out, force=False)

    assert result.path is None
    assert result.designator_count == 1
    assert out.read_text(encoding="utf-8") == "old content"
    assert any("already exists" in d.message for d in result.diagnostics)


def test_write_force_overwrites_existing_file(tmp_path: Path) -> None:
    """force=True overwrites an existing file."""
    out = tmp_path / "designators.csv"
    out.write_text("old content", encoding="utf-8")
    result = DesignatorsWriter.write(["R1"], out, force=True)

    assert result.path == out
    assert out.read_text(encoding="utf-8").strip() == "R1:1"


def test_write_creates_parent_directories(tmp_path: Path) -> None:
    """write() creates parent directories if they do not exist."""
    out = tmp_path / "deep" / "nested" / "designators.csv"
    result = DesignatorsWriter.write(["C1"], out, force=True)

    assert result.path == out
    assert out.exists()


def test_write_utf8_no_bom(tmp_path: Path) -> None:
    """Output file is plain UTF-8, no BOM."""
    out = tmp_path / "designators.csv"
    DesignatorsWriter.write(["R1"], out, force=True)
    raw = out.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "File must not have a UTF-8 BOM"


def test_write_unix_line_endings(tmp_path: Path) -> None:
    """Lines are terminated with LF only (\\n), not CRLF."""
    out = tmp_path / "designators.csv"
    DesignatorsWriter.write(["R1", "C1"], out, force=True)
    raw = out.read_bytes()
    assert b"\r\n" not in raw


def test_result_success_diagnostic(tmp_path: Path) -> None:
    """Successful write emits an info diagnostic with the count."""
    out = tmp_path / "designators.csv"
    result = DesignatorsWriter.write(["R1", "R2"], out, force=True)
    infos = [d.message for d in result.diagnostics if d.severity == "info"]
    assert any("2 designators" in msg for msg in infos)


# ---------------------------------------------------------------------------
# DesignatorsResult dataclass
# ---------------------------------------------------------------------------


def test_designators_result_immutable(tmp_path: Path) -> None:
    """DesignatorsResult is frozen — attributes cannot be reassigned."""
    result = DesignatorsResult(
        path=tmp_path / "d.csv",
        designator_count=3,
        diagnostics=(),
    )
    with pytest.raises((AttributeError, TypeError)):
        result.designator_count = 99  # type: ignore[misc]


def test_designators_result_path_coerced_to_path(tmp_path: Path) -> None:
    """path is coerced to Path even when given as a string."""
    result = DesignatorsResult(
        path=str(tmp_path / "d.csv"),  # type: ignore[arg-type]
        designator_count=1,
        diagnostics=(),
    )
    assert isinstance(result.path, Path)


# ---------------------------------------------------------------------------
# FabricatorConfig — generate_designators field
# ---------------------------------------------------------------------------


def test_fabricator_config_default_is_false() -> None:
    """generate_designators defaults to False when not set in YAML."""
    from jbom.config.fabricators import load_fabricator

    cfg = load_fabricator("generic")
    assert cfg.generate_designators is False


def test_fabricator_config_parse_true(tmp_path: Path) -> None:
    """generate_designators: true is parsed correctly from YAML."""
    import yaml
    from jbom.config.fabricators import FabricatorConfig

    # Patch a minimal fab YAML with generate_designators: true
    yaml_content = """
name: "TestFab"
id: "testfab"
generate_designators: true
suppliers:
  - generic
pos_columns:
  "Designator": "reference"
  "Mid X": "x"
  "Mid Y": "y"
  "Layer": "side"
  "Rotation": "rotation"
  "Package": "package"
field_synonyms:
  fab_pn:
    display_name: "Part #"
    synonyms: []
  supplier_pn:
    display_name: "SPN"
    synonyms: []
  mpn:
    display_name: "MPN"
    synonyms: []
"""
    data = yaml.safe_load(yaml_content)
    cfg = FabricatorConfig.from_yaml_dict(data, default_id="testfab")
    assert cfg.generate_designators is True


def test_fabricator_config_parse_false_explicit(tmp_path: Path) -> None:
    """generate_designators: false is parsed correctly from YAML."""
    import yaml
    from jbom.config.fabricators import FabricatorConfig

    yaml_content = """
name: "TestFab"
id: "testfab"
generate_designators: false
suppliers:
  - generic
pos_columns:
  "Designator": "reference"
  "Mid X": "x"
  "Mid Y": "y"
  "Layer": "side"
  "Rotation": "rotation"
  "Package": "package"
field_synonyms:
  fab_pn:
    display_name: "Part #"
    synonyms: []
  supplier_pn:
    display_name: "SPN"
    synonyms: []
  mpn:
    display_name: "MPN"
    synonyms: []
"""
    data = yaml.safe_load(yaml_content)
    cfg = FabricatorConfig.from_yaml_dict(data, default_id="testfab")
    assert cfg.generate_designators is False


# ---------------------------------------------------------------------------
# FabricationRequest — generate_designators field
# ---------------------------------------------------------------------------


def test_fabrication_request_defaults_false(tmp_path: Path) -> None:
    """generate_designators defaults to False in FabricationRequest."""
    from jbom.application.fabrication_orchestration import FabricationRequest

    req = FabricationRequest(input_path=str(tmp_path))
    assert req.generate_designators is False


def test_fabrication_request_truthy_coercion(tmp_path: Path) -> None:
    """generate_designators is coerced to bool."""
    from jbom.application.fabrication_orchestration import FabricationRequest

    req = FabricationRequest(input_path=str(tmp_path), generate_designators=1)  # type: ignore[arg-type]
    assert req.generate_designators is True


# ---------------------------------------------------------------------------
# FabricationWorkflow integration — designators artifact produced
# ---------------------------------------------------------------------------


def test_fabrication_workflow_generates_designators_when_requested(
    tmp_path: Path,
) -> None:
    """When generate_designators=True, workflow writes designators.csv artifact."""
    import textwrap
    from jbom.application.fabrication_orchestration import (
        FabricationRequest,
        FabricationWorkflow,
    )

    # Minimal KiCad project fixture
    proj_name = "proj"
    (tmp_path / f"{proj_name}.kicad_pro").write_text(
        "(kicad_project (version 1))\n", encoding="utf-8"
    )
    (tmp_path / f"{proj_name}.kicad_sch").write_text(
        "(kicad_sch (version 20211123) (generator eeschema))\n", encoding="utf-8"
    )
    pcb_content = textwrap.dedent(
        """\
        (kicad_pcb (version 20211014) (generator pcbnew)
          (footprint "R_0805_2012" (at 10 5 0) (layer "F.Cu")
            (property "Reference" "R1")
            (attr smd)
          )
          (footprint "C_0603_1608" (at 15 8 0) (layer "F.Cu")
            (property "Reference" "C1")
            (attr smd)
          )
        )
    """
    )
    (tmp_path / f"{proj_name}.kicad_pcb").write_text(pcb_content, encoding="utf-8")

    req = FabricationRequest(
        input_path=str(tmp_path),
        skip_bom=True,
        skip_pos=True,
        skip_gerbers=True,
        skip_backup=True,
        generate_designators=True,
    )
    result = FabricationWorkflow().run(req)

    des_artifacts = [a for a in result.artifacts if a.artifact_type == "designators"]
    assert des_artifacts, "Expected a 'designators' artifact in the result"
    des_path = des_artifacts[0].path
    assert des_path is not None and des_path.exists()
    content = des_path.read_text(encoding="utf-8")
    assert "C1:1" in content
    assert "R1:1" in content


def test_fabrication_workflow_skips_designators_when_not_requested(
    tmp_path: Path,
) -> None:
    """When generate_designators=False (default), no designators artifact is produced."""
    from jbom.application.fabrication_orchestration import (
        FabricationRequest,
        FabricationWorkflow,
    )

    proj_name = "proj"
    (tmp_path / f"{proj_name}.kicad_pro").write_text(
        "(kicad_project (version 1))\n", encoding="utf-8"
    )
    (tmp_path / f"{proj_name}.kicad_sch").write_text(
        "(kicad_sch (version 20211123) (generator eeschema))\n", encoding="utf-8"
    )
    (tmp_path / f"{proj_name}.kicad_pcb").write_text(
        "(kicad_pcb (version 20211014) (generator pcbnew))\n", encoding="utf-8"
    )

    req = FabricationRequest(
        input_path=str(tmp_path),
        skip_bom=True,
        skip_pos=True,
        skip_gerbers=True,
        skip_backup=True,
        generate_designators=False,
    )
    result = FabricationWorkflow().run(req)

    des_artifacts = [a for a in result.artifacts if a.artifact_type == "designators"]
    assert not des_artifacts
    assert not (tmp_path / "production" / "designators.csv").exists()
