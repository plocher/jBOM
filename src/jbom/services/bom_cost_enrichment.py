"""Optional BOM ``cost`` enrichment from LCSC/JLC bulk-break prices (#381).

Thin path only: when the caller requests the ``cost`` field, resolve an
LCSC C-number identity from the BOM entry and look up the unit price at
the bulk break quantity class (default qty 50). Missing identity or a
failed lookup leaves ``cost`` empty and never fails the BOM. Cost is
never written back to inventory.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from jbom.common.types import Diagnostic
from jbom.services.bom_generator import BOMData, BOMEntry
from jbom.suppliers.lcsc.pricing import (
    DEFAULT_BULK_BREAK_QTY,
    select_bulk_unit_price,
    select_bulk_unit_price_from_row,
)

log = logging.getLogger(__name__)

# LCSC distributor part numbers are ``C`` + digits (e.g. C25804).
_LCSC_C_NUMBER_RE = re.compile(r"^C\d+$", re.IGNORECASE)

# Attribute keys consulted (in order) for an existing C-number identity.
_LCSC_IDENTITY_KEYS: tuple[str, ...] = (
    "lcsc",
    "LCSC",
    "inv:lcsc",
    "fabricator_part_number",
    "jbom:fabricator_part_number",
    "spn",
    "SPN",
    "inv:spn",
)

# Callable: LCSC C-number -> raw JLCPCB row mapping (or None on miss/error).
LcscRowLookup = Callable[[str], Mapping[str, object] | None]


@dataclass(frozen=True)
class BomCostEnrichmentResult:
    """Result of optional bulk-cost enrichment for one BOM."""

    bom_data: BOMData
    diagnostics: tuple[Diagnostic, ...] = ()
    resolved_count: int = 0
    skipped_count: int = 0


def is_lcsc_c_number(value: str) -> bool:
    """Return True when *value* looks like an LCSC C-number."""

    return bool(_LCSC_C_NUMBER_RE.match(str(value or "").strip()))


def extract_lcsc_identity(entry: BOMEntry) -> str:
    """Extract an LCSC C-number identity from a BOM entry, if present.

    Checks common attribute keys (``lcsc``, fabricator part number, SPN)
    and returns the first value that matches ``C\\d+``. Empty string when
    no LCSC identity is available.
    """

    attributes = entry.attributes or {}
    for key in _LCSC_IDENTITY_KEYS:
        raw = attributes.get(key, "")
        text = str(raw or "").strip()
        if is_lcsc_c_number(text):
            # Normalize to canonical uppercase C-prefix form.
            return text.upper() if text[0].isalpha() else f"C{text[1:]}".upper()
    return ""


def cost_field_requested(selected_fields: Sequence[str] | None) -> bool:
    """Return True when the BOM field list includes the optional ``cost`` field."""

    for field_name in selected_fields or ():
        token = str(field_name or "").strip().lower()
        if token == "cost" or token.endswith(":cost"):
            return True
    return False


def resolve_entry_bulk_cost(
    entry: BOMEntry,
    *,
    lookup_row: LcscRowLookup,
    target_qty: int = DEFAULT_BULK_BREAK_QTY,
) -> str:
    """Resolve bulk unit cost for one BOM entry via *lookup_row*.

    Soft-fail contract: any missing identity, lookup miss, or exception
    yields ``\"\"`` and never raises to the caller.
    """

    identity = extract_lcsc_identity(entry)
    if not identity:
        return ""

    try:
        row = lookup_row(identity)
    except Exception as exc:  # noqa: BLE001 — soft-fail BOM cost path
        log.debug("BOM cost lookup failed for %s: %s", identity, exc)
        return ""

    if row is None:
        return ""

    price = select_bulk_unit_price_from_row(row, target_qty=target_qty)
    if price:
        return price

    # Allow callers to return a bare price-break list as the "row".
    if isinstance(row, Sequence) and not isinstance(row, (str, bytes, Mapping)):
        return select_bulk_unit_price(row, target_qty=target_qty)
    return ""


def enrich_bom_with_bulk_cost(
    bom_data: BOMData,
    selected_fields: Sequence[str] | None,
    *,
    lookup_row: LcscRowLookup | None = None,
    target_qty: int = DEFAULT_BULK_BREAK_QTY,
    verbose: bool = False,
) -> BomCostEnrichmentResult:
    """Attach ``cost`` attributes for BOM rows when the field is requested.

    When ``cost`` is not in *selected_fields*, returns *bom_data* unchanged
    (no lookups). When requested, each entry gets a ``cost`` attribute set
    to the bulk unit price or ``\"\"``. Lookups never fail the BOM.

    Args:
        bom_data: BOM rows to enrich.
        selected_fields: Field list from BOM generation / ``--fields``.
        lookup_row: Injectable LCSC row lookup (tests / offline fixtures).
            When omitted, uses the live JLCPCB search provider.
        target_qty: Bulk break quantity class (default 50).
        verbose: Emit info diagnostics about skip/resolve counts.

    Returns:
        :class:`BomCostEnrichmentResult` with updated BOM data and diagnostics.
    """

    if not cost_field_requested(selected_fields):
        return BomCostEnrichmentResult(bom_data=bom_data)

    effective_lookup = lookup_row or default_lcsc_row_lookup
    updated_entries: list[BOMEntry] = []
    resolved = 0
    skipped = 0
    diagnostics: list[Diagnostic] = []

    for entry in bom_data.entries:
        cost_value = resolve_entry_bulk_cost(
            entry,
            lookup_row=effective_lookup,
            target_qty=target_qty,
        )
        if cost_value:
            resolved += 1
        else:
            skipped += 1

        new_attrs = dict(entry.attributes or {})
        new_attrs["cost"] = cost_value
        updated_entries.append(
            BOMEntry(
                references=entry.references,
                value=entry.value,
                footprint=entry.footprint,
                quantity=entry.quantity,
                lib_id=entry.lib_id,
                attributes=new_attrs,
            )
        )

    if verbose:
        diagnostics.append(
            Diagnostic(
                "info",
                (
                    f"BOM cost field: bulk qty class {target_qty}; "
                    f"resolved={resolved}, empty={skipped}"
                ),
            )
        )

    return BomCostEnrichmentResult(
        bom_data=BOMData(
            project_name=bom_data.project_name,
            entries=updated_entries,
            metadata=dict(bom_data.metadata or {}),
        ),
        diagnostics=tuple(diagnostics),
        resolved_count=resolved,
        skipped_count=skipped,
    )


def default_lcsc_row_lookup(c_number: str) -> Mapping[str, object] | None:
    """Look up a JLCPCB component row for *c_number* via the live LCSC provider.

    Soft-fail: returns ``None`` when the provider is unavailable, the part
    is missing, or any error occurs. Intended for production BOM runs when
    ``cost`` is requested; unit tests inject fixtures instead.
    """

    identity = str(c_number or "").strip().upper()
    if not is_lcsc_c_number(identity):
        return None

    try:
        from jbom.config.providers import SearchProviderConfig
        from jbom.services.search.cache import InMemorySearchCache
        from jbom.suppliers.lcsc.provider import JlcpcbProvider

        cache = InMemorySearchCache()
        cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
        provider = JlcpcbProvider.from_config(cfg, cache=cache)
        if not provider.available():
            return None

        results = provider.search(identity, limit=10)
    except Exception as exc:  # noqa: BLE001 — soft-fail
        log.debug("default LCSC cost lookup error for %s: %s", identity, exc)
        return None

    for result in results:
        dpn = str(result.distributor_part_number or "").strip().upper()
        if dpn != identity:
            continue
        raw = result.raw_data
        if isinstance(raw, Mapping):
            return raw
    return None


def fixture_row_lookup_from_api_payload(
    payload: Mapping[str, object],
) -> LcscRowLookup:
    """Build an offline :class:`LcscRowLookup` from a captured JLCPCB JSON payload."""

    rows_by_code: dict[str, Mapping[str, object]] = {}
    data = payload.get("data") if isinstance(payload, Mapping) else None
    page = data.get("componentPageInfo") if isinstance(data, Mapping) else None
    rows = page.get("list") if isinstance(page, Mapping) else None
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            code = str(row.get("componentCode") or "").strip().upper()
            if is_lcsc_c_number(code):
                rows_by_code[code] = row

    def _lookup(c_number: str) -> Mapping[str, object] | None:
        return rows_by_code.get(str(c_number or "").strip().upper())

    return _lookup


__all__ = [
    "BomCostEnrichmentResult",
    "LcscRowLookup",
    "cost_field_requested",
    "default_lcsc_row_lookup",
    "enrich_bom_with_bulk_cost",
    "extract_lcsc_identity",
    "fixture_row_lookup_from_api_payload",
    "is_lcsc_c_number",
    "resolve_entry_bulk_cost",
]
