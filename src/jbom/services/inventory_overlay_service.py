"""Inventory overlay service for canonical BOM namespace projection.

Phase-2 slice scope:
- centralize inventory application for BOM entries
- project inventory-derived values into explicit `i:*` fields
- provide deterministic `i:package` fallback for no-inventory flows
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from jbom.common.component_utils import derive_package_from_footprint
from jbom.services.bom_generator import BOMData, BOMEntry
from jbom.services.inventory_matcher import InventoryMatcher

_INVENTORY_NAMESPACE_FIELDS: tuple[str, ...] = (
    "inventory_ipn",
    "manufacturer",
    "manufacturer_part",
    "description",
    "datasheet",
    "lcsc",
    "tolerance",
    "voltage",
    "wattage",
    "package",
    "smd",
    "fabricator_part_number",
)


@dataclass(frozen=True)
class InventoryOverlayResult:
    """Container for inventory-overlaid BOM data and overlay metadata."""

    bom_data: BOMData
    namespace_fields: tuple[str, ...]


class InventoryOverlayService:
    """Apply inventory enhancement and project explicit `i:*` namespace fields."""

    def __init__(self, *, inventory_matcher: Optional[InventoryMatcher] = None) -> None:
        """Initialize service with injectable matcher for testability."""

        self._inventory_matcher = inventory_matcher or InventoryMatcher()

    def overlay_bom_data(
        self,
        bom_data: BOMData,
        *,
        inventory_file: Path | None,
        fabricator_id: str,
        project_name: str | None,
    ) -> InventoryOverlayResult:
        """Apply inventory overlay and project inventory namespace fields."""

        overlaid_data = bom_data
        if inventory_file is not None:
            overlaid_data = self._inventory_matcher.enhance_bom_with_inventory(
                bom_data,
                inventory_file,
                fabricator_id=fabricator_id,
                project_name=project_name,
            )

        namespaced_entries = [
            self._project_inventory_namespace_fields(entry)
            for entry in overlaid_data.entries
        ]

        metadata = dict(overlaid_data.metadata)
        metadata["inventory_overlay_namespace_fields"] = _INVENTORY_NAMESPACE_FIELDS
        if inventory_file is None:
            metadata["inventory_overlay_mode"] = "project_fallback_only"
        else:
            metadata["inventory_overlay_mode"] = "inventory_applied"

        projected_bom_data = BOMData(
            project_name=overlaid_data.project_name,
            entries=namespaced_entries,
            metadata=metadata,
        )
        return InventoryOverlayResult(
            bom_data=projected_bom_data,
            namespace_fields=_INVENTORY_NAMESPACE_FIELDS,
        )

    def _project_inventory_namespace_fields(self, entry: BOMEntry) -> BOMEntry:
        """Project normalized entry attributes into explicit `i:*` namespace keys."""

        attributes = dict(entry.attributes)

        has_inventory_match = bool(attributes.get("inventory_matched"))
        if has_inventory_match:
            for field_name in _INVENTORY_NAMESPACE_FIELDS:
                value = self._coerce_inventory_value(attributes.get(field_name))
                if value:
                    attributes[f"i:{field_name}"] = value

        if not self._coerce_inventory_value(attributes.get("i:package")):
            package_value = self._coerce_inventory_value(attributes.get("package"))
            if not package_value:
                package_value = derive_package_from_footprint(entry.footprint)
            if package_value:
                attributes["i:package"] = package_value

        return BOMEntry(
            references=entry.references,
            value=entry.value,
            footprint=entry.footprint,
            quantity=entry.quantity,
            lib_id=entry.lib_id,
            attributes=attributes,
        )

    def _coerce_inventory_value(self, value: object) -> str:
        """Convert attribute values into non-empty strings for namespace projection."""

        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, bool):
            return "Yes" if value else "No"
        return str(value).strip()
