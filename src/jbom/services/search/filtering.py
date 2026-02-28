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
from jbom.common.value_parsing import parse_res_to_ohms, parse_value_to_normal
from jbom.services.search.models import SearchResult


def _parse_voltage_to_volts(value: str) -> float | None:
    if not value:
        return None

    t = str(value).strip().lower().replace(" ", "")
    t = t.replace("μ", "u").replace("µ", "u")

    m = re.match(r"^([0-9]*\.?[0-9]+)(mv|v)$", t)
    if not m:
        return None

    try:
        num = float(m.group(1))
    except ValueError:
        return None

    unit = m.group(2)
    if unit == "mv":
        return num * 1e-3
    return num


def _close_enough(a: float, b: float, *, rel_tol: float = 0.001) -> bool:
    if a == b:
        return True
    if b == 0:
        return abs(a) < rel_tol
    return abs(a - b) <= abs(b) * rel_tol


class SearchFilter:
    """Client-side filtering helpers."""

    @staticmethod
    def filter_by_query(
        results: list[SearchResult], query: str, *, category: str = ""
    ) -> list[SearchResult]:
        """Filter results based on query terms matching parametric attributes.

        Current behavior mirrors legacy jBOM's implementation for resistors:
        - If the query contains a parseable resistance, keep only results whose
          "Resistance" attribute matches.
        - If the query contains a tolerance percentage, keep only exact matches
          when the result includes "Tolerance".

        Filtering is "fail open" when a result lacks parametric attributes.
        """

        filtered: list[SearchResult] = []

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
                target_volts = _parse_voltage_to_volts(token)
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

        for r in results:
            if not r.attributes:
                filtered.append(r)
                continue

            keep = True

            if target_value is not None:
                attr_name_by_cat = {
                    "RES": "Resistance",
                    "CAP": "Capacitance",
                    "IND": "Inductance",
                    "REG": "Output Voltage",
                }
                attr_name = attr_name_by_cat.get(cat, "")
                if attr_name:
                    raw_attr = r.attributes.get(attr_name, "")
                    if raw_attr:
                        attr_value = parse_value_to_normal(cat, raw_attr)
                        if attr_value is None or not _close_enough(
                            attr_value, target_value
                        ):
                            keep = False

            if keep and cat == "CAP" and target_volts is not None:
                vr_attr = r.attributes.get("Voltage Rating", "")
                if vr_attr:
                    attr_volts = _parse_voltage_to_volts(vr_attr)
                    # Interpret voltage rating as a minimum requirement.
                    if attr_volts is None or attr_volts + 1e-12 < target_volts:
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
    def rank(results: list[SearchResult], *, category: str = "") -> list[SearchResult]:
        """Rank by stock (desc), price (asc), then category value (asc)."""

        cat = normalize_component_type(category or "")
        attr_name_by_cat = {
            "RES": "Resistance",
            "CAP": "Capacitance",
            "IND": "Inductance",
            "REG": "Output Voltage",
        }
        attr_name = attr_name_by_cat.get(cat, "")

        def sort_key(r: SearchResult) -> tuple[int, float, float]:
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

            canonical = float("inf")
            if attr_name and r.attributes:
                raw = r.attributes.get(attr_name, "")
                if raw:
                    v = parse_value_to_normal(cat, raw)
                    if v is not None:
                        canonical = v

            return (-stock, price_value, canonical)

        return sorted(results, key=sort_key)


__all__ = ["SearchFilter", "SearchSorter", "apply_default_filters"]
