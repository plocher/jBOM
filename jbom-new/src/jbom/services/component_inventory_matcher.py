"""Component inventory matcher service for jBOM.

Matches project components against existing inventory using sophisticated
scoring algorithms that consider component type, value, package, and properties.
Adapted from mature logic in the old jBOM codebase.
"""

import re
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

from jbom.common.types import InventoryItem
from jbom.services.inventory_reader import InventoryReader


@dataclass
class ComponentMatch:
    """Represents a component matched against inventory."""

    inventory_item: InventoryItem
    score: int
    debug_info: Optional[str] = None


class ComponentInventoryMatcher:
    """Matches project components to existing inventory items using sophisticated scoring."""

    def __init__(self, inventory_file: Optional[Path] = None):
        """Initialize matcher with optional inventory file."""
        self.inventory: List[InventoryItem] = []
        self.inventory_fields: List[str] = []

        if inventory_file:
            self._load_inventory(inventory_file)

    def _load_inventory(self, inventory_file: Path) -> None:
        """Load inventory from file."""
        if not inventory_file.exists():
            raise FileNotFoundError(f"Inventory file not found: {inventory_file}")

        reader = InventoryReader(inventory_file)
        self.inventory, self.inventory_fields = reader.load()

    def find_matches(
        self, component_data: Dict, debug: bool = False
    ) -> List[ComponentMatch]:
        """Find matching inventory items for a component.

        Args:
            component_data: Component data dict with keys like 'value', 'footprint', 'lib_id', 'properties'
            debug: Enable debug information

        Returns:
            List of ComponentMatch objects sorted by match quality
        """
        if not self.inventory:
            return []

        matches = []

        # Extract component characteristics
        comp_type = self._get_component_type(component_data)
        comp_pkg = self._extract_package_from_footprint(
            component_data.get("footprint", "")
        )
        comp_val_norm = self._normalize_value(component_data.get("value", ""))

        debug_info = []
        if debug:
            debug_info.append(f"Component type: {comp_type or 'Unknown'}")
            debug_info.append(f"Package: {comp_pkg or 'None'}")
            debug_info.append(f"Value: {component_data.get('value', 'None')}")

        candidates_checked = 0
        candidates_passed = 0

        for item in self.inventory:
            candidates_checked += 1

            # Apply primary filters first
            if not self._passes_primary_filters(
                comp_type, comp_pkg, comp_val_norm, component_data, item
            ):
                continue

            candidates_passed += 1
            score = self._calculate_match_score(component_data, item, comp_type)

            if score > 0:
                item_debug = None
                if debug:
                    item_debug = f"IPN: {item.ipn}, Score: {score}"

                matches.append(
                    ComponentMatch(
                        inventory_item=item, score=score, debug_info=item_debug
                    )
                )

        if debug:
            debug_info.append(
                f"Candidates: {candidates_checked}, Passed filters: {candidates_passed}, Matched: {len(matches)}"
            )

        # Sort by score descending (best matches first)
        matches.sort(key=lambda x: x.score, reverse=True)

        # Add global debug info to first match
        if matches and debug:
            matches[0].debug_info = f"{matches[0].debug_info}; {'; '.join(debug_info)}"

        return matches

    def _passes_primary_filters(
        self,
        comp_type: Optional[str],
        comp_pkg: str,
        comp_val_norm: str,
        component_data: Dict,
        item: InventoryItem,
    ) -> bool:
        """Apply primary filters: type/category, package, value matching."""
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

        # 3) Value match - for passive components use numeric comparison
        if comp_val_norm:
            comp_value = component_data.get("value", "")
            if comp_type == "RESISTOR":
                comp_num = self._parse_res_to_ohms(comp_value)
                inv_num = self._parse_res_to_ohms(item.value)
                if (
                    comp_num is None
                    or inv_num is None
                    or abs(comp_num - inv_num) > 1e-12
                ):
                    return False
            elif comp_type == "CAPACITOR":
                comp_num = self._parse_cap_to_farad(comp_value)
                inv_num = self._parse_cap_to_farad(item.value)
                if (
                    comp_num is None
                    or inv_num is None
                    or abs(comp_num - inv_num) > 1e-18
                ):
                    return False
            elif comp_type == "INDUCTOR":
                comp_num = self._parse_ind_to_henry(comp_value)
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

    def _calculate_match_score(
        self, component_data: Dict, item: InventoryItem, comp_type: Optional[str]
    ) -> int:
        """Calculate match score between component and inventory item."""
        score = 0

        # Component type matching (50 points)
        if comp_type and comp_type in (item.category or ""):
            score += 50

        # Value matching (40 points)
        comp_value = component_data.get("value", "")
        if comp_value and self._values_match(comp_value, item.value):
            score += 40

        # Footprint matching (30 points)
        comp_footprint = component_data.get("footprint", "")
        if (
            comp_footprint
            and item.package
            and self._footprint_matches(comp_footprint, item.package)
        ):
            score += 30

        # Property matching (varies)
        prop_score = self._match_properties(component_data, item, comp_type)
        score += prop_score

        return score

    def _get_component_type(self, component_data: Dict) -> Optional[str]:
        """Determine component type from lib_id or footprint."""
        lib_id = component_data.get("lib_id", "")

        if not lib_id:
            return None

        # Extract from lib_id (format: "library:symbol")
        if ":" in lib_id:
            _, symbol = lib_id.split(":", 1)
            symbol_upper = symbol.upper()

            if symbol_upper.startswith("R"):
                return "RESISTOR"
            elif symbol_upper.startswith("C"):
                return "CAPACITOR"
            elif symbol_upper.startswith("L"):
                return "INDUCTOR"
            elif symbol_upper.startswith("LED"):
                return "LED"
            elif symbol_upper.startswith("D"):
                return "DIODE"
            elif symbol_upper.startswith("U") or "IC" in symbol_upper:
                return "IC"

        return None

    def _extract_package_from_footprint(self, footprint: str) -> str:
        """Extract package designation from footprint."""
        if not footprint:
            return ""

        fp = footprint.lower()

        # Common SMD packages (sorted by length descending for better matching)
        smd_packages = [
            "sot-23-6",
            "sot-23-5",
            "sot-23-3",
            "sot-23",
            "sot-223",
            "sot-89",
            "soic-28",
            "soic-16",
            "soic-14",
            "soic-8",
            "soic",
            "qfn-32",
            "qfn-28",
            "qfn-24",
            "qfn-20",
            "qfn-16",
            "qfn",
            "tssop-28",
            "tssop-20",
            "tssop-16",
            "tssop-14",
            "tssop-8",
            "tssop",
            "msop-10",
            "msop-8",
            "msop",
            "1210",
            "1206",
            "1008",
            "0805",
            "0603",
            "0402",
            "0201",
        ]

        for pattern in smd_packages:
            if pattern in fp:
                return pattern

        return ""

    def _normalize_value(self, value: str) -> str:
        """Normalize values for comparison."""
        if not value:
            return ""

        value = value.strip().lower()
        # Remove common unit symbols and whitespace
        value = re.sub(r"[ωω]|ohm", "", value)
        value = value.replace("μ", "u")
        value = re.sub(r"\s+", "", value)
        return value

    def _values_match(self, comp_value: str, inv_value: str) -> bool:
        """Check if component and inventory values match."""
        if not comp_value or not inv_value:
            return False

        # Normalize both values
        comp_norm = self._normalize_value(comp_value)
        inv_norm = self._normalize_value(inv_value)

        return comp_norm == inv_norm

    def _footprint_matches(self, footprint: str, package: str) -> bool:
        """Check if footprint matches package designation."""
        if not footprint or not package:
            return False

        footprint = footprint.lower()
        package = package.lower()

        # Common SMD packages for pattern matching
        smd_patterns = [
            "sot-23",
            "sot-223",
            "soic",
            "qfn",
            "tssop",
            "msop",
            "1210",
            "1206",
            "1008",
            "0805",
            "0603",
            "0402",
            "0201",
        ]

        # Check if any pattern appears in both
        for pattern in smd_patterns:
            if pattern in footprint and pattern in package:
                return True

        # Try without dashes (some inventories use 'sot23' vs 'sot-23')
        for pattern in smd_patterns:
            if "-" in pattern:
                pattern_no_dash = pattern.replace("-", "")
                if pattern in footprint and pattern_no_dash in package:
                    return True

        return False

    def _match_properties(
        self, component_data: Dict, item: InventoryItem, comp_type: Optional[str]
    ) -> int:
        """Match component properties with inventory item."""
        score = 0
        properties = component_data.get("properties", {})

        # Tolerance matching (exact match gets 15 points, tighter tolerance gets 10)
        if "Tolerance" in properties and item.tolerance:
            comp_tol = self._parse_tolerance_percent(properties["Tolerance"])
            item_tol = self._parse_tolerance_percent(item.tolerance)

            if comp_tol is not None and item_tol is not None:
                if comp_tol == item_tol:
                    score += 15  # Exact match
                elif item_tol < comp_tol:
                    score += 10  # Tighter tolerance acceptable

        # Voltage matching (10 points)
        voltage_fields = ["Voltage", "V"]
        for field in voltage_fields:
            if field in properties and item.voltage:
                if properties[field] in item.voltage:
                    score += 10
                    break

        # Power/Wattage matching (10 points)
        power_fields = ["Wattage", "Power", "W", "P"]
        for field in power_fields:
            if field in properties and item.wattage:
                if properties[field] in item.wattage:
                    score += 10
                    break

        return score

    def _parse_tolerance_percent(self, tol_str: str) -> Optional[float]:
        """Parse tolerance string like '±5%', '5%' to numeric percentage."""
        if not tol_str:
            return None

        # Clean up the string
        cleaned = tol_str.strip().replace("±", "").replace("%", "").strip()

        try:
            return float(cleaned)
        except ValueError:
            return None

    # Simplified versions of the old parsing functions
    def _parse_res_to_ohms(self, value_str: str) -> Optional[float]:
        """Parse resistance value to ohms."""
        if not value_str:
            return None

        # Simple regex for basic resistance values
        match = re.match(r"^\s*([0-9]*\.?[0-9]+)\s*([kKmMrR]?)\s*$", value_str.strip())
        if not match:
            return None

        num_str, unit = match.groups()
        try:
            num = float(num_str)
        except ValueError:
            return None

        # Apply multiplier
        multipliers = {"k": 1000, "K": 1000, "m": 0.001, "M": 1000000, "r": 1, "R": 1}
        multiplier = multipliers.get(unit, 1)

        return num * multiplier

    def _parse_cap_to_farad(self, value_str: str) -> Optional[float]:
        """Parse capacitance value to farads."""
        if not value_str:
            return None

        # Simple regex for basic capacitance values
        match = re.match(
            r"^\s*([0-9]*\.?[0-9]+)\s*([pnumf]?)[fF]?\s*$", value_str.strip()
        )
        if not match:
            return None

        num_str, unit = match.groups()
        try:
            num = float(num_str)
        except ValueError:
            return None

        # Apply multiplier
        multipliers = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "f": 1e-15}
        multiplier = multipliers.get(unit, 1e-6)  # Default to microfarads

        return num * multiplier

    def _parse_ind_to_henry(self, value_str: str) -> Optional[float]:
        """Parse inductance value to henries."""
        if not value_str:
            return None

        # Simple regex for basic inductance values
        match = re.match(
            r"^\s*([0-9]*\.?[0-9]+)\s*([pnumf]?)[hH]?\s*$", value_str.strip()
        )
        if not match:
            return None

        num_str, unit = match.groups()
        try:
            num = float(num_str)
        except ValueError:
            return None

        # Apply multiplier
        multipliers = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3}
        multiplier = multipliers.get(unit, 1e-6)  # Default to microhenries

        return num * multiplier
