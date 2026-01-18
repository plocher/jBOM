"""Fabricator configuration loader.

Loads fabricator definitions from built-in config files.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import yaml


@dataclass
class FabricatorConfig:
    id: str
    name: str
    pos_columns: Dict[str, str]  # Header -> internal field mapping


_BUILTIN_DIR = Path(__file__).parent / "fabricators"


def list_fabricators() -> list[str]:
    if not _BUILTIN_DIR.exists():
        return []
    return sorted(p.stem.replace(".fab", "") for p in _BUILTIN_DIR.glob("*.fab.yaml"))


def load_fabricator(fid: str) -> FabricatorConfig:
    path = _BUILTIN_DIR / f"{fid}.fab.yaml"
    if not path.exists():
        raise ValueError(f"Unknown fabricator: {fid}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    pid = data.get("id", fid)
    name = data.get("name", fid)
    pos_columns = data.get("pos_columns", {}) or {}
    if not isinstance(pos_columns, dict) or not pos_columns:
        raise ValueError(f"Fabricator '{fid}' missing pos_columns")
    return FabricatorConfig(id=pid, name=name, pos_columns=pos_columns)


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
