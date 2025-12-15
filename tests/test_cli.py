#!/usr/bin/env python3
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jbom.cli.main import main as cli_main


class TestCLIJlcImplicationBom(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # Dummy paths
        self.inv = Path(self.tmp.name) / 'inv.csv'
        self.inv.write_text('IPN,Category,Package,Value,LCSC,Priority\n', encoding='utf-8')
        self.proj = Path(self.tmp.name) / 'proj'
        self.proj.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    @patch('jbom.jbom.BOMGenerator')
    @patch('jbom.jbom.InventoryMatcher')
    @patch('jbom.cli.main._parse_fields_argument')
    @patch('jbom.cli.main.generate_bom_api')
    def test_bom_jlc_implies_preset(self, mock_gen_api, mock_parse, _m_inv, _m_bomgen):
        mock_gen_api.return_value = {
            'bom_entries': [],
            'available_fields': {'reference': 'd', 'quantity': 'd', 'lcsc': 'd', 'value': 'd', 'i:package': 'd'},
            'components': [],
        }
        mock_parse.return_value = ['reference','quantity','lcsc']
        rc = cli_main(['bom', str(self.proj), '-i', str(self.inv), '--jlc'])
        self.assertEqual(rc, 0)
        # First arg to _parse_fields_argument should be '+jlc'
        called_args = mock_parse.call_args[0]
        self.assertTrue(called_args[0].startswith('+jlc'))

    @patch('jbom.jbom.BOMGenerator')
    @patch('jbom.jbom.InventoryMatcher')
    @patch('jbom.cli.main._parse_fields_argument')
    @patch('jbom.cli.main.generate_bom_api')
    def test_bom_jlc_prepends_when_fields_present(self, mock_gen_api, mock_parse, _m_inv, _m_bomgen):
        mock_gen_api.return_value = {
            'bom_entries': [],
            'available_fields': {'reference': 'd', 'quantity': 'd', 'lcsc': 'd', 'value': 'd'},
            'components': [],
        }
        mock_parse.return_value = ['reference','lcsc']
        rc = cli_main(['bom', str(self.proj), '-i', str(self.inv), '--jlc', '-f', 'reference,lcsc'])
        self.assertEqual(rc, 0)
        called_args = mock_parse.call_args[0]
        self.assertTrue(called_args[0].split(',')[0] == '+jlc')


class TestCLIJlcImplicationPos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.board = Path(self.tmp.name) / 'b.kicad_pcb'
        self.board.write_text('(kicad_pcb (version 20211014) (host pcbnew "6") (footprint "Res:R_0603" (layer "F.Cu") (at 1 2 0) (fp_text reference "R1"))))'.replace('))))', ')))'), encoding='utf-8')
        self.out = Path(self.tmp.name) / 'out.csv'

    def tearDown(self):
        self.tmp.cleanup()

    @patch('jbom.cli.main.PositionGenerator.parse_fields_argument')
    def test_pos_jlc_implies_preset(self, mock_parse):
        mock_parse.return_value = ['reference','side','x','y','rotation','package']
        rc = cli_main(['pos', str(self.board), '-o', str(self.out), '--jlc', '--loader', 'sexp'])
        self.assertEqual(rc, 0)
        called_args = mock_parse.call_args[0]
        self.assertTrue(called_args[0].startswith('+jlc'))

    def test_pos_end_to_end_writes_file(self):
        # Ensure CLI writes a CSV using sexp loader
        rc = cli_main(['pos', str(self.board), '-o', str(self.out), '--loader', 'sexp'])
        self.assertEqual(rc, 0)
        self.assertTrue(self.out.exists())
        self.assertIn('Reference', self.out.read_text(encoding='utf-8').splitlines()[0])


if __name__ == '__main__':
    unittest.main()
