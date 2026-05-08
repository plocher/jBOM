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


__all__ = [
    "ProjectMetadata",
    "create_metadata",
    "normalize_archive_stem",
]
