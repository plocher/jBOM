"""Common discovery helpers for CLI default behaviors.

This module centralizes heuristics for finding KiCad artifacts in a working
directory so individual commands (POS, BOM, etc.) can share the logic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

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
    """Find a KiCad PCB file (.kicad_pcb) in the directory, if any.

    If multiple, pick the lexicographically first for stability.
    """
    pcbs = [p for p in cwd.iterdir() if p.is_file() and p.suffix in PCB_EXTS]
    return sorted(pcbs)[0] if pcbs else None


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
