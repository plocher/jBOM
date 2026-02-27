#!/usr/bin/env python3
"""Unit tests for component value parsing and type detection."""
import unittest
import tempfile
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from jbom.common.types import Component
from jbom.processors.inventory_matcher import InventoryMatcher
from jbom.processors.component_types import (
    get_category_fields,
    get_value_interpretation,
)
from jbom.common.constants import CATEGORY_FIELDS, VALUE_INTERPRETATION
from jbom.generators.bom import BOMGenerator


class TestResistorParsing(unittest.TestCase):
    """Test resistor value parsing and EIA formatting.

    Validates:
    - Parsing various formats: 330R, 3R3, 22K, 2M2, etc.
    - EIA formatting with precision control: 10K vs 10K0.
    - Edge cases and invalid inputs.
    """

    def setUp(self):
        # Create a temporary inventory file for matcher
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        self.temp_inv.write("IPN,Name,Category,Value,LCSC\ntest,test,RES,330R,C123\n")
        self.temp_inv.close()
        self.matcher = InventoryMatcher(Path(self.temp_inv.name))

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_parse_res_to_ohms(self):
        """Test parsing various resistor value formats to ohms"""
        test_cases = [
            ("330", 330.0),
            ("330R", 330.0),
            ("330Ω", 330.0),
            ("3R3", 3.3),
            ("22k", 22000.0),
            ("22K", 22000.0),
            ("22k0", 22000.0),
            ("22K0", 22000.0),
            ("2M2", 2200000.0),
            ("1M", 1000000.0),
            ("0R22", 0.22),
            ("10K1", 10100.0),
            ("47K5", 47500.0),
            ("2M7", 2700000.0),
            ("1R2", 1.2),
            ("", None),
            ("invalid", None),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = self.matcher._parse_res_to_ohms(input_val)
                if expected is None:
                    self.assertIsNone(result)
                else:
                    self.assertAlmostEqual(result, expected, places=6)

    def test_ohms_to_eia_basic(self):
        """Test formatting ohms to EIA format"""
        test_cases = [
            (330.0, False, "330R"),
            (3300.0, False, "3K3"),
            (10000.0, False, "10K"),
            (22000.0, False, "22K"),
            (1000000.0, False, "1M"),
            (2200000.0, False, "2M2"),
            (3.3, False, "3R3"),
            (0.22, False, "0R22"),
        ]

        for ohms, force_zero, expected in test_cases:
            with self.subTest(ohms=ohms, force_zero=force_zero):
                result = self.matcher._ohms_to_eia(ohms, force_trailing_zero=force_zero)
                self.assertEqual(result, expected)

    def test_ohms_to_eia_precision(self):
        """Test EIA formatting with precision trailing zeros"""
        test_cases = [
            (10000.0, True, "10K0"),
            (22000.0, True, "22K0"),
            (1000000.0, True, "1M0"),
            (330.0, True, "330R"),  # No trailing zero for R values
        ]

        for ohms, force_zero, expected in test_cases:
            with self.subTest(ohms=ohms, force_zero=force_zero):
                result = self.matcher._ohms_to_eia(ohms, force_trailing_zero=force_zero)
                self.assertEqual(result, expected)


class TestCapacitorParsing(unittest.TestCase):
    """Test capacitor value parsing and formatting.

    Validates:
    - Parsing formats: 100nF, 1uF, 220pF, 1n0, etc.
    - EIA-style formatting: 100nF, 2u2F, 4n7F.
    """

    def setUp(self):
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        self.temp_inv.write("IPN,Name,Category,Value,LCSC\ntest,test,CAP,100nF,C123\n")
        self.temp_inv.close()
        self.matcher = InventoryMatcher(Path(self.temp_inv.name))

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_parse_cap_to_farad(self):
        """Test parsing capacitor values to farads"""
        test_cases = [
            ("100nF", 100e-9),
            ("100n", 100e-9),
            ("0.1uF", 0.1e-6),
            ("1uF", 1e-6),
            ("1u", 1e-6),
            ("220pF", 220e-12),
            ("220p", 220e-12),
            ("1n0", 1e-9),
            ("1u0", 1e-6),
            ("", None),
            ("invalid", None),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = self.matcher._parse_cap_to_farad(input_val)
                if expected is None:
                    self.assertIsNone(result)
                else:
                    self.assertAlmostEqual(result, expected, places=12)

    def test_farad_to_eia(self):
        """Test formatting farads to EIA format"""
        test_cases = [
            (100e-9, "100nF"),
            (1e-6, "1uF"),
            (0.1e-6, "100nF"),
            (220e-12, "220pF"),
            (2.2e-6, "2u2F"),
            (4.7e-9, "4n7F"),
        ]

        for farads, expected in test_cases:
            with self.subTest(farads=farads):
                result = self.matcher._farad_to_eia(farads)
                self.assertEqual(result, expected)


class TestInductorParsing(unittest.TestCase):
    """Test inductor value parsing and formatting.

    Validates:
    - Parsing formats: 10uH, 2m2H, 100nH, etc.
    - EIA-style formatting: 10uH, 2m2H, 4u7H.
    """

    def setUp(self):
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        self.temp_inv.write("IPN,Name,Category,Value,LCSC\ntest,test,IND,10uH,C123\n")
        self.temp_inv.close()
        self.matcher = InventoryMatcher(Path(self.temp_inv.name))

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_parse_ind_to_henry(self):
        """Test parsing inductor values to henrys"""
        test_cases = [
            ("10uH", 10e-6),
            ("10u", 10e-6),
            ("100nH", 100e-9),
            ("100n", 100e-9),
            ("2m2H", 2.2e-3),
            ("2m2", 2.2e-3),
            ("1mH", 1e-3),
            ("", None),
            ("invalid", None),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = self.matcher._parse_ind_to_henry(input_val)
                if expected is None:
                    self.assertIsNone(result)
                else:
                    self.assertAlmostEqual(result, expected, places=9)

    def test_henry_to_eia(self):
        """Test formatting henrys to EIA format"""
        test_cases = [
            (10e-6, "10uH"),
            (100e-9, "100nH"),
            (2.2e-3, "2m2H"),
            (1e-3, "1mH"),
            (4.7e-6, "4u7H"),
        ]

        for henrys, expected in test_cases:
            with self.subTest(henrys=henrys):
                result = self.matcher._henry_to_eia(henrys)
                self.assertEqual(result, expected)


class TestCategorySpecificFields(unittest.TestCase):
    """Test category-specific field mappings and value interpretation"""

    def test_get_category_fields(self):
        """Test category-specific field retrieval"""
        # Test resistor fields
        res_fields = get_category_fields("RES")
        self.assertIn("Tolerance", res_fields)
        self.assertIn("V", res_fields)
        self.assertIn("W", res_fields)
        self.assertNotIn("Capacitance", res_fields)  # Should not have capacitor fields

        # Test capacitor fields
        cap_fields = get_category_fields("CAP")
        self.assertIn("Voltage", cap_fields)
        self.assertIn("Type", cap_fields)
        self.assertIn("Tolerance", cap_fields)
        self.assertNotIn("Resistance", cap_fields)  # Should not have resistor fields

        # Test LED fields
        led_fields = get_category_fields("LED")
        self.assertIn("mcd", led_fields)
        self.assertIn("Wavelength", led_fields)
        self.assertIn("Angle", led_fields)

        # Test unknown category (should get default fields)
        unknown_fields = get_category_fields("UNKNOWN")
        self.assertIn("Tolerance", unknown_fields)  # Should include common fields
        self.assertIn("Temperature Coefficient", unknown_fields)

    def test_get_value_interpretation(self):
        """Test value interpretation mapping"""
        # Test known interpretations
        self.assertEqual(get_value_interpretation("RES"), "Resistance")
        self.assertEqual(get_value_interpretation("CAP"), "Capacitance")
        self.assertEqual(get_value_interpretation("IND"), "Inductance")
        self.assertEqual(get_value_interpretation("LED"), "Color")

        # Test alternative naming
        self.assertEqual(get_value_interpretation("RESISTOR"), "Resistance")
        self.assertEqual(get_value_interpretation("CAPACITOR"), "Capacitance")

        # Test unknown types
        self.assertIsNone(get_value_interpretation("UNKNOWN"))
        self.assertIsNone(get_value_interpretation(""))

    def test_category_field_constants(self):
        """Test that the category field constants are properly defined"""
        # Test that main categories exist
        self.assertIn("RES", CATEGORY_FIELDS)
        self.assertIn("CAP", CATEGORY_FIELDS)
        self.assertIn("LED", CATEGORY_FIELDS)
        self.assertIn("IND", CATEGORY_FIELDS)

        # Test that value interpretation constants exist
        self.assertIn("RES", VALUE_INTERPRETATION)
        self.assertIn("CAP", VALUE_INTERPRETATION)
        self.assertIn("IND", VALUE_INTERPRETATION)
        self.assertIn("LED", VALUE_INTERPRETATION)


class TestComponentTypeDetection(unittest.TestCase):
    """Test component type detection from lib_id and footprint.

    Validates:
    - Detection from lib_id: Device:R → RES, Device:C → CAP.
    - Detection from footprint patterns.
    - Handling unknown component types.
    """

    def setUp(self):
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        self.temp_inv.write("IPN,Name,Category,Value,LCSC\ntest,test,RES,330R,C123\n")
        self.temp_inv.close()
        self.matcher = InventoryMatcher(Path(self.temp_inv.name))

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_get_component_type(self):
        """Test component type detection"""
        test_cases = [
            ("Device:R", "RES"),
            ("Device:C", "CAP"),
            ("Device:L", "IND"),
            ("Device:LED", "LED"),
            ("Device:Q_NPN_BCE", "Q"),  # Fixed: Q components are transistors
            ("Connector:Conn_01x02", "CON"),
            ("Switch:SW_Push", "SWI"),
            ("MCU:ESP32", "IC"),  # Fixed: MCU components are ICs
            ("IC:74HC595", "IC"),  # Additional test for IC prefix
            ("SPCoast:resistor", "RES"),
            ("SPCoast:capacitor", "CAP"),
            ("unknown:part", None),
        ]

        for lib_id, expected in test_cases:
            with self.subTest(lib_id=lib_id):
                component = Component(
                    reference="R1", lib_id=lib_id, value="", footprint=""
                )
                result = self.matcher._get_component_type(component)
                self.assertEqual(result, expected)


class TestPrecisionResistorDetection(unittest.TestCase):
    """Test precision resistor detection logic.

    Validates:
    - Pattern detection for precision values: 10K0, 47K5, 2M7.
    - BOM generation warnings when 1% parts are implied but unavailable.
    - Standard vs precision value handling.
    """

    def setUp(self):
        # Create comprehensive inventory with standard decade values
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )

        # Standard E6/E12/E24 decade values with both 1% and 5% tolerances
        csv_content = [
            "IPN,Name,Category,Generic,Package,Value,Tolerance,LCSC,Priority"
        ]

        # E12 series standard values (5% tolerance)
        e12_values = [
            "10R",
            "12R",
            "15R",
            "18R",
            "22R",
            "27R",
            "33R",
            "39R",
            "47R",
            "56R",
            "68R",
            "82R",
        ]
        for i, val in enumerate(e12_values):
            csv_content.append(f"R{100+i},{val} 5%,RES,0603,0603,{val},5%,C{100+i},1")
            # Add K and M variants
            k_val = val.replace("R", "K")
            m_val = (
                val.replace("R", "M") if val != "10R" else None
            )  # Skip 10M (too large)
            csv_content.append(
                f"R{200+i},{k_val} 5%,RES,0603,0603,{k_val},5%,C{200+i},1"
            )
            if m_val:
                csv_content.append(
                    f"R{300+i},{m_val} 5%,RES,0603,0603,{m_val},5%,C{300+i},1"
                )

        # E24/E48 precision values (1% tolerance) - subset for testing
        precision_values = ["10K0", "10K1", "10K2", "47K5", "22K1", "33K2"]
        for i, val in enumerate(precision_values):
            csv_content.append(f"RP{i},{val} 1%,RES,0603,0603,{val},1%,CP{i},1")

        # Some standard values with only 5% available (for warning tests)
        warning_test_values = ["91K", "1M3"]
        for i, val in enumerate(warning_test_values):
            csv_content.append(f"RW{i},{val} 5%,RES,0603,0603,{val},5%,CW{i},2")

        self.temp_inv.write("\n".join(csv_content))
        self.temp_inv.close()

        self.matcher = InventoryMatcher(Path(self.temp_inv.name))

        # Test components covering various scenarios
        self.components = [
            # Precision components that HAVE 1% inventory matches
            Component("R1", "Device:R", "10K0", "PCM_SPCoast:0603-RES"),  # Has 1% match
            Component("R2", "Device:R", "47K5", "PCM_SPCoast:0603-RES"),  # Has 1% match
            # Precision components that DON'T have 1% matches (should warn)
            Component(
                "R3", "Device:R", "91K0", "PCM_SPCoast:0603-RES"
            ),  # Only 5% available
            Component(
                "R4", "Device:R", "1M30", "PCM_SPCoast:0603-RES"
            ),  # Only 5% available
            # Standard components (should not warn)
            Component("R5", "Device:R", "10K", "PCM_SPCoast:0603-RES"),  # Standard
            Component("R6", "Device:R", "47R", "PCM_SPCoast:0603-RES"),  # Standard
            # Component with no inventory match at all
            Component(
                "R7", "Device:R", "999K9", "PCM_SPCoast:0603-RES"
            ),  # Not in inventory
        ]

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_precision_detection_pattern(self):
        """Test that precision resistor patterns are correctly detected"""
        import re

        precision_pattern = r"^\s*\d+[kKmMrR]\d+\s*"

        test_cases = [
            # Single trailing digit (precision)
            ("10K0", True),  # Precision - trailing 0
            ("10K1", True),  # Precision - trailing 1
            ("47K5", True),  # Precision - trailing 5
            ("2M7", True),  # Precision - trailing 7
            ("1R2", True),  # Precision - trailing 2
            # Multi-digit trailing (precision)
            ("1K33", True),  # Precision - 1.33kΩ
            ("2K74", True),  # Precision - 2.74kΩ
            ("10K05", True),  # Precision - 10.05kΩ
            ("1M47", True),  # Precision - 1.47MΩ
            ("0R125", True),  # Precision - 0.125Ω
            # Standard values (no trailing digits)
            ("10K", False),  # Standard - no trailing digit
            ("330R", False),  # Standard - no trailing digit
            ("22k", False),  # Standard - lowercase, no trailing digit
            ("1M", False),  # Standard - no trailing digit
        ]

        for value, should_match in test_cases:
            with self.subTest(value=value):
                matches = bool(re.match(precision_pattern, value))
                self.assertEqual(
                    matches,
                    should_match,
                    (
                        f"Value '{value}' should "
                        f"{'match' if should_match else 'not match'} precision pattern"
                    ),
                )

    def test_bom_generation_precision_warnings(self):
        """Test that BOM generation includes precision warnings"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom()

        # Create lookup by reference
        entries_by_ref = {e.reference: e for e in bom_entries}

        # Test cases:
        # R1 (10K0): Precision format, has 1% match -> No warning
        self.assertIn("R1", entries_by_ref)
        self.assertNotIn("Warning", entries_by_ref["R1"].notes)

        # R2 (47K5): Precision format, has 1% match -> No warning
        self.assertIn("R2", entries_by_ref)
        self.assertNotIn("Warning", entries_by_ref["R2"].notes)

        # R3 (91K0): Precision format, only 5% available -> Warning
        self.assertIn("R3", entries_by_ref)
        self.assertIn("Warning", entries_by_ref["R3"].notes)

        # R4 (1M30): Precision format, only 5% available -> Warning
        self.assertIn("R4", entries_by_ref)
        self.assertIn("Warning", entries_by_ref["R4"].notes)

        # R5 (10K): Standard format -> No warning
        self.assertIn("R5", entries_by_ref)
        self.assertNotIn("Warning", entries_by_ref["R5"].notes)

        # R6 (47R): Standard format -> No warning
        self.assertIn("R6", entries_by_ref)
        self.assertNotIn("Warning", entries_by_ref["R6"].notes)

        # R7 (999K9): No match at all -> "No inventory match found"
        self.assertIn("R7", entries_by_ref)
        self.assertIn("No inventory match found", entries_by_ref["R7"].notes)


class TestNormalizeComponentType(unittest.TestCase):
    """Test the normalize_component_type function"""

    def test_normalize_component_type_mapping(self):
        """Test that normalize_component_type maps component types correctly"""
        from jbom import normalize_component_type

        # Test direct mapping to existing categories
        self.assertEqual(normalize_component_type("R"), "RES")
        self.assertEqual(normalize_component_type("RESISTOR"), "RES")
        self.assertEqual(normalize_component_type("C"), "CAP")
        self.assertEqual(normalize_component_type("CAPACITOR"), "CAP")
        self.assertEqual(normalize_component_type("D"), "DIO")
        self.assertEqual(normalize_component_type("DIODE"), "DIO")
        self.assertEqual(normalize_component_type("L"), "IND")
        self.assertEqual(normalize_component_type("INDUCTOR"), "IND")

        # Test direct category returns (case insensitive)
        self.assertEqual(normalize_component_type("RES"), "RES")
        self.assertEqual(normalize_component_type("res"), "RES")
        self.assertEqual(normalize_component_type("CAP"), "CAP")

        # Test transistor mapping
        self.assertEqual(normalize_component_type("TRANSISTOR"), "Q")

        # Test unknown component (returns as-is, uppercase)
        self.assertEqual(
            normalize_component_type("Device:Unknown_Part"), "DEVICE:UNKNOWN_PART"
        )
        self.assertEqual(normalize_component_type(""), "")


if __name__ == "__main__":
    unittest.main()
