"""Identity policy used by ``jbom promote``.

The ``build_ipn`` function returns a deterministic Internal Part Number for a
parsed component, when enough information is present.  The policy is
intentionally conservative: when an IPN cannot be confidently constructed, the
function returns an empty string and the workflow leaves the IPN column blank
so that downstream curation can fill it.
"""

from __future__ import annotations

import re

from jbom.services.promote.description_parser import ParsedDescription

__all__ = ["build_ipn"]


def _sanitize(token: str) -> str:
    if not token:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9._%+\-]", "", token)
    cleaned = cleaned.replace("..", ".")
    return cleaned


def _passive_ipn(prefix: str, parsed: ParsedDescription) -> str:
    parts: list[str] = [prefix]
    if parsed.value:
        parts.append(_sanitize(parsed.value))
    if parsed.type:
        parts.append(_sanitize(parsed.type))
    if parsed.tolerance:
        parts.append(_sanitize(parsed.tolerance))
    if parsed.package:
        parts.append(_sanitize(parsed.package))
    if parsed.voltage:
        parts.append(_sanitize(parsed.voltage))
    sanitized = [part for part in parts if part]
    if len(sanitized) <= 1:
        return ""
    return "_".join(sanitized)


def build_ipn(parsed: ParsedDescription) -> str:
    """Return a deterministic IPN for *parsed*, or an empty string.

    Today the policy emits IPNs for passive components (RES/CAP/IND) and LEDs.
    Other categories return ``""`` so canonical output leaves IPN blank.
    """

    category = (parsed.category or "").upper()
    if category == "RES":
        return _passive_ipn("RES", parsed)
    if category == "CAP":
        return _passive_ipn("CAP", parsed)
    if category == "IND":
        return _passive_ipn("IND", parsed)
    if category == "LED":
        parts = ["LED"]
        if parsed.wavelength:
            parts.append(_sanitize(parsed.wavelength))
        if parsed.package:
            parts.append(_sanitize(parsed.package))
        sanitized = [p for p in parts if p]
        if len(sanitized) <= 1:
            return ""
        return "_".join(sanitized)
    return ""
