"""Tests for ``jbom.services.project_metadata.expand_archive_template``."""

from __future__ import annotations

from pathlib import Path

from jbom.services.project_metadata import (
    DEFAULT_ARCHIVE_TEMPLATE,
    expand_archive_template,
)


def _write_minimal_project(
    tmp_path: Path,
    *,
    title: str,
    revision: str,
) -> Path:
    """Create a minimal .kicad_pcb + .kicad_pro pair with a title block."""
    project_dir = tmp_path
    project_name = project_dir.name
    pcb = project_dir / f"{project_name}.kicad_pcb"
    pcb.write_text(
        "(kicad_pcb (version 20211014)\n"
        f'  (title_block (title "{title}") (rev "{revision}"))\n'
        ")\n",
        encoding="utf-8",
    )
    (project_dir / f"{project_name}.kicad_pro").write_text(
        "(kicad_project (version 1))\n",
        encoding="utf-8",
    )
    return pcb


def test_expand_archive_template_uses_pcb_title_block(tmp_path: Path) -> None:
    """The template expands KiCad title-block variables from the PCB."""
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    pcb = _write_minimal_project(project_dir, title="cpNode", revision="1.0")
    stem = expand_archive_template("${TITLE}_${REVISION}", pcb)
    assert stem == "cpNode_1.0"


def test_expand_archive_template_default_template(tmp_path: Path) -> None:
    """An empty template falls back to ``DEFAULT_ARCHIVE_TEMPLATE``."""
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    pcb = _write_minimal_project(project_dir, title="MyBoard", revision="2.1")
    stem = expand_archive_template("", pcb)
    assert DEFAULT_ARCHIVE_TEMPLATE == "${TITLE}_${REVISION}"
    assert stem == "MyBoard_2.1"


def test_expand_archive_template_falls_back_to_pcb_stem(tmp_path: Path) -> None:
    """When the title block is empty, fall back to the PCB filename stem."""
    project_dir = tmp_path / "fallback"
    project_dir.mkdir()
    # Build a PCB whose title block has no title/rev so template yields '_'.
    pcb = _write_minimal_project(project_dir, title="", revision="")
    stem = expand_archive_template("${TITLE}_${REVISION}", pcb)
    assert stem == "fallback"


def test_expand_archive_template_handles_missing_pcb(tmp_path: Path) -> None:
    """When the PCB file does not exist, returns ``\"(unknown)\"``."""
    missing = tmp_path / "missing.kicad_pcb"
    stem = expand_archive_template("${TITLE}_${REVISION}", missing)
    assert stem == "(unknown)"


def test_expand_archive_template_normalises_unsafe_characters(tmp_path: Path) -> None:
    """Special characters in title-block values are normalised for filename use."""
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    pcb = _write_minimal_project(project_dir, title="My Board v2", revision="rev/A")
    stem = expand_archive_template("${TITLE}_${REVISION}", pcb)
    # spaces -> underscore; slash removed by the normaliser.
    assert " " not in stem
    assert "/" not in stem
    assert "My_Board_v2" in stem
