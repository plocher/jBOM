"""PCB domain models for jBOM (initial skeleton).

These dataclasses represent loaded PCB footprints and board metadata.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class PcbComponent:
    reference: str
    footprint_name: str
    package_token: str
    center_x_mm: float
    center_y_mm: float
    rotation_deg: float
    side: str  # 'TOP' | 'BOTTOM'
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class BoardModel:
    path: Path
    footprints: List[PcbComponent] = field(default_factory=list)
    title: str = ""
    kicad_version: Optional[str] = None
    board_origin_mm: Optional[tuple[float, float]] = None
    aux_origin_mm: Optional[tuple[float, float]] = None
