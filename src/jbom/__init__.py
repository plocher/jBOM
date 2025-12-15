"""jBOM - Intelligent KiCad Bill of Materials Generator

A sophisticated BOM generator for KiCad projects that matches schematic components
against an inventory file (CSV, Excel, or Apple Numbers) to produce fabrication-ready BOMs.
"""

from .__version__ import __version__, __version_info__

# Import data types
from .common.types import Component, InventoryItem, BOMEntry
from .common.constants import ComponentType, DiagnosticIssue, CommonFields
from .common.fields import normalize_field_name, field_to_header

# Import schematic loader and BOM generator
from .sch import SchematicLoader, BOMGenerator
from .sch.types import normalize_component_type

# Import inventory matcher
from .inventory import InventoryMatcher

# Import from jbom.py (main CLI functions)
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
    "Component",
    "InventoryItem",
    "BOMEntry",
    "ComponentType",
    "DiagnosticIssue",
    "CommonFields",
    "SchematicLoader",
    "InventoryMatcher",
    "BOMGenerator",
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
