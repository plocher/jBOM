"""Shared type constants (shim)."""
from __future__ import annotations

from ..jbom import ComponentType, DiagnosticIssue, CommonFields  # type: ignore[F401]

__all__ = [
    "ComponentType",
    "DiagnosticIssue",
    "CommonFields",
]
