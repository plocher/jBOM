"""Inventory matcher (shim).

Phase P0: re-export from jbom.jbom.
"""
from __future__ import annotations

from ..jbom import (  # type: ignore[F401]
    InventoryMatcher,
    InventoryItem,
    EXCEL_SUPPORT,
    NUMBERS_SUPPORT,
)

__all__ = [
    "InventoryMatcher",
    "InventoryItem",
    "EXCEL_SUPPORT",
    "NUMBERS_SUPPORT",
]
