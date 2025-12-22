#!/usr/bin/env python3
"""Unit tests for SearchResultScorer class."""
import unittest
from unittest.mock import Mock, patch

from jbom.common.types import Component
from jbom.search import SearchResult
from jbom.processors.search_result_scorer import SearchResultScorer


class TestSearchResultScorer(unittest.TestCase):
    """Test search result scoring and priority calculation."""

    def setUp(self):
        """Set up test data for scoring tests."""
        self.component = Component(
            reference="R1",
            lib_id="Device:R",
            value="10k",
            footprint="Resistor_SMD:R_0603_1608Metric",
            properties={"Tolerance": "1%", "Power": "0.1W"},
        )

        # High quality result - good stock, active, good price
        self.high_quality_result = SearchResult(
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
            attributes={"Resistance": "10 kOhms", "Tolerance": "1%", "Package": "0603"},
            stock_quantity=50000,
            lifecycle_status="Active",
        )

        # Lower quality result - less stock, higher price
        self.medium_quality_result = SearchResult(
            manufacturer="Vishay",
            mpn="CRCW060310K0FKEA",
            description="RES SMD 10K OHM 1% 1/10W 0603",
            datasheet="",
            distributor="Mouser",
            distributor_part_number="71-CRCW060310K0FKEA",
            availability="500 In Stock",
            price="0.25",
            details_url="",
            raw_data={},
            attributes={"Resistance": "10 kOhms", "Tolerance": "1%", "Package": "0603"},
            stock_quantity=500,
            lifecycle_status="Active",
        )

        # Poor quality result - NRND status, low stock
        self.low_quality_result = SearchResult(
            manufacturer="Generic",
            mpn="GEN-10K-0603",
            description="RES SMD 10K OHM 5% 1/10W 0603",  # Worse tolerance
            datasheet="",
            distributor="Mouser",
            distributor_part_number="999-GEN-10K-0603",
            availability="50 In Stock",
            price="0.05",  # Cheaper but worse specs
            details_url="",
            raw_data={},
            attributes={"Resistance": "10 kOhms", "Tolerance": "5%", "Package": "0603"},
            stock_quantity=50,
            lifecycle_status="NRND",
        )

    def test_scorer_initialization(self):
        """Test SearchResultScorer initialization."""
        scorer = SearchResultScorer()
        self.assertIsInstance(scorer, SearchResultScorer)

    @patch("jbom.processors.search_result_scorer.InventoryMatcher")
    def test_calculate_priority_high_quality(self, mock_matcher_class):
        """Test priority calculation for high-quality search result."""
        # Mock InventoryMatcher to return high match score
        mock_matcher = Mock()
        mock_matcher_class.return_value = mock_matcher
        mock_matcher.find_matches.return_value = [(Mock(), 90, None)]  # High score

        scorer = SearchResultScorer()
        priority = scorer.calculate_priority(self.component, self.high_quality_result)

        # High quality result should get low priority number (best)
        self.assertLessEqual(priority, 2)  # Should be 1 or 2 (very good)

        # Verify matcher was called correctly
        mock_matcher.find_matches.assert_called_once()

    @patch("jbom.processors.search_result_scorer.InventoryMatcher")
    def test_calculate_priority_medium_quality(self, mock_matcher_class):
        """Test priority calculation for medium-quality search result."""
        # Mock InventoryMatcher to return medium match score
        mock_matcher = Mock()
        mock_matcher_class.return_value = mock_matcher
        mock_matcher.find_matches.return_value = [(Mock(), 60, None)]  # Medium score

        scorer = SearchResultScorer()
        priority = scorer.calculate_priority(self.component, self.medium_quality_result)

        # Medium quality should get higher priority number
        self.assertGreater(priority, 1)
        self.assertLessEqual(priority, 10)  # Still reasonable

    @patch("jbom.processors.search_result_scorer.InventoryMatcher")
    def test_calculate_priority_low_quality(self, mock_matcher_class):
        """Test priority calculation for low-quality search result."""
        # Mock InventoryMatcher to return low match score
        mock_matcher = Mock()
        mock_matcher_class.return_value = mock_matcher
        mock_matcher.find_matches.return_value = [(Mock(), 30, None)]  # Low score

        scorer = SearchResultScorer()
        priority = scorer.calculate_priority(self.component, self.low_quality_result)

        # Low quality should get high priority number (worse)
        self.assertGreater(priority, 5)

    @patch("jbom.processors.search_result_scorer.InventoryMatcher")
    def test_priority_ordering_by_stock(self, mock_matcher_class):
        """Test that higher stock quantities result in better priorities."""
        # Mock equal match scores
        mock_matcher = Mock()
        mock_matcher_class.return_value = mock_matcher
        mock_matcher.find_matches.return_value = [(Mock(), 80, None)]

        scorer = SearchResultScorer()

        high_stock_priority = scorer.calculate_priority(
            self.component, self.high_quality_result
        )
        medium_stock_priority = scorer.calculate_priority(
            self.component, self.medium_quality_result
        )

        # Higher stock should get better (lower) priority
        self.assertLess(high_stock_priority, medium_stock_priority)

    @patch("jbom.processors.search_result_scorer.InventoryMatcher")
    def test_priority_ordering_by_lifecycle(self, mock_matcher_class):
        """Test that lifecycle status affects priority calculation."""
        # Mock equal match scores
        mock_matcher = Mock()
        mock_matcher_class.return_value = mock_matcher
        mock_matcher.find_matches.return_value = [(Mock(), 80, None)]

        scorer = SearchResultScorer()

        active_priority = scorer.calculate_priority(
            self.component, self.high_quality_result
        )
        nrnd_priority = scorer.calculate_priority(
            self.component, self.low_quality_result
        )

        # Active parts should get better (lower) priority than NRND
        self.assertLess(active_priority, nrnd_priority)

    def test_calculate_match_score_integration(self):
        """Test integration with actual InventoryMatcher scoring."""
        # This test uses real InventoryMatcher to verify integration
        scorer = SearchResultScorer()

        # Create a mock inventory item from search result
        mock_inventory_item = scorer._search_result_to_inventory_item(
            self.high_quality_result
        )

        # Verify the conversion preserves key data
        self.assertEqual(mock_inventory_item.value, "10k")  # Extracted from attributes
        self.assertEqual(mock_inventory_item.manufacturer, "Yageo")
        self.assertEqual(mock_inventory_item.mfgpn, "RC0603FR-0710KL")
        self.assertEqual(
            mock_inventory_item.package, "0603"
        )  # Extracted from attributes

    def test_stock_quantity_scoring(self):
        """Test stock quantity scoring logic."""
        scorer = SearchResultScorer()

        # High stock should score well
        high_score = scorer._calculate_stock_score(50000)
        medium_score = scorer._calculate_stock_score(500)
        low_score = scorer._calculate_stock_score(50)

        # Scores should decrease with stock quantity
        self.assertGreater(high_score, medium_score)
        self.assertGreater(medium_score, low_score)

        # All scores should be positive
        self.assertGreater(high_score, 0)
        self.assertGreater(medium_score, 0)
        self.assertGreater(low_score, 0)

    def test_lifecycle_status_scoring(self):
        """Test lifecycle status scoring logic."""
        scorer = SearchResultScorer()

        active_score = scorer._calculate_lifecycle_score("Active")
        nrnd_score = scorer._calculate_lifecycle_score("NRND")
        obsolete_score = scorer._calculate_lifecycle_score("Obsolete")

        # Active should score highest
        self.assertGreater(active_score, nrnd_score)
        self.assertGreater(nrnd_score, obsolete_score)
        self.assertGreater(obsolete_score, 0)  # Obsolete should be positive but lowest

    def test_price_scoring(self):
        """Test price competitiveness scoring."""
        scorer = SearchResultScorer()

        # Lower prices should generally score better, but not the only factor
        cheap_score = scorer._calculate_price_score(0.05)
        expensive_score = scorer._calculate_price_score(0.50)

        # Verify scoring makes sense (cheaper is generally better)
        self.assertGreaterEqual(cheap_score, expensive_score)

        # But not necessarily linear - very cheap might indicate quality issues
        # This allows for more sophisticated price scoring logic

    def test_search_result_to_inventory_item_conversion(self):
        """Test conversion from SearchResult to InventoryItem for matching."""
        scorer = SearchResultScorer()
        inventory_item = scorer._search_result_to_inventory_item(
            self.high_quality_result
        )

        # Verify all key fields are mapped correctly
        self.assertEqual(inventory_item.manufacturer, "Yageo")
        self.assertEqual(inventory_item.mfgpn, "RC0603FR-0710KL")
        self.assertEqual(inventory_item.distributor, "Mouser")
        self.assertEqual(inventory_item.distributor_part_number, "603-RC0603FR-0710KL")

        # Verify attributes are extracted
        self.assertEqual(inventory_item.tolerance, "1%")
        self.assertEqual(inventory_item.package, "0603")

        # Verify computed fields
        self.assertEqual(inventory_item.source, "Search")
        self.assertGreater(inventory_item.priority, 0)  # Should have computed priority

    def test_composite_priority_calculation(self):
        """Test that priority calculation combines all factors correctly."""
        scorer = SearchResultScorer()

        # Test with results that have different strengths/weaknesses
        results = [
            self.high_quality_result,
            self.medium_quality_result,
            self.low_quality_result,
        ]

        # Calculate priorities for all results
        priorities = []
        for result in results:
            priority = scorer.calculate_priority(self.component, result)
            priorities.append(priority)

        # Verify priorities are ordered sensibly
        self.assertGreaterEqual(
            len(set(priorities)), 2
        )  # At least some differentiation

        # High quality should have best (lowest) priority
        high_idx = results.index(self.high_quality_result)
        self.assertEqual(priorities[high_idx], min(priorities))


if __name__ == "__main__":
    unittest.main()
