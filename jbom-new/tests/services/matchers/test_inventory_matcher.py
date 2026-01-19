"""Unit tests for InventoryMatcher service."""

from pathlib import Path
from unittest.mock import patch

from jbom.services.inventory_matcher import InventoryMatcher
from jbom.services.generators.bom_generator import BOMEntry, BOMData
from jbom.common.types import InventoryItem, DEFAULT_PRIORITY


class TestInventoryMatcher:
    """Test the InventoryMatcher service in isolation."""

    def test_init(self):
        """Test initialization."""
        matcher = InventoryMatcher()
        assert matcher is not None

    def test_enhance_bom_with_inventory_no_file(self):
        """Test enhancement when inventory file doesn't exist."""
        matcher = InventoryMatcher()

        # Create sample BOM data
        bom_data = BOMData(
            project_name="TestProject",
            entries=[BOMEntry(["R1"], "10K", "R_0603_1608Metric", 1, "Device:R", {})],
        )

        non_existent_file = Path("/tmp/nonexistent.csv")
        result = matcher.enhance_bom_with_inventory(bom_data, non_existent_file)

        # Should return original BOM data unchanged
        assert result.project_name == bom_data.project_name
        assert len(result.entries) == 1
        assert result.entries[0].references == ["R1"]
        assert not result.entries[0].attributes.get("inventory_matched")

    def test_enhance_bom_with_inventory_match_found(self):
        """Test enhancement when inventory matches are found."""
        matcher = InventoryMatcher()

        # Create sample BOM data
        bom_data = BOMData(
            project_name="TestProject",
            entries=[
                BOMEntry(["R1"], "10K", "R_0603_1608Metric", 1, "Device:R", {}),
                BOMEntry(["C1"], "100nF", "C_0603_1608Metric", 1, "Device:C", {}),
            ],
        )

        # Mock inventory items
        inventory_items = [
            InventoryItem(
                ipn="RES_10K",
                category="RES",
                value="10K",
                package="0603",
                manufacturer="Yageo",
                mfgpn="RC0603FR-0710KL",
                description="10K 0603 1% resistor",
                tolerance="1%",
                keywords="",
                smd="",
                type="",
                voltage="",
                amperage="",
                wattage="",
                lcsc="",
                datasheet="",
                distributor="",
                distributor_part_number="",
                uuid="",
                fabricator="",
                priority=DEFAULT_PRIORITY,
                source="",
                source_file=None,
                raw_data={},
            ),
            InventoryItem(
                ipn="CAP_100nF",
                category="CAP",
                value="100nF",
                package="0603",
                manufacturer="Murata",
                mfgpn="GRM188R71C104KA01D",
                description="100nF 0603 10% capacitor",
                voltage="16V",
                keywords="",
                smd="",
                type="",
                tolerance="",
                amperage="",
                wattage="",
                lcsc="",
                datasheet="",
                distributor="",
                distributor_part_number="",
                uuid="",
                fabricator="",
                priority=DEFAULT_PRIORITY,
                source="",
                source_file=None,
                raw_data={},
            ),
        ]

        inventory_file = Path("/tmp/inventory.csv")

        # Mock the inventory loading
        with patch.object(matcher, "_load_inventory", return_value=inventory_items):
            result = matcher.enhance_bom_with_inventory(bom_data, inventory_file)

        # Verify enhancement
        assert len(result.entries) == 2
        assert result.metadata["inventory_file"] == str(inventory_file)
        assert result.metadata["matched_entries"] == 2

        # Check resistor enhancement
        resistor_entry = next(e for e in result.entries if "R1" in e.references)
        assert resistor_entry.attributes["inventory_matched"] is True
        assert resistor_entry.attributes["manufacturer"] == "Yageo"
        assert resistor_entry.attributes["manufacturer_part"] == "RC0603FR-0710KL"
        assert resistor_entry.attributes["tolerance"] == "1%"

        # Check capacitor enhancement
        capacitor_entry = next(e for e in result.entries if "C1" in e.references)
        assert capacitor_entry.attributes["inventory_matched"] is True
        assert capacitor_entry.attributes["manufacturer"] == "Murata"
        assert capacitor_entry.attributes["voltage"] == "16V"

    def test_enhance_bom_with_inventory_no_matches(self):
        """Test enhancement when no inventory matches are found."""
        matcher = InventoryMatcher()

        # Create BOM data with components not in inventory
        bom_data = BOMData(
            project_name="TestProject",
            entries=[BOMEntry(["R1"], "47K", "R_0603_1608Metric", 1, "Device:R", {})],
        )

        # Inventory with different components
        inventory_items = [
            InventoryItem(
                ipn="RES_10K",
                category="RES",
                value="10K",
                package="0603",
                manufacturer="",
                mfgpn="",
                description="",
                tolerance="",
                keywords="",
                smd="",
                type="",
                voltage="",
                amperage="",
                wattage="",
                lcsc="",
                datasheet="",
                distributor="",
                distributor_part_number="",
                uuid="",
                fabricator="",
                priority=DEFAULT_PRIORITY,
                source="",
                source_file=None,
                raw_data={},
            )
        ]

        inventory_file = Path("/tmp/inventory.csv")

        with patch.object(matcher, "_load_inventory", return_value=inventory_items):
            result = matcher.enhance_bom_with_inventory(bom_data, inventory_file)

        # No matches should be found
        assert result.metadata["matched_entries"] == 0
        assert not result.entries[0].attributes.get("inventory_matched")

    def test_match_strategies(self):
        """Test different matching strategies."""
        matcher = InventoryMatcher()

        # Create test entry
        entry = BOMEntry(["R1"], "10K", "R_0603_1608Metric", 1, "Device:R", {})

        # Create inventory lookup
        inventory_item = InventoryItem(
            ipn="RES_10K",
            category="RES",
            value="10K",
            package="0603",
            manufacturer="",
            mfgpn="",
            description="",
            tolerance="",
            keywords="",
            smd="",
            type="",
            voltage="",
            amperage="",
            wattage="",
            lcsc="",
            datasheet="",
            distributor="",
            distributor_part_number="",
            uuid="",
            fabricator="",
            priority=DEFAULT_PRIORITY,
            source="",
            source_file=None,
            raw_data={},
        )

        # Test ipn_exact strategy
        exact_lookup = {"RES_10K": inventory_item}
        match = matcher._find_matching_inventory_item(entry, exact_lookup, "ipn_exact")
        assert match == inventory_item

        # Test ipn_fuzzy strategy (should find by value)
        fuzzy_lookup = {"10K": inventory_item}  # Just value, no category
        match = matcher._find_matching_inventory_item(entry, fuzzy_lookup, "ipn_fuzzy")
        assert match == inventory_item

        # Test value_package strategy
        value_package_lookup = {"10K_0603": inventory_item}
        match = matcher._find_matching_inventory_item(
            entry, value_package_lookup, "value_package"
        )
        assert match == inventory_item

    def test_generate_ipn_from_entry(self):
        """Test IPN generation from BOM entry."""
        matcher = InventoryMatcher()

        # Test resistor
        resistor_entry = BOMEntry(["R1"], "10K", "R_0603_1608Metric", 1, "Device:R", {})
        ipn = matcher._generate_ipn_from_entry(resistor_entry)
        assert ipn == "RES_10K"

        # Test capacitor
        capacitor_entry = BOMEntry(
            ["C1"], "100nF", "C_0603_1608Metric", 1, "Device:C", {}
        )
        ipn = matcher._generate_ipn_from_entry(capacitor_entry)
        assert ipn == "CAP_100nF"

        # Test with special characters in value
        special_entry = BOMEntry(
            ["R1"], "4K7/0.1W", "R_0603_1608Metric", 1, "Device:R", {}
        )
        ipn = matcher._generate_ipn_from_entry(special_entry)
        assert ipn == "RES_4K7_0.1W"  # Forward slash replaced with underscore

    def test_detect_category_from_lib_id(self):
        """Test category detection from lib_id."""
        matcher = InventoryMatcher()

        test_cases = [
            ("Device:R", "RES"),
            ("Device:C", "CAP"),
            ("Device:L", "IND"),
            ("Device:D", "DIODE"),
            ("Device:LED", "LED"),
            ("Device:U", "IC"),
            ("Timer:NE555P", "IC"),  # Contains IC
            ("Unknown:Something", "UNKNOWN"),
            ("NoColon", "UNKNOWN"),
            ("", "UNKNOWN"),
        ]

        for lib_id, expected_category in test_cases:
            category = matcher._detect_category_from_lib_id(lib_id)
            assert (
                category == expected_category
            ), f"Failed for {lib_id}: got {category}, expected {expected_category}"

    def test_extract_package(self):
        """Test package extraction from footprint."""
        matcher = InventoryMatcher()

        test_cases = [
            ("R_0603_1608Metric", "0603"),
            ("C_0805_2012Metric", "0805"),
            ("SOT-23", "SOT-23"),
            ("SOIC-8_3.9x4.9mm", "SOIC-8"),
            ("Unknown_Footprint", "Unknown_Footprint"),  # Fallback
            ("", ""),  # Empty
        ]

        for footprint, expected_package in test_cases:
            package = matcher._extract_package(footprint)
            assert (
                package == expected_package
            ), f"Failed for {footprint}: got {package}, expected {expected_package}"

    def test_create_inventory_lookup_strategies(self):
        """Test inventory lookup creation for different strategies."""
        matcher = InventoryMatcher()

        inventory_items = [
            InventoryItem(
                ipn="RES_10K",
                category="RES",
                value="10K",
                package="0603",
                manufacturer="",
                mfgpn="",
                description="",
                tolerance="",
                keywords="",
                smd="",
                type="",
                voltage="",
                amperage="",
                wattage="",
                lcsc="",
                datasheet="",
                distributor="",
                distributor_part_number="",
                uuid="",
                fabricator="",
                priority=DEFAULT_PRIORITY,
                source="",
                source_file=None,
                raw_data={},
            )
        ]

        # Test ipn_exact
        exact_lookup = matcher._create_inventory_lookup(inventory_items, "ipn_exact")
        assert "RES_10K" in exact_lookup
        assert len(exact_lookup) == 1

        # Test ipn_fuzzy (should have both full IPN and value)
        fuzzy_lookup = matcher._create_inventory_lookup(inventory_items, "ipn_fuzzy")
        assert "RES_10K" in fuzzy_lookup  # Full IPN
        assert "10K" in fuzzy_lookup  # Value without category
        assert len(fuzzy_lookup) == 2

        # Test value_package
        value_package_lookup = matcher._create_inventory_lookup(
            inventory_items, "value_package"
        )
        assert "10K_0603" in value_package_lookup
        assert len(value_package_lookup) == 1


