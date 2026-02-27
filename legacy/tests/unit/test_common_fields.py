#!/usr/bin/env python3
"""Unit tests for field normalization, parsing, and constants."""
import unittest
import tempfile
import csv
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from jbom.common.types import Component
from jbom.processors.inventory_matcher import InventoryMatcher
from jbom.generators.bom import BOMGenerator
from jbom.common.constants import (
    ComponentType,
    DiagnosticIssue,
    CommonFields,
    ScoreWeights,
)


class TestFieldArgumentParsing(unittest.TestCase):
    """Test --fields argument parsing with preset expansion"""

    def setUp(self):
        """Create a matcher with some test inventory for field validation"""
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        csv_writer = csv.DictWriter(
            self.temp_inv,
            fieldnames=["IPN", "Category", "Package", "Value", "LCSC", "Priority"],
        )
        csv_writer.writeheader()
        csv_writer.writerow(
            {
                "IPN": "R001",
                "Category": "RES",
                "Package": "0603",
                "Value": "330R",
                "LCSC": "C25231",
                "Priority": "1",
            }
        )
        self.temp_inv.close()
        self.matcher = InventoryMatcher(Path(self.temp_inv.name))

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_parse_jlc_preset(self):
        """Test expanding +jlc preset using BOMGenerator context"""
        from jbom.generators.bom import BOMGenerator
        from jbom.api import BOMOptions
        from jbom.common.config_fabricators import reload_fabricators
        from jbom.common.config import reload_config

        # Ensure config environment is clean/loaded
        reload_config()
        reload_fabricators()

        # Create generator with JLC fabricator
        opts = BOMOptions(fabricator="jlc")
        # We need a matcher, but for field parsing it doesn't need to be fully populated with real data
        # beyond what setup provides
        gen = BOMGenerator(self.matcher, opts)

        available_fields = {
            "reference": "Standard BOM field",
            "quantity": "Standard BOM field",
            "lcsc": "Standard BOM field",
            "value": "Standard BOM field",
            "footprint": "Standard BOM field",
            "description": "Standard BOM field",
            "datasheet": "Standard BOM field",
            "smd": "Standard BOM field",
            "i:package": "Inventory field",
            "fabricator": "Standard BOM field",
            "fabricator_part_number": "Standard BOM field",
        }

        # Use generator's parse method which knows about fabricators
        result = gen.parse_fields_argument("+jlc", available_fields, False, False)

        self.assertIn("reference", result)
        self.assertIn("quantity", result)
        self.assertIn("value", result)
        # JLC config maps "Footprint" to "i:package", so i:package should be in result
        self.assertIn("i:package", result)
        # fabricator_part_number is aliased to LCSC in JLC config, but internally it's fabricator_part_number
        self.assertIn("fabricator_part_number", result)

    def test_parse_standard_preset(self):
        """Test expanding +default preset"""
        from jbom.common.fields import parse_fields_argument as _parse_fields_argument

        available_fields = {
            "reference": "Standard",
            "quantity": "Standard",
            "description": "Standard",
            "value": "Standard",
            "footprint": "Standard",
            "lcsc": "Standard",
            "datasheet": "Standard",
            "smd": "Standard",
            "manufacturer": "Standard",
            "mfgpn": "Standard",
            "fabricator": "Standard",
            "fabricator_part_number": "Standard",
        }

        result = _parse_fields_argument("+default", available_fields, False, False)
        self.assertIn("reference", result)
        self.assertIn("quantity", result)
        self.assertIn("description", result)
        self.assertIn("manufacturer", result)
        self.assertIn("mfgpn", result)
        self.assertIn("fabricator", result)
        self.assertIn("fabricator_part_number", result)

    def test_parse_minimal_preset(self):
        """Test expanding +minimal preset"""
        from jbom.common.fields import parse_fields_argument as _parse_fields_argument

        available_fields = {
            "reference": "Standard",
            "quantity": "Standard",
            "value": "Standard",
            "lcsc": "Standard",
        }

        result = _parse_fields_argument("+minimal", available_fields, False, False)
        self.assertEqual(result, ["reference", "quantity", "value", "lcsc"])

    def test_parse_all_preset(self):
        """Test expanding +all preset to include all available fields"""
        from jbom.common.fields import parse_fields_argument as _parse_fields_argument

        available_fields = {
            "reference": "Standard",
            "value": "Standard",
            "customfield": "Custom",
            "lcsc": "Standard",
        }

        result = _parse_fields_argument("+all", available_fields, False, False)
        # Should include all fields in sorted order
        self.assertEqual(result, ["customfield", "lcsc", "reference", "value"])

    def test_parse_custom_fields(self):
        """Test parsing custom comma-separated field list"""
        from jbom.common.fields import parse_fields_argument as _parse_fields_argument

        available_fields = {
            "reference": "Standard",
            "quantity": "Standard",
            "value": "Standard",
            "lcsc": "Standard",
        }

        result = _parse_fields_argument(
            "reference,quantity,value,lcsc", available_fields, False, False
        )
        self.assertEqual(result, ["reference", "quantity", "value", "lcsc"])

    def test_parse_mixed_preset_and_custom(self):
        """Test mixing preset expansion with custom fields"""
        from jbom.common.fields import parse_fields_argument as _parse_fields_argument

        available_fields = {
            "reference": "Standard",
            "quantity": "Standard",
            "value": "Standard",
            "lcsc": "Standard",
            "customfield": "Custom",
            "datasheet": "Standard",
            "smd": "Standard",
            "description": "Standard",
            "footprint": "Standard",
            "i:package": "Inventory",
        }

        # Use +minimal instead of +jlc since minimal is a global preset
        result = _parse_fields_argument(
            "+minimal,customfield", available_fields, False, False
        )
        self.assertIn("reference", result)
        self.assertIn("customfield", result)
        # minimal has lcsc, check for it
        self.assertIn("lcsc", result)

    def test_invalid_preset_name(self):
        """Test error when using invalid preset name"""
        from jbom.common.fields import parse_fields_argument as _parse_fields_argument

        available_fields = {"reference": "Standard", "value": "Standard"}

        with self.assertRaises(ValueError) as context:
            _parse_fields_argument("+invalid", available_fields, False, False)

        self.assertIn("Unknown preset", str(context.exception))
        self.assertIn("invalid", str(context.exception))

    def test_invalid_field_name(self):
        """Test error when using invalid field name"""
        from jbom.common.fields import parse_fields_argument as _parse_fields_argument

        available_fields = {"reference": "Standard", "value": "Standard"}

        with self.assertRaises(ValueError) as context:
            _parse_fields_argument(
                "reference,InvalidField", available_fields, False, False
            )

        self.assertIn("Unknown field", str(context.exception))
        self.assertIn("InvalidField", str(context.exception))

    def test_deduplication(self):
        """Test that duplicate fields are removed"""
        from jbom.common.fields import parse_fields_argument as _parse_fields_argument

        available_fields = {
            "reference": "Standard",
            "value": "Standard",
        }

        result = _parse_fields_argument(
            "reference,value,reference", available_fields, False, False
        )
        # Should have only 2 items, not 3
        self.assertEqual(len([f for f in result if f == "reference"]), 1)

    def test_empty_fields_argument(self):
        """Test that empty --fields defaults to standard preset"""
        from jbom.common.fields import parse_fields_argument as _parse_fields_argument

        available_fields = {
            "reference": "Standard",
            "quantity": "Standard",
            "description": "Standard",
            "value": "Standard",
            "footprint": "Standard",
            "lcsc": "Standard",
            "datasheet": "Standard",
            "smd": "Standard",
        }

        result = _parse_fields_argument(None, available_fields, False, False)
        self.assertIn("reference", result)  # Now returns snake_case
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)


