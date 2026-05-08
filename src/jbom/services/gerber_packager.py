"""GerberPackager service for archiving gerber artifacts.

Packages explicit gerber artifact paths into a ZIP archive and optionally
removes the intermediate gerber directory after archiving unless debug mode
is enabled.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Sequence

from jbom.services.zip_archiver import ZipArchiver


class GerberPackager:
    """Service for packaging gerber artifacts into archives.

    Accepts explicit paths to gerber artifacts, archives them using ZipArchiver,
    and removes the intermediate directory unless debug mode is enabled.
    """

    def __init__(self) -> None:
        """Initialize the GerberPackager."""
        self._zip_archiver = ZipArchiver()

    def package(
        self,
        artifact_paths: Sequence[Path],
        archive_path: Path,
        *,
        debug: bool = False,
    ) -> Path:
        """Package gerber artifacts into a ZIP archive.

        Archives the provided artifact paths and optionally removes their
        parent directory. If debug mode is enabled, the directory is preserved
        for inspection.

        Args:
            artifact_paths: Sequence of Path objects (gerber files) to archive
            archive_path: Destination ZIP file path
            debug: If True, preserve intermediate gerber directory; if False, remove it

        Returns:
            The archive_path (for convenience chaining)

        Raises:
            ValueError: If artifact_paths is empty
            FileNotFoundError: If any artifact path doesn't exist
            OSError: If archiving or cleanup fails
        """
        if not artifact_paths:
            raise ValueError("artifact_paths cannot be empty")

        # Determine the gerber directory (assumed to be the common parent)
        artifact_paths_list = [Path(p).resolve() for p in artifact_paths]

        if not all(p.exists() for p in artifact_paths_list):
            missing = [p for p in artifact_paths_list if not p.exists()]
            raise FileNotFoundError(
                f"One or more artifact paths do not exist: {missing}"
            )

        # Find common parent directory (gerber directory)
        # Walk up from any single file to find the root gerber directory
        gerber_dir = artifact_paths_list[0].parent
        while gerber_dir.name != "gerbers" and gerber_dir.parent != gerber_dir:
            gerber_dir = gerber_dir.parent
            # Stop if we've gone beyond the actual artifact locations
            if not any(str(p).startswith(str(gerber_dir)) for p in artifact_paths_list):
                # Go back one level
                gerber_dir = gerber_dir.parent
                break

        # Create the archive
        self._zip_archiver.archive(artifact_paths_list, archive_path)

        # Clean up gerber directory unless debug mode
        if not debug and gerber_dir.exists() and gerber_dir.is_dir():
            try:
                shutil.rmtree(gerber_dir)
            except OSError as e:
                raise OSError(f"Failed to remove gerber directory {gerber_dir}: {e}")

        return archive_path


__all__ = ["GerberPackager"]
