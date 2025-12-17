"""Fabricator definitions and part number lookup logic."""
from abc import ABC, abstractmethod
from typing import Dict, List, Type

from jbom.common.types import InventoryItem
from jbom.common.fields import normalize_field_name


class Fabricator(ABC):
    """Base class for PCB Fabricators."""

    name: str = "Generic"
    part_number_header: str = "Fabricator Part Number"

    @abstractmethod
    def get_part_number(self, item: InventoryItem) -> str:
        """Get the part number for this fabricator from an inventory item."""
        pass

    def get_name(self, item: InventoryItem) -> str:
        """Get the fabricator name. Can be dynamic based on item."""
        return self.name

    def matches(self, item: InventoryItem) -> bool:
        """Check if inventory item is supported by this fabricator."""
        return bool(self.get_part_number(item))


class JLCFabricator(Fabricator):
    """JLCPCB Fabricator logic."""

    name = "JLC"
    part_number_header = "LCSC"

    # Priority list of fields to check for JLC part number
    # Normalized field names (lowercase, no spaces, hyphens to underscores)
    PART_NUMBER_FIELDS = [
        "lcsc_part_#",
        "jlcpcb_part_#",
        "jlc_part",
        "lcsc_part",
        "lcsc",
        "jlc",
    ]

    def get_part_number(self, item: InventoryItem) -> str:
        # Check explicit LCSC field first (it's a first-class citizen in InventoryItem)
        if item.lcsc:
            return item.lcsc

        # Check raw data for other fields
        return _find_value_in_raw_data(item, self.PART_NUMBER_FIELDS)


class SeeedFabricator(Fabricator):
    """Seeed Studio Fabricator logic."""

    name = "Seeed"
    part_number_header = "Seeed SKU"

    PART_NUMBER_FIELDS = [
        "seeed_sku",
        "seeed_part",
    ]

    def get_part_number(self, item: InventoryItem) -> str:
        return _find_value_in_raw_data(item, self.PART_NUMBER_FIELDS)


class PCBWayFabricator(Fabricator):
    """PCBWay Fabricator logic."""

    name = "PCBWay"
    part_number_header = "MFGPN"

    PART_NUMBER_FIELDS = [
        "pcbway_part",
    ]

    def get_part_number(self, item: InventoryItem) -> str:
        # PCBWay often uses MFGPN + Distributor info, but here we just return the PN
        # The user instructions mention distributor, but for the BOM file we typically just need the PN
        # or we might need a specific "Distributor" column.
        # For now, let's return the best part number we can find.
        return _find_value_in_raw_data(item, self.PART_NUMBER_FIELDS)


def _find_value_in_raw_data(item: InventoryItem, field_candidates: List[str]) -> str:
    """Helper to find first matching non-empty value from raw_data."""
    # Create a normalized map of the raw data keys once
    # This is a bit inefficient if done for every item every time,
    # but InventoryItem structure is rigid.
    # Ideally InventoryLoader would normalize keys.
    # But InventoryLoader keeps original keys in raw_data (mostly).

    # Let's iterate through candidates and check against item.raw_data

    # We need to match normalized candidates against normalized raw keys
    for candidate in field_candidates:
        # Check specific attributes first if they exist
        if candidate == "lcsc" and item.lcsc:
            return item.lcsc
        if candidate in ["mfgpn", "mpn"] and item.mfgpn:
            return item.mfgpn

        # Check raw data
        for raw_key, value in item.raw_data.items():
            if not value:
                continue
            if normalize_field_name(raw_key) == candidate:
                return value

    return ""


class GenericFabricator(Fabricator):
    """Generic Fabricator logic (returns Manufacturer name and MFGPN)."""

    name = "Generic"

    def get_part_number(self, item: InventoryItem) -> str:
        # For Generic, we return the Manufacturer Part Number
        if item.mfgpn:
            return item.mfgpn
        if item.lcsc:
            return item.lcsc
        return ""

    def get_name(self, item: InventoryItem) -> str:
        """Get the manufacturer name as the fabricator name."""
        if item.manufacturer:
            return item.manufacturer
        return self.name

    def matches(self, item: InventoryItem) -> bool:
        """Generic fabricator matches all inventory items."""
        return True


# Registry of available fabricators
FABRICATORS: Dict[str, Type[Fabricator]] = {
    "jlc": JLCFabricator,
    "seeed": SeeedFabricator,
    "pcbway": PCBWayFabricator,
    "generic": GenericFabricator,
}


def get_fabricator(name: str) -> Fabricator:
    """Get fabricator instance by name (case insensitive)."""
    key = name.lower()
    if key in FABRICATORS:
        return FABRICATORS[key]()
    return GenericFabricator()  # Default to Generic if unknown
