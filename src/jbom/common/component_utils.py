"""Component utility functions.

Deprecated: prefer :mod:`jbom.common.component_classification`.

This module remains as a compatibility shim for existing imports.
"""

from __future__ import annotations

from typing import Optional

from jbom.common.component_classification import (
    get_component_type as _get_component_type,
)


def derive_package_from_footprint(footprint: str) -> str:
    """Derive a best-effort package name from a KiCad footprint identifier.

    Strips the library prefix (e.g. ``SPCoast:0603-RES`` -> ``0603-RES``).
    Returns the footprint as-is if no colon separator is present.

    Args:
        footprint: KiCad footprint string (may include library prefix)

    Returns:
        Package name string, empty string if footprint is empty
    """
    if not footprint:
        return ""
    if ":" in footprint:
        return footprint.split(":", 1)[-1]
    return footprint


def get_component_type(lib_id: str, footprint: str = "") -> Optional[str]:
    """Determine component type from library ID and footprint.

    Args:
        lib_id: KiCad library ID (e.g., "Device:R")
        footprint: Component footprint (e.g., "R_0603")

    Returns:
        Component type string or None if unknown
    """

    return _get_component_type(lib_id=lib_id, footprint=footprint)
