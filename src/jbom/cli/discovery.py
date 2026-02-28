"""CLI discovery functions for KiCad project files.

Provides functions to find KiCad v6+ project files (`*.kicad_pro`),
schematic files (`*.kicad_sch`), and PCB files (`*.kicad_pcb`) in directories.
Handles autosave files and directory name matching preferences.
"""

import sys
from pathlib import Path
from typing import Optional, Tuple

__all__ = [
    "find_project",
    "find_pcb",
    "find_schematic",
    "find_project_and_pcb",
    "default_output_name",
]


def find_project(search_dir: Path) -> Optional[Path]:
    """Find the single KiCad v6+ project file in a directory.

    Returns the project file only if exactly one `*.kicad_pro` exists.

    Args:
        search_dir: Directory to search in

    Returns:
        Path to the single `*.kicad_pro` file, or None if not found.

    Raises:
        ValueError: If multiple `*.kicad_pro` files are found.
    """
    if not search_dir.is_dir():
        return None

    kicad_pro_files = sorted(search_dir.glob("*.kicad_pro"))
    if not kicad_pro_files:
        return None

    if len(kicad_pro_files) > 1:
        raise ValueError(
            f"Multiple project files found in {search_dir}: {len(kicad_pro_files)}"
        )

    return kicad_pro_files[0]


def find_pcb(search_dir: Path) -> Optional[Path]:
    """Find the best PCB file in a directory.

    Args:
        search_dir: Directory to search in

    Returns:
        Path to .kicad_pcb file, or None if not found
    """
    if not search_dir.is_dir():
        return None

    # Find all PCB files
    pcb_files = list(search_dir.glob("*.kicad_pcb"))
    if not pcb_files:
        return None

    # Separate autosave and normal files
    normal_files = [f for f in pcb_files if not f.name.startswith("_autosave-")]
    autosave_files = [f for f in pcb_files if f.name.startswith("_autosave-")]

    dir_name = search_dir.name

    # Prefer normal files that match directory name
    matching_normal = [f for f in normal_files if f.stem == dir_name]
    if matching_normal:
        return matching_normal[0]

    # Use any normal file
    if normal_files:
        return sorted(normal_files)[0]

    # Fall back to autosave files with warning
    if autosave_files:
        print(
            f"WARNING: Only autosave PCB files found in {search_dir}. Using autosave file (may be incomplete).",
            file=sys.stderr,
        )
        matching_autosave = [
            f for f in autosave_files if f.stem == f"_autosave-{dir_name}"
        ]
        if matching_autosave:
            return matching_autosave[0]
        return sorted(autosave_files)[0]

    return None


def find_schematic(search_dir: Path) -> Optional[Path]:
    """Find the best schematic file in a directory.

    Args:
        search_dir: Directory to search in

    Returns:
        Path to .kicad_sch file, or None if not found
    """
    if not search_dir.is_dir():
        return None

    schematic_files = list(search_dir.glob("*.kicad_sch"))
    if not schematic_files:
        return None

    # Separate autosave and normal files
    normal_files = [f for f in schematic_files if not f.name.startswith("_autosave-")]
    autosave_files = [f for f in schematic_files if f.name.startswith("_autosave-")]

    dir_name = search_dir.name

    # Prefer normal files that match directory name
    matching_normal = [f for f in normal_files if f.stem == dir_name]
    if matching_normal:
        return matching_normal[0]

    # Use any normal file
    if normal_files:
        return sorted(normal_files)[0]

    # Fall back to autosave files with warning
    if autosave_files:
        print(
            f"WARNING: Only autosave schematic files found in {search_dir}. Using autosave file (may be incomplete).",
            file=sys.stderr,
        )
        matching_autosave = [
            f for f in autosave_files if f.stem == f"_autosave-{dir_name}"
        ]
        if matching_autosave:
            return matching_autosave[0]
        return sorted(autosave_files)[0]

    return None


def find_project_and_pcb(search_dir: Path) -> Tuple[Optional[Path], Optional[Path]]:
    """Find both project and PCB files in a directory.

    Args:
        search_dir: Directory to search in

    Returns:
        Tuple of (project_file, pcb_file) - either may be None
    """
    project = find_project(search_dir)
    pcb = find_pcb(search_dir)
    return project, pcb


def default_output_name(
    search_dir: Path, project: Optional[Path], pcb: Optional[Path], suffix: str
) -> Path:
    """Generate default output filename based on project context.

    Args:
        search_dir: Directory being searched
        project: Project file found (or None)
        pcb: PCB file found (or None)
        suffix: File suffix to append (e.g., "pos.csv")

    Returns:
        Path for default output file
    """
    # Use project name if available
    if project:
        base_name = project.stem
    # Use PCB name if available
    elif pcb:
        base_name = pcb.stem
    # Fall back to directory name
    else:
        base_name = search_dir.name

    return search_dir / f"{base_name}.{suffix}"
