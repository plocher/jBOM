"""Component classification and categorization utilities.

Phase 1 intent
This module is an extraction point for component classification logic.

We want:
- a clean, testable public API (pure functions)
- an explicit "component classifier" concept so more sophisticated approaches
  (rules/config-driven) can be introduced later without rewriting call sites

The default classifier uses a scoring / bidding model: each signal contributes a
weighted score to a candidate category, and the category with the highest total
score wins.  Signal weight reflects specificity — a longer, more precise match
outweighs a short prefix match.  This removes all ordering sensitivity from the
original if/elif chain.

See: GitHub issue #149
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional, Protocol

from jbom.common.constants import (
    CATEGORY_FIELDS,
    COMPONENT_TYPE_MAPPING,
    DEFAULT_CATEGORY_FIELDS,
    VALUE_INTERPRETATION,
)

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Classification signal infrastructure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClassificationSignal:
    """A weighted classification signal for component type scoring.

    Attributes:
        category: The ComponentType identifier this signal votes for.
        weight: How strongly this signal votes (higher = more authoritative).
        match: Callable ``(component_upper, footprint_upper, ref_upper) -> bool``
            that returns True when the signal applies.
    """

    category: str
    weight: float
    match: Callable[[str, str, str], bool]


@dataclass(frozen=True)
class TextClassificationSignal:
    """A weighted classification signal operating on free-text fields (Description, Keywords).

    Attributes:
        category: The ComponentType identifier this signal votes for.
        weight: How strongly this signal votes.
        match: Callable ``(text_upper,) -> bool`` operating on the uppercased combined
            description + keywords string.
    """

    category: str
    weight: float
    match: Callable[[str], bool]


# ---------------------------------------------------------------------------
# Text-based signal table (Description + Keywords)
# ---------------------------------------------------------------------------
# These operate on a combined uppercase string of the KiCad component\'s
# Description and Keywords properties.  They supplement the primary
# lib_id/footprint/reference signals; a strong primary signal (e.g. IC
# footprint at 6.0) will always outweigh a weak text hint (3.0).
# ---------------------------------------------------------------------------

_TEXT_SIGNALS: list[TextClassificationSignal] = [
    # Neopixel is brand-specific → very high confidence
    TextClassificationSignal("LED", 4.0, lambda t: "NEOPIXEL" in t),
    TextClassificationSignal("LED", 3.0, lambda t: "LED" in t),
    TextClassificationSignal("RLY", 3.0, lambda t: "RELAY" in t),
    TextClassificationSignal("IND", 3.0, lambda t: "INDUCTOR" in t),
    TextClassificationSignal("IND", 3.0, lambda t: "FERRITE" in t),
    TextClassificationSignal("OSC", 3.0, lambda t: "CRYSTAL" in t),
    TextClassificationSignal("OSC", 3.0, lambda t: "OSCILLATOR" in t),
    TextClassificationSignal("OSC", 3.0, lambda t: "XTAL" in t),
    TextClassificationSignal("FUS", 3.0, lambda t: "FUSE" in t),
    TextClassificationSignal("CON", 3.0, lambda t: "CONNECTOR" in t),
    TextClassificationSignal("DIO", 3.0, lambda t: "DIODE" in t),
    TextClassificationSignal("RES", 3.0, lambda t: "RESISTOR" in t),
    TextClassificationSignal("CAP", 3.0, lambda t: "CAPACITOR" in t),
    TextClassificationSignal("Q", 3.0, lambda t: "TRANSISTOR" in t),
    TextClassificationSignal("SWI", 3.0, lambda t: "SWITCH" in t),
    TextClassificationSignal("REG", 3.0, lambda t: "REGULATOR" in t),
]


def _is_ic_footprint(footprint_upper: str) -> bool:
    """Return True if the footprint indicates an integrated circuit."""

    ic_footprint_patterns = [
        "SOIC",
        "QFP",
        "QFN",
        "BGA",
        "DIP",
        "PDIP",
        "PLCC",
        "LGA",
        "TQFP",
        "LQFP",
        "SSOP",
        "TSSOP",
        "MSOP",
        "SOT23-5",
        "SOT23-6",
        "SC70",
        "WLCSP",
        "UFBGA",
        "VQFN",
        "HVQFN",
        "DFQFN",
        "UDFN",
    ]
    return any(pattern in footprint_upper for pattern in ic_footprint_patterns)


# ---------------------------------------------------------------------------
# Signal table
# ---------------------------------------------------------------------------
# Signals are independent — order does not affect correctness.
# Weight tiers:
#   6.0  IC footprint or FB RefDes (very reliable hardware signal)
#   5.0  multi-char specific substring / IPC RefDes convention
#   4.0  footprint library prefix or RefDes for common types
#   3.0  IC-prefix patterns / RefDes with moderate confidence
#   2.0  single-char prefix with higher-than-usual IC affinity (U, Q)
#   1.5  broad but useful single-char connector hint (J in name)
#   1.0  single-char name prefix (weakest, easily overridden)

_SIGNALS: list[ClassificationSignal] = [
    # ------------------------------------------------------------------
    # High-specificity multi-char name substrings
    # ------------------------------------------------------------------
    ClassificationSignal("CON", 5.0, lambda n, f, r: "CONN" in n),
    ClassificationSignal("LED", 3.0, lambda n, f, r: "LED" in n),
    ClassificationSignal("IND", 5.0, lambda n, f, r: "INDUCTOR" in n),
    ClassificationSignal("IND", 5.0, lambda n, f, r: "FERRITE" in n),
    ClassificationSignal("SWI", 4.0, lambda n, f, r: "SW" in n),
    ClassificationSignal("RLY", 5.0, lambda n, f, r: "RELAY" in n),
    ClassificationSignal("OSC", 5.0, lambda n, f, r: "CRYSTAL" in n),
    ClassificationSignal("OSC", 5.0, lambda n, f, r: "XTAL" in n),
    ClassificationSignal("FUS", 5.0, lambda n, f, r: "FUSE" in n),
    # ------------------------------------------------------------------
    # IC indicator name patterns (override single-char prefix classification).
    # These must outweigh the single-char prefix signals (1.0–2.0).
    # ------------------------------------------------------------------
    ClassificationSignal("IC", 3.0, lambda n, f, r: "LM" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "TL" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "NE" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "MC" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "CD" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "SN" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "74" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "40" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "AD" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "MAX" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "LT" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "MCP" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "PIC" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "ATMEGA" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "STM32" in n),
    ClassificationSignal("IC", 3.0, lambda n, f, r: "ESP" in n),
    # ------------------------------------------------------------------
    # Footprint-based signals
    # ------------------------------------------------------------------
    # IC package footprints are highly authoritative
    ClassificationSignal("IC", 6.0, lambda n, f, r: _is_ic_footprint(f)),
    # Footprint library prefix signals for passive/discrete categories
    ClassificationSignal("CAP", 4.0, lambda n, f, r: "CAPACITOR" in f),
    ClassificationSignal("RES", 4.0, lambda n, f, r: "RESISTOR" in f),
    ClassificationSignal("LED", 4.0, lambda n, f, r: "LED" in f),
    ClassificationSignal("CON", 4.0, lambda n, f, r: "CONNECTOR" in f),
    ClassificationSignal("DIO", 4.0, lambda n, f, r: "DIODE" in f),
    ClassificationSignal("IND", 4.0, lambda n, f, r: "INDUCTOR" in f),
    # ------------------------------------------------------------------
    # Reference designator signals (IPC convention — most authoritative
    # non-footprint signal since the designer explicitly assigned it).
    #
    # All signals require <PREFIX><digit> (e.g. "R1", "CON3") so that
    # multi-char designators like "REG1" or "CON1" are not misclassified
    # by a shorter, lower-specificity prefix match.
    #
    # CON* (3-char) must appear before C* (1-char) so "CON1"-style refs
    # resolve to connector rather than capacitor.
    #
    # FB at 6.0 outweighs F→FUS (5.0); the digit constraint additionally
    # prevents F firing on "FB*" refs (second char 'B' is not a digit).
    # ------------------------------------------------------------------
    ClassificationSignal(
        "CON", 5.0, lambda n, f, r: r[:3] == "CON" and r[3:4].isdigit()
    ),
    ClassificationSignal("CON", 5.0, lambda n, f, r: r[:1] == "J" and r[1:2].isdigit()),
    ClassificationSignal(
        "IND", 6.0, lambda n, f, r: r[:2] == "FB" and r[2:3].isdigit()
    ),
    ClassificationSignal("DIO", 3.0, lambda n, f, r: r[:1] == "D" and r[1:2].isdigit()),
    ClassificationSignal("Q", 3.0, lambda n, f, r: r[:1] == "Q" and r[1:2].isdigit()),
    ClassificationSignal("IC", 3.0, lambda n, f, r: r[:1] == "U" and r[1:2].isdigit()),
    ClassificationSignal("RLY", 5.0, lambda n, f, r: r[:1] == "K" and r[1:2].isdigit()),
    ClassificationSignal("OSC", 5.0, lambda n, f, r: r[:1] == "Y" and r[1:2].isdigit()),
    ClassificationSignal("FUS", 5.0, lambda n, f, r: r[:1] == "F" and r[1:2].isdigit()),
    # Standard IPC passive-component designators — weight 4.0 outweighs
    # IC name-pattern false-positives (e.g. "NE" inside "Generic").
    ClassificationSignal("RES", 4.0, lambda n, f, r: r[:1] == "R" and r[1:2].isdigit()),
    ClassificationSignal("CAP", 4.0, lambda n, f, r: r[:1] == "C" and r[1:2].isdigit()),
    ClassificationSignal("IND", 4.0, lambda n, f, r: r[:1] == "L" and r[1:2].isdigit()),
    # ------------------------------------------------------------------
    # Single-char name prefix signals (weakest — easily overridden by any
    # of the above).
    # ------------------------------------------------------------------
    ClassificationSignal("RES", 1.0, lambda n, f, r: n.startswith("R")),
    ClassificationSignal("CAP", 1.0, lambda n, f, r: n.startswith("C")),
    ClassificationSignal("IND", 1.0, lambda n, f, r: n.startswith("L")),
    ClassificationSignal("DIO", 1.0, lambda n, f, r: n.startswith("D")),
    ClassificationSignal("Q", 2.0, lambda n, f, r: n.startswith("Q")),
    ClassificationSignal("IC", 2.0, lambda n, f, r: n.startswith("U")),
    ClassificationSignal("CON", 1.5, lambda n, f, r: "J" in n),
]


def _classify_by_score(
    component_upper: str,
    footprint_upper: str,
    ref_upper: str,
    description_upper: str = "",
    keywords_upper: str = "",
) -> Optional[str]:
    """Score all active signals and return the highest-scoring category.

    Args:
        component_upper: Uppercased component name (lib_id part after ``:``)
        footprint_upper: Uppercased KiCad footprint string.
        ref_upper: Uppercased reference designator (e.g. ``"R1"``, ``"U3"``).
        description_upper: Uppercased KiCad Description property (optional).
        keywords_upper: Uppercased KiCad Keywords property (optional).

    Returns:
        The winning category string, or ``None`` if no signals matched.
    """

    scores: dict[str, float] = {}
    for signal in _SIGNALS:
        if signal.match(component_upper, footprint_upper, ref_upper):
            scores[signal.category] = scores.get(signal.category, 0.0) + signal.weight

    # Description + Keywords fallback: activated only when the primary signals
    # (name / footprint / reference) yield no winner.  This prevents description
    # text from additively inflating scores for components already classified by
    # more authoritative signals.
    if not scores:
        extra_text = f"{description_upper} {keywords_upper}".strip()
        if extra_text:
            for text_signal in _TEXT_SIGNALS:
                if text_signal.match(extra_text):
                    scores[text_signal.category] = (
                        scores.get(text_signal.category, 0.0) + text_signal.weight
                    )

    if not scores:
        _logger.debug(
            "classify(%s, fp=%s, ref=%s): no signals matched → None",
            component_upper,
            footprint_upper,
            ref_upper,
        )
        return None

    winner = max(scores, key=scores.__getitem__)
    _logger.debug(
        "classify(%s, fp=%s, ref=%s): scores=%s → %s",
        component_upper,
        footprint_upper,
        ref_upper,
        scores,
        winner,
    )
    return winner


class ComponentClassifier(Protocol):
    """Classify a schematic component into a standardized component type."""

    def classify(
        self,
        lib_id: str,
        footprint: str = "",
        reference: str = "",
        description: str = "",
        keywords: str = "",
    ) -> Optional[str]:
        """Return a standardized component type (e.g., "RES", "CAP") or None."""


class HeuristicComponentClassifier:
    """Default component classifier.

    This is intentionally simple and pure (no file I/O, no global config).

    Notes:
        - Return values use jbom-new's canonical type identifiers from
          :class:`jbom.common.constants.ComponentType`.
        - Uses a scoring / bidding model where each signal contributes a
          weighted score.  The category with the highest total score wins.
    """

    def classify(
        self,
        lib_id: str,
        footprint: str = "",
        reference: str = "",
        description: str = "",
        keywords: str = "",
    ) -> Optional[str]:
        """Classify a component by scoring weighted signals."""

        return _get_component_type_heuristic(
            lib_id=lib_id,
            footprint=footprint,
            reference=reference,
            description=description,
            keywords=keywords,
        )


DEFAULT_COMPONENT_CLASSIFIER: ComponentClassifier = HeuristicComponentClassifier()


def normalize_component_type(component_type: str) -> str:
    """Normalize a component type string to a standard category.

    Args:
        component_type: A component type identifier (e.g., "RES", "resistor", "R").

    Returns:
        A normalized component type identifier.

    Notes:
        - If the input already matches a known category, it is returned.
        - Otherwise, the global mapping is applied (e.g., "R" -> "RES").
        - If no mapping exists, the upper-cased value is returned as-is.
    """

    category = component_type.upper() if component_type else ""

    if category in CATEGORY_FIELDS:
        return category
    if category in COMPONENT_TYPE_MAPPING:
        return COMPONENT_TYPE_MAPPING[category]

    return category


def get_category_fields(component_type: str) -> list[str]:
    """Get relevant inventory fields for a component category."""

    normalized_type = normalize_component_type(component_type)
    return CATEGORY_FIELDS.get(normalized_type, DEFAULT_CATEGORY_FIELDS)


def get_value_interpretation(component_type: str) -> Optional[str]:
    """Get what the inventory "Value" field represents for a given category."""

    normalized_type = normalize_component_type(component_type)
    return VALUE_INTERPRETATION.get(normalized_type)


def get_component_type(
    lib_id: str,
    footprint: str = "",
    reference: str = "",
    *,
    description: str = "",
    keywords: str = "",
    classifier: ComponentClassifier = DEFAULT_COMPONENT_CLASSIFIER,
) -> Optional[str]:
    """Determine component type from library ID, footprint, and reference designator.

    Args:
        lib_id: KiCad library ID (e.g., "Device:R").
        footprint: KiCad footprint name.
        reference: KiCad reference designator (e.g., "R1", "U3", "J2").
            When provided, IPC reference designator prefix signals are active.
        description: KiCad component Description property (optional).  Used as
            a supplementary scored signal when primary signals yield no winner.
        keywords: KiCad component Keywords property (optional).  Same role as
            *description*.
        classifier: The classifier to use.

    Returns:
        A standardized component type identifier (e.g., "RES", "CAP", "IC")
        or None if unknown.
    """

    # Validation at intake point: callers sometimes pass None-ish values.
    if not lib_id:
        return None

    return classifier.classify(lib_id, footprint, reference, description, keywords)


def _get_component_type_heuristic(
    lib_id: str,
    footprint: str = "",
    reference: str = "",
    description: str = "",
    keywords: str = "",
) -> Optional[str]:
    """Scoring-based implementation of component type detection.

    Each signal in ``_SIGNALS`` contributes a weighted vote to a category.
    The category with the highest total score wins.  Signals are independent—
    there is no ordering dependency.
    """

    if not lib_id:
        return None

    # Extract the component part from lib_id (after colon)
    if ":" in lib_id:
        component_part = lib_id.split(":", 1)[1]
    else:
        component_part = lib_id

    component_upper = component_part.upper()
    footprint_upper = footprint.upper() if footprint else ""
    ref_upper = reference.upper() if reference else ""
    description_upper = description.upper() if description else ""
    keywords_upper = keywords.upper() if keywords else ""

    # Fast path: exact name lookup beats any heuristic.
    if component_upper in COMPONENT_TYPE_MAPPING:
        result = COMPONENT_TYPE_MAPPING[component_upper]
        _logger.debug(
            "classify(%s, fp=%s, ref=%s): exact mapping → %s",
            component_upper,
            footprint_upper,
            ref_upper,
            result,
        )
        return result

    return _classify_by_score(
        component_upper, footprint_upper, ref_upper, description_upper, keywords_upper
    )
