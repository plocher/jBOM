#!/usr/bin/env python3
"""Unit tests for BOM generation logic."""
import unittest
import tempfile
import csv
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from jbom.common.types import Component, BOMEntry, InventoryItem
from jbom.generators.bom import BOMGenerator
from jbom.processors.inventory_matcher import InventoryMatcher


class TestBOMGeneration(unittest.TestCase):
    """Test BOM generation and CSV output"""

    def setUp(self):
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        csv_content = [
            (
                "IPN,Name,Category,Generic,Package,Value,LCSC,Manufacturer,MFGPN,"
                "Description,Datasheet,Priority"
            ),
            (
                "R001,330R,RES,0603,0603,330R,C25231,UNI-ROYAL,0603WAJ0331T5E,"
                "330Ω 5% 0603,https://example.com/r1,1"
            ),
            (
                "C001,100nF,CAP,0603,0603,100nF,C14663,YAGEO,CC0603KRX7R9BB104,"
                "100nF X7R 0603,https://example.com/c1,1"
            ),
        ]
        self.temp_inv.write("\n".join(csv_content))
        self.temp_inv.close()

        self.matcher = InventoryMatcher(Path(self.temp_inv.name))
        self.components = [
            Component("R1", "Device:R", "330R", "PCM_SPCoast:0603-RES"),
            Component(
                "R2", "Device:R", "330R", "PCM_SPCoast:0603-RES"
            ),  # Duplicate for grouping
            Component("C1", "Device:C", "100nF", "PCM_SPCoast:0603-CAP"),
        ]

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_component_grouping(self):
        """Test that components are grouped by their matching inventory item"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        groups = bom_gen._group_components()

        # Should have 2 groups: one for R1,R2 (same inventory item) and one for C1
        self.assertEqual(len(groups), 2)

        # Find the resistor group (should be grouped by IPN, not value)
        resistor_group = None
        for key, comps in groups.items():
            if "R001" in key:  # IPN-based grouping
                resistor_group = comps
                break

        self.assertIsNotNone(resistor_group)
        self.assertEqual(len(resistor_group), 2)  # R1 and R2

    def test_bom_generation(self):
        """Test basic BOM generation"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom()

        # Should have entries for grouped components
        self.assertGreater(len(bom_entries), 0)

        # Find resistor entry (should be grouped)
        resistor_entry = None
        for entry in bom_entries:
            if "R1" in entry.reference and "R2" in entry.reference:
                resistor_entry = entry
                break

        self.assertIsNotNone(resistor_entry)
        self.assertEqual(resistor_entry.quantity, 2)
        self.assertEqual(resistor_entry.value, "330R")

    def test_csv_output_basic(self):
        """Test basic CSV output format"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            temp_csv = Path(f.name)

        try:
            # Basic field list (non-verbose, no manufacturer) - normalized snake_case
            fields = [
                "reference",
                "quantity",
                "description",
                "value",
                "footprint",
                "lcsc",
                "datasheet",
                "smd",
            ]
            bom_gen.write_bom_csv(bom_entries, temp_csv, fields)

            # Read back and verify format
            with open(temp_csv, "r") as f:
                reader = csv.reader(f)
                header = next(reader)

                # Headers should be Title Case
                expected_header = [
                    "Reference",
                    "Quantity",
                    "Description",
                    "Value",
                    "Footprint",
                    "LCSC",
                    "Datasheet",
                    "SMD",
                ]
                self.assertEqual(header, expected_header)

                # Should have at least one data row
                rows = list(reader)
                self.assertGreater(len(rows), 0)
        finally:
            temp_csv.unlink()

    def test_csv_output_verbose(self):
        """Test verbose CSV output format"""
        from jbom.common.generator import GeneratorOptions

        bom_gen = BOMGenerator(self.matcher, GeneratorOptions(verbose=True))
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom(
            verbose=True
        )  # Pass verbose to generate_bom

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            temp_csv = Path(f.name)

        try:
            # Verbose field list with manufacturer - normalized snake_case
            fields = [
                "reference",
                "quantity",
                "description",
                "value",
                "footprint",
                "lcsc",
                "manufacturer",
                "mfgpn",
                "datasheet",
                "smd",
                "match_quality",
                "priority",
            ]
            bom_gen.write_bom_csv(bom_entries, temp_csv, fields)

            # Read back and verify format includes extra columns
            with open(temp_csv, "r") as f:
                reader = csv.reader(f)
                header = next(reader)

                # Should include manufacturer and verbose columns (simplified) - Title Case headers
                self.assertIn("Manufacturer", header)
                self.assertIn("MFGPN", header)
                self.assertIn("Match Quality", header)
                self.assertIn("Priority", header)
        finally:
            temp_csv.unlink()


class TestBOMSorting(unittest.TestCase):
    """Test BOM sorting by category and component numbering"""

    def setUp(self):
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        csv_content = [
            (
                "IPN,Name,Category,Generic,Package,Value,LCSC,Manufacturer,MFGPN,"
                "Description,Datasheet,Priority"
            ),
            (
                "R001,330R,RES,0603,0603,330R,C25231,UNI-ROYAL,0603WAJ0331T5E,"
                "330Ω 5% 0603,https://example.com/r1,1"
            ),
            (
                "R002,10K,RES,0603,0603,10K,C25232,UNI-ROYAL,0603WAF1002T5E,"
                "10kΩ 5% 0603,https://example.com/r2,1"
            ),
            (
                "C001,1uF,CAP,0603,0603,1uF,C14663,YAGEO,CC0603KRX7R9BB104,"
                "1uF X7R 0603,https://example.com/c1,1"
            ),
            (
                "D001,BAT54A,DIO,SOT-23,SOT-23,BAT54A,C12345,FOSAN,BAT54A,BAT54A Schottky,"
                "https://example.com/d1,1"
            ),
            (
                "LED001,WS2812B,LED,5050,5050,WS2812B,C54678,XINGLIGHT,WS2812B,RGB LED,"
                "https://example.com/led1,1"
            ),
        ]
        self.temp_inv.write("\n".join(csv_content))
        self.temp_inv.close()

        self.matcher = InventoryMatcher(Path(self.temp_inv.name))
        # Components in mixed order to test sorting
        self.components = [
            Component("R10", "Device:R", "330R", "PCM_SPCoast:0603-RES"),
            Component("LED3", "Device:LED", "WS2812B", "PCM_SPCoast:WS2812B"),
            Component("C2", "Device:C", "1uF", "PCM_SPCoast:0603-CAP"),
            Component("R1", "Device:R", "10K", "PCM_SPCoast:0603-RES"),
            Component("D5", "Device:D", "BAT54A", "Package_TO_SOT_SMD:SOT-23"),
            Component("R2", "Device:R", "10K", "PCM_SPCoast:0603-RES"),  # Same as R1
        ]

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_bom_sort_key_parsing(self):
        """Test component reference parsing for sorting"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components

        test_cases = [
            ("R1", ("R", 1)),
            ("C10", ("C", 10)),
            ("LED4", ("LED", 4)),
            ("U100", ("U", 100)),
        ]

        for ref, expected in test_cases:
            with self.subTest(reference=ref):
                category, number = bom_gen._parse_reference(ref)
                self.assertEqual(category, expected[0])
                self.assertEqual(number, expected[1])

    def test_bom_sorting_order(self):
        """Test that BOM entries are sorted correctly"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom()

        # Extract references to check order
        references = [entry.reference for entry in bom_entries]

        # The actual references might be grouped, so check the essential ordering
        self.assertEqual(len(references), 5)

        # Check that categories appear in correct order
        categories_found = []
        for ref in references:
            # Extract first letter/category from reference
            if ref.startswith("C"):
                categories_found.append("C")
            elif ref.startswith("D"):
                categories_found.append("D")
            elif ref.startswith("LED"):
                categories_found.append("LED")
            elif ref.startswith("R"):
                categories_found.append("R")

        # Should be in alphabetical order by category
        expected_categories = ["C", "D", "LED", "R", "R"]
        self.assertEqual(categories_found, expected_categories)


class TestCustomFieldOutput(unittest.TestCase):
    """Test custom field selection in BOM output"""

    def setUp(self):
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        csv_content = [
            "IPN,Name,Category,Package,Value,Tolerance,LCSC,Manufacturer,MFGPN,Priority",
            "R001,330R 5%,RES,0603,330R,5%,C25231,UNI-ROYAL,0603WAJ0331T5E,1",
        ]
        self.temp_inv.write("\n".join(csv_content))
        self.temp_inv.close()

        self.matcher = InventoryMatcher(Path(self.temp_inv.name))
        self.components = [
            Component(
                "R1",
                "Device:R",
                "330R",
                "PCM_SPCoast:0603-RES",
                properties={"Tolerance": "1%", "Power": "0.1W"},
            ),
        ]

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_custom_field_csv_output(self):
        """Test CSV output with custom field selection"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            temp_csv = Path(f.name)

        try:
            # Test custom fields including prefixed ones (normalized snake_case)
            custom_fields = [
                "reference",
                "value",
                "i:package",
                "c:tolerance",
                "manufacturer",
            ]
            bom_gen.write_bom_csv(bom_entries, temp_csv, custom_fields)

            # Read back and verify
            with open(temp_csv, "r") as f:
                reader = csv.reader(f)
                header = next(reader)

                # Headers should be Title Case without spaces after prefixes
                expected_header = [
                    "Reference",
                    "Value",
                    "I:Package",
                    "C:Tolerance",
                    "Manufacturer",
                ]
                self.assertEqual(header, expected_header)

                # Check data row
                data_row = next(reader)
                self.assertEqual(data_row[0], "R1")  # Reference
                self.assertEqual(data_row[1], "330R")  # Value
                self.assertEqual(data_row[2], "0603")  # I:Package (from inventory)
                self.assertEqual(data_row[3], "1%")  # C:Tolerance (from component)
                self.assertEqual(data_row[4], "UNI-ROYAL")  # Manufacturer
        finally:
            temp_csv.unlink()

    def test_ambiguous_field_csv_output(self):
        """Test CSV output with ambiguous fields that auto-split into columns"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            temp_csv = Path(f.name)

        try:
            # Use ambiguous field that should auto-split (normalized snake_case)
            custom_fields = ["reference", "value", "tolerance"]
            bom_gen.write_bom_csv(bom_entries, temp_csv, custom_fields)

            # Read back and verify
            with open(temp_csv, "r") as f:
                reader = csv.reader(f)
                header = next(reader)

                # Should auto-expand to separate I: and C: columns with Title Case headers
                expected_header = ["Reference", "Value", "I:Tolerance", "C:Tolerance"]
                self.assertEqual(header, expected_header)

                # Check data
                data_row = next(reader)
                self.assertEqual(data_row[0], "R1")  # Reference
                self.assertEqual(data_row[1], "330R")  # Value
                self.assertEqual(data_row[2], "5%")  # I:Tolerance (from inventory)
                self.assertEqual(data_row[3], "1%")  # C:Tolerance (from component)
        finally:
            temp_csv.unlink()


class TestSMDFiltering(unittest.TestCase):
    """Test SMD component filtering functionality"""

    def setUp(self):
        # Create test inventory with both SMD and PTH components
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        csv_content = [
            "IPN,Name,Category,Package,Value,SMD,LCSC,Manufacturer,MFGPN,Description,Priority",
            "R001,330R SMD,RES,0603,330R,SMD,C25231,UNI-ROYAL,0603WAJ0331T5E,330Ω SMD 0603,1",
            "R002,330R PTH,RES,THT,330R,PTH,C25232,VISHAY,PTR0603330R,330Ω PTH,1",
            "C001,100nF SMD,CAP,0603,100nF,SMD,C14663,YAGEO,CC0603KRX7R9BB104,100nF SMD 0603,1",
            "C002,100nF PTH,CAP,THT,100nF,PTH,C14664,VISHAY,K104K15X7RF5TL2,100nF PTH,1",
        ]
        self.temp_inv.write("\n".join(csv_content))
        self.temp_inv.close()

        self.matcher = InventoryMatcher(Path(self.temp_inv.name))
        # Create mixed components - some that will match SMD, some PTH
        # Note: THT components use different footprints that won't match 0603 package
        self.components = [
            Component(
                "R1", "Device:R", "330R", "PCM_SPCoast:0603-RES"
            ),  # Should match SMD (R001)
            Component(
                "R2", "Device:R", "330R", "PCM_SPCoast:DIP-RES"
            ),  # Should match PTH (R002)
            Component(
                "C1", "Device:C", "100nF", "PCM_SPCoast:0603-CAP"
            ),  # Should match SMD (C001)
            Component(
                "C2", "Device:C", "100nF", "PCM_SPCoast:DIP-CAP"
            ),  # Should match PTH (C002)
        ]

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_smd_filtering_enabled(self):
        """Test that SMD filtering works when enabled"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components

        # Generate BOM with SMD filtering
        bom_entries, _, _ = bom_gen.generate_bom(smd_only=True)

        # Should only include SMD components
        smd_entries = [entry for entry in bom_entries if entry.smd == "SMD"]
        pth_entries = [entry for entry in bom_entries if entry.smd == "PTH"]

        # All entries should be SMD when filtering is enabled
        self.assertEqual(len(smd_entries), len(bom_entries))
        self.assertEqual(len(pth_entries), 0)

    def test_smd_filtering_disabled(self):
        """Test that SMD filtering is off by default"""
        # Create a simple test with one SMD and one PTH component
        # that match different inventory items
        temp_inv2 = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv")
        csv_content2 = [
            "IPN,Name,Category,Package,Value,SMD,LCSC,Manufacturer,MFGPN,Description,Priority",
            "R001,330R SMD,RES,0603,330R,SMD,C25231,UNI-ROYAL,0603WAJ0331T5E,330Ω SMD 0603,1",
            (
                "R003,1K PTH,RES,THT,1K,PTH,C25233,VISHAY,PTR06031K,1kΩ PTH,1"
            ),  # Different value to force different match
        ]
        temp_inv2.write("\n".join(csv_content2))
        temp_inv2.close()

        matcher2 = InventoryMatcher(Path(temp_inv2.name))
        components2 = [
            Component(
                "R1", "Device:R", "330R", "PCM_SPCoast:0603-RES"
            ),  # Should match SMD item
            Component(
                "R2", "Device:R", "1K", "PCM_SPCoast:DIP-RES"
            ),  # Should match PTH item
        ]

        bom_gen = BOMGenerator(matcher2)
        bom_gen.components = components2
        bom_entries, _, _ = bom_gen.generate_bom(smd_only=False)

        # Should include both SMD and PTH components
        smd_entries = [entry for entry in bom_entries if entry.smd == "SMD"]
        pth_entries = [entry for entry in bom_entries if entry.smd == "PTH"]

        # Should have both types
        self.assertGreater(
            len(smd_entries), 0, "Should have at least one SMD component"
        )
        self.assertGreater(
            len(pth_entries), 0, "Should have at least one PTH component"
        )

        # Clean up
        Path(temp_inv2.name).unlink()

    def test_is_smd_component_method(self):
        """Test the _is_smd_component helper method"""
        bom_gen = BOMGenerator(self.matcher)

        # Test explicit SMD marking
        smd_entry = BOMEntry(
            reference="R1",
            quantity=1,
            value="330R",
            footprint="0603",
            lcsc="C123",
            manufacturer="TEST",
            mfgpn="TEST",
            description="Test",
            datasheet="",
            smd="SMD",
        )
        self.assertTrue(bom_gen._is_smd_component(smd_entry))

        # Test explicit PTH marking
        pth_entry = BOMEntry(
            reference="R2",
            quantity=1,
            value="330R",
            footprint="THT",
            lcsc="C124",
            manufacturer="TEST",
            mfgpn="TEST",
            description="Test",
            datasheet="",
            smd="PTH",
        )
        self.assertFalse(bom_gen._is_smd_component(pth_entry))

        # Test footprint-based inference for unclear SMD field
        unclear_smd_entry = BOMEntry(
            reference="R3",
            quantity=1,
            value="330R",
            footprint="PCM_SPCoast:0603-RES",
            lcsc="C125",
            manufacturer="TEST",
            mfgpn="TEST",
            description="Test",
            datasheet="",
            smd="",  # Unclear SMD field
        )
        self.assertTrue(
            bom_gen._is_smd_component(unclear_smd_entry)
        )  # Should infer SMD from 0603


