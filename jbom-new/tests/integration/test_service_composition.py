"""Integration tests demonstrating service composition."""

from pathlib import Path
from unittest.mock import patch

from jbom.services.readers.schematic_reader import SchematicReader
from jbom.services.generators.bom_generator import BOMGenerator
from jbom.common.types import Component
from jbom.common.options import GeneratorOptions


class TestServiceComposition:
    """Test composing multiple services together."""

    def test_schematic_reader_plus_bom_generator_composition(self):
        """Demonstrate SchematicReader + BOMGenerator working together."""
        # Create services independently
        reader = SchematicReader()
        generator = BOMGenerator()

        # Mock components that would be read from a schematic
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
            Component(
                reference="C1",
                lib_id="Device:C",
                value="100nF",
                footprint="C_0603_1608Metric",
                uuid="uuid-3",
                properties={"Voltage": "50V"},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            ),
            # This component should be filtered out (DNP)
            Component(
                reference="R3",
                lib_id="Device:R",
                value="0",
                footprint="R_0603_1608Metric",
                uuid="uuid-4",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=True,
            ),
        ]

        # Mock the schematic reader to return our test components
        with patch.object(reader, "load_components", return_value=mock_components):
            # Step 1: Load components from schematic (using reader service)
            components = reader.load_components(Path("/tmp/test.kicad_sch"))

            # Step 2: Generate BOM from components (using generator service)
            bom_data = generator.generate_bom_data(components, "TestProject")

        # Verify the composition worked correctly
        assert len(components) == 4  # All components loaded

        assert bom_data.project_name == "TestProject"
        assert (
            bom_data.total_line_items == 2
        )  # R1+R2 aggregated, C1 separate, R3 filtered out
        assert bom_data.total_components == 3  # 2 resistors + 1 capacitor

        # Verify aggregation worked correctly

        # R1 and R2 should be aggregated
        resistor_entry = next(e for e in bom_data.entries if "R1" in e.references)
        assert sorted(resistor_entry.references) == ["R1", "R2"]
        assert resistor_entry.value == "10K"
        assert resistor_entry.quantity == 2
        assert resistor_entry.attributes["Tolerance"] == "5%"

        # C1 should be its own entry
        capacitor_entry = next(e for e in bom_data.entries if "C1" in e.references)
        assert capacitor_entry.references == ["C1"]
        assert capacitor_entry.value == "100nF"
        assert capacitor_entry.quantity == 1
        assert capacitor_entry.attributes["Voltage"] == "50V"

        # R3 should not appear (filtered out due to DNP)
        all_references = [ref for entry in bom_data.entries for ref in entry.references]
        assert "R3" not in all_references

    def test_service_configuration_independence(self):
        """Test that services can be configured independently."""
        # Different reader configurations
        verbose_reader = SchematicReader(GeneratorOptions(verbose=True))
        quiet_reader = SchematicReader(GeneratorOptions(verbose=False))

        # Different generator configurations
        value_only_generator = BOMGenerator("value_only")
        lib_id_generator = BOMGenerator("lib_id_value")

        # All services should maintain their configurations
        assert verbose_reader.options.verbose is True
        assert quiet_reader.options.verbose is False
        assert value_only_generator.aggregation_strategy == "value_only"
        assert lib_id_generator.aggregation_strategy == "lib_id_value"

    def test_workflow_like_composition(self):
        """Demonstrate workflow-like usage pattern."""
        # This is how a workflow might use multiple services

        # Setup: Services with specific configurations
        reader = SchematicReader()
        # Use value-only aggregation for this workflow
        generator = BOMGenerator("value_only")

        # Mock different footprint components with same value
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

        # Workflow execution
        with patch.object(reader, "load_components", return_value=mock_components):
            # Input: Schematic file path
            schematic_path = Path("/project/main.kicad_sch")

            # Step 1: Read schematic
            components = reader.load_components(schematic_path)

            # Step 2: Generate BOM (with value-only aggregation)
            bom_data = generator.generate_bom_data(
                components, project_name="MyProject", filters={"exclude_dnp": True}
            )

            # Step 3: Workflow could now pass BOM data to formatter, inventory matcher, etc.
            # (demonstrating how services compose in workflows)

        # Verify workflow results
        # With value_only aggregation, both resistors aggregate despite different footprints
        assert len(bom_data.entries) == 1
        assert bom_data.entries[0].quantity == 2
        assert sorted(bom_data.entries[0].references) == ["R1", "R2"]

        # Metadata shows filtering and aggregation worked
        assert bom_data.metadata["aggregation_strategy"] == "value_only"
        assert bom_data.metadata["total_input_components"] == 2
        assert bom_data.metadata["filtered_components"] == 2  # None filtered out
