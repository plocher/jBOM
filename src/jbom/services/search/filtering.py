"""Search filtering and sorting.

This module contains pure client-side helpers:
- Parametric filtering (query-driven)
- Default availability/lifecycle filtering
- Sorting/ranking

All functions are side-effect free.
"""

from __future__ import annotations

import re
from typing import Iterable

from jbom.common.component_classification import normalize_component_type
from jbom.common.value_parsing import (
    parse_res_to_ohms,
    parse_value_to_normal,
    parse_voltage_to_volts,
)
from jbom.services.search.models import SearchResult


_CATEGORY_ATTR_NAME: dict[str, str] = {
    "RES": "Resistance",
    "CAP": "Capacitance",
    "IND": "Inductance",
    "REG": "Output Voltage",
}

_KNOWN_PACKAGE_TOKENS: tuple[str, ...] = (
    "0201",
    "0402",
    "0603",
    "0805",
    "1206",
    "1210",
    "1812",
    "2010",
    "2512",
)

_QUERY_CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "RES": ("RESISTOR", "RESISTORS"),
    "CAP": ("CAPACITOR", "CAPACITORS"),
    "IND": ("INDUCTOR", "INDUCTORS"),
}
_PASSIVE_STOCK_MIN_QTY = 2000
_PASSIVE_STOCK_INTENTS = frozenset({"RES", "CAP"})
_BASIC_PART_RELEVANCE_BOOST = 2

_PACKAGE_PATTERN = re.compile(
    r"\b(0201|0402|0603|0805|1206|1210|1812|2010|2512)\b", re.IGNORECASE
)


def _close_enough(a: float, b: float, *, rel_tol: float = 0.001) -> bool:
    if a == b:
        return True
    if b == 0:
        return abs(a) < rel_tol
    return abs(a - b) <= abs(b) * rel_tol


def _extract_package_token(result: SearchResult) -> str:
    """Extract normalized package token from attributes/raw data/description."""

    candidates: list[str] = []
    if result.attributes:
        candidates.append(str(result.attributes.get("Package", "")))
    if result.raw_data:
        for key in ("componentSpecificationEn", "package", "Package"):
            candidates.append(str(result.raw_data.get(key, "")))

    candidates.append(result.description or "")
    candidates.append(result.mpn or "")

    for text in candidates:
        if not text:
            continue
        match = _PACKAGE_PATTERN.search(text.upper())
        if match:
            return match.group(1).upper()

    return ""


