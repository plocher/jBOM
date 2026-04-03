"""Shared value/tolerance matching helpers for search and inventory matching."""

from __future__ import annotations

from jbom.common.component_classification import normalize_component_type
from jbom.common.value_parsing import parse_value_to_normal
from jbom.config.defaults import get_defaults

_CATEGORY_DEFAULT_KEYS: dict[str, str] = {
    "RES": "resistor",
    "CAP": "capacitor",
    "IND": "inductor",
}
_MIN_RELATIVE_TOLERANCE = 0.001


def close_enough_numeric(a: float, b: float, *, rel_tol: float) -> bool:
    """Return True when *a* is within relative tolerance of *b*."""

    if a == b:
        return True
    if b == 0:
        return abs(a) <= rel_tol
    return abs(a - b) <= abs(b) * rel_tol


def parse_tolerance_percent(text: str | None) -> float | None:
    """Parse tolerance strings like ``1%`` or ``±5%`` into percent floats."""

    if not text:
        return None

    cleaned = (
        str(text).strip().replace("%", "").replace("+/-", "").replace("±", "").strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


def default_tolerance_percent_for_category(category: str) -> float | None:
    """Return defaults-profile tolerance hint (percent) for a category."""

    normalized = normalize_component_type(category or "")
    category_key = _CATEGORY_DEFAULT_KEYS.get(normalized, "")
    if not category_key:
        return None
    cfg = get_defaults()
    return parse_tolerance_percent(cfg.get_domain_default(category_key, "tolerance"))


def effective_relative_tolerance(
    category: str,
    *,
    explicit_tolerance_percent: float | None,
    minimum_relative_tolerance: float = _MIN_RELATIVE_TOLERANCE,
) -> float:
    """Return effective relative tolerance for numeric value comparison."""

    tolerance_percent = (
        explicit_tolerance_percent
        if explicit_tolerance_percent is not None
        else default_tolerance_percent_for_category(category)
    )
    if tolerance_percent is None:
        return minimum_relative_tolerance
    return max(minimum_relative_tolerance, tolerance_percent / 100.0)


def candidate_tolerance_meets_requirement(
    *,
    required_tolerance_percent: float | None,
    candidate_tolerance_text: str | None,
) -> bool:
    """Return True when candidate tolerance is as good or better than required.

    Missing/unparseable candidate tolerance remains fail-open to preserve legacy
    behavior for sparse supplier/inventory data.
    """

    if required_tolerance_percent is None:
        return True

    candidate_tolerance_percent = parse_tolerance_percent(candidate_tolerance_text)
    if candidate_tolerance_percent is None:
        return True

    return candidate_tolerance_percent <= required_tolerance_percent


def numeric_value_match(
    *,
    category: str,
    expected_value: str,
    candidate_value: str,
    explicit_tolerance_percent: float | None = None,
) -> bool:
    """Return True when numeric values match with category-aware tolerance."""

    normalized_category = normalize_component_type(category or "")
    expected = parse_value_to_normal(normalized_category, expected_value)
    candidate = parse_value_to_normal(normalized_category, candidate_value)
    if expected is None or candidate is None:
        return False

    rel_tol = effective_relative_tolerance(
        normalized_category,
        explicit_tolerance_percent=explicit_tolerance_percent,
    )
    return close_enough_numeric(candidate, expected, rel_tol=rel_tol)
