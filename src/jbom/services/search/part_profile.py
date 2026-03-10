"""Component identity classification — PartProfile and classify_item.

PartProfile encodes the stable electro-mechanical identity of a component:
category, package, technology subtype, and tolerance.  It is the canonical
query unit passed to search providers.

Subtype vocabulary is category-scoped::

    CAP: c0g | x7r | x5r | y5v | electrolytic | tantalum | film  (default x7r)
    IND: signal | power | ferrite                                  (default signal)
    RES: smd | wirewound | metal_film                             (default smd)

This module is the single authoritative home for technology-detection logic
previously scattered across ``suppliers/lcsc/query_planner.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jbom.common.constants import COMPONENT_TYPE_MAPPING
from jbom.common.types import InventoryItem

if TYPE_CHECKING:  # pragma: no cover
    from jbom.config.defaults import DefaultsConfig

# Canonical category codes supported in this module
_SUPPORTED: frozenset[str] = frozenset({"RES", "CAP", "IND"})

# CAP: MLCC dielectric codes scanned against item.type (uppercase), in priority order.
# NP0 is a synonym for C0G and is checked first so it maps correctly.
_CAP_MLCC_DIELECTRICS: tuple[tuple[str, str], ...] = (
    ("NP0", "c0g"),
    ("C0G", "c0g"),
    ("X5R", "x5r"),
    ("Y5V", "y5v"),
    ("X7R", "x7r"),
)

# IND: large SMD packages that indicate power inductors
_POWER_IND_PACKAGES: frozenset[str] = frozenset({"1210", "1812", "2520", "4532"})


@dataclass(frozen=True)
class PartProfile:
    """Stable electro-mechanical identity of a component.

    Used as the unit of identity when building parametric search queries.
    All fields are normalized strings; tolerance may be empty when absent.
    """

    category: str  # canonical: "RES" | "CAP" | "IND"
    package: str  # normalized package code, e.g. "0603"
    subtype: str  # category-scoped technology code (see module docstring)
    tolerance: str  # normalized tolerance string, e.g. "5%"; may be empty


def detect_subtype(item: InventoryItem, category: str) -> str:
    """Return the technology subtype for *item* given its canonical *category*.

    *category* should be a canonical code ("RES", "CAP", or "IND").  Aliases
    such as "RESISTOR" are also accepted.

    Returns a vocabulary-constrained string; see module docstring for the
    full vocabulary per category.  Returns an empty string for unsupported
    categories.
    """
    canon = _canon_category(category)
    if canon == "CAP":
        return _detect_cap_subtype(item)
    if canon == "IND":
        return _detect_ind_subtype(item)
    if canon == "RES":
        return _detect_res_subtype(item)
    return ""


def classify_item(
    item: InventoryItem,
    defaults: DefaultsConfig | None = None,  # noqa: ARG001 — reserved for future use
) -> PartProfile | None:
    """Classify *item* into a :class:`PartProfile`, or return ``None``.

    Returns ``None`` for categories outside the current classification scope
    (IC, CON, DIO, and all others not yet supported).

    Args:
        item:     Inventory item to classify.
        defaults: Defaults profile (reserved; not used in current scope).
    """
    canon = _canon_category(item.category)
    if canon is None:
        return None
    subtype = detect_subtype(item, canon)
    package = " ".join((item.package or "").strip().split())
    return PartProfile(
        category=canon,
        package=package,
        subtype=subtype,
        tolerance=(item.tolerance or "").strip(),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _canon_category(raw: str) -> str | None:
    """Return canonical category code (RES/CAP/IND) or None if unsupported."""
    upper = (raw or "").strip().upper()
    if not upper:
        return None
    if upper in _SUPPORTED:
        return upper
    code = COMPONENT_TYPE_MAPPING.get(upper)
    if code in _SUPPORTED:
        return code
    return None


def _fp_entry_name(footprint_full: str) -> str:
    """Return the entry name (after ':') from a KiCad footprint ID."""
    if not footprint_full or ":" not in footprint_full:
        return ""
    return footprint_full.split(":", 1)[1]


def _fp_lib_name(footprint_full: str) -> str:
    """Return the library nickname (before ':') from a KiCad footprint ID."""
    if not footprint_full or ":" not in footprint_full:
        return ""
    return footprint_full.split(":", 1)[0]


def _detect_cap_subtype(item: InventoryItem) -> str:
    """Detect CAP technology subtype from KiCad symbol/footprint signals and type field."""
    fp_entry = _fp_entry_name(item.footprint_full)
    fp_lib = _fp_lib_name(item.footprint_full)
    type_upper = (item.type or "").upper()

    # Tantalum is a distinct subtype — check library nickname before CP_ entry prefix
    # (tantalum footprints also use the CP_ prefix, so lib must win)
    if "Tantalum" in fp_lib:
        return "tantalum"
    if "TANTALUM" in type_upper:
        return "tantalum"

    # Strong structural signals: KiCad symbol name or footprint entry prefix
    if "Polarized" in item.symbol_name:
        return "electrolytic"
    if fp_entry.startswith("CP_"):
        return "electrolytic"

    # Remaining library hints → electrolytic (Elec, Polarized)
    if any(hint in fp_lib for hint in ("Elec", "Polarized")):
        return "electrolytic"

    # MLCC dielectric codes from type field (uppercase comparison)
    for code, subtype in _CAP_MLCC_DIELECTRICS:
        if code in type_upper:
            return subtype

    # Polymer/polyester film cap (e.g. "Film", "PET")
    if "FILM" in type_upper:
        return "film"

    # Default MLCC assumption
    return "x7r"


def _detect_ind_subtype(item: InventoryItem) -> str:
    """Detect IND technology subtype.

    Ferrite detection takes priority over power detection.
    Power detection uses symbol name and large-package structural signals.
    Default is signal/RF inductor.
    """
    description_upper = (item.description or "").upper()
    if "FERRITE" in description_upper:
        return "ferrite"

    if "_Core" in item.symbol_name or item.symbol_name == "L_Core":
        return "power"

    package = " ".join((item.package or "").strip().split()).upper()
    if package in _POWER_IND_PACKAGES:
        return "power"

    return "signal"


def _detect_res_subtype(item: InventoryItem) -> str:
    """Detect RES technology subtype from type field."""
    type_lower = (item.type or "").lower()
    if "wirewound" in type_lower:
        return "wirewound"
    if "metal film" in type_lower or "metal_film" in type_lower:
        return "metal_film"
    return "smd"


__all__ = ["PartProfile", "classify_item", "detect_subtype"]
