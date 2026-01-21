"""Shared workspace/project helpers for Behave steps (DRY).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any


def ensure_dir(base: Path, rel_path: str) -> Path:
    """Ensure a directory exists under base, return absolute Path."""
    p = (base / rel_path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_project(base: Path, name: str) -> Path:
    """Ensure a minimal KiCad project skeleton exists under base/name.

    Creates name.kicad_pro, name.kicad_sch, name.kicad_pcb if missing.
    Uses existing BOM/POS render helpers to avoid duplicating KiCad syntax.
    """
    from . import bom_steps, pos_steps  # lazy import of helpers

    proj_dir = ensure_dir(base, name)

    sch = proj_dir / f"{name}.kicad_sch"
    if not sch.exists():
        # minimal schematic with a single component
        components: List[Dict[str, Any]] = [
            {"Reference": "R1", "Value": "10K", "Footprint": "R_0805_2012"}
        ]
        # Reuse renderer which writes relative to context.project_root; here we write directly
        sch.write_text(
            bom_steps._render_kicad_schematic(name, components), encoding="utf-8"
        )

    pcb = proj_dir / f"{name}.kicad_pcb"
    if not pcb.exists():
        components = [
            {
                "Reference": "U1",
                "X(mm)": "0",
                "Y(mm)": "0",
                "Rotation": "0",
                "Side": "TOP",
                "Footprint": "SOIC-8_3.9x4.9mm",
            }
        ]
        pcb.write_text(pos_steps._render_pcb(name, components), encoding="utf-8")

    pro = proj_dir / f"{name}.kicad_pro"
    if not pro.exists():
        pro.write_text("(kicad_project (version 1))\n", encoding="utf-8")

    return proj_dir


def chdir(context, target: Path) -> None:
    """Change the scenario's project_root to the given absolute path."""
    assert target.exists() and target.is_dir(), f"Directory not found: {target}"
    context.project_root = target
