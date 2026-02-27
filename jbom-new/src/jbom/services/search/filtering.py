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

from jbom.common.value_parsing import parse_res_to_ohms
from jbom.services.search.models import SearchResult


class SearchFilter:
    """Client-side filtering helpers."""

    @staticmethod
    def filter_by_query(results: list[SearchResult], query: str) -> list[SearchResult]:
        """Filter results based on query terms matching parametric attributes.

        Current behavior mirrors legacy jBOM's implementation for resistors:
        - If the query contains a parseable resistance, keep only results whose
          "Resistance" attribute matches.
        - If the query contains a tolerance percentage, keep only exact matches
          when the result includes "Tolerance".

        Filtering is "fail open" when a result lacks parametric attributes.
        """

        filtered: list[SearchResult] = []

        # Resistance target.
        # Queries are usually multi-token (e.g. "10K resistor 0603"), while the
        # value parser expects a single value token.
        target_ohms = None
        for token in re.split(r"[\s,]+", query or ""):
            if not token:
                continue
            target_ohms = parse_res_to_ohms(token)
            if target_ohms is not None:
                break

        # Tolerance target (e.g. "1%", "5%")
        target_tol: float | None = None
        tol_match = re.search(r"(\d+(?:\.\d+)?)%", query)
        if tol_match:
            try:
                target_tol = float(tol_match.group(1))
            except ValueError:
                target_tol = None

        for r in results:
            if not r.attributes:
                filtered.append(r)
                continue

            keep = True

            if target_ohms is not None:
                res_attr = r.attributes.get("Resistance", "")
                if res_attr:
                    attr_ohms = parse_res_to_ohms(res_attr)
                    if attr_ohms is None or abs(attr_ohms - target_ohms) > (
                        target_ohms * 0.001
                    ):
                        keep = False

            if keep and target_tol is not None:
                tol_attr = r.attributes.get("Tolerance", "")
                if tol_attr:
                    clean_tol = tol_attr.replace("%", "").replace("+/-", "").strip()
                    try:
                        attr_tol = float(clean_tol)
                        if attr_tol != target_tol:
                            keep = False
                    except ValueError:
                        # If the result tolerance is unparsable, fail open.
                        pass

            if keep:
                filtered.append(r)

        return filtered


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
    def rank(results: list[SearchResult]) -> list[SearchResult]:
        """Rank by stock (desc) then price (asc)."""

        def sort_key(r: SearchResult) -> tuple[int, float]:
            stock = r.stock_quantity
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
            return (-stock, price_value)

        return sorted(results, key=sort_key)


__all__ = ["SearchFilter", "SearchSorter", "apply_default_filters"]
