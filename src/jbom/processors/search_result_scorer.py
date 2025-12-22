"""
SearchResultScorer for ranking search results using InventoryMatcher logic.

Combines technical component matching with supplier quality metrics to produce
priority rankings for automated inventory enrichment.
"""
import re

from jbom.common.types import Component, InventoryItem, DEFAULT_PRIORITY
from jbom.search import SearchResult
from jbom.processors.inventory_matcher import InventoryMatcher


class SearchResultScorer:
    """Scores and ranks search results for inventory enrichment."""

    def __init__(self):
        """Initialize the scorer."""
        # Weights for composite scoring
        self.MATCH_SCORE_WEIGHT = 0.6  # Technical match quality
        self.STOCK_SCORE_WEIGHT = 0.2  # Stock quantity availability
        self.LIFECYCLE_SCORE_WEIGHT = (
            0.15  # Lifecycle status (Active > NRND > Obsolete)
        )
        self.PRICE_SCORE_WEIGHT = 0.05  # Price competitiveness (lower weight)

    def calculate_priority(
        self, component: Component, search_result: SearchResult
    ) -> int:
        """
        Calculate priority ranking for a search result vs component.

        Args:
            component: The KiCad component to match
            search_result: The search result from distributor

        Returns:
            Priority number (1=best, higher=worse)
        """
        # Convert search result to inventory item for InventoryMatcher
        inventory_item = self._search_result_to_inventory_item(search_result)

        # Create temporary matcher with just this item
        matcher = InventoryMatcher(None)
        matcher.set_inventory([inventory_item], [])

        # Get technical match score using InventoryMatcher logic
        matches = matcher.find_matches(component, debug=False)
        match_score = matches[0][1] if matches else 0

        # Calculate supplier quality metrics
        stock_score = self._calculate_stock_score(search_result.stock_quantity)
        lifecycle_score = self._calculate_lifecycle_score(
            search_result.lifecycle_status
        )
        price_score = self._calculate_price_score(
            self._parse_price(search_result.price)
        )

        # Combine scores with weights
        composite_score = (
            match_score * self.MATCH_SCORE_WEIGHT
            + stock_score * self.STOCK_SCORE_WEIGHT
            + lifecycle_score * self.LIFECYCLE_SCORE_WEIGHT
            + price_score * self.PRICE_SCORE_WEIGHT
        )

        # Convert to priority ranking (higher score = lower priority number = better)
        # Use more granular priority calculation for better differentiation
        if composite_score >= 95:
            priority = 1
        elif composite_score >= 85:
            priority = 2
        elif composite_score >= 75:
            priority = 3
        elif composite_score >= 65:
            priority = 4
        elif composite_score >= 55:
            priority = 5
        elif composite_score >= 45:
            priority = 6
        else:
            # Lower scores get higher priority numbers with finer gradation
            priority = min(20, max(7, int(8 + ((50 - composite_score) / 4))))

        return priority

    def _search_result_to_inventory_item(
        self, search_result: SearchResult
    ) -> InventoryItem:
        """
        Convert SearchResult to InventoryItem for InventoryMatcher scoring.

        Args:
            search_result: Search result from distributor

        Returns:
            InventoryItem suitable for matching
        """
        # Extract value from attributes or description
        value = self._extract_value_from_result(search_result)

        # Extract package from attributes or description
        package = self._extract_package_from_result(search_result)

        # Extract tolerance, voltage, etc from attributes
        tolerance = search_result.attributes.get("Tolerance", "")
        voltage = search_result.attributes.get("Voltage", "")

        # Create inventory item
        return InventoryItem(
            ipn="",  # Not needed for matching
            keywords="",
            category=self._extract_category_from_result(search_result),
            description=search_result.description,
            smd="",  # Could infer from package
            value=value,
            type="",
            tolerance=tolerance,
            voltage=voltage,
            amperage="",
            wattage="",
            lcsc="",  # Not from search results
            manufacturer=search_result.manufacturer,
            mfgpn=search_result.mpn,
            datasheet=search_result.datasheet,
            package=package,
            distributor=search_result.distributor,
            distributor_part_number=search_result.distributor_part_number,
            priority=DEFAULT_PRIORITY,  # Will be calculated
            source="Search",
            raw_data=search_result.raw_data,
        )

    def _extract_value_from_result(self, search_result: SearchResult) -> str:
        """Extract component value from search result."""
        # Try attributes first
        if "Resistance" in search_result.attributes:
            resistance = search_result.attributes["Resistance"]
            # Convert "10 kOhms" to "10k"
            return self._normalize_resistance_value(resistance)

        if "Capacitance" in search_result.attributes:
            capacitance = search_result.attributes["Capacitance"]
            # Convert "0.1 µF" to "100nF"
            return self._normalize_capacitance_value(capacitance)

        if "Inductance" in search_result.attributes:
            return search_result.attributes["Inductance"]

        # Try extracting from description
        return self._extract_value_from_description(search_result.description)

    def _extract_package_from_result(self, search_result: SearchResult) -> str:
        """Extract package info from search result."""
        # Try attributes first
        if "Package" in search_result.attributes:
            return search_result.attributes["Package"]

        # Extract from description (look for common SMD packages)
        desc = (search_result.description or "").lower()
        common_packages = [
            "0603",
            "0805",
            "1206",
            "0402",
            "1210",
            "2512",
            "sot-23",
            "soic-8",
            "qfn-16",
            "bga-144",
        ]

        for package in common_packages:
            if package in desc:
                return package

        return ""

    def _extract_category_from_result(self, search_result: SearchResult) -> str:
        """Extract component category from search result."""
        desc = (search_result.description or "").upper()

        if "RES" in desc or "RESISTOR" in desc:
            return "RES"
        elif "CAP" in desc or "CAPACITOR" in desc:
            return "CAP"
        elif "IND" in desc or "INDUCTOR" in desc:
            return "IND"
        elif "LED" in desc:
            return "LED"
        elif "DIODE" in desc:
            return "DIODE"
        elif "IC" in desc or "MICROCONTROLLER" in desc:
            return "IC"
        else:
            return "OTHER"

    def _normalize_resistance_value(self, resistance_str: str) -> str:
        """Normalize resistance value to standard format."""
        # Convert "10 kOhms" to "10k", "1000 Ohms" to "1k", etc.
        resistance_str = resistance_str.replace("Ohms", "").replace("Ω", "").strip()

        if "k" in resistance_str.lower():
            return resistance_str.lower().replace(" ", "")
        elif "m" in resistance_str.lower():
            return resistance_str.lower().replace(" ", "")
        else:
            # Plain ohms value, convert to k if appropriate
            try:
                value = float(resistance_str.split()[0])
                if value >= 1000:
                    return f"{value/1000:.0f}k"
                else:
                    return f"{value:.0f}"
            except (ValueError, IndexError):
                return resistance_str

    def _normalize_capacitance_value(self, capacitance_str: str) -> str:
        """Normalize capacitance value to standard format."""
        # Convert "0.1 µF" to "100nF", "100 pF" to "100pF", etc.
        capacitance_str = capacitance_str.replace("µ", "u").replace("μ", "u")

        if "uf" in capacitance_str.lower():
            # Convert µF to nF if appropriate
            try:
                value = float(capacitance_str.split()[0])
                if value < 1:
                    return f"{value * 1000:.0f}nF"
                else:
                    return f"{value}uF"
            except (ValueError, IndexError):
                return capacitance_str

        return capacitance_str.lower().replace(" ", "")

    def _extract_value_from_description(self, description: str) -> str:
        """Extract value from description text."""
        # Look for resistance patterns: "10K", "1.2M", "100R"
        resistance_pattern = r"(\d+(?:\.\d+)?)\s*([KMR]?)(?:\s*OHM)?(?=\s|$)"
        match = re.search(resistance_pattern, description, re.IGNORECASE)
        if match:
            value, unit = match.groups()
            if unit.upper() == "K":
                return f"{value}k"
            elif unit.upper() == "M":
                return f"{value}M"
            else:
                return value

        # Look for capacitance patterns: "100NF", "0.1UF", "22PF"
        cap_pattern = r"(\d+(?:\.\d+)?)\s*([PNMU]F)"
        match = re.search(cap_pattern, description, re.IGNORECASE)
        if match:
            value, unit = match.groups()
            return f"{value}{unit.lower()}"

        return ""

    def _calculate_stock_score(self, stock_quantity: int) -> float:
        """
        Calculate score based on stock quantity availability.

        Args:
            stock_quantity: Number of units in stock

        Returns:
            Score from 0-100 (higher is better)
        """
        if stock_quantity <= 0:
            return 0
        elif stock_quantity < 100:
            return 20  # Low stock
        elif stock_quantity < 1000:
            return 60  # Medium stock
        elif stock_quantity < 10000:
            return 80  # Good stock
        else:
            return 100  # Excellent stock

    def _calculate_lifecycle_score(self, lifecycle_status: str) -> float:
        """
        Calculate score based on part lifecycle status.

        Args:
            lifecycle_status: Part lifecycle (Active, NRND, Obsolete, etc.)

        Returns:
            Score from 0-100 (higher is better)
        """
        status = (lifecycle_status or "").upper()

        if status == "ACTIVE":
            return 100
        elif status == "NRND" or "NOT RECOMMENDED" in status:
            return 60
        elif status == "OBSOLETE":
            return 20
        else:
            return 30  # Unknown status gets lower score than obsolete

    def _calculate_price_score(self, price: float) -> float:
        """
        Calculate score based on price competitiveness.

        Args:
            price: Unit price in dollars

        Returns:
            Score from 0-100 (lower price generally better, but not linear)
        """
        if price <= 0:
            return 0  # Invalid price

        # Price scoring is more complex - very cheap might indicate quality issues
        # Sweet spot is typically in reasonable mid-range
        if price < 0.01:
            return 40  # Suspiciously cheap
        elif price < 0.10:
            return 80  # Good price for passives
        elif price < 1.00:
            return 70  # Reasonable price
        elif price < 10.00:
            return 50  # Getting expensive
        else:
            return 30  # Very expensive

    def _parse_price(self, price_str: str) -> float:
        """Parse price string to float value."""
        try:
            # Remove currency symbols and whitespace
            price_clean = re.sub(r"[^\d\.]", "", price_str)
            return float(price_clean)
        except (ValueError, AttributeError):
            return 0.0