class TestNormalizeFieldName(unittest.TestCase):
    """Test normalize_field_name function for case-insensitive field handling"""

    def test_snake_case_preserved(self):
        """Test that snake_case format is preserved as-is"""
        from jbom import normalize_field_name

        test_cases = [
            ("match_quality", "match_quality"),
            ("reference", "reference"),
            ("i:package", "i:package"),
            ("c:tolerance", "c:tolerance"),
            ("my_custom_field", "my_custom_field"),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = normalize_field_name(input_val)
                self.assertEqual(result, expected)

    def test_title_case_conversion(self):
        """Test that Title Case is converted to snake_case"""
        from jbom import normalize_field_name

        test_cases = [
            ("Match Quality", "match_quality"),
            ("Reference", "reference"),
            ("Package", "package"),
            ("Manufacturer PN", "manufacturer_pn"),
            ("I:Package", "i:package"),
            ("C:Tolerance", "c:tolerance"),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = normalize_field_name(input_val)
                self.assertEqual(result, expected)

    def test_camelcase_conversion(self):
        """Test that CamelCase is converted to snake_case"""
        from jbom import normalize_field_name

        test_cases = [
            ("MatchQuality", "match_quality"),
            ("MyCustomField", "my_custom_field"),
            ("IPackage", "ipackage"),  # Consecutive caps like XMLData -> xmldata
            ("DataValue", "data_value"),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = normalize_field_name(input_val)
                self.assertEqual(result, expected)

    def test_uppercase_conversion(self):
        """Test that UPPERCASE is converted to lowercase"""
        from jbom import normalize_field_name

        test_cases = [
            ("REFERENCE", "reference"),
            ("MATCH_QUALITY", "match_quality"),
            ("VALUE", "value"),
            ("I:PACKAGE", "i:package"),
            ("C:TOLERANCE", "c:tolerance"),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = normalize_field_name(input_val)
                self.assertEqual(result, expected)

    def test_prefix_handling(self):
        """Test that I: and C: prefixes are handled correctly"""
        from jbom import normalize_field_name

        test_cases = [
            ("I:Package", "i:package"),
            ("i:package", "i:package"),
            ("C:Tolerance", "c:tolerance"),
            ("c:tolerance", "c:tolerance"),
            ("I:Match Quality", "i:match_quality"),
            ("C:Custom Field", "c:custom_field"),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = normalize_field_name(input_val)
                self.assertEqual(result, expected)

    def test_whitespace_handling(self):
        """Test that extra whitespace is normalized"""
        from jbom import normalize_field_name

        test_cases = [
            ("Match  Quality", "match_quality"),  # Double space
            ("  reference  ", "reference"),  # Leading/trailing spaces
            ("Match   Quality", "match_quality"),  # Multiple spaces
            ("Package  Type", "package_type"),  # Space in middle
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = normalize_field_name(input_val)
                self.assertEqual(result, expected)


class TestFieldPrefixSystem(unittest.TestCase):
    """Test I:/C: prefix system for field disambiguation"""

    def setUp(self):
        # Create inventory with fields that might conflict with component properties
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        csv_content = [
            "IPN,Name,Category,Package,Value,Tolerance,Voltage,LCSC,Priority",
            "R001,330R 5%,RES,0603,330R,5%,75V,C25231,1",
            "C001,100nF,CAP,0603,100nF,10%,25V,C14663,1",
        ]
        self.temp_inv.write("\n".join(csv_content))
        self.temp_inv.close()

        self.matcher = InventoryMatcher(Path(self.temp_inv.name))

        # Components with properties that might conflict with inventory fields
        self.components = [
            Component(
                "R1",
                "Device:R",
                "330R",
                "PCM_SPCoast:0603-RES",
                properties={"Tolerance": "1%", "Voltage": "50V"},
            ),
            Component(
                "C1",
                "Device:C",
                "100nF",
                "PCM_SPCoast:0603-CAP",
                properties={"Voltage": "50V"},
            ),
        ]

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_field_discovery(self):
        """Test that field discovery finds both inventory and component fields"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        available_fields = bom_gen.get_available_fields(self.components)

        # Should have standard BOM fields (normalized snake_case)
        self.assertIn("reference", available_fields)
        self.assertIn("quantity", available_fields)
        self.assertIn("value", available_fields)

        # Should have inventory fields (both prefixed and unprefixed where appropriate)
        self.assertIn("i:tolerance", available_fields)
        self.assertIn("i:package", available_fields)

        # Should have component property fields
        self.assertIn("c:tolerance", available_fields)
        self.assertIn("c:voltage", available_fields)

        # Should have ambiguous fields that exist in both sources
        self.assertIn("tolerance", available_fields)  # Ambiguous field
        self.assertIn("voltage", available_fields)  # Ambiguous field

    def test_field_value_extraction_prefixed(self):
        """Test field value extraction with explicit prefixes"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom()

        # Find resistor entry
        resistor_entry = None
        for entry in bom_entries:
            if "R1" in entry.reference:
                resistor_entry = entry
                break

        self.assertIsNotNone(resistor_entry)

        # Find corresponding component and inventory item
        component = self.components[0]  # R1
        inventory_item = None
        for item in self.matcher.inventory:
            if item.lcsc == resistor_entry.lcsc:
                inventory_item = item
                break

        self.assertIsNotNone(inventory_item)

        # Test explicit inventory field extraction
        inv_tolerance = bom_gen._get_field_value(
            "I:Tolerance", resistor_entry, component, inventory_item
        )
        self.assertEqual(inv_tolerance, "5%")  # From inventory

        # Test explicit component property extraction
        comp_tolerance = bom_gen._get_field_value(
            "C:Tolerance", resistor_entry, component, inventory_item
        )
        self.assertEqual(comp_tolerance, "1%")  # From component properties

    def test_ambiguous_field_handling(self):
        """Test that ambiguous fields return combined values"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom()

        # Find resistor entry
        resistor_entry = None
        for entry in bom_entries:
            if "R1" in entry.reference:
                resistor_entry = entry
                break

        component = self.components[0]
        inventory_item = None
        for item in self.matcher.inventory:
            if item.lcsc == resistor_entry.lcsc:
                inventory_item = item
                break

        # Test ambiguous field (should return combined value)
        tolerance_value = bom_gen._get_field_value(
            "Tolerance", resistor_entry, component, inventory_item
        )
        self.assertIn(
            "i:", tolerance_value
        )  # Should contain inventory marker (lowercase)
        self.assertIn(
            "c:", tolerance_value
        )  # Should contain component marker (lowercase)


class TestNewConstants(unittest.TestCase):
    """Test the new constant classes and their values"""

    def test_component_type_constants(self):
        """Test ComponentType constants have expected values"""
        self.assertEqual(ComponentType.RESISTOR, "RES")
        self.assertEqual(ComponentType.CAPACITOR, "CAP")
        self.assertEqual(ComponentType.INDUCTOR, "IND")
        self.assertEqual(ComponentType.DIODE, "DIO")
        self.assertEqual(ComponentType.LED, "LED")
        self.assertEqual(ComponentType.TRANSISTOR, "Q")
        self.assertEqual(ComponentType.INTEGRATED_CIRCUIT, "IC")
        self.assertEqual(ComponentType.CONNECTOR, "CON")
        self.assertEqual(ComponentType.SWITCH, "SWI")
        self.assertEqual(ComponentType.MICROCONTROLLER, "MCU")
        self.assertEqual(ComponentType.REGULATOR, "REG")
        self.assertEqual(ComponentType.OSCILLATOR, "OSC")

    def test_diagnostic_issue_constants(self):
        """Test DiagnosticIssue constants have expected values"""
        self.assertEqual(DiagnosticIssue.TYPE_UNKNOWN, "type_unknown")
        self.assertEqual(DiagnosticIssue.NO_TYPE_MATCH, "no_type_match")
        self.assertEqual(DiagnosticIssue.NO_VALUE_MATCH, "no_value_match")
        self.assertEqual(DiagnosticIssue.PACKAGE_MISMATCH, "package_mismatch")
        self.assertEqual(
            DiagnosticIssue.PACKAGE_MISMATCH_GENERIC, "package_mismatch_generic"
        )
        self.assertEqual(DiagnosticIssue.NO_MATCH, "no_match")

    def test_common_fields_constants(self):
        """Test CommonFields constants have expected values"""
        self.assertEqual(CommonFields.VOLTAGE, "V")
        self.assertEqual(CommonFields.AMPERAGE, "A")
        self.assertEqual(CommonFields.WATTAGE, "W")
        self.assertEqual(CommonFields.TOLERANCE, "Tolerance")
        self.assertEqual(CommonFields.POWER, "Power")
        self.assertEqual(
            CommonFields.TEMPERATURE_COEFFICIENT, "Temperature Coefficient"
        )

    def test_score_weights_constants(self):
        """Test ScoreWeights constants have expected values"""
        self.assertEqual(ScoreWeights.TOLERANCE_EXACT, 15)
        self.assertEqual(ScoreWeights.TOLERANCE_BETTER, 12)
        self.assertEqual(ScoreWeights.VOLTAGE_MATCH, 10)
        self.assertEqual(ScoreWeights.CURRENT_MATCH, 10)
        self.assertEqual(ScoreWeights.POWER_MATCH, 10)
        self.assertEqual(ScoreWeights.LED_WAVELENGTH, 8)
        self.assertEqual(ScoreWeights.LED_INTENSITY, 8)
        self.assertEqual(ScoreWeights.OSC_FREQUENCY, 12)
        self.assertEqual(ScoreWeights.OSC_STABILITY, 8)
        self.assertEqual(ScoreWeights.LED_ANGLE, 5)
        self.assertEqual(ScoreWeights.OSC_LOAD, 5)
        self.assertEqual(ScoreWeights.CON_PITCH, 10)
        self.assertEqual(ScoreWeights.MCU_FAMILY, 8)
        self.assertEqual(ScoreWeights.GENERIC_PROPERTY, 3)


if __name__ == "__main__":
    unittest.main()
