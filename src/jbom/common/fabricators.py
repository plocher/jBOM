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

    def get_bom_columns(self) -> Dict[str, str]:
        """Get mapping of internal field names to fabricator-specific CSV headers.

        Returns:
            Dict mapping normalized field name to output header string.
            If a field is not in the dict, default field_to_header() conversion is used.
        """
        return {}

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
    part_number_header = "Distributor Part Number"

    PART_NUMBER_FIELDS = [
        "distributor_part_number",  # Normalized from inventory loader
        "pcbway_part",
    ]

    def get_part_number(self, item: InventoryItem) -> str:
        # PCBWay prefers Distributor SKU or their own PN
        # If neither, we can fall back to MFGPN in the BOM column,
        # but get_part_number specifically targets the "Fabricator Part Number" column.

        # 1. Check explicit distributor part number (from data model)
        if item.distributor_part_number:
            return item.distributor_part_number

        # 2. Check PCBWay specific field
        val = _find_value_in_raw_data(item, self.PART_NUMBER_FIELDS)
        if val:
            return val

        # 3. Fallback to MFGPN if nothing else, as PCBWay can source by MFGPN
        # However, usually we want this in a separate column.
        # For the "Fabricator Part Number" column specifically, we return the SKU.
        return ""

    def get_bom_columns(self) -> Dict[str, str]:
        """PCBWay specific column headers."""
        return {
            "reference": "Designator",
            "quantity": "Quantity",
            "value": "Value",
            "footprint": "Package",
            "i:package": "Package",
            "mfgpn": "Manufacturer Part Number",
            "manufacturer": "Manufacturer",
            "description": "Description",
            "fabricator_part_number": "Distributor Part Number",
        }


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
