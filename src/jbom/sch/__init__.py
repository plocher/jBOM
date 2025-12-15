"""Schematic parsing and component type detection for jBOM.

Provides:
- KiCad schematic parsing (.kicad_sch files)
- Component type detection from library IDs and footprints
- Category-specific field mappings
"""

from jbom.sch.parser import KiCadParser
from jbom.sch.types import (
    get_component_type,
    get_category_fields,
    get_value_interpretation,
    normalize_component_type,
)
from jbom.common.types import Component, BOMEntry

__all__ = [
    "KiCadParser",
    "get_component_type",
    "get_category_fields",
    "get_value_interpretation",
    "normalize_component_type",
    "Component",
    "BOMEntry",
]
