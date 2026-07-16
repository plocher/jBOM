"""DesignSourcePackager for archiving KiCad project source files.

Creates a ZIP archive containing design-source files (project, schematic,
PCB, and related KiCad metadata) from a project directory. Intended for
embedding into fabrication provenance backups.
"""

from __future__ import annotations

import zipfile
from pathlib import Path


class DesignSourcePackager:
    """Package KiCad design-source files from a project directory."""

    _SOURCE_SUFFIXES: tuple[str, ...] = (
        ".kicad_pro",
        ".kicad_prl",
        ".kicad_sch",
        ".kicad_pcb",
        ".kicad_dru",
    )
    _OPTIONAL_FILES: tuple[str, ...] = (
        "fabrication-toolkit-options.json",
        ".jbom/jbom-options.json",
    )

    def package(self, project_dir: Path, archive_path: Path) -> Path:
        """Create a design-source archive from *project_dir*.

        Args:
            project_dir: KiCad project directory to snapshot.
            archive_path: Destination path for the ZIP archive.

        Returns:
            Path to the created archive.

        Raises:
            ValueError: If project_dir does not exist or no source files found.
            OSError: If archive creation fails.
        """
        project_dir = Path(project_dir).resolve()
        if not project_dir.is_dir():
            raise ValueError(f"project_dir is not a directory: {project_dir}")

        source_files = self._collect_source_files(project_dir)
        if not source_files:
            raise ValueError(f"No design-source files found in {project_dir}")

        archive_path = Path(archive_path).resolve()
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_files:
                arcname = str(file_path.relative_to(project_dir))
                zipf.write(file_path, arcname=arcname)

        return archive_path

    def _collect_source_files(self, project_dir: Path) -> list[Path]:
        """Collect design-source files to archive from *project_dir*."""
        collected: list[Path] = []
        seen: set[Path] = set()

        for file_path in sorted(project_dir.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.suffix not in self._SOURCE_SUFFIXES:
                continue
            resolved = file_path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            collected.append(resolved)

        for relative_name in self._OPTIONAL_FILES:
            candidate = (project_dir / relative_name).resolve()
            if candidate.is_file() and candidate not in seen:
                seen.add(candidate)
                collected.append(candidate)

        return sorted(collected)


__all__ = ["DesignSourcePackager"]
