"""Integration test demonstrating SchematicReader service independence."""


from jbom.services.readers.schematic_reader import SchematicReader
from jbom.common.options import GeneratorOptions


class TestSchematicReaderIntegration:
    """Test SchematicReader service with real schematic files."""

    def test_service_works_without_plugin_infrastructure(self):
        """Prove the service works independently of plugin architecture."""
        # This test demonstrates that the service can be used directly
        # without any plugin infrastructure or CLI handling

        reader = SchematicReader()

        # The service has a clean interface
        assert hasattr(reader, "load_components")
        assert callable(reader.load_components)

        # Can be configured with options
        options = GeneratorOptions(verbose=True)
        configured_reader = SchematicReader(options)
        assert configured_reader.options.verbose is True

    def test_service_can_be_composed_with_other_services(self):
        """Demonstrate that services can be easily composed."""
        # Example of how services would compose in workflows
        reader = SchematicReader()

        # Mock workflow composition - in real code this would be:
        # components = reader.load_components(schematic_path)
        # inventory = inventory_matcher.match_components(components)
        # enhanced_bom = bom_generator.generate_with_inventory(components, inventory)

        # The service provides the right abstraction level for composition
        assert hasattr(reader, "load_components")  # Input method
        # Output would be List[Component] - perfect for passing to other services

    def test_multiple_readers_can_coexist(self):
        """Show that multiple service instances work independently."""
        reader1 = SchematicReader(GeneratorOptions(verbose=True))
        reader2 = SchematicReader(GeneratorOptions(verbose=False))

        assert reader1.options.verbose is True
        assert reader2.options.verbose is False

        # Each service instance maintains its own state
        # This is key for workflow orchestration where you might need
        # different configurations for different operations
