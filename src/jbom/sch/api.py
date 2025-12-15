"""Schematic API (shim) for jBOM.

Phase P0 refactor: export the public API from jbom.jbom so callers can
import from jbom.sch.api without behavior change.
"""
from __future__ import annotations

# Re-export from the existing implementation
from ..jbom import GenerateOptions, generate_bom_api  # type: ignore[F401]

__all__ = [
    "GenerateOptions",
    "generate_bom_api",
]
