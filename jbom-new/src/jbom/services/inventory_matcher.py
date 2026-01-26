"""Inventory matcher service that enhances BOM entries with inventory data."""

from typing import List, Optional
from pathlib import Path

from jbom.services.bom_generator import BOMEntry, BOMData
from jbom.common.types import InventoryItem
from jbom.services.inventory_reader import InventoryReader


class InventoryMatcher:
    """Service that matches BOM entries to inventory items and enhances them."""

    def __init__(self):
        """Initialize the inventory matcher."""
        pass

    def enhance_bom_with_inventory(
        self, bom_data: BOMData, inventory_file: Path
    ) -> BOMData:
        """Enhance BOM data with inventory information.

        The matching function's scope is to find inventory items that satisfy the
        electrical/physical requirements of partially specified KiCad components.

        Matching Strategy:
        1. Happy Path: component.IPN == inventory.IPN (exact match)
        2. Heuristic matching: value-based matching (case-insensitive)
        3. Higher confidence: value + package matching
        4. Worst Case: Insufficient component specification → no match

        Args:
            bom_data: BOM data to enhance
            inventory_file: Path to inventory CSV file

        Returns:
            Enhanced BOM data with inventory information
        """
        # Load inventory data
        inventory_items = self._load_inventory(inventory_file)
        if not inventory_items:
            return bom_data  # Return original if no inventory

        # Enhance each BOM entry
        enhanced_entries = []
        for entry in bom_data.entries:
            enhanced_entry = self._enhance_entry_with_inventory(entry, inventory_items)
            enhanced_entries.append(enhanced_entry)

        # Create enhanced BOM data
        enhanced_metadata = bom_data.metadata.copy()
        enhanced_metadata.update(
            {
                "inventory_file": str(inventory_file),
                "inventory_items_loaded": len(inventory_items),
                "matched_entries": len(
                    [
                        e
                        for e in enhanced_entries
                        if e.attributes.get("inventory_matched")
                    ]
                ),
            }
        )

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
            # If we can't load inventory, return empty list
            return []

    def _enhance_entry_with_inventory(
        self,
        entry: BOMEntry,
        inventory_items: List[InventoryItem],
    ) -> BOMEntry:
        """Enhance a single BOM entry with inventory data."""
        # Try to find matching inventory item
        inventory_item = self._find_matching_inventory_item(entry, inventory_items)

        if not inventory_item:
            # No match found, return original entry
            return entry

        # Create enhanced attributes
        enhanced_attributes = entry.attributes.copy()
        enhanced_attributes.update(
            {
                # Inventory match metadata
                "inventory_matched": True,
                "inventory_ipn": inventory_item.ipn,
                # Enhanced component data
                "manufacturer": inventory_item.manufacturer
                if inventory_item.manufacturer
                else enhanced_attributes.get("manufacturer", ""),
                "manufacturer_part": inventory_item.mfgpn
                if inventory_item.mfgpn
                else enhanced_attributes.get("manufacturer_part", ""),
                "description": inventory_item.description
                if inventory_item.description
                else enhanced_attributes.get("description", ""),
                "datasheet": inventory_item.datasheet
                if inventory_item.datasheet
                else enhanced_attributes.get("datasheet", ""),
                "lcsc_part": inventory_item.lcsc
                if inventory_item.lcsc
                else enhanced_attributes.get("lcsc_part", ""),
                "tolerance": inventory_item.tolerance
                if inventory_item.tolerance
                else enhanced_attributes.get("tolerance", ""),
                "voltage": inventory_item.voltage
                if inventory_item.voltage
                else enhanced_attributes.get("voltage", ""),
                "wattage": inventory_item.wattage
                if inventory_item.wattage
                else enhanced_attributes.get("wattage", ""),
            }
        )

        # Create enhanced BOM entry
        enhanced_entry = BOMEntry(
            references=entry.references,
            value=entry.value,
            footprint=entry.footprint,
            lib_id=entry.lib_id,
            quantity=entry.quantity,
            attributes=enhanced_attributes,
        )

        return enhanced_entry

    def _find_matching_inventory_item(
        self,
        entry: BOMEntry,
        inventory_items: List[InventoryItem],
    ) -> Optional[InventoryItem]:
        """Find matching inventory item for a BOM entry using simple heuristics."""
        # First check if entry has explicit IPN (rare but possible)
        entry_ipn = entry.attributes.get("ipn")
        if entry_ipn:
            for item in inventory_items:
                if entry_ipn == item.ipn:
                    return item

        # Use heuristic matching on electro-mechanical attributes
        # Try value-based matching (case-insensitive)
        for item in inventory_items:
            if entry.value.upper() == item.value.upper():
                return item

        # Try value + package matching for higher confidence
        package = self._extract_package(entry.footprint)
        if package:
            for item in inventory_items:
                if (
                    entry.value.upper() == item.value.upper()
                    and package == item.package
                ):
                    return item

        return None

    def _extract_package(self, footprint: str) -> str:
        """Extract package size from footprint (simplified)."""
        if not footprint:
            return ""

        # Look for common package patterns
        import re

        patterns = [
            r"(\d{4})_\d{4}Metric",  # 0603_1608Metric -> 0603
            r"(SOT-\d+)",  # SOT-23, SOT-223
            r"(SOIC-\d+)",  # SOIC-8, SOIC-14
        ]

        for pattern in patterns:
            match = re.search(pattern, footprint)
            if match:
                return match.group(1)

        # Fallback - return footprint as-is
        return footprint
