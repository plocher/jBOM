#!/usr/bin/env python3
"""Functional tests for POS command - error cases."""
import sys
from pathlib import Path

# Ensure tests directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_functional_base import FunctionalTestBase


class TestPOSErrorCases(FunctionalTestBase):
    """Test POS command error handling."""
    
    def test_pos_missing_pcb_file(self):
        """Missing PCB file should produce clear error."""
        rc, stdout, stderr = self.run_jbom([
            'pos', 'nonexistent.kicad_pcb',
            '-o', str(self.output_dir / 'pos.csv'),
            '--loader', 'sexp'
        ], expected_rc=None)
        
        # Should fail with non-zero exit code
        self.assertNotEqual(rc, 0, "Should fail with non-zero exit code")
        
        # Error message should mention the file
        combined_output = stdout + stderr
        self.assertTrue(
            'nonexistent' in combined_output.lower() or
            'not found' in combined_output.lower() or
            'does not exist' in combined_output.lower(),
            "Should mention missing PCB file"
        )
    
    def test_pos_directory_with_no_pcb(self):
        """Empty directory should produce error about no PCB file."""
        empty_dir = self.output_dir / 'empty_pcb_dir'
        empty_dir.mkdir()
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(empty_dir),
            '-o', str(self.output_dir / 'pos.csv'),
            '--loader', 'sexp'
        ], expected_rc=None)
        
        # Should fail
        self.assertNotEqual(rc, 0)
        
        # Should mention no PCB found
        combined_output = stdout + stderr
        self.assertTrue(
            'could not find pcb' in combined_output.lower() or
            'no .kicad_pcb' in combined_output.lower() or
            'pcb file' in combined_output.lower(),
            "Should mention no PCB file found"
        )
    
    def test_pos_malformed_pcb_file(self):
        """Malformed PCB should produce parse error."""
        bad_pcb = self.output_dir / 'bad.kicad_pcb'
        bad_pcb.write_text('This is not valid S-expression syntax (())')
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(bad_pcb),
            '-o', str(self.output_dir / 'pos.csv'),
            '--loader', 'sexp'
        ], expected_rc=None)
        
        # Should fail
        self.assertNotEqual(rc, 0)
        
        # Should mention parse error or syntax error
        combined_output = stdout + stderr
        self.assertTrue(
            'parse' in combined_output.lower() or
            'syntax' in combined_output.lower() or
            'invalid' in combined_output.lower() or
            'error' in combined_output.lower(),
            "Should mention parse/syntax error"
        )
    
    def test_pos_invalid_units(self):
        """Invalid units should produce argparse error."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(self.output_dir / 'pos.csv'),
            '--units', 'kilometers',
            '--loader', 'sexp'
        ], expected_rc=None)
        
        # Should fail
        self.assertNotEqual(rc, 0)
        
        # Should mention invalid choice and valid options
        combined_output = stdout + stderr
        self.assertTrue(
            'invalid choice' in combined_output.lower() or
            'argument --units' in combined_output.lower(),
            "Should mention invalid units argument"
        )
        
        # Should show valid choices
        self.assertTrue(
            'mm' in combined_output or
            'inch' in combined_output,
            "Should show valid unit choices"
        )
    
    def test_pos_invalid_layer(self):
        """Invalid layer should produce argparse error."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(self.output_dir / 'pos.csv'),
            '--layer', 'MIDDLE',
            '--loader', 'sexp'
        ], expected_rc=None)
        
        # Should fail
        self.assertNotEqual(rc, 0)
        
        # Should mention invalid choice
        combined_output = stdout + stderr
        self.assertTrue(
            'invalid choice' in combined_output.lower() or
            'argument --layer' in combined_output.lower() or
            'middle' in combined_output.lower(),
            "Should mention invalid layer argument"
        )
        
        # Should show valid choices
        self.assertTrue(
            'TOP' in combined_output or
            'BOTTOM' in combined_output,
            "Should show valid layer choices"
        )
    
    def test_pos_invalid_loader(self):
        """Invalid loader should produce argparse error."""
        pcb_file = self.minimal_proj / 'minimal.kicad_pcb'
        
        rc, stdout, stderr = self.run_jbom([
            'pos', str(pcb_file),
            '-o', str(self.output_dir / 'pos.csv'),
            '--loader', 'magic'
        ], expected_rc=None)
        
        # Should fail
        self.assertNotEqual(rc, 0)
        
        # Should mention invalid choice
        combined_output = stdout + stderr
        self.assertTrue(
            'invalid choice' in combined_output.lower() or
            'argument --loader' in combined_output.lower() or
            'magic' in combined_output.lower(),
            "Should mention invalid loader argument"
        )
        
        # Should show valid choices
        self.assertTrue(
            'auto' in combined_output or
            'sexp' in combined_output or
            'pcbnew' in combined_output,
            "Should show valid loader choices"
        )


if __name__ == '__main__':
    import unittest
    unittest.main()
