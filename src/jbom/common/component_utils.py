"""Component utility functions.

Deprecated: prefer :mod:`jbom.common.component_classification`.

This module remains as a compatibility shim for existing imports.
"""

from __future__ import annotations

from typing import Optional

from jbom.common.component_classification import (
    get_component_type as _get_component_type,
)


def get_component_type(lib_id: str, footprint: str = "") -> Optional[str]:
    """Determine component type from library ID and footprint.

    Args:
        lib_id: KiCad library ID (e.g., "Device:R")
        footprint: Component footprint (e.g., "R_0603")

    Returns:
        Component type string or None if unknown
    """

    return _get_component_type(lib_id=lib_id, footprint=footprint)
