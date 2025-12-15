#!/usr/bin/env python3
"""Functional tests for schematic edge cases."""
import sys
from pathlib import Path

# Ensure tests directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_functional_base import FunctionalTestBase


class TestSchematicEdgeCases(FunctionalTestBase):
    """Test edge cases in schematic processing."""
    
    def test_empty_schematic_no_components(self):
        """Empty schematic (no components) should produce empty BOM without error."""
        # Create empty schematic with minimal structure
        empty_proj = self.output_dir / 'empty_project'
        empty_proj.mkdir()
        empty_sch = empty_proj / 'empty.kicad_sch'
        
        # Minimal valid KiCad schematic with no components
        empty_sch.write_text(
            '(kicad_sch (version 20230121) (generator eeschema)\n'
            '  (uuid "00000000-0000-0000-0000-000000000000")\n'
            '  (paper "A4")\n'
            '  (lib_symbols)\n'
            '  (sheet_instances\n'
            '    (path "/" (page "1"))\n'
            '  )\n'
            ')\n'
        )
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(empty_proj),
            '-i', str(self.inventory_csv),
            '-o', str(output_file)
        ])
        
        # Should succeed with empty BOM
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
        
        # Validate CSV - should have headers but no data rows
        rows = self.assert_csv_valid(output_file)
        self.assertEqual(len(rows), 1, "Should only have header row")
        self.assertIn('Reference', rows[0])
    
    def test_component_with_no_value(self):
        """Component with empty value field should not crash."""
        proj = self.output_dir / 'no_value_project'
        proj.mkdir()
        sch = proj / 'test.kicad_sch'
        
        # Schematic with component that has empty value
        sch.write_text(
            '(kicad_sch (version 20230121) (generator eeschema)\n'
            '  (uuid "00000000-0000-0000-0000-000000000000")\n'
            '  (paper "A4")\n'
            '  (lib_symbols)\n'
            '  (symbol (lib_id "Device:R") (at 100 100 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes)\n'
            '    (property "Reference" "R1" (at 100 95 0))\n'
            '    (property "Value" "" (at 100 105 0))\n'
            '    (property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 100 110 0))\n'
            '  )\n'
            '  (sheet_instances\n'
            '    (path "/" (page "1"))\n'
            '  )\n'
            ')\n'
        )
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(proj),
            '-i', str(self.inventory_csv),
            '-o', str(output_file)
        ])
        
        # Should succeed
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
        
        # Validate CSV structure
        rows = self.assert_csv_valid(output_file)
        self.assertGreater(len(rows), 1, "Should have headers + R1")
    
    def test_component_with_special_characters_in_value(self):
        """Component value with special characters (quotes, commas) should be CSV-escaped."""
        proj = self.output_dir / 'special_chars_project'
        proj.mkdir()
        sch = proj / 'test.kicad_sch'
        
        # Component with special characters in value
        sch.write_text(
            '(kicad_sch (version 20230121) (generator eeschema)\n'
            '  (uuid "00000000-0000-0000-0000-000000000000")\n'
            '  (paper "A4")\n'
            '  (lib_symbols)\n'
            '  (symbol (lib_id "Device:R") (at 100 100 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes)\n'
            '    (property "Reference" "R1" (at 100 95 0))\n'
            '    (property "Value" "Test, with \\"quotes\\"" (at 100 105 0))\n'
            '    (property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 100 110 0))\n'
            '  )\n'
            '  (sheet_instances\n'
            '    (path "/" (page "1"))\n'
            '  )\n'
            ')\n'
        )
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(proj),
            '-i', str(self.inventory_csv),
            '-o', str(output_file)
        ])
        
        # Should succeed
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
        
        # Validate CSV can be parsed (special chars properly escaped)
        rows = self.assert_csv_valid(output_file)
        self.assertGreater(len(rows), 1, "Should have headers + data")
    
    def test_component_with_unicode_in_description(self):
        """Component with unicode characters should be handled correctly."""
        proj = self.output_dir / 'unicode_project'
        proj.mkdir()
        sch = proj / 'test.kicad_sch'
        
        # Component with unicode in description
        sch.write_text(
            '(kicad_sch (version 20230121) (generator eeschema)\n'
            '  (uuid "00000000-0000-0000-0000-000000000000")\n'
            '  (paper "A4")\n'
            '  (lib_symbols)\n'
            '  (symbol (lib_id "Device:R") (at 100 100 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes)\n'
            '    (property "Reference" "R1" (at 100 95 0))\n'
            '    (property "Value" "330Ω" (at 100 105 0))\n'
            '    (property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 100 110 0))\n'
            '    (property "Description" "Résistance ±5% 330Ω" (at 100 115 0))\n'
            '  )\n'
            '  (sheet_instances\n'
            '    (path "/" (page "1"))\n'
            '  )\n'
            ')\n',
            encoding='utf-8'
        )
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(proj),
            '-i', str(self.inventory_csv),
            '-o', str(output_file)
        ])
        
        # Should succeed
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
        
        # Read and verify unicode handling
        content = output_file.read_text(encoding='utf-8')
        self.assertIn('Reference', content)
    
    def test_dnp_components_excluded(self):
        """Components marked as DNP (Do Not Place) should be excluded from BOM."""
        proj = self.output_dir / 'dnp_project'
        proj.mkdir()
        sch = proj / 'test.kicad_sch'
        
        # Schematic with one normal and one DNP component
        sch.write_text(
            '(kicad_sch (version 20230121) (generator eeschema)\n'
            '  (uuid "00000000-0000-0000-0000-000000000000")\n'
            '  (paper "A4")\n'
            '  (lib_symbols)\n'
            '  (symbol (lib_id "Device:R") (at 100 100 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes)\n'
            '    (property "Reference" "R1" (at 100 95 0))\n'
            '    (property "Value" "100R" (at 100 105 0))\n'
            '    (property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 100 110 0))\n'
            '  )\n'
            '  (symbol (lib_id "Device:R") (at 100 120 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes) (dnp yes)\n'
            '    (property "Reference" "R2" (at 100 115 0))\n'
            '    (property "Value" "200R" (at 100 125 0))\n'
            '    (property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 100 130 0))\n'
            '  )\n'
            '  (sheet_instances\n'
            '    (path "/" (page "1"))\n'
            '  )\n'
            ')\n'
        )
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(proj),
            '-i', str(self.inventory_csv),
            '-o', str(output_file)
        ])
        
        # Should succeed
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
        
        # Check that only R1 is in BOM, not R2 (DNP)
        content = output_file.read_text(encoding='utf-8')
        self.assertIn('R1', content)
        self.assertNotIn('R2', content)
    
    def test_components_with_in_bom_no_excluded(self):
        """Components with in_bom=no should be excluded from BOM."""
        proj = self.output_dir / 'in_bom_no_project'
        proj.mkdir()
        sch = proj / 'test.kicad_sch'
        
        # Schematic with one normal and one in_bom=no component
        sch.write_text(
            '(kicad_sch (version 20230121) (generator eeschema)\n'
            '  (uuid "00000000-0000-0000-0000-000000000000")\n'
            '  (paper "A4")\n'
            '  (lib_symbols)\n'
            '  (symbol (lib_id "Device:R") (at 100 100 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes)\n'
            '    (property "Reference" "R1" (at 100 95 0))\n'
            '    (property "Value" "100R" (at 100 105 0))\n'
            '    (property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 100 110 0))\n'
            '  )\n'
            '  (symbol (lib_id "power:GND") (at 100 120 0) (unit 1)\n'
            '    (in_bom no) (on_board yes)\n'
            '    (property "Reference" "#PWR01" (at 100 115 0))\n'
            '    (property "Value" "GND" (at 100 125 0))\n'
            '    (property "Footprint" "" (at 100 130 0))\n'
            '  )\n'
            '  (sheet_instances\n'
            '    (path "/" (page "1"))\n'
            '  )\n'
            ')\n'
        )
        
        output_file = self.output_dir / 'bom.csv'
        rc, stdout, stderr = self.run_jbom([
            'bom', str(proj),
            '-i', str(self.inventory_csv),
            '-o', str(output_file)
        ])
        
        # Should succeed
        self.assertEqual(rc, 0)
        self.assertTrue(output_file.exists())
        
        # Check that only R1 is in BOM, not #PWR01
        content = output_file.read_text(encoding='utf-8')
        self.assertIn('R1', content)
        self.assertNotIn('#PWR', content)
        self.assertNotIn('GND', content)


if __name__ == '__main__':
    import unittest
    unittest.main()
