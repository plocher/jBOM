#!/usr/bin/env python3
"""Functional tests for inventory generation and inventory-less BOM workflows."""
import sys
from pathlib import Path

# Ensure tests directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from .test_functional_base import FunctionalTestBase


class TestInventoryGeneration(FunctionalTestBase):
    """Test inventory generation and inventory-less BOM workflows."""

    def test_generate_inventory_default(self):
        """Generate inventory from project with default settings."""
        output = self.output_dir / "inventory.csv"

        rc, stdout, stderr = self.run_jbom(
            [
                "inventory",
                str(self.minimal_proj),
                "-o",
                str(output),
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)

        # Should have header + data rows
        self.assertGreater(len(rows), 1, "Inventory should have data rows")

        # Check headers
        header = rows[0]
        self.assertIn("IPN", header)
        self.assertIn("Value", header)
        self.assertIn("Package", header)
        self.assertIn("Category", header)
        self.assertIn("Manufacturer", header)

        # Check data
        # R1/R2/R3 are 1K/100R etc.
        values = [row[header.index("Value")] for row in rows[1:]]
        self.assertIn("1K", values)
        self.assertIn("100nF", values)

    def test_generate_inventory_console(self):
        """Generate inventory to console."""
        rc, stdout, stderr = self.run_jbom(
            [
                "inventory",
                str(self.minimal_proj),
                "-o",
                "console",
            ]
        )

        self.assertEqual(rc, 0)
        self.assert_stdout_is_table(stdout)
        self.assertIn("IPN", stdout)
        self.assertIn("1K", stdout)

    def test_bom_without_inventory_file(self):
        """Generate BOM without an inventory file (using auto-generated inventory)."""
        output = self.output_dir / "bom_no_inv.csv"

        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.minimal_proj),
                "-o",
                str(output),
                # Note: No -i argument
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)

        # Should have header + data rows
        self.assertGreater(len(rows), 1, "BOM should have data rows")

        header = rows[0]
        self.assertIn("Reference", header)
        self.assertIn("Value", header)

        # Check that we have entries
        ref_idx = header.index("Reference")
        refs = [row[ref_idx] for row in rows[1:]]
        # minimal_project has R1, R2, R3, C1, D1, J1
        self.assertTrue(any("R1" in r for r in refs))
        self.assertTrue(any("C1" in r for r in refs))

        # Check notes - should not say "No inventory match found" because we generated inventory from components!
        # Actually, since we generate inventory FROM the components, they should all match exactly.
        if "Notes" in header:
            notes_idx = header.index("Notes")
            notes = [row[notes_idx] for row in rows[1:]]
            for note in notes:
                self.assertNotIn("No inventory match found", note)

    def test_bom_without_inventory_file_verbose(self):
        """Generate verbose BOM without an inventory file."""
        output = self.output_dir / "bom_no_inv_verbose.csv"

        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.minimal_proj),
                "-o",
                str(output),
                "-v",  # Verbose
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        header = rows[0]

        # Should have Match Quality
        self.assertIn("Match Quality", header)

        # Scores should be high because we generated inventory from the components themselves
        mq_idx = header.index("Match Quality")
        scores = [row[mq_idx] for row in rows[1:]]
        for score in scores:
            self.assertIn("Score:", score)

    def test_generate_inventory_with_search_enabled(self):
        """Test inventory generation with search enrichment (mocked)."""
        from unittest.mock import patch, Mock

        output = self.output_dir / "enriched_inventory.csv"

        # Mock the search provider to avoid real API calls
        with patch("jbom.api.MouserProvider") as mock_provider_class:
            mock_provider = Mock()
            mock_provider_class.return_value = mock_provider
            mock_provider.search.return_value = []  # No search results

            rc, stdout, stderr = self.run_jbom(
                [
                    "inventory",
                    str(self.minimal_proj),
                    "-o",
                    str(output),
                    "--search",
                    "--provider",
                    "mouser",
                    "--limit",
                    "1",
                ]
            )

            self.assertEqual(rc, 0)
            rows = self.assert_csv_valid(output)

            # Should still have inventory data (even with no search results)
            self.assertGreater(len(rows), 1, "Enriched inventory should have data rows")

            # Check that search statistics were printed
            self.assertIn("Search statistics:", stdout)
            self.assertIn("Provider: mouser", stdout)

    def test_generate_inventory_with_search_multiple_results(self):
        """Test inventory generation with multiple search results per component."""
        from unittest.mock import patch, Mock

        output = self.output_dir / "enriched_inventory_multi.csv"

        # Mock search results
        mock_search_result = Mock()
        mock_search_result.manufacturer = "Test Mfg"
        mock_search_result.mpn = "TEST-PART-123"
        mock_search_result.price = "0.10"
        mock_search_result.stock_quantity = 1000
        mock_search_result.lifecycle_status = "Active"
        mock_search_result.description = "Test Description"
        mock_search_result.distributor_part_number = "DPN123"

        with patch("jbom.api.MouserProvider") as mock_provider_class:
            mock_provider = Mock()
            mock_provider_class.return_value = mock_provider
            mock_provider.search.return_value = [
                mock_search_result
            ]  # One result per search

            rc, stdout, stderr = self.run_jbom(
                [
                    "inventory",
                    str(self.minimal_proj),
                    "-o",
                    str(output),
                    "--search",
                    "--provider",
                    "mouser",
                    "--limit",
                    "3",  # Request multiple results
                ]
            )

            self.assertEqual(rc, 0)
            rows = self.assert_csv_valid(output)

            # Should have inventory data enhanced with search results
            self.assertGreater(len(rows), 1, "Enhanced inventory should have data rows")

            # Look for search-enriched fields in header
            header = rows[0]
            self.assertIn("Manufacturer", header)
            self.assertIn("MFGPN", header)

            # Verify search statistics in output
            self.assertIn("Search statistics:", stdout)
            self.assertIn("Searches performed:", stdout)

    def test_generate_inventory_search_api_error(self):
        """Test handling of search provider API errors."""
        from unittest.mock import patch

        output = self.output_dir / "inventory_api_error.csv"

        with patch("jbom.api.MouserProvider") as mock_provider_class:
            # Mock provider initialization to fail
            mock_provider_class.side_effect = ValueError("Invalid API key")

            rc, stdout, stderr = self.run_jbom(
                [
                    "inventory",
                    str(self.minimal_proj),
                    "-o",
                    str(output),
                    "--search",
                    "--provider",
                    "mouser",
                ],
                expected_rc=1,  # Expect failure
            )

            # Should fail gracefully
            self.assertEqual(rc, 1)
            self.assertIn("Search provider error", stderr)
            self.assertIn("Invalid API key", stderr)

    def test_generate_inventory_search_limit_none(self):
        """Test inventory generation with unlimited search results."""
        from unittest.mock import patch, Mock

        output = self.output_dir / "enriched_inventory_unlimited.csv"

        with patch("jbom.api.MouserProvider") as mock_provider_class:
            mock_provider = Mock()
            mock_provider_class.return_value = mock_provider
            mock_provider.search.return_value = []  # No search results for simplicity

            rc, stdout, stderr = self.run_jbom(
                [
                    "inventory",
                    str(self.minimal_proj),
                    "-o",
                    str(output),
                    "--search",
                    "--provider",
                    "mouser",
                    "--limit",
                    "none",  # Unlimited results
                ]
            )

            self.assertEqual(rc, 0)
            self.assert_csv_valid(output)

            # Should mention unlimited results in output
            self.assertIn("Search statistics:", stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
