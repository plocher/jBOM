"""
Functional tests for Search Logic.
Covering: Smart Filtering, Stock Buffers, and Ranking.
"""
from jbom.search import SearchResult
from jbom.search.filter import SearchFilter
from .test_functional_base import FunctionalTestBase


class TestFunctionalSearch(FunctionalTestBase):
    def setUp(self):
        super().setUp()
        # Mock results
        self.r1 = SearchResult(
            manufacturer="Yageo",
            mpn="RC0603-10K-1%",
            description="10k 1%",
            datasheet="",
            distributor="Mouser",
            distributor_part_number="1",
            availability="1000 In Stock",
            price="0.10",
            details_url="",
            raw_data={},
            attributes={"Resistance": "10 kOhms", "Tolerance": "1%"},
            stock_quantity=1000,
            lifecycle_status="Active",
        )
        self.r2 = SearchResult(
            manufacturer="Yageo",
            mpn="RC0603-10K-5%",
            description="10k 5%",
            datasheet="",
            distributor="Mouser",
            distributor_part_number="2",
            availability="5000 In Stock",
            price="0.05",
            details_url="",
            raw_data={},
            attributes={"Resistance": "10 kOhms", "Tolerance": "5%"},
            stock_quantity=5000,
            lifecycle_status="Active",
        )
        self.r3 = SearchResult(
            manufacturer="Vishay",
            mpn="MCT0603-10K-0.1%",
            description="10k 0.1%",
            datasheet="",
            distributor="Mouser",
            distributor_part_number="3",
            availability="100 In Stock",
            price="1.00",
            details_url="",
            raw_data={},
            attributes={"Resistance": "10 kOhms", "Tolerance": "0.1%"},
            stock_quantity=100,
            lifecycle_status="Active",
        )
        self.results = [self.r1, self.r2, self.r3]

    def test_parametric_filtering_tolerance(self):
        """Test: Search for '10k 1%' filters out 5% tolerance."""
        # Query specifies 1%
        filtered = SearchFilter.filter_by_query(self.results, "10k 1%")

        # Should keep 1% (exact) and maybe tighter?
        # Current logic is exact match for tolerance if specified.
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].mpn, "RC0603-10K-1%")

    def test_parametric_filtering_resistance(self):
        """Test: Search for '10k' keeps all 10k resistors."""
        filtered = SearchFilter.filter_by_query(self.results, "10k")
        self.assertEqual(len(filtered), 3)

    def test_stock_quantity_filtering(self):
        """Test: 'In Stock > Needed' logic (future requirement)."""
        # This functionality doesn't exist yet in SearchFilter, so this test serves as the spec.
        # We want to request 2000 units.
        needed = 2000

        # Filter should exclude r1 (1000) and r3 (100). Only r2 (5000) remains.
        # NOTE: This API doesn't exist yet on SearchFilter.
        filtered = SearchFilter.filter_by_stock(self.results, min_quantity=needed)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].mpn, "RC0603-10K-5%")

    def test_ranking_logic(self):
        """Test: Results sorted by Availability desc, Price asc."""
        # Unsorted list
        unsorted = [self.r3, self.r1, self.r2]

        # Sort using our provider logic (or moved to a common Sorter class)
        # For now, let's assume we implement a Sorter.rank(results) method.
        from jbom.search.filter import SearchSorter

        sorted_results = SearchSorter.rank(unsorted)

        # Expect: r2 (5000 qty), r1 (1000 qty), r3 (100 qty)
        self.assertEqual(sorted_results[0].mpn, "RC0603-10K-5%")
        self.assertEqual(sorted_results[1].mpn, "RC0603-10K-1%")
        self.assertEqual(sorted_results[2].mpn, "MCT0603-10K-0.1%")
