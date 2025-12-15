"""Schematic-focused API surface for jBOM.

This package re-exports the existing schematic/BOM API from jbom.jbom to
provide a stable location parallel to the future PCB modules (src/jbom/pcb).

Phase P0: thin shims only (no behavior changes).
"""

from .api import GenerateOptions, generate_bom_api
from .model import Component
from .bom import BOMEntry, BOMGenerator
from .parser import KiCadParser

__all__ = [
    "GenerateOptions",
    "generate_bom_api",
    "Component",
    "BOMEntry",
    "BOMGenerator",
    "KiCadParser",
]
