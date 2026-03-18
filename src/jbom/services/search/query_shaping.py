"""Search query shaping helpers.

These helpers are intentionally lightweight and deterministic:
- normalize user/item query tokens for provider-facing keyword search
- apply small category-aware intent boosts (currently LED)
- keep behavior reusable across all search entry points
"""

from __future__ import annotations

import re

from jbom.common.component_classification import normalize_component_type
from jbom.services.search.normalization import STANDARD_SMD_PACKAGES

_LED_COLOR_ALIASES: dict[str, str] = {
    "R": "red",
    "G": "green",
    "B": "blue",
    "Y": "yellow",
    "A": "amber",
    "W": "white",
    "WW": "warm white",
    "CW": "cool white",
    "IR": "infrared",
    "UV": "ultraviolet",
}


def normalize_ascii_token(text: str) -> str:
    """Normalize text to ASCII-friendly tokens used in provider queries."""

    if not text:
        return ""

    t = str(text)
    t = t.replace("Ω", "")
    t = t.replace("ω", "")
    t = t.replace("μ", "u")
    t = t.replace("µ", "u")
    return " ".join(t.split()).strip()


def expand_led_color_token(value: str) -> str:
    """Expand shorthand LED color tokens (for example, ``G`` -> ``green``)."""

    normalized = normalize_ascii_token(value)
    if not normalized:
        return ""
    compact = normalized.upper().replace(" ", "")
    return _LED_COLOR_ALIASES.get(compact, normalized)


def shape_search_query(query: str, *, category: str = "", package: str = "") -> str:
    """Apply deterministic query shaping for provider-facing keyword search."""

    base = normalize_ascii_token(query)
    if not base:
        return ""

    tokens = [tok for tok in re.split(r"\s+", base) if tok]
    shaped: list[str] = []
    seen: set[str] = set()

    def _append(token: str) -> None:
        normalized = normalize_ascii_token(token)
        if not normalized:
            return
        for part in re.split(r"\s+", normalized):
            key = part.lower()
            if key in seen:
                continue
            seen.add(key)
            shaped.append(part)

    category_norm = normalize_component_type(category or "")
    is_led_intent = (
        category_norm == "LED"
        or any(tok.upper() in {"LED", "LEDS"} for tok in tokens)
        or "LIGHT EMITTING DIODE" in base.upper()
    )

    if is_led_intent:
        tokens = [expand_led_color_token(tok) for tok in tokens]

    for tok in tokens:
        _append(tok)

    if not is_led_intent:
        return " ".join(shaped)

    if "led" not in seen and "leds" not in seen:
        _append("LED")

    package_token = normalize_ascii_token(package).upper()
    has_standard_package = package_token in STANDARD_SMD_PACKAGES or any(
        tok.upper() in STANDARD_SMD_PACKAGES for tok in shaped
    )
    if has_standard_package:
        _append("SMD")

    _append("indicator")
    return " ".join(shaped)


__all__ = ["expand_led_color_token", "normalize_ascii_token", "shape_search_query"]
