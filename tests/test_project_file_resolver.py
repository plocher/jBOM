#!/usr/bin/env python3
"""Test ProjectFileResolver service."""

import tempfile
import unittest
from pathlib import Path

from jbom.services.project_file_resolver import ProjectFileResolver


class TestProjectFileResolver(unittest.TestCase):
    """Test ProjectFileResolver service functionality."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jbom_file_resolver_"))

    def tearDown(self):
        """Clean up test files."""
        for p in self.tmpdir.iterdir():
            if p.is_file():
                p.unlink()

    def test_resolve_explicit_schematic_file(self):
        """Test resolving explicit .kicad_sch file paths (backward compatibility)."""
        schematic = self.tmpdir / "board.kicad_sch"
        schematic.write_text("(kicad_sch (version 20211123))")

        resolver = ProjectFileResolver()
        result = resolver.resolve_input(str(schematic))

        self.assertEqual(result.input_type, "explicit_file")
        # Use resolved paths to handle macOS symlink differences
        self.assertEqual(result.resolved_path, schematic.resolve())
        self.assertTrue(result.is_schematic)
        self.assertFalse(result.is_pcb)

    def test_resolve_explicit_pcb_file(self):
        """Test resolving explicit .kicad_pcb file paths."""
        pcb = self.tmpdir / "board.kicad_pcb"
        pcb.write_text("(kicad_pcb (version 20211014))")

        resolver = ProjectFileResolver()
        result = resolver.resolve_input(str(pcb))

        self.assertEqual(result.input_type, "explicit_file")
        self.assertEqual(result.resolved_path, pcb.resolve())
        self.assertFalse(result.is_schematic)
        self.assertTrue(result.is_pcb)

    def test_resolve_current_directory(self):
        """Test resolving current directory '.' input."""
        schematic = self.tmpdir / "project.kicad_sch"
        schematic.write_text("(kicad_sch (version 20211123))")

        # Change to test directory for this test
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(self.tmpdir)

            resolver = ProjectFileResolver()
            result = resolver.resolve_input(".")

            self.assertEqual(result.input_type, "directory")
            self.assertEqual(result.resolved_path, schematic.resolve())
            self.assertTrue(result.is_schematic)
            self.assertIsNotNone(result.project_context)
        finally:
            os.chdir(original_cwd)

    def test_resolve_project_directory_path(self):
        """Test resolving project directory paths."""
        project = self.tmpdir / "test.kicad_pro"
        project.write_text("(kicad_pro (version 20211014))")

        schematic = self.tmpdir / "test.kicad_sch"
        schematic.write_text("(kicad_sch (version 20211123))")

        resolver = ProjectFileResolver()
        result = resolver.resolve_input(str(self.tmpdir))

        self.assertEqual(result.input_type, "directory")
        self.assertEqual(result.resolved_path, schematic.resolve())
        self.assertTrue(result.is_schematic)
        self.assertIsNotNone(result.project_context)
        self.assertEqual(result.project_context.project_base_name, "test")

    def test_resolve_base_name_input(self):
        """Test resolving project base name inputs."""
        project = self.tmpdir / "myboard.kicad_pro"
        project.write_text("(kicad_pro (version 20211014))")

        schematic = self.tmpdir / "myboard.kicad_sch"
        schematic.write_text("(kicad_sch (version 20211123))")

        # Change to test directory for base name resolution
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(self.tmpdir)

            resolver = ProjectFileResolver()
            result = resolver.resolve_input("myboard")

            self.assertEqual(result.input_type, "base_name")
            self.assertEqual(result.resolved_path, schematic.resolve())
            self.assertTrue(result.is_schematic)
            self.assertIsNotNone(result.project_context)
        finally:
            os.chdir(original_cwd)

    def test_resolve_pcb_input_returns_pcb(self):
        """Test that resolver can return PCB files when appropriate."""
        pcb = self.tmpdir / "test.kicad_pcb"
        pcb.write_text("(kicad_pcb (version 20211014))")

        resolver = ProjectFileResolver(prefer_pcb=True)
        result = resolver.resolve_input(str(self.tmpdir))

        self.assertEqual(result.input_type, "directory")
        self.assertEqual(result.resolved_path, pcb.resolve())
        self.assertTrue(result.is_pcb)

    def test_resolve_cross_file_intelligence(self):
        """Test cross-file intelligence (sch -> pcb, pcb -> sch)."""
        schematic = self.tmpdir / "board.kicad_sch"
        schematic.write_text("(kicad_sch (version 20211123))")

        pcb = self.tmpdir / "board.kicad_pcb"
        pcb.write_text("(kicad_pcb (version 20211014))")

        resolver = ProjectFileResolver()
        result = resolver.resolve_input(str(schematic))

        # Should find matching PCB
        matching_pcb = result.get_matching_pcb()
        self.assertEqual(matching_pcb, pcb.resolve())

    def test_error_for_missing_files(self):
        """Test appropriate error messages for missing files."""
        nonexistent = self.tmpdir / "nonexistent.kicad_sch"

        resolver = ProjectFileResolver()

        with self.assertRaises(FileNotFoundError) as cm:
            resolver.resolve_input(str(nonexistent))

        self.assertIn("File not found", str(cm.exception))

    def test_error_for_empty_directory(self):
        """Test error message for directory with no KiCad files."""
        resolver = ProjectFileResolver()

        with self.assertRaises(ValueError) as cm:
            resolver.resolve_input(str(self.tmpdir))

        self.assertIn("No project files found", str(cm.exception))

    def test_helpful_suggestions(self):
        """Test that resolver provides helpful suggestions for common mistakes."""
        # Create PCB file but user asks for schematic
        pcb = self.tmpdir / "board.kicad_pcb"
        pcb.write_text("(kicad_pcb (version 20211014))")

        resolver = ProjectFileResolver()
        result = resolver.resolve_input(str(self.tmpdir))

        # Should find PCB and suggest it's available
        self.assertEqual(result.resolved_path, pcb.resolve())

        # Should indicate schematic is missing but PCB is available
        suggestions = result.get_suggestions()
        self.assertIn("schematic", suggestions)

    def test_hierarchical_schematic_resolution(self):
        """Test resolution of hierarchical schematics."""
        # Create main schematic with hierarchical sheets
        main_sch = self.tmpdir / "main.kicad_sch"
        main_sch_content = """(kicad_sch (version 20211123)
  (sheet (at 50 50) (size 30 20)
    (property "Sheetname" "Power Supply")
    (property "Sheetfile" "power.kicad_sch")
  )
)"""
        main_sch.write_text(main_sch_content)

        power_sch = self.tmpdir / "power.kicad_sch"
        power_sch.write_text("(kicad_sch (version 20211123))")

        resolver = ProjectFileResolver()
        result = resolver.resolve_input(str(self.tmpdir))

        # Should resolve to main schematic
        self.assertEqual(result.resolved_path, main_sch.resolve())

        # Should provide access to all hierarchical files
        hierarchical_files = result.get_hierarchical_files()
        self.assertIn(main_sch.resolve(), hierarchical_files)
        self.assertIn(power_sch.resolve(), hierarchical_files)


if __name__ == "__main__":
    unittest.main()
