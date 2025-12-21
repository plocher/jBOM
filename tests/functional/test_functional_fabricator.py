#!/usr/bin/env python3
"""Functional tests for fabricator support."""
import sys
from pathlib import Path

# Ensure tests directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from .test_functional_base import FunctionalTestBase


class TestFabricatorSupport(FunctionalTestBase):
    """Test fabricator support (JLC, Seeed, etc.)."""

    def setUp(self):
        super().setUp()
        # Create inventory with fabricator specific fields
        self.inv_path = self.output_dir / "inv_fab.csv"
        self.inv_path.write_text(
            "IPN,Category,Value,Package,LCSC,Seeed SKU,MFGPN,Description,Priority\n"
            "R1,RES,10k,0603,C12345,10101010,0603WAF1002T5E,Resistor,1\n"
            "C1,CAP,100nF,0603,C67890,20202020,CC0603KRX7R9BB104,Capacitor,1\n"
        )

        # Create minimal project with matching components
        self.proj_dir = self.output_dir / "project"
        self.proj_dir.mkdir()
        sch_file = self.proj_dir / "main.kicad_sch"
        sch_file.write_text(
            """(kicad_sch (version 20231120) (generator "eeschema")
  (lib_symbols
    (symbol "Device:R" (in_bom yes) (on_board yes)
      (property "Reference" "R1" (id 0) (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "10k" (id 1) (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "R_0603_1608Metric" (id 2) (at 0 0 0) (effects (font (size 1.27 1.27) hide)))
    )
    (symbol "Device:C" (in_bom yes) (on_board yes)
      (property "Reference" "C1" (id 0) (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "100nF" (id 1) (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "C_0603_1608Metric" (id 2) (at 0 0 0) (effects (font (size 1.27 1.27) hide)))
    )
  )
  (symbol (lib_id "Device:R") (at 100 100 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced)
    (uuid "00000000-0000-0000-0000-000000000001")
    (property "Reference" "R1" (id 0) (at 100 90 0) (effects (font (size 1.27 1.27))))
    (property "Value" "10k" (id 1) (at 100 92 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "R_0603_1608Metric" (id 2) (at 100 100 0) (effects (font (size 1.27 1.27) hide)))
  )
  (symbol (lib_id "Device:C") (at 120 100 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced)
    (uuid "00000000-0000-0000-0000-000000000002")
    (property "Reference" "C1" (id 0) (at 120 90 0) (effects (font (size 1.27 1.27))))
    (property "Value" "100nF" (id 1) (at 120 92 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "C_0603_1608Metric" (id 2) (at 120 100 0) (effects (font (size 1.27 1.27) hide)))
  )
)"""
        )

    def test_jlc_fabricator_flag(self):
        """Test --fabricator jlc populates fabricator_part_number correctly."""
        output = self.output_dir / "bom_jlc.csv"

        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.proj_dir),
                "-i",
                str(self.inv_path),
                "-o",
                str(output),
                "--fabricator",
                "jlc",
                "-f",
                "Reference,Value,Fabricator,Fabricator_Part_Number",
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        header = rows[0]
        # Fabricator column not in JLC default
        self.assertIn("LCSC", header)  # JLC header name

        # Check rows
        for row in rows[1:]:
            fab_pn = row[header.index("LCSC")]
            ref = row[header.index("Designator")]

            if "R1" in ref:
                self.assertEqual(fab_pn, "C12345", f"R1 mismatch. Stderr:\n{stderr}")
            elif "C1" in ref:
                self.assertEqual(fab_pn, "C67890", f"C1 mismatch. Stderr:\n{stderr}")

    def test_seeed_fabricator_flag(self):
        """Test --fabricator seeed populates fabricator_part_number correctly."""
        output = self.output_dir / "bom_seeed.csv"

        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.proj_dir),
                "-i",
                str(self.inv_path),
                "-o",
                str(output),
                "--fabricator",
                "seeed",
                "-f",
                "Reference,Value,Fabricator,Fabricator_Part_Number",
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        header = rows[0]
        self.assertIn("Seeed Part Number", header)  # Seeed header name

        # Check rows
        for row in rows[1:]:
            fab_pn = row[header.index("Seeed Part Number")]
            ref = row[header.index("Designator")]

            if "R1" in ref:
                self.assertEqual(fab_pn, "10101010")  # Seeed SKU
            elif "C1" in ref:
                self.assertEqual(fab_pn, "20202020")  # Seeed SKU

    def test_implicit_jlc_flag(self):
        """Test --jlc implies --fabricator jlc."""
        output = self.output_dir / "bom_implicit_jlc.csv"

        # We use custom fields to verify the fabricator info is available
        # even if not in the default JLC preset
        rc, stdout, stderr = self.run_jbom(
            [
                "bom",
                str(self.proj_dir),
                "-i",
                str(self.inv_path),
                "-o",
                str(output),
                "--jlc",
                "-f",
                "+jlc,Fabricator,Fabricator_Part_Number",
            ]
        )

        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        header = rows[0]
        self.assertIn("LCSC", header)  # JLC header name

        # Check rows
        for row in rows[1:]:
            fab_pn = row[header.index("LCSC")]
            # Check fabricator indirectly
            self.assertTrue(fab_pn.startswith("C"))


if __name__ == "__main__":
    import unittest

    unittest.main()
