"""Options dataclasses for generators.

Provides typed configuration options for BOM and placement generators.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Set

__all__ = [
    "GeneratorOptions",
    "BOMOptions",
    "PlacementOptions",
]


@dataclass
class GeneratorOptions:
    """Base options for all generators."""

    verbose: bool = False
    debug: bool = False
    debug_categories: Set[str] = field(default_factory=set)
    fields: Optional[List[str]] = None


@dataclass
class BOMOptions(GeneratorOptions):
    """Options specific to BOM generation."""

    smd_only: bool = False


@dataclass
class PlacementOptions(GeneratorOptions):
    """Options specific to placement/CPL generation.

    Attributes:
        origin: Coordinate origin. ``"board"`` uses absolute KiCad coordinates;
            ``"aux"`` subtracts the board's auxiliary origin (``aux_axis_origin``,
            falling back to ``(0, 0)`` when unset — matching pcbnew
            ``GetAuxOrigin()``).
        y_direction: ``"up"`` keeps KiCad internal Y (increases down on disk,
            reported as-is). ``"down"`` negates Y after origin subtraction so
            place-file Mid Y matches Fabrication-Toolkit / industry CPL output
            (Y increases upward from the origin).
        position_mode: ``"anchor"`` uses the footprint ``(at …)`` position.
            ``"auto"`` mirrors Fabrication-Toolkit: SMD → anchor, through-hole
            → centre of pad bounding box (pad centres). ``"pad_center"`` always
            uses the pad-centre bbox when pads are present.
        smd_only: When True, emit only SMD footprints.
        layer_filter: Optional TOP/BOTTOM filter.
    """

    origin: Literal["board", "aux"] = "board"
    y_direction: Literal["up", "down"] = "up"
    position_mode: Literal["anchor", "auto", "pad_center"] = "anchor"
    smd_only: bool = True
    layer_filter: Optional[Literal["TOP", "BOTTOM"]] = None
