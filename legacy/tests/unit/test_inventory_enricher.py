#!/usr/bin/env python3
"""Unit tests for InventoryEnricher class."""
import unittest
from unittest.mock import Mock, patch

from jbom.common.types import Component
from jbom.search import SearchResult, SearchProvider
from jbom.processors.inventory_enricher import InventoryEnricher


class TestInventoryEnricher(unittest.TestCase):
    """Test inventory enrichment with search results."""

    def setUp(self):
        """Set up test components and mock search provider."""
        # Mock components from project
        self.components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10k",
                footprint="Resistor_SMD:R_0603_1608Metric",
                properties={"Tolerance": "1%", "Power": "0.1W"},
            ),
            Component(
                reference="C1",
                lib_id="Device:C",
                value="100nF",
                footprint="Capacitor_SMD:C_0603_1608Metric",
                properties={"Voltage": "50V", "Type": "X7R"},
            ),
        ]

        # Mock search results
        self.search_results = [
            SearchResult(
                manufacturer="Yageo",
                mpn="RC0603FR-0710KL",
                description="RES SMD 10K OHM 1% 1/10W 0603",
                datasheet="",
                distributor="Mouser",
                distributor_part_number="603-RC0603FR-0710KL",
                availability="50000 In Stock",
                price="0.10",
                details_url="",
                raw_data={},
                attributes={"Resistance": "10 kOhms", "Tolerance": "1%"},
                stock_quantity=50000,
                lifecycle_status="Active",
            ),
            SearchResult(
                manufacturer="Samsung",
                mpn="CL10B104KB8NNNC",
                description="CAP CER 0.1UF 50V X7R 0603",
                datasheet="",
                distributor="Mouser",
                distributor_part_number="187-CL10B104KB8NNNC",
                availability="25000 In Stock",
                price="0.20",
                details_url="",
                raw_data={},
                attributes={
                    "Capacitance": "0.1 µF",
                    "Voltage": "50V",
                    "Dielectric": "X7R",
                },
                stock_quantity=25000,
                lifecycle_status="Active",
            ),
        ]

        # Mock search provider
        self.mock_provider = Mock(spec=SearchProvider)
        self.mock_provider.name = "MockProvider"

    def test_enricher_initialization(self):
        """Test InventoryEnricher initialization."""
        enricher = InventoryEnricher(
            components=self.components, search_provider=self.mock_provider, limit=1
        )

        self.assertEqual(enricher.components, self.components)
        self.assertEqual(enricher.search_provider, self.mock_provider)
        self.assertEqual(enricher.limit, 1)

    def test_enricher_initialization_with_defaults(self):
        """Test InventoryEnricher initialization with default parameters."""
        enricher = InventoryEnricher(
            components=self.components, search_provider=self.mock_provider
        )

        self.assertEqual(enricher.limit, 1)  # Default limit
        self.assertFalse(enricher.interactive)  # Default interactive

    def test_enrich_inventory_single_result(self):
        """Test enriching inventory with single search result per component."""

        # Setup mock to return different results for different queries
        def mock_search(query, limit=10):
            if "10k" in query.lower():
                return [self.search_results[0]]
            elif "100nf" in query.lower():
                return [self.search_results[1]]
            return []

        self.mock_provider.search.side_effect = mock_search

        enricher = InventoryEnricher(
            components=self.components, search_provider=self.mock_provider, limit=1
        )

        enriched_items, fields = enricher.enrich()

        # Should have 2 items (one per component)
        self.assertEqual(len(enriched_items), 2)

        # Check first item (resistor)
        resistor_item = next(item for item in enriched_items if "10k" in item.value)
        self.assertEqual(resistor_item.value, "10k")
        self.assertEqual(resistor_item.manufacturer, "Yageo")
        self.assertEqual(resistor_item.mfgpn, "RC0603FR-0710KL")
        self.assertEqual(resistor_item.distributor_part_number, "603-RC0603FR-0710KL")
        self.assertEqual(resistor_item.priority, 1)  # Best match

        # Check second item (capacitor)
        cap_item = next(item for item in enriched_items if "100nF" in item.value)
        self.assertEqual(cap_item.value, "100nF")
        self.assertEqual(cap_item.manufacturer, "Samsung")
        self.assertEqual(cap_item.mfgpn, "CL10B104KB8NNNC")

        # Verify search was called for each component
        self.assertEqual(self.mock_provider.search.call_count, 2)

    def test_enrich_inventory_multiple_results(self):
        """Test enriching inventory with multiple search results per component."""
        # Return multiple results for same component
        multiple_results = [
            self.search_results[0],  # Priority 1 (best)
            SearchResult(  # Priority 2 (alternative)
                manufacturer="Vishay",
                mpn="CRCW060310K0FKEA",
                description="RES SMD 10K OHM 1% 1/10W 0603",
                datasheet="",
                distributor="Mouser",
                distributor_part_number="71-CRCW060310K0FKEA",
                availability="10000 In Stock",
                price="0.15",
                details_url="",
                raw_data={},
                attributes={"Resistance": "10 kOhms", "Tolerance": "1%"},
                stock_quantity=10000,
                lifecycle_status="Active",
            ),
        ]

        self.mock_provider.search.return_value = multiple_results

        enricher = InventoryEnricher(
            components=[self.components[0]],  # Just resistor
            search_provider=self.mock_provider,
            limit=2,
        )

        enriched_items, fields = enricher.enrich()

        # Should have 2 items (multiple candidates for same component)
        self.assertEqual(len(enriched_items), 2)

        # Check priorities are assigned correctly
        priorities = [item.priority for item in enriched_items]

        # Should have some priority differentiation (exact priorities may vary based on scoring)
        self.assertEqual(len(priorities), 2)
        self.assertTrue(
            all(p > 0 for p in priorities)
        )  # All priorities should be positive

        # Higher stock quantity result should have equal or better priority
        high_stock_item = next(
            item for item in enriched_items if item.mfgpn == "RC0603FR-0710KL"
        )
        low_stock_item = next(
            item for item in enriched_items if item.mfgpn == "CRCW060310K0FKEA"
        )
        self.assertLessEqual(high_stock_item.priority, low_stock_item.priority)

    def test_enrich_inventory_no_search_results(self):
        """Test enriching inventory when no search results found."""
        self.mock_provider.search.return_value = []

        enricher = InventoryEnricher(
            components=self.components, search_provider=self.mock_provider, limit=1
        )

        enriched_items, fields = enricher.enrich()

        # Should still have items but without supplier data
        self.assertEqual(len(enriched_items), 2)

        for item in enriched_items:
            self.assertEqual(item.manufacturer, "")
            self.assertEqual(item.mfgpn, "")
            self.assertEqual(item.distributor_part_number, "")
            # Should have basic project data
            self.assertIn(item.value, ["10k", "100nF"])

    def test_build_search_query(self):
        """Test search query construction from component data."""
        enricher = InventoryEnricher(
            components=self.components, search_provider=self.mock_provider
        )

        # Test resistor query
        resistor_query = enricher._build_search_query(self.components[0])
        self.assertIn("10k", resistor_query.lower())
        self.assertIn("resistor", resistor_query.lower())
        self.assertIn("0603", resistor_query.lower())

        # Test capacitor query
        cap_query = enricher._build_search_query(self.components[1])
        self.assertIn("100nf", cap_query.lower())
        self.assertIn("capacitor", cap_query.lower())
        self.assertIn("0603", cap_query.lower())

    @patch("jbom.processors.inventory_enricher.SearchResultScorer")
    def test_score_and_rank_results(self, mock_scorer_class):
        """Test scoring and ranking of search results."""
        mock_scorer = Mock()
        mock_scorer_class.return_value = mock_scorer

        # Mock scoring to return different priorities based on stock quantity
        def mock_calculate_priority(comp, result):
            # Return different priorities based on stock quantity to ensure differentiation
            if result.stock_quantity >= 50000:
                return 1
            else:
                return 2

        mock_scorer.calculate_priority.side_effect = mock_calculate_priority

        enricher = InventoryEnricher(
            components=[self.components[0]], search_provider=self.mock_provider
        )

        ranked_results = enricher._score_and_rank_results(
            self.components[0], self.search_results
        )

        # Should have called scorer for each result
        self.assertEqual(mock_scorer.calculate_priority.call_count, 2)

        # Results should be ranked by priority
        self.assertEqual(len(ranked_results), 2)
        priorities = [
            result[1] for result in ranked_results
        ]  # (SearchResult, priority) tuples
        self.assertEqual(priorities, [1, 2])

    def test_create_inventory_item_from_component_and_search(self):
        """Test creating inventory item from component + search result."""
        enricher = InventoryEnricher(
            components=self.components, search_provider=self.mock_provider
        )

        item = enricher._create_inventory_item(
            self.components[0], self.search_results[0], priority=1
        )

        # Should combine component data with search result
        self.assertEqual(item.value, "10k")  # From component
        self.assertEqual(item.manufacturer, "Yageo")  # From search result
        self.assertEqual(item.mfgpn, "RC0603FR-0710KL")  # From search result
        self.assertEqual(item.priority, 1)  # From priority calculation
        self.assertEqual(item.source, "Search")  # Should indicate search source

        # Should preserve component properties
        self.assertEqual(item.tolerance, "1%")
        self.assertEqual(item.wattage, "0.1W")

    def test_create_inventory_item_component_only(self):
        """Test creating inventory item from component only (no search results)."""
        enricher = InventoryEnricher(
            components=self.components, search_provider=self.mock_provider
        )

        item = enricher._create_inventory_item(
            self.components[0],
            search_result=None,
            priority=99,  # Default priority when no search result
        )

        # Should have component data but no supplier data
        self.assertEqual(item.value, "10k")
        self.assertEqual(item.manufacturer, "")
        self.assertEqual(item.mfgpn, "")
        self.assertEqual(item.distributor_part_number, "")
        self.assertEqual(item.priority, 99)
        self.assertEqual(item.source, "Project")


if __name__ == "__main__":
    unittest.main()
