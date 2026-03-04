"""Phase 4 decision-tree query shaping for JLCPCB/LCSC search.

This module provides deterministic helper logic for building structured
JLCPCB/LCSC parametric search queries from inventory item attributes.

All configurable constants (domain defaults, package ratings, routing rules,
query fields) are loaded from the defaults profile system (#98) via
get_defaults() / DefaultsConfig. See generic.defaults.yaml for factory values
and docs/dev/architecture/component-attribute-enrichment.md for the design model.
"""

from __future__ import annotations

from dataclasses import dataclass

from jbom.common.types import InventoryItem
from jbom.common.value_parsing import farad_to_eia, ohms_to_eia
from jbom.config.defaults import DefaultsConfig, get_defaults
from jbom.services.search.cache import normalize_query


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
            "phase4"
            f"|first={self.first_sort_name or ''}"
            f"|second={self.second_sort_name or ''}"
            f"|spec={specs}"
            f"|attr={attrs}"
            f"|q={normalize_query(self.keyword_query)}"
        )


def build_phase4_parametric_query_plan(
    item: InventoryItem,
    *,
    base_query: str,
    defaults: DefaultsConfig | None = None,
) -> JlcpcbParametricQueryPlan:
    """Build a Phase 4 query plan for one inventory item.

    Supported categories:
    - RES (resistor)
    - CAP (capacitor)

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
    dielectric = _dielectric_token(item.type) or defaults.get_domain_default(
        "capacitor", "dielectric", fallback="X7R"
    )

    attributes: list[tuple[str, tuple[str, ...]]] = [("Capacitance", (capacitance,))]
    if tolerance:
        attributes.append(("Tolerance", (tolerance,)))

    keyword_query = _merge_keyword_tokens(base_query, [dielectric, voltage])

    return JlcpcbParametricQueryPlan(
        use_parametric=True,
        base_query=base_query,
        keyword_query=keyword_query,
        reason="capacitor parametric query plan",
        first_sort_name=first_sort,
        second_sort_name=None,
        component_specification_list=tuple(specs),
        component_attribute_list=tuple(attributes),
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


__all__ = [
    "JlcpcbParametricQueryPlan",
    "build_phase4_parametric_query_plan",
]
