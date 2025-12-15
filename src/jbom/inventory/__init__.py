"""Inventory matching API surface.

Re-exports inventory API from jbom.jbom for convenience.
This allows imports like: from jbom.inventory import InventoryMatcher
"""

from ..jbom import InventoryMatcher, InventoryItem

__all__ = ["InventoryMatcher", "InventoryItem"]
