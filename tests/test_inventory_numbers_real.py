#!/usr/bin/env python3
"""Integration test for Numbers inventory (real file path if available).

Skips if the Numbers inventory file or dependency is not available, or if no
KiCad schematic is found under the user's projects directory.
"""
import unittest
from pathlib import Path
import os

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Get inventory path from environment (None if not set)
_inventory_env = os.environ.get('INVENTORY', '').strip()
INVENTORY_PATH = Path(_inventory_env) if _inventory_env else None

# Prefer an explicit list from PROJECTS_LIST; fall back to PROJECTS root
_PROJECTS_LIST = os.environ.get('PROJECTS_LIST', '').strip()
_projects_env = os.environ.get('PROJECTS', '').strip()
PROJECTS_ROOT = Path(_projects_env) if (_projects_env and not _PROJECTS_LIST) else None


class TestRealNumbersInventory(unittest.TestCase):
    def test_inventory_loads_if_available(self):
        try:
            from jbom.inventory import InventoryMatcher
        except Exception:
            self.skipTest('jbom not importable')
        try:
            import numbers_parser  # noqa: F401
        except Exception:
            self.skipTest('numbers-parser not installed')
        if not INVENTORY_PATH:
            self.skipTest('INVENTORY environment variable not set')
        if not INVENTORY_PATH.exists() or not INVENTORY_PATH.is_file():
            self.skipTest('Real Numbers inventory file not present')
        if INVENTORY_PATH.suffix.lower() not in ['.csv', '.xlsx', '.xls', '.numbers']:
            self.skipTest('Inventory file has no valid extension')
        matcher = InventoryMatcher(INVENTORY_PATH)
        self.assertGreaterEqual(len(matcher.inventory), 1)

    def test_generate_bom_with_real_inventory_if_project_available(self):
        try:
            import numbers_parser  # noqa: F401
        except Exception:
            self.skipTest('numbers-parser not installed')
        if not INVENTORY_PATH:
            self.skipTest('INVENTORY environment variable not set')
        if not INVENTORY_PATH.exists() or not INVENTORY_PATH.is_file():
            self.skipTest('Real Numbers inventory file not present')
        if INVENTORY_PATH.suffix.lower() not in ['.csv', '.xlsx', '.xls', '.numbers']:
            self.skipTest('Inventory file has no valid extension')

        from jbom.jbom import generate_bom_api
        # Determine a project to run against
        targets = []
        if _PROJECTS_LIST:
            targets = [Path(p.strip()) for p in _PROJECTS_LIST.split(',') if p.strip()]
        elif PROJECTS_ROOT and PROJECTS_ROOT.exists():
            # fallback: scan root for first project with a schematic
            sch_files = list(PROJECTS_ROOT.rglob('*.kicad_sch'))
            if sch_files:
                targets = [sch_files[0].parent]
        if not targets:
            self.skipTest('No projects specified or found')
        # Use the first target
        proj_dir = targets[0]
        result = generate_bom_api(str(proj_dir), str(INVENTORY_PATH))
        # Should produce a dict with keys and at least parse inventory
        self.assertIn('inventory_count', result)
        self.assertGreaterEqual(result['inventory_count'], 1)


if __name__ == '__main__':
    unittest.main()
