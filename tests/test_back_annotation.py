"""
Tests for back-annotation (Step 4).
"""
import unittest
import tempfile
import shutil
import csv
from pathlib import Path
from jbom.processors.annotator import SchematicAnnotator
from jbom.cli.annotate_command import AnnotateCommand
import argparse

# Minimal schematic with one component
TEST_SCHEMATIC = """(kicad_sch (version 20211014) (generator eeschema)
  (uuid "00000000-0000-0000-0000-000000000000")
  (paper "A4")
  (symbol (lib_id "Device:R") (at 100 100 0) (unit 1)
    (in_bom yes) (on_board yes)
    (uuid "12345678-1234-1234-1234-1234567890ab")
    (property "Reference" "R1" (id 0) (at 100 90 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "10k" (id 1) (at 100 110 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" "R_0603" (id 2) (at 100 110 0)
      (effects (font (size 1.27 1.27)))
    )
  )
)"""


class TestBackAnnotation(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.sch_path = Path(self.test_dir) / "test.kicad_sch"
        with open(self.sch_path, "w") as f:
            f.write(TEST_SCHEMATIC)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_annotator_update(self):
        """Test SchematicAnnotator updates component directly."""
        annotator = SchematicAnnotator(self.sch_path)
        annotator.load()

        # Update R1 (by UUID)
        uuid = "12345678-1234-1234-1234-1234567890ab"
        updates = {"LCSC": "C12345", "Value": "10k 1%", "Manufacturer": "Yageo"}

        found = annotator.update_component(uuid, updates)
        self.assertTrue(found, "Should find component by UUID")
        self.assertTrue(annotator.modified)

        annotator.save()

        # Verify changes in file
        with open(self.sch_path, "r") as f:
            content = f.read()

        self.assertIn('"LCSC" "C12345"', content)
        self.assertIn('"Value" "10k 1%"', content)
        self.assertIn('"Manufacturer" "Yageo"', content)

    def test_annotate_command(self):
        """Test full jbom annotate command workflow."""
        # Create an inventory file
        inv_path = Path(self.test_dir) / "inventory.csv"
        with open(inv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["IPN", "Category", "Value", "LCSC", "UUID"])
            # Update R1
            writer.writerow(
                [
                    "R1_0603",
                    "RES",
                    "10k 1%",
                    "C99999",
                    "12345678-1234-1234-1234-1234567890ab",
                ]
            )

        cmd = AnnotateCommand()
        args = argparse.Namespace(
            project=str(self.sch_path), inventory=str(inv_path), dry_run=False
        )

        rc = cmd.execute(args)
        self.assertEqual(rc, 0)

        # Verify file updated
        with open(self.sch_path, "r") as f:
            content = f.read()

        self.assertIn('"LCSC" "C99999"', content)
        self.assertIn('"Value" "10k 1%"', content)


if __name__ == "__main__":
    unittest.main()
