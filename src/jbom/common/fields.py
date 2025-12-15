"""Field normalization helpers (shim).

Phase P0: re-export from existing implementation to avoid behavior changes.
"""
from __future__ import annotations

from ..jbom import normalize_field_name, field_to_header  # type: ignore[F401]

__all__ = ["normalize_field_name", "field_to_header"]
