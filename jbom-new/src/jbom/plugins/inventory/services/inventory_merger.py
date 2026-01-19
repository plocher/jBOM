"""
Service for merging inventory items, handling append operations and deduplication.

Implements the merge strategy: preserve existing data, enhance incomplete entries.
"""

from typing import List, Dict, Optional
from pathlib import Path
from jbom.common.types import InventoryItem
from jbom.loaders.inventory import InventoryLoader


class InventoryMerger:
    """Handles merging new inventory items with existing inventory data."""

    def __init__(self):
        """Initialize the merger."""
        pass

    def merge_with_existing(
        self, new_items: List[InventoryItem], existing_file: Path
    ) -> List[InventoryItem]:
        """Merge new inventory items with existing inventory file.

        Merge strategy:
        - Preserve existing complete entries (don't overwrite)
        - Enhance existing incomplete entries with new data
        - Add new unique items

        Args:
            new_items: List of new InventoryItem objects to merge
            existing_file: Path to existing inventory file

        Returns:
            List of merged InventoryItem objects
        """
        # Load existing inventory if file exists
        existing_items = []
        if existing_file.exists():
            loader = InventoryLoader(existing_file)
            existing_items, _ = loader.load()

        # Create lookup by IPN for existing items
        existing_by_ipn: Dict[str, InventoryItem] = {
            item.ipn: item for item in existing_items
        }

        # Merge logic
        merged_items = []
        processed_ipns = set()

        # Process existing items first, potentially enhancing them
        for existing_item in existing_items:
            ipn = existing_item.ipn
            processed_ipns.add(ipn)

            # Check if we have new data for this IPN
            new_item = self._find_item_by_ipn(new_items, ipn)
            if new_item:
                # Enhance existing item with new data
                enhanced_item = self._enhance_item(existing_item, new_item)
                merged_items.append(enhanced_item)
            else:
                # Keep existing item as-is
                merged_items.append(existing_item)

        # Add new items that don't exist in existing inventory
        for new_item in new_items:
            if new_item.ipn not in processed_ipns:
                merged_items.append(new_item)

        return merged_items

    def deduplicate_new_items(self, items: List[InventoryItem]) -> List[InventoryItem]:
        """Remove duplicates from a list of new inventory items.

        When duplicates are found (same IPN), merge their data.

        Args:
            items: List of InventoryItem objects that may contain duplicates

        Returns:
            List of deduplicated InventoryItem objects
        """
        items_by_ipn: Dict[str, List[InventoryItem]] = {}

        # Group items by IPN
        for item in items:
            if item.ipn not in items_by_ipn:
                items_by_ipn[item.ipn] = []
            items_by_ipn[item.ipn].append(item)

        # Merge duplicates within each IPN group
        deduplicated = []
        for ipn, ipn_items in items_by_ipn.items():
            if len(ipn_items) == 1:
                deduplicated.append(ipn_items[0])
            else:
                # Merge multiple items with same IPN
                merged_item = self._merge_duplicate_items(ipn_items)
                deduplicated.append(merged_item)

        return deduplicated

    def _find_item_by_ipn(
        self, items: List[InventoryItem], ipn: str
    ) -> Optional[InventoryItem]:
        """Find an inventory item by its IPN.

        Args:
            items: List of InventoryItem objects to search
            ipn: IPN to search for

        Returns:
            InventoryItem if found, None otherwise
        """
        for item in items:
            if item.ipn == ipn:
                return item
        return None

    def _enhance_item(
        self, existing: InventoryItem, new: InventoryItem
    ) -> InventoryItem:
        """Enhance an existing inventory item with data from a new item.

        Strategy: Only fill in missing/empty fields in the existing item.
        Never overwrite existing data.

        Args:
            existing: Existing InventoryItem
            new: New InventoryItem with potentially additional data

        Returns:
            Enhanced InventoryItem
        """
        # Create a copy of the existing item to avoid modifying the original
        enhanced = InventoryItem(
            ipn=existing.ipn,  # IPN never changes
            keywords=self._merge_field(existing.keywords, new.keywords),
            category=existing.category,  # Category should be consistent for same IPN
            description=self._merge_field(existing.description, new.description),
            smd=self._merge_field(existing.smd, new.smd),
            value=existing.value,  # Value should be consistent for same IPN
            type=self._merge_field(existing.type, new.type),
            tolerance=self._merge_field(existing.tolerance, new.tolerance),
            voltage=self._merge_field(existing.voltage, new.voltage),
            amperage=self._merge_field(existing.amperage, new.amperage),
            wattage=self._merge_field(existing.wattage, new.wattage),
            lcsc=self._merge_field(existing.lcsc, new.lcsc),
            manufacturer=self._merge_field(existing.manufacturer, new.manufacturer),
            mfgpn=self._merge_field(existing.mfgpn, new.mfgpn),
            datasheet=self._merge_field(existing.datasheet, new.datasheet),
            package=self._merge_field(existing.package, new.package),
            distributor=self._merge_field(existing.distributor, new.distributor),
            distributor_part_number=self._merge_field(
                existing.distributor_part_number, new.distributor_part_number
            ),
            uuid=self._merge_field(existing.uuid, new.uuid),
            fabricator=self._merge_field(existing.fabricator, new.fabricator),
            priority=existing.priority,  # Keep existing priority
            source=existing.source,  # Keep original source
            source_file=existing.source_file,  # Keep original source file
            raw_data=self._merge_raw_data(existing.raw_data, new.raw_data),
        )

        return enhanced

    def _merge_duplicate_items(self, items: List[InventoryItem]) -> InventoryItem:
        """Merge multiple inventory items with the same IPN.

        Uses the first item as base and merges data from others.

        Args:
            items: List of InventoryItem objects with same IPN

        Returns:
            Merged InventoryItem
        """
        if not items:
            raise ValueError("Cannot merge empty list of items")

        if len(items) == 1:
            return items[0]

        # Use first item as base
        base = items[0]

        # Merge data from remaining items
        for item in items[1:]:
            base = self._enhance_item(base, item)

        return base

    def _merge_field(self, existing: str, new: str) -> str:
        """Merge two string fields, preferring existing non-empty values.

        Args:
            existing: Existing field value
            new: New field value

        Returns:
            Merged field value
        """
        # If existing has content, keep it
        if existing and existing.strip():
            return existing

        # Otherwise use new value if it has content
        if new and new.strip():
            return new

        # Both empty, return existing (which might be empty string)
        return existing

    def _merge_raw_data(self, existing: Dict, new: Dict) -> Dict:
        """Merge raw_data dictionaries, preserving existing data.

        Args:
            existing: Existing raw data dictionary
            new: New raw data dictionary

        Returns:
            Merged raw data dictionary
        """
        merged = existing.copy()

        # Add new keys that don't exist in existing
        for key, value in new.items():
            if key not in merged:
                merged[key] = value

        return merged
