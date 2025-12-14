"""jBOM - Intelligent KiCad Bill of Materials Generator

A sophisticated BOM generator for KiCad projects that matches schematic components
against an inventory file (CSV, Excel, or Apple Numbers) to produce fabrication-ready BOMs.
"""

from .__version__ import __version__, __version_info__
from .jbom import (
    Component,
    InventoryItem,
    BOMEntry,
    ComponentType,
    DiagnosticIssue,
    CommonFields,
    KiCadParser,
    InventoryMatcher,
    BOMGenerator,
    GenerateOptions,
    generate_bom_api,
)

__all__ = [
    "__version__",
    "__version_info__",
    "Component",
    "InventoryItem",
    "BOMEntry",
    "ComponentType",
    "DiagnosticIssue",
    "CommonFields",
    "KiCadParser",
    "InventoryMatcher",
    "BOMGenerator",
    "GenerateOptions",
    "generate_bom_api",
]
