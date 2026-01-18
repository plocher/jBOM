import tempfile
from pathlib import Path
import unittest

from jbom.cli.discovery import (
    find_project,
    find_pcb,
    find_schematic,
    find_project_and_pcb,
    default_output_name,
)


class TestDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jbom_discovery_"))

    def tearDown(self):
        # best-effort cleanup of files only (no directories recursion)
        for p in self.tmpdir.iterdir():
            if p.is_file():
                p.unlink()

    def test_no_files(self):
        self.assertIsNone(find_project(self.tmpdir))
        self.assertIsNone(find_pcb(self.tmpdir))
        self.assertIsNone(find_schematic(self.tmpdir))

    def test_pcb_only(self):
        pcb = self.tmpdir / "board.kicad_pcb"
        pcb.write_text("(kicad_pcb)\n")
        self.assertEqual(find_pcb(self.tmpdir), pcb)
        proj, found_pcb = find_project_and_pcb(self.tmpdir)
        self.assertIsNone(proj)
        self.assertEqual(found_pcb, pcb)

    def test_project_and_output_name(self):
        pcb = self.tmpdir / "board.kicad_pcb"
        pcb.write_text("(kicad_pcb)\n")
        project = self.tmpdir / "proj.kicad_pro"
        project.write_text("(kicad_pro)\n")
        self.assertEqual(find_project(self.tmpdir), project)
        out = default_output_name(self.tmpdir, project, pcb, "pos.csv")
        self.assertEqual(out.name, "proj.pos.csv")

    def test_legacy_project(self):
        legacy = self.tmpdir / "legacy.pro"
        legacy.write_text("legacy\n")
        self.assertEqual(find_project(self.tmpdir), legacy)

    def test_directory_matching_preferred(self):
        # Create two pcb files, prefer one whose stem matches directory name
        (self.tmpdir / f"{self.tmpdir.name}.kicad_pcb").write_text("(kicad_pcb)\n")
        (self.tmpdir / "other.kicad_pcb").write_text("(kicad_pcb)\n")
        found = find_pcb(self.tmpdir)
        self.assertEqual(found.stem, self.tmpdir.name)

    def test_autosave_only_warns_and_picks(self):
        # Only autosave files available
        (self.tmpdir / "_autosave-foo.kicad_pcb").write_text("(kicad_pcb)\n")
        found = find_pcb(self.tmpdir)
        self.assertIsNotNone(found)
        self.assertTrue(found.name.startswith("_autosave-"))


if __name__ == "__main__":
    unittest.main()
