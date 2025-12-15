#!/usr/bin/env python3
"""Functional tests for BOM command - error cases."""
import sys
from pathlib import Path

# Ensure tests directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_functional_base import FunctionalTestBase


class TestBOMErrorCases(FunctionalTestBase):
    """Test BOM command error handling."""
    
    def test_bom_missing_inventory_file(self):
        """Missing inventory file should produce clear error."""
        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', 'nonexistent.csv',
            '-o', str(self.output_dir / 'bom.csv')
        ], expected_rc=None)
        
        # Should fail with non-zero exit code
        self.assertNotEqual(rc, 0, "Should fail with non-zero exit code")
        
        # Error message should mention the file
        combined_output = stdout + stderr
        self.assertIn('nonexistent.csv', combined_output.lower())
    
    def test_bom_invalid_inventory_format(self):
        """Invalid inventory format should produce error."""
        # Create a text file that's not CSV/XLSX/Numbers
        bad_inv = self.output_dir / 'inventory.txt'
        bad_inv.write_text('This is not a valid inventory file')
        
        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', str(bad_inv),
            '-o', str(self.output_dir / 'bom.csv')
        ], expected_rc=None)
        
        # Should fail
        self.assertNotEqual(rc, 0)
        
        # Should mention unsupported format
        combined_output = stdout + stderr
        self.assertTrue(
            'unsupported' in combined_output.lower() or 
            'format' in combined_output.lower(),
            "Should mention unsupported format"
        )
    
    def test_bom_missing_project_directory(self):
        """Missing project directory should produce error."""
        # Note: Creates directory if it doesn't exist, then fails on no schematic
        # This test validates we get an error either way
        rc, stdout, stderr = self.run_jbom([
            'bom', 'nonexistent_project/',
            '-i', str(self.inventory_csv),
            '-o', str(self.output_dir / 'bom.csv')
        ], expected_rc=None)
        
        # Should fail with some error
        self.assertNotEqual(rc, 0, "Should fail with non-zero exit code")
        
        # Should mention missing project, file, or no schematic
        combined_output = stdout + stderr
        self.assertTrue(
            'not found' in combined_output.lower() or
            'no such file' in combined_output.lower() or
            'does not exist' in combined_output.lower() or
            'no .kicad_sch' in combined_output.lower() or
            'schematic' in combined_output.lower(),
            "Should mention missing project or schematic"
        )
    
    def test_bom_project_with_no_schematics(self):
        """Empty project directory should produce error."""
        empty_proj = self.output_dir / 'empty_project'
        empty_proj.mkdir()
        
        rc, stdout, stderr = self.run_jbom([
            'bom', str(empty_proj),
            '-i', str(self.inventory_csv),
            '-o', str(self.output_dir / 'bom.csv')
        ], expected_rc=None)
        
        # Should fail
        self.assertNotEqual(rc, 0)
        
        # Should mention no schematic found
        combined_output = stdout + stderr
        self.assertTrue(
            'no .kicad_sch' in combined_output.lower() or
            'schematic' in combined_output.lower(),
            "Should mention no schematic file found"
        )
    
    def test_bom_invalid_field_name(self):
        """Invalid field name should produce error with field list."""
        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', str(self.inventory_csv),
            '-o', str(self.output_dir / 'bom.csv'),
            '-f', 'Reference,InvalidField'
        ], expected_rc=None)
        
        # Should fail
        self.assertNotEqual(rc, 0)
        
        # Should mention invalid field
        combined_output = stdout + stderr
        self.assertIn('invalidfield', combined_output.lower())
        
        # Should suggest available fields
        self.assertTrue(
            'available' in combined_output.lower() or
            'valid' in combined_output.lower() or
            '--list-fields' in combined_output.lower(),
            "Should suggest available fields"
        )
    
    def test_bom_invalid_preset_name(self):
        """Invalid preset name should produce error with preset list."""
        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', str(self.inventory_csv),
            '-o', str(self.output_dir / 'bom.csv'),
            '-f', '+invalid_preset'
        ], expected_rc=None)
        
        # Should fail
        self.assertNotEqual(rc, 0)
        
        # Should mention invalid preset
        combined_output = stdout + stderr
        self.assertIn('invalid_preset', combined_output.lower())
        
        # Should list valid presets
        self.assertTrue(
            '+standard' in combined_output.lower() or
            '+jlc' in combined_output.lower() or
            'valid' in combined_output.lower(),
            "Should list valid presets"
        )
    
    def test_bom_malformed_schematic_file(self):
        """Malformed schematic should produce parse error."""
        bad_sch = self.output_dir / 'bad_project'
        bad_sch.mkdir()
        sch_file = bad_sch / 'bad.kicad_sch'
        sch_file.write_text('This is not valid S-expression syntax (())')
        
        rc, stdout, stderr = self.run_jbom([
            'bom', str(bad_sch),
            '-i', str(self.inventory_csv),
            '-o', str(self.output_dir / 'bom.csv')
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
    
    def test_bom_missing_inventory_headers(self):
        """Inventory without required headers should produce error."""
        bad_inv = self.output_dir / 'bad_inventory.csv'
        # Missing required columns like IPN, Category, etc.
        bad_inv.write_text('SomeColumn,AnotherColumn\nvalue1,value2\n')
        
        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', str(bad_inv),
            '-o', str(self.output_dir / 'bom.csv')
        ], expected_rc=None)
        
        # Should fail
        self.assertNotEqual(rc, 0)
        
        # Should mention missing headers/columns
        combined_output = stdout + stderr
        self.assertTrue(
            'column' in combined_output.lower() or
            'header' in combined_output.lower() or
            'required' in combined_output.lower() or
            'missing' in combined_output.lower(),
            "Should mention missing headers/columns"
        )


if __name__ == '__main__':
    import unittest
    unittest.main()
