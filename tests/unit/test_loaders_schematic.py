#!/usr/bin/env python3
"""Unit tests for schematic loading and hierarchical support."""
import unittest
import tempfile
import sys
import io
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from jbom.common.types import Component, InventoryItem
from jbom.common.utils import (
    find_best_schematic,
    is_hierarchical_schematic,
    extract_sheet_files,
    process_hierarchical_schematic,
)


class TestSchematicLoader(unittest.TestCase):
    """Test KiCad schematic parsing (basic functionality)"""

    def test_component_creation(self):
        """Test Component dataclass creation"""
        comp = Component(
            reference="R1",
            lib_id="Device:R",
            value="330R",
            footprint="Resistor_SMD:R_0603_1608Metric",
            properties={"Tolerance": "5%", "W": "0.1W"},
        )

        self.assertEqual(comp.reference, "R1")
        self.assertEqual(comp.lib_id, "Device:R")
        self.assertEqual(comp.value, "330R")
        self.assertEqual(comp.properties["Tolerance"], "5%")
        self.assertTrue(comp.in_bom)
        self.assertFalse(comp.dnp)

    def test_inventory_item_creation(self):
        """Test InventoryItem dataclass creation"""
        item = InventoryItem(
            ipn="R001",
            keywords="resistor",
            category="RES",
            description="330Ω 5% 0603 resistor",
            smd="Yes",
            value="330R",
            type="Resistor",
            tolerance="5%",
            voltage="75V",
            amperage="",
            wattage="0.1W",
            lcsc="C25231",
            manufacturer="UNI-ROYAL",
            mfgpn="0603WAJ0331T5E",
            datasheet="https://example.com",
            package="0603",
            priority=1,
        )

        self.assertEqual(item.ipn, "R001")
        self.assertEqual(item.category, "RES")
        self.assertEqual(item.value, "330R")
        self.assertEqual(item.priority, 1)


