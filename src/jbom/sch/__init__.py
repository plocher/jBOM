"""Schematic-focused API surface for jBOM.

Re-exports schematic/BOM API from jbom.jbom for convenience.
This allows imports like: from jbom.sch import Component, BOMGenerator
"""

from ..jbom import (
    GenerateOptions,
    generate_bom_api,
    Component,
    BOMEntry,
    BOMGenerator,
    KiCadParser,
)

__all__ = [
    "GenerateOptions",
    "generate_bom_api",
    "Component",
    "BOMEntry",
    "BOMGenerator",
    "KiCadParser",
]
