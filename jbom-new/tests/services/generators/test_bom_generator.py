"""Unit tests for BOMGenerator service."""

from jbom.services.bom_generator import BOMGenerator, BOMEntry, BOMData
from jbom.common.types import Component


class TestBOMGenerator:
    """Test the BOMGenerator service in isolation."""

    def test_init_with_default_strategy(self):
        """Test initialization with default aggregation strategy."""
        generator = BOMGenerator()
        assert generator.aggregation_strategy == "value_footprint"

    def test_init_with_custom_strategy(self):
        """Test initialization with custom aggregation strategy."""
        generator = BOMGenerator("value_only")
        assert generator.aggregation_strategy == "value_only"

    def test_generate_bom_data_empty_components(self):
        """Test BOM generation with empty component list."""
        generator = BOMGenerator()
        components = []

        bom_data = generator.generate_bom_data(components)

        assert bom_data.project_name == "Project"
        assert len(bom_data.entries) == 0
        assert bom_data.total_components == 0
        assert bom_data.total_line_items == 0

    def test_generate_bom_data_single_component(self):
        """Test BOM generation with single component."""
        generator = BOMGenerator()
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-1",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            )
        ]

        bom_data = generator.generate_bom_data(components, "TestProject")

        assert bom_data.project_name == "TestProject"
        assert len(bom_data.entries) == 1
        assert bom_data.total_components == 1
        assert bom_data.total_line_items == 1

        entry = bom_data.entries[0]
        assert entry.references == ["R1"]
        assert entry.value == "10K"
        assert entry.footprint == "R_0603_1608Metric"
        assert entry.lib_id == "Device:R"
        assert entry.quantity == 1

    def test_generate_bom_data_multiple_same_components(self):
        """Test BOM generation with multiple identical components."""
        generator = BOMGenerator()
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-1",
                properties={"Tolerance": "5%"},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
            Component(
                reference="R2",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-2",
                properties={"Tolerance": "5%"},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
        ]

        bom_data = generator.generate_bom_data(components)

        assert len(bom_data.entries) == 1
        assert bom_data.total_components == 2
        assert bom_data.total_line_items == 1

        entry = bom_data.entries[0]
        assert sorted(entry.references) == ["R1", "R2"]
        assert entry.value == "10K"
        assert entry.quantity == 2
        assert entry.attributes["Tolerance"] == "5%"

    def test_generate_bom_data_different_components(self):
        """Test BOM generation with different components."""
        generator = BOMGenerator()
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-1",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
            Component(
                reference="C1",
                lib_id="Device:C",
                value="100nF",
                footprint="C_0603_1608Metric",
                uuid="uuid-2",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
        ]

        bom_data = generator.generate_bom_data(components)

        assert len(bom_data.entries) == 2
        assert bom_data.total_components == 2
        assert bom_data.total_line_items == 2

        # Entries should be sorted by reference
        entries = sorted(bom_data.entries, key=lambda e: e.references[0])
        assert entries[0].references == ["C1"]
        assert entries[0].value == "100nF"
        assert entries[1].references == ["R1"]
        assert entries[1].value == "10K"

    def test_apply_filters_exclude_dnp(self):
        """Test filtering excludes DNP components."""
        generator = BOMGenerator()
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-1",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
            Component(
                reference="R2",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-2",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=True,
            ),
        ]

        bom_data = generator.generate_bom_data(components)

        assert len(bom_data.entries) == 1
        assert bom_data.entries[0].references == ["R1"]
        assert bom_data.metadata["total_input_components"] == 2
        assert bom_data.metadata["filtered_components"] == 1

    def test_apply_filters_exclude_not_in_bom(self):
        """Test filtering excludes components not in BOM."""
        generator = BOMGenerator()
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-1",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
            Component(
                reference="TP1",
                lib_id="Device:TestPoint",
                value="TestPoint",
                footprint="TestPoint_Pad_1.0x1.0mm",
                uuid="uuid-2",
                properties={},
                in_bom=False,
                exclude_from_sim=False,
                dnp=False,
            ),
        ]

        bom_data = generator.generate_bom_data(components)

        assert len(bom_data.entries) == 1
        assert bom_data.entries[0].references == ["R1"]

    def test_apply_filters_exclude_power_symbols(self):
        """Test filtering excludes power symbols (# prefix)."""
        generator = BOMGenerator()
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-1",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
            Component(
                reference="#PWR01",
                lib_id="power:GND",
                value="",
                footprint="",
                uuid="uuid-2",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
        ]

        bom_data = generator.generate_bom_data(components)

        assert len(bom_data.entries) == 1
        assert bom_data.entries[0].references == ["R1"]

    def test_aggregation_strategy_value_only(self):
        """Test aggregation by value only (ignoring footprint)."""
        generator = BOMGenerator("value_only")
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-1",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
            Component(
                reference="R2",
                lib_id="Device:R",
                value="10K",
                footprint="R_0805_2012Metric",
                uuid="uuid-2",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
        ]

        bom_data = generator.generate_bom_data(components)

        # Should aggregate into one entry despite different footprints
        assert len(bom_data.entries) == 1
        assert bom_data.entries[0].quantity == 2
        assert sorted(bom_data.entries[0].references) == ["R1", "R2"]

    def test_aggregation_strategy_lib_id_value(self):
        """Test aggregation by lib_id and value."""
        generator = BOMGenerator("lib_id_value")
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-1",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
            Component(
                reference="RV1",
                lib_id="Device:R_Variable",
                value="10K",
                footprint="Potentiometer_Alps_RK09K_Single_Vertical",
                uuid="uuid-2",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
        ]

        bom_data = generator.generate_bom_data(components)

        # Should NOT aggregate due to different lib_id
        assert len(bom_data.entries) == 2

    def test_property_merging(self):
        """Test that properties are properly merged from multiple components."""
        generator = BOMGenerator()
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-1",
                properties={"Tolerance": "5%", "Wattage": "0.1W"},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
            Component(
                reference="R2",
                lib_id="Device:R",
                value="10K",
                footprint="R_0603_1608Metric",
                uuid="uuid-2",
                properties={"Tolerance": "5%", "Manufacturer": "Yageo"},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
        ]

        bom_data = generator.generate_bom_data(components)

        assert len(bom_data.entries) == 1
        entry = bom_data.entries[0]
        assert entry.attributes["Tolerance"] == "5%"
        assert entry.attributes["Wattage"] == "0.1W"
        assert entry.attributes["Manufacturer"] == "Yageo"


class TestBOMEntry:
    """Test BOMEntry data class."""

    def test_references_string_single(self):
        """Test references_string with single reference."""
        entry = BOMEntry(["R1"], "10K", "R_0603", 1)
        assert entry.references_string == "R1"

    def test_references_string_multiple_sorted(self):
        """Test references_string with multiple references, properly sorted."""
        entry = BOMEntry(["R3", "R1", "R2"], "10K", "R_0603", 3)
        assert entry.references_string == "R1, R2, R3"


class TestBOMData:
    """Test BOMData data class."""

    def test_empty_bom_data(self):
        """Test BOMData with no entries."""
        bom_data = BOMData("Test", [])
        assert bom_data.total_components == 0
        assert bom_data.total_line_items == 0

    def test_bom_data_totals(self):
        """Test BOMData total calculations."""
        entries = [
            BOMEntry(["R1", "R2"], "10K", "R_0603", 2),
            BOMEntry(["C1"], "100nF", "C_0603", 1),
            BOMEntry(["U1", "U2", "U3"], "LM358", "SOIC-8", 3),
        ]
        bom_data = BOMData("Test", entries)

        assert bom_data.total_components == 6  # 2 + 1 + 3
        assert bom_data.total_line_items == 3  # 3 entries
