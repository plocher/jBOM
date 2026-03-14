"""Fabricator projection service for BOM/POS output orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from jbom.config.fabricators import (
    FabricatorConfig,
    apply_fabricator_column_mapping,
    load_fabricator,
)


@dataclass(frozen=True)
class FabricatorProjection:
    """Resolved fabricator projection for a selected field list."""

    fabricator_id: str
    output_type: str
    selected_fields: tuple[str, ...]
    headers: tuple[str, ...]
    fabricator_config: Optional[FabricatorConfig]


class FabricatorProjectionService:
    """Centralize fabricator-aware header/field projection behavior."""

    def build_projection(
        self,
        *,
        fabricator_id: str,
        output_type: str,
        selected_fields: Sequence[str],
    ) -> FabricatorProjection:
        """Resolve headers and effective fabricator config for selected fields."""

        normalized_fields = tuple(selected_fields)
        headers = tuple(
            apply_fabricator_column_mapping(
                fabricator_id,
                output_type,
                list(normalized_fields),
            )
        )
        return FabricatorProjection(
            fabricator_id=fabricator_id,
            output_type=output_type,
            selected_fields=normalized_fields,
            headers=headers,
            fabricator_config=self.load_config(fabricator_id),
        )

    def load_config(self, fabricator_id: str) -> Optional[FabricatorConfig]:
        """Best-effort load of a fabricator configuration."""

        try:
            return load_fabricator(fabricator_id)
        except ValueError:
            return None

    @staticmethod
    def resolve_fabricator_part_number(
        attributes: Mapping[str, Any],
        *,
        fabricator_id: str,
        fabricator_config: Optional[FabricatorConfig],
    ) -> str:
        """Resolve fabricator part number via explicit and synonym-driven attributes."""

        explicit = str(attributes.get("fabricator_part_number", "")).strip()
        if explicit:
            return explicit

        effective_config = fabricator_config
        if effective_config is None:
            try:
                effective_config = load_fabricator(fabricator_id)
            except ValueError:
                effective_config = None

        if effective_config is None:
            return ""

        normalized_attributes = FabricatorProjectionService._normalize_attributes(
            attributes,
            effective_config,
        )
        for (
            canonical
        ) in FabricatorProjectionService._part_number_precedence_for_fabricator(
            fabricator_id
        ):
            candidate = normalized_attributes.get(canonical, "").strip()
            if candidate:
                return candidate

        return ""

    @staticmethod
    def _normalize_attributes(
        raw_attributes: Mapping[str, Any],
        fabricator_config: FabricatorConfig,
    ) -> dict[str, str]:
        """Add canonical synonym keys to a raw attribute mapping."""

        normalized: dict[str, str] = {
            str(key): str(value) for key, value in raw_attributes.items()
        }

        for header, value in list(normalized.items()):
            canonical = fabricator_config.resolve_field_synonym(header)
            if canonical is None:
                continue

            existing_value = normalized.get(canonical, "").strip()
            if existing_value:
                continue
            normalized[canonical] = value

        return normalized

    @staticmethod
    def _part_number_precedence_for_fabricator(fabricator_id: str) -> tuple[str, ...]:
        """Return canonical part-number precedence for the given fabricator."""

        if (fabricator_id or "").strip().lower() == "pcbway":
            return ("mpn", "supplier_pn", "fab_pn")
        return ("fab_pn", "supplier_pn", "mpn")
