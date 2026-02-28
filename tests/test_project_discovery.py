#!/usr/bin/env python3
"""Test ProjectDiscovery service."""

import tempfile
import unittest
from pathlib import Path

from jbom.services.project_discovery import ProjectDiscovery


class TestProjectDiscovery(unittest.TestCase):
    """Test ProjectDiscovery service functionality."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jbom_project_discovery_"))

    def tearDown(self):
        """Clean up test files."""
        for p in self.tmpdir.iterdir():
            if p.is_file():
                p.unlink()

    def test_empty_directory_requires_project_file(self):
        """KiCad 6+ projects must contain exactly one *.kicad_pro."""
        discovery = ProjectDiscovery()

        with self.assertRaises(ValueError) as cm:
            discovery.find_project_file(self.tmpdir)
        self.assertIn("No project files found", str(cm.exception))

        self.assertIsNone(discovery.find_schematic_file(self.tmpdir))
        self.assertIsNone(discovery.find_pcb_file(self.tmpdir))

    def test_find_kicad_pro_project_file(self):
        """Test finding .kicad_pro project files."""
        project_file = self.tmpdir / "test_project.kicad_pro"
        project_file.write_text("(kicad_pro (version 20211014))")

        discovery = ProjectDiscovery()
        found = discovery.find_project_file(self.tmpdir)

        self.assertEqual(found, project_file)

    def test_multiple_projects_raises_exception(self):
        """Test that multiple project files raise an exception."""
        (self.tmpdir / "project1.kicad_pro").write_text(
            "(kicad_pro (version 20211014))"
        )
        (self.tmpdir / "project2.kicad_pro").write_text(
            "(kicad_pro (version 20211014))"
        )

        discovery = ProjectDiscovery()

        with self.assertRaises(ValueError) as cm:
            discovery.find_project_file(self.tmpdir)

        self.assertIn("Multiple project files found", str(cm.exception))

    def test_discover_project_files_returns_all(self):
        """Test discovering all project files at once."""
        project = self.tmpdir / "test.kicad_pro"
        project.write_text("(kicad_pro (version 20211014))")

        schematic = self.tmpdir / "test.kicad_sch"
        schematic.write_text("(kicad_sch (version 20211123))")

        pcb = self.tmpdir / "test.kicad_pcb"
        pcb.write_text("(kicad_pcb (version 20211014))")

        discovery = ProjectDiscovery()
        result = discovery.discover_project_files(self.tmpdir)

        self.assertEqual(result.project_file, project)
        self.assertEqual(result.schematic_file, schematic)
        self.assertEqual(result.pcb_file, pcb)

    def test_find_schematic_file(self):
        """Test finding schematic files."""
        schematic = self.tmpdir / "test.kicad_sch"
        schematic.write_text("(kicad_sch (version 20211123))")

        discovery = ProjectDiscovery()
        found = discovery.find_schematic_file(self.tmpdir)

        self.assertEqual(found, schematic)

    def test_find_pcb_file(self):
        """Test finding PCB files."""
        pcb = self.tmpdir / "test.kicad_pcb"
        pcb.write_text("(kicad_pcb (version 20211014))")

        discovery = ProjectDiscovery()
        found = discovery.find_pcb_file(self.tmpdir)

        self.assertEqual(found, pcb)

    def test_handle_autosave_files_with_warning(self):
        """Test that autosave files are found with warning."""
        autosave = self.tmpdir / "_autosave-test.kicad_sch"
        autosave.write_text("(kicad_sch (version 20211123))")

        discovery = ProjectDiscovery()
        found = discovery.find_schematic_file(self.tmpdir)

        self.assertEqual(found, autosave)

    def test_prefer_normal_over_autosave_files(self):
        """Test that normal files are preferred over autosave files."""
        autosave = self.tmpdir / "_autosave-test.kicad_sch"
        autosave.write_text("(kicad_sch (version 20211123))")

        normal = self.tmpdir / "normal.kicad_sch"
        normal.write_text("(kicad_sch (version 20211123))")

        discovery = ProjectDiscovery()
        found = discovery.find_schematic_file(self.tmpdir)

        self.assertEqual(found, normal)


if __name__ == "__main__":
    unittest.main()
