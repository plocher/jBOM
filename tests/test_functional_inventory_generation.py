#!/usr/bin/env python3
"""Functional tests for inventory generation and inventory-less BOM workflows."""
import sys
from pathlib import Path

# Ensure tests directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_functional_base import FunctionalTestBase


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


if __name__ == "__main__":
    import unittest

    unittest.main()
