"""
Functional tests for back-annotation (Step 4).
"""
import sys
import csv
import unittest
from pathlib import Path

# Ensure tests directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from .test_functional_base import FunctionalTestBase
from jbom.processors.annotator import SchematicAnnotator

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


class TestBackAnnotation(FunctionalTestBase):
    def setUp(self):
        super().setUp()
        self.sch_path = self.output_dir / "test.kicad_sch"
        with open(self.sch_path, "w") as f:
            f.write(TEST_SCHEMATIC)

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
        self.assert_file_contains(self.sch_path, '"LCSC" "C12345"')
        self.assert_file_contains(self.sch_path, '"Value" "10k 1%"')
        self.assert_file_contains(self.sch_path, '"Manufacturer" "Yageo"')

    def test_annotate_command(self):
        """Test full jbom annotate command workflow."""
        # Create an inventory file
        inv_path = self.output_dir / "inventory.csv"
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

        rc, stdout, stderr = self.run_jbom(
            ["annotate", str(self.sch_path), "-i", str(inv_path)]
        )

        self.assertEqual(rc, 0)

        # Verify file updated
        self.assert_file_contains(self.sch_path, '"LCSC" "C99999"')
        self.assert_file_contains(self.sch_path, '"Value" "10k 1%"')


if __name__ == "__main__":
    unittest.main()
