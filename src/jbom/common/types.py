"""Data classes for jBOM components and inventory items."""
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
    source_file: Optional[
        Path
    ] = None  # Absolute path to the .kicad_sch this component came from


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
    supplier: str = (
        ""  # Supplier name matching the Supplier CSV column (e.g. "LCSC", "Mouser")
    )
    spn: str = ""  # Supplier Part Number from the SPN CSV column
    manufacturer: str = ""
    mfgpn: str = ""
    datasheet: str = ""
    row_type: str = "ITEM"  # COMPONENT or ITEM
    component_id: str = ""  # Requirement identity for COMPONENT rows
    package: str = ""
    uuid: str = ""  # KiCad UUID for back-annotation
    fabricator: str = ""  # Specific fabricator for this item (e.g. "JLC", "Seeed")
    priority: int = (
        DEFAULT_PRIORITY  # Priority from CSV: 1=most desirable, higher=less desirable
    )
    # KiCad harvest fidelity fields (populated at project harvest; round-trips via CSV)
    footprint_full: str = ""  # KiCad footprint ID, e.g. "Capacitor_SMD:CP_Elec_4x5.4mm"
    symbol_lib: str = ""  # KiCad symbol library nickname, e.g. "Device"
    symbol_name: str = ""  # KiCad symbol entry name, e.g. "C_Polarized"
    pins: str = ""  # connector pin count, e.g. "4"
    pitch: str = ""  # connector pitch, e.g. "2.54mm"
    # Typed parametric fields (decoded at intake from explicit columns or Value fallback)
    resistance: Optional[float] = None  # in ohms  (RES)
    capacitance: Optional[float] = None  # in farads (CAP)
    inductance: Optional[float] = None  # in henries (IND)
    name: str = ""  # component name for non-passives (e.g. "LM358D", "AMS1117-3.3")
    aliases: str = ""  # alternate identity tokens for matching (space/comma delimited)
    dnp: bool = False  # global do-not-populate marker from inventory
    # Source tracking for federated inventory
    source: str = "Unknown"  # e.g. "CSV", "JLC-Private", "Project"
    source_file: Optional[Path] = None  # Path to the file where this item was found
    raw_data: Dict[str, str] = field(default_factory=dict)


__all__ = [
    "DEFAULT_PRIORITY",
    "Component",
    "InventoryItem",
]