class SearchFilter:
    """Client-side filtering helpers."""

    @staticmethod
    def filter_by_query(
        results: list[SearchResult], query: str, *, category: str = ""
    ) -> list[SearchResult]:
        """Filter results based on query terms matching parametric attributes.
        Category-aware behavior:
        Current behavior mirrors legacy jBOM's implementation for resistors:
        - If the query contains a parseable resistance, keep only results whose
          "Resistance" attribute matches.
        - If the query contains a tolerance percentage, keep only exact matches
          when the result includes "Tolerance".
        - When a strict core-attribute pass (Resistance/Capacitance/Inductance)
          yields at least one match, candidates missing that core attribute are
          excluded.
        - If strict pass yields zero results, automatically fall back to
          fail-open behavior so users still get clueful context.
        """

        cat = normalize_component_type(category or "")

        # Primary numeric target (category-specific). If category is not provided,
        # preserve legacy behavior: resistance matching only.
        target_value: float | None = None
        if cat:
            for token in re.split(r"[\s,]+", query or ""):
                if not token:
                    continue
                target_value = parse_value_to_normal(cat, token)
                if target_value is not None:
                    break
        else:
            for token in re.split(r"[\s,]+", query or ""):
                if not token:
                    continue
                target_value = parse_res_to_ohms(token)
                if target_value is not None:
                    cat = "RES"
                    break

        # Optional capacitor voltage rating target.
        target_volts: float | None = None
        if cat == "CAP":
            for token in re.split(r"[\s,]+", query or ""):
                if not token:
                    continue
                target_volts = parse_voltage_to_volts(token)
                if target_volts is not None:
                    break

        # Tolerance target (e.g. "1%", "5%")
        target_tol: float | None = None
        tol_match = re.search(r"(\d+(?:\.\d+)?)%", query)
        if tol_match:
            try:
                target_tol = float(tol_match.group(1))
            except ValueError:
                target_tol = None

        # Package token target (e.g. 0603, 0805).
        target_package = ""
        for token in re.split(r"[\s,/_-]+", query or ""):
            package_token = token.strip().upper()
            if package_token in _KNOWN_PACKAGE_TOKENS:
                target_package = package_token
                break

        attr_name = _CATEGORY_ATTR_NAME.get(cat, "")
        strict_core_attr = target_value is not None and bool(attr_name)
        strict_package = bool(
            target_package and any(_extract_package_token(r) for r in results)
        )

        def _filter_pass(
            *, require_core_attr: bool, require_package_match: bool
        ) -> list[SearchResult]:
            filtered: list[SearchResult] = []

            for r in results:
                keep = True

                if target_value is not None and attr_name:
                    raw_attr = (r.attributes or {}).get(attr_name, "")
                    if not raw_attr:
                        if require_core_attr:
                            keep = False
                    else:
                        attr_value = parse_value_to_normal(cat, raw_attr)
                        if attr_value is None or not _close_enough(
                            attr_value, target_value
                        ):
                            keep = False

                if keep and cat == "CAP" and target_volts is not None:
                    vr_attr = (r.attributes or {}).get("Voltage Rating", "")
                    if vr_attr:
                        attr_volts = parse_voltage_to_volts(vr_attr)
                        # Interpret voltage rating as a minimum requirement.
                        if attr_volts is None or attr_volts + 1e-12 < target_volts:
                            keep = False

                if keep and target_tol is not None:
                    tol_attr = (r.attributes or {}).get("Tolerance", "")
                    if tol_attr:
                        clean_tol = tol_attr.replace("%", "").replace("+/-", "").strip()
                        try:
                            attr_tol = float(clean_tol)
                            if attr_tol != target_tol:
                                keep = False
                        except ValueError:
                            # If the result tolerance is unparsable, fail open.
                            pass

                if keep and target_package:
                    observed_package = _extract_package_token(r)
                    if observed_package:
                        if observed_package != target_package and require_package_match:
                            keep = False
                    elif require_package_match:
                        keep = False

                if keep:
                    filtered.append(r)

            return filtered

        if strict_core_attr or strict_package:
            strict_filtered = _filter_pass(
                require_core_attr=strict_core_attr,
                require_package_match=strict_package,
            )
            if strict_filtered:
                return strict_filtered

        return _filter_pass(require_core_attr=False, require_package_match=False)


def apply_default_filters(results: Iterable[SearchResult]) -> list[SearchResult]:
    """Apply conservative default filters (in-stock, avoid obsolete/NRND).

    This is intended for interactive `jbom search` usage.

    Providers are encouraged to return raw results; these filters are applied
    by the CLI/service layer so `--all` can bypass them.
    """

    filtered: list[SearchResult] = []
    for r in results:
        if r.stock_quantity <= 0:
            continue

        status = (r.lifecycle_status or "").lower()
        if "obsolete" in status or "not recommended" in status:
            continue

        if "factory order" in (r.availability or "").lower():
            continue

        filtered.append(r)

    return filtered


