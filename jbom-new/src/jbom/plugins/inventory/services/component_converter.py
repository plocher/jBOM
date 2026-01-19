"""
Service for converting KiCad Component objects to InventoryItem objects.

Handles IPN generation, category detection, package extraction, and property mapping.
"""

import re
from typing import List, Dict
from jbom.common.types import Component, InventoryItem, DEFAULT_PRIORITY


class ComponentToInventoryConverter:
    """Converts KiCad components to inventory items with intelligent categorization."""

    def __init__(self):
        """Initialize converter with category mappings."""
        # Order matters! More specific patterns should come first
        # Use OrderedDict or process longer patterns first to avoid false matches
        self.category_mappings = {
            # LED pattern (must come before general L pattern)
            "LED": "LED",
            # Diode patterns (specific patterns first)
            "D_Zener": "DIODE",
            "D_Schottky": "DIODE",
            "D_Small": "DIODE",
            "D": "DIODE",
            # IC patterns (specific patterns first)
            "NE555P": "IC",  # Specific timer IC
            "Timer": "IC",  # Timer category (library prefix)
            "U": "IC",
            "IC": "IC",
            # Capacitor patterns
            "C_Small": "CAP",
            "CP": "CAP",  # Polarized capacitor
            "C": "CAP",
            # Inductor patterns (L must come after LED)
            "L_Small": "IND",
            "L": "IND",
            # Resistor patterns
            "RV": "RES",  # Variable resistor
            "RT": "RES",  # Thermistor
            "RN": "RES",  # Resistor network
            "R": "RES",
            # Transistor patterns
            "MOSFET": "TRANSISTOR",
            "BJT": "TRANSISTOR",
            "Q": "TRANSISTOR",
            # Crystal/Oscillator patterns
            "XTAL": "CRYSTAL",
            "X": "CRYSTAL",
            "Y": "CRYSTAL",
            # Connector patterns
            "CONN": "CONN",
            "P": "CONN",
            "J": "CONN",
            # Switch patterns
            "SW": "SWITCH",
            "S": "SWITCH",
            # Fuse patterns
            "PTC": "FUSE",
            "F": "FUSE",
            # Test point patterns
            "TEST": "TEST",
            "TP": "TEST",
        }

    def convert_components(self, components: List[Component]) -> List[InventoryItem]:
        """Convert a list of components to inventory items with deduplication.

        Args:
            components: List of KiCad Component objects

        Returns:
            List of unique InventoryItem objects
        """
        # Group components by generated IPN to handle duplicates
        component_groups: Dict[str, List[Component]] = {}

        for component in components:
            if not component.in_bom or component.dnp:
                continue  # Skip components not in BOM or marked DNP

            ipn = self._generate_ipn(component)
            if ipn not in component_groups:
                component_groups[ipn] = []
            component_groups[ipn].append(component)

        # Convert each group to a single inventory item
        inventory_items = []
        for ipn, group_components in component_groups.items():
            # Use the first component as the base, but merge properties from all
            base_component = group_components[0]
            merged_properties = self._merge_component_properties(group_components)

            inventory_item = self._convert_single_component(
                base_component, merged_properties
            )
            inventory_items.append(inventory_item)

        return inventory_items

    def _convert_single_component(
        self, component: Component, merged_properties: Dict[str, str]
    ) -> InventoryItem:
        """Convert a single component to an inventory item."""
        category = self._detect_category(component)
        package = self._extract_package(component.footprint)
        ipn = self._generate_ipn(component)

        # Build description from available information
        description_parts = []
        if component.value and component.value != component.lib_id.split(":")[-1]:
            description_parts.append(component.value)
        if package:
            description_parts.append(package)
        description = " ".join(description_parts)

        return InventoryItem(
            ipn=ipn,
            keywords="",
            category=category,
            description=description,
            smd=self._detect_smd(component.footprint),
            value=component.value,
            type="",
            tolerance=merged_properties.get("Tolerance", ""),
            voltage=merged_properties.get("Voltage", merged_properties.get("V", "")),
            amperage=merged_properties.get("Amperage", merged_properties.get("A", "")),
            wattage=merged_properties.get("Wattage", merged_properties.get("W", "")),
            lcsc="",
            manufacturer=merged_properties.get("Manufacturer", ""),
            mfgpn=merged_properties.get("MFGPN", merged_properties.get("MPN", "")),
            datasheet=merged_properties.get("Datasheet", ""),
            package=package,
            distributor="",
            distributor_part_number="",
            uuid=component.uuid,
            fabricator="",
            priority=DEFAULT_PRIORITY,
            source="KiCad",
            source_file=None,
            raw_data={
                "original_properties": merged_properties,
                "lib_id": component.lib_id,
            },
        )

    def _generate_ipn(self, component: Component) -> str:
        """Generate an Internal Part Number (IPN) for a component.

        For resistors, handles E-series logic where precision in value notation
        indicates tolerance: 10K (5%), 10K0 (1%), 9K76 (1%)

        Args:
            component: KiCad Component object

        Returns:
            Generated IPN string
        """
        category = self._detect_category(component)

        # Use component value, cleaning it up for IPN use
        value = component.value
        if not value:
            # Fallback to lib_id symbol name
            value = component.lib_id.split(":")[-1]

        # For resistors, preserve E-series precision in IPN
        if category == "RES":
            clean_value = self._normalize_resistor_value_for_ipn(
                value, component.properties
            )
        else:
            clean_value = self._normalize_value_for_ipn(value)

        return f"{category}_{clean_value}"

    def _detect_category(self, component: Component) -> str:
        """Detect component category from lib_id and reference."""
        # First try to match based on lib_id
        if ":" in component.lib_id:
            lib_prefix, symbol = component.lib_id.split(":", 1)

            # Check both the library prefix and symbol
            for pattern, category in self.category_mappings.items():
                # Check library prefix (e.g., "Timer" in "Timer:NE555P")
                if lib_prefix.upper() == pattern.upper():
                    return category
                # Check symbol (e.g., "LED" in "Device:LED" or "NE555P" in "Timer:NE555P")
                if (
                    symbol.upper().startswith(pattern.upper())
                    or pattern.upper() in symbol.upper()
                    or symbol.upper() == pattern.upper()
                ):
                    return category

        # Fall back to reference prefix
        ref_match = re.match(r"^([A-Z]+)", component.reference)
        if ref_match:
            ref_prefix = ref_match.group(1)
            if ref_prefix in self.category_mappings:
                return self.category_mappings[ref_prefix]

        # Default to UNKNOWN for unknown components (more honest than IC)
        return "UNKNOWN"

    def _extract_package(self, footprint: str) -> str:
        """Extract package size from footprint name."""
        if not footprint:
            return ""

        # Common SMD package patterns
        smd_patterns = [
            r"(\d{4})_\d{4}Metric",  # 0603_1608Metric -> 0603
            r"(\d{4})",  # Direct 4-digit codes
            r"(SOT-\d+)",  # SOT-23, SOT-223, etc.
            r"(SOIC-\d+)",  # SOIC-8, SOIC-14, etc.
            r"(TSSOP-\d+)",  # TSSOP-28, etc.
            r"(QFN-\d+)",  # QFN-32, etc.
            r"(LQFP-\d+)",  # LQFP-64, etc.
            r"(BGA-\d+)",  # BGA-256, etc.
            r"(DIP-\d+)",  # DIP-8, DIP-14, etc.
        ]

        for pattern in smd_patterns:
            match = re.search(pattern, footprint, re.IGNORECASE)
            if match:
                return match.group(1)

        # If no standard pattern found, try to extract meaningful part
        clean_footprint = re.sub(r"_\d+x\d+mm.*$", "", footprint)
        clean_footprint = re.sub(r"^[A-Z]_", "", clean_footprint)

        return clean_footprint if clean_footprint else footprint

    def _detect_smd(self, footprint: str) -> str:
        """Detect if component is SMD based on footprint."""
        if not footprint:
            return ""

        smd_indicators = [
            "Metric",
            "_",
            "SOT",
            "SOIC",
            "TSSOP",
            "QFN",
            "LQFP",
            "BGA",
            "0201",
            "0402",
            "0603",
            "0805",
            "1206",
            "1210",
            "2010",
            "2512",
        ]

        tht_indicators = ["DIP", "PDIP", "SIP", "Pin", "THT", "ThroughHole"]

        footprint_upper = footprint.upper()

        for indicator in smd_indicators:
            if indicator.upper() in footprint_upper:
                return "SMD"

        for indicator in tht_indicators:
            if indicator.upper() in footprint_upper:
                return "THT"

        return ""

    def _normalize_value_for_ipn(self, value: str) -> str:
        """Normalize component value for use in IPN."""
        if not value:
            return "UNKNOWN"

        # Remove spaces and make safe for filename
        normalized = re.sub(r"\s+", "", value)

        # Replace problematic characters
        normalized = normalized.replace("/", "_")
        normalized = normalized.replace("\\", "_")
        normalized = normalized.replace(":", "_")

        return normalized

    def _normalize_resistor_value_for_ipn(
        self, value: str, properties: Dict[str, str]
    ) -> str:
        """Normalize resistor value for IPN with E-series awareness.

        E-series logic:
        - 10K    -> E12/E24 series, 5% tolerance (standard)
        - 10K0   -> E96 series, 1% tolerance (precision)
        - 9K76   -> E96 series, 1% tolerance (high precision)

        The presence of decimal digits indicates higher precision/tighter tolerance.

        Args:
            value: Resistor value string (e.g., '10K', '10K0', '9K76')
            properties: Component properties dictionary

        Returns:
            Normalized value suitable for IPN that preserves E-series distinction
        """
        if not value:
            return "UNKNOWN"

        # Remove spaces
        clean_value = re.sub(r"\s+", "", value)

        # Detect E-series precision from value format
        # Pattern: digits + optional decimal digits + unit (K, M, R)
        match = re.match(r"^(\d+)(K|M|R)(\d*)$", clean_value, re.IGNORECASE)
        if match:
            base_digits = match.group(1)
            unit = match.group(2).upper()
            decimal_digits = match.group(3)

            # If there are decimal digits after the unit, it's high precision
            if decimal_digits:
                # High precision E96 series: 10K0, 9K76
                normalized = f"{base_digits}{unit}{decimal_digits}"
            else:
                # Standard E12/E24 series: 10K, 4K7
                # Check if tolerance explicitly indicates high precision
                tolerance = properties.get("Tolerance", "")
                if tolerance in ["1%", "0.5%", "0.1%"]:
                    # Even though written as 10K, tolerance indicates E96
                    normalized = f"{base_digits}{unit}0"
                else:
                    # Standard series
                    normalized = f"{base_digits}{unit}"
        else:
            # Fallback to basic normalization for non-standard formats
            normalized = self._normalize_value_for_ipn(clean_value)

        # Make safe for filename
        normalized = normalized.replace("/", "_")
        normalized = normalized.replace("\\", "_")
        normalized = normalized.replace(":", "_")

        return normalized

    def _merge_component_properties(
        self, components: List[Component]
    ) -> Dict[str, str]:
        """Merge properties from multiple components with the same IPN."""
        merged = {}

        for component in components:
            for key, value in component.properties.items():
                if value and value.strip():  # Only add non-empty values
                    if key not in merged or not merged[key]:
                        merged[key] = value.strip()

        return merged
