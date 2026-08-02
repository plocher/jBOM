"""PCB domain models for jBOM (initial skeleton).

These dataclasses represent loaded PCB footprints and board metadata.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class PadLocal:
    """One copper pad in footprint-local millimetres.

    Coordinates are relative to the footprint anchor ``(at x y [rot])``,
    matching KiCad's on-disk pad ``(at …)`` values before board placement.
    """

    x_mm: float
    y_mm: float
    rotation_deg: float = 0.0
    width_mm: float = 0.0
    height_mm: float = 0.0
    name: str = ""
    pad_type: str = ""


@dataclass
class PcbComponent:
    reference: str
    footprint_name: str
    package_token: str
    center_x_mm: float
    center_y_mm: float
    rotation_deg: float
    side: str  # 'TOP' | 'BOTTOM'
    # Raw text tokens as they appeared in the KiCad file (if available)
    center_x_raw: Optional[str] = None
    center_y_raw: Optional[str] = None
    rotation_raw: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    # Footprint-local pad centres used for THT pad-bbox placement (FT parity).
    pads: Tuple[PadLocal, ...] = ()


@dataclass
class BoardModel:
    path: Path
    footprints: List[PcbComponent] = field(default_factory=list)
    title: str = ""
    kicad_version: Optional[str] = None
    board_origin_mm: Optional[tuple[float, float]] = None
    aux_origin_mm: Optional[tuple[float, float]] = None
    grid_origin_mm: Optional[tuple[float, float]] = None
