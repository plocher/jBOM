"""Package-related constants (shim)."""
from __future__ import annotations

from ..jbom import PackageType, SMDType  # type: ignore[F401]

__all__ = ["PackageType", "SMDType"]