class TestDebugFunctionality(unittest.TestCase):
    """Test debug functionality and alternative match display"""

    def setUp(self):
        # Create test inventory with multiple matching items
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        csv_content = [
            (
                "IPN,Name,Category,Package,Value,Tolerance,LCSC,Manufacturer,MFGPN,"
                "Description,Priority"
            ),
            (
                "R001,330R 5%,RES,0603,330R,5%,C25231,UNI-ROYAL,0603WAJ0331T5E,"
                "330Ω 5% 0603,1"
            ),
            (
                "R002,330R 1%,RES,0603,330R,1%,C25232,YAGEO,RC0603FR-07330RL,"
                "330Ω 1% 0603,2"
            ),
            (
                "R003,330R 10%,RES,0603,330R,10%,C25233,VISHAY,CRCW0603330RJNEA,"
                "330Ω 10% 0603,3"
            ),
        ]
        self.temp_inv.write("\n".join(csv_content))
        self.temp_inv.close()

        self.matcher = InventoryMatcher(Path(self.temp_inv.name))
        self.components = [
            Component("R1", "Device:R", "330R", "PCM_SPCoast:0603-RES"),
        ]

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_debug_mode_enabled(self):
        """Test that debug mode works without polluting BOM notes"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom(debug=True)

        self.assertEqual(len(bom_entries), 1)
        entry = bom_entries[0]

        # Debug information should NOT be in the BOM notes - it's handled by console output
        # BOM files should remain clean and professional
        self.assertNotIn("DEBUG:", entry.notes or "")

        # Verify basic BOM entry structure is intact
        self.assertTrue(entry.reference)
        self.assertTrue(entry.lcsc)
        self.assertTrue(entry.description)

    def test_debug_alternatives_displayed(self):
        """Test that debug mode processes multiple matches correctly"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom(debug=True)

        entry = bom_entries[0]

        # Debug information should NOT pollute BOM notes
        self.assertNotIn("ALTERNATIVES:", entry.notes or "")
        self.assertNotIn("Alt1:", entry.notes or "")

        # However, the BOM should still contain the best match
        self.assertTrue(entry.lcsc)  # Should have matched a component
        self.assertIn(
            "C252", entry.lcsc
        )  # Should match one of the LCSC numbers (C25231, C25232, C25233)

    def test_debug_mode_disabled(self):
        """Test that normal mode doesn't show debug information"""
        bom_gen = BOMGenerator(self.matcher)
        bom_gen.components = self.components
        bom_entries, _, _ = bom_gen.generate_bom(debug=False)

        self.assertEqual(len(bom_entries), 1)
        entry = bom_entries[0]

        # Should not contain debug information
        self.assertNotIn("DEBUG:", entry.notes)
        self.assertNotIn("ALTERNATIVES:", entry.notes)
        self.assertNotIn("Component: R1", entry.notes)

    def test_find_matches_debug_signature(self):
        """Test that find_matches returns proper 3-tuple with debug info"""
        component = Component("R1", "Device:R", "330R", "PCM_SPCoast:0603-RES")

        # Test with debug enabled
        matches = self.matcher.find_matches(component, debug=True)

        self.assertGreater(len(matches), 0)

        # Each match should be a 3-tuple: (item, score, debug_info)
        for match in matches:
            self.assertEqual(len(match), 3)
            item, score, debug_info = match
            self.assertIsInstance(item, InventoryItem)
            self.assertIsInstance(score, int)
            # Debug info should be present for first match, may be None for others
            if debug_info is not None:
                self.assertIsInstance(debug_info, str)


