"""Sophisticated inventory matching service interface.

Phase 1 goal (Task 1.5): define a clean, stable service contract for the
"sophisticated" matcher behavior being ported from legacy jBOM.

This module intentionally contains *no matching implementation yet*.

Design constraints:
- Constructor Configuration Pattern: operational knobs live on MatchingOptions.
- Domain-only: accepts domain objects, not file paths; performs no file I/O.
- Typed outputs: matching results are returned as dataclasses (no tuples/dicts).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from jbom.common.component_classification import get_component_type
from jbom.common.constants import ComponentType
from jbom.common.package_matching import (
    extract_package_from_footprint,
    footprint_matches_package,
)
from jbom.common.types import Component, InventoryItem
from jbom.common.value_parsing import (
    parse_cap_to_farad,
    parse_ind_to_henry,
    parse_res_to_ohms,
)


@dataclass(frozen=True)
class MatchingOptions:
    """Configuration for :class:`SophisticatedInventoryMatcher`.

    Attributes:
        include_debug_info: If True, matcher may populate :attr:`MatchResult.debug_info`.
            This should remain domain-safe diagnostic text (no printing).

    Notes:
        Per ADR 0001 (Option A), the matcher stays fabricator-agnostic in Phase 1.
        Fabricator-specific inventory selection is the caller's responsibility.
    """

    include_debug_info: bool = False


@dataclass(frozen=True)
class MatchResult:
    """A single candidate match between a component and an inventory item."""

    inventory_item: InventoryItem
    score: int
    debug_info: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate result invariants."""

        if self.score < 0:
            raise ValueError("score must be >= 0")


