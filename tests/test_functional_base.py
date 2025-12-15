#!/usr/bin/env python3
"""Base class for functional tests with common utilities."""
import csv
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from typing import List, Optional, Tuple


class FunctionalTestBase(unittest.TestCase):
    """Base class for functional tests with common utilities."""
    
    @classmethod
    def setUpClass(cls):
        """Set up paths to test resources."""
        cls.fixtures = Path(__file__).parent / 'fixtures'
        
        # Real-world resources for integration testing
        cls.inventory_numbers = Path('/Users/jplocher/Dropbox/KiCad/jBOM-dev/SPCoast-INVENTORY.numbers')
        cls.real_projects = {
            'altmill': Path('/Users/jplocher/Dropbox/KiCad/projects/AltmillSwitches'),
            'core_wt32': Path('/Users/jplocher/Dropbox/KiCad/projects/Core-wt32-eth0'),
            'led_strip': Path('/Users/jplocher/Dropbox/KiCad/projects/LEDStripDriver'),
        }
        
        # Test fixtures for isolated/error testing
        cls.minimal_proj = cls.fixtures / 'minimal_project'
        cls.inventory_csv = cls.fixtures / 'inventory.csv'
    
    def setUp(self):
        """Create temporary directory for test output."""
        # Ensure src is on path
        src_path = Path(__file__).parent.parent / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        self.tmp = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.tmp.name)
    
    def tearDown(self):
        """Clean up temporary directory."""
        self.tmp.cleanup()
    
    def run_jbom(self, args: List[str], expected_rc: Optional[int] = 0) -> Tuple[int, str, str]:
        """Run jBOM CLI and capture output.
        
        Args:
            args: Command line arguments (e.g. ['bom', 'project/', '-i', 'inv.csv'])
            expected_rc: Expected return code (None to skip check)
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        from jbom.cli.main import main
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout = StringIO()
        stderr = StringIO()
        
        try:
            sys.stdout = stdout
            sys.stderr = stderr
            rc = main(args)
        except SystemExit as e:
            # Argparse calls sys.exit() on error
            rc = e.code if e.code is not None else 1
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        stdout_val = stdout.getvalue()
        stderr_val = stderr.getvalue()
        
        if expected_rc is not None:
            self.assertEqual(rc, expected_rc, 
                f"Expected exit code {expected_rc}, got {rc}\n"
                f"stdout: {stdout_val}\n"
                f"stderr: {stderr_val}")
        
        return rc, stdout_val, stderr_val
    
    def assert_csv_valid(self, csv_path: Path) -> List[List[str]]:
        """Validate CSV file is well-formed and return rows.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            List of rows (each row is a list of strings)
        """
        self.assertTrue(csv_path.exists(), f"CSV file not found: {csv_path}")
        
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        self.assertGreater(len(rows), 0, "CSV is empty")
        return rows
    
    def assert_csv_headers(self, csv_path: Path, expected_headers: List[str]) -> List[List[str]]:
        """Validate CSV has expected headers and return all rows.
        
        Args:
            csv_path: Path to CSV file
            expected_headers: Expected header row
            
        Returns:
            List of all rows including header
        """
        rows = self.assert_csv_valid(csv_path)
        self.assertEqual(rows[0], expected_headers, 
            f"Header mismatch.\nExpected: {expected_headers}\nGot: {rows[0]}")
        return rows
    
    def assert_file_contains(self, file_path: Path, text: str):
        """Assert that a file contains specific text."""
        self.assertTrue(file_path.exists(), f"File not found: {file_path}")
        content = file_path.read_text(encoding='utf-8')
        self.assertIn(text, content, f"Text '{text}' not found in {file_path}")
    
    def assert_stdout_is_csv(self, stdout: str) -> List[List[str]]:
        """Assert that stdout contains valid CSV and return rows."""
        from io import StringIO
        reader = csv.reader(StringIO(stdout))
        rows = list(reader)
        self.assertGreater(len(rows), 0, "Stdout CSV is empty")
        return rows
    
    def assert_stdout_is_table(self, stdout: str):
        """Assert that stdout contains formatted table (not CSV)."""
        self.assertGreater(len(stdout), 0, "Stdout is empty")
        # Tables should have visual separators
        self.assertTrue(
            any(separator in stdout for separator in ['---', '===', '│', '|']),
            "Stdout does not appear to be a formatted table"
        )
