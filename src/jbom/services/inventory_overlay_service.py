"""Inventory overlay service for canonical BOM namespace projection.

The overlay workflow has two stages:
1. optionally enrich merged BOM entries with inventory matching results.
2. project inventory-facing attributes into explicit `i:*` namespace fields.

Projected namespace fields are defined by defaults `inventory_schema`
canonical fields so schema evolution is centralized in one profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from jbom.common.component_utils import derive_package_from_footprint
from jbom.config.defaults import get_defaults
from jbom.services.bom_generator import BOMData, BOMEntry
from jbom.services.inventory_matcher import InventoryMatcher


@dataclass(frozen=True)
class InventoryOverlayResult:
    """Container for inventory-overlaid BOM data and overlay metadata."""

    bom_data: BOMData
    namespace_fields: tuple[str, ...]


class InventoryOverlayService:
    """Apply inventory enhancement and project explicit `i:*` namespace fields."""

    def __init__(
        self,
        *,
        inventory_matcher: Optional[InventoryMatcher] = None,
        namespace_fields: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize service dependencies and resolved namespace field set."""

        self._inventory_matcher = inventory_matcher or InventoryMatcher()
        self._namespace_fields = (
            namespace_fields or self._resolve_namespace_fields_from_defaults()
        )

    @property
    def namespace_fields(self) -> tuple[str, ...]:
        """Return the resolved canonical inventory namespace projection fields."""

        return self._namespace_fields

    def overlay_bom_data(
        self,
        bom_data: BOMData,
        *,
        inventory_file: Path | None,
        fabricator_id: str,
        project_name: str | None,
        include_inventory_dnp: bool = False,
    ) -> InventoryOverlayResult:
        """Apply inventory overlay and project inventory namespace fields."""

        overlaid_data = bom_data
        if inventory_file is not None:
            overlaid_data = self._inventory_matcher.enhance_bom_with_inventory(
                bom_data,
                inventory_file,
                fabricator_id=fabricator_id,
                project_name=project_name,
                include_inventory_dnp=include_inventory_dnp,
            )

        namespaced_entries = [
            self._project_inventory_namespace_fields(entry)
            for entry in overlaid_data.entries
        ]

        metadata = dict(overlaid_data.metadata)
        metadata["inventory_overlay_namespace_fields"] = self._namespace_fields
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
            namespace_fields=self._namespace_fields,
        )

    def _project_inventory_namespace_fields(self, entry: BOMEntry) -> BOMEntry:
        """Project normalized entry attributes into explicit `i:*` namespace keys."""

        attributes = dict(entry.attributes)

        has_inventory_match = bool(attributes.get("inventory_matched"))
        if has_inventory_match:
            for field_name in self._namespace_fields:
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

    def _resolve_namespace_fields_from_defaults(self) -> tuple[str, ...]:
        """Resolve canonical namespace projection fields from defaults profile."""

        return tuple(get_defaults().get_inventory_schema().canonical_fields)
