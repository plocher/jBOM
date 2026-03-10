"""Category-aware parametric query builder for JLCPCB/LCSC search.

This module provides deterministic helper logic for building structured
JLCPCB/LCSC parametric search queries from inventory item attributes.

All configurable constants (domain defaults, package ratings, routing rules,
query fields) are loaded from the defaults profile system via
get_defaults() / DefaultsConfig. See generic.defaults.yaml for factory values
and docs/dev/architecture/component-attribute-enrichment.md for the design model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from jbom.common.types import InventoryItem
from jbom.common.value_parsing import farad_to_eia, henry_to_eia, ohms_to_eia
from jbom.config.defaults import DefaultsConfig, get_defaults
from jbom.services.search.cache import normalize_query

# Compiled regexes for connector footprint parsing
_CON_PINS_RE = re.compile(r"(\d+)[xX](\d+)")
_CON_PITCH_RE = re.compile(r"_P(\d+(?:[.,]\d+)?)mm", re.IGNORECASE)
# Known KLC connector series prefixes (matched against footprint entry name)
_CON_SERIES_PREFIXES = (
    "JST_PH",
    "JST_XH",
    "JST_GH",
    "JST_SH",
    "JST_ZH",
    "PinHeader",
    "Molex",
    "USB",
    "RJ",
)


@dataclass(frozen=True)
class JlcpcbParametricQueryPlan:
    """Planned JLCPCB query shape for one inventory item."""

    use_parametric: bool
    base_query: str
    keyword_query: str
    reason: str
    first_sort_name: str | None = None
    second_sort_name: str | None = None
    component_specification_list: tuple[str, ...] = ()
    component_attribute_list: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def component_attribute_payload(self) -> list[dict[str, list[str]]]:
        """Return API-ready attribute payload."""

        payload: list[dict[str, list[str]]] = []
        for name, values in self.component_attribute_list:
            payload.append({name: list(values)})
        return payload

    def cache_fingerprint(self) -> str:
        """Return deterministic cache fingerprint for this plan."""

        specs = ",".join(self.component_specification_list)
        attrs = ";".join(f"{k}={','.join(v)}" for k, v in self.component_attribute_list)
        return (
            "jlcpcb"
            f"|first={self.first_sort_name or ''}"
            f"|second={self.second_sort_name or ''}"
            f"|spec={specs}"
            f"|attr={attrs}"
            f"|q={normalize_query(self.keyword_query)}"
        )


def build_parametric_query_plan(
    item: InventoryItem,
    *,
    base_query: str,
    defaults: DefaultsConfig | None = None,
) -> JlcpcbParametricQueryPlan:
    """Build a parametric query plan for one inventory item.

    Supported categories:
    - RES (resistor)
    - CAP (capacitor) — with electrolytic vs MLCC technology detection
    - IND (inductor) — with ferrite bead, power, and signal/RF subtype routing
    - CON (connector) — with pitch/pin-count/series extraction from footprint

    Args:
        item: Inventory item to build a query plan for.
        base_query: Pre-built keyword query string (used as fallback).
        defaults: Defaults profile to use. Loads 'generic' profile when None.
    """
    cfg = defaults if defaults is not None else get_defaults()
    category = _normalize_category(item.category)
    if category == "RES":
        return _build_resistor_plan(item, base_query=base_query, defaults=cfg)
    if category == "CAP":
        return _build_capacitor_plan(item, base_query=base_query, defaults=cfg)
    if category == "IND":
        return _build_inductor_plan(item, base_query=base_query, defaults=cfg)
    if category == "CON":
        return _build_connector_plan(item, base_query=base_query, defaults=cfg)

    return JlcpcbParametricQueryPlan(
        use_parametric=False,
        base_query=base_query,
        keyword_query=base_query,
        reason=f"unsupported category: {category or '(missing)'}",
    )


def _build_resistor_plan(
    item: InventoryItem, *, base_query: str, defaults: DefaultsConfig
) -> JlcpcbParametricQueryPlan:
    rules = defaults.get_category_route_rules("resistor")
    first_sort = rules.get("first_sort", "Resistors")
    second_sort = _resistor_second_sort(item, defaults=defaults)

    specs: list[str] = []
    package = _normalize_token(item.package)
    if package:
        specs.append(package)

    resistance = _resistance_attribute_value(item)
    if not resistance:
        return JlcpcbParametricQueryPlan(
            use_parametric=False,
            base_query=base_query,
            keyword_query=base_query,
            reason="missing resistance value for resistor parametric search",
        )

    tolerance = _normalize_tolerance(
        item.tolerance,
        default=defaults.get_domain_default("resistor", "tolerance", fallback="5%"),
    )

    attributes: list[tuple[str, tuple[str, ...]]] = [("Resistance", (resistance,))]
    if tolerance:
        attributes.append(("Tolerance", (tolerance,)))

    power_rating = _normalize_token(item.wattage) or defaults.get_package_power(package)
    technology = _resistor_technology_token(item.type)

    keyword_query = _merge_keyword_tokens(base_query, [technology, power_rating])

    return JlcpcbParametricQueryPlan(
        use_parametric=True,
        base_query=base_query,
        keyword_query=keyword_query,
        reason="resistor parametric query plan",
        first_sort_name=first_sort,
        second_sort_name=second_sort,
        component_specification_list=tuple(specs),
        component_attribute_list=tuple(attributes),
    )


def _build_capacitor_plan(
    item: InventoryItem, *, base_query: str, defaults: DefaultsConfig
) -> JlcpcbParametricQueryPlan:
    rules = defaults.get_category_route_rules("capacitor")
    first_sort = rules.get("first_sort", "Capacitors")

    # Technology detection: electrolytic/tantalum vs MLCC
    if _detect_cap_is_electrolytic(item):
        second_sort = rules.get(
            "second_sort_electrolytic", "Aluminum Electrolytic Capacitors"
        )
        is_electrolytic = True
    else:
        second_sort = rules.get(
            "second_sort_mlcc", "Multilayer Ceramic Capacitors (MLCC)"
        )
        is_electrolytic = False

    specs: list[str] = []
    package = _normalize_token(item.package)
    if package:
        specs.append(package)

    capacitance = _capacitance_attribute_value(item)
    if not capacitance:
        return JlcpcbParametricQueryPlan(
            use_parametric=False,
            base_query=base_query,
            keyword_query=base_query,
            reason="missing capacitance value for capacitor parametric search",
        )

    tolerance = _normalize_tolerance(
        item.tolerance,
        default=defaults.get_domain_default("capacitor", "tolerance", fallback="10%"),
    )
    voltage = _normalize_voltage(item.voltage) or defaults.get_package_voltage(package)

    attributes: list[tuple[str, tuple[str, ...]]] = [("Capacitance", (capacitance,))]
    if tolerance:
        attributes.append(("Tolerance", (tolerance,)))

    if is_electrolytic:
        # Electrolytic: voltage is the key search term; dielectric not applicable
        keyword_query = _merge_keyword_tokens(base_query, [voltage])
    else:
        dielectric = _dielectric_token(item.type) or defaults.get_domain_default(
            "capacitor", "dielectric", fallback="X7R"
        )
        keyword_query = _merge_keyword_tokens(base_query, [dielectric, voltage])

    return JlcpcbParametricQueryPlan(
        use_parametric=True,
        base_query=base_query,
        keyword_query=keyword_query,
        reason="capacitor parametric query plan",
        first_sort_name=first_sort,
        second_sort_name=second_sort,
        component_specification_list=tuple(specs),
        component_attribute_list=tuple(attributes),
    )


def _build_inductor_plan(
    item: InventoryItem, *, base_query: str, defaults: DefaultsConfig
) -> JlcpcbParametricQueryPlan:
    """Build a parametric query plan for an inductor (IND)."""
    rules = defaults.get_category_route_rules("inductor")
    first_sort = rules.get("first_sort", "Inductors")

    subtype = _detect_ind_subtype(item)
    if subtype == "ferrite":
        second_sort = rules.get("second_sort_ferrite", "Ferrite Beads")
    elif subtype == "power":
        second_sort = rules.get("second_sort_power", "Power Inductors")
    else:
        second_sort = rules.get("second_sort_signal", "Inductors (SMD)")

    specs: list[str] = []
    package = _normalize_token(item.package)
    if package:
        specs.append(package)

    if subtype == "ferrite":
        # Ferrite beads: rated by impedance, not inductance; navigate to category
        # and use keyword query — no structured inductance attribute.
        return JlcpcbParametricQueryPlan(
            use_parametric=True,
            base_query=base_query,
            keyword_query=base_query,
            reason="ferrite bead parametric query plan",
            first_sort_name=first_sort,
            second_sort_name=second_sort,
            component_specification_list=tuple(specs),
            component_attribute_list=(),
        )

    inductance = _inductance_attribute_value(item)
    if not inductance:
        return JlcpcbParametricQueryPlan(
            use_parametric=False,
            base_query=base_query,
            keyword_query=base_query,
            reason="missing inductance value for inductor parametric search",
        )

    attributes: list[tuple[str, tuple[str, ...]]] = [("Inductance", (inductance,))]
    current = _normalize_token(item.amperage)
    keyword_query = _merge_keyword_tokens(base_query, [current] if current else [])

    return JlcpcbParametricQueryPlan(
        use_parametric=True,
        base_query=base_query,
        keyword_query=keyword_query,
        reason=f"inductor parametric query plan ({subtype})",
        first_sort_name=first_sort,
        second_sort_name=second_sort,
        component_specification_list=tuple(specs),
        component_attribute_list=tuple(attributes),
    )


def _build_connector_plan(
    item: InventoryItem, *, base_query: str, defaults: DefaultsConfig
) -> JlcpcbParametricQueryPlan:
    """Build a parametric query plan for a connector (CON)."""
    rules = defaults.get_category_route_rules("connector")
    first_sort = rules.get("first_sort", "Connectors")

    tokens: list[str] = []
    has_structured_data = False

    # 1. First-class item fields (populated directly from CSV or schematic properties)
    if item.pitch:
        tokens.append(_normalize_token(item.pitch))
        has_structured_data = True
    if item.pins:
        tokens.append(f"{_normalize_token(item.pins)}-pin")
        has_structured_data = True

    # 2. Parse footprint entry name (after ':') for additional signals
    fp_entry = _fp_entry_name(item.footprint_full)
    fp_lib = _fp_lib_name(item.footprint_full)
    if fp_entry:
        has_structured_data = True

        # Series from entry name prefix (KLC-standardized), lib nickname as additive
        series = _detect_connector_series(fp_entry, fp_lib)
        if series:
            tokens.append(series)

        # Pitch from entry name (fallback when item.pitch absent)
        if not item.pitch:
            m = _CON_PITCH_RE.search(fp_entry)
            if m:
                pitch_str = m.group(1).replace(",", ".")
                tokens.append(f"{pitch_str}mm")

        # Pin count from entry name (fallback when item.pins absent)
        if not item.pins:
            m = _CON_PINS_RE.search(fp_entry)
            if m:
                rows, cols = int(m.group(1)), int(m.group(2))
                total_pins = rows * cols
                tokens.append(f"{total_pins}-pin")

    if not has_structured_data:
        return JlcpcbParametricQueryPlan(
            use_parametric=False,
            base_query=base_query,
            keyword_query=base_query,
            reason="connector: no structured data (footprint/pins/pitch absent) — manual search required",
        )

    keyword_query = _merge_keyword_tokens(base_query, [*tokens, "connector"])
    return JlcpcbParametricQueryPlan(
        use_parametric=True,
        base_query=base_query,
        keyword_query=keyword_query,
        reason="connector keyword-enriched parametric query plan",
        first_sort_name=first_sort,
        second_sort_name=None,
        component_specification_list=(),
        component_attribute_list=(),
    )


def _normalize_category(text: str) -> str:
    return _normalize_token(text).upper()


def _normalize_token(text: str) -> str:
    return " ".join((text or "").strip().split())


def _normalize_tolerance(text: str, *, default: str) -> str:
    t = _normalize_token(text)
    if not t or t.upper() == "N/A":
        t = default
    if not t:
        return ""
    if t.endswith("%"):
        return t
    if t.replace(".", "", 1).isdigit():
        return f"{t}%"
    return t


def _normalize_voltage(text: str) -> str:
    v = _normalize_token(text).upper()
    if not v or v == "N/A":
        return ""
    if v.endswith("V"):
        return v
    if v.replace(".", "", 1).isdigit():
        return f"{v}V"
    return v


def _package_default(mapping: dict[str, str], package: str) -> str:
    p = _normalize_token(package).upper()
    if not p:
        return ""
    return mapping.get(p, "")


def _resistance_attribute_value(item: InventoryItem) -> str:
    raw = ""
    if item.resistance is not None:
        raw = ohms_to_eia(item.resistance)
    elif _normalize_token(item.value):
        raw = _normalize_token(item.value)

    if not raw:
        return ""

    out = raw.replace(" ", "").replace("ohm", "Ω").replace("OHM", "Ω")
    if "Ω" not in out:
        out = f"{out}Ω"
    return out


def _capacitance_attribute_value(item: InventoryItem) -> str:
    if item.capacitance is not None:
        return _normalize_token(farad_to_eia(item.capacitance))
    return _normalize_token(item.value)


def _resistor_second_sort(
    item: InventoryItem, *, defaults: DefaultsConfig
) -> str | None:
    rules = defaults.get_category_route_rules("resistor")
    smd = _normalize_token(item.smd).upper()
    if smd == "SMD":
        return rules.get("second_sort_smd")
    if smd == "PTH":
        return rules.get("second_sort_pth")

    type_token = _normalize_token(item.type).lower()
    if any(t in type_token for t in ("wirewound", "metal film", "carbon film")):
        return rules.get("second_sort_pth")
    return None


def _resistor_technology_token(text: str) -> str:
    t = _normalize_token(text).lower()
    if "wirewound" in t:
        return "wirewound resistor"
    if "metal film" in t:
        return "metal film resistor"
    if "carbon film" in t:
        return "carbon film resistor"
    return ""


def _dielectric_token(text: str) -> str:
    t = _normalize_token(text).upper()
    for candidate in ("X7R", "X5R", "C0G", "NP0", "Y5V"):
        if candidate in t:
            return candidate
    return ""


def _merge_keyword_tokens(base_query: str, extras: list[str]) -> str:
    tokens: list[str] = []
    for token in [base_query, *extras]:
        cleaned = _normalize_token(token)
        if cleaned and cleaned not in tokens:
            tokens.append(cleaned)
    return " ".join(tokens).strip()


# ---------------------------------------------------------------------------
# KiCad footprint ID helpers
# ---------------------------------------------------------------------------


def _fp_entry_name(footprint_full: str) -> str:
    """Return the entry name (after ':') from a KiCad footprint ID."""
    if not footprint_full or ":" not in footprint_full:
        return ""
    return footprint_full.split(":", 1)[1]


def _fp_lib_name(footprint_full: str) -> str:
    """Return the library nickname (before ':') from a KiCad footprint ID."""
    if not footprint_full or ":" not in footprint_full:
        return ""
    return footprint_full.split(":", 1)[0]


# ---------------------------------------------------------------------------
# Technology detection helpers
# ---------------------------------------------------------------------------


def _detect_cap_is_electrolytic(item: InventoryItem) -> bool:
    """Return True if the capacitor is likely electrolytic or tantalum.

    Detection priority:
    - Strong: KiCad symbol entry name contains 'Polarized'
    - Strong: Footprint entry name (after ':') starts with 'CP_'
    - Additive: Library nickname contains 'Elec' or 'Tantalum' or 'Polarized'
      (KLC nicknames only; non-KLC nicknames are neutral, not negative)
    """
    if "Polarized" in item.symbol_name:
        return True
    fp_entry = _fp_entry_name(item.footprint_full)
    if fp_entry.startswith("CP_"):
        return True
    fp_lib = _fp_lib_name(item.footprint_full)
    if any(hint in fp_lib for hint in ("Elec", "Tantalum", "Polarized")):
        return True
    return False


def _detect_ind_subtype(item: InventoryItem) -> str:
    """Detect inductor subtype: 'ferrite', 'power', or 'signal'.

    Ferrite detection takes priority. Power detection uses structural signals
    (symbol name, package size). Default is signal/RF inductor.
    """
    description_upper = (item.description or "").upper()
    if "FERRITE" in description_upper:
        return "ferrite"

    if "_Core" in item.symbol_name or item.symbol_name == "L_Core":
        return "power"

    package = _normalize_token(item.package).upper()
    if package in {"1210", "1812", "2520", "4532"}:
        return "power"

    return "signal"


def _inductance_attribute_value(item: InventoryItem) -> str:
    """Return EIA-formatted inductance string for parametric attribute."""
    if item.inductance is not None:
        return _normalize_token(henry_to_eia(item.inductance))
    return _normalize_token(item.value)


def _detect_connector_series(fp_entry: str, fp_lib: str) -> str:
    """Detect connector series from footprint entry name and library nickname.

    Entry name prefix is the primary signal (KLC-standardized).
    Library nickname is an additive signal: if it contains a known series
    prefix it confirms the series, but a non-KLC nickname is neutral.
    Longer, more-specific prefixes are checked first to avoid false matches
    (e.g. 'JST_PH' before generic 'JST').
    """
    for prefix in _CON_SERIES_PREFIXES:
        if fp_entry.startswith(prefix):
            return prefix
    # Library nickname as additive: only if it explicitly names the series
    for prefix in _CON_SERIES_PREFIXES:
        if prefix in fp_lib:
            return prefix
    return ""


__all__ = [
    "JlcpcbParametricQueryPlan",
    "build_parametric_query_plan",
]
