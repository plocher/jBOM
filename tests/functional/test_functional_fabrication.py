"""
Functional tests for Fabrication Logic.
Covering: PCBWay column mapping and PN selection.
"""
from jbom.common.types import Component, InventoryItem
from jbom.generators.bom import BOMGenerator
from jbom.processors.inventory_matcher import InventoryMatcher
from jbom.common.generator import GeneratorOptions
from .test_functional_base import FunctionalTestBase


class TestFunctionalFabrication(FunctionalTestBase):
    def test_pcbway_column_mapping(self):
        """Test: Verify PCBWay BOM has correct headers."""
        # Setup Component and Inventory
        comp = Component("R1", "Device:R", "10k", "Resistor_SMD:R_0603_1608Metric")

        item = InventoryItem(
            ipn="RES-10K",
            keywords="resistor, 10k",
            category="Resistor",
            description="10k 1%",
            smd="Yes",
            value="10k",
            type="Resistor",
            tolerance="1%",
            voltage="",
            amperage="",
            wattage="",
            lcsc="",
            manufacturer="Yageo",
            mfgpn="RC0603-10K",
            datasheet="",
            distributor="DigiKey",
            distributor_part_number="311-10K-ND",
            package="0603",
        )

        matcher = InventoryMatcher(None)
        matcher.set_inventory([item], ["distributor_part_number", "mfgpn"])

        # Generate for PCBWay
        options = GeneratorOptions(verbose=False)
        options.fabricator = "pcbway"

        gen = BOMGenerator(matcher, options)
        gen.components = [comp]  # Inject

        entries, _ = gen.process([comp])

        # Write to file
        out = self.output_dir / "pcbway.csv"
        gen.write_csv(entries, out, gen._get_default_fields())

        # Verify Headers
        rows = self.assert_csv_valid(out)
        headers = rows[0]

        expected = [
            "Designator",
            "Quantity",
            "Value",
            "Comment",
            "Package",
            "Distributor Part Number",
        ]
        self.assertEqual(headers, expected)

    def test_pcbway_pn_selection(self):
        """Test: Verify PCBWay uses Distributor PN if available."""
        # Setup as above
        comp = Component("R1", "Device:R", "10k", "Resistor_SMD:R_0603_1608Metric")
        item = InventoryItem(
            ipn="RES-10K",
            keywords="resistor, 10k",
            category="Resistor",
            description="10k 1%",
            smd="Yes",
            value="10k",
            type="Resistor",
            tolerance="1%",
            voltage="",
            amperage="",
            wattage="",
            lcsc="",
            manufacturer="Yageo",
            mfgpn="RC0603-10K",
            datasheet="",
            distributor="DigiKey",
            distributor_part_number="311-10K-ND",
            package="0603",
        )

        matcher = InventoryMatcher(None)
        matcher.set_inventory([item], [])

        options = GeneratorOptions(verbose=False)
        options.fabricator = "pcbway"
        gen = BOMGenerator(matcher, options)
        gen.components = [comp]

        entries, _ = gen.process([comp])

        # The BOMEntry should contain the fabricator PN
        # For PCBWayFabricator, get_part_number() returns distributor_part_number
        self.assertEqual(entries[0].fabricator_part_number, "311-10K-ND")
        self.assertEqual(
            entries[0].fabricator, "PCBWay"
        )  # Actually "PCBWay" is the name of the Fab class? No, get_name returns "PCBWay"
