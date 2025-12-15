#!/usr/bin/env python3
"""Integration tests targeting specific user projects.

- BOM generation using the real Numbers inventory, per project
- POS generation using the S-expression loader

Skips gracefully if files or optional dependencies are not present.
"""
import unittest
from pathlib import Path
import tempfile
import os

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jbom.pcb.board_loader import load_board
from jbom.pcb.position import PositionGenerator, PlacementOptions

INVENTORY_PATH = Path(os.environ.get('INVENTORY', '/dev/null'))
# PROJECTS_LIST: comma-separated list of project directories provided by Makefile
_PROJECTS_LIST = os.environ.get('PROJECTS_LIST', '').strip()
PROJECTS = [Path(p.strip()) for p in (_PROJECTS_LIST.split(',') if _PROJECTS_LIST else []) if p.strip()]


class TestIntegrationProjects(unittest.TestCase):
    def test_bom_with_numbers_inventory(self):
        # Skip if numbers-parser or inventory not available
        try:
            import numbers_parser  # noqa: F401
        except Exception:
            self.skipTest('numbers-parser not installed')
        if not INVENTORY_PATH.exists():
            self.skipTest('Numbers inventory not present')

        from jbom.jbom import generate_bom_api

        for proj in PROJECTS:
            with self.subTest(project=str(proj)):
                if not proj.exists():
                    self.skipTest(f'Project directory missing: {proj}')
                # Use project directory (generate_bom_api will locate schematic)
                result = generate_bom_api(str(proj), str(INVENTORY_PATH))
                self.assertIn('inventory_count', result)
                self.assertGreaterEqual(result['inventory_count'], 1)
                # Ensure keys present; do not assert entry counts (projects may vary)
                self.assertIn('bom_entries', result)
                self.assertIn('components', result)

    def test_pos_generation(self):
        # No dependency on Numbers inventory; just ensure we can load and emit a POS CSV
        for proj in PROJECTS:
            with self.subTest(project=str(proj)):
                if not proj.exists():
                    self.skipTest(f'Project directory missing: {proj}')
                boards = list(proj.rglob('*.kicad_pcb'))
                if not boards:
                    self.skipTest(f'No .kicad_pcb under {proj}')
                board = load_board(boards[0], mode='sexp')
                # Write POS CSV
                with tempfile.TemporaryDirectory() as td:
                    out = Path(td) / f'{boards[0].stem}.pos.csv'
                    pg = PositionGenerator(board, PlacementOptions(units='mm', origin='board', smd_only=False))
                    fields = pg.parse_fields_argument('+standard')
                    pg.write_csv(out, fields)
                    text = out.read_text(encoding='utf-8').splitlines()
                    self.assertGreaterEqual(len(text), 1)
                    self.assertIn('Reference', text[0])


if __name__ == '__main__':
    unittest.main()
