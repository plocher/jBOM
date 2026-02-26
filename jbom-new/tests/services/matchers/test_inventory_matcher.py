"""Unit tests for InventoryMatcher service (Phase 3 — sophisticated pipeline)."""

from pathlib import Path
from unittest.mock import patch

from jbom.services.inventory_matcher import InventoryMatcher
from jbom.services.bom_generator import BOMEntry, BOMData
from jbom.common.types import Component, InventoryItem, DEFAULT_PRIORITY


def _make_inventory_item(
    *,
    ipn: str = "",
    category: str = "",
    value: str = "",
    package: str = "",
    manufacturer: str = "",
    mfgpn: str = "",
    description: str = "",
    tolerance: str = "",
    voltage: str = "",
    wattage: str = "",
    lcsc: str = "",
    datasheet: str = "",
    fabricator: str = "",
    priority: int = DEFAULT_PRIORITY,
    raw_data: dict | None = None,
) -> InventoryItem:
    """Convenience helper that auto-populates raw_data from kwargs."""
    rd = raw_data if raw_data is not None else {}
    # Ensure raw_data mirrors the key fields (as InventoryReader would do)
    for key, val in {
        "IPN": ipn,
        "Category": category,
        "Value": value,
        "Package": package,
        "Manufacturer": manufacturer,
        "MFGPN": mfgpn,
        "Description": description,
        "Tolerance": tolerance,
        "Voltage": voltage,
        "Wattage": wattage,
        "LCSC": lcsc,
        "Datasheet": datasheet,
    }.items():
        rd.setdefault(key, val)

    return InventoryItem(
        ipn=ipn,
        keywords="",
        category=category,
        description=description,
        smd="",
        value=value,
        type="",
        tolerance=tolerance,
        voltage=voltage,
        amperage="",
        wattage=wattage,
        lcsc=lcsc,
        manufacturer=manufacturer,
        mfgpn=mfgpn,
        datasheet=datasheet,
        package=package,
        distributor="",
        distributor_part_number="",
        uuid="",
        fabricator=fabricator,
        priority=priority,
        source="CSV",
        source_file=None,
        raw_data=rd,
    )


