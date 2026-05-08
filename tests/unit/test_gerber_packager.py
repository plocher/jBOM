"""Unit tests for GerberPackager service."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import pytest

from jbom.services.gerber_packager import GerberPackager


class TestGerberPackager:
    """Tests for GerberPackager service."""

    def test_package_single_gerber_file(self) -> None:
        """GerberPackager should archive a single gerber file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a gerber directory with a file
            gerber_dir = tmpdir_path / "gerbers"
            gerber_dir.mkdir()
            gerber_file = gerber_dir / "design.gbr"
            gerber_file.write_text("Gerber data")

            # Package it
            archive_path = tmpdir_path / "output.zip"
            packager = GerberPackager()
            result = packager.package([gerber_file], archive_path)

            # Verify archive was created and returned
            assert result == archive_path
            assert archive_path.exists()

            # Verify gerber directory was removed (default behavior)
            assert not gerber_dir.exists()

            # Verify archive contents
            with zipfile.ZipFile(archive_path, "r") as z:
                names = z.namelist()
                assert any("design.gbr" in name for name in names)

    def test_package_multiple_gerber_files(self) -> None:
        """GerberPackager should archive multiple gerber files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create gerber directory with multiple files
            gerber_dir = tmpdir_path / "gerbers"
            gerber_dir.mkdir()
            file1 = gerber_dir / "design.gbr"
            file1.write_text("Gerber 1")
            file2 = gerber_dir / "design.gbl"
            file2.write_text("Gerber 2")

            # Package them
            archive_path = tmpdir_path / "output.zip"
            packager = GerberPackager()
            packager.package([file1, file2], archive_path)

            # Verify both files in archive
            with zipfile.ZipFile(archive_path, "r") as z:
                names = z.namelist()
                assert any("design.gbr" in name for name in names)
                assert any("design.gbl" in name for name in names)

            # Verify directory removed
            assert not gerber_dir.exists()

    def test_package_with_debug_mode_preserves_directory(self) -> None:
        """GerberPackager should preserve gerber directory when debug=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create gerber directory
            gerber_dir = tmpdir_path / "gerbers"
            gerber_dir.mkdir()
            gerber_file = gerber_dir / "design.gbr"
            gerber_file.write_text("Gerber data")

            # Package with debug=True
            archive_path = tmpdir_path / "output.zip"
            packager = GerberPackager()
            packager.package([gerber_file], archive_path, debug=True)

            # Verify directory still exists
            assert gerber_dir.exists()
            assert gerber_file.exists()

            # Verify archive was created
            assert archive_path.exists()

    def test_package_raises_on_empty_paths(self) -> None:
        """GerberPackager should raise ValueError on empty artifact_paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            archive_path = tmpdir_path / "output.zip"

            packager = GerberPackager()
            with pytest.raises(ValueError, match="artifact_paths cannot be empty"):
                packager.package([], archive_path)

    def test_package_raises_on_missing_artifact(self) -> None:
        """GerberPackager should raise FileNotFoundError if artifact doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            nonexistent = tmpdir_path / "nonexistent.gbr"
            archive_path = tmpdir_path / "output.zip"

            packager = GerberPackager()
            with pytest.raises(FileNotFoundError):
                packager.package([nonexistent], archive_path)

    def test_package_returns_archive_path(self) -> None:
        """GerberPackager.package should return the archive_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create gerber file
            gerber_dir = tmpdir_path / "gerbers"
            gerber_dir.mkdir()
            gerber_file = gerber_dir / "design.gbr"
            gerber_file.write_text("Gerber")

            # Package and check return value
            archive_path = tmpdir_path / "output.zip"
            packager = GerberPackager()
            result = packager.package([gerber_file], archive_path)

            assert result == archive_path
            assert isinstance(result, Path)

    def test_package_nested_gerber_files(self) -> None:
        """GerberPackager should handle gerber files in subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create nested gerber structure
            gerber_dir = tmpdir_path / "gerbers"
            gerber_dir.mkdir()
            subdir = gerber_dir / "layer"
            subdir.mkdir()
            gerber_file = subdir / "design.gbr"
            gerber_file.write_text("Gerber in subdirectory")

            # Package it
            archive_path = tmpdir_path / "output.zip"
            packager = GerberPackager()
            packager.package([gerber_file], archive_path)

            # Verify in archive
            with zipfile.ZipFile(archive_path, "r") as z:
                names = z.namelist()
                assert any("design.gbr" in name for name in names)

            # Verify cleanup - entire gerber directory should be removed
            assert (
                not gerber_dir.exists()
            ), f"Gerber directory still exists: {gerber_dir}"

    def test_package_creates_parent_archive_directory(self) -> None:
        """GerberPackager should create parent directories of archive path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create gerber file
            gerber_dir = tmpdir_path / "gerbers"
            gerber_dir.mkdir()
            gerber_file = gerber_dir / "design.gbr"
            gerber_file.write_text("Gerber")

            # Archive to nested path
            archive_path = tmpdir_path / "deep" / "nested" / "output.zip"
            packager = GerberPackager()
            packager.package([gerber_file], archive_path)

            # Verify archive created in nested location
            assert archive_path.exists()
            assert archive_path.parent.exists()
