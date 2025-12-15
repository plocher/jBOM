#!/usr/bin/env python3
"""Tests for placement generation (PositionGenerator) and field parsing.

These tests exercise the new 'pos' functionality introduced in the v2 CLI.
"""
import csv
import io
import tempfile
import unittest
from pathlib import Path

# Ensure src is on path (mirrors pattern in existing tests)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jbom.pcb.board_loader import load_board
from jbom.pcb.position import PositionGenerator, PlacementOptions


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
        self.board_path = Path(self.tmp.name) / 'test.kicad_pcb'
        self.board_path.write_text(_SIMPLE_BOARD, encoding='utf-8')
        self.board = load_board(self.board_path, mode='sexp')

    def tearDown(self):
        self.tmp.cleanup()

    def test_presets(self):
        pg = PositionGenerator(self.board, PlacementOptions(smd_only=False))
        self.assertEqual(pg.parse_fields_argument('+standard'), ['reference','x','y','rotation','side','footprint','smd'])
        self.assertEqual(pg.parse_fields_argument('+jlc'), ['reference','side','x','y','rotation','package','smd'])
        # Custom list
        self.assertEqual(pg.parse_fields_argument('Reference,X,Y,Side'), ['reference','x','y','side'])
        # All includes all known fields
        self.assertCountEqual(pg.parse_fields_argument('+all'), ['reference','x','y','rotation','side','footprint','package','datasheet','version','smd'])

    def test_units_and_origin(self):
        # Coordinates are 25.4,50.8 mm → 1.0000,2.0000 inches
        pg = PositionGenerator(self.board, PlacementOptions(units='inch', origin='board', smd_only=False))
        out = Path(self.tmp.name) / 'out.csv'
        pg.write_csv(out, pg.parse_fields_argument('+standard'))
        data = out.read_text(encoding='utf-8').splitlines()
        self.assertIn('Reference,X,Y,Rotation,Side,Footprint,SMD', data[0])
        # R1 row in inches with 4 decimals
        self.assertIn('R1,1.0000,2.0000,90.0,TOP,Resistor_SMD:R_0603_1608Metric', data[1])

    def test_filters(self):
        # smd_only=True should exclude the header footprint lacking an SMD package token
        pg = PositionGenerator(self.board, PlacementOptions(smd_only=True))
        rows = pg.generate_kicad_pos_rows()
        # Only R1 (0603) should remain
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], 'R1')

        # layer filter TOP keeps R1 only
        pg2 = PositionGenerator(self.board, PlacementOptions(smd_only=False, layer_filter='TOP'))
        rows2 = pg2.generate_kicad_pos_rows()
        self.assertEqual(len(rows2), 1)
        self.assertEqual(rows2[0][0], 'R1')


if __name__ == '__main__':
    unittest.main()
