"""jBOM - Intelligent KiCad Bill of Materials Generator

A sophisticated BOM generator for KiCad projects that matches schematic components
against an inventory file (CSV, Excel, or Apple Numbers) to produce fabrication-ready BOMs.
"""

from .__version__ import __version__, __version_info__

# Import data types
from .common.types import Component, InventoryItem, BOMEntry
from .common.constants import ComponentType, DiagnosticIssue, CommonFields
from .common.fields import normalize_field_name, field_to_header

# Import from new v3.0 module structure
from .loaders.schematic import SchematicLoader
from .generators.bom import BOMGenerator
from .processors.component_types import normalize_component_type
from .processors.inventory_matcher import InventoryMatcher

# Import v3.0 unified API
from .api import (
    generate_bom,
    generate_pos,
    BOMOptions,
    POSOptions,
)

# Import from jbom.py (main CLI functions and backward compatibility)
from .jbom import (
    GenerateOptions,
    generate_bom_api,
    EXCEL_SUPPORT,
    NUMBERS_SUPPORT,
    # Extra re-exports for backward/test compatibility
    extract_sheet_files,
    find_best_schematic,
    is_hierarchical_schematic,
    process_hierarchical_schematic,
    _parse_fields_argument,
    print_bom_table,
    print_debug_diagnostics,
    _shorten_url,
    _wrap_text,
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
    # Loaders
    "SchematicLoader",
    "InventoryMatcher",
    # Generators
    "BOMGenerator",
    # v3.0 Unified API (primary)
    "generate_bom",
    "generate_pos",
    "BOMOptions",
    "POSOptions",
    # v2.x API (backward compatibility)
    "GenerateOptions",
    "generate_bom_api",
    "EXCEL_SUPPORT",
    "NUMBERS_SUPPORT",
    # Helpers (tests/back-compat)
    "normalize_field_name",
    "field_to_header",
    "normalize_component_type",
    "extract_sheet_files",
    "find_best_schematic",
    "is_hierarchical_schematic",
    "process_hierarchical_schematic",
    "_parse_fields_argument",
    "print_bom_table",
    "print_debug_diagnostics",
    "_shorten_url",
    "_wrap_text",
]
