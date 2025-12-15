"""Data processors for jBOM.

Processing and transformation of loaded data:
- Component type detection and categorization
- Inventory matching and scoring
"""

from jbom.processors.component_types import (
    get_component_type,
    get_category_fields,
    get_value_interpretation,
    normalize_component_type,
)
from jbom.processors.inventory_matcher import InventoryMatcher

__all__ = [
    "get_component_type",
    "get_category_fields",
    "get_value_interpretation",
    "normalize_component_type",
    "InventoryMatcher",
]
