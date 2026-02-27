import unittest
from jbom.common.fabricators import GenericFabricator
from jbom.common.types import InventoryItem


class TestGenericFabricator(unittest.TestCase):
    def setUp(self):
        self.fab = GenericFabricator()

    def test_get_part_number_mfgpn(self):
        item = InventoryItem(
            ipn="1",
            category="R",
            keywords="",
            description="",
            smd="",
            value="10k",
            type="",
            tolerance="",
            voltage="",
            amperage="",
            wattage="",
            lcsc="",
            manufacturer="Yageo",
            mfgpn="RC0603FR-0710KL",
            datasheet="",
        )
        self.assertEqual(self.fab.get_part_number(item), "RC0603FR-0710KL")

    def test_get_part_number_lcsc_fallback(self):
        item = InventoryItem(
            ipn="1",
            category="R",
            keywords="",
            description="",
            smd="",
            value="10k",
            type="",
            tolerance="",
            voltage="",
            amperage="",
            wattage="",
            lcsc="C12345",
            manufacturer="Yageo",
            mfgpn="",
            datasheet="",
        )
        self.assertEqual(self.fab.get_part_number(item), "C12345")

    def test_get_name_manufacturer(self):
        item = InventoryItem(
            ipn="1",
            category="R",
            keywords="",
            description="",
            smd="",
            value="10k",
            type="",
            tolerance="",
            voltage="",
            amperage="",
            wattage="",
            lcsc="",
            manufacturer="Yageo",
            mfgpn="",
            datasheet="",
        )
        self.assertEqual(self.fab.get_name(item), "Yageo")

    def test_get_name_default(self):
        item = InventoryItem(
            ipn="1",
            category="R",
            keywords="",
            description="",
            smd="",
            value="10k",
            type="",
            tolerance="",
            voltage="",
            amperage="",
            wattage="",
            lcsc="",
            manufacturer="",
            mfgpn="",
            datasheet="",
        )
        self.assertEqual(self.fab.get_name(item), "Generic")
