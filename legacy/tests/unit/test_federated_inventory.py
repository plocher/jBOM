"""
Tests for federated inventory loading (Step 3.5).
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from jbom.loaders.inventory import InventoryLoader


class TestFederatedInventory(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_load_multiple_csv_files(self):
        """Test loading items from two different CSV files."""
        # Create first CSV
        csv1 = Path(self.test_dir) / "inv1.csv"
        with open(csv1, "w") as f:
            f.write("IPN,Category,Value\n")
            f.write("100-01,Resistor,10k\n")

        # Create second CSV
        csv2 = Path(self.test_dir) / "inv2.csv"
        with open(csv2, "w") as f:
            f.write("IPN,Category,Value\n")
            f.write("200-01,Capacitor,100nF\n")

        loader = InventoryLoader([csv1, csv2])
        items, fields = loader.load()

        self.assertEqual(len(items), 2)
        ipns = sorted([i.ipn for i in items])
        self.assertEqual(ipns, ["100-01", "200-01"])

        # Check source tracking
        item1 = next(i for i in items if i.ipn == "100-01")
        self.assertEqual(item1.source, "CSV")
        self.assertEqual(str(item1.source_file), str(csv1))

    def test_load_jlc_private_export(self):
        """Test loading a real JLC Private Inventory export."""
        # This test relies on the example file being present in the repo
        example_path = Path("examples/Parts Inventory on JLCPCB.xlsx")
        if not example_path.exists():
            self.skipTest("JLC example file not found")

        loader = InventoryLoader(example_path)
        items, fields = loader.load()

        self.assertTrue(len(items) > 0, "Should load items from JLC export")

        # Check a sample item
        item = items[0]
        self.assertEqual(item.source, "JLC-Private")
        self.assertEqual(str(item.source_file), str(example_path))
        self.assertTrue(
            item.lcsc.startswith("C"), f"LCSC ID should start with C, got {item.lcsc}"
        )
        self.assertEqual(item.ipn, item.lcsc, "IPN should default to LCSC ID")
        self.assertTrue(item.category, "Category should be populated")


if __name__ == "__main__":
    unittest.main()
