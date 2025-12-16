#!/usr/bin/env python3
"""Tests for KiCad plugin integration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import unittest
import tempfile
import subprocess


class TestKiCadPlugin(unittest.TestCase):
    """Test KiCad plugin wrapper functionality"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)
        self.plugin_path = Path(__file__).parent.parent / "kicad_jbom_plugin.py"

        # Create minimal inventory
        self.inv = self.tmpdir / "inv.csv"
        self.inv.write_text(
            "IPN,Category,Package,Value,LCSC,Priority\n"
            "R-0603-330,RES,0603,330R,C123,1\n"
            "C-0603-100n,CAP,0603,100nF,C456,1\n",
            encoding="utf-8",
        )

        # Create minimal schematic
        self.schematic = self.tmpdir / "test.kicad_sch"
        self.schematic.write_text(
            "(kicad_sch (version 20211123) "
            "(lib_symbols "
            '(symbol "Device:R" (property "Reference" "R")) '
            '(symbol "Device:C" (property "Reference" "C"))) '
            '(symbol (lib_id "Device:R") (at 10 10 0) '
            '(property "Reference" "R1" (id 0)) '
            '(property "Value" "330R" (id 1)) '
            '(property "Footprint" "Resistor_SMD:R_0603_1608Metric" (id 2))) '
            '(symbol (lib_id "Device:C") (at 20 20 0) '
            '(property "Reference" "C1" (id 0)) '
            '(property "Value" "100nF" (id 1)) '
            '(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (id 2))))',
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_plugin_executes_successfully(self):
        """Plugin should execute and create BOM file"""
        output = self.tmpdir / "bom.csv"

        result = subprocess.run(
            [
                sys.executable,
                str(self.plugin_path),
                str(self.schematic),
                "-i",
                str(self.inv),
                "-o",
                str(output),
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, f"Plugin failed: {result.stderr}")
        self.assertTrue(output.exists(), "BOM file was not created")

        # Check content
        content = output.read_text(encoding="utf-8")
        self.assertIn("Reference", content)
        self.assertIn("R1", content)
        self.assertIn("C1", content)

    def test_plugin_with_verbose_flag(self):
        """Plugin should support -v flag"""
        output = self.tmpdir / "bom_verbose.csv"

        result = subprocess.run(
            [
                sys.executable,
                str(self.plugin_path),
                str(self.schematic),
                "-i",
                str(self.inv),
                "-o",
                str(output),
                "-v",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertTrue(output.exists())

        # Verbose should add match quality columns
        content = output.read_text(encoding="utf-8")
        # Check for verbose fields (normalized to title case)
        self.assertTrue(
            any(field in content for field in ["Match Quality", "Match_Quality"]),
            "Verbose mode should add match quality info",
        )

    def test_plugin_with_custom_fields(self):
        """Plugin should support custom field selection"""
        output = self.tmpdir / "bom_custom.csv"

        result = subprocess.run(
            [
                sys.executable,
                str(self.plugin_path),
                str(self.schematic),
                "-i",
                str(self.inv),
                "-o",
                str(output),
                "-f",
                "Reference,Value,LCSC",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertTrue(output.exists())

        content = output.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        header = lines[0]

        # Should have requested fields
        self.assertIn("Reference", header)
        self.assertIn("Value", header)
        self.assertIn("LCSC", header)

    def test_plugin_with_jlc_preset(self):
        """Plugin should support field presets like +jlc"""
        output = self.tmpdir / "bom_jlc.csv"

        result = subprocess.run(
            [
                sys.executable,
                str(self.plugin_path),
                str(self.schematic),
                "-i",
                str(self.inv),
                "-o",
                str(output),
                "-f",
                "+jlc",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertTrue(output.exists())

        content = output.read_text(encoding="utf-8")
        # JLC format should have specific fields
        self.assertIn("Reference", content)
        self.assertIn("Value", content)
        self.assertIn("LCSC", content)

    def test_plugin_with_missing_inventory(self):
        """Plugin should fail gracefully with missing inventory"""
        output = self.tmpdir / "bom.csv"

        result = subprocess.run(
            [
                sys.executable,
                str(self.plugin_path),
                str(self.schematic),
                "-i",
                str(self.tmpdir / "nonexistent.csv"),
                "-o",
                str(output),
            ],
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0, "Should fail with missing inventory")
        self.assertIn("not found", result.stderr.lower())

    def test_plugin_creates_output_directory(self):
        """Plugin should create output directory if needed"""
        output = self.tmpdir / "subdir" / "bom.csv"

        result = subprocess.run(
            [
                sys.executable,
                str(self.plugin_path),
                str(self.schematic),
                "-i",
                str(self.inv),
                "-o",
                str(output),
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertTrue(output.exists())
        self.assertTrue(output.parent.exists())


if __name__ == "__main__":
    unittest.main()
