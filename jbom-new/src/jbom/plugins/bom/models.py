"""BOM data models.

This module defines the data structures used throughout the BOM plugin,
representing components from schematics and aggregated BOM entries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any


@dataclass
class SchematicComponent:
    """Individual component from schematic file.

    Represents a single component as read from KiCad schematic files,
    before aggregation into BOM entries.
    """

    reference: str  # Component designator (R1, U1, etc.)
    value: str  # Component value (10K, 100nF, etc.)
    footprint: str  # Footprint identifier
    attributes: Dict[str, Any]  # Additional KiCad attributes
    sheet_path: str  # Sheet path for hierarchical designs

    @property
    def aggregation_key(self) -> tuple:
        """Key used for grouping components into BOM entries."""
        return (self.value, self.footprint)

    @property
    def is_dnp(self) -> bool:
        """Check if component is marked 'do not populate'."""
        dnp_attrs = [
            self.attributes.get("dnp", "").lower(),
            self.attributes.get("do_not_populate", "").lower(),
            self.value.lower(),
        ]
        return any(
            attr in ["true", "1", "yes", "dnp", "do not populate"] for attr in dnp_attrs
        )

    @property
    def is_excluded_from_bom(self) -> bool:
        """Check if component is marked 'exclude from BOM'."""
        exclude_attr = self.attributes.get("exclude_from_bom", "").lower()
        return exclude_attr in ["true", "1", "yes"]


@dataclass
class BOMEntry:
    """Aggregated BOM line item.

    Represents a single line in the BOM, potentially combining multiple
    components with the same value and footprint.
    """

    references: List[str]  # Component references ["R1", "R2", "R3"]
    value: str  # Component value
    footprint: str  # Footprint identifier
    quantity: int  # Total quantity needed
    attributes: Dict[str, Any] = field(default_factory=dict)  # Merged attributes

    # Supply chain fields (populated from component attributes)
    manufacturer: str = ""  # Component manufacturer (e.g., "Texas Instruments")
    mpn: str = ""  # Manufacturer Part Number (e.g., "LM358DR")
    description: str = ""  # Component description

    # Fabricator part number (unified field - meaning depends on fabricator)
    # JLCPCB: LCSC catalog number (e.g., "C7950")
    # PCBWay: Distributor part number (e.g., "595-LM358DR")
    # Generic: Manufacturer part number
    fabricator_part_number: str = ""

    # Raw component fields for flexible part number lookup
    component_fields: Dict[str, str] = field(default_factory=dict)

    @property
    def references_string(self) -> str:
        """Comma-separated string of references for display."""
        return ", ".join(sorted(self.references))

    def add_component(self, component: SchematicComponent) -> None:
        """Add a component to this BOM entry."""
        if component.reference not in self.references:
            self.references.append(component.reference)
            self.quantity = len(self.references)

            # Merge attributes (simple strategy: keep first occurrence)
            for key, value in component.attributes.items():
                if key not in self.attributes:
                    self.attributes[key] = value


@dataclass
class BOMData:
    """Complete BOM dataset.

    Container for all BOM information including entries, metadata,
    and source file information.
    """

    project_name: str  # Project name for output files
    schematic_files: List[Path]  # Source schematic files
    entries: List[BOMEntry]  # Aggregated BOM entries
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    @property
    def total_components(self) -> int:
        """Total number of individual components in the BOM."""
        return sum(entry.quantity for entry in self.entries)

    @property
    def total_line_items(self) -> int:
        """Total number of unique line items in the BOM."""
        return len(self.entries)

    def get_components_by_value(self, value: str) -> List[BOMEntry]:
        """Get all BOM entries with the specified value."""
        return [entry for entry in self.entries if entry.value == value]

    def sort_entries(self, sort_key: str = "references") -> None:
        """Sort BOM entries by the specified key."""
        if sort_key == "references":
            self.entries.sort(key=lambda e: e.references[0])
        elif sort_key == "value":
            self.entries.sort(key=lambda e: e.value)
        elif sort_key == "quantity":
            self.entries.sort(key=lambda e: e.quantity, reverse=True)
        elif sort_key == "footprint":
            self.entries.sort(key=lambda e: e.footprint)
