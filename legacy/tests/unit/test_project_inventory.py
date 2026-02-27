import unittest
from jbom.common.types import Component
from jbom.loaders.project_inventory import ProjectInventoryLoader


class TestProjectInventoryLoader(unittest.TestCase):
    def test_load_inventory(self):
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10k",
                footprint="Resistor_SMD:R_0603_1608Metric",
                uuid="",
                properties={"Tolerance": "1%"},
            ),
            Component(
                reference="R2",
                lib_id="Device:R",
                value="10k",
                footprint="Resistor_SMD:R_0603_1608Metric",
                uuid="",
                properties={"Tolerance": "1%"},
            ),
            Component(
                reference="C1",
                lib_id="Device:C",
                value="100nF",
                footprint="Capacitor_SMD:C_0603_1608Metric",
                uuid="",
                properties={"Voltage": "50V"},
            ),
        ]
        loader = ProjectInventoryLoader(components)
        inventory, fields = loader.load()

        # Should have 2 items (R1/R2 grouped, C1 separate)
        self.assertEqual(len(inventory), 2)

        # Check Resistor item
        r_item = next((i for i in inventory if i.category == "RES"), None)
        self.assertIsNotNone(r_item)
        self.assertEqual(r_item.value, "10k")
        # Package extraction logic depends on ProjectInventoryLoader implementation
        # "0603" is in SMD_PACKAGES, so it should be extracted
        self.assertEqual(r_item.package, "0603")
        self.assertEqual(r_item.tolerance, "1%")

        # Check Capacitor item
        c_item = next((i for i in inventory if i.category == "CAP"), None)
        self.assertIsNotNone(c_item)
        self.assertEqual(c_item.value, "100nF")
        self.assertEqual(c_item.voltage, "50V")

        # Check fields
        self.assertIn("Tolerance", fields)
        self.assertIn("Voltage", fields)
        self.assertIn("IPN", fields)
        self.assertIn("Value", fields)

    def test_grouping_different_values(self):
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10k",
                footprint="R_0603",
                uuid="",
                properties={},
            ),
            Component(
                reference="R2",
                lib_id="Device:R",
                value="20k",
                footprint="R_0603",
                uuid="",
                properties={},
            ),
        ]
        loader = ProjectInventoryLoader(components)
        inventory, _ = loader.load()
        self.assertEqual(len(inventory), 2)

    def test_grouping_different_footprints(self):
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10k",
                footprint="R_0603",
                uuid="",
                properties={},
            ),
            Component(
                reference="R2",
                lib_id="Device:R",
                value="10k",
                footprint="R_0805",
                uuid="",
                properties={},
            ),
        ]
        loader = ProjectInventoryLoader(components)
        inventory, _ = loader.load()
        self.assertEqual(len(inventory), 2)

    def test_grouping_different_properties(self):
        """Test that components with different key properties are not grouped."""
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10k",
                footprint="R_0603",
                uuid="",
                properties={"Tolerance": "1%"},
            ),
            Component(
                reference="R2",
                lib_id="Device:R",
                value="10k",
                footprint="R_0603",
                uuid="",
                properties={"Tolerance": "5%"},
            ),
        ]
        loader = ProjectInventoryLoader(components)
        inventory, _ = loader.load()
        self.assertEqual(len(inventory), 2)

        # Verify tolerances are preserved
        tols = sorted([item.tolerance for item in inventory])
        self.assertEqual(tols, ["1%", "5%"])
