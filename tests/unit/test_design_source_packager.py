"""Unit tests for ``DesignSourcePackager``."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from jbom.services.design_source_packager import DesignSourcePackager


class TestDesignSourcePackager:
    """Tests for packaging KiCad design-source archives."""

    def test_package_includes_kicad_and_optional_source_files(
        self, tmp_path: Path
    ) -> None:
        """Archive should include KiCad source files and optional JSON configs."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        (project_dir / "project.kicad_pro").write_text("", encoding="utf-8")
        (project_dir / "project.kicad_prl").write_text("", encoding="utf-8")
        (project_dir / "project.kicad_pcb").write_text("", encoding="utf-8")
        (project_dir / "project.kicad_sch").write_text("", encoding="utf-8")
        (project_dir / "fabrication-toolkit-options.json").write_text(
            "{}", encoding="utf-8"
        )

        subdir = project_dir / "sheets"
        subdir.mkdir()
        (subdir / "daughter.kicad_sch").write_text("", encoding="utf-8")

        jbom_dir = project_dir / ".jbom"
        jbom_dir.mkdir()
        (jbom_dir / "jbom-options.json").write_text("{}", encoding="utf-8")

        archive_path = tmp_path / "design-sources.zip"
        result = DesignSourcePackager().package(project_dir, archive_path)

        assert result == archive_path
        assert archive_path.exists()

        with zipfile.ZipFile(archive_path, "r") as zipf:
            names = set(zipf.namelist())

        assert "project.kicad_pro" in names
        assert "project.kicad_prl" in names
        assert "project.kicad_pcb" in names
        assert "project.kicad_sch" in names
        assert "sheets/daughter.kicad_sch" in names
        assert "fabrication-toolkit-options.json" in names
        assert ".jbom/jbom-options.json" in names

    def test_package_raises_for_missing_project_dir(self, tmp_path: Path) -> None:
        """Missing project directory should raise ValueError."""
        project_dir = tmp_path / "missing"
        archive_path = tmp_path / "design-sources.zip"

        with pytest.raises(ValueError, match="project_dir is not a directory"):
            DesignSourcePackager().package(project_dir, archive_path)

    def test_package_raises_when_no_design_source_files(self, tmp_path: Path) -> None:
        """Directories with no supported source files should raise ValueError."""
        project_dir = tmp_path / "empty_project"
        project_dir.mkdir()
        (project_dir / "notes.txt").write_text("not a design file", encoding="utf-8")
        archive_path = tmp_path / "design-sources.zip"

        with pytest.raises(ValueError, match="No design-source files found"):
            DesignSourcePackager().package(project_dir, archive_path)
