"""Schematic BOM (shim) for jBOM.

Exposes BOMEntry and BOMGenerator for schematic-driven BOM creation.
"""
from __future__ import annotations

from ..jbom import BOMEntry, BOMGenerator  # type: ignore[F401]

__all__ = [
    "BOMEntry",
    "BOMGenerator",
]
