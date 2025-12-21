"""
TDD tests for CLI integration with configuration-driven fabricator system.

Tests that CLI flags, presets, and BOM generation work correctly with
the new config-driven approach.
"""

import unittest
from unittest.mock import patch, MagicMock
import argparse

from jbom.cli.bom_command import BOMCommand
from jbom.common.config import FabricatorConfig
from jbom.common.config_fabricators import ConfigurableFabricator


class TestCLIFabricatorDetection(unittest.TestCase):
    """Test CLI fabricator detection from flags and presets."""

    def setUp(self):
        """Set up test environment."""
        self.bom_command = BOMCommand()
        # Create dummy inventory file for validation
        with open("test.csv", "w") as f:
            f.write("dummy")

        # Create test fabricator configs - using generic names to avoid hardcoding
        self.fab1_config = FabricatorConfig(
            name="Test Fabricator 1",
            id="fab1",
            cli_flags=["--fab1", "--test-fab1"],
            cli_presets=["+fab1", "+test-fab1"],
        )

        self.fab2_config = FabricatorConfig(
            name="Test Fabricator 2",
            id="fab2",
            cli_flags=["--fab2"],
            cli_presets=["+fab2"],
        )

    def tearDown(self):
        import os

        if os.path.exists("test.csv"):
            os.remove("test.csv")

    @patch("jbom.cli.bom_command.get_fabricator_by_cli_flag")
    def test_explicit_fabricator_flag_takes_precedence(self, mock_get_by_flag):
        """Test that explicit --fabricator argument takes precedence over everything."""
        args = argparse.Namespace()
        args.fabricator = "explicit"
        args.fabricator_fab1 = False
        args.fields = "+fab1"  # Should be ignored

        result = self.bom_command._determine_fabricator(args, "+jlc")

        # Should return explicit fabricator, not JLC
        self.assertEqual(result, "explicit")
        mock_get_by_flag.assert_not_called()

    @patch("jbom.cli.bom_command.get_fabricator_by_cli_flag")
    def test_fab1_flag_detection(self, mock_get_by_flag):
        """Test that fabricator flag is detected and mapped to correct fabricator."""
        mock_fabricator = MagicMock()
        mock_fabricator.config.id = "fab1"
        mock_get_by_flag.return_value = mock_fabricator

        args = argparse.Namespace()
        args.fabricator = None
        args.fabricator_fab1 = True
        args.fields = None

        result = self.bom_command._determine_fabricator(args, None)

        self.assertEqual(result, "fab1")
        mock_get_by_flag.assert_called_once_with("--fab1")

    @patch("jbom.cli.bom_command.get_fabricator_by_preset")
    def test_preset_detection_in_fields(self, mock_get_by_preset):
        """Test that fabricator presets in fields argument are detected."""
        mock_fabricator = MagicMock()
        mock_fabricator.config.id = "fab2"
        mock_get_by_preset.return_value = mock_fabricator

        args = argparse.Namespace()
        args.fabricator = None
        args.fabricator_fab1 = False

        result = self.bom_command._determine_fabricator(args, "+fab2,reference,value")

        self.assertEqual(result, "fab2")
        mock_get_by_preset.assert_called_once_with("+fab2")

    @patch("jbom.cli.bom_command.get_fabricator_by_preset")
    def test_multiple_presets_first_one_wins(self, mock_get_by_preset):
        """Test that when multiple presets are specified, first fabricator-specific one wins."""
        mock_fab1_fabricator = MagicMock()
        mock_fab1_fabricator.config.id = "fab1"

        def mock_preset_lookup(preset):
            if preset == "+fab1":
                return mock_fab1_fabricator
            elif preset == "+fab2":
                return MagicMock()  # Would be fab2
            return None

        mock_get_by_preset.side_effect = mock_preset_lookup

        args = argparse.Namespace()
        args.fabricator = None
        args.fabricator_fab1 = False

        result = self.bom_command._determine_fabricator(args, "+fab1,+fab2,reference")

        # Should return first fabricator found (fab1)
        self.assertEqual(result, "fab1")

    def test_no_fabricator_specified_returns_none(self):
        """Test that when no fabricator is specified, None is returned."""
        args = argparse.Namespace()
        args.fabricator = None
        args.fabricator_fab1 = False

        result = self.bom_command._determine_fabricator(args, "reference,value")

        # Should return None to use default
        self.assertIsNone(result)

    @patch("jbom.cli.bom_command.get_fabricator_by_cli_flag")
    @patch("jbom.cli.bom_command.get_fabricator_by_preset")
    def test_flag_overrides_preset(self, mock_get_by_preset, mock_get_by_flag):
        """Test that CLI flag takes precedence over presets in fields."""
        mock_fab1_fabricator = MagicMock()
        mock_fab1_fabricator.config.id = "fab1"
        mock_get_by_flag.return_value = mock_fab1_fabricator

        mock_fab2_fabricator = MagicMock()
        mock_fab2_fabricator.config.id = "fab2"
        mock_get_by_preset.return_value = mock_fab2_fabricator

        args = argparse.Namespace()
        args.fabricator = None
        args.fabricator_fab1 = True  # Should override preset

        result = self.bom_command._determine_fabricator(args, "+fab2")

        # Should return fab1 from flag, not fab2 from preset
        self.assertEqual(result, "fab1")
        mock_get_by_flag.assert_called_once_with("--fab1")
        mock_get_by_preset.assert_not_called()


