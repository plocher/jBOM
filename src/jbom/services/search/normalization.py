"""Shared text/identifier normalization helpers for search services/providers."""

from __future__ import annotations

import re

STANDARD_SMD_PACKAGES: frozenset[str] = frozenset(
    {"0201", "0402", "0603", "0805", "1206", "1210", "1812", "2010", "2512"}
)

_PACKAGE_TOKEN_PATTERN = re.compile(
    r"\b(0201|0402|0603|0805|1206|1210|1812|2010|2512)\b", re.IGNORECASE
)


def normalize_whitespace_token(text: str) -> str:
    """Collapse repeated whitespace and trim leading/trailing spaces."""

    return " ".join((text or "").strip().split())


def normalize_upper_token(text: str) -> str:
    """Return an uppercase, whitespace-normalized token."""

    return normalize_whitespace_token(text).upper()


def normalize_mpn_token(text: str) -> str:
    """Normalize MPN text for exact-match comparisons."""

    return re.sub(r"\s+", "", normalize_upper_token(text))


def normalize_manufacturer_token(text: str) -> str:
    """Normalize manufacturer text for case-insensitive equality checks."""

    return normalize_upper_token(text)


def extract_package_token(*texts: str) -> str:
    """Extract a normalized standard SMD package token from text candidates."""

    for text in texts:
        if not text:
            continue
        match = _PACKAGE_TOKEN_PATTERN.search(text.upper())
        if match:
            return match.group(1).upper()
    return ""


def footprint_entry_name(footprint_full: str) -> str:
    """Return the entry name (after ':') from a KiCad footprint ID."""

    if not footprint_full or ":" not in footprint_full:
        return ""
    return footprint_full.split(":", 1)[1]


def footprint_lib_name(footprint_full: str) -> str:
    """Return the library nickname (before ':') from a KiCad footprint ID."""

    if not footprint_full or ":" not in footprint_full:
        return ""
    return footprint_full.split(":", 1)[0]


__all__ = [
    "STANDARD_SMD_PACKAGES",
    "extract_package_token",
    "footprint_entry_name",
    "footprint_lib_name",
    "normalize_manufacturer_token",
    "normalize_mpn_token",
    "normalize_upper_token",
    "normalize_whitespace_token",
]
