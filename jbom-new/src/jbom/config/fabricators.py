"""Fabricator configuration loader.

Loads fabricator definitions from built-in config files.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml


@dataclass
class FabricatorConfig:
    """Configuration for a PCB fabricator.

    Defines column mappings, part number preferences, presets, and CLI aliases
    for fabricator-specific BOM and position file generation.
    """

    id: str
    name: str
    pos_columns: Dict[str, str]  # Header -> internal field mapping
    description: Optional[str] = None
    bom_columns: Optional[Dict[str, str]] = None  # Header -> internal field mapping
    part_number: Optional[Dict[str, Any]] = None  # Part number configuration
    presets: Optional[Dict[str, Any]] = None  # Field presets
    cli_aliases: Optional[Dict[str, List[str]]] = None  # CLI flags and presets
    pcb_manufacturing: Optional[Dict[str, Any]] = None  # Manufacturing info
    pcb_assembly: Optional[Dict[str, Any]] = None  # Assembly info
    website: Optional[str] = None  # Fabricator website


_BUILTIN_DIR = Path(__file__).parent / "fabricators"


def list_fabricators() -> list[str]:
    """List available fabricator IDs by scanning config directory.

    Returns:
        Sorted list of fabricator IDs (config filenames without .fab.yaml)
    """
    if not _BUILTIN_DIR.exists():
        return []
    return sorted(p.stem.replace(".fab", "") for p in _BUILTIN_DIR.glob("*.fab.yaml"))


def get_available_fabricators() -> list[str]:
    """Get list of available fabricators with fallback for consistency.

    This is the preferred function for CLI and BDD tests to ensure
    consistent fabricator discovery across the codebase.

    Returns:
        List of fabricator IDs, falling back to ["generic"] if none found
    """
    fabricators = list_fabricators()
    return fabricators if fabricators else ["generic"]


def load_fabricator(fid: str) -> FabricatorConfig:
    """Load fabricator configuration from YAML file.

    Args:
        fid: Fabricator ID (filename without .fab.yaml extension)

    Returns:
        FabricatorConfig with all parsed fields

    Raises:
        ValueError: If fabricator not found or missing required fields
    """
    path = _BUILTIN_DIR / f"{fid}.fab.yaml"
    if not path.exists():
        raise ValueError(f"Unknown fabricator: {fid}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Required fields
    pid = data.get("id", fid)
    name = data.get("name", fid)
    pos_columns = data.get("pos_columns", {}) or {}
    if not isinstance(pos_columns, dict) or not pos_columns:
        raise ValueError(f"Fabricator '{fid}' missing pos_columns")

    # Optional fields
    description = data.get("description")
    bom_columns = data.get("bom_columns")
    part_number = data.get("part_number")
    presets = data.get("presets")
    cli_aliases = data.get("cli_aliases")
    pcb_manufacturing = data.get("pcb_manufacturing")
    pcb_assembly = data.get("pcb_assembly")
    website = data.get("website")

    return FabricatorConfig(
        id=pid,
        name=name,
        pos_columns=pos_columns,
        description=description,
        bom_columns=bom_columns,
        part_number=part_number,
        presets=presets,
        cli_aliases=cli_aliases,
        pcb_manufacturing=pcb_manufacturing,
        pcb_assembly=pcb_assembly,
        website=website,
    )


def headers_for_fields(fab: Optional[FabricatorConfig], fields: list[str]) -> list[str]:
    """Map internal field names to headers using fabricator mapping when available.

    If a fabricator is active, use its headers (reverse map). Otherwise use defaults.
    """
    # Default header mapping to match legacy format
    default_headers = {
        "reference": "Designator",
        "value": "Val",
        "package": "Package",
        "footprint": "Footprint",
        "x": "Mid X",
        "y": "Mid Y",
        "rotation": "Rotation",
        "side": "Layer",
        "smd": "SMD",
    }

    if fab:
        # reverse map internal -> header, prefer first occurrence order in fab file
        rev: Dict[str, str] = {}
        for header, internal in fab.pos_columns.items():
            rev.setdefault(internal, header)
        # Use fabricator mapping, falling back to defaults for unmapped fields
        return [rev.get(f, default_headers.get(f, f)) for f in fields]

    return [default_headers.get(f, f) for f in fields]
