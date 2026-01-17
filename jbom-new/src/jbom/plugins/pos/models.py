"""Data models for POS (Position/Placement) plugin.

These models represent component positioning data specifically for
POS file generation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ComponentPosition:
    """Represents a single component's position information for POS generation.

    This is the core data structure for POS files, containing all information
    needed to generate placement data for PCB assembly.
    """

    reference: str  # Component designator (e.g., "R1", "C2")
    value: str  # Component value (e.g., "1K", "0.1uF")
    package: str  # Package type (e.g., "0603", "SOIC-8")
    footprint: str  # Full footprint name (e.g., "R_0603_1608Metric")
    x_mm: float  # X position in millimeters
    y_mm: float  # Y position in millimeters
    rotation_deg: float  # Rotation in degrees
    layer: str  # Layer ("Top" or "Bottom")
    attributes: Dict[str, str] = field(default_factory=dict)  # Additional attributes


@dataclass
class PositionData:
    """Complete position data for a PCB project.

    Contains all components and metadata needed for POS file generation.
    """

    pcb_file: Path  # Source PCB file path
    components: List[ComponentPosition] = field(default_factory=list)
    board_title: str = ""  # Board title from PCB
    kicad_version: Optional[str] = None  # KiCad version used

    def filter_by_layer(self, layer: str) -> List[ComponentPosition]:
        """Filter components by layer (Top/Bottom)."""
        return [comp for comp in self.components if comp.layer.lower() == layer.lower()]

    def filter_by_package_type(
        self, package_patterns: List[str]
    ) -> List[ComponentPosition]:
        """Filter components by package patterns."""
        filtered = []
        for comp in self.components:
            for pattern in package_patterns:
                if pattern.lower() in comp.package.lower():
                    filtered.append(comp)
                    break
        return filtered

    def get_component_count(self) -> int:
        """Get total number of components."""
        return len(self.components)


@dataclass
class PosGenerationConfig:
    """Configuration for POS file generation."""

    output_format: str = "csv"  # Output format ("csv", "txt")
    include_layers: List[str] = field(default_factory=lambda: ["Top", "Bottom"])
    exclude_references: List[str] = field(default_factory=list)  # References to exclude
    units: str = "mm"  # Units ("mm", "mil")
    origin_mode: str = "absolute"  # Origin mode ("absolute", "aux", "grid")
    rotation_format: str = "degrees"  # Rotation format ("degrees", "radians")

    # CSV-specific options
    delimiter: str = ","
    quote_strings: bool = True
    include_header: bool = True

    # Column configuration
    column_mapping: Dict[str, str] = field(
        default_factory=lambda: {
            "reference": "Designator",
            "value": "Val",
            "package": "Package",
            "x": "Mid X",
            "y": "Mid Y",
            "rotation": "Rotation",
            "layer": "Layer",
        }
    )


# Type aliases for convenience
ComponentList = List[ComponentPosition]
LayerName = str  # "Top" or "Bottom"
PackageType = str  # Package identifier like "0603", "SOIC-8"