class TestInventoryMatcherIntegration:
    """Integration tests for InventoryMatcher with mocked file I/O."""

    def test_full_workflow_with_mocked_inventory_file(self):
        """Test complete workflow with directly mocked inventory loading."""
        matcher = InventoryMatcher()

        # Create BOM data
        bom_data = BOMData(
            project_name="TestProject",
            entries=[
                BOMEntry(
                    ["R1", "R2"],
                    "10K",
                    "R_0603_1608Metric",
                    2,
                    "Device:R",
                    {"Tolerance": "5%"},
                ),
                BOMEntry(["C1"], "100nF", "C_0603_1608Metric", 1, "Device:C", {}),
            ],
        )

        # Create mock inventory items directly (avoiding complex file mocking)
        mock_inventory_items = [
            InventoryItem(
                ipn="RES_10K",
                category="RES",
                value="10K",
                package="0603",
                manufacturer="Yageo",
                mfgpn="RC0603FR-0710KL",
                description="10K 0603 1% resistor",
                tolerance="1%",
                keywords="",
                smd="",
                type="",
                voltage="",
                amperage="",
                wattage="",
                lcsc="",
                datasheet="",
                distributor="",
                distributor_part_number="",
                uuid="",
                fabricator="",
                priority=DEFAULT_PRIORITY,
                source="",
                source_file=None,
                raw_data={},
            ),
            InventoryItem(
                ipn="CAP_100nF",
                category="CAP",
                value="100nF",
                package="0603",
                manufacturer="Murata",
                mfgpn="GRM188R71C104KA01D",
                description="100nF 0603 10% capacitor",
                voltage="16V",
                keywords="",
                smd="",
                type="",
                tolerance="",
                amperage="",
                wattage="",
                lcsc="",
                datasheet="",
                distributor="",
                distributor_part_number="",
                uuid="",
                fabricator="",
                priority=DEFAULT_PRIORITY,
                source="",
                source_file=None,
                raw_data={},
            ),
        ]

        inventory_file = Path("/tmp/test_inventory.csv")

        # Mock just the inventory loading method directly
        with patch.object(
            matcher, "_load_inventory", return_value=mock_inventory_items
        ):
            result = matcher.enhance_bom_with_inventory(
                bom_data, inventory_file, "ipn_fuzzy"
            )

        # Verify results
        assert len(result.entries) == 2
        assert result.metadata["matched_entries"] == 2

        # Check resistor entry (aggregated R1, R2)
        resistor_entry = next(e for e in result.entries if "R1" in e.references)
        assert resistor_entry.quantity == 2
        assert resistor_entry.attributes["inventory_matched"] is True
        assert resistor_entry.attributes["manufacturer"] == "Yageo"
        assert (
            resistor_entry.attributes["tolerance"] == "1%"
        )  # From inventory, overrides original 5%

        # Check capacitor entry
        capacitor_entry = next(e for e in result.entries if "C1" in e.references)
        assert capacitor_entry.attributes["inventory_matched"] is True
        assert capacitor_entry.attributes["manufacturer"] == "Murata"
        assert capacitor_entry.attributes["voltage"] == "16V"
