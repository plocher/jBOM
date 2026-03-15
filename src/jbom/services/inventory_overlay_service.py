"""Inventory overlay service for canonical BOM namespace projection.

The overlay workflow has two stages:
1. optionally enrich merged BOM entries with inventory matching results.
2. project inventory-facing attributes into explicit `i:*` namespace fields.

Projected namespace fields are profile-driven. The service derives canonical
field candidates from defaults, supplier profiles, fabricator profiles, and
the inventory item schema, then normalizes aliases to the BOM attribute names
emitted by inventory matching.
"""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields
from pathlib import Path
from typing import Optional

from jbom.common.component_utils import derive_package_from_footprint
from jbom.common.fields import normalize_field_name
from jbom.common.types import InventoryItem
from jbom.config.defaults import get_defaults
from jbom.config.fabricators import get_available_fabricators, load_fabricator
from jbom.config.suppliers import get_available_suppliers, load_supplier
from jbom.services.bom_generator import BOMData, BOMEntry
from jbom.services.inventory_matcher import InventoryMatcher

_PROFILE_TO_OVERLAY_FIELD_ALIASES: dict[str, str] = {
    "ipn": "inventory_ipn",
    "mfgpn": "manufacturer_part",
    "mpn": "manufacturer_part",
    "manufacturer_part_number": "manufacturer_part",
    "power": "wattage",
    "fab_pn": "fabricator_part_number",
    "supplier_pn": "fabricator_part_number",
}


@dataclass(frozen=True)
class InventoryOverlayResult:
    """Container for inventory-overlaid BOM data and overlay metadata."""

    bom_data: BOMData
    namespace_fields: tuple[str, ...]


class InventoryOverlayService:
    """Apply inventory enhancement and project explicit `i:*` namespace fields.

    Namespace projection is intentionally derived from configuration profiles so
    new suppliers/fabricators can introduce relevant inventory attributes
    without requiring code edits to this service.
    """

    def __init__(
        self,
        *,
        inventory_matcher: Optional[InventoryMatcher] = None,
        namespace_fields: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize service dependencies and resolved namespace projection set."""

        self._inventory_matcher = inventory_matcher or InventoryMatcher()
        self._namespace_fields = (
            namespace_fields or self._resolve_namespace_fields_from_profiles()
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

    def _resolve_namespace_fields_from_profiles(self) -> tuple[str, ...]:
        """Resolve namespace projection fields from defaults and profile metadata.

        Resolution order is deterministic:
        1. defaults profile canonical field names,
        2. supplier inventory column identifiers,
        3. fabricator projection canonical fields,
        4. inventory schema attributes.

        Normalized profile tokens are aliased to overlay attribute names and
        deduplicated while preserving first-seen ordering.
        """

        ordered_tokens: list[str] = []
        seen_tokens: set[str] = set()

        def _append_token(raw_token: str | None) -> None:
            if not raw_token:
                return
            normalized = normalize_field_name(raw_token)
            if not normalized or normalized in seen_tokens:
                return
            seen_tokens.add(normalized)
            ordered_tokens.append(normalized)

        defaults = get_defaults()
        for canonical_name in defaults.field_synonyms.keys():
            _append_token(canonical_name)

        for supplier_id in get_available_suppliers():
            try:
                supplier_profile = load_supplier(supplier_id)
            except ValueError:
                continue
            _append_token(supplier_profile.inventory_column)
            for synonym in supplier_profile.inventory_column_synonyms:
                _append_token(synonym)

        for fabricator_id in get_available_fabricators():
            try:
                fabricator_profile = load_fabricator(fabricator_id)
            except ValueError:
                continue
            for canonical_name in fabricator_profile.field_synonyms.keys():
                _append_token(canonical_name)

        for schema_field in dataclass_fields(InventoryItem):
            _append_token(schema_field.name)

        mapped_fields: list[str] = []
        seen_fields: set[str] = set()
        for token in ordered_tokens:
            mapped_name = _PROFILE_TO_OVERLAY_FIELD_ALIASES.get(token, token)
            if mapped_name in seen_fields:
                continue
            seen_fields.add(mapped_name)
            mapped_fields.append(mapped_name)

        return tuple(mapped_fields)
