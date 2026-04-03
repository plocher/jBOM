"""Sophisticated inventory matching service with configurable heuristic scoring.

The matcher preserves strict numeric behavior for passives (RES/CAP/IND) while
using a signal-voting model for non-passives to handle free-form, human-authored
inventory/project field relationships.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Union
from jbom.common.component_classification import (
    get_component_type,
    normalize_component_type,
)
from jbom.common.constants import ComponentType
from jbom.common.package_matching import (
    extract_package_from_footprint,
    footprint_matches_package,
)
from jbom.common.types import Component, InventoryItem
from jbom.common.value_parsing import parse_value_to_normal
from jbom.services.fabricator_inventory_selector import EligibleInventoryItem
from jbom.services.value_matching import (
    candidate_tolerance_meets_requirement,
    numeric_value_match,
    parse_tolerance_percent,
)

_PASSIVE_TYPES = {
    ComponentType.RESISTOR,
    ComponentType.CAPACITOR,
    ComponentType.INDUCTOR,
}
_LCSC_MATCH_POLICIES = {"validate", "hard_accept", "ignore"}
_CATEGORY_COMPATIBILITY = {
    (ComponentType.INTEGRATED_CIRCUIT, ComponentType.REGULATOR),
    (ComponentType.REGULATOR, ComponentType.INTEGRATED_CIRCUIT),
    (ComponentType.INTEGRATED_CIRCUIT, ComponentType.MICROCONTROLLER),
    (ComponentType.MICROCONTROLLER, ComponentType.INTEGRATED_CIRCUIT),
}
_IDENTITY_ANCHOR_REQUIRED_TYPES = {
    ComponentType.INTEGRATED_CIRCUIT,
    ComponentType.REGULATOR,
    ComponentType.MICROCONTROLLER,
    ComponentType.DIODE,
    ComponentType.TRANSISTOR,
    ComponentType.LED,
    ComponentType.OSCILLATOR,
    ComponentType.FUSE,
    ComponentType.ANALOG,
}


@dataclass(frozen=True)
class NonPassiveSignalAssessment:
    """Signal evaluation payload for one non-passive component/item pair."""

    score: int
    positive_families: frozenset[str]
    contributions: tuple[tuple[str, int], ...]
    hard_reject: bool = False
    hard_accept: bool = False


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
    non_passive_min_signal_score: int = 35
    non_passive_min_positive_families: int = 1
    non_passive_top_margin: int = 0
    lcsc_match_policy: str = "validate"
    lcsc_mismatch_reject: bool = True

    def __post_init__(self) -> None:
        """Validate configuration at data intake."""
        if self.non_passive_min_signal_score < 0:
            raise ValueError("non_passive_min_signal_score must be >= 0")
        if self.non_passive_min_positive_families < 0:
            raise ValueError("non_passive_min_positive_families must be >= 0")
        if self.non_passive_top_margin < 0:
            raise ValueError("non_passive_top_margin must be >= 0")
        if self.lcsc_match_policy not in _LCSC_MATCH_POLICIES:
            raise ValueError(
                "lcsc_match_policy must be one of: validate, hard_accept, ignore"
            )


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

    @staticmethod
    def _is_blank_constraint(value: str | None) -> bool:
        """Return True when a component constraint should be treated as blank.

        KiCad may encode empty user fields as "~" in schematic data. For
        matching semantics, this is equivalent to blank/no-constraint.
        """

        if value is None:
            return True
        stripped = value.strip()
        return stripped == "" or stripped == "~"

    @classmethod
    def _normalize_identifier(cls, value: str) -> str:
        """Normalize free-form identifiers for cross-field comparisons."""

        text = (value or "").strip().lower()
        if not text:
            return ""

        text = text.replace("μ", "u").replace("µ", "u")
        text = text.replace("Ω", "ohm").replace("ω", "ohm")
        raw_tokens = re.findall(r"[a-z0-9]+(?:x[a-z0-9]+)?", text)
        normalized_tokens = [
            cls._normalize_identifier_token(token) for token in raw_tokens
        ]
        return " ".join(token for token in normalized_tokens if token)

    @staticmethod
    def _normalize_identifier_token(token: str) -> str:
        """Normalize one identifier token into canonical comparison form."""

        t = token.strip().lower()
        if not t:
            return ""

        if t in {"con", "conn", "connector"}:
            return "connector"
        if t in {"soic", "sop", "ssop", "tssop", "msop"}:
            return "smalloutline"
        if t in {"dpak", "d2pak"}:
            return "to252"
        if t.startswith("to") and t[2:].isdigit():
            return f"to{int(t[2:])}"

        x_match = re.fullmatch(r"0*(\d+)x0*(\d+)", t)
        if x_match:
            return f"{int(x_match.group(1))}x{int(x_match.group(2))}"

        if t.isdigit():
            return str(int(t))
        return t

    @classmethod
    def _tokenize_identifier(cls, value: str) -> set[str]:
        """Tokenize free-form strings to normalized comparison tokens."""

        normalized = cls._normalize_identifier(value)
        if not normalized:
            return set()
        return {token for token in normalized.split(" ") if token}

    @staticmethod
    def _token_overlap_ratio(left: set[str], right: set[str]) -> float:
        """Return normalized overlap ratio between token sets."""

        if not left or not right:
            return 0.0
        return len(left & right) / max(len(left), len(right))

    @staticmethod
    def _footprint_stub(value: str) -> str:
        """Return a compact footprint identity token."""

        text = (value or "").strip().lower()
        if ":" in text:
            text = text.split(":", 1)[1]
        return re.sub(r"[^a-z0-9]+", "", text)

    @classmethod
    def _package_family_from_hint(cls, package_hint: str) -> set[str]:
        """Map one package hint to canonical package family labels."""

        hint = (package_hint or "").strip().lower()
        if not hint:
            return set()

        if hint in {"soic", "sop", "ssop", "tssop", "msop"}:
            return {"small_outline"}
        if hint in {"dpak", "d-pak", "to252", "to-252"}:
            return {"to252"}
        if hint in {"sot23", "sot-23"}:
            return {"sot23"}
        if hint in {"sot223", "sot-223"}:
            return {"sot223"}
        if hint == "sot":
            # Broad "sot" is too vague to be useful as a package family.
            return set()
        if re.fullmatch(r"\d{4}", hint):
            return {hint}

        to_match = re.fullmatch(r"to[-_ ]?(\d+)", hint)
        if to_match:
            return {f"to{to_match.group(1)}"}
        return {hint}

    @classmethod
    def _package_families(cls, *texts: str) -> set[str]:
        """Extract package family tokens from package and footprint text."""

        families: set[str] = set()
        for raw in texts:
            text = (raw or "").strip().lower()
            if not text:
                continue

            if re.search(r"\b(soic|sop|ssop|tssop|msop)\b", text):
                families.add("small_outline")
            if re.search(r"\bto[-_ ]?252\b", text) or "dpak" in text or "d-pak" in text:
                families.add("to252")
            if re.search(r"\bto[-_ ]?220\b", text):
                families.add("to220")
            if re.search(r"\bsot[-_ ]?23\b", text):
                families.add("sot23")
            if re.search(r"\bsot[-_ ]?223\b", text):
                families.add("sot223")
            if re.search(r"\bqfn\b", text):
                families.add("qfn")
            if re.search(r"\bqfp\b", text):
                families.add("qfp")
            if re.search(r"\bdip\b", text):
                families.add("dip")
            families.update(re.findall(r"\b\d{4}\b", text))

            footprint_hint = extract_package_from_footprint(raw)
            families.update(cls._package_family_from_hint(footprint_hint))

        return families

    @staticmethod
    def _normalized_item_category(item: InventoryItem) -> str:
        """Return normalized candidate category token."""

        return normalize_component_type(item.category or "")

    @staticmethod
    def _categories_compatible(component_category: str, item_category: str) -> bool:
        """Return True when component and inventory categories are compatible."""

        if not component_category or not item_category:
            return True
        if component_category == item_category:
            return True
        return (component_category, item_category) in _CATEGORY_COMPATIBILITY

    @staticmethod
    def _requires_identity_anchor(component_category: str) -> bool:
        """Return True when value/IPN identity evidence is required for acceptance."""

        return component_category in _IDENTITY_ANCHOR_REQUIRED_TYPES

    @staticmethod
    def _infer_value_category(value: str) -> str:
        """Infer a passive category from value text when evidence is unambiguous."""

        text = (value or "").strip()
        if not text:
            return ""

        hits: list[str] = []
        for category in (
            ComponentType.CAPACITOR,
            ComponentType.RESISTOR,
            ComponentType.INDUCTOR,
        ):
            if parse_value_to_normal(category, text) is not None:
                hits.append(category)
        if len(hits) == 1:
            return hits[0]
        return ""

    @staticmethod
    def _first_non_empty(mapping: dict[str, str], keys: Sequence[str]) -> str:
        """Return first non-empty string value for the given keys."""

        for key in keys:
            value = str(mapping.get(key, "")).strip()
            if value:
                return value
        return ""

    @staticmethod
    def _extract_component_lcsc(component: Component) -> str:
        """Extract component LCSC value from schematic attributes when present."""

        properties = component.properties or {}
        for key in ("lcsc", "LCSC", "i:lcsc"):
            value = str(properties.get(key, "")).strip()
            if value:
                return value

        for key, value in properties.items():
            if str(key or "").strip().lower().endswith("lcsc"):
                text = str(value).strip()
                if text:
                    return text
        return ""

    @staticmethod
    def _extract_item_lcsc(item: InventoryItem) -> str:
        """Extract candidate LCSC value from canonical or raw fields."""

        canonical = str(item.lcsc or "").strip()
        if canonical:
            return canonical
        raw = item.raw_data or {}
        return SophisticatedInventoryMatcher._first_non_empty(
            raw, ("LCSC", "lcsc", "LCSC Part", "LCSC Part #")
        )

    @staticmethod
    def _candidate_identity_fields(item: InventoryItem) -> dict[str, str]:
        """Return normalized candidate identity strings for cross-field matching."""

        raw = item.raw_data or {}
        return {
            "value": str(item.value or "").strip()
            or SophisticatedInventoryMatcher._first_non_empty(raw, ("Value", "value")),
            "ipn": str(item.ipn or "").strip()
            or SophisticatedInventoryMatcher._first_non_empty(raw, ("IPN", "ipn")),
            "name": str(item.name or "").strip()
            or SophisticatedInventoryMatcher._first_non_empty(
                raw, ("Name", "name", "ComponentName", "componentname")
            ),
            "mfgpn": str(item.mfgpn or "").strip()
            or SophisticatedInventoryMatcher._first_non_empty(
                raw, ("MPN", "MFGPN", "Manufacturer Part Number")
            ),
            "description": str(item.description or "").strip()
            or SophisticatedInventoryMatcher._first_non_empty(
                raw, ("Description", "description")
            ),
        }

    def _evaluate_non_passive_signals(
        self,
        component: Component,
        item: InventoryItem,
        *,
        component_type: str,
        component_package: str,
    ) -> NonPassiveSignalAssessment:
        """Evaluate non-passive signal contributions for one candidate."""

        score = 0
        positive_families: set[str] = set()
        contributions: list[tuple[str, int]] = []
        hard_reject = False
        hard_accept = False

        def contribute(key: str, value: int, family: str = "") -> None:
            nonlocal score
            score += value
            contributions.append((key, value))
            if value > 0 and family:
                positive_families.add(family)

        item_category = self._normalized_item_category(item)
        if component_type and item_category:
            if self._categories_compatible(component_type, item_category):
                contribute("category_compatible", 20, "category")
            else:
                contribute("category_conflict", -45)

        inferred_value_category = self._infer_value_category(component.value)
        if inferred_value_category and item_category:
            if inferred_value_category != item_category:
                contribute(
                    f"value_category_conflict:{inferred_value_category}->{item_category}",
                    -90,
                )

        component_lcsc = self._extract_component_lcsc(component)
        item_lcsc = self._extract_item_lcsc(item)
        if component_lcsc and self._options.lcsc_match_policy != "ignore":
            left = self._normalize_identifier(component_lcsc)
            right = self._normalize_identifier(item_lcsc)
            if left and right and left == right:
                if self._options.lcsc_match_policy == "hard_accept":
                    contribute("lcsc_hard_accept", 180, "lcsc")
                    hard_accept = True
                else:
                    contribute("lcsc_match", 70, "lcsc")
            elif right:
                contribute("lcsc_mismatch", -150)
                if self._options.lcsc_mismatch_reject:
                    hard_reject = True

        component_value_normalized = self._normalize_identifier(component.value)
        component_value_tokens = self._tokenize_identifier(component.value)
        candidate_fields = self._candidate_identity_fields(item)
        exact_identity_match = ""
        best_overlap = 0.0
        best_overlap_field = ""
        for field_name, field_value in candidate_fields.items():
            if not field_value:
                continue
            candidate_normalized = self._normalize_identifier(field_value)
            if (
                component_value_normalized
                and candidate_normalized
                and component_value_normalized == candidate_normalized
            ):
                exact_identity_match = field_name
                break

            overlap = self._token_overlap_ratio(
                component_value_tokens, self._tokenize_identifier(field_value)
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_overlap_field = field_name

        if exact_identity_match:
            contribute(f"value_exact:{exact_identity_match}", 55, "identity")
        elif best_overlap >= 0.80:
            contribute(f"value_overlap_strong:{best_overlap_field}", 35, "identity")
        elif best_overlap >= 0.60:
            contribute(f"value_overlap_medium:{best_overlap_field}", 24, "identity")
        elif best_overlap >= 0.40:
            contribute(f"value_overlap_weak:{best_overlap_field}", 12, "identity")

        raw = item.raw_data or {}
        component_footprint = str(component.footprint or "")
        component_footprint_stub = self._footprint_stub(component_footprint)
        component_footprint_tokens = self._tokenize_identifier(component_footprint)
        candidate_footprints = [
            str(item.footprint_full or ""),
            str(raw.get("Footprint", "")),
            str(raw.get("footprint_full", "")),
        ]

        exact_footprint_match = False
        best_footprint_overlap = 0.0
        for candidate_footprint in candidate_footprints:
            if not candidate_footprint:
                continue
            candidate_stub = self._footprint_stub(candidate_footprint)
            if component_footprint_stub and component_footprint_stub == candidate_stub:
                exact_footprint_match = True
                break
            overlap = self._token_overlap_ratio(
                component_footprint_tokens,
                self._tokenize_identifier(candidate_footprint),
            )
            if overlap > best_footprint_overlap:
                best_footprint_overlap = overlap

        if exact_footprint_match:
            contribute("footprint_exact", 50, "footprint")
        elif best_footprint_overlap >= 0.75:
            contribute("footprint_overlap_strong", 30, "footprint")
        elif best_footprint_overlap >= 0.50:
            contribute("footprint_overlap_medium", 18, "footprint")

        component_package_families = self._package_families(
            component.footprint, component_package
        )
        item_package_families = self._package_families(
            item.package,
            item.footprint_full,
            str(raw.get("Footprint", "")),
        )
        if component_package_families and item_package_families:
            if component_package_families & item_package_families:
                contribute("package_compatible", 25, "package")
            else:
                contribute("package_conflict", -25)
        elif component.footprint and item.package:
            if footprint_matches_package(component.footprint, item.package):
                contribute("package_footprint_match", 20, "package")

        if component.value and item.keywords:
            if component.value.lower() in item.keywords.lower():
                contribute("keyword_contains_value", 10, "keywords")

        return NonPassiveSignalAssessment(
            score=score,
            positive_families=frozenset(positive_families),
            contributions=tuple(contributions),
            hard_reject=hard_reject,
            hard_accept=hard_accept,
        )

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
           - Category-aware numeric tolerance matching for RES/CAP/IND
           - Otherwise normalized string equality
        4) Optional tolerance requirement gate:
           - If component specifies tolerance, candidate tolerance must be
             as strict or stricter when explicitly present on inventory item.
        """

        comp_type = get_component_type(
            component.lib_id, component.footprint, component.reference
        )
        comp_pkg = extract_package_from_footprint(component.footprint)
        comp_val_norm = (
            ""
            if self._is_blank_constraint(component.value)
            else self._normalize_value(component.value)
        )
        # Legacy-compatible unknown fallback: no type/package/value constraints.
        if not comp_type and not comp_pkg and not comp_val_norm:
            return True

        component_lcsc = self._extract_component_lcsc(component)
        item_lcsc = self._extract_item_lcsc(item)
        if component_lcsc and self._options.lcsc_match_policy != "ignore":
            left = self._normalize_identifier(component_lcsc)
            right = self._normalize_identifier(item_lcsc)
            if left and right and left == right:
                if self._options.lcsc_match_policy == "hard_accept":
                    return True
            elif right and self._options.lcsc_mismatch_reject:
                return False

        if comp_type not in _PASSIVE_TYPES:
            assessment = self._evaluate_non_passive_signals(
                component,
                item,
                component_type=comp_type or "",
                component_package=comp_pkg,
            )
            if assessment.hard_accept:
                return True
            if assessment.hard_reject:
                return False
            if assessment.score < self._options.non_passive_min_signal_score:
                return False
            if (
                len(assessment.positive_families)
                < self._options.non_passive_min_positive_families
            ):
                return False
            if self._requires_identity_anchor(comp_type or ""):
                if not (assessment.positive_families & {"identity", "lcsc"}):
                    return False
            elif not (assessment.positive_families & {"identity", "footprint", "lcsc"}):
                return False
            return True

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
            component_tolerance_percent = parse_tolerance_percent(
                (component.properties or {}).get("Tolerance")
            )
            if comp_type == ComponentType.RESISTOR:
                if not numeric_value_match(
                    category=comp_type,
                    expected_value=component.value,
                    candidate_value=item.value,
                    explicit_tolerance_percent=component_tolerance_percent,
                ):
                    return False
            elif comp_type == ComponentType.CAPACITOR:
                if not numeric_value_match(
                    category=comp_type,
                    expected_value=component.value,
                    candidate_value=item.value,
                    explicit_tolerance_percent=component_tolerance_percent,
                ):
                    return False
            elif comp_type == ComponentType.INDUCTOR:
                if not numeric_value_match(
                    category=comp_type,
                    expected_value=component.value,
                    candidate_value=item.value,
                    explicit_tolerance_percent=component_tolerance_percent,
                ):
                    return False
            else:
                inv_val_norm = self._normalize_value(item.value) if item.value else ""
                if not inv_val_norm or inv_val_norm != comp_val_norm:
                    return False
            if not candidate_tolerance_meets_requirement(
                required_tolerance_percent=component_tolerance_percent,
                candidate_tolerance_text=item.tolerance,
            ):
                return False

        return True

    def _values_match(self, component: Component, item: InventoryItem) -> bool:
        """Return True if component and item values match (legacy rules)."""

        if not component.value or not item.value:
            return False

        comp_type = get_component_type(
            component.lib_id, component.footprint, component.reference
        )

        if comp_type == ComponentType.RESISTOR:
            return numeric_value_match(
                category=comp_type,
                expected_value=component.value,
                candidate_value=item.value,
                explicit_tolerance_percent=parse_tolerance_percent(
                    (component.properties or {}).get("Tolerance")
                ),
            )

        if comp_type == ComponentType.CAPACITOR:
            return numeric_value_match(
                category=comp_type,
                expected_value=component.value,
                candidate_value=item.value,
                explicit_tolerance_percent=parse_tolerance_percent(
                    (component.properties or {}).get("Tolerance")
                ),
            )

        if comp_type == ComponentType.INDUCTOR:
            return numeric_value_match(
                category=comp_type,
                expected_value=component.value,
                candidate_value=item.value,
                explicit_tolerance_percent=parse_tolerance_percent(
                    (component.properties or {}).get("Tolerance")
                ),
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
        tol = properties.get("Tolerance")
        if not self._is_blank_constraint(tol) and item.tolerance:
            comp_tol = parse_tolerance_percent(tol)
            item_tol = parse_tolerance_percent(item.tolerance)
            if comp_tol is not None and item_tol is not None:
                if comp_tol == item_tol:
                    score += 15
                elif item_tol < comp_tol:
                    score += 10

        # Voltage matching.
        for field in ("Voltage", "V"):
            v = properties.get(field)
            if not self._is_blank_constraint(v) and item.voltage:
                if v in item.voltage:
                    score += 10
                    break

        # Power / wattage matching.
        for field in ("Wattage", "Power", "W", "P"):
            w = properties.get(field)
            if not self._is_blank_constraint(w) and item.wattage:
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
        comp_type = get_component_type(
            component.lib_id, component.footprint, component.reference
        )
        comp_pkg = extract_package_from_footprint(component.footprint)

        if comp_type in _PASSIVE_TYPES:
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

        assessment = self._evaluate_non_passive_signals(
            component,
            item,
            component_type=comp_type or "",
            component_package=comp_pkg,
        )
        if assessment.hard_reject:
            return 0

        score += max(0, assessment.score)
        score += self._match_properties(component, item)
        return score

    def find_matches(
        self,
        component: Component,
        inventory: Sequence[Union[InventoryItem, EligibleInventoryItem]],
    ) -> List[MatchResult]:
        """Find matching inventory items for a single component.

        Notes:
            Per ADR 0001 (Option A), this matcher remains fabricator-agnostic.
            Fabricator-specific policy lives in the selection layer.

            However, Phase 2 introduces a preference-tier hint via
            :class:`~jbom.services.fabricator_inventory_selector.EligibleInventoryItem`.
            When present, ordering is:

            Ordering behavior is category-aware:
            - passives (RES/CAP/IND): `(preference_tier asc, item.priority asc, score desc)`
            - non-passives: `(preference_tier asc, score desc, item.priority asc)`

            Plain :class:`~jbom.common.types.InventoryItem` values are treated as
            `preference_tier=0` for backward compatibility.

        Args:
            component: The schematic component to match.
            inventory: Candidate inventory items (plain or eligible-wrapped).

        Returns:
            Matches sorted by category-aware precedence described above.
        """

        if not inventory:
            return []

        results: list[tuple[int, MatchResult]] = []
        comp_type = get_component_type(
            component.lib_id, component.footprint, component.reference
        )
        comp_pkg = extract_package_from_footprint(component.footprint)

        for candidate in inventory:
            if isinstance(candidate, EligibleInventoryItem):
                item = candidate.item
                preference_tier = candidate.preference_tier
            else:
                item = candidate
                preference_tier = 0

            if not self._passes_primary_filters(component, item):
                continue

            score = self._calculate_match_score(component, item)
            if score <= 0:
                continue

            debug_info = None
            if self._options.include_debug_info:
                signal_debug = ""
                if comp_type not in _PASSIVE_TYPES:
                    assessment = self._evaluate_non_passive_signals(
                        component,
                        item,
                        component_type=comp_type or "",
                        component_package=comp_pkg,
                    )
                    signal_debug = ", ".join(
                        f"{key}:{value}"
                        for key, value in assessment.contributions
                        if value
                    )
                debug_info = (
                    f"ipn={item.ipn}, tier={preference_tier}, "
                    f"priority={item.priority}, score={score}"
                )
                if signal_debug:
                    debug_info += f", signals=[{signal_debug}]"

            results.append(
                (
                    preference_tier,
                    MatchResult(
                        inventory_item=item, score=score, debug_info=debug_info
                    ),
                )
            )

        if comp_type in _PASSIVE_TYPES:
            results.sort(
                key=lambda t: (t[0], t[1].inventory_item.priority, -t[1].score)
            )
        else:
            results.sort(
                key=lambda t: (t[0], -t[1].score, t[1].inventory_item.priority)
            )
        ordered = [mr for _tier, mr in results]

        if (
            comp_type not in _PASSIVE_TYPES
            and self._options.non_passive_top_margin > 0
            and len(ordered) >= 2
        ):
            margin = ordered[0].score - ordered[1].score
            if margin < self._options.non_passive_top_margin:
                return []

        return ordered


__all__ = [
    "MatchingOptions",
    "MatchResult",
    "SophisticatedInventoryMatcher",
]
