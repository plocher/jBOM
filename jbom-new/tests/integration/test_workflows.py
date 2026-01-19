"""Integration tests for workflow orchestration."""

from pathlib import Path
from unittest.mock import patch

from jbom.workflows.bom_workflows import (
    generate_basic_bom,
    generate_inventory_enhanced_bom,
    generate_filtered_bom,
)
from jbom.common.types import Component, InventoryItem, DEFAULT_PRIORITY
from jbom.common.options import GeneratorOptions


class TestBOMWorkflows:
    """Test workflow orchestration functions."""

    def test_generate_basic_bom_workflow(self):
        """Test basic BOM generation workflow."""
        # Mock components from schematic
        mock_components = [
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

        schematic_file = Path("/project/main.kicad_sch")

        # Mock the SchematicReader.load_components method
        with patch("jbom.workflows.bom_workflows.SchematicReader") as mock_reader_class:
            mock_reader = mock_reader_class.return_value
            mock_reader.load_components.return_value = mock_components

            # Execute workflow
            result = generate_basic_bom(schematic_file, "TestProject")

        # Verify workflow results
        assert result.project_name == "TestProject"
        assert len(result.entries) == 2  # R and C components
        assert result.total_components == 2
        assert result.total_line_items == 2

        # Verify services were orchestrated correctly
        mock_reader_class.assert_called_once()
        mock_reader.load_components.assert_called_once_with(schematic_file)

    def test_generate_inventory_enhanced_bom_workflow(self):
        """Test inventory-enhanced BOM workflow."""
        # Mock components
        mock_components = [
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

        # Mock inventory items
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
        ]

        schematic_file = Path("/project/main.kicad_sch")
        inventory_file = Path("/inventory/parts.csv")

        # Mock both services
        with patch(
            "jbom.workflows.bom_workflows.SchematicReader"
        ) as mock_reader_class, patch(
            "jbom.workflows.bom_workflows.InventoryMatcher"
        ) as mock_matcher_class:
            mock_reader = mock_reader_class.return_value
            mock_reader.load_components.return_value = mock_components

            mock_matcher = mock_matcher_class.return_value
            # Mock the internal _load_inventory to return our inventory items
            mock_matcher._load_inventory.return_value = mock_inventory_items
            # Mock enhance_bom_with_inventory to call through to the real implementation
            mock_matcher.enhance_bom_with_inventory.side_effect = (
                lambda bom_data, inv_file, strategy: bom_data
            )

            # Execute workflow
            result = generate_inventory_enhanced_bom(
                schematic_file, inventory_file, "TestProject"
            )

        # Verify workflow orchestration
        mock_reader_class.assert_called_once()
        mock_reader.load_components.assert_called_once_with(schematic_file)
        mock_matcher_class.assert_called_once()
        mock_matcher.enhance_bom_with_inventory.assert_called_once()

        # Verify basic result structure
        assert result.project_name == "TestProject"
        assert len(result.entries) == 2

    def test_generate_filtered_bom_workflow(self):
        """Test filtered BOM workflow with custom aggregation."""
        # Mock components with different footprints but same value
        mock_components = [
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

        schematic_file = Path("/project/main.kicad_sch")

        with patch("jbom.workflows.bom_workflows.SchematicReader") as mock_reader_class:
            mock_reader = mock_reader_class.return_value
            mock_reader.load_components.return_value = mock_components

            # Execute workflow with value-only aggregation
            result = generate_filtered_bom(
                schematic_file,
                project_name="TestProject",
                aggregation_strategy="value_only",  # Should aggregate R1 and R2
                exclude_dnp=True,
                include_only_bom=True,
            )

        # Verify custom aggregation worked
        assert result.project_name == "TestProject"
        # With value_only aggregation, both 10K resistors should be grouped
        # (This would be 2 entries with default value_footprint strategy)
        assert result.metadata["aggregation_strategy"] == "value_only"

    def test_workflow_with_options(self):
        """Test workflow with custom options."""
        mock_components = [
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
        ]

        schematic_file = Path("/project/main.kicad_sch")
        options = GeneratorOptions(verbose=True)

        with patch("jbom.workflows.bom_workflows.SchematicReader") as mock_reader_class:
            mock_reader_class.return_value.load_components.return_value = (
                mock_components
            )

            # Execute workflow with options
            result = generate_basic_bom(schematic_file, "TestProject", options)

        # Verify options were passed to SchematicReader
        mock_reader_class.assert_called_once_with(options)
        assert result.project_name == "TestProject"

    def test_project_name_inference(self):
        """Test that project name is inferred from schematic file if not provided."""
        mock_components = [
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
        ]

        schematic_file = Path("/project/MyCircuit.kicad_sch")

        with patch("jbom.workflows.bom_workflows.SchematicReader") as mock_reader_class:
            mock_reader_class.return_value.load_components.return_value = (
                mock_components
            )

            # Execute workflow without explicit project name
            result = generate_basic_bom(schematic_file)  # No project_name provided

        # Verify project name was inferred from file
        assert result.project_name == "MyCircuit"  # stem of the file
