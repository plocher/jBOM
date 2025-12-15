"""Options dataclasses for generators.

Provides typed configuration options for BOM and placement generators.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal, Optional

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
    fields: Optional[List[str]] = None


@dataclass
class BOMOptions(GeneratorOptions):
    """Options specific to BOM generation."""
    smd_only: bool = False


@dataclass
class PlacementOptions(GeneratorOptions):
    """Options specific to placement/CPL generation."""
    units: Literal['mm', 'inch'] = 'mm'
    origin: Literal['board', 'aux'] = 'board'
    smd_only: bool = True
    layer_filter: Optional[Literal['TOP', 'BOTTOM']] = None
