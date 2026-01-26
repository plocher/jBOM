"""Unit tests for InventoryMatcher service."""

from pathlib import Path
from unittest.mock import patch

from jbom.services.inventory_matcher import InventoryMatcher
from jbom.services.bom_generator import BOMEntry, BOMData
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

    def test_matching_logic(self):
        """Test the simplified matching logic."""
        matcher = InventoryMatcher()

        # Create test entry
        entry = BOMEntry(["R1"], "10K", "R_0603_1608Metric", 1, "Device:R", {})

        # Create inventory items
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
        inventory_items = [inventory_item]

        # Test value-based matching
        match = matcher._find_matching_inventory_item(entry, inventory_items)
        assert match == inventory_item

    def test_extract_package(self):
        """Test package extraction from footprint."""
        matcher = InventoryMatcher()

        # Test 0603 package extraction
        footprint = "R_0603_1608Metric"
        package = matcher._extract_package(footprint)
        assert package == "0603"

        # Test SOIC package extraction
        footprint = "SOIC-8_3.9x4.9mm_P1.27mm"
        package = matcher._extract_package(footprint)
        assert package == "SOIC-8"


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
            result = matcher.enhance_bom_with_inventory(bom_data, inventory_file)

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
