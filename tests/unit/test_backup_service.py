"""Unit tests for BackupService."""

from __future__ import annotations

import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from jbom.services.backup_service import BackupService


class TestBackupService:
    """Tests for BackupService."""

    def test_backup_single_artifact(self) -> None:
        """BackupService should create backup archive for single artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a production artifact
            artifact = tmpdir_path / "jbom.csv"
            artifact.write_text("BOM data")

            # Create backup
            backup_dir = tmpdir_path / "backups"
            service = BackupService()
            result = service.backup([artifact], backup_dir, "project_1.0")

            # Verify backup was created
            assert result.exists()
            assert backup_dir.exists()
            assert "project_1.0" in result.name
            assert result.name.endswith(".zip")

            # Verify archive contents
            with zipfile.ZipFile(result, "r") as z:
                names = z.namelist()
                assert any("jbom.csv" in name for name in names)

    def test_backup_multiple_artifacts(self) -> None:
        """BackupService should backup multiple artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create multiple artifacts
            artifact1 = tmpdir_path / "jbom.csv"
            artifact1.write_text("BOM")
            artifact2 = tmpdir_path / "cpl.csv"
            artifact2.write_text("POS")
            artifact3 = tmpdir_path / "gerbers.zip"
            artifact3.write_text("Gerbers")

            # Create backup
            backup_dir = tmpdir_path / "backups"
            service = BackupService()
            result = service.backup(
                [artifact1, artifact2, artifact3],
                backup_dir,
                "project_1.0",
            )

            # Verify all artifacts in backup
            with zipfile.ZipFile(result, "r") as z:
                names = z.namelist()
                assert any("jbom.csv" in name for name in names)
                assert any("cpl.csv" in name for name in names)
                assert any("gerbers.zip" in name for name in names)

    def test_backup_creates_backup_directory(self) -> None:
        """BackupService should create backup directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create artifact
            artifact = tmpdir_path / "jbom.csv"
            artifact.write_text("BOM")

            # Backup to non-existent directory
            backup_dir = tmpdir_path / "deep" / "nested" / "backups"
            service = BackupService()
            result = service.backup([artifact], backup_dir, "project_1.0")

            # Verify directory was created
            assert backup_dir.exists()
            assert result.exists()

    def test_backup_timestamp_format(self) -> None:
        """BackupService should use YYYY-MM-DD_HH-MM-SS timestamp format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            artifact = tmpdir_path / "jbom.csv"
            artifact.write_text("BOM")

            backup_dir = tmpdir_path / "backups"
            service = BackupService()
            result = service.backup([artifact], backup_dir, "project_1.0")

            # Extract timestamp from filename
            # Format: project_1.0_YYYY-MM-DD_HH-MM-SS.zip
            filename = result.name
            assert filename.startswith("project_1.0_")
            assert filename.endswith(".zip")

            # Verify timestamp is valid
            timestamp_part = filename[len("project_1.0_") : -len(".zip")]
            # Parse timestamp to verify format
            parsed = datetime.strptime(timestamp_part, "%Y-%m-%d_%H-%M-%S")
            assert isinstance(parsed, datetime)

    def test_backup_raises_on_empty_artifacts(self) -> None:
        """BackupService should raise ValueError on empty artifact_paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            backup_dir = tmpdir_path / "backups"

            service = BackupService()
            with pytest.raises(ValueError, match="artifact_paths cannot be empty"):
                service.backup([], backup_dir, "project_1.0")

    def test_backup_raises_on_empty_stem(self) -> None:
        """BackupService should raise ValueError on empty archive_stem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            artifact = tmpdir_path / "jbom.csv"
            artifact.write_text("BOM")
            backup_dir = tmpdir_path / "backups"

            service = BackupService()
            with pytest.raises(ValueError, match="archive_stem cannot be empty"):
                service.backup([artifact], backup_dir, "")

    def test_backup_raises_on_whitespace_stem(self) -> None:
        """BackupService should raise ValueError on whitespace-only archive_stem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            artifact = tmpdir_path / "jbom.csv"
            artifact.write_text("BOM")
            backup_dir = tmpdir_path / "backups"

            service = BackupService()
            with pytest.raises(ValueError, match="archive_stem cannot be empty"):
                service.backup([artifact], backup_dir, "   ")

    def test_backup_raises_on_missing_artifact(self) -> None:
        """BackupService should raise FileNotFoundError if artifact doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            nonexistent = tmpdir_path / "nonexistent.csv"
            backup_dir = tmpdir_path / "backups"

            service = BackupService()
            with pytest.raises(FileNotFoundError):
                service.backup([nonexistent], backup_dir, "project_1.0")

    def test_backup_returns_path(self) -> None:
        """BackupService.backup should return the backup archive path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            artifact = tmpdir_path / "jbom.csv"
            artifact.write_text("BOM")
            backup_dir = tmpdir_path / "backups"

            service = BackupService()
            result = service.backup([artifact], backup_dir, "project_1.0")

            assert isinstance(result, Path)
            assert result.exists()
            assert result.name.endswith(".zip")

    def test_backup_multiple_calls_create_different_archives(self) -> None:
        """BackupService should create timestamped archives for multiple calls."""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            artifact = tmpdir_path / "jbom.csv"
            artifact.write_text("BOM")
            backup_dir = tmpdir_path / "backups"

            service = BackupService()

            # Create first backup
            result1 = service.backup([artifact], backup_dir, "project_1.0")

            # Delay to ensure different timestamp (must be at least 1 second)
            time.sleep(1.1)

            # Create second backup
            result2 = service.backup([artifact], backup_dir, "project_1.0")

            # Both should exist and have different names
            assert result1.exists()
            assert result2.exists()
            assert (
                result1.name != result2.name
            ), f"Expected different names but got {result1.name} and {result2.name}"
            assert backup_dir.exists()

    def test_backup_stem_with_special_chars(self) -> None:
        """BackupService should handle archive stems with valid characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            artifact = tmpdir_path / "jbom.csv"
            artifact.write_text("BOM")
            backup_dir = tmpdir_path / "backups"

            service = BackupService()
            result = service.backup([artifact], backup_dir, "project-name_v1.0")

            assert result.exists()
            assert "project-name_v1.0" in result.name

    def test_backup_with_nested_artifact_paths(self) -> None:
        """BackupService should handle artifacts in nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create artifacts in nested structure
            production_dir = tmpdir_path / "production"
            production_dir.mkdir()
            artifact1 = production_dir / "jbom.csv"
            artifact1.write_text("BOM")

            backups_dir = production_dir / "backups"

            service = BackupService()
            result = service.backup([artifact1], backups_dir, "project_1.0")

            # Verify backup created in correct location
            assert backups_dir.exists()
            # Use resolved paths to handle symlink differences on macOS
            assert result.parent.resolve() == backups_dir.resolve()
            assert result.exists()
