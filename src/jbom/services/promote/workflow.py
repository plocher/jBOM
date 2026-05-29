"""Promote workflow.

Turns a sequence of supplier-export rows into canonical jBOM inventory rows.

The workflow has three layers:

* a source adapter normalises the row into a :class:`SourceSeed`.
* the description parser extracts EM fields and category.
* an optional enrichment step calls the supplier provider's MPN lookup or
  keyword search to fill in supplier-side data such as ``Manufacturer``,
  ``MPN``, and ``Datasheet``.

The output is a list of canonical row dictionaries (string-valued) plus a
matching list of field names that the writer uses to render CSV output.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional

from jbom.common.types import InventoryItem
from jbom.common.value_parsing import farad_to_eia, henry_to_eia, ohms_to_eia
from jbom.services.promote.description_parser import (
    ParsedDescription,
    parse_description,
)
from jbom.services.promote.identity import build_ipn
from jbom.services.promote.source_adapters import (
    SourceAdapter,
    SourceSeed,
    select_adapter,
)
from jbom.services.search.inventory_search_service import (
    InventorySearchCandidate,
    InventorySearchRecord,
    InventorySearchService,
)


CANONICAL_FIELDS: tuple[str, ...] = (
    "RowType",
    "ComponentID",
    "IPN",
    "Category",
    "Value",
    "Package",
    "Description",
    "Keywords",
    "Manufacturer",
    "MFGPN",
    "Supplier",
    "SPN",
    "Datasheet",
    "Resistance",
    "Capacitance",
    "Inductance",
    "Tolerance",
    "Type",
    "V",
    "A",
    "W",
    "Wavelength",
    "mcd",
    "Angle",
    "Priority",
    "SupplierContext",
)


@dataclass
class PromotionStats:
    """Counters describing what a promote run did, useful in non-verbose output."""

    rows_total: int = 0
    rows_parsed: int = 0
    rows_with_canonical_value: int = 0
    rows_enriched_mpn: int = 0
    rows_enriched_search: int = 0
    rows_enrichment_skipped: int = 0
    rows_enrichment_misses: int = 0


@dataclass
class PromotedRow:
    """One canonical-row result paired with the diagnostics that produced it."""

    canonical: dict[str, str]
    extras: dict[str, str] = field(default_factory=dict)
    parsed: ParsedDescription = field(default_factory=ParsedDescription)
    enrichment_note: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_to_inventory_item(
    seed: SourceSeed,
    parsed: ParsedDescription,
    *,
    supplier_label: str,
) -> InventoryItem:
    """Build an :class:`InventoryItem` from seed + parsed fields."""

    return InventoryItem(
        ipn=build_ipn(parsed),
        keywords="",
        category=parsed.category,
        description=seed.description,
        smd="",
        value=parsed.value,
        type=parsed.type,
        tolerance=parsed.tolerance,
        voltage=parsed.voltage,
        amperage=parsed.current,
        wattage=parsed.power,
        supplier=supplier_label,
        spn=seed.spn,
        manufacturer=seed.manufacturer,
        mfgpn=seed.mfgpn,
        datasheet="",
        package=parsed.package,
        resistance=parsed.resistance,
        capacitance=parsed.capacitance,
        inductance=parsed.inductance,
    )


def _populate_canonical(
    item: InventoryItem,
    parsed: ParsedDescription,
    *,
    supplier_context: str,
) -> dict[str, str]:
    """Materialize an InventoryItem into a stable canonical row dict."""

    row: dict[str, str] = {field_name: "" for field_name in CANONICAL_FIELDS}
    row["RowType"] = "ITEM"
    row["IPN"] = item.ipn
    row["Category"] = item.category
    row["Value"] = item.value
    row["Package"] = item.package
    row["Description"] = item.description
    row["Manufacturer"] = item.manufacturer
    row["MFGPN"] = item.mfgpn
    row["Supplier"] = item.supplier
    row["SPN"] = item.spn
    row["Datasheet"] = item.datasheet
    row["Tolerance"] = item.tolerance
    row["Type"] = item.type
    row["V"] = item.voltage
    row["A"] = item.amperage
    row["W"] = item.wattage
    row["Wavelength"] = parsed.wavelength
    row["mcd"] = parsed.mcd
    row["Angle"] = parsed.angle
    row["SupplierContext"] = supplier_context
    if item.resistance is not None:
        row["Resistance"] = ohms_to_eia(item.resistance)
    if item.capacitance is not None:
        row["Capacitance"] = farad_to_eia(item.capacitance)
    if item.inductance is not None:
        row["Inductance"] = henry_to_eia(item.inductance)
    return row


def _format_extras(extras: Mapping[str, str]) -> dict[str, str]:
    return {key: str(value) for key, value in extras.items() if value}


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------


def _merge_search_result(canonical: dict[str, str], result) -> None:
    """Apply provider :class:`SearchResult` fields into canonical row."""

    if not canonical.get("Manufacturer") and getattr(result, "manufacturer", ""):
        canonical["Manufacturer"] = result.manufacturer
    if not canonical.get("MFGPN") and getattr(result, "mpn", ""):
        canonical["MFGPN"] = result.mpn
    if not canonical.get("Datasheet") and getattr(result, "datasheet", ""):
        canonical["Datasheet"] = result.datasheet
    if getattr(result, "distributor_part_number", "") and not canonical.get("SPN"):
        canonical["SPN"] = result.distributor_part_number
    # Manufacturer-side description is usually richer; do not overwrite existing
    # source description even when provider returns something.


def _enrich_row(
    canonical: dict[str, str],
    item: InventoryItem,
    *,
    service: Optional[InventorySearchService],
    verbose: bool,
) -> tuple[str, bool, bool]:
    """Best-effort supplier enrichment.

    Returns ``(note, used_mpn, used_search)``.
    """

    if service is None:
        return ("no-enrich", False, False)

    provider = getattr(service, "_provider", None)
    used_mpn = False
    used_search = False

    if provider is not None and item.mfgpn:
        try:
            result = provider.lookup_by_mpn(item.manufacturer, item.mfgpn)
        except Exception as exc:  # pragma: no cover - defensive
            if verbose:
                print(
                    f"  enrichment: MPN lookup failed for {item.mfgpn!r}: {exc}",
                    file=sys.stderr,
                )
            result = None
        if result is not None:
            _merge_search_result(canonical, result)
            used_mpn = True
            return ("mpn-hit", used_mpn, used_search)

    # Keyword fallback via service.search, when item is searchable
    try:
        records: list[InventorySearchRecord] = service.search([item])
    except Exception as exc:  # pragma: no cover - defensive
        if verbose:
            print(
                f"  enrichment: keyword search failed: {exc}",
                file=sys.stderr,
            )
        return ("search-error", used_mpn, used_search)

    if not records:
        return ("no-candidates", used_mpn, used_search)

    record = records[0]
    candidates: list[InventorySearchCandidate] = record.candidates or []
    if not candidates:
        return ("no-candidates", used_mpn, used_search)

    _merge_search_result(canonical, candidates[0].result)
    used_search = True
    return ("search-hit", used_mpn, used_search)


# ---------------------------------------------------------------------------
# Workflow entry point
# ---------------------------------------------------------------------------


@dataclass
class PromotionResult:
    """Output of :func:`promote_rows`."""

    rows: list[PromotedRow]
    fieldnames: list[str]
    stats: PromotionStats


def promote_rows(
    source_rows: Iterable[Mapping[str, str]],
    *,
    adapter: SourceAdapter,
    supplier_context: str,
    supplier_label: str = "",
    search_service: Optional[InventorySearchService] = None,
    verbose: bool = False,
) -> PromotionResult:
    """Promote *source_rows* into canonical inventory rows.

    Args:
        source_rows: Iterable of source CSV row dictionaries (DictReader-style).
        adapter: Source adapter used to normalize each row.
        supplier_context: Stable string written to the ``SupplierContext`` column.
        supplier_label: Display label written to the ``Supplier`` column.  When
            empty, the column is left blank.
        search_service: Optional supplier search service.  When provided, MPN
            lookup is attempted first, with keyword search as fallback.  When
            ``None`` no enrichment is performed.
        verbose: When True, per-row provenance/enrichment notes are written to
            stderr.

    Returns:
        :class:`PromotionResult` carrying canonical rows, the ordered fieldname
        list (canonical + supplemental traceability columns), and a stats
        block describing what happened.
    """

    stats = PromotionStats()
    promoted: list[PromotedRow] = []
    supplemental_columns: list[str] = []
    supplemental_seen: set[str] = set()

    rows_list = list(source_rows)
    stats.rows_total = len(rows_list)

    for source_row in rows_list:
        seed = adapter.adapt(source_row)
        parsed = parse_description(
            seed.description,
            category_hint=seed.category_hint,
            package_hint=seed.package,
            mfgpn=seed.mfgpn,
            spn=seed.spn,
        )
        if parsed.category or parsed.value or parsed.package:
            stats.rows_parsed += 1
        if parsed.value:
            stats.rows_with_canonical_value += 1

        item = _seed_to_inventory_item(
            seed, parsed, supplier_label=supplier_label or seed.manufacturer
        )
        canonical = _populate_canonical(item, parsed, supplier_context=supplier_context)

        note = "no-enrich"
        if search_service is not None:
            note, used_mpn, used_search = _enrich_row(
                canonical,
                item,
                service=search_service,
                verbose=verbose,
            )
            if used_mpn:
                stats.rows_enriched_mpn += 1
            if used_search:
                stats.rows_enriched_search += 1
            if note in {"no-candidates", "search-error"}:
                stats.rows_enrichment_misses += 1
        else:
            stats.rows_enrichment_skipped += 1

        extras = _format_extras(seed.extras)
        for key in extras.keys():
            if key not in supplemental_seen and key not in CANONICAL_FIELDS:
                supplemental_seen.add(key)
                supplemental_columns.append(key)

        if verbose:
            provenance_summary = ", ".join(
                f"{k}={v}" for k, v in parsed.provenance.items()
            )
            print(
                f"  promote: spn={seed.spn or '-'} category={parsed.category or '-'} "
                f"value={parsed.value or '-'} enrich={note} parsed=[{provenance_summary}]",
                file=sys.stderr,
            )

        promoted.append(
            PromotedRow(
                canonical=canonical,
                extras=extras,
                parsed=parsed,
                enrichment_note=note,
            )
        )

    fieldnames = list(CANONICAL_FIELDS) + supplemental_columns
    return PromotionResult(rows=promoted, fieldnames=fieldnames, stats=stats)


__all__ = [
    "CANONICAL_FIELDS",
    "PromotionResult",
    "PromotionStats",
    "PromotedRow",
    "promote_rows",
    "select_adapter",
]
