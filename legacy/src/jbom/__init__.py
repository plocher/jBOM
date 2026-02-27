"""jBOM - Intelligent KiCad Bill of Materials Generator

A sophisticated BOM generator for KiCad projects that matches schematic components
against an inventory file (CSV, Excel, or Apple Numbers) to produce fabrication-ready BOMs.
"""

from .__version__ import __version__, __version_info__

# Import data types
from .common.types import Component, InventoryItem, BOMEntry
from .common.constants import ComponentType, DiagnosticIssue, CommonFields
from .common.fields import normalize_field_name, field_to_header

# Import from v3.0 module structure
from .loaders.schematic import SchematicLoader
from .loaders.inventory import EXCEL_SUPPORT, NUMBERS_SUPPORT
from .generators.bom import BOMGenerator
from .processors.component_types import normalize_component_type
from .processors.inventory_matcher import InventoryMatcher

# Import v3.0 unified API (primary)
from .api import (
    generate_bom,
    generate_pos,
    BOMOptions,
    POSOptions,
)

__all__ = [
    "__version__",
    "__version_info__",
    # Core types
    "Component",
    "InventoryItem",
    "BOMEntry",
    "ComponentType",
    "DiagnosticIssue",
    "CommonFields",
    # v3.0 Module Classes
    "SchematicLoader",
    "InventoryMatcher",
    "BOMGenerator",
    # v3.0 Unified API (primary interface)
    "generate_bom",
    "generate_pos",
    "BOMOptions",
    "POSOptions",
    # Utilities
    "normalize_field_name",
    "field_to_header",
    "normalize_component_type",
    # Feature flags
    "EXCEL_SUPPORT",
    "NUMBERS_SUPPORT",
]
