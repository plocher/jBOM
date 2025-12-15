"""Schematic model (shim) for jBOM.

Exposes Component for schematic elements.
"""
from __future__ import annotations

from ..jbom import Component  # type: ignore[F401]

__all__ = ["Component"]
