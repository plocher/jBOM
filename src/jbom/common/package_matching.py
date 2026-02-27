"""Package matching utilities for jBOM.

This module provides utilities for extracting package information from
footprint strings and matching packages between components and inventory.
"""
from __future__ import annotations


# Package constants
class PackageType:
    """Package type lists for footprint and SMD identification"""

    SMD_PACKAGES = [  # SMD package list
        # Passive component packages (imperial)
        "0402",
        "0603",
        "0805",
        "1206",
        "1210",
        # Passive component packages (metric)
        "1005",
        "1608",
        "2012",
        "3216",
        "3225",
        "5050",
        # SOT packages
        "sot",
        "sot-23",
        "sot-223",
        "sot-89",
        "sot-143",
        "sot-323",
        "sc-70",
        "sot-23-5",
        "sot-23-6",
        "sot-353",
        "sot-363",
        # IC packages
        "soic",
        "ssop",
        "tssop",
        "qfp",
        "qfn",
        "dfn",
        "bga",
        "wlcsp",
        "lga",
        "plcc",
        "pqfp",
        "tqfp",
        "lqfp",
        "msop",
        "sc70",
        # Diode packages
        "sod-123",
        "sod-323",
        "sod-523",
        "sod-923",
        # Power packages (SMD)
        "dpak",
        "d2pak",
    ]

    THROUGH_HOLE_PACKAGES = [  # Through-hole package list
        "dip",
        "through-hole",
        "axial",
        "radial",
        "to-220",
        "to-252",
        "to-263",
        "to-39",
        "to-92",  # Through-hole power packages
    ]


def extract_package_from_footprint(footprint: str) -> str:
    """Extract package identifier from KiCad footprint string.

    Searches the footprint string for known SMD package patterns,
    preferring longer matches over shorter ones.

    Args:
        footprint: KiCad footprint string (e.g., "R_0603_1608Metric")

    Returns:
        Package identifier string (e.g., "0603"), or empty string if no match

    Examples:
        >>> extract_package_from_footprint("R_0603_1608Metric")
        "0603"
        >>> extract_package_from_footprint("C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")
        "0805"
        >>> extract_package_from_footprint("SOT-23")
        "sot-23"
        >>> extract_package_from_footprint("Unknown_Package")
        ""
    """
    if not footprint:
        return ""

    fp = footprint.lower()

    # Try direct matching with SMD packages (standard format)
    # Sort by length descending to match longer patterns first (e.g., 'sot-23' before 'sot')
    for pattern in sorted(PackageType.SMD_PACKAGES, key=len, reverse=True):
        if pattern in fp:
            return pattern

    return ""


def footprint_matches_package(footprint: str, package: str) -> bool:
    """Check if a component footprint matches an inventory package designation.

    Uses both direct matching and dash-removal variations to handle different
    naming conventions (e.g., "sot-23" vs "sot23").

    Args:
        footprint: Component footprint string
        package: Inventory package designation

    Returns:
        True if the footprint and package are considered a match

    Examples:
        >>> footprint_matches_package("SOT-23", "sot-23")
        True
        >>> footprint_matches_package("R_0603_1608Metric", "0603")
        True
        >>> footprint_matches_package("SOT-23", "sot23")  # Dash variation
        True
        >>> footprint_matches_package("R_0603_1608Metric", "0805")
        False
    """
    if not footprint or not package:
        return False

    footprint = footprint.lower()
    package = package.lower()

    # First try direct matching: check if any SMD package pattern
    # appears in both footprint and package (most common case)
    for pattern in PackageType.SMD_PACKAGES:
        if pattern in footprint and pattern in package:
            return True

    # Second try: automatic dash removal for inventory naming variations
    # Many inventories use 'sot23' instead of 'sot-23', 'sod123' instead of 'sod-123', etc.
    for pattern in PackageType.SMD_PACKAGES:
        if "-" in pattern:
            pattern_no_dash = pattern.replace("-", "")
            if pattern in footprint and pattern_no_dash in package:
                return True

    return False


__all__ = ["PackageType", "extract_package_from_footprint", "footprint_matches_package"]
