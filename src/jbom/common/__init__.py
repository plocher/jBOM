"""Common utilities shared (eventually) by schematic and PCB modules.

Phase P0: thin re-exports from jbom.jbom for backward-compat.
"""

from .fields import normalize_field_name, field_to_header
from .types import ComponentType, DiagnosticIssue, CommonFields
from .packages import PackageType, SMDType

__all__ = [
    "normalize_field_name",
    "field_to_header",
    "ComponentType",
    "DiagnosticIssue",
    "CommonFields",
    "PackageType",
    "SMDType",
]
