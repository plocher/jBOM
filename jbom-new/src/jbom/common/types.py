"""Data classes for jBOM components, inventory, and BOM entries."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path

# Default priority value
DEFAULT_PRIORITY = 99


@dataclass
class Component:
    """Represents a component from KiCad schematic"""

    reference: str
    lib_id: str
    value: str
    footprint: str
    uuid: str = ""  # KiCad UUID
    properties: Dict[str, str] = field(default_factory=dict)
    in_bom: bool = True
    exclude_from_sim: bool = False
    dnp: bool = False


@dataclass
class InventoryItem:
    """Represents an item from the inventory CSV"""

    ipn: str
    keywords: str
    category: str
    description: str
    smd: str
    value: str
    type: str
    tolerance: str
    voltage: str
    amperage: str
    wattage: str
    lcsc: str
    manufacturer: str
    mfgpn: str
    datasheet: str
    package: str = ""
    distributor: str = ""
    distributor_part_number: str = ""
    uuid: str = ""  # KiCad UUID for back-annotation
    fabricator: str = ""  # Specific fabricator for this item (e.g. "JLC", "Seeed")
    priority: int = (
        DEFAULT_PRIORITY  # Priority from CSV: 1=most desirable, higher=less desirable
    )
    # Source tracking for federated inventory
    source: str = "Unknown"  # e.g. "CSV", "JLC-Private", "Project"
    source_file: Optional[Path] = None  # Path to the file where this item was found
    raw_data: Dict[str, str] = field(default_factory=dict)


@dataclass
class BOMEntry:
    """Represents a bill of materials entry"""

    reference: str
    quantity: int
    value: str
    footprint: str
    lcsc: str
    manufacturer: str
    mfgpn: str
    description: str
    datasheet: str
    smd: str = ""
    distributor: str = ""
    distributor_part_number: str = ""
    match_quality: str = ""
    notes: str = ""
    # Fabricator specific fields
    fabricator: str = ""
    fabricator_part_number: str = ""
    # Debug fields (emitted when --verbose)
    priority: int = 0


__all__ = [
    "DEFAULT_PRIORITY",
    "Component",
    "InventoryItem",
    "BOMEntry",
]
