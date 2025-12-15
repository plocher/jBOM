#!/usr/bin/env python3
"""Functional tests for POS command - happy paths."""
import sys
from pathlib import Path

# Ensure tests directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_functional_base import FunctionalTestBase


class TestPOSHappyPaths(FunctionalTestBase):
    """Test POS command happy path scenarios."""
    
    def test_pos_default_fields(self):
        """Generate POS with default (+standard) fields."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        output = self.output_dir / 'pos.csv'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(output),
            '--loader', 'sexp'
        ])
        
        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        
        # Should have header + data rows
        self.assertGreater(len(rows), 1, "POS should have data rows")
        
        # Check for +standard fields
        header = rows[0]
        self.assertIn('Reference', header)
        self.assertIn('X', header)
        self.assertIn('Y', header)
        self.assertIn('Rotation', header)
        self.assertIn('Side', header)
        self.assertIn('Footprint', header)
        self.assertIn('SMD', header)
    
    def test_pos_jlc_flag(self):
        """Generate POS with --jlc flag (JLC preset)."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        output = self.output_dir / 'pos_jlc.csv'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(output),
            '--jlc',
            '--loader', 'sexp'
        ])
        
        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        
        # Check for JLC fields (note: order matters for JLC)
        header = rows[0]
        self.assertIn('Reference', header)
        self.assertIn('Side', header)
        self.assertIn('X', header)
        self.assertIn('Y', header)
        self.assertIn('Rotation', header)
        self.assertIn('Package', header)
        self.assertIn('SMD', header)
    
    def test_pos_custom_fields(self):
        """Generate POS with custom field list."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        output = self.output_dir / 'pos_custom.csv'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(output),
            '-f', 'Reference,X,Y,Smd',
            '--loader', 'sexp'
        ])
        
        self.assertEqual(rc, 0)
        rows = self.assert_csv_headers(output, ['Reference', 'X', 'Y', 'SMD'])
        self.assertGreater(len(rows), 1)
    
    def test_pos_units_mm(self):
        """Generate POS with millimeter units (default)."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        output = self.output_dir / 'pos_mm.csv'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(output),
            '--units', 'mm',
            '--loader', 'sexp'
        ])
        
        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        
        # Check that coordinates are reasonable for mm
        # Our test components are at ~50-100 mm
        x_idx = rows[0].index('X')
        y_idx = rows[0].index('Y')
        
        for row in rows[1:]:
            if row:
                x_val = float(row[x_idx])
                y_val = float(row[y_idx])
                # Should be in the range we set (around 50-100 mm)
                self.assertGreater(x_val, 40)
                self.assertLess(x_val, 110)
    
    def test_pos_units_inch(self):
        """Generate POS with inch units."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        output = self.output_dir / 'pos_inch.csv'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(output),
            '--units', 'inch',
            '--loader', 'sexp'
        ])
        
        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        
        # Check that coordinates are reasonable for inches
        # Our test components at 50-100 mm = ~2-4 inches
        x_idx = rows[0].index('X')
        y_idx = rows[0].index('Y')
        
        for row in rows[1:]:
            if row:
                x_val = float(row[x_idx])
                y_val = float(row[y_idx])
                # Should be in inch range
                self.assertGreater(x_val, 1.5)
                self.assertLess(x_val, 4.5)
    
    def test_pos_origin_board(self):
        """Generate POS with board origin (default)."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        output = self.output_dir / 'pos_board.csv'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(output),
            '--origin', 'board',
            '--loader', 'sexp'
        ])
        
        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        self.assertGreater(len(rows), 1)
    
    def test_pos_origin_aux(self):
        """Generate POS with auxiliary origin."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        output = self.output_dir / 'pos_aux.csv'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(output),
            '--origin', 'aux',
            '--loader', 'sexp'
        ])
        
        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        self.assertGreater(len(rows), 1)
    
    def test_pos_layer_top(self):
        """Generate POS for TOP layer only."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        output = self.output_dir / 'pos_top.csv'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(output),
            '--layer', 'TOP',
            '--loader', 'sexp',
            '--smd-only'  # Keep default
        ])
        
        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        
        # Check that all components are on TOP
        side_idx = rows[0].index('Side')
        for row in rows[1:]:
            if row:
                self.assertEqual(row[side_idx], 'TOP')
    
    def test_pos_layer_bottom(self):
        """Generate POS for BOTTOM layer only."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        output = self.output_dir / 'pos_bottom.csv'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(output),
            '--layer', 'BOTTOM',
            '--loader', 'sexp',
            '--smd-only'  # Keep default
        ])
        
        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        
        # Our minimal project has J1 on bottom
        # With --smd-only, may be empty
        if len(rows) > 1:
            side_idx = rows[0].index('Side')
            for row in rows[1:]:
                if row:
                    self.assertEqual(row[side_idx], 'BOTTOM')
    
    def test_pos_to_console(self):
        """Generate POS to console (formatted table)."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', 'console',
            '--loader', 'sexp'
        ])
        
        self.assertEqual(rc, 0)
        self.assert_stdout_is_table(stdout)
        
        # Table should contain component references
        self.assertIn('R1', stdout)
        self.assertIn('C1', stdout)
    
    def test_pos_to_stdout(self):
        """Generate POS to stdout (CSV format)."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', '-',
            '--loader', 'sexp'
        ])
        
        self.assertEqual(rc, 0)
        rows = self.assert_stdout_is_csv(stdout)
        
        # Should have header + data
        self.assertGreater(len(rows), 1)
        self.assertIn('Reference', rows[0])
    
    def test_pos_coordinate_precision(self):
        """Verify POS coordinate precision (4 decimal places)."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        output = self.output_dir / 'pos_precision.csv'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(output),
            '--loader', 'sexp'
        ])
        
        self.assertEqual(rc, 0)
        rows = self.assert_csv_valid(output)
        
        x_idx = rows[0].index('X')
        y_idx = rows[0].index('Y')
        rot_idx = rows[0].index('Rotation')
        
        for row in rows[1:]:
            if row:
                x_str = row[x_idx]
                y_str = row[y_idx]
                rot_str = row[rot_idx]
                
                # Coordinates should have up to 4 decimal places
                if '.' in x_str:
                    decimals = len(x_str.split('.')[1])
                    self.assertLessEqual(decimals, 4, f"X coordinate {x_str} has too many decimals")
                
                # Rotation should have 1 decimal place
                if '.' in rot_str:
                    decimals = len(rot_str.split('.')[1])
                    self.assertLessEqual(decimals, 1, f"Rotation {rot_str} should have 1 decimal place")


if __name__ == '__main__':
    import unittest
    unittest.main()