class TestHierarchicalSupport(unittest.TestCase):
    """Test hierarchical schematic support functionality"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name) / "test_project"
        self.project_dir.mkdir()

        # Create test inventory
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        csv_content = [
            "IPN,Name,Category,Package,Value,LCSC,Manufacturer,MFGPN,Description,Priority",
            "R001,330R,RES,0603,330R,C25231,UNI-ROYAL,0603WAJ0331T5E,330Ω 5% 0603,1",
            "C001,100nF,CAP,0603,100nF,C14663,YAGEO,CC0603KRX7R9BB104,100nF X7R 0603,1",
        ]
        self.temp_inv.write("\n".join(csv_content))
        self.temp_inv.close()

    def tearDown(self):
        self.temp_dir.cleanup()
        Path(self.temp_inv.name).unlink()

    def create_hierarchical_root(self, filename="test_project.kicad_sch"):
        """Create a mock hierarchical root schematic file"""
        root_content = """(kicad_sch
    (version 20231120)
    (generator "eeschema")
    (generator_version "8.0")
    (uuid "test-root-uuid")
    (paper "A4")
    (lib_symbols)
    (sheet
        (at 25.4 25.4)
        (size 12.7 3.81)
        (property "Sheetname" "SubSheet1")
        (property "Sheetfile" "subsheet1.kicad_sch")
    )
    (sheet
        (at 45.4 25.4)
        (size 12.7 3.81)
        (property "Sheetname" "SubSheet2")
        (property "Sheetfile" "subsheet2.kicad_sch")
    )
)"""
        root_file = self.project_dir / filename
        root_file.write_text(root_content)
        return root_file

    def create_simple_schematic(
        self, filename="simple.kicad_sch", with_components=True
    ):
        """Create a mock simple schematic file"""
        if with_components:
            content = """(kicad_sch
    (version 20231120)
    (lib_symbols
        (symbol "Device:R" (properties...))
    )
    (symbol (lib_id "Device:R") (at 50 50 0) (unit 1)
        (in_bom yes) (on_board yes) (dnp no)
        (property "Reference" "R1" (at 52 50 0))
        (property "Value" "330R" (at 50 47 0))
        (property "Footprint" "PCM_SPCoast:0603-RES" (at 50 45 0))
    )
)"""
        else:
            content = """(kicad_sch
    (version 20231120)
    (lib_symbols)
)"""
        simple_file = self.project_dir / filename
        simple_file.write_text(content)
        return simple_file

    def test_is_hierarchical_schematic(self):
        """Test detection of hierarchical schematics"""
        # Create hierarchical schematic
        hierarchical_file = self.create_hierarchical_root()
        self.assertTrue(is_hierarchical_schematic(hierarchical_file))

        # Create simple schematic
        simple_file = self.create_simple_schematic("simple.kicad_sch")
        self.assertFalse(is_hierarchical_schematic(simple_file))

    def test_extract_sheet_files(self):
        """Test extraction of sheet file references"""
        hierarchical_file = self.create_hierarchical_root()
        sheet_files = extract_sheet_files(hierarchical_file)

        self.assertEqual(len(sheet_files), 2)
        self.assertIn("subsheet1.kicad_sch", sheet_files)
        self.assertIn("subsheet2.kicad_sch", sheet_files)

    def test_find_best_schematic_normal_file(self):
        """Test finding best schematic with normal files"""
        # Create files - should prefer directory-matching name
        self.create_simple_schematic("test_project.kicad_sch")
        self.create_simple_schematic("other.kicad_sch")

        best = find_best_schematic(self.project_dir)
        self.assertEqual(best.name, "test_project.kicad_sch")

    def test_find_best_schematic_hierarchical_priority(self):
        """Test that hierarchical schematics are preferred"""
        # Create hierarchical root and simple schematic
        self.create_hierarchical_root("test_project.kicad_sch")
        self.create_simple_schematic("simple.kicad_sch")

        best = find_best_schematic(self.project_dir)
        self.assertEqual(
            best.name, "test_project.kicad_sch"
        )  # Should prefer hierarchical root

    def test_find_best_schematic_autosave_warning(self):
        """Test autosave file handling with warning"""
        # Create only autosave file
        self.create_hierarchical_root("_autosave-test_project.kicad_sch")

        # Capture stdout to check for warning
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            best = find_best_schematic(self.project_dir)
            self.assertEqual(best.name, "_autosave-test_project.kicad_sch")

            # Check that warning was issued
            output = captured_output.getvalue()
            self.assertIn("WARNING", output)
            self.assertIn("autosave", output.lower())
        finally:
            sys.stdout = sys.__stdout__

    def test_process_hierarchical_schematic(self):
        """Test processing of hierarchical schematic files"""
        # Create hierarchical root
        root_file = self.create_hierarchical_root()

        # Create sub-sheets
        self.create_simple_schematic("subsheet1.kicad_sch")
        self.create_simple_schematic("subsheet2.kicad_sch")

        files_to_process = process_hierarchical_schematic(root_file, self.project_dir)

        # Should return root + 2 sub-sheets
        self.assertEqual(len(files_to_process), 3)
        file_names = [f.name for f in files_to_process]
        self.assertIn("test_project.kicad_sch", file_names)
        self.assertIn("subsheet1.kicad_sch", file_names)
        self.assertIn("subsheet2.kicad_sch", file_names)

    def test_process_hierarchical_missing_subsheet(self):
        """Test handling of missing sub-sheet files"""
        # Create hierarchical root but not sub-sheets
        root_file = self.create_hierarchical_root()

        # Capture stdout to check for warnings
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            files_to_process = process_hierarchical_schematic(
                root_file, self.project_dir
            )

            # Should still return root file even if sub-sheets missing
            self.assertEqual(len(files_to_process), 1)
            self.assertEqual(files_to_process[0].name, "test_project.kicad_sch")

            # Check for warning messages
            output = captured_output.getvalue()
            self.assertIn("Warning", output)
            self.assertIn("not found", output)
        finally:
            sys.stdout = sys.__stdout__

    def test_process_simple_schematic(self):
        """Test that simple schematics are processed normally"""
        simple_file = self.create_simple_schematic()
        files_to_process = process_hierarchical_schematic(simple_file, self.project_dir)

        # Should return only the single file
        self.assertEqual(len(files_to_process), 1)
        self.assertEqual(files_to_process[0].name, "simple.kicad_sch")


if __name__ == "__main__":
    unittest.main()
