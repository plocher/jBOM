"""Inventory search (Phase 6.3).

This service searches an external catalog (starting with Mouser) for candidates
that could fill gaps in an inventory file.

Design goals:
- No file I/O (CLI handles reading/writing)
- Deterministic, testable behavior
- No API calls required in unit tests (provider can be mocked)
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass

from jbom.common.component_classification import normalize_component_type
from jbom.common.types import Component, InventoryItem
from jbom.common.value_parsing import farad_to_eia, henry_to_eia, ohms_to_eia
from jbom.config.fabricators import FabricatorConfig
from jbom.config.suppliers import resolve_supplier_by_id
from jbom.services.search.cache import normalize_query
from jbom.services.search.filtering import SearchSorter, apply_default_filters
from jbom.services.search.models import SearchResult
from jbom.services.search.provider import SearchProvider
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)


@dataclass(frozen=True)
class InventorySearchCandidate:
    """One scored candidate for an inventory item."""

    result: SearchResult
    match_score: int


@dataclass(frozen=True)
class InventorySearchRecord:
    """Search outcomes for one inventory item."""

    inventory_item: InventoryItem
    query: str
    candidates: list[InventorySearchCandidate]
    error: str | None = None


def _normalize_ascii_value(text: str) -> str:
    """Normalize value strings to ASCII-friendly equivalents."""

    if not text:
        return ""

    t = str(text)
    t = t.replace("Ω", "")
    t = t.replace("ω", "")
    t = t.replace("μ", "u")
    t = t.replace("µ", "u")
    return " ".join(t.split()).strip()


def _category_token(category: str) -> str:
    """Return a normalized category token usable for comparisons."""

    return normalize_component_type(category or "")


def _category_matches(item_category: str, selector: str) -> bool:
    """Return True if an inventory category matches a selector token."""

    cat = (item_category or "").strip().upper()
    sel = (selector or "").strip().upper()
    if not cat or not sel:
        return False

    return cat == sel or cat.startswith(sel) or (sel in cat)


class InventorySearchService:
    """Service that searches external catalogs for inventory backfill candidates."""

    @staticmethod
    def is_sparse_for_fabricator(
        item: InventoryItem, fabricator: FabricatorConfig
    ) -> bool:
        """Return True if item has no PN for any supplier in fabricator.suppliers.

        This is Phase 1 "fab-relative sparseness": sparseness is defined relative to
        the fabricator's ordered supplier list.
        """

        # If a fabricator has no suppliers list, treat sparseness as "not applicable".
        if not fabricator.suppliers:
            return False

        for supplier_id in fabricator.suppliers:
            supplier = resolve_supplier_by_id(supplier_id)
            if supplier is None:
                # Unknown supplier IDs are warned at config load time.
                continue

            pn = ""
            if supplier.id == "lcsc":
                # InventoryReader populates InventoryItem.lcsc from several header variants.
                # TODO(#107): Once Phase 2 normalizes supplier lookups through inventory_column
                # synonyms everywhere, this special-case should be removable.
                pn = (item.lcsc or "").strip()
            else:
                pn = str(
                    (item.raw_data or {}).get(supplier.inventory_column, "")
                ).strip()

            if pn:
                return False

        return True

    @staticmethod
    def filter_sparse_items_for_fabricator(
        items: list[InventoryItem], *, fabricator: FabricatorConfig
    ) -> list[InventoryItem]:
        """Filter to items that are sparse for this fabricator."""

        return [
            i
            for i in items
            if InventorySearchService.is_sparse_for_fabricator(i, fabricator)
        ]

    def __init__(
        self,
        provider: SearchProvider,
        *,
        candidate_limit: int = 3,
        request_delay_seconds: float = 0.0,
    ) -> None:
        self._provider = provider
        self._candidate_limit = max(1, int(candidate_limit))
        self._request_delay_seconds = max(0.0, float(request_delay_seconds))
        self._matcher = SophisticatedInventoryMatcher(MatchingOptions())

    @staticmethod
    def filter_searchable_items(
        items: list[InventoryItem], *, categories: str | None
    ) -> list[InventoryItem]:
        """Filter to items suitable for catalog search.

        Pure logic — no provider or network access required.
        Safe to call without instantiating the service (e.g. dry-run mode).
        """

        default_searchable = {
            "RES",
            "CAP",
            "IND",
            "LED",
            "DIO",
            "IC",
            "Q",
            "REG",
            "OSC",
            "CONN",
            "CON",
        }

        excluded = {"SLK", "BOARD", "DOC", "MECH"}

        if categories:
            selectors = {
                _category_token(t) for t in re.split(r"[\s,]+", categories) if t.strip()
            }
        else:
            selectors = default_searchable

        out: list[InventoryItem] = []
        for item in items:
            cat_raw = (item.category or "").strip()
            if not cat_raw:
                continue

            cat_norm = _category_token(cat_raw)
            if cat_norm in excluded:
                continue

            min_value_len = 1 if cat_norm == "LED" else 2
            if not item.value or len(str(item.value).strip()) < min_value_len:
                continue

            if any(_category_matches(cat_raw, s) for s in selectors):
                out.append(item)

        return out

    def build_query(self, item: InventoryItem) -> str:
        """Build a provider-friendly keyword query string.

        Primary value token selection:
        - Passives (RES/CAP/IND): use the typed numeric field formatted back to an
          EIA string for consistent, normalised search terms.  Falls back to the
          raw Value string when the typed field is absent.
        - Non-passives: prefer the Name field (e.g. 'LM358D', 'AMS1117-3.3');
          fall back to Value when Name is empty.
        """

        parts: list[str] = []

        cat = _category_token(item.category)

        # Determine the primary value token.
        if cat == "RES" and item.resistance is not None:
            value_token = ohms_to_eia(item.resistance)
        elif cat == "CAP" and item.capacitance is not None:
            value_token = farad_to_eia(item.capacitance)
        elif cat == "IND" and item.inductance is not None:
            value_token = henry_to_eia(item.inductance)
        elif cat in ("RES", "CAP", "IND"):
            # Typed field absent — fall back to raw value string.
            value_token = _normalize_ascii_value(item.value)
        elif item.name:
            # Non-passive with an explicit component name.
            value_token = item.name
        else:
            value_token = _normalize_ascii_value(item.value)

        if value_token:
            parts.append(value_token)

        default_type_keywords = {
            "RES": "resistor",
            "CAP": "capacitor",
            "IND": "inductor",
            "LED": "LED",
            "DIO": "diode",
            "IC": "IC",
            "Q": "transistor",
            "REG": "regulator",
            "CON": "connector",
            "CONN": "connector",
        }

        supplier = resolve_supplier_by_id(self._provider.provider_id)
        type_keywords = dict(default_type_keywords)
        if supplier is not None and supplier.search_type_query_keywords:
            # Supplier config overrides/adds to the built-in defaults.
            type_keywords.update(supplier.search_type_query_keywords)

        if cat in type_keywords:
            parts.append(type_keywords[cat])

        if item.package:
            parts.append(_normalize_ascii_value(item.package))

        if (
            item.tolerance
            and item.tolerance.strip()
            and item.tolerance.strip().upper() != "N/A"
        ):
            parts.append(_normalize_ascii_value(item.tolerance))

        return " ".join(p for p in parts if p).strip()

    def search(self, items: list[InventoryItem]) -> list[InventorySearchRecord]:
        """Search for candidates for each inventory item.

        This implementation deduplicates provider calls by normalized query so that
        repeated inventory rows do not burn additional API quota.
        """

        # Phase 6.3 behavior: limit is purely service configuration.
        provider_limit = max(10, self._candidate_limit * 3)

        query_groups: dict[str, list[tuple[InventoryItem, str]]] = defaultdict(list)
        per_item_query: list[tuple[InventoryItem, str, str]] = []

        for item in items:
            query = self.build_query(item)
            key = normalize_query(query)
            per_item_query.append((item, query, key))

            if query:
                query_groups[key].append((item, query))

        # Dispatch unique queries.
        ranked_by_query: dict[str, list[SearchResult]] = {}
        error_by_query: dict[str, str] = {}

        for key, group in query_groups.items():
            # Keep the original (non-normalized) query string for the provider call.
            provider_query = group[0][1]

            try:
                raw_results = self._provider.search(
                    provider_query, limit=provider_limit
                )
                filtered = apply_default_filters(raw_results)
                ranked_by_query[key] = SearchSorter.rank(filtered)
            except Exception as exc:
                error_by_query[key] = str(exc)

            # Be conservative with public APIs (configurable for tests).
            if self._request_delay_seconds > 0:
                time.sleep(self._request_delay_seconds)

        # Fan-out per-item scoring.
        records: list[InventorySearchRecord] = []
        for item, query, key in per_item_query:
            if not query:
                records.append(
                    InventorySearchRecord(
                        inventory_item=item,
                        query=query,
                        candidates=[],
                        error="empty query",
                    )
                )
                continue

            if key in error_by_query:
                records.append(
                    InventorySearchRecord(
                        inventory_item=item,
                        query=query,
                        candidates=[],
                        error=error_by_query[key],
                    )
                )
                continue

            ranked = ranked_by_query.get(key, [])
            candidates = self._score_candidates(item, ranked)
            records.append(
                InventorySearchRecord(
                    inventory_item=item,
                    query=query,
                    candidates=candidates[: self._candidate_limit],
                )
            )

        return records

    def _score_candidates(
        self, base_item: InventoryItem, results: list[SearchResult]
    ) -> list[InventorySearchCandidate]:
        comp = self._inventory_item_to_component(base_item)

        scored: list[InventorySearchCandidate] = []
        for r in results:
            candidate_item = self._search_result_to_inventory_item(r, base_item)
            matches = self._matcher.find_matches(comp, [candidate_item])
            score = matches[0].score if matches else 0
            if score <= 0:
                continue
            scored.append(InventorySearchCandidate(result=r, match_score=score))

        scored.sort(
            key=lambda c: (
                -c.match_score,
                -c.result.stock_quantity,
                _price_to_float(c.result.price),
            )
        )
        return scored

    @staticmethod
    def _inventory_item_to_component(item: InventoryItem) -> Component:
        cat = _category_token(item.category)
        # Choose a lib_id that makes get_component_type return the correct type.
        lib_id_map = {
            "RES": "Device:R",
            "CAP": "Device:C",
            "IND": "Device:L",
            "DIO": "Device:D",
            "LED": "Device:LED",
            "Q": "Device:Q",
            "IC": "Device:U",
            "REG": "Device:U",
            "OSC": "Device:U",
            "CON": "Connector:Conn",
            "CONN": "Connector:Conn",
        }
        lib_id = lib_id_map.get(cat, f"{cat}:{item.ipn}" if cat else "Device:Generic")

        props: dict[str, str] = {}
        if item.tolerance:
            props["Tolerance"] = item.tolerance
        if item.voltage:
            props["Voltage"] = item.voltage
        if item.wattage:
            props["Wattage"] = item.wattage

        return Component(
            reference=item.ipn or "",
            lib_id=lib_id,
            value=item.value or "",
            footprint=item.package or "",
            properties=props,
        )

    @staticmethod
    def _search_result_to_inventory_item(
        result: SearchResult, base_item: InventoryItem
    ) -> InventoryItem:
        # For scoring we only need a subset of fields used by SophisticatedInventoryMatcher.
        # Category/value/package are the most important.
        return InventoryItem(
            ipn="",
            keywords="",
            category=base_item.category or "",
            description=result.description,
            smd="",
            value=_value_from_search_result(result, base_item),
            type="",
            tolerance=result.attributes.get("Tolerance", "") or base_item.tolerance,
            voltage=result.attributes.get("Voltage", "") or base_item.voltage,
            amperage="",
            wattage=result.attributes.get("Power", "") or base_item.wattage,
            lcsc="",
            manufacturer=result.manufacturer,
            mfgpn=result.mpn,
            datasheet=result.datasheet,
            package=_package_from_search_result(result, base_item),
            distributor=result.distributor,
            distributor_part_number=result.distributor_part_number,
            raw_data={},
        )

    def generate_report(self, records: list[InventorySearchRecord]) -> str:
        total = len(records)
        successes = sum(1 for r in records if r.candidates)
        failures = total - successes

        unique_queries = {
            normalize_query(r.query) for r in records if (r.query or "").strip()
        }

        by_cat: dict[str, dict[str, int]] = {}
        for r in records:
            cat = (r.inventory_item.category or "").strip().upper() or "(missing)"
            stats = by_cat.setdefault(cat, {"total": 0, "success": 0})
            stats["total"] += 1
            if r.candidates:
                stats["success"] += 1

        lines: list[str] = []
        lines.append("INVENTORY SEARCH REPORT")
        lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append(f"Total searchable items: {total}")
        lines.append(
            f"Unique queries dispatched: {len(unique_queries)} (of {total} items)"
        )
        if total:
            lines.append(
                f"Successful searches: {successes} ({successes/total*100:.1f}%)"
            )
            lines.append(f"Failed searches: {failures} ({failures/total*100:.1f}%)")
        lines.append("")
        lines.append("By category:")
        for cat, stats in sorted(by_cat.items()):
            rate = (
                (stats["success"] / stats["total"] * 100.0) if stats["total"] else 0.0
            )
            lines.append(f"  {cat}: {stats['success']}/{stats['total']} ({rate:.1f}%)")

        return "\n".join(lines) + "\n"

    def enhanced_csv_columns(self) -> list[str]:
        cols: list[str] = ["Search Query", "Search Success"]
        for idx in range(1, self._candidate_limit + 1):
            cols.extend(
                [
                    f"Candidate {idx} Manufacturer",
                    f"Candidate {idx} MPN",
                    f"Candidate {idx} Distributor PN",
                    f"Candidate {idx} Availability",
                    f"Candidate {idx} Stock",
                    f"Candidate {idx} Price",
                    f"Candidate {idx} Lifecycle",
                    f"Candidate {idx} Match Score",
                ]
            )
        return cols

    def enhance_inventory_rows(
        self,
        original_items: list[InventoryItem],
        *,
        original_field_order: list[str],
        records: list[InventorySearchRecord],
    ) -> list[dict[str, str]]:
        by_ipn = {r.inventory_item.ipn: r for r in records if r.inventory_item.ipn}

        enhanced: list[dict[str, str]] = []
        for item in original_items:
            row = dict(item.raw_data or {})

            # Ensure all original fields exist.
            for f in original_field_order:
                row.setdefault(f, "")

            rec = by_ipn.get(item.ipn)
            if rec is None:
                # Not searched / filtered out.
                row["Search Query"] = ""
                row["Search Success"] = ""
                for col in self.enhanced_csv_columns()[2:]:
                    row[col] = ""
                enhanced.append(row)
                continue

            row["Search Query"] = rec.query
            row["Search Success"] = "Yes" if rec.candidates else "No"

            # Fill candidate columns.
            for i in range(1, self._candidate_limit + 1):
                prefix = f"Candidate {i} "
                if i <= len(rec.candidates):
                    c = rec.candidates[i - 1]
                    row[prefix + "Manufacturer"] = c.result.manufacturer
                    row[prefix + "MPN"] = c.result.mpn
                    row[prefix + "Distributor PN"] = c.result.distributor_part_number
                    row[prefix + "Availability"] = c.result.availability
                    row[prefix + "Stock"] = str(c.result.stock_quantity)
                    row[prefix + "Price"] = c.result.price
                    row[prefix + "Lifecycle"] = c.result.lifecycle_status
                    row[prefix + "Match Score"] = str(c.match_score)
                else:
                    row[prefix + "Manufacturer"] = ""
                    row[prefix + "MPN"] = ""
                    row[prefix + "Distributor PN"] = ""
                    row[prefix + "Availability"] = ""
                    row[prefix + "Stock"] = ""
                    row[prefix + "Price"] = ""
                    row[prefix + "Lifecycle"] = ""
                    row[prefix + "Match Score"] = ""

            enhanced.append(row)

        return enhanced


def _price_to_float(price: str) -> float:
    try:
        t = re.sub(r"[^0-9\.]", "", price or "")
        return float(t)
    except ValueError:
        return float("inf")


def _value_from_search_result(result: SearchResult, base_item: InventoryItem) -> str:
    # Attempt to preserve semantic value for passives.
    cat = _category_token(base_item.category)

    if cat == "RES":
        return result.attributes.get("Resistance", "") or base_item.value

    if cat == "CAP":
        return result.attributes.get("Capacitance", "") or base_item.value

    if cat == "IND":
        return result.attributes.get("Inductance", "") or base_item.value

    return base_item.value


def _package_from_search_result(result: SearchResult, base_item: InventoryItem) -> str:
    return result.attributes.get("Package", "") or base_item.package


__all__ = [
    "InventorySearchCandidate",
    "InventorySearchRecord",
    "InventorySearchService",
]
