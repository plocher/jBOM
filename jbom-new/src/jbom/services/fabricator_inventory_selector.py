"""Fabricator-aware inventory selection.

Phase 2 introduces a fabricator selection layer (ADR 0001) that prunes inventory
items to those usable for a specific fabricator and annotates them with a
fabricator preference tier.

Selection pipeline (in order):
1) Project restriction: honor optional `Projects` field (comma-separated).
2) Field normalization: map evolving CSV header variants to canonical names using
   FabricatorConfig.field_synonyms.
3) Tier assignment: evaluate FabricatorConfig.tier_rules in ascending tier order.

This service is intentionally *stateless* with respect to InventoryItem objects:
- It does NOT mutate InventoryItem.raw_data.
- It preserves input order.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional

from jbom.common.types import InventoryItem
from jbom.config.fabricators import FabricatorConfig


@dataclass(frozen=True)
class EligibleInventoryItem:
    """Inventory item annotated with fabricator selection metadata."""

    item: InventoryItem
    preference_tier: int
    matched_canonical_field: str = ""


class FabricatorInventorySelector:
    """Filters inventory items to those eligible for a fabricator profile."""

    def __init__(self, fabricator_config: FabricatorConfig):
        """Create a selector bound to a specific fabricator config."""

        if not fabricator_config.tier_rules:
            raise ValueError(
                "FabricatorConfig is missing tier_rules; cannot select eligible inventory"
            )

        self._config = fabricator_config

    def select_eligible(
        self, inventory: List[InventoryItem], project_name: Optional[str] = None
    ) -> List[EligibleInventoryItem]:
        """Select eligible inventory items for this fabricator.

        Args:
            inventory: Inventory items to filter.
            project_name: Optional project identifier. Matching is performed against
                the optional `Projects` inventory field after normalizing to basename
                (no extension), so values like "CustomerA.kicad_sch" and
                "CustomerA.kicad_pcb" match "CustomerA".

        Returns:
            List of eligible items in the same order they appeared in `inventory`.
        """

        eligible: List[EligibleInventoryItem] = []

        for item in inventory:
            if not self._passes_project_filter(item, project_name):
                continue

            normalized_raw_data = self._normalized_raw_data(item)
            tier = self._assign_tier(normalized_raw_data)
            if tier is None:
                continue

            eligible.append(
                EligibleInventoryItem(
                    item=item,
                    preference_tier=tier,
                    matched_canonical_field="",
                )
            )

        return eligible

    def _passes_project_filter(
        self, item: InventoryItem, project_name: Optional[str]
    ) -> bool:
        """Return True if the item is allowed for the given project.

        Inventory can optionally declare project restriction via a comma-separated
        `Projects` field. If present, this item is only eligible when a project is
        provided and it matches.

        Project names are normalized to basename (no extension) for matching.
        """

        projects_field = str(item.raw_data.get("Projects", "")).strip()
        if not projects_field:
            return True

        if not project_name:
            return False

        project_basename = self._project_basename(project_name)
        allowed = [
            self._project_basename(p.strip())
            for p in projects_field.split(",")
            if p.strip()
        ]
        return project_basename in allowed

    @staticmethod
    def _project_basename(project_name: str) -> str:
        """Normalize a project identifier to a basename without extension."""

        return Path(project_name).stem

    def _normalized_raw_data(self, item: InventoryItem) -> Dict[str, str]:
        """Return a normalized raw_data mapping with canonical keys added.

        This does not mutate the InventoryItem.

        Canonical keys are populated from synonyms only when the canonical key is
        missing or empty.
        """

        raw = item.raw_data or {}
        normalized: Dict[str, str] = dict(raw)

        for header, value in raw.items():
            canonical = self._config.resolve_field_synonym(header)
            if canonical is None:
                continue

            existing = str(normalized.get(canonical, ""))
            if existing.strip():
                continue

            normalized[canonical] = str(value)

        return normalized

    def _assign_tier(self, raw_data: Mapping[str, str]) -> Optional[int]:
        """Assign a preference tier using the fabricator's tier_rules.

        Returns None when no tier matches.
        """

        for tier_num in sorted(self._config.tier_rules.keys()):
            rule = self._config.tier_rules[tier_num]
            if rule.matches(raw_data):
                return tier_num

        return None
