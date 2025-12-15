"""Schematic parser (shim) for jBOM.

Exposes KiCadParser for schematic S-expression parsing.
"""
from __future__ import annotations

from ..jbom import KiCadParser  # type: ignore[F401]

__all__ = ["KiCadParser"]
