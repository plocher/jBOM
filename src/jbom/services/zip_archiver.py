"""ZipArchiver service for creating ZIP archives from path lists.

This service provides a simple, dependency-free packaging primitive
that accepts an explicit list of source paths and creates a ZIP archive.
It has no knowledge of what the files are—purely packaging.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Sequence


class ZipArchiver:
    """Service for archiving explicit path lists into ZIP files.

    Archives paths with relative directory structure preserved.
    Raises ValueError on empty input. Creates parent directories
    of the archive path automatically.
    """

    def archive(
        self,
        source_paths: Sequence[Path],
        archive_path: Path,
    ) -> None:
        """Create a ZIP archive from an explicit list of source paths.

        Args:
            source_paths: Sequence of Path objects (files or directories) to archive
            archive_path: Destination ZIP file path

        Raises:
            ValueError: If source_paths is empty
            OSError: If archive creation fails (e.g., permission denied)
            FileNotFoundError: If a source path doesn't exist

        Note:
            - Creates parent directories of archive_path if needed
            - Preserves relative directory structure within the archive
            - Single files archive with their basename; directories archive with relative structure
            - Raises ValueError if source_paths is empty
        """
        if not source_paths:
            raise ValueError("source_paths cannot be empty")

        # Ensure parent directory exists
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        # Collect all files to archive (handling both files and directories)
        files_to_archive: list[tuple[Path, str]] = []  # (file_path, arcname)
        for source in source_paths:
            source_path = Path(source).resolve()

            if not source_path.exists():
                raise FileNotFoundError(f"Source path does not exist: {source_path}")

            if source_path.is_file():
                # Archive single file with just its basename
                files_to_archive.append((source_path, source_path.name))
            elif source_path.is_dir():
                # Archive all files in directory, preserving structure relative to dir parent
                for file_in_dir in source_path.rglob("*"):
                    if file_in_dir.is_file():
                        # Preserve structure: source_path/subdir/file.txt -> subdir/file.txt
                        rel_path = file_in_dir.relative_to(source_path)
                        arcname = str(rel_path)
                        files_to_archive.append((file_in_dir, arcname))

        if not files_to_archive:
            raise ValueError(
                "No files found in source paths (all sources were empty directories)"
            )

        # Create the archive
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path, arcname in files_to_archive:
                zipf.write(file_path, arcname=arcname)


__all__ = ["ZipArchiver"]
