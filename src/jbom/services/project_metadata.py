"""ProjectMetadata service for extracting and managing project-level metadata.

This service extracts title block metadata from KiCad project files (schematic and PCB)
and provides helper utilities for archive naming and metadata provenance tracking.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from jbom.common.types import TitleBlockMetadata
from jbom.services.pcb_reader import DefaultKiCadReaderService
from jbom.services.schematic_reader import SchematicReader


@dataclass(frozen=True)
class ProjectMetadata:
    """Extracted project metadata with provenance tracking.

    Stores project name and title block metadata from both schematic and PCB sources.
    Both metadata objects are independent; downstream code decides which to use for
    artifact naming (e.g., FabricationWorkflow uses pcb_metadata for gerber archives).
    """

    project_name: str
    """Project name, typically derived from .kicad_pro basename or title block."""

    pcb_metadata: Optional[TitleBlockMetadata]
    """Title block metadata extracted from PCB file, if available."""

    schematic_metadata: Optional[TitleBlockMetadata]
    """Title block metadata extracted from schematic file, if available."""

    release_timestamp: datetime
    """Wall-clock timestamp when metadata was captured."""


def normalize_archive_stem(name: str) -> str:
    """Normalize a string for use in archive filenames.

    Converts spaces to underscores and removes special characters, preserving
    alphanumerics, hyphens, and underscores.

    Args:
        name: String to normalize (typically project name or title)

    Returns:
        Normalized string suitable for use as archive filename stem
    """
    if not name:
        return "archive"

    # Convert spaces to underscores
    normalized = name.replace(" ", "_")

    # Keep only alphanumerics, hyphens, underscores
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "", normalized)

    # Collapse multiple consecutive underscores to one, but preserve hyphens
    normalized = re.sub(r"_+", "_", normalized)

    # Remove leading/trailing underscores (but not hyphens)
    normalized = normalized.strip("_")

    return normalized if normalized else "archive"


def create_metadata(
    project_file: Path,
    pcb_file: Optional[Path] = None,
    schematic_file: Optional[Path] = None,
) -> ProjectMetadata:
    """Create ProjectMetadata by extracting metadata from project files.

    Reads title block metadata from PCB and/or schematic files and combines them
    with a derived project name. The project name falls back to .kicad_pro basename
    if title blocks don't provide one.

    Args:
        project_file: Path to .kicad_pro file
        pcb_file: Optional path to .kicad_pcb file
        schematic_file: Optional path to .kicad_sch file

    Returns:
        ProjectMetadata with extracted and derived information

    Raises:
        FileNotFoundError: If project_file doesn't exist
        ValueError: If metadata extraction fails
    """
    if not project_file.exists():
        raise FileNotFoundError(f"Project file not found: {project_file}")

    # Extract project name from .kicad_pro basename
    project_name = project_file.stem

    # Extract metadata from PCB if available
    pcb_metadata: Optional[TitleBlockMetadata] = None
    if pcb_file and pcb_file.exists():
        try:
            reader = DefaultKiCadReaderService()
            pcb_metadata = reader.read_metadata(pcb_file)
        except Exception:
            # Silently continue if PCB metadata extraction fails
            pass

    # Extract metadata from schematic if available
    schematic_metadata: Optional[TitleBlockMetadata] = None
    if schematic_file and schematic_file.exists():
        try:
            reader = SchematicReader()
            schematic_metadata = reader.read_metadata(schematic_file)
        except Exception:
            # Silently continue if schematic metadata extraction fails
            pass

    # Use PCB title if available, otherwise schematic title, otherwise project_name
    if pcb_metadata and pcb_metadata.title:
        project_name = pcb_metadata.title
    elif schematic_metadata and schematic_metadata.title:
        project_name = schematic_metadata.title

    return ProjectMetadata(
        project_name=project_name,
        pcb_metadata=pcb_metadata,
        schematic_metadata=schematic_metadata,
        release_timestamp=datetime.now(),
    )


DEFAULT_ARCHIVE_TEMPLATE = "${TITLE}_${REVISION}"


def _normalize_archive_filename_stem(value: str) -> str:
    """Filename-safe normaliser that preserves dots (e.g. revision ``1.0``).

    Mirrors the plugin dialog's ``_normalise`` helper so the CLI and plugin
    produce identical archive stems.  Replaces unsafe characters with an
    underscore, keeps word characters, dots, and hyphens; strips leading /
    trailing underscores.
    """

    return re.sub(r"[^\w.-]", "_", str(value or "")).strip("_")


def expand_archive_template(
    template: str,
    pcb_file: Optional[Path],
) -> str:
    """Expand KiCad title-block variables in *template* against a PCB file.

    Mirrors the plugin's archive-name expansion so the CLI and plugin produce
    identical stems for the same project.  Resolves ``${TITLE}``,
    ``${REVISION}``, ``${DATE}`` / ``${ISSUE_DATE}``, ``${CURRENT_DATE}``, and
    ``${COMPANY}`` from the PCB title block (read via the file-based S-expr
    parser, so no KiCad SWIG bindings are required).

    Fallback order when the template expands to an empty / unusable stem:

    1. The PCB filename stem (e.g. ``cpNode-Xiao-68x90``) — only when the
       PCB file actually exists on disk.
    2. The literal string ``"(unknown)"``.

    Args:
        template: Template string.  When empty, ``DEFAULT_ARCHIVE_TEMPLATE``
            (``"${TITLE}_${REVISION}"``) is used.
        pcb_file: Optional path to the PCB; when ``None`` or missing, returns
            ``"(unknown)"``.

    Returns:
        Filename-safe archive-name stem.  Preserves dots so semantic
        revisions like ``1.0`` survive normalisation.
    """

    effective_template = template if template else DEFAULT_ARCHIVE_TEMPLATE
    if pcb_file is not None and pcb_file.exists():
        try:
            from jbom.services.text_variable_expander import expand_text_variables

            project_file = pcb_file.parent / f"{pcb_file.parent.name}.kicad_pro"
            metadata = create_metadata(project_file, pcb_file=pcb_file)
            if metadata.pcb_metadata is not None:
                expanded = expand_text_variables(
                    effective_template, metadata.pcb_metadata
                )
                cleaned = _normalize_archive_filename_stem(expanded)
                if cleaned:
                    return cleaned
        except Exception:
            pass
        # PCB exists but title-block expansion yielded nothing usable.
        stem = _normalize_archive_filename_stem(pcb_file.stem)
        if stem:
            return stem
    return "(unknown)"


__all__ = [
    "DEFAULT_ARCHIVE_TEMPLATE",
    "ProjectMetadata",
    "create_metadata",
    "expand_archive_template",
    "normalize_archive_stem",
]