class TestInventoryMatcher:
    """Test the InventoryMatcher service in isolation."""

    def test_init(self) -> None:
        """Test initialization."""
        matcher = InventoryMatcher()
        assert matcher is not None

    def test_enhance_bom_with_inventory_no_file(self) -> None:
        """Test enhancement when inventory file doesn't exist."""
        matcher = InventoryMatcher()

        bom_data = BOMData(
            project_name="TestProject",
            entries=[BOMEntry(["R1"], "10K", "R_0603_1608Metric", 1, "Device:R", {})],
        )

        result = matcher.enhance_bom_with_inventory(
            bom_data, Path("/tmp/nonexistent.csv")
        )

        assert result.project_name == bom_data.project_name
        assert len(result.entries) == 1
        assert not result.entries[0].attributes.get("inventory_matched")

    def test_enhance_bom_with_inventory_match_found(self) -> None:
        """Test enhancement when inventory matches are found via sophisticated matcher."""
        matcher = InventoryMatcher()

        bom_data = BOMData(
            project_name="TestProject",
            entries=[
                BOMEntry(["R1"], "10K", "R_0603_1608Metric", 1, "Device:R", {}),
                BOMEntry(["C1"], "100nF", "C_0603_1608Metric", 1, "Device:C", {}),
            ],
        )

        inventory_items = [
            _make_inventory_item(
                ipn="RES_10K",
                category="RESISTOR",
                value="10K",
                package="0603",
                manufacturer="Yageo",
                mfgpn="RC0603FR-0710KL",
                description="10K 0603 1% resistor",
                tolerance="1%",
                lcsc="C25804",
            ),
            _make_inventory_item(
                ipn="CAP_100nF",
                category="CAPACITOR",
                value="100nF",
                package="0603",
                manufacturer="Murata",
                mfgpn="GRM188R71C104KA01D",
                description="100nF 0603 10% capacitor",
                voltage="16V",
                lcsc="C14663",
            ),
        ]

        inventory_file = Path("/tmp/inventory.csv")

        with patch.object(matcher, "_load_inventory", return_value=inventory_items):
            result = matcher.enhance_bom_with_inventory(bom_data, inventory_file)

        assert len(result.entries) == 2
        assert result.metadata["inventory_file"] == str(inventory_file)
        assert result.metadata["matched_entries"] == 2
        assert result.metadata["orphan_entries"] == 0

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

    def test_enhance_bom_with_inventory_no_matches(self) -> None:
        """Test enhancement when no inventory matches are found (orphan reporting)."""
        matcher = InventoryMatcher()

        bom_data = BOMData(
            project_name="TestProject",
            entries=[BOMEntry(["R1"], "47K", "R_0603_1608Metric", 1, "Device:R", {})],
        )

        inventory_items = [
            _make_inventory_item(
                ipn="RES_10K",
                category="RESISTOR",
                value="10K",
                package="0603",
                lcsc="C25804",
            ),
        ]

        inventory_file = Path("/tmp/inventory.csv")

        with patch.object(matcher, "_load_inventory", return_value=inventory_items):
            result = matcher.enhance_bom_with_inventory(bom_data, inventory_file)

        assert result.metadata["matched_entries"] == 0
        assert result.metadata["orphan_entries"] == 1
        assert "R1" in result.metadata["orphan_references"][0]
        assert not result.entries[0].attributes.get("inventory_matched")

    def test_bom_entry_to_component(self) -> None:
        """Test BOM entry → Component conversion preserves representative data."""
        entry = BOMEntry(
            ["R1", "R2"],
            "10K",
            "R_0603_1608Metric",
            2,
            "Device:R",
            {"Tolerance": "5%"},
        )

        component = InventoryMatcher._bom_entry_to_component(entry)

        assert isinstance(component, Component)
        assert component.reference == "R1"
        assert component.lib_id == "Device:R"
        assert component.value == "10K"
        assert component.footprint == "R_0603_1608Metric"
        assert component.properties["Tolerance"] == "5%"

    def test_fabricator_filtering_fallback(self) -> None:
        """When fabricator config is unavailable, uses unfiltered inventory."""
        matcher = InventoryMatcher()

        items = [
            _make_inventory_item(
                ipn="RES_10K",
                category="RESISTOR",
                value="10K",
                package="0603",
            ),
        ]

        # Non-existent fabricator → fallback to raw items
        result = matcher._filter_by_fabricator(items, "nonexistent_fab", None)
        assert len(result) == len(items)

    def test_metadata_includes_fabricator_info(self) -> None:
        """Enhanced metadata includes fabricator and eligible item counts."""
        matcher = InventoryMatcher()

        bom_data = BOMData(
            project_name="TestProject",
            entries=[BOMEntry(["R1"], "10K", "R_0603_1608Metric", 1, "Device:R", {})],
        )

        inventory_items = [
            _make_inventory_item(
                ipn="RES_10K",
                category="RESISTOR",
                value="10K",
                package="0603",
                lcsc="C25804",
            ),
        ]

        with patch.object(matcher, "_load_inventory", return_value=inventory_items):
            result = matcher.enhance_bom_with_inventory(bom_data, Path("/tmp/inv.csv"))

        assert "fabricator_id" in result.metadata
        assert "eligible_items" in result.metadata
        assert result.metadata["fabricator_id"] == "generic"


class TestInventoryMatcherIntegration:
    """Integration tests for InventoryMatcher with the full sophisticated pipeline."""

    def test_full_workflow_with_mocked_inventory_file(self) -> None:
        """Test complete pipeline: load → filter → match → enrich."""
        matcher = InventoryMatcher()

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

        mock_inventory_items = [
            _make_inventory_item(
                ipn="RES_10K",
                category="RESISTOR",
                value="10K",
                package="0603",
                manufacturer="Yageo",
                mfgpn="RC0603FR-0710KL",
                description="10K 0603 1% resistor",
                tolerance="1%",
                lcsc="C25804",
            ),
            _make_inventory_item(
                ipn="CAP_100nF",
                category="CAPACITOR",
                value="100nF",
                package="0603",
                manufacturer="Murata",
                mfgpn="GRM188R71C104KA01D",
                description="100nF 0603 10% capacitor",
                voltage="16V",
                lcsc="C14663",
            ),
        ]

        inventory_file = Path("/tmp/test_inventory.csv")

        with patch.object(
            matcher, "_load_inventory", return_value=mock_inventory_items
        ):
            result = matcher.enhance_bom_with_inventory(bom_data, inventory_file)

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

    def test_fabricator_specific_matching(self) -> None:
        """Test that fabricator_id parameter flows through correctly."""
        matcher = InventoryMatcher()

        bom_data = BOMData(
            project_name="TestProject",
            entries=[BOMEntry(["R1"], "10K", "R_0603_1608Metric", 1, "Device:R", {})],
        )

        inventory_items = [
            _make_inventory_item(
                ipn="RES_10K",
                category="RESISTOR",
                value="10K",
                package="0603",
                lcsc="C25804",
                mfgpn="RC0603FR-0710KL",
            ),
        ]

        inventory_file = Path("/tmp/test_inventory.csv")

        with patch.object(matcher, "_load_inventory", return_value=inventory_items):
            result = matcher.enhance_bom_with_inventory(
                bom_data, inventory_file, fabricator_id="jlc"
            )

        assert result.metadata["fabricator_id"] == "jlc"