class SophisticatedInventoryMatcher:
    """Matches a single :class:`~jbom.common.types.Component` against inventory.

    Phase 1 extraction plan:
    - Task 1.5: define the service interface
    - Task 1.5b: port primary filtering (fast rejection)
    - Task 1.5c: port scoring + ordering and implement :meth:`find_matches`
    """

    def __init__(self, options: MatchingOptions):
        """Create a matcher with a fixed configuration."""

        self._options = options

    @staticmethod
    def _normalize_value(value: str) -> str:
        """Normalize a value string for non-numeric comparisons.

        This is a legacy-compatible normalization used for primary filtering of
        non-passive components.
        """

        t = (value or "").strip().lower()
        t = re.sub(r"[Ωω]|ohm", "", t)
        t = t.replace("μ", "u")
        t = re.sub(r"\s+", "", t)
        return t

    def _passes_primary_filters(
        self, component: Component, item: InventoryItem
    ) -> bool:
        """Return True if an inventory item is eligible for scoring.

        Ported from legacy jBOM's `_passes_primary_filters`.

        This filter is fabricator-agnostic (ADR 0001). The caller must pass an
        already fabricator-selected inventory list to :meth:`find_matches`.

        Filters (in order):
        1) Type/category match (when component type can be determined)
        2) Package match (when a package can be extracted from footprint)
        3) Value match:
           - Numeric equality for RES/CAP/IND
           - Otherwise normalized string equality
        """

        comp_type = get_component_type(component.lib_id, component.footprint)
        comp_pkg = extract_package_from_footprint(component.footprint)
        comp_val_norm = (
            self._normalize_value(component.value) if component.value else ""
        )

        # 1) Type/category must match if we could determine it.
        if comp_type:
            cat = (item.category or "").upper()
            if comp_type not in cat:
                return False

        # 2) Package must match when we can extract it.
        if comp_pkg:
            ipkg = (item.package or "").lower()
            if comp_pkg not in ipkg:
                return False

        # 3) Value match by type (numeric for RES/CAP/IND).
        if comp_val_norm:
            if comp_type == ComponentType.RESISTOR:
                comp_num = parse_res_to_ohms(component.value)
                inv_num = parse_res_to_ohms(item.value)
                if (
                    comp_num is None
                    or inv_num is None
                    or abs(comp_num - inv_num) > 1e-12
                ):
                    return False
            elif comp_type == ComponentType.CAPACITOR:
                comp_num = parse_cap_to_farad(component.value)
                inv_num = parse_cap_to_farad(item.value)
                if (
                    comp_num is None
                    or inv_num is None
                    or abs(comp_num - inv_num) > 1e-18
                ):
                    return False
            elif comp_type == ComponentType.INDUCTOR:
                comp_num = parse_ind_to_henry(component.value)
                inv_num = parse_ind_to_henry(item.value)
                if (
                    comp_num is None
                    or inv_num is None
                    or abs(comp_num - inv_num) > 1e-18
                ):
                    return False
            else:
                inv_val_norm = self._normalize_value(item.value) if item.value else ""
                if not inv_val_norm or inv_val_norm != comp_val_norm:
                    return False

        return True

    @staticmethod
    def _parse_tolerance_percent(tolerance: str) -> Optional[float]:
        """Parse tolerance strings like '±5%' or '5%' into a percent float."""

        if not tolerance:
            return None

        t = tolerance.strip().replace("±", "").replace("%", "").strip()
        try:
            return float(t)
        except ValueError:
            return None

    def _values_match(self, component: Component, item: InventoryItem) -> bool:
        """Return True if component and item values match (legacy rules)."""

        if not component.value or not item.value:
            return False

        comp_type = get_component_type(component.lib_id, component.footprint)

        if comp_type == ComponentType.RESISTOR:
            comp_num = parse_res_to_ohms(component.value)
            inv_num = parse_res_to_ohms(item.value)
            return (
                comp_num is not None
                and inv_num is not None
                and abs(comp_num - inv_num) <= 1e-12
            )

        if comp_type == ComponentType.CAPACITOR:
            comp_num = parse_cap_to_farad(component.value)
            inv_num = parse_cap_to_farad(item.value)
            return (
                comp_num is not None
                and inv_num is not None
                and abs(comp_num - inv_num) <= 1e-18
            )

        if comp_type == ComponentType.INDUCTOR:
            comp_num = parse_ind_to_henry(component.value)
            inv_num = parse_ind_to_henry(item.value)
            return (
                comp_num is not None
                and inv_num is not None
                and abs(comp_num - inv_num) <= 1e-18
            )

        return self._normalize_value(component.value) == self._normalize_value(
            item.value
        )

    def _match_properties(self, component: Component, item: InventoryItem) -> int:
        """Return property match bonus score.

        This ports the Phase 1 property scoring behavior from legacy jBOM:
        tolerance, voltage, and wattage/power.
        """

        score = 0
        properties = component.properties or {}

        # Tolerance matching.
        if (tol := properties.get("Tolerance")) and item.tolerance:
            comp_tol = self._parse_tolerance_percent(tol)
            item_tol = self._parse_tolerance_percent(item.tolerance)
            if comp_tol is not None and item_tol is not None:
                if comp_tol == item_tol:
                    score += 15
                elif item_tol < comp_tol:
                    score += 10

        # Voltage matching.
        for field in ("Voltage", "V"):
            if (v := properties.get(field)) and item.voltage:
                if v in item.voltage:
                    score += 10
                    break

        # Power / wattage matching.
        for field in ("Wattage", "Power", "W", "P"):
            if (w := properties.get(field)) and item.wattage:
                if w in item.wattage:
                    score += 10
                    break

        return score

    def _calculate_match_score(self, component: Component, item: InventoryItem) -> int:
        """Calculate match score (ported from legacy jBOM).

        Weights:
        - Type match: +50
        - Value match: +40
        - Footprint/package match: +30
        - Property match bonus: varies
        - Keyword match: +10
        """

        score = 0

        comp_type = get_component_type(component.lib_id, component.footprint)
        if comp_type and comp_type in (item.category or ""):
            score += 50

        if self._values_match(component, item):
            score += 40

        if component.footprint and item.package:
            if footprint_matches_package(component.footprint, item.package):
                score += 30

        score += self._match_properties(component, item)

        if component.value and item.keywords and component.value in item.keywords:
            score += 10

        return score

    def find_matches(
        self, component: Component, inventory: List[InventoryItem]
    ) -> List[MatchResult]:
        """Find matching inventory items for a single component.

        Notes:
            Per ADR 0001 (Option A), this matcher is fabricator-agnostic. The
            caller must supply a pre-selected inventory list appropriate for the
            intended fabricator.

            Ordering is exactly legacy: `(item.priority asc, score desc)`.
            This method must NOT modify `item.priority`.

        Args:
            component: The schematic component to match.
            inventory: Candidate inventory items (pre-selected by caller).

        Returns:
            Matches sorted by `(item.priority, -score)`.
        """

        if not inventory:
            return []

        results: List[MatchResult] = []
        for item in inventory:
            if not self._passes_primary_filters(component, item):
                continue

            score = self._calculate_match_score(component, item)
            if score <= 0:
                continue

            debug_info = None
            if self._options.include_debug_info:
                debug_info = f"ipn={item.ipn}, priority={item.priority}, score={score}"

            results.append(
                MatchResult(inventory_item=item, score=score, debug_info=debug_info)
            )

        results.sort(key=lambda r: (r.inventory_item.priority, -r.score))
        return results


__all__ = [
    "MatchingOptions",
    "MatchResult",
    "SophisticatedInventoryMatcher",
]
