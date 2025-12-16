#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import unittest
import tempfile
import csv

from jbom.cli.main import main as cli_main


class TestCLIBehavior(unittest.TestCase):
    """Test CLI behavior without mocking implementation details"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

        # Create minimal inventory
        self.inv = self.tmpdir / "inv.csv"
        self.inv.write_text(
            "IPN,Category,Package,Value,LCSC,Priority\n"
            "R-0603-330,RES,0603,330R,C123,1\n",
            encoding="utf-8",
        )

        # Create minimal schematic
        self.schematic = self.tmpdir / "test.kicad_sch"
        self.schematic.write_text(
            "(kicad_sch (version 20211123) "
            '(lib_symbols (symbol "Device:R" (property "Reference" "R"))) '
            '(symbol (lib_id "Device:R") (at 10 10 0) '
            '(property "Reference" "R1" (id 0)) '
            '(property "Value" "330R" (id 1)) '
            '(property "Footprint" "Resistor_SMD:R_0603_1608Metric" (id 2))))',
            encoding="utf-8",
        )

        # Create minimal PCB
        self.pcb = self.tmpdir / "test.kicad_pcb"
        self.pcb.write_text(
            '(kicad_pcb (version 20211014) (host pcbnew "6") '
            '(footprint "Resistor_SMD:R_0603_1608Metric" (layer "F.Cu") (at 10 20 0) '
            '(fp_text reference "R1" (at 0 0 0) (layer "F.SilkS"))))',
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_bom_with_jlc_flag_produces_jlc_fields(self):
        """--jlc flag should produce JLC-specific field layout"""
        output = self.tmpdir / "bom_jlc.csv"
        rc = cli_main(
            [
                "bom",
                str(self.schematic),
                "-i",
                str(self.inv),
                "-o",
                str(output),
                "--jlc",
            ]
        )

        self.assertEqual(rc, 0)
        self.assertTrue(output.exists())

        # Check that JLC fields are present
        with open(output, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            # JLC format should have these specific fields
            self.assertIn("Reference", headers)
            self.assertIn("Quantity", headers)
            self.assertIn("Value", headers)
            self.assertIn("LCSC", headers)
            # Package comes from inventory (I:Package)
            self.assertTrue(any("Package" in h for h in headers))

    def test_bom_with_custom_fields(self):
        """Custom field list should be respected"""
        output = self.tmpdir / "bom_custom.csv"
        rc = cli_main(
            [
                "bom",
                str(self.schematic),
                "-i",
                str(self.inv),
                "-o",
                str(output),
                "-f",
                "Reference,Value,LCSC",
            ]
        )

        self.assertEqual(rc, 0)
        with open(output, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            self.assertIn("Reference", headers)
            self.assertIn("Value", headers)
            self.assertIn("LCSC", headers)
            # Should have exactly these fields (or very close)
            self.assertLessEqual(len(headers), 5)  # Allow for minor additions

    def test_pos_with_jlc_flag_produces_jlc_fields(self):
        """--jlc flag should produce JLC placement format"""
        output = self.tmpdir / "pos_jlc.csv"
        rc = cli_main(
            ["pos", str(self.pcb), "-o", str(output), "--jlc", "--loader", "sexp"]
        )

        self.assertEqual(rc, 0)
        self.assertTrue(output.exists())

        with open(output, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            # JLC POS format
            self.assertIn("Reference", headers)
            self.assertIn("Side", headers)
            self.assertIn("X", headers)
            self.assertIn("Y", headers)
            self.assertIn("Rotation", headers)

    def test_pos_writes_csv_file(self):
        """POS command should create valid CSV output"""
        output = self.tmpdir / "pos.csv"
        rc = cli_main(["pos", str(self.pcb), "-o", str(output), "--loader", "sexp"])

        self.assertEqual(rc, 0)
        self.assertTrue(output.exists())

        content = output.read_text(encoding="utf-8")
        self.assertIn("Reference", content)
        self.assertIn("R1", content)

    def test_cli_help_works(self):
        """CLI help should not crash"""
        with self.assertRaises(SystemExit) as cm:
            cli_main(["--help"])
        # argparse exits with 0 for help
        self.assertEqual(cm.exception.code, 0)

    def test_cli_version_works(self):
        """CLI version flag should work"""
        with self.assertRaises(SystemExit) as cm:
            cli_main(["--version"])
        self.assertEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
