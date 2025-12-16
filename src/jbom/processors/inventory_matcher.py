"""
Inventory matcher for jBOM.

Matches components to inventory items using a multi-stage scoring algorithm
that considers component type, value, package, and various properties.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple

from jbom.common.types import Component, InventoryItem
from jbom.common.constants import ComponentType, CommonFields, ScoreWeights
from jbom.common.packages import PackageType
from jbom.common.values import (
    parse_res_to_ohms,
    parse_cap_to_farad,
    parse_ind_to_henry,
    ohms_to_eia,
    farad_to_eia,
    henry_to_eia,
    cap_unit_multiplier,
    ind_unit_multiplier,
)
from jbom.loaders.inventory import InventoryLoader


# Import component type detection utilities from processors module
from jbom.processors.component_types import get_component_type, get_category_fields


class InventoryMatcher:
    """Matches components to inventory items"""

    def __init__(self, inventory_path: Path):
        self.inventory_path = inventory_path
        self.inventory: List[InventoryItem] = []
        self.inventory_fields: List[str] = []
        self._load_inventory()

    def _load_inventory(self):
        """Load inventory from supported file format (CSV, Excel, Numbers)"""
        loader = InventoryLoader(self.inventory_path)
        self.inventory, self.inventory_fields = loader.load()

    def find_matches(
        self, component: Component, debug: bool = False
    ) -> List[Tuple[InventoryItem, int, Optional[str]]]:
        """Find matching inventory items for a component using primary filtering first."""
        matches: List[Tuple[InventoryItem, int, Tuple[int, int], Optional[str]]] = []

        # Primary filters: category/type, package, exact value
        comp_type = self._get_component_type(component)
        comp_pkg = self._extract_package_from_footprint(component.footprint)
        comp_val_norm = (
            self._normalize_value(component.value) if component.value else ""
        )

        debug_info = []
        if debug:
            debug_info.append(f"Component: {component.reference} ({component.lib_id})")
            debug_info.append(f"Detected type: {comp_type or 'Unknown'}")
            debug_info.append(f"Package: {comp_pkg or 'None'}")
            debug_info.append(f"Value: {component.value or 'None'}")

        candidates_checked = 0
        candidates_passed = 0

        for item in self.inventory:
            candidates_checked += 1
            if not self._passes_primary_filters(
                comp_type, comp_pkg, comp_val_norm, component, item, debug
            ):
                continue
            candidates_passed += 1
            score, score_debug = self._calculate_match_score(component, item, debug)
            if score > 0:
                item_debug = None
                if debug:
                    item_debug = (
                        f"IPN: {item.ipn}, Score: {score}, Priority: {item.priority}"
                        + (f", {score_debug}" if score_debug else "")
                    )
                matches.append((item, score, item.priority, item_debug))

        if debug:
            debug_info.append(
                f"Candidates: {candidates_checked}, Passed filters: {candidates_passed}, Matched: {len(matches)}"
            )

        # Sort by priority first (lower is better), then by score desc
        matches.sort(key=lambda x: (x[2], -x[1]))

        # Format return with debug info
        result_debug = "; ".join(debug_info) if debug and debug_info else None
        return [
            (itm, sc, result_debug if i == 0 else item_debug)
            for i, (itm, sc, _, item_debug) in enumerate(matches)
        ]

    def _calculate_match_score(
        self, component: Component, item: InventoryItem, debug: bool = False
    ) -> Tuple[int, Optional[str]]:
        """Calculate match score between component and inventory item"""
        score = 0
        debug_parts = []

        # Component type matching
        comp_type = self._get_component_type(component)
        if comp_type and comp_type in item.category:
            score += 50
            if debug:
                debug_parts.append(f"Type match: +50 ({comp_type} in {item.category})")
        elif debug and comp_type:
            debug_parts.append(f"Type mismatch: {comp_type} not in {item.category}")

        # Value matching
        if component.value and self._values_match(component.value, item.value):
            score += 40
            if debug:
                debug_parts.append(
                    f"Value match: +40 ({component.value} = {item.value})"
                )
        elif debug and component.value:
            debug_parts.append(f"Value mismatch: {component.value} ≠ {item.value}")

        # Footprint matching
        if component.footprint and item.package:
            footprint_match = self._footprint_matches(component.footprint, item.package)
            if footprint_match:
                score += 30
                if debug:
                    debug_parts.append("Footprint match: +30")
            elif debug:
                debug_parts.append(
                    f"Footprint mismatch: {component.footprint} ≠ {item.package}"
                )

        # Property matching
        prop_score = self._match_properties(component, item)
        if prop_score > 0:
            score += prop_score
            if debug:
                debug_parts.append(f"Property match: +{prop_score}")

        # Keyword matching
        if component.value in item.keywords:
            score += 10
            if debug:
                debug_parts.append("Keyword match: +10")

        debug_info = ", ".join(debug_parts) if debug and debug_parts else None
        return score, debug_info

    def _extract_package_from_footprint(self, footprint: str) -> str:
        fp = (footprint or "").lower()

        # Try direct matching with SMD packages (standard format)
        # Sort by length descending to match longer patterns first (e.g., 'sot-23' before 'sot')
        for pattern in sorted(PackageType.SMD_PACKAGES, key=len, reverse=True):
            if pattern in fp:
                return pattern

        return ""

    def _passes_primary_filters(
        self,
        comp_type: Optional[str],
        comp_pkg: str,
        comp_val_norm: str,
        component: Component,
        item: InventoryItem,
        debug: bool = False,
    ) -> bool:
        # 1) Type/category must match if we could determine it
        if comp_type:
            cat = (item.category or "").upper()
            if comp_type not in cat:
                return False
        # 2) Package must match when we can extract it
        if comp_pkg:
            ipkg = (item.package or "").lower()
            if comp_pkg not in ipkg:
                return False
        # 3) Value match by type (numeric for RES/CAP/IND)
        if comp_val_norm:
            if comp_type == ComponentType.RESISTOR:
                comp_num = self._parse_res_to_ohms(component.value)
                inv_num = self._parse_res_to_ohms(item.value)
                if (
                    comp_num is None
                    or inv_num is None
                    or abs(comp_num - inv_num) > 1e-12
                ):
                    return False
            elif comp_type == ComponentType.CAPACITOR:
                comp_num = self._parse_cap_to_farad(component.value)
                inv_num = self._parse_cap_to_farad(item.value)
                if (
                    comp_num is None
                    or inv_num is None
                    or abs(comp_num - inv_num) > 1e-18
                ):
                    return False
            elif comp_type == ComponentType.INDUCTOR:
                comp_num = self._parse_ind_to_henry(component.value)
                inv_num = self._parse_ind_to_henry(item.value)
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

    def _get_component_type(self, component: Component) -> Optional[str]:
        """Determine component type from lib_id or footprint"""
        return get_component_type(component.lib_id, component.footprint)

    def _values_match(self, comp_value: str, inv_value: str) -> bool:
        """Check if component and inventory values match"""
        if not comp_value or not inv_value:
            return False

        # Normalize values
        comp_norm = self._normalize_value(comp_value)
        inv_norm = self._normalize_value(inv_value)

        return comp_norm == inv_norm

    def _normalize_value(self, value: str) -> str:
        """Normalize values for non-resistance comparisons (legacy fallback)."""
        value = (value or "").strip().lower()
        # Strip unit symbols and collapse whitespace
        value = re.sub(r"[Ωω]|ohm", "", value)
        value = value.replace("μ", "u")
        value = re.sub(r"\s+", "", value)
        return value

    # ---- Resistance parsing / EIA formatting helpers ----
    _OHM_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*([kKmMrR]?)\s*\+?\s*$")

    def _parse_res_to_ohms(self, s: str) -> Optional[float]:
        """Delegate to common.values.parse_res_to_ohms (kept for back-compat)."""
        return parse_res_to_ohms(s)

    def _ohms_to_eia(self, ohms: float, *, force_trailing_zero: bool = False) -> str:
        """Delegate to common.values.ohms_to_eia (kept for back-compat)."""
        return ohms_to_eia(ohms, force_trailing_zero=force_trailing_zero)

    # ---- Capacitor parsing / EIA-ish formatting ----
    def _parse_cap_to_farad(self, s: str) -> Optional[float]:
        return parse_cap_to_farad(s)

    def _cap_unit_multiplier(self, unit: str) -> float:
        return cap_unit_multiplier(unit)

    def _farad_to_eia(self, farad: float) -> str:
        return farad_to_eia(farad)

    # ---- Inductor parsing / EIA-ish formatting ----
    def _parse_ind_to_henry(self, s: str) -> Optional[float]:
        return parse_ind_to_henry(s)

    def _ind_unit_multiplier(self, unit: str) -> float:
        return ind_unit_multiplier(unit)

    def _henry_to_eia(self, henry: float) -> str:
        return henry_to_eia(henry)

    def _footprint_matches(self, footprint: str, package: str) -> bool:
        """Check if footprint matches package inventory designation"""
        if not footprint or not package:
            return False

        footprint = footprint.lower()
        package = package.lower()

        # First try direct matching: check if any SMD package pattern
        # appears in both footprint and package (most common case)
        for pattern in PackageType.SMD_PACKAGES:
            if pattern in footprint and pattern in package:
                return True

        # Second try: automatic dash removal for inventory naming variations
        # Many inventories use 'sot23' instead of 'sot-23', 'sod123' instead of 'sod-123', etc.
        for pattern in PackageType.SMD_PACKAGES:
            if "-" in pattern:
                pattern_no_dash = pattern.replace("-", "")
                if pattern in footprint and pattern_no_dash in package:
                    return True

        return False

    def _match_properties(self, component: Component, item: InventoryItem) -> int:
        """Match component properties with inventory item using category-specific logic"""
        score = 0

        # Get component type to determine which properties are relevant
        comp_type = self._get_component_type(component)
        relevant_fields = (
            get_category_fields(comp_type) if comp_type else get_category_fields("")
        )

        # Tolerance matching - exact match preferred; tighter tolerances substitute only when exact unavailable
        if (
            CommonFields.TOLERANCE in relevant_fields
            and CommonFields.TOLERANCE in component.properties
            and item.tolerance
        ):
            comp_tol = self._parse_tolerance_percent(
                component.properties[CommonFields.TOLERANCE]
            )
            item_tol = self._parse_tolerance_percent(item.tolerance)

            if comp_tol is not None and item_tol is not None:
                if comp_tol == item_tol:
                    # Exact match - full score
                    score += ScoreWeights.TOLERANCE_EXACT
                elif item_tol < comp_tol:
                    # Inventory has tighter tolerance than required - acceptable substitution
                    # Prefer next-tighter over overly-tight: score inversely proportional to tightness gap
                    # Gap = comp_tol - item_tol (positive value)
                    # Closer gap (smaller tightness difference) gets higher score
                    # Use a bonus that decreases as tolerance gets tighter than necessary
                    tolerance_gap = comp_tol - item_tol
                    # Award full bonus if within 1% of required, half bonus if tighter
                    if tolerance_gap <= 1.0:
                        score += (
                            ScoreWeights.TOLERANCE_BETTER
                        )  # Nearly exact or 1% tighter
                    else:
                        score += max(
                            1, ScoreWeights.TOLERANCE_BETTER // 2
                        )  # Significantly tighter gets reduced bonus
                # If item_tol >= comp_tol, no points (exact match handled above, looser can't substitute)

        # Voltage matching (V or Voltage)
        if (
            any(field in relevant_fields for field in [CommonFields.VOLTAGE, "Voltage"])
            and item.voltage
        ):
            voltage_props = [
                p
                for p in ["Voltage", CommonFields.VOLTAGE]
                if p in component.properties
            ]
            for prop in voltage_props:
                if component.properties[prop] in item.voltage:
                    score += ScoreWeights.VOLTAGE_MATCH
                    break

        # Current/Amperage matching (A or Amperage)
        if (
            any(
                field in relevant_fields
                for field in [CommonFields.AMPERAGE, "Amperage"]
            )
            and item.amperage
        ):
            current_props = [
                p
                for p in [CommonFields.AMPERAGE, "Amperage"]
                if p in component.properties
            ]
            for prop in current_props:
                if component.properties[prop] in item.amperage:
                    score += ScoreWeights.CURRENT_MATCH
                    break

        # Power/Wattage matching (W, Power, or P)
        if (
            any(
                field in relevant_fields
                for field in [CommonFields.WATTAGE, CommonFields.POWER]
            )
            and item.wattage
        ):
            power_props = [
                p
                for p in [CommonFields.WATTAGE, CommonFields.POWER, "P"]
                if p in component.properties
            ]
            for prop in power_props:
                if component.properties[prop] in item.wattage:
                    score += ScoreWeights.POWER_MATCH
                    break

        # LED-specific properties
        if comp_type == ComponentType.LED:
            # Wavelength matching
            if (
                "Wavelength" in component.properties
                and hasattr(item, "wavelength")
                and item.wavelength
            ):
                if component.properties["Wavelength"] in item.wavelength:
                    score += ScoreWeights.LED_WAVELENGTH

            # Luminous intensity (mcd) matching
            if "mcd" in component.properties and hasattr(item, "mcd") and item.mcd:
                if component.properties["mcd"] in item.mcd:
                    score += ScoreWeights.LED_INTENSITY

            # Angle matching
            if (
                "Angle" in component.properties
                and hasattr(item, "angle")
                and item.angle
            ):
                if component.properties["Angle"] in item.angle:
                    score += ScoreWeights.LED_ANGLE

        # Oscillator-specific properties
        if comp_type == ComponentType.OSCILLATOR:
            if (
                "Frequency" in component.properties
                and hasattr(item, "frequency")
                and item.frequency
            ):
                if component.properties["Frequency"] in item.frequency:
                    score += ScoreWeights.OSC_FREQUENCY

            if (
                "Stability" in component.properties
                and hasattr(item, "stability")
                and item.stability
            ):
                if component.properties["Stability"] in item.stability:
                    score += ScoreWeights.OSC_STABILITY

            if "Load" in component.properties and hasattr(item, "load") and item.load:
                if component.properties["Load"] in item.load:
                    score += ScoreWeights.OSC_LOAD

        # Connector-specific properties
        if comp_type == ComponentType.CONNECTOR:
            if (
                "Pitch" in component.properties
                and hasattr(item, "pitch")
                and item.pitch
            ):
                if component.properties["Pitch"] in item.pitch:
                    score += ScoreWeights.CON_PITCH

        # MCU/IC-specific properties
        if comp_type in [
            ComponentType.MICROCONTROLLER,
            ComponentType.INTEGRATED_CIRCUIT,
        ]:
            if (
                "Family" in component.properties
                and hasattr(item, "family")
                and item.family
            ):
                if component.properties["Family"] in item.family:
                    score += ScoreWeights.MCU_FAMILY

        # Generic property matching for any additional properties
        for prop_name, prop_value in component.properties.items():
            if (
                prop_name in relevant_fields
                and hasattr(item, prop_name.lower())
                and getattr(item, prop_name.lower(), None)
            ):
                if prop_value in getattr(item, prop_name.lower()):
                    score += (
                        ScoreWeights.GENERIC_PROPERTY
                    )  # Lower score for generic matches

        return score

    def _parse_tolerance_percent(self, tol_str: str) -> Optional[float]:
        """Parse tolerance string like '±5%', '5%', '±1%' to numeric percentage"""
        if not tol_str:
            return None

        # Clean up the string - remove ±, %, spaces
        cleaned = tol_str.strip().replace("±", "").replace("%", "").strip()

        try:
            return float(cleaned)
        except ValueError:
            return None
