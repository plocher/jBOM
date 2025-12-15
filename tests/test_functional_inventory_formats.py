#!/usr/bin/env python3
"""Functional tests for different inventory file formats."""
import sys
from pathlib import Path

# Ensure tests directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_functional_base import FunctionalTestBase


class TestInventoryFormats(FunctionalTestBase):
    """Test loading inventory from different file formats."""
    
    def setUp(self):
        super().setUp()
        # Paths to real inventory files in different formats
        self.inventory_csv = Path('/Users/jplocher/Dropbox/KiCad/jBOM-dev/SPCoast-INVENTORY.csv')
        self.inventory_xlsx = Path('/Users/jplocher/Dropbox/KiCad/jBOM-dev/SPCoast-INVENTORY.xlsx')
        self.inventory_numbers = Path('/Users/jplocher/Dropbox/KiCad/jBOM-dev/SPCoast-INVENTORY.numbers')
    
    def test_csv_inventory_format(self):
        """CSV inventory file should load successfully."""
        if not self.inventory_csv.exists():
            self.skipTest(f'CSV inventory not found at {self.inventory_csv}')
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', str(self.inventory_csv),
            '-o', str(output_file)
        ])
        
        # Should succeed
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
        
        # Validate CSV structure
        rows = self.assert_csv_valid(output_file)
        self.assertGreater(len(rows), 1, "Should have headers + data")
    
    def test_xlsx_inventory_format(self):
        """XLSX (Excel) inventory file should load successfully."""
        if not self.inventory_xlsx.exists():
            self.skipTest(f'XLSX inventory not found at {self.inventory_xlsx}')
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', str(self.inventory_xlsx),
            '-o', str(output_file)
        ])
        
        # Should succeed (requires openpyxl)
        if rc != 0 and 'openpyxl' in stderr.lower():
            self.skipTest('openpyxl package not installed')
        
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
        
        # Validate CSV structure
        rows = self.assert_csv_valid(output_file)
        self.assertGreater(len(rows), 1, "Should have headers + data")
    
    def test_numbers_inventory_format(self):
        """Numbers inventory file should load successfully."""
        if not self.inventory_numbers.exists():
            self.skipTest(f'Numbers inventory not found at {self.inventory_numbers}')
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', str(self.inventory_numbers),
            '-o', str(output_file)
        ])
        
        # Should succeed (requires numbers-parser)
        if rc != 0 and 'numbers-parser' in stderr.lower():
            self.skipTest('numbers-parser package not installed')
        
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
        
        # Validate CSV structure
        rows = self.assert_csv_valid(output_file)
        self.assertGreater(len(rows), 1, "Should have headers + data")
    
    def test_inventory_formats_produce_consistent_results(self):
        """All inventory formats should produce similar results."""
        if not (self.inventory_csv.exists() and 
                self.inventory_xlsx.exists() and 
                self.inventory_numbers.exists()):
            self.skipTest('Not all inventory formats available')
        
        results = {}
        
        # Test each format
        for fmt, inv_path in [
            ('csv', self.inventory_csv),
            ('xlsx', self.inventory_xlsx),
            ('numbers', self.inventory_numbers)
        ]:
            output_file = self.output_dir / f'bom_{fmt}.csv'
            rc, stdout, stderr = self.run_jbom([
                'bom', str(self.minimal_proj),
                '-i', str(inv_path),
                '-o', str(output_file)
            ], expected_rc=None)
            
            # Skip if optional dependency missing
            if rc != 0 and ('openpyxl' in stderr.lower() or 'numbers-parser' in stderr.lower()):
                continue
            
            self.assertEqual(rc, 0, f'{fmt} format should succeed')
            rows = self.assert_csv_valid(output_file)
            results[fmt] = rows
        
        # At least CSV should work
        self.assertIn('csv', results, 'CSV format should always work')
        
        # If we have multiple formats, compare row counts
        if len(results) > 1:
            row_counts = {fmt: len(rows) for fmt, rows in results.items()}
            # Allow small differences due to formatting, but should be similar
            self.assertTrue(
                max(row_counts.values()) - min(row_counts.values()) <= 2,
                f"Row counts should be similar across formats: {row_counts}"
            )
    
    def test_empty_inventory_file(self):
        """Empty inventory file should produce warning but not crash."""
        empty_inv = self.output_dir / 'empty_inventory.csv'
        empty_inv.write_text('IPN,Category,Value\n')  # Headers only, no data
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', str(empty_inv),
            '-o', str(output_file)
        ])
        
        # Should succeed but with no inventory matches
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
        
        # BOM should still be generated
        rows = self.assert_csv_valid(output_file)
        self.assertGreater(len(rows), 1, "Should have headers + components")
    
    def test_inventory_with_extra_columns(self):
        """Inventory with unknown/extra columns should be ignored gracefully."""
        extra_cols_inv = self.output_dir / 'extra_inventory.csv'
        extra_cols_inv.write_text(
            'IPN,Category,Value,LCSC,ExtraColumn1,AnotherExtra,RandomData\n'
            'R001,RES,330R,C25231,extra1,extra2,extra3\n'
        )
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', str(extra_cols_inv),
            '-o', str(output_file)
        ])
        
        # Should succeed - extra columns ignored
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
    
    def test_inventory_with_unicode_characters(self):
        """Inventory with unicode characters should be handled correctly."""
        unicode_inv = self.output_dir / 'unicode_inventory.csv'
        unicode_inv.write_text(
            'IPN,Category,Value,Description,LCSC\n'
            'R001,RES,330Ω,Résistance 330Ω ±5%,C25231\n'
            'C001,CAP,100μF,Condensateur électrolytique,C14663\n'
            'U001,IC,ATmega328,Microcontrôleur 8-bit,C123456\n',
            encoding='utf-8'
        )
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', str(unicode_inv),
            '-o', str(output_file)
        ])
        
        # Should succeed with unicode
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
        
        # Read output and verify unicode preserved
        content = output_file.read_text(encoding='utf-8')
        # Just verify it can be read without encoding errors
        self.assertIn('Reference', content)  # Basic sanity check - BOM column


if __name__ == '__main__':
    import unittest
    unittest.main()
