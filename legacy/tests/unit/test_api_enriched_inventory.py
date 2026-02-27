#!/usr/bin/env python3
"""Unit tests for generate_enriched_inventory API function."""
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

from jbom.api import generate_enriched_inventory, InventoryOptions
from jbom.common.types import Component, InventoryItem


class TestGenerateEnrichedInventoryAPI(unittest.TestCase):
    """Test the generate_enriched_inventory API function."""

    def setUp(self):
        """Set up test components and mocks."""
        self.mock_components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10k",
                footprint="Resistor_SMD:R_0603_1608Metric",
                properties={"Tolerance": "1%"},
            ),
            Component(
                reference="C1",
                lib_id="Device:C",
                value="100nF",
                footprint="Capacitor_SMD:C_0603_1608Metric",
                properties={"Voltage": "50V"},
            ),
        ]

    @patch("jbom.api.BOMGenerator")
    def test_generate_inventory_without_search(self, mock_bom_generator_class):
        """Test basic inventory generation without search."""
        # Mock BOMGenerator
        mock_generator = Mock()
        mock_bom_generator_class.return_value = mock_generator
        mock_generator.discover_input.return_value = Path("test.kicad_sch")
        mock_generator.load_input.return_value = self.mock_components

        result = generate_enriched_inventory(input="test_project")

        self.assertTrue(result["success"])
        self.assertEqual(result["component_count"], 2)
        self.assertIn("inventory_items", result)
        self.assertIn("field_names", result)
        self.assertEqual(result["search_stats"]["search_enabled"], False)

    @patch("jbom.api.MouserProvider")
    @patch("jbom.api.InventoryEnricher")
    @patch("jbom.api.BOMGenerator")
    def test_generate_inventory_with_search(
        self, mock_bom_generator_class, mock_enricher_class, mock_provider_class
    ):
        """Test inventory generation with search enrichment."""
        # Mock BOMGenerator
        mock_generator = Mock()
        mock_bom_generator_class.return_value = mock_generator
        mock_generator.discover_input.return_value = Path("test.kicad_sch")
        mock_generator.load_input.return_value = self.mock_components

        # Mock MouserProvider
        mock_provider = Mock()
        mock_provider_class.return_value = mock_provider

        # Mock InventoryEnricher
        mock_enricher = Mock()
        mock_enricher_class.return_value = mock_enricher

        mock_inventory_items = [
            Mock(spec=InventoryItem),
            Mock(spec=InventoryItem),
        ]
        mock_field_names = ["IPN", "Value", "Manufacturer", "MFGPN"]

        mock_enricher.enrich.return_value = (mock_inventory_items, mock_field_names)
        mock_enricher.search_count = 2
        mock_enricher.successful_searches = 2
        mock_enricher.failed_searches = 0

        # Test with search enabled
        options = InventoryOptions(search=True, provider="mouser", limit=1)
        result = generate_enriched_inventory(input="test_project", options=options)

        self.assertTrue(result["success"])
        self.assertEqual(result["component_count"], 2)
        self.assertEqual(len(result["inventory_items"]), 2)
        self.assertIn("search_stats", result)
        self.assertEqual(result["search_stats"]["searches_performed"], 2)
        self.assertEqual(result["search_stats"]["provider"], "mouser")

        # Verify enricher was called correctly
        mock_enricher_class.assert_called_once()
        call_args = mock_enricher_class.call_args
        self.assertEqual(call_args[1]["components"], self.mock_components)
        self.assertEqual(call_args[1]["limit"], 1)

    @patch("jbom.api.BOMGenerator")
    def test_generate_inventory_project_not_found(self, mock_bom_generator_class):
        """Test error handling when project cannot be loaded."""
        mock_generator = Mock()
        mock_bom_generator_class.return_value = mock_generator
        mock_generator.discover_input.side_effect = FileNotFoundError(
            "Project not found"
        )

        result = generate_enriched_inventory(input="nonexistent_project")

        self.assertFalse(result["success"])
        self.assertIn("Error loading project", result["error"])
        self.assertEqual(result["component_count"], 0)
        self.assertEqual(result["inventory_items"], [])

    @patch("jbom.api.BOMGenerator")
    def test_generate_inventory_no_components(self, mock_bom_generator_class):
        """Test handling when no components are found."""
        mock_generator = Mock()
        mock_bom_generator_class.return_value = mock_generator
        mock_generator.discover_input.return_value = Path("empty.kicad_sch")
        mock_generator.load_input.return_value = []  # Empty component list

        result = generate_enriched_inventory(input="empty_project")

        self.assertFalse(result["success"])
        self.assertIn("No components found", result["error"])
        self.assertEqual(result["component_count"], 0)

    @patch("jbom.api.MouserProvider")
    @patch("jbom.api.BOMGenerator")
    def test_search_provider_error(self, mock_bom_generator_class, mock_provider_class):
        """Test error handling when search provider fails to initialize."""
        # Mock BOMGenerator
        mock_generator = Mock()
        mock_bom_generator_class.return_value = mock_generator
        mock_generator.discover_input.return_value = Path("test.kicad_sch")
        mock_generator.load_input.return_value = self.mock_components

        # Mock MouserProvider to raise error
        mock_provider_class.side_effect = ValueError("Invalid API key")

        options = InventoryOptions(search=True, provider="mouser")
        result = generate_enriched_inventory(input="test_project", options=options)

        self.assertFalse(result["success"])
        self.assertIn("Search provider error", result["error"])
        self.assertIn("Invalid API key", result["error"])

    @patch("jbom.api.BOMGenerator")
    def test_invalid_search_provider(self, mock_bom_generator_class):
        """Test error handling for invalid search provider."""
        # Mock BOMGenerator to succeed - we want to test provider validation
        mock_generator = Mock()
        mock_bom_generator_class.return_value = mock_generator
        mock_generator.discover_input.return_value = Path("test.kicad_sch")
        mock_generator.load_input.return_value = self.mock_components

        options = InventoryOptions(search=True, provider="invalid_provider")
        result = generate_enriched_inventory(input="test_project", options=options)

        self.assertFalse(result["success"])
        self.assertIn("Unsupported search provider", result["error"])

    @patch("jbom.api._write_inventory_output")
    @patch("jbom.api.BOMGenerator")
    def test_output_writing(self, mock_bom_generator_class, mock_write_output):
        """Test that output is written when specified."""
        # Mock BOMGenerator
        mock_generator = Mock()
        mock_bom_generator_class.return_value = mock_generator
        mock_generator.discover_input.return_value = Path("test.kicad_sch")
        mock_generator.load_input.return_value = self.mock_components

        result = generate_enriched_inventory(input="test_project", output="output.csv")

        self.assertTrue(result["success"])
        mock_write_output.assert_called_once()

    @patch("jbom.api._write_inventory_output")
    @patch("jbom.api.BOMGenerator")
    def test_output_writing_error(self, mock_bom_generator_class, mock_write_output):
        """Test error handling during output writing."""
        # Mock BOMGenerator
        mock_generator = Mock()
        mock_bom_generator_class.return_value = mock_generator
        mock_generator.discover_input.return_value = Path("test.kicad_sch")
        mock_generator.load_input.return_value = self.mock_components

        # Mock output writing to fail
        mock_write_output.side_effect = IOError("Cannot write file")

        result = generate_enriched_inventory(
            input="test_project", output="readonly.csv"
        )

        self.assertFalse(result["success"])
        self.assertIn("Error writing output", result["error"])
        # Should still include the inventory data despite output error
        self.assertGreater(len(result["inventory_items"]), 0)

    def test_inventory_options_defaults(self):
        """Test InventoryOptions default values."""
        options = InventoryOptions()

        self.assertFalse(options.search)
        self.assertEqual(options.provider, "mouser")
        self.assertIsNone(options.api_key)
        self.assertEqual(options.limit, 1)
        self.assertFalse(options.interactive)
        self.assertIsNone(options.fields)


if __name__ == "__main__":
    unittest.main()
