"""Common utilities shared by schematic and PCB modules.

Provides field normalization, type definitions, package lists, and file discovery.
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

__all__ = [
    "normalize_field_name",
    "field_to_header",
    "ComponentType",
    "DiagnosticIssue",
    "CommonFields",
    "PackageType",
    "SMDType",
    "find_best_schematic",
    "find_best_pcb",
    "is_hierarchical_schematic",
    "extract_sheet_files",
    "process_hierarchical_schematic",
]
