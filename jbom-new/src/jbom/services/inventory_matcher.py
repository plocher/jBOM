"""Inventory matcher service that enhances BOM entries with inventory data.

This service implements the core matching pipeline:
1. Load inventory items from file(s)
2. Filter/rank inventory by fabricator profile (FabricatorInventorySelector)
3. Match each aggregated BOM group to filtered inventory (SophisticatedInventoryMatcher)
4. Enrich BOM entries with best-match inventory data
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path

from jbom.common.types import Component, InventoryItem
from jbom.config.fabricators import FabricatorConfig, load_fabricator
from jbom.services.bom_generator import BOMEntry, BOMData
from jbom.services.fabricator_inventory_selector import FabricatorInventorySelector
from jbom.services.inventory_reader import InventoryReader
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)

logger = logging.getLogger(__name__)


class InventoryMatcher:
    """Service that matches BOM entries to inventory items and enhances them."""

    def __init__(self) -> None:
        """Initialize the inventory matcher."""

    def enhance_bom_with_inventory(
        self,
        bom_data: BOMData,
        inventory_file: Path,
        fabricator_id: str = "generic",
        project_name: Optional[str] = None,
    ) -> BOMData:
        """Enhance BOM data with inventory information.

        Pipeline steps:
        1. Load raw inventory items from file
        2. Filter inventory through fabricator profile (affinity → project → tier)
        3. For each BOM entry, construct a representative Component and match
           against the filtered inventory using SophisticatedInventoryMatcher
        4. Enrich matched entries with inventory data

        Args:
            bom_data: BOM data to enhance
            inventory_file: Path to inventory file
            fabricator_id: Fabricator profile ID (default: "generic")
            project_name: Optional project name for project-restricted items

        Returns:
            Enhanced BOM data with inventory information
        """
        # Step 1: Load inventory
        inventory_items = self._load_inventory(inventory_file)
        if not inventory_items:
            return bom_data

        # Step 2: Filter inventory through fabricator profile
        eligible_items, fabricator_config = self._filter_by_fabricator(
            inventory_items, fabricator_id, project_name
        )

        # Step 3+4: Match and enrich each BOM entry
        matcher = SophisticatedInventoryMatcher(MatchingOptions())
        enhanced_entries = []
        matched_count = 0
        orphan_refs: List[str] = []

        for entry in bom_data.entries:
            component = self._bom_entry_to_component(entry)
            matches = matcher.find_matches(component, eligible_items)

            if matches:
                best = matches[0]
                enhanced_entry = self._enrich_entry(
                    entry,
                    best.inventory_item,
                    fabricator_id=fabricator_id,
                    fabricator_config=fabricator_config,
                )
                enhanced_entries.append(enhanced_entry)
                matched_count += 1
            else:
                enhanced_entries.append(entry)
                orphan_refs.append(entry.references_string)

        # Build enhanced metadata
        enhanced_metadata = bom_data.metadata.copy()
        enhanced_metadata.update(
            {
                "inventory_file": str(inventory_file),
                "inventory_items_loaded": len(inventory_items),
                "fabricator_id": fabricator_id,
                "eligible_items": len(eligible_items),
                "matched_entries": matched_count,
                "orphan_entries": len(orphan_refs),
            }
        )
        if orphan_refs:
            enhanced_metadata["orphan_references"] = orphan_refs

        return BOMData(
            project_name=bom_data.project_name,
            entries=enhanced_entries,
            metadata=enhanced_metadata,
        )

    def _load_inventory(self, inventory_file: Path) -> List[InventoryItem]:
        """Load inventory items from file."""
        if not inventory_file.exists():
            return []

        try:
            loader = InventoryReader(inventory_file)
            inventory_items, _ = loader.load()
            return inventory_items
        except Exception:
            return []

    def _filter_by_fabricator(
        self,
        inventory_items: List[InventoryItem],
        fabricator_id: str,
        project_name: Optional[str],
    ) -> tuple[list, Optional[FabricatorConfig]]:
        """Filter inventory through fabricator profile.

        Returns:
            (eligible_items, fabricator_config)

        eligible_items:
            - List[EligibleInventoryItem] when a fabricator config is found
            - List[InventoryItem] as fallback when no config is available

        fabricator_config:
            - Loaded config when available
            - None when falling back
        """
        try:
            config = load_fabricator(fabricator_id)
            selector = FabricatorInventorySelector(config)
            return selector.select_eligible(inventory_items, project_name), config
        except (ValueError, Exception) as exc:
            logger.debug(
                "Fabricator '%s' config unavailable (%s); using unfiltered inventory",
                fabricator_id,
                exc,
            )
            return inventory_items, None

    @staticmethod
    def _bom_entry_to_component(entry: BOMEntry) -> Component:
        """Construct a representative Component from a BOM entry.

        Since all components in an aggregated group have identical
        electro-mechanical specs by definition, any member is representative.
        The BOMEntry carries lib_id, value, footprint, and merged attributes
        from the group — exactly what the sophisticated matcher needs.
        """
        return Component(
            reference=entry.references[0] if entry.references else "",
            lib_id=entry.lib_id,
            value=entry.value,
            footprint=entry.footprint,
            properties=entry.attributes,
        )

    @staticmethod
    def _normalized_raw_data(
        config: FabricatorConfig, raw_data: Dict[str, str]
    ) -> Dict[str, str]:
        """Return a raw_data mapping augmented with canonical keys.

        This mirrors the normalization behavior in FabricatorInventorySelector but
        is used during enrichment because EligibleInventoryItem does not mutate
        InventoryItem.raw_data.
        """
        raw = raw_data or {}
        normalized: Dict[str, str] = dict(raw)

        for header, value in raw.items():
            canonical = config.resolve_field_synonym(header)
            if canonical is None:
                continue

            existing = str(normalized.get(canonical, ""))
            if existing.strip():
                continue

            normalized[canonical] = str(value)

        return normalized

    @staticmethod
    def _resolve_fabricator_part_number(
        *,
        item: InventoryItem,
        fabricator_id: str,
        fabricator_config: Optional[FabricatorConfig],
    ) -> str:
        """Resolve fabricator_part_number using fabricator field_synonyms.

        Phase 4 inventory schema uses explicit supplier columns (LCSC/Mouser/etc)
        and fabricator configs supply tolerant synonym lists.
        """
        if fabricator_config is None:
            return item.lcsc or item.distributor_part_number or item.mfgpn

        normalized = InventoryMatcher._normalized_raw_data(
            fabricator_config, item.raw_data
        )

        fid = (fabricator_id or "").strip().lower()
        precedence = ["fab_pn", "supplier_pn", "mpn"]
        if fid == "pcbway":
            # PCBWay wants MPN as the primary identifier.
            precedence = ["mpn", "supplier_pn", "fab_pn"]

        for canonical in precedence:
            v = str(normalized.get(canonical, "")).strip()
            if v:
                return v

        return ""

    @staticmethod
    def _enrich_entry(
        entry: BOMEntry,
        item: InventoryItem,
        *,
        fabricator_id: str,
        fabricator_config: Optional[FabricatorConfig],
    ) -> BOMEntry:
        """Enrich a BOM entry with data from the best-matching inventory item."""
        enhanced_attributes = entry.attributes.copy()

        fabricator_part_number = InventoryMatcher._resolve_fabricator_part_number(
            item=item,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

        enhanced_attributes.update(
            {
                "inventory_matched": True,
                "inventory_ipn": item.ipn,
                "manufacturer": item.manufacturer
                if item.manufacturer
                else enhanced_attributes.get("manufacturer", ""),
                "manufacturer_part": item.mfgpn
                if item.mfgpn
                else enhanced_attributes.get("manufacturer_part", ""),
                "description": item.description
                if item.description
                else enhanced_attributes.get("description", ""),
                "datasheet": item.datasheet
                if item.datasheet
                else enhanced_attributes.get("datasheet", ""),
                # Canonical attribute key used by CLI field system.
                "lcsc": item.lcsc if item.lcsc else enhanced_attributes.get("lcsc", ""),
                "tolerance": item.tolerance
                if item.tolerance
                else enhanced_attributes.get("tolerance", ""),
                "voltage": item.voltage
                if item.voltage
                else enhanced_attributes.get("voltage", ""),
                "wattage": item.wattage
                if item.wattage
                else enhanced_attributes.get("wattage", ""),
                "package": item.package
                if item.package
                else enhanced_attributes.get("package", ""),
                "smd": item.smd if item.smd else enhanced_attributes.get("smd", ""),
                "fabricator_part_number": fabricator_part_number
                if fabricator_part_number
                else enhanced_attributes.get("fabricator_part_number", ""),
            }
        )

        return BOMEntry(
            references=entry.references,
            value=entry.value,
            footprint=entry.footprint,
            lib_id=entry.lib_id,
            quantity=entry.quantity,
            attributes=enhanced_attributes,
        )
