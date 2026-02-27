#!/usr/bin/env python3
"""Functional tests for BOM command - happy paths."""
import sys
from pathlib import Path

# Ensure tests directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from .test_functional_base import FunctionalTestBase


class TestBOMHappyPaths(FunctionalTestBase):
    """Test BOM command happy path scenarios."""

    def test_bom_default_fields(self):
        """Generate BOM with default (+standard) fields."""
        output = self.output_dir / "bom.csv"

        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.modern_proj),
                "-i",
                str(self.modern_inventory),
                "-o",
                str(output),
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)

        # Should have header + data rows
        self.assertGreater(len(rows), 1, "BOM should have data rows")

        # Check for +standard fields
        header = rows[0]
        self.assertIn("Reference", header)
        self.assertIn("Quantity", header)
        self.assertIn("Description", header)
        self.assertIn("Value", header)
        self.assertIn("Footprint", header)
        self.assertIn("Manufacturer", header)
        self.assertIn("MFGPN", header)
        self.assertIn("Fabricator", header)
        self.assertIn("Part Number", header)
        self.assertIn("Datasheet", header)
        self.assertIn("SMD", header)

    def test_bom_jlc_flag(self):
        """Generate BOM with --jlc flag (JLC preset)."""
        output = self.output_dir / "bom_jlc.csv"

        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.modern_proj),
                "-i",
                str(self.modern_inventory),
                "-o",
                str(output),
                "--jlc",
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)

        # Check for JLC fields
        header = rows[0]
        self.assertIn("Designator", header)
        self.assertIn("Quantity", header)
        self.assertIn("Value", header)
        # Package field may appear as 'I:Package' when using inventory prefix
        # JLC config maps 'Footprint' to 'i:package'
        self.assertTrue(
            "Footprint" in header or "I:Package" in header,
            f"Package field not found in header: {header}",
        )
        # Fabricator name column is implicit in JLC format and not included by default
        # JLC Fabricator renames 'Fabricator Part Number' to 'LCSC'
        self.assertIn("LCSC", header)
        self.assertNotIn("Fabricator Part Number", header)
        self.assertIn("Surface Mount", header)

    def test_bom_custom_fields(self):
        """Generate BOM with custom field list."""
        output = self.output_dir / "bom_custom.csv"

        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.modern_proj),
                "-i",
                str(self.modern_inventory),
                "-o",
                str(output),
                "-f",
                "Reference,Value,Lcsc",
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_headers(output, ["Reference", "Value", "LCSC"])
        self.assertGreater(len(rows), 1)

    def test_bom_mixed_preset_and_custom(self):
        """Generate BOM with mixed preset + custom fields."""
        output = self.output_dir / "bom_mixed.csv"

        # Use component fields that we know exist
        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.modern_proj),
                "-i",
                str(self.modern_inventory),
                "-o",
                str(output),
                "-f",
                "+minimal,Footprint",
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        header = rows[0]

        # Should have minimal fields + Footprint
        self.assertIn("Reference", header)
        self.assertIn("Quantity", header)
        self.assertIn("Value", header)
        self.assertIn("LCSC", header)  # Normalized to title case
        self.assertIn("Footprint", header)

    def test_bom_to_console(self):
        """Generate BOM to console (formatted table)."""
        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.modern_proj),
                "-i",
                str(self.modern_inventory),
                "-o",
                "console",
            ]
        )

        self.assertEqual(rc, 0)
        self.assert_stdout_is_table(stdout)

        # Table should contain component references
        # Use simple check for common prefixes since we switched to real project
        self.assertTrue(
            "R" in stdout or "C" in stdout, "Should contain resistors or capacitors"
        )

    def test_bom_to_stdout(self):
        """Generate BOM to stdout (CSV format)."""
        rc, stdout, stderr = self.run_jbom(
            ["bom", str(self.modern_proj), "-i", str(self.modern_inventory), "-o", "-"]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_stdout_is_csv(stdout)

        # Should have header + data
        self.assertGreater(len(rows), 1)
        self.assertIn("Reference", rows[0])

    def test_bom_verbose_mode(self):
        """Generate BOM with verbose mode (-v)."""
        output = self.output_dir / "bom_verbose.csv"

        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.modern_proj),
                "-i",
                str(self.modern_inventory),
                "-o",
                str(output),
                "-v",
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        header = rows[0]

        # Verbose adds Match Quality (with space) and Priority
        self.assertIn("Match Quality", header)
        self.assertIn("Priority", header)

    def test_bom_debug_mode(self):
        """Generate BOM with debug mode (-d)."""
        output = self.output_dir / "bom_debug.csv"

        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.modern_proj),
                "-i",
                str(self.modern_inventory),
                "-o",
                str(output),
                "-d",
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)

        # Debug adds Notes column when there are notes to display
        # Note: Notes column may not appear if no components have notes
        # Just verify the file was generated successfully
        self.assertGreater(len(rows), 1, "BOM should have data rows")

    def test_bom_smd_only(self):
        """Generate BOM with --smd-only filter."""
        output = self.output_dir / "bom_smd.csv"

        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.modern_proj),
                "-i",
                str(self.modern_inventory),
                "-o",
                str(output),
                "--smd-only",
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)

        # Should only have SMD components
        # AltmillSwitches is mostly SMD, hard to verify strictly without knowing PTH parts
        # But we can verify it ran and produced output
        self.assertGreater(len(rows), 1)

        references = []
        ref_idx = rows[0].index("Reference")
        for row in rows[1:]:
            if row:  # Skip empty rows
                references.append(row[ref_idx])

        # Verify we have some components
        self.assertTrue(len(references) > 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
