"""Common discovery helpers for CLI default behaviors.

This module centralizes heuristics for finding KiCad artifacts in a working
directory so individual commands (POS, BOM, etc.) can share the logic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple
import sys

PROJECT_EXTS = (".kicad_pro", ".pro")
SCHEMATIC_EXTS = (".kicad_sch", ".sch")
PCB_EXTS = (".kicad_pcb",)


def find_project(cwd: Path) -> Optional[Path]:
    """Return a KiCad project file (.kicad_pro or legacy .pro) if present.

    If multiple exist, prefer .kicad_pro over .pro and then the lexicographically
    first file for stable behavior.
    """
    projects = [p for p in cwd.iterdir() if p.is_file() and p.suffix in PROJECT_EXTS]
    if not projects:
        return None
    # Prefer .kicad_pro
    pro_new = sorted(p for p in projects if p.suffix == ".kicad_pro")
    if pro_new:
        return pro_new[0]
    return sorted(projects)[0]


def find_pcb(cwd: Path) -> Optional[Path]:
    """Find the best .kicad_pcb in cwd using stable, user-friendly heuristics.

    Heuristics adapted from original jBOM:
    - Prefer non-autosave files.
    - Prefer file whose stem matches the directory name.
    - If only autosave files exist, warn and choose matching autosave first.
    - Fall back to lexicographically first file.
    """
    if not cwd.is_dir():
        return None

    pcb_files = list(cwd.glob("*.kicad_pcb"))
    if not pcb_files:
        # mirror original behavior: print helpful message to stderr
        print(f"No .kicad_pcb file found in {cwd}", file=sys.stderr)
        return None

    normal = [f for f in pcb_files if not f.name.startswith("_autosave-")]
    autosave = [f for f in pcb_files if f.name.startswith("_autosave-")]

    dir_name = cwd.name

    # Prefer normal files that match directory name
    matching_normal = [f for f in normal if f.stem == dir_name]
    if matching_normal:
        return matching_normal[0]

    # Any normal file
    if normal:
        return sorted(normal)[0]

    # Fall back to autosave with warning
    if autosave:
        print(
            f"WARNING: Only autosave PCB files found in {cwd}. Using autosave file (may be incomplete).",
            file=sys.stderr,
        )
        matching_autosave = [f for f in autosave if f.stem == f"_autosave-{dir_name}"]
        if matching_autosave:
            return matching_autosave[0]
        return sorted(autosave)[0]

    return None


def find_schematic(cwd: Path) -> Optional[Path]:
    """Find a KiCad schematic file (.kicad_sch or legacy .sch)."""
    sch = [p for p in cwd.iterdir() if p.is_file() and p.suffix in SCHEMATIC_EXTS]
    return sorted(sch)[0] if sch else None


def find_project_and_pcb(cwd: Path) -> Tuple[Optional[Path], Optional[Path]]:
    """Convenience wrapper returning (project, pcb)."""
    return (find_project(cwd), find_pcb(cwd))


def default_output_name(
    cwd: Path, project: Optional[Path], stem_source: Path, suffix: str
) -> Path:
    """Compute default output filename inside cwd using project or a source path.

    Example: suffix="pos.csv" -> <project>.pos.csv or <stem_source>.pos.csv
    """
    base = (project.stem if project else stem_source.stem) + "." + suffix
    return cwd / base
