"""POS field value resolution service.

Extracts and resolves individual field values from POS entries, applying
fabricator-specific projection and namespace-aware source selection.
"""
from __future__ import annotations

from typing import Any, Optional

from jbom.common.fields import normalize_field_name, split_kicad_strip_field
from jbom.common.component_utils import derive_package_from_footprint
from jbom.services.field_listing_service import resolve_field
from jbom.config.fields import (
    ANNOTATION_NAMESPACE,
    INV_NAMESPACE,
    PCB_NAMESPACE,
    SCH_NAMESPACE,
)
from jbom.config.fabricators import FabricatorConfig

# Source priority: PCB first, then inventory, then schematic
_POS_SOURCE_PRIORITY = [PCB_NAMESPACE, INV_NAMESPACE, SCH_NAMESPACE]


def resolve_pos_field_value(
    entry: dict[str, Any],
    field: str,
    *,
    fabricator_id: str = "generic",
    fabricator_config: Optional[FabricatorConfig] = None,
) -> str:
    """Extract and resolve a field value from a POS entry.

    Handles standard fields, namespaced fields (sch:, pcb:, inv:, ann:), position
    coordinates (x, y, rotation), and KiCad strip modifiers (k:). Applies
    fabricator-specific projection and source precedence rules.

    Args:
        entry: POS entry dictionary
        field: Field name to resolve (standard, namespaced, position, or with modifier)
        fabricator_id: Fabricator ID for projection logic
        fabricator_config: Optional fabricator configuration

    Returns:
        String value for the field
    """
    import logging

    row_sources = _build_pos_row_sources(entry)

    # Handle k: modifier — KiCad LIBRARY:NAME → NAME (strip library nickname).
    # "k:footprint" defaults to inventory source; use
    # "inv:k:", "sch:k:", "pcb:k:" explicitly.
    kicad_parts = split_kicad_strip_field(field)
    if kicad_parts is not None:
        source, inner = kicad_parts
        if field.startswith("k:"):
            logging.getLogger(__name__).debug(
                "k:%s: no source prefix specified, defaulting to inv: (inventory). "
                "Use inv:k:, sch:k:, or pcb:k: to be explicit.",
                inner,
            )
        raw = resolve_field(
            f"{source}:{inner}", row_sources, priority=_POS_SOURCE_PRIORITY
        )
        return derive_package_from_footprint(raw)

    # Handle namespaced fields
    namespace_prefix, separator, _ = field.partition(":")
    if separator and namespace_prefix in {SCH_NAMESPACE, PCB_NAMESPACE, INV_NAMESPACE}:
        return resolve_field(field, row_sources, priority=_POS_SOURCE_PRIORITY)
    if separator and namespace_prefix == ANNOTATION_NAMESPACE:
        return str(entry.get(field, "") or "")

    # Handle position coordinates
    if field == "x":
        if entry.get("x_raw"):
            return str(entry["x_raw"])
        return f"{entry['x_mm']:.4f}"
    if field == "y":
        if entry.get("y_raw"):
            return str(entry["y_raw"])
        return f"{entry['y_mm']:.4f}"
    if field == "rotation":
        if entry.get("rotation_raw") is not None:
            return str(entry["rotation_raw"])
        return f"{entry['rotation']:.1f}"

    if field == "fabricator_part_number":
        return _resolve_fabricator_part_number(
            entry,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    # Handle standard POS fields
    field_mapping = {
        "reference": "reference",
        "side": "side",
    }
    if field in field_mapping:
        return str(entry.get(field_mapping[field], ""))
    if field in {"value", "footprint", "package"}:
        return resolve_field(
            field,
            row_sources,
            priority=_POS_SOURCE_PRIORITY,
        )
    return resolve_field(
        field,
        row_sources,
        priority=_POS_SOURCE_PRIORITY,
    ) or str(entry.get(field, ""))


def _resolve_fabricator_part_number(
    entry: dict[str, Any],
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Resolve fabricator part number using projection service."""
    from jbom.services.fabricator_projection_service import FabricatorProjectionService

    return FabricatorProjectionService.resolve_fabricator_part_number(
        entry,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )


def _build_pos_row_sources(entry: dict[str, Any]) -> dict[str, dict[str, object]]:
    """Build source field maps for one POS row (`sch`, `pcb`, `inv`)."""
    row_sources: dict[str, dict[str, object]] = {
        SCH_NAMESPACE: {},
        PCB_NAMESPACE: {},
        INV_NAMESPACE: {},
    }
    for key, value in entry.items():
        normalized_key = normalize_field_name(str(key or ""))
        prefix, separator, remainder = normalized_key.partition(":")
        if (
            separator
            and prefix in {SCH_NAMESPACE, PCB_NAMESPACE, INV_NAMESPACE}
            and remainder
        ):
            row_sources[prefix][remainder] = value
        elif normalized_key:
            row_sources[PCB_NAMESPACE].setdefault(normalized_key, value)

    if entry.get("x_raw"):
        row_sources[PCB_NAMESPACE].setdefault("x", entry.get("x_raw"))
    elif entry.get("x_mm") is not None:
        row_sources[PCB_NAMESPACE].setdefault("x", f"{entry['x_mm']:.4f}")

    if entry.get("y_raw"):
        row_sources[PCB_NAMESPACE].setdefault("y", entry.get("y_raw"))
    elif entry.get("y_mm") is not None:
        row_sources[PCB_NAMESPACE].setdefault("y", f"{entry['y_mm']:.4f}")

    if entry.get("rotation_raw") is not None:
        row_sources[PCB_NAMESPACE].setdefault("rotation", entry.get("rotation_raw"))
    elif entry.get("rotation") is not None:
        row_sources[PCB_NAMESPACE].setdefault("rotation", f"{entry['rotation']:.1f}")

    return row_sources


__all__ = [
    "resolve_pos_field_value",
]
