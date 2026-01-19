"""Inventory matcher service that enhances BOM entries with inventory data."""

from typing import List, Dict, Optional
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
        self, bom_data: BOMData, inventory_file: Path, match_strategy: str = "ipn_fuzzy"
    ) -> BOMData:
        """Enhance BOM data with inventory information.

        Args:
            bom_data: BOM data to enhance
            inventory_file: Path to inventory CSV file
            match_strategy: Strategy for matching ("ipn_exact", "ipn_fuzzy", "value_package")

        Returns:
            Enhanced BOM data with inventory information
        """
        # Load inventory data
        inventory_items = self._load_inventory(inventory_file)
        if not inventory_items:
            return bom_data  # Return original if no inventory

        # Create lookup structures based on strategy
        inventory_lookup = self._create_inventory_lookup(
            inventory_items, match_strategy
        )

        # Enhance each BOM entry
        enhanced_entries = []
        for entry in bom_data.entries:
            enhanced_entry = self._enhance_entry_with_inventory(
                entry, inventory_lookup, match_strategy
            )
            enhanced_entries.append(enhanced_entry)

        # Create enhanced BOM data
        enhanced_metadata = bom_data.metadata.copy()
        enhanced_metadata.update(
            {
                "inventory_file": str(inventory_file),
                "match_strategy": match_strategy,
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

    def _create_inventory_lookup(
        self, inventory_items: List[InventoryItem], match_strategy: str
    ) -> Dict[str, InventoryItem]:
        """Create lookup dictionary based on matching strategy."""
        lookup = {}

        for item in inventory_items:
            if match_strategy == "ipn_exact":
                # Match by exact IPN
                lookup[item.ipn] = item
            elif match_strategy == "ipn_fuzzy":
                # Match by IPN and also create alternate keys
                lookup[item.ipn] = item
                # Add alternate keys (e.g., without category prefix)
                if "_" in item.ipn:
                    parts = item.ipn.split("_", 1)
                    if len(parts) > 1:
                        lookup[parts[1]] = item  # Value without category
            elif match_strategy == "value_package":
                # Match by value + package combination
                if item.value and item.package:
                    key = f"{item.value}_{item.package}"
                    lookup[key] = item

        return lookup

    def _enhance_entry_with_inventory(
        self,
        entry: BOMEntry,
        inventory_lookup: Dict[str, InventoryItem],
        match_strategy: str,
    ) -> BOMEntry:
        """Enhance a single BOM entry with inventory data."""
        # Try to find matching inventory item
        inventory_item = self._find_matching_inventory_item(
            entry, inventory_lookup, match_strategy
        )

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
        inventory_lookup: Dict[str, InventoryItem],
        match_strategy: str,
    ) -> Optional[InventoryItem]:
        """Find matching inventory item for a BOM entry."""
        if match_strategy == "ipn_exact":
            # Generate expected IPN from entry
            expected_ipn = self._generate_ipn_from_entry(entry)
            return inventory_lookup.get(expected_ipn)

        elif match_strategy == "ipn_fuzzy":
            # Try multiple IPN variations
            ipn_candidates = [
                self._generate_ipn_from_entry(entry),  # Full IPN
                entry.value,  # Just value
                f"{entry.value}_{self._extract_package(entry.footprint)}",  # Value + package
            ]

            for candidate in ipn_candidates:
                if candidate and candidate in inventory_lookup:
                    return inventory_lookup[candidate]
            return None

        elif match_strategy == "value_package":
            # Match by value + package
            package = self._extract_package(entry.footprint)
            if entry.value and package:
                key = f"{entry.value}_{package}"
                return inventory_lookup.get(key)
            return None

        return None

    def _generate_ipn_from_entry(self, entry: BOMEntry) -> str:
        """Generate expected IPN from BOM entry (similar to component converter)."""
        # Determine category from lib_id
        category = self._detect_category_from_lib_id(entry.lib_id)

        # Clean value for IPN
        clean_value = entry.value.replace(" ", "").replace("/", "_").replace("\\", "_")

        return f"{category}_{clean_value}"

    def _detect_category_from_lib_id(self, lib_id: str) -> str:
        """Detect component category from lib_id."""
        if not lib_id or ":" not in lib_id:
            return "UNKNOWN"

        lib_prefix, symbol = lib_id.split(":", 1)

        # Check library prefix first (e.g., "Timer" indicates IC)
        if lib_prefix.upper() in ["TIMER", "ANALOG", "MICROCONTROLLER"]:
            return "IC"

        # Category mapping based on symbol (order matters! More specific patterns first)
        if symbol.upper().startswith("LED"):
            return "LED"
        elif symbol.upper().startswith("C"):
            return "CAP"
        elif symbol.upper().startswith("R"):
            return "RES"
        elif symbol.upper().startswith("L"):
            return "IND"
        elif symbol.upper().startswith("D"):
            return "DIODE"
        elif symbol.upper().startswith("U") or "IC" in symbol.upper():
            return "IC"
        else:
            return "UNKNOWN"

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
