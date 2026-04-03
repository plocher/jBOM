"""Shared text/identifier normalization helpers for search services/providers."""

from __future__ import annotations

import re
from functools import lru_cache

from jbom.config.defaults import get_active_defaults_profile, get_defaults

_FALLBACK_STANDARD_SMD_PACKAGES: frozenset[str] = frozenset(
    {"0201", "0402", "0603", "0805", "1206", "1210", "1812", "2010", "2512"}
)


def get_standard_smd_packages() -> frozenset[str]:
    """Return configured package tokens from the active defaults profile."""

    active_profile = get_active_defaults_profile()
    return _cached_package_tokens(active_profile)


@lru_cache(maxsize=32)
def _cached_package_tokens(profile_name: str) -> frozenset[str]:
    cfg = get_defaults(profile_name)
    configured = {
        token.strip().upper()
        for token in cfg.get_search_package_tokens()
        if token and token.strip()
    }
    return frozenset(configured) if configured else _FALLBACK_STANDARD_SMD_PACKAGES


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
    package_tokens = get_standard_smd_packages()
    if not package_tokens:
        return ""
    pattern = re.compile(
        r"\b(" + "|".join(sorted(package_tokens, key=len, reverse=True)) + r")\b",
        re.IGNORECASE,
    )

    for text in texts:
        if not text:
            continue
        match = pattern.search(text.upper())
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
    "extract_package_token",
    "footprint_entry_name",
    "footprint_lib_name",
    "get_standard_smd_packages",
    "normalize_manufacturer_token",
    "normalize_mpn_token",
    "normalize_upper_token",
    "normalize_whitespace_token",
]
