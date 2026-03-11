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

from dataclasses import dataclass

from jbom.common.value_parsing import canonical_value as _canonical_value_fn

_TILDE = "~"
_VERSION = (
    1  # Bump when encoding rules change; existing IDs with other versions are stale.
)


@dataclass(frozen=True)
class _OptionalIdFieldDef:
    """Mapping between the three representations of one optional ComponentID field.

    Attributes:
        profile_name:     Name used in the defaults YAML config (e.g. ``"voltage"``).
        component_id_key: Encoded key in the ComponentID string (e.g. ``"V"``).
        param_name:       Keyword argument name in ``make_component_id()`` (e.g.
                          ``"voltage"``).

    Adding a new encodable field requires exactly one new entry in
    ``OPTIONAL_ID_FIELD_DEFS`` plus a matching parameter in ``make_component_id``.
    """

    profile_name: str
    component_id_key: str
    param_name: str


# ---------------------------------------------------------------------------
# Canonical definition of every optional ComponentID field.
# This is the single source of truth — do not repeat these names elsewhere.
# ---------------------------------------------------------------------------
OPTIONAL_ID_FIELD_DEFS: tuple[_OptionalIdFieldDef, ...] = (
    _OptionalIdFieldDef("tolerance", "TOL", "tolerance"),
    _OptionalIdFieldDef("voltage", "V", "voltage"),
    _OptionalIdFieldDef("current", "A", "amperage"),
    _OptionalIdFieldDef("wattage", "W", "wattage"),
    _OptionalIdFieldDef("type", "TYPE", "component_type"),
)

# Derived convenience set of all valid profile_names — used for validation.
KNOWN_OPTIONAL_FIELD_NAMES: frozenset[str] = frozenset(
    d.profile_name for d in OPTIONAL_ID_FIELD_DEFS
)

# Keys used in a ComponentID, in alphabetical order (for documentation).
# The actual sort is performed at runtime so this list is informational only.
_KNOWN_KEYS = ("A", "CAT", "PKG", "TOL", "TYPE", "V", "VAL", "W")

# Maps legacy short column names to their canonical long-form equivalents.
# Apply these renames before stripping a row down to COMPONENT_ROW_COLUMNS.
COLUMN_NORMALISE: dict[str, str] = {
    "V": "Voltage",
    "A": "Current",
    "W": "Power",
}

# Canonical columns present in every COMPONENT row of combined.csv.
# Exactly the hash inputs (decoded to long form) plus decoded parametric values.
# COMPONENT rows MUST NOT carry per-instance or project-provenance fields
# (Project, UUID, IPN, Quantity, Designator, …).
COMPONENT_ROW_COLUMNS: tuple[str, ...] = (
    "RowType",
    "ComponentID",
    "Category",
    "Value",
    "Package",
    "Tolerance",
    "Voltage",
    "Current",
    "Power",
    "Type",
    "Resistance",
    "Capacitance",
    "Inductance",
)


def is_current_version(component_id: str) -> bool:
    """Return True if *component_id* was produced by the current encoding rules.

    A current-version ID starts with ``str(_VERSION)`` as its first
    ``|``-delimited segment.  Any other prefix — including the legacy
    ``REQ1`` prefix, a blank string, or a different version number —
    is considered stale.
    """
    if not component_id:
        return False
    first = component_id.split("|")[0]
    return first.isdigit() and int(first) == _VERSION


def is_null_value(value: str) -> bool:
    """Return True if *value* is effectively blank.

    A value is blank when it is the empty string or the KiCad null placeholder
    ``~`` (with optional surrounding whitespace).
    """
    return not value or value.strip() == _TILDE


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
    from jbom.common.component_classification import normalize_component_type

    cat = _norm(category) or "UNK"
    val = _canonical_value_fn(normalize_component_type(cat), _norm(value))

    fields: dict[str, str] = {
        "CAT": cat,
        "VAL": val,
        "PKG": _norm(package),
        "TOL": _norm(tolerance),
        "V": _norm(voltage),
        "A": _norm(amperage),
        "W": _norm(wattage),
        "TYPE": _norm(component_type),
    }

    parts = [f"{k}={v}" for k, v in sorted(fields.items()) if v or k == "CAT"]
    return "|".join([str(_VERSION)] + parts)


__all__ = [
    "OPTIONAL_ID_FIELD_DEFS",
    "KNOWN_OPTIONAL_FIELD_NAMES",
    "COLUMN_NORMALISE",
    "COMPONENT_ROW_COLUMNS",
    "is_current_version",
    "is_null_value",
    "make_component_id",
]
