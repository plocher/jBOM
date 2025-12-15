"""Common utilities shared by schematic and PCB modules.

Provides field normalization, type definitions, package lists, file discovery,
generator base classes, and output utilities.
"""

from .fields import normalize_field_name, field_to_header
from .types import ComponentType, DiagnosticIssue, CommonFields
from .packages import PackageType, SMDType
from .utils import (
    find_best_schematic,
    find_best_pcb,
    is_hierarchical_schematic,
    extract_sheet_files,
    process_hierarchical_schematic,
)
from .generator import Generator, FieldProvider, GeneratorOptions
from .fields_system import FieldPresetRegistry, parse_fields_argument
from .output import resolve_output_path
from .options import BOMOptions, PlacementOptions

__all__ = [
    # Field utilities
    "normalize_field_name",
    "field_to_header",
    # Types
    "ComponentType",
    "DiagnosticIssue",
    "CommonFields",
    "PackageType",
    "SMDType",
    # File discovery
    "find_best_schematic",
    "find_best_pcb",
    "is_hierarchical_schematic",
    "extract_sheet_files",
    "process_hierarchical_schematic",
    # Generator infrastructure
    "Generator",
    "FieldProvider",
    "GeneratorOptions",
    "BOMOptions",
    "PlacementOptions",
    # Field system
    "FieldPresetRegistry",
    "parse_fields_argument",
    # Output utilities
    "resolve_output_path",
]
