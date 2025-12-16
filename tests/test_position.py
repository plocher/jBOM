#!/usr/bin/env python3
"""Tests for placement generation (POSGenerator) and field parsing.

These tests exercise the new 'pos' functionality introduced in the v2 CLI.
"""
import tempfile
import unittest
from pathlib import Path

# Ensure src is on path (mirrors pattern in existing tests)
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jbom.loaders.pcb import load_board
from jbom.generators.pos import POSGenerator, PlacementOptions


_SIMPLE_BOARD = """
(kicad_pcb (version 20211014) (host pcbnew "6.0")
  (footprint "Resistor_SMD:R_0603_1608Metric" (layer "F.Cu") (at 25.4 50.8 90)
    (fp_text reference "R1" (at 0 0 0) (layer "F.SilkS")))
  (footprint "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" (layer "B.Cu") (at 0 0 0)
    (fp_text reference "J1" (at 0 0 0) (layer "B.SilkS")))
)
""".strip()


class TestPlacementFields(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.board_path = Path(self.tmp.name) / "test.kicad_pcb"
        self.board_path.write_text(_SIMPLE_BOARD, encoding="utf-8")
        self.board = load_board(self.board_path, mode="sexp")

    def tearDown(self):
        self.tmp.cleanup()

    def test_presets(self):
        opts = PlacementOptions(smd_only=False)
        pg = POSGenerator(opts)
        pg.board = self.board  # Set board directly for testing
        self.assertEqual(
            pg.parse_fields_argument("+standard"),
            ["reference", "x", "y", "rotation", "side", "footprint", "smd"],
        )
        self.assertEqual(
            pg.parse_fields_argument("+jlc"),
            ["reference", "side", "x", "y", "rotation", "package", "smd"],
        )
        # Custom list
        self.assertEqual(
            pg.parse_fields_argument("Reference,X,Y,Side"),
            ["reference", "x", "y", "side"],
        )
        # All includes all known fields
        self.assertCountEqual(
            pg.parse_fields_argument("+all"),
            [
                "reference",
                "x",
                "y",
                "rotation",
                "side",
                "footprint",
                "package",
                "datasheet",
                "version",
                "smd",
            ],
        )

    def test_units_and_origin(self):
        # Coordinates are 25.4,50.8 mm → 1.0000,2.0000 inches
        opts = PlacementOptions(units="inch", origin="board", smd_only=False)
        pg = POSGenerator(opts)
        pg.board = self.board  # Set board directly for testing
        out = Path(self.tmp.name) / "out.csv"
        components = list(pg.iter_components())
        pg.write_csv(components, out, pg.parse_fields_argument("+standard"))
        data = out.read_text(encoding="utf-8").splitlines()
        self.assertIn("Reference,X,Y,Rotation,Side,Footprint,SMD", data[0])
        # R1 row in inches with 4 decimals
        self.assertIn(
            "R1,1.0000,2.0000,90.0,TOP,Resistor_SMD:R_0603_1608Metric", data[1]
        )

    def test_filters(self):
        # smd_only=True should exclude the header footprint lacking an SMD package token
        opts = PlacementOptions(smd_only=True)
        pg = POSGenerator(opts)
        pg.board = self.board  # Set board directly for testing
        components = list(pg.iter_components())
        # Only R1 (0603) should remain
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0].reference, "R1")

        # layer filter TOP keeps R1 only
        opts2 = PlacementOptions(smd_only=False, layer_filter="TOP")
        pg2 = POSGenerator(opts2)
        pg2.board = self.board  # Set board directly for testing
        components2 = list(pg2.iter_components())
        self.assertEqual(len(components2), 1)
        self.assertEqual(components2[0].reference, "R1")


if __name__ == "__main__":
    unittest.main()
