"""Package-related constants."""
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


__all__ = ["PackageType"]
