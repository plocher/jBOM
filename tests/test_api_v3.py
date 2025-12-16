#!/usr/bin/env python3
"""Tests for jBOM v3.0 unified API

Tests the new generate_bom() and generate_pos() functions with input=/output= parameters.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import unittest
import tempfile

from jbom import generate_bom, generate_pos, BOMOptions, POSOptions


class TestGenerateBOMAPI(unittest.TestCase):
    """Test new v3.0 generate_bom() API"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

        # Create minimal inventory file
        self.inventory = self.tmpdir / "inventory.csv"
        self.inventory.write_text(
            "IPN,Category,Package,Value,LCSC,Priority\n"
            "R-0603-330,RES,0603,330R,C123,1\n"
            "C-0603-100n,CAP,0603,100nF,C456,1\n",
            encoding="utf-8",
        )

        # Create minimal schematic
        self.schematic = self.tmpdir / "test.kicad_sch"
        schematic_content = """(kicad_sch (version 20211123) (generator eeschema)
  (lib_symbols
    (symbol "Device:R" (property "Reference" "R"))
    (symbol "Device:C" (property "Reference" "C")))
  (symbol (lib_id "Device:R") (at 10 10 0)
    (property "Reference" "R1" (id 0))
    (property "Value" "330R" (id 1))
    (property "Footprint" "Resistor_SMD:R_0603_1608Metric" (id 2)))
  (symbol (lib_id "Device:C") (at 20 20 0)
    (property "Reference" "C1" (id 0))
    (property "Value" "100nF" (id 1))
    (property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (id 2))))
"""
        self.schematic.write_text(schematic_content, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_generate_bom_with_file_input(self):
        """Test generate_bom with specific schematic file"""
        result = generate_bom(input=self.schematic, inventory=self.inventory)

        self.assertIn("components", result)
        self.assertIn("bom_entries", result)
        self.assertIn("inventory_count", result)
        self.assertEqual(result["inventory_count"], 2)
        # Parser includes lib_symbol definitions, so expect 4 (2 libs + 2 instances)
        self.assertEqual(len(result["components"]), 4)

    def test_generate_bom_with_directory_input(self):
        """Test generate_bom with directory (auto-discovery)"""
        result = generate_bom(input=self.tmpdir, inventory=self.inventory)

        self.assertIn("components", result)
        # Parser includes lib_symbol definitions, so expect 4 (2 libs + 2 instances)
        self.assertEqual(len(result["components"]), 4)

    def test_generate_bom_with_output_file(self):
        """Test generate_bom writes output file"""
        output = self.tmpdir / "bom.csv"
        generate_bom(input=self.schematic, inventory=self.inventory, output=output)

        self.assertTrue(output.exists())
        content = output.read_text(encoding="utf-8")
        self.assertIn("Reference", content)
        self.assertIn("R1", content)
        self.assertIn("C1", content)

    def test_generate_bom_with_options(self):
        """Test generate_bom with BOMOptions"""
        opts = BOMOptions(verbose=True, debug=True, smd_only=True)

        result = generate_bom(
            input=self.schematic, inventory=self.inventory, options=opts
        )

        # All components are SMD, so should still have 2
        self.assertEqual(len(result["bom_entries"]), 2)

    def test_generate_bom_file_not_found(self):
        """Test generate_bom raises error for missing file"""
        with self.assertRaises(FileNotFoundError):
            generate_bom(
                input=self.tmpdir / "nonexistent.kicad_sch", inventory=self.inventory
            )

    def test_generate_bom_inventory_not_found(self):
        """Test generate_bom raises error for missing inventory"""
        with self.assertRaises(FileNotFoundError):
            generate_bom(
                input=self.schematic, inventory=self.tmpdir / "nonexistent.csv"
            )


class TestGeneratePOSAPI(unittest.TestCase):
    """Test new v3.0 generate_pos() API"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

        # Create minimal PCB
        self.pcb = self.tmpdir / "test.kicad_pcb"
        pcb_content = """(kicad_pcb (version 20211014) (host pcbnew "6.0")
  (footprint "Resistor_SMD:R_0603_1608Metric" (layer "F.Cu") (at 10.0 20.0 90)
    (fp_text reference "R1" (at 0 0 0) (layer "F.SilkS")))
  (footprint "Capacitor_SMD:C_0603_1608Metric" (layer "B.Cu") (at 30.0 40.0 0)
    (fp_text reference "C1" (at 0 0 0) (layer "B.SilkS"))))
"""
        self.pcb.write_text(pcb_content, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_generate_pos_with_file_input(self):
        """Test generate_pos with specific PCB file"""
        result = generate_pos(input=self.pcb, loader_mode="sexp")

        self.assertIn("board", result)
        self.assertIn("entries", result)
        self.assertIn("generator", result)
        # SMD only by default, so only R1 (top layer)
        self.assertGreaterEqual(len(result["entries"]), 1)

    def test_generate_pos_with_directory_input(self):
        """Test generate_pos with directory (auto-discovery)"""
        result = generate_pos(input=self.tmpdir, loader_mode="sexp")

        self.assertIn("entries", result)
        self.assertGreaterEqual(len(result["entries"]), 1)

    def test_generate_pos_with_output_file(self):
        """Test generate_pos writes output file"""
        output = self.tmpdir / "pos.csv"
        generate_pos(input=self.pcb, output=output, loader_mode="sexp")

        self.assertTrue(output.exists())
        content = output.read_text(encoding="utf-8")
        self.assertIn("Reference", content)
        self.assertIn("R1", content)

    def test_generate_pos_with_options(self):
        """Test generate_pos with POSOptions"""
        opts = POSOptions(
            units="inch",
            origin="board",
            smd_only=False,  # Include THT
            layer_filter="TOP",
        )

        result = generate_pos(input=self.pcb, options=opts, loader_mode="sexp")

        # Should have at least R1 on top
        self.assertGreaterEqual(len(result["entries"]), 1)

    def test_generate_pos_file_not_found(self):
        """Test generate_pos raises error for missing file"""
        with self.assertRaises(FileNotFoundError):
            generate_pos(
                input=self.tmpdir / "nonexistent.kicad_pcb", loader_mode="sexp"
            )


if __name__ == "__main__":
    unittest.main()