class TestDiagnosticWarning(unittest.TestCase):
    """Test diagnostic warning functionality"""

    def setUp(self):
        # Create a minimal test setup
        self.temp_inv = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        )
        csv_content = [
            "IPN,Name,Category,Package,Value,SMD,LCSC,Priority",
            "R001,330R,RES,0603,330R,SMD,C25231,1",
        ]
        self.temp_inv.write("\n".join(csv_content))
        self.temp_inv.close()

        self.matcher = InventoryMatcher(Path(self.temp_inv.name))
        self.bom_gen = BOMGenerator(self.matcher)

    def tearDown(self):
        Path(self.temp_inv.name).unlink()

    def test_smd_warning_with_invalid_value(self):
        """Test that diagnostic warnings are generated for invalid SMD field values"""
        import sys
        from io import StringIO

        # Capture stderr to check for warnings
        old_stderr = sys.stderr
        captured_stderr = StringIO()
        sys.stderr = captured_stderr

        try:
            # Create an entry with invalid SMD field value
            entry = BOMEntry(
                reference="R1",
                quantity=1,
                value="330R",
                footprint="0603",
                lcsc="C25231",
                manufacturer="TEST",
                mfgpn="TEST",
                description="Test",
                datasheet="",
                smd="Q16",  # Invalid SMD value
            )

            # This should trigger the warning in _is_smd_component
            is_smd = self.bom_gen._is_smd_component(entry)

            # Check that warning was printed to stderr
            stderr_output = captured_stderr.getvalue()
            self.assertIn("Warning: Unexpected SMD field value", stderr_output)
            self.assertIn("Q16", stderr_output)
            self.assertIn("R1", stderr_output)

            # Should default to non-SMD
            self.assertFalse(is_smd)

        finally:
            sys.stderr = old_stderr


if __name__ == "__main__":
    unittest.main()
