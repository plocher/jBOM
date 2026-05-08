"""BackupService for creating dated backup archives of production artifacts.

Archives production artifacts (BOM, POS, gerbers) into dated backup files
stored in production/backups/ directory with timestamp naming.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Sequence

from jbom.services.zip_archiver import ZipArchiver


class BackupService:
    """Service for creating dated backup archives of production artifacts.

    Archives explicit production artifact paths into dated backup archives
    stored in a backups subdirectory with timestamps.
    """

    def __init__(self) -> None:
        """Initialize the BackupService."""
        self._zip_archiver = ZipArchiver()

    def backup(
        self,
        artifact_paths: Sequence[Path],
        backup_dir: Path,
        archive_stem: str,
    ) -> Path:
        """Create a dated backup archive of production artifacts.

        Archives the provided artifact paths into a timestamped ZIP file
        in the backup directory. The archive filename is constructed as:
        `{archive_stem}_{YYYY-MM-DD_HH-MM-SS}.zip`

        Args:
            artifact_paths: Sequence of Path objects (production artifacts) to backup
            backup_dir: Directory where backup archive will be created (e.g., production/backups/)
            archive_stem: Base name for the archive (e.g., "cpNode_1.0"), without .zip extension

        Returns:
            Path to the created backup archive

        Raises:
            ValueError: If artifact_paths is empty or archive_stem is empty
            FileNotFoundError: If any artifact path doesn't exist
            OSError: If backup creation fails
        """
        if not artifact_paths:
            raise ValueError("artifact_paths cannot be empty")

        if not archive_stem or not archive_stem.strip():
            raise ValueError("archive_stem cannot be empty")

        # Validate all artifacts exist
        artifact_paths_list = [Path(p).resolve() for p in artifact_paths]
        if not all(p.exists() for p in artifact_paths_list):
            missing = [p for p in artifact_paths_list if not p.exists()]
            raise FileNotFoundError(
                f"One or more artifact paths do not exist: {missing}"
            )

        # Create backup directory if needed
        backup_dir_path = Path(backup_dir).resolve()
        backup_dir_path.mkdir(parents=True, exist_ok=True)

        # Generate timestamp for archive name
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archive_filename = f"{archive_stem}_{timestamp}.zip"
        archive_path = backup_dir_path / archive_filename

        # Create the backup archive
        self._zip_archiver.archive(artifact_paths_list, archive_path)

        return archive_path


__all__ = ["BackupService"]