class TestCLIFieldPresetIntegration(unittest.TestCase):
    """Test integration between CLI field presets and fabricators."""

    def test_config_based_field_presets(self):
        """Test that field presets are resolved from configuration."""
        # Create test fabricator with custom preset
        test_config = FabricatorConfig(
            name="Test Fabricator",
            id="test",
            presets={
                "default": {
                    "description": "Test BOM format",
                    "fields": [
                        "reference",
                        "quantity",
                        "value",
                        "fabricator_part_number",
                    ],
                }
            },
            cli_presets=["+test"],
        )

        # Create fabricator directly (not through global config)
        fabricator = ConfigurableFabricator(test_config)

        # Should have correct preset fields
        fields = fabricator.get_preset_fields("default")
        expected_fields = ["reference", "quantity", "value", "fabricator_part_number"]
        self.assertEqual(fields, expected_fields)


class TestBOMColumnMapping(unittest.TestCase):
    """Test that BOM column headers are mapped correctly from configuration."""

    def test_fabricator_column_header_mapping(self):
        """Test that fabricator maps internal fields to custom headers."""
        config = FabricatorConfig(
            name="Test Fabricator A",
            id="testa",
            part_number_header="PART_NUM",
            bom_columns={
                "PART_NUM": "fabricator_part_number",
                "REF": "reference",
                "PKG": "i:package",
            },
        )

        fabricator = ConfigurableFabricator(config)
        columns = fabricator.get_bom_columns()

        # Should map to fabricator-specific headers
        self.assertEqual(columns["PART_NUM"], "fabricator_part_number")
        self.assertEqual(columns["REF"], "reference")
        self.assertEqual(columns["PKG"], "i:package")

    def test_different_fabricator_header_mapping(self):
        """Test that different fabricators can use different headers for same fields."""
        config = FabricatorConfig(
            name="Test Fabricator B",
            id="testb",
            part_number_header="DIST_PART_NUM",
            bom_columns={
                "DIST_PART_NUM": "fabricator_part_number",
                "COMPONENT": "reference",
                "FOOTPRINT": "i:package",
            },
        )

        fabricator = ConfigurableFabricator(config)
        columns = fabricator.get_bom_columns()

        # Should map to this fabricator's specific headers
        self.assertEqual(columns["DIST_PART_NUM"], "fabricator_part_number")
        self.assertEqual(columns["COMPONENT"], "reference")
        self.assertEqual(columns["FOOTPRINT"], "i:package")

    def test_fabricator_part_number_header_property(self):
        """Test that part_number_header property returns correct header."""
        fab1_config = FabricatorConfig(
            name="Test Fab 1", id="fab1", part_number_header="P/N"
        )

        fab2_config = FabricatorConfig(
            name="Test Fab 2", id="fab2", part_number_header="Part Number"
        )

        fab1 = ConfigurableFabricator(fab1_config)
        fab2 = ConfigurableFabricator(fab2_config)

        self.assertEqual(fab1.part_number_header, "P/N")
        self.assertEqual(fab2.part_number_header, "Part Number")


class TestConfigurationValidation(unittest.TestCase):
    """Test validation of configuration data."""

    def test_fabricator_requires_name_and_id(self):
        """Test that fabricators require name and id fields."""
        with self.assertRaises(TypeError):
            # Should fail without required fields
            FabricatorConfig()

    def test_fabricator_with_minimal_config(self):
        """Test creating fabricator with minimal required configuration."""
        config = FabricatorConfig(name="Test", id="test")
        fabricator = ConfigurableFabricator(config)

        # Should work with minimal config
        self.assertEqual(fabricator.name, "Test")
        self.assertEqual(fabricator.config.id, "test")

    def test_empty_cli_aliases_handled_gracefully(self):
        """Test that empty CLI aliases are handled gracefully."""
        config = FabricatorConfig(
            name="Test", id="test", cli_flags=[], cli_presets=[]  # Empty  # Empty
        )

        fabricator = ConfigurableFabricator(config)

        # Should default to ID-based flag
        self.assertEqual(len(fabricator.config.cli_flags), 1)
        self.assertEqual(fabricator.config.cli_flags[0], "--test")
        self.assertEqual(len(fabricator.config.cli_presets), 1)
        self.assertEqual(fabricator.config.cli_presets[0], "+test")


class TestEndToEndCLIScenarios(unittest.TestCase):
    """End-to-end scenarios testing complete CLI workflows."""

    @patch("jbom.cli.bom_command.generate_bom")
    @patch("jbom.cli.bom_command.get_fabricator_by_preset")
    def test_fabricator_preset_end_to_end(self, mock_get_by_preset, mock_generate_bom):
        """Test complete workflow: CLI with fabricator preset should use correct fabricator."""
        # Mock test fabricator
        mock_fab = MagicMock()
        mock_fab.config.id = "testfab"
        mock_get_by_preset.return_value = mock_fab

        # Mock BOM generation result
        mock_generate_bom.return_value = {
            "bom_entries": [],
            "generator": MagicMock(),
            "available_fields": {},
        }

        # Simulate CLI execution
        bom_command = BOMCommand()
        args = argparse.Namespace()
        args.project = "test_project"
        args.inventory = ["test.csv"]
        args.output = None
        args.outdir = None
        args.fabricator = None  # Not explicitly set
        args.fabricator_testfab = False  # Not using flag
        args.fields = "+testfab"  # Using preset
        args.verbose = False
        args.debug = False
        args.smd_only = False

        # Execute command
        result = bom_command.execute(args)

        # Should succeed
        self.assertEqual(result, 0)

        # Should have called generate_bom with test fabricator
        mock_generate_bom.assert_called_once()
        call_args = mock_generate_bom.call_args
        options = call_args[1]["options"]  # Named argument
        self.assertEqual(options.fabricator, "testfab")


if __name__ == "__main__":
    unittest.main()
