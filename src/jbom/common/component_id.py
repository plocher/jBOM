"""Canonical ComponentID generation.

A ComponentID is a stable, deterministic string that uniquely identifies
a component requirement type.  Two components with identical electrical
requirements must produce the same ComponentID regardless of which code
path constructs it.

Format:  ``{version}|{KEY=VALUE}|{KEY=VALUE}|...``

The **first segment** is always a bare integer version number.  It is not
a ``KEY=VALUE`` pair — it is metadata about the encoding rules in use.
Parsing: ``ver, *fields = cid.split('|')``.

When the encoding rules change, bump ``_VERSION`` and regeneration is
trivial: re-run ``make_component_id`` on the existing row's field data.
Stale IDs are detectable: ``cid.split('|')[0]`` is a digit string whose
value does not match the current ``_VERSION``.

Current encoding rules (version 1):
- Values are uppercased and stripped of leading/trailing whitespace.
- ``~`` (KiCad null placeholder) is normalised to ``""`` — equivalent to blank.
- Fields with an empty value after normalisation are omitted.
- ``CAT`` is always included (defaults to ``"UNK"`` when absent).
- Remaining included fields are sorted alphabetically by key.

Example:  RES 330R 0603 100mW  →  ``1|CAT=RES|PKG=0603|VAL=330R|W=100MW``

Any change to these rules requires a version bump.
Callers must never construct a ComponentID string directly.
"""
from __future__ import annotations

_TILDE = "~"
_VERSION = (
    1  # Bump when encoding rules change; existing IDs with other versions are stale.
)

# Keys used in a ComponentID, in alphabetical order (for documentation).
# The actual sort is performed at runtime so this list is informational only.
_KNOWN_KEYS = ("A", "CAT", "PKG", "TOL", "TYPE", "V", "VAL", "W")


def _norm(value: str) -> str:
    """Normalise a raw field value: strip, uppercase, treat ``~`` as blank."""
    v = value.strip().upper()
    return "" if v == _TILDE else v


def make_component_id(
    category: str,
    value: str,
    package: str,
    tolerance: str = "",
    voltage: str = "",
    amperage: str = "",
    wattage: str = "",
    component_type: str = "",
) -> str:
    """Return the canonical ComponentID for a component requirement.

    Args:
        category: Component category (e.g. ``"RES"``, ``"CAP"``).
        value: Electrical value (e.g. ``"10K"``, ``"100NF"``).
        package: Package / footprint code (e.g. ``"0603"``).
        tolerance: Tolerance constraint (e.g. ``"5%"``).  Blank / ``~`` → omitted.
        voltage: Voltage rating.  Blank / ``~`` → omitted.
        amperage: Current rating.  Blank / ``~`` → omitted.
        wattage: Power rating.  Blank / ``~`` → omitted.
        component_type: ``Type`` property (e.g. ``"X5R"``).  Blank / ``~`` → omitted.

    Returns:
        A ``|``-delimited ``KEY=VALUE`` string, keys sorted alphabetically,
        empty fields omitted.  ``CAT`` is always present.
    """
    fields: dict[str, str] = {
        "CAT": _norm(category) or "UNK",
        "VAL": _norm(value),
        "PKG": _norm(package),
        "TOL": _norm(tolerance),
        "V": _norm(voltage),
        "A": _norm(amperage),
        "W": _norm(wattage),
        "TYPE": _norm(component_type),
    }

    parts = [f"{k}={v}" for k, v in sorted(fields.items()) if v or k == "CAT"]
    return "|".join([str(_VERSION)] + parts)
