"""Source-export adapters for ``jbom promote``.

Adapters convert one row of a supplier-export CSV into a normalized *source
seed* dictionary that the promote workflow can extend with parsed EM fields,
identity, and supplier-enrichment data.

The seed dict is intentionally small and canonical:

* ``spn``         — supplier part number (e.g. JLCPCB ``C12345``)
* ``mfgpn``       — manufacturer part number
* ``manufacturer``— manufacturer name (when source provides one)
* ``description`` — free-text description
* ``package``     — package / footprint code (e.g. ``0603``)
* ``category_hint`` — best-effort source category string (e.g. ``Capacitors``)
* ``supplier``    — supplier label (filled by workflow from CLI context)
* ``extras``      — supplemental source columns (qty, pricing, etc.) for
                    traceability; preserved in the canonical output.

Adapters are pure data shape; they do not parse free-text descriptions or
classify components — that is the responsibility of the description parser
and identity policy modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping


@dataclass
class SourceSeed:
    """Normalized seed row produced by a source adapter."""

    spn: str = ""
    mfgpn: str = ""
    manufacturer: str = ""
    description: str = ""
    package: str = ""
    category_hint: str = ""
    extras: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Header signatures
# ---------------------------------------------------------------------------

# Columns whose presence strongly indicates a JLCPCB private parts export.
# JLCPCB has shipped exports with both ``JLC Part #`` and ``JLCPCB Part #``
# headers, so the signature accepts either spelling.
_JLC_PART_NUMBER_HEADERS: tuple[str, ...] = ("JLCPCB Part #", "JLC Part #")
_JLC_SIGNATURE_COLUMNS: frozenset[str] = frozenset({"MFR Part #"})

# Supplemental JLC columns that should be preserved verbatim for traceability.
_JLC_TRACE_COLUMNS: tuple[str, ...] = (
    "JLCPCB Parts Qty",
    "Global Sourcing Parts Qty",
    "Consigned Parts Qty",
    "Unit Price($)",
    "Total Price($)",
)


def detect_source_format(headers: Iterable[str]) -> str:
    """Return the best-fit source-format identifier for the given headers.

    Args:
        headers: Iterable of column names from the source CSV.

    Returns:
        ``"jlc"`` when the headers match a JLCPCB export signature, otherwise
        ``"generic"``.
    """

    header_set = {(h or "").strip() for h in headers}
    has_jlc_part_header = any(
        header in header_set for header in _JLC_PART_NUMBER_HEADERS
    )
    if has_jlc_part_header and _JLC_SIGNATURE_COLUMNS.issubset(header_set):
        return "jlc"
    return "generic"


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------


class SourceAdapter:
    """Base class for supplier-export source adapters."""

    #: Stable adapter identifier (``"jlc"`` / ``"generic"`` / ...).
    source_format: str = "generic"

    def adapt(self, row: Mapping[str, str]) -> SourceSeed:
        """Convert one source row into a :class:`SourceSeed`.

        Subclasses must implement this method.
        """

        raise NotImplementedError


# ---------------------------------------------------------------------------
# JLCPCB private-parts export adapter
# ---------------------------------------------------------------------------


class JlcpcbExportAdapter(SourceAdapter):
    """Adapter for JLCPCB ``Parts Inventory on JLCPCB.csv`` exports."""

    source_format = "jlc"

    def adapt(self, row: Mapping[str, str]) -> SourceSeed:
        get = lambda key: str((row.get(key) or "")).strip()  # noqa: E731

        spn = ""
        for header in _JLC_PART_NUMBER_HEADERS:
            spn = get(header)
            if spn:
                break

        extras: dict[str, str] = {}
        for column in _JLC_TRACE_COLUMNS:
            value = get(column)
            if value:
                extras[column] = value

        return SourceSeed(
            spn=spn,
            mfgpn=get("MFR Part #"),
            manufacturer="",  # JLC export does not provide manufacturer as a column
            description=get("Description"),
            package=get("Footprint"),
            category_hint=get("Category"),
            extras=extras,
        )


# ---------------------------------------------------------------------------
# Generic CSV adapter (best-effort canonical-name passthrough)
# ---------------------------------------------------------------------------


_GENERIC_SPN_KEYS = (
    "SPN",
    "Supplier Part Number",
    "Supplier PN",
    "JLCPCB Part #",
    "JLC Part #",
)
_GENERIC_MFGPN_KEYS = ("MFGPN", "MPN", "MFR Part #", "Manufacturer Part Number")
_GENERIC_MANUFACTURER_KEYS = ("Manufacturer", "Mfg", "Mfr")
_GENERIC_PACKAGE_KEYS = ("Package", "Footprint")
_GENERIC_CATEGORY_KEYS = ("Category", "Type", "Part Type")
_GENERIC_DESCRIPTION_KEYS = ("Description", "Desc")


def _first_nonempty(row: Mapping[str, str], keys: Iterable[str]) -> str:
    """Return the first non-empty value in *row* for any of *keys*."""

    for key in keys:
        value = (row.get(key) or "").strip() if row.get(key) is not None else ""
        if value:
            return value
    return ""


class GenericCsvAdapter(SourceAdapter):
    """Best-effort adapter that maps common canonical names through."""

    source_format = "generic"

    def adapt(self, row: Mapping[str, str]) -> SourceSeed:
        spn = _first_nonempty(row, _GENERIC_SPN_KEYS)
        mfgpn = _first_nonempty(row, _GENERIC_MFGPN_KEYS)
        manufacturer = _first_nonempty(row, _GENERIC_MANUFACTURER_KEYS)
        package = _first_nonempty(row, _GENERIC_PACKAGE_KEYS)
        category_hint = _first_nonempty(row, _GENERIC_CATEGORY_KEYS)
        description = _first_nonempty(row, _GENERIC_DESCRIPTION_KEYS)

        # Preserve any source columns that did not feed into canonical fields.
        used_keys = set(
            _GENERIC_SPN_KEYS
            + _GENERIC_MFGPN_KEYS
            + _GENERIC_MANUFACTURER_KEYS
            + _GENERIC_PACKAGE_KEYS
            + _GENERIC_CATEGORY_KEYS
            + _GENERIC_DESCRIPTION_KEYS
        )
        extras: dict[str, str] = {}
        for key, value in row.items():
            key_norm = (key or "").strip()
            if not key_norm or key_norm in used_keys:
                continue
            value_str = (value or "").strip() if value is not None else ""
            if value_str:
                extras[key_norm] = value_str

        return SourceSeed(
            spn=spn,
            mfgpn=mfgpn,
            manufacturer=manufacturer,
            description=description,
            package=package,
            category_hint=category_hint,
            extras=extras,
        )


# ---------------------------------------------------------------------------
# Adapter selection
# ---------------------------------------------------------------------------


def select_adapter(source_format: str) -> SourceAdapter:
    """Return the adapter implementation for *source_format*.

    Args:
        source_format: Adapter identifier (``"jlc"``, ``"generic"``).

    Returns:
        An instance of the requested adapter.

    Raises:
        ValueError: When *source_format* is not a recognised adapter.
    """

    key = (source_format or "").strip().lower()
    if key == "jlc":
        return JlcpcbExportAdapter()
    if key == "generic":
        return GenericCsvAdapter()
    raise ValueError(f"Unknown promote source format: {source_format!r}")


__all__ = [
    "GenericCsvAdapter",
    "JlcpcbExportAdapter",
    "SourceAdapter",
    "SourceSeed",
    "detect_source_format",
    "select_adapter",
]
