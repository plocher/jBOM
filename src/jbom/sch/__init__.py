"""Schematic loading, BOM generation, and component type detection for jBOM.

Provides:
- KiCad schematic loading (.kicad_sch files)
- BOM generation from components and inventory
- Component type detection from library IDs and footprints
- Category-specific field mappings
"""

# Backward compatibility: re-export from new locations
from jbom.loaders.schematic import SchematicLoader
from jbom.generators.bom import BOMGenerator
from jbom.processors.component_types import (
    get_component_type,
    get_category_fields,
    get_value_interpretation,
    normalize_component_type,
)
from jbom.common.types import Component, BOMEntry

__all__ = [
    "SchematicLoader",
    "BOMGenerator",
    "get_component_type",
    "get_category_fields",
    "get_value_interpretation",
    "normalize_component_type",
    "Component",
    "BOMEntry",
]