class SearchSorter:
    """Sorting utilities."""

    @staticmethod
    def rank(
        results: list[SearchResult], *, category: str = "", query: str = ""
    ) -> list[SearchResult]:
        """Rank by relevance/price with passive stock used as a coarse eligibility gate."""

        cat = normalize_component_type(category or "")
        attr_name = _CATEGORY_ATTR_NAME.get(cat, "")
        relevance_context = _build_relevance_context(query)
        category_intent = relevance_context.get("category_intent", "") or cat
        ranked_pool = _apply_passive_stock_gate(
            results, category_intent=category_intent
        )

        def sort_key(r: SearchResult) -> tuple[int, float, float, str, str, str]:
            try:
                price_clean = (
                    (r.price or "")
                    .replace("$", "")
                    .replace("€", "")
                    .replace("£", "")
                    .strip()
                )
                price_value = float(price_clean)
            except ValueError:
                price_value = float("inf")

            canonical = float("inf")
            if attr_name and r.attributes:
                raw = r.attributes.get(attr_name, "")
                if raw:
                    v = parse_value_to_normal(cat, raw)
                    if v is not None:
                        canonical = v
            relevance = _query_relevance_score(r, context=relevance_context)
            manufacturer = (r.manufacturer or "").upper()
            mpn = (r.mpn or "").upper()
            supplier_pn = (r.distributor_part_number or "").upper()
            return (-relevance, price_value, canonical, manufacturer, mpn, supplier_pn)

        return sorted(ranked_pool, key=sort_key)


def _apply_passive_stock_gate(
    results: list[SearchResult], *, category_intent: str
) -> list[SearchResult]:
    """Filter low-stock passive candidates when better-stocked options exist."""

    if category_intent not in _PASSIVE_STOCK_INTENTS:
        return results

    sufficiently_stocked = [
        r for r in results if r.stock_quantity >= _PASSIVE_STOCK_MIN_QTY
    ]
    if sufficiently_stocked:
        return sufficiently_stocked

    # Fail-open: preserve context when all candidates are low stock.
    return results


def _build_relevance_context(query: str) -> dict[str, str]:
    """Parse query once for ranking relevance calculations."""

    query_tokens = [
        tok.strip().upper()
        for tok in re.split(r"[\s,/_-]+", query or "")
        if tok.strip()
    ]

    requested_package = ""
    for tok in query_tokens:
        if tok in _KNOWN_PACKAGE_TOKENS:
            requested_package = tok
            break

    category_intent = ""
    for category_key, hints in _QUERY_CATEGORY_HINTS.items():
        if any(hint in query_tokens for hint in hints):
            category_intent = category_key
            break

    return {
        "requested_package": requested_package,
        "category_intent": category_intent,
        "query_tokens": " ".join(query_tokens),
    }


def _query_relevance_score(result: SearchResult, *, context: dict[str, str]) -> int:
    """Score a result against query terms, package intent, and category intent."""

    query_tokens = [tok for tok in context.get("query_tokens", "").split(" ") if tok]
    if not query_tokens:
        return 0

    haystack = " ".join(
        [
            result.description or "",
            result.category or "",
            result.manufacturer or "",
            result.mpn or "",
            " ".join(f"{k} {v}" for k, v in (result.attributes or {}).items()),
        ]
    ).upper()

    score = 0
    for tok in query_tokens:
        if len(tok) < 2:
            continue
        if tok in haystack:
            score += 1

    requested_package = context.get("requested_package", "")
    if requested_package:
        if requested_package in haystack:
            score += 8
        else:
            mismatched_package = any(
                pkg in haystack
                for pkg in _KNOWN_PACKAGE_TOKENS
                if pkg != requested_package
            )
            if mismatched_package:
                score -= 8

    category_intent = context.get("category_intent", "")
    if category_intent == "RES":
        if "RESISTOR" in haystack:
            score += 6
        elif "THERMISTOR" in haystack:
            score -= 10
        else:
            score -= 4
    elif category_intent == "CAP":
        if "CAPACITOR" in haystack:
            score += 6
        else:
            score -= 4
    elif category_intent == "IND":
        if "INDUCTOR" in haystack:
            score += 6
        else:
            score -= 4
    if _component_library_tier(result) == "basic":
        score += _BASIC_PART_RELEVANCE_BOOST

    return score


def _component_library_tier(result: SearchResult) -> str:
    """Normalize provider library tier labels to basic/extended where possible."""

    if not result.raw_data:
        return ""

    raw = str(result.raw_data.get("componentLibraryType", "")).strip().lower()
    if raw in {"base", "basic"}:
        return "basic"
    if raw in {"expand", "extended"}:
        return "extended"
    return ""


__all__ = ["SearchFilter", "SearchSorter", "apply_default_filters"]
