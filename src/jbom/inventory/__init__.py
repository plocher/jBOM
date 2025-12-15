"""Inventory management for jBOM.

Provides inventory loading and matching functionality.
Supports CSV, Excel (.xlsx, .xls), and Apple Numbers (.numbers) file formats.
"""

from jbom.inventory.loader import InventoryLoader
from jbom.inventory.matcher import InventoryMatcher
from jbom.common.types import InventoryItem

__all__ = ["InventoryLoader", "InventoryMatcher", "InventoryItem"]
