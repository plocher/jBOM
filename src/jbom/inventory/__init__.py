"""Inventory management for jBOM.

Provides inventory loading and matching functionality.
Supports CSV, Excel (.xlsx, .xls), and Apple Numbers (.numbers) file formats.
"""

# Backward compatibility: re-export from new locations
from jbom.loaders.inventory import InventoryLoader
from jbom.processors.inventory_matcher import InventoryMatcher
from jbom.common.types import InventoryItem

__all__ = ["InventoryLoader", "InventoryMatcher", "InventoryItem"]
