#!/usr/bin/env python3
"""Test ProjectContext service."""

import tempfile
import unittest
from pathlib import Path

from jbom.services.project_context import ProjectContext


class TestProjectContext(unittest.TestCase):
    """Test ProjectContext service functionality."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jbom_project_context_"))

    def tearDown(self):
        """Clean up test files."""
        for p in self.tmpdir.iterdir():
            if p.is_file():
                p.unlink()

    def test_initialize_with_project_directory(self):
        """Test initializing ProjectContext with a project directory."""
        project_file = self.tmpdir / "test.kicad_pro"
        project_file.write_text("(kicad_pro (version 20211014))")

        schematic_file = self.tmpdir / "test.kicad_sch"
        schematic_file.write_text("(kicad_sch (version 20211123))")

        context = ProjectContext(self.tmpdir)

        self.assertEqual(context.project_directory, self.tmpdir)
        self.assertEqual(context.project_file, project_file)
        self.assertEqual(context.schematic_file, schematic_file)
        self.assertEqual(context.project_base_name, "test")

    def test_get_related_file_paths(self):
        """Test getting related file paths from base name."""
        project_file = self.tmpdir / "myproject.kicad_pro"
        project_file.write_text("(kicad_pro (version 20211014))")

        context = ProjectContext(self.tmpdir)

        # Test getting expected paths for related files
        expected_sch = self.tmpdir / "myproject.kicad_sch"
        expected_pcb = self.tmpdir / "myproject.kicad_pcb"

        self.assertEqual(context.get_expected_schematic_path(), expected_sch)
        self.assertEqual(context.get_expected_pcb_path(), expected_pcb)

    def test_resolve_hierarchical_schematics(self):
        """Test finding hierarchical schematic files."""
        # Create main schematic with hierarchical references
        main_sch = self.tmpdir / "main.kicad_sch"
        main_sch_content = """(kicad_sch (version 20211123)
  (sheet (at 50 50) (size 30 20)
    (property "Sheetname" "Power Supply")
    (property "Sheetfile" "power.kicad_sch")
  )
  (sheet (at 50 80) (size 30 20)
    (property "Sheetname" "MCU")
    (property "Sheetfile" "mcu.kicad_sch")
  )
)"""
        main_sch.write_text(main_sch_content)

        # Create hierarchical sheet files
        power_sch = self.tmpdir / "power.kicad_sch"
        power_sch.write_text("(kicad_sch (version 20211123))")

        mcu_sch = self.tmpdir / "mcu.kicad_sch"
        mcu_sch.write_text("(kicad_sch (version 20211123))")

        context = ProjectContext(self.tmpdir)
        hierarchical_files = context.get_hierarchical_schematic_files()

        self.assertIn(main_sch, hierarchical_files)
        self.assertIn(power_sch, hierarchical_files)
        self.assertIn(mcu_sch, hierarchical_files)

    def test_cross_file_intelligence(self):
        """Test cross-file relationships (sch <-> pcb)."""
        # Create project with both schematic and PCB
        project_file = self.tmpdir / "board.kicad_pro"
        project_file.write_text("(kicad_pro (version 20211014))")

        schematic_file = self.tmpdir / "board.kicad_sch"
        schematic_file.write_text("(kicad_sch (version 20211123))")

        pcb_file = self.tmpdir / "board.kicad_pcb"
        pcb_file.write_text("(kicad_pcb (version 20211014))")

        context = ProjectContext(self.tmpdir)

        # Test finding matching PCB for schematic
        matching_pcb = context.find_matching_pcb_for_schematic(schematic_file)
        self.assertEqual(matching_pcb, pcb_file)

        # Test finding matching schematic for PCB
        matching_sch = context.find_matching_schematic_for_pcb(pcb_file)
        self.assertEqual(matching_sch, schematic_file)

    def test_no_project_files_raises_error(self):
        """Test that missing project files raise appropriate error."""
        with self.assertRaises(ValueError) as cm:
            ProjectContext(self.tmpdir)

        self.assertIn("No project files found", str(cm.exception))

    def test_project_metadata_extraction(self):
        """Test extracting metadata from project files."""
        project_content = """(kicad_project (version 1)
  (general
    (title "Test Project")
    (revision "1.0")
    (date "2023-01-01")
  )
)"""
        project_file = self.tmpdir / "test.kicad_pro"
        project_file.write_text(project_content)

        context = ProjectContext(self.tmpdir)
        metadata = context.get_project_metadata()

        self.assertIsInstance(metadata, dict)
        # Basic metadata should include base project info
        self.assertIn("project_base_name", metadata)
        self.assertEqual(metadata["project_base_name"], "test")

    def test_suggest_missing_files(self):
        """Test suggesting missing related files."""
        # Only create schematic, missing PCB
        schematic_file = self.tmpdir / "test.kicad_sch"
        schematic_file.write_text("(kicad_sch (version 20211123))")

        context = ProjectContext(self.tmpdir)
        suggestions = context.suggest_missing_files()

        self.assertIsInstance(suggestions, dict)
        # Should suggest creating matching PCB file
        expected_pcb = self.tmpdir / "test.kicad_pcb"
        self.assertIn("suggested_pcb", suggestions)
        self.assertEqual(suggestions["suggested_pcb"], expected_pcb)


if __name__ == "__main__":
    unittest.main()
