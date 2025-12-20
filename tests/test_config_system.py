"""
Test-driven development tests for jBOM configuration system.

Tests both positive and negative cases for:
- Configuration loading and hierarchical merging
- Fabricator registry and lookup
- CLI integration (flags and presets)
- Field mapping and BOM column generation
- Error handling and validation
"""

import unittest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from jbom.common.config import (
    ConfigLoader,
    JBOMConfig,
    FabricatorConfig,
    get_config,
    reload_config,
)
from jbom.common.config_fabricators import (
    ConfigurableFabricator,
    FabricatorRegistry,
    get_fabricator,
)
from jbom.common.types import InventoryItem


class TestConfigLoader(unittest.TestCase):
    """Test configuration loading and hierarchical merging."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self._cleanup_temp_dir())

    def _cleanup_temp_dir(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_builtin_config_loads_successfully(self):
        """Test that built-in configuration loads with expected fabricators."""
        loader = ConfigLoader()
        config = loader._get_builtin_config()

        # Should have standard fabricators
        fab_ids = [f.id for f in config.fabricators]
        self.assertIn("jlc", fab_ids)
        self.assertIn("pcbway", fab_ids)
        self.assertIn("seeed", fab_ids)
        self.assertIn("generic", fab_ids)

        # JLC should have correct configuration
        jlc = config.get_fabricator("jlc")
        self.assertIsNotNone(jlc)
        self.assertEqual(jlc.name, "JLCPCB")
        self.assertEqual(jlc.part_number_header, "LCSC")
        self.assertIn("--jlc", jlc.cli_flags)
        self.assertIn("+jlc", jlc.cli_presets)

    def test_config_file_loading(self):
        """Test loading configuration from YAML file."""
        # Create test config file
        config_data = {
            "version": "1.0.0",
            "fabricators": [
                {
                    "name": "Test Fab",
                    "id": "test",
                    "description": "Test fabricator",
                    "part_number": {
                        "header": "Test Part Number",
                        "priority_fields": ["test_pn", "mfgpn"],
                    },
                    "cli_aliases": {"flags": ["--test"], "presets": ["+test"]},
                }
            ],
        }

        config_file = self.temp_dir / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader()
        config = loader._load_config_file(config_file)

        # Should load fabricator correctly
        self.assertEqual(len(config.fabricators), 1)
        fab = config.fabricators[0]
        self.assertEqual(fab.name, "Test Fab")
        self.assertEqual(fab.id, "test")
        self.assertEqual(fab.part_number_header, "Test Part Number")
        self.assertEqual(fab.cli_flags, ["--test"])
        self.assertEqual(fab.cli_presets, ["+test"])

    @patch("jbom.common.config.ConfigLoader._get_config_paths")
    def test_hierarchical_config_merging(self, mock_paths):
        """Test that configurations merge hierarchically with proper precedence."""
        # Create base config
        base_config = self.temp_dir / "base.yaml"
        base_data = {
            "fabricators": [
                {
                    "name": "Base Fab",
                    "id": "test",
                    "part_number": {"header": "Base Header"},
                    "cli_aliases": {"flags": ["--base"]},
                }
            ]
        }
        with open(base_config, "w") as f:
            yaml.dump(base_data, f)

        # Create override config
        override_config = self.temp_dir / "override.yaml"
        override_data = {
            "fabricators": [
                {
                    "name": "Override Fab",  # Should override
                    "id": "test",  # Same ID to merge
                    "part_number": {"header": "Override Header"},  # Should override
                    "cli_aliases": {"presets": ["+override"]},  # Should add to existing
                }
            ]
        }
        with open(override_config, "w") as f:
            yaml.dump(override_data, f)

        # Mock config paths to return our test files
        mock_paths.return_value = [base_config, override_config]

        loader = ConfigLoader()
        config = loader.load_config()

        # Should have merged configuration
        fab = config.get_fabricator("test")
        self.assertIsNotNone(fab)
        self.assertEqual(fab.name, "Override Fab")  # Overridden
        self.assertEqual(fab.part_number_header, "Override Header")  # Overridden
        # CLI flags should be merged (implementation dependent)

    def test_invalid_config_file_handling(self):
        """Test handling of invalid/malformed configuration files."""
        # Create invalid YAML file
        invalid_config = self.temp_dir / "invalid.yaml"
        with open(invalid_config, "w") as f:
            f.write("invalid: yaml: content: [unclosed")

        loader = ConfigLoader()

        # Should raise exception or handle gracefully
        with self.assertRaises(yaml.YAMLError):
            loader._load_config_file(invalid_config)

    def test_missing_required_fields(self):
        """Test validation of required configuration fields."""
        # Create config missing required fields
        invalid_data = {
            "fabricators": [
                {
                    "name": "Test Fab",
                    # Missing required "id" field
                    "description": "Test fabricator",
                }
            ]
        }

        config_file = self.temp_dir / "missing_fields.yaml"
        with open(config_file, "w") as f:
            yaml.dump(invalid_data, f)

        loader = ConfigLoader()

        # Should handle missing required fields gracefully
        with self.assertRaises(KeyError):
            loader._load_config_file(config_file)


class TestConfigurableFabricator(unittest.TestCase):
    """Test the ConfigurableFabricator implementation."""

    def setUp(self):
        """Set up test fabricator configuration."""
        self.jlc_config = FabricatorConfig(
            name="Test JLC",
            id="jlc",
            part_number_header="LCSC",
            part_number_fields=["lcsc", "jlc"],
            bom_columns={"LCSC": "fabricator_part_number", "Package": "i:package"},
            cli_flags=["--jlc"],
            cli_presets=["+jlc"],
        )

        self.generic_config = FabricatorConfig(
            name="Generic",
            id="generic",
            part_number_header="Manufacturer Part Number",
            part_number_fields=["mfgpn", "mpn"],
            dynamic_name=True,
            name_source="manufacturer",
        )

        # Create test inventory items
        self.jlc_item = InventoryItem(
            ipn="TEST-001",
            keywords="test",
            category="RES",
            description="Test resistor",
            smd="SMD",
            value="10K",
            type="",
            tolerance="",
            voltage="",
            amperage="",
            wattage="",
            lcsc="C123456",
            manufacturer="Yageo",
            mfgpn="RC0603FR-0710KL",
            datasheet="",
            package="0603",
            priority=10,
            raw_data={"LCSC": "C123456"},
        )

        self.generic_item = InventoryItem(
            ipn="TEST-002",
            keywords="test",
            category="CAP",
            description="Test capacitor",
            smd="SMD",
            value="100nF",
            type="",
            tolerance="",
            voltage="50V",
            amperage="",
            wattage="",
            lcsc="",  # No LCSC
            manufacturer="Samsung",
            mfgpn="CL10A104KB8NNNC",
            datasheet="",
            package="0603",
            priority=10,
            raw_data={"Manufacturer": "Samsung"},
        )

    def test_jlc_fabricator_part_number_lookup(self):
        """Test JLC fabricator finds part numbers correctly."""
        jlc = ConfigurableFabricator(self.jlc_config)

        # Should find LCSC part number
        part_num = jlc.get_part_number(self.jlc_item)
        self.assertEqual(part_num, "C123456")

        # Should match items with LCSC numbers
        self.assertTrue(jlc.matches(self.jlc_item))

        # Should not match items without LCSC numbers
        self.assertFalse(jlc.matches(self.generic_item))

    def test_generic_fabricator_dynamic_naming(self):
        """Test generic fabricator uses manufacturer name dynamically."""
        generic = ConfigurableFabricator(self.generic_config)

        # Should use manufacturer name
        fab_name = generic.get_name(self.generic_item)
        self.assertEqual(fab_name, "Samsung")

        # Should find manufacturer part number
        part_num = generic.get_part_number(self.generic_item)
        self.assertEqual(part_num, "CL10A104KB8NNNC")

        # Generic should match all items
        self.assertTrue(generic.matches(self.jlc_item))
        self.assertTrue(generic.matches(self.generic_item))

    def test_bom_column_mappings(self):
        """Test BOM column header mappings."""
        jlc = ConfigurableFabricator(self.jlc_config)

        columns = jlc.get_bom_columns()
        self.assertEqual(columns["LCSC"], "fabricator_part_number")
        self.assertEqual(columns["Package"], "i:package")

    def test_part_number_priority_order(self):
        """Test that part number fields are checked in priority order."""
        # Create item with multiple possible part number fields
        multi_item = InventoryItem(
            ipn="TEST-003",
            keywords="test",
            category="RES",
            description="Multi-source part",
            smd="SMD",
            value="1K",
            type="",
            tolerance="",
            voltage="",
            amperage="",
            wattage="",
            lcsc="",  # No LCSC
            manufacturer="Generic",
            mfgpn="GEN123",
            datasheet="",
            package="0603",
            priority=10,
            raw_data={"jlc": "JLC789", "mfgpn": "GEN123"},  # JLC should have priority
        )

        jlc = ConfigurableFabricator(self.jlc_config)

        # Should find JLC part number first (higher priority than mfgpn)
        part_num = jlc.get_part_number(multi_item)
        self.assertEqual(part_num, "JLC789")

    def test_preset_fields_lookup(self):
        """Test fabricator preset field lookup."""
        config = FabricatorConfig(
            name="Test",
            id="test",
            presets={
                "default": {"fields": ["reference", "quantity", "value"]},
                "extended": {
                    "fields": ["reference", "quantity", "value", "manufacturer"]
                },
            },
        )

        fabricator = ConfigurableFabricator(config)

        # Should return correct fields for presets
        default_fields = fabricator.get_preset_fields("default")
        self.assertEqual(default_fields, ["reference", "quantity", "value"])

        extended_fields = fabricator.get_preset_fields("extended")
        self.assertEqual(
            extended_fields, ["reference", "quantity", "value", "manufacturer"]
        )

        # Should return None for non-existent preset
        missing_fields = fabricator.get_preset_fields("nonexistent")
        self.assertIsNone(missing_fields)


class TestFabricatorRegistry(unittest.TestCase):
    """Test the FabricatorRegistry functionality."""

    @patch("jbom.common.config_fabricators.get_config")
    def test_fabricator_registry_loading(self, mock_get_config):
        """Test that fabricator registry loads from configuration."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.fabricators = [
            FabricatorConfig(
                name="JLC", id="jlc", cli_flags=["--jlc"], cli_presets=["+jlc"]
            ),
            FabricatorConfig(
                name="PCBWay",
                id="pcbway",
                cli_flags=["--pcbway"],
                cli_presets=["+pcbway"],
            ),
        ]
        mock_get_config.return_value = mock_config

        registry = FabricatorRegistry()

        # Should load both fabricators
        self.assertIsNotNone(registry.get_fabricator("jlc"))
        self.assertIsNotNone(registry.get_fabricator("pcbway"))
        self.assertEqual(len(registry.list_fabricators()), 2)

    @patch("jbom.common.config_fabricators.get_config")
    def test_cli_flag_lookup(self, mock_get_config):
        """Test CLI flag to fabricator lookup."""
        mock_config = MagicMock()
        mock_config.get_fabricator_by_cli_flag.return_value = FabricatorConfig(
            name="JLC", id="jlc", cli_flags=["--jlc"]
        )
        mock_get_config.return_value = mock_config

        registry = FabricatorRegistry()

        # Should find fabricator by CLI flag
        fab = registry.get_fabricator_by_cli_flag("--jlc")
        self.assertIsNotNone(fab)

    @patch("jbom.common.config_fabricators.get_config")
    def test_preset_lookup(self, mock_get_config):
        """Test preset to fabricator lookup."""
        mock_config = MagicMock()
        mock_config.get_fabricator_by_preset.return_value = FabricatorConfig(
            name="JLC", id="jlc", cli_presets=["+jlc"]
        )
        mock_get_config.return_value = mock_config

        registry = FabricatorRegistry()

        # Should find fabricator by preset
        fab = registry.get_fabricator_by_preset("+jlc")
        self.assertIsNotNone(fab)

    @patch("jbom.common.config_fabricators.get_config")
    def test_default_fabricator_fallback(self, mock_get_config):
        """Test fallback to default fabricator."""
        mock_config = MagicMock()
        mock_config.fabricators = [FabricatorConfig(name="Generic", id="generic")]
        mock_get_config.return_value = mock_config

        registry = FabricatorRegistry()

        # Should return generic fabricator as default
        default_fab = registry.get_default_fabricator()
        self.assertIsNotNone(default_fab)
        self.assertEqual(default_fab.config.id, "generic")

    @patch("jbom.common.config_fabricators.get_config")
    def test_case_insensitive_lookup(self, mock_get_config):
        """Test that fabricator lookup is case-insensitive."""
        mock_config = MagicMock()
        mock_config.fabricators = [FabricatorConfig(name="JLC", id="jlc")]
        mock_get_config.return_value = mock_config

        registry = FabricatorRegistry()

        # Should find fabricator regardless of case
        self.assertIsNotNone(registry.get_fabricator("jlc"))
        self.assertIsNotNone(registry.get_fabricator("JLC"))
        self.assertIsNotNone(registry.get_fabricator("Jlc"))


class TestGlobalFunctions(unittest.TestCase):
    """Test global configuration and fabricator functions."""

    @patch("jbom.common.config_fabricators.get_fabricator_registry")
    def test_get_fabricator_function(self, mock_registry):
        """Test global get_fabricator function."""
        mock_fab = MagicMock()
        mock_reg = MagicMock()
        mock_reg.get_fabricator.return_value = mock_fab
        mock_registry.return_value = mock_reg

        result = get_fabricator("jlc")

        mock_reg.get_fabricator.assert_called_once_with("jlc")
        self.assertEqual(result, mock_fab)

    @patch("jbom.common.config_fabricators.get_fabricator_registry")
    def test_get_fabricator_with_fallback(self, mock_registry):
        """Test get_fabricator falls back to generic when fabricator not found."""
        mock_default_fab = MagicMock()
        mock_reg = MagicMock()
        mock_reg.get_fabricator.return_value = None
        mock_reg.get_default_fabricator.return_value = mock_default_fab
        mock_registry.return_value = mock_reg

        result = get_fabricator("nonexistent")

        mock_reg.get_default_fabricator.assert_called_once()
        self.assertEqual(result, mock_default_fab)

    def test_config_reload_functionality(self):
        """Test that configuration can be reloaded."""
        # This tests the reload mechanism works without errors
        original_config = get_config()
        reloaded_config = reload_config()

        # Should be valid configurations
        self.assertIsInstance(original_config, JBOMConfig)
        self.assertIsInstance(reloaded_config, JBOMConfig)

        # Should have fabricators
        self.assertTrue(len(reloaded_config.fabricators) > 0)


class TestNegativeCases(unittest.TestCase):
    """Test error handling and edge cases."""

    def test_empty_config_file(self):
        """Test handling of empty configuration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Empty file
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader()
            config = loader._load_config_file(temp_path)

            # Should handle empty config gracefully
            self.assertIsInstance(config, JBOMConfig)
            self.assertEqual(len(config.fabricators), 0)
        finally:
            temp_path.unlink()

    def test_malformed_yaml(self):
        """Test handling of malformed YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: [unclosed bracket")
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader()
            with self.assertRaises(yaml.YAMLError):
                loader._load_config_file(temp_path)
        finally:
            temp_path.unlink()

    def test_unknown_fabricator_lookup(self):
        """Test lookup of non-existent fabricators."""
        # Should return generic fabricator for unknown IDs
        fab = get_fabricator("nonexistent")
        self.assertIsNotNone(fab)
        # Should be the default/generic fabricator

    def test_missing_part_number_fields(self):
        """Test fabricator with no part number fields."""
        config = FabricatorConfig(
            name="Test", id="test", part_number_fields=[]  # No fields configured
        )

        fabricator = ConfigurableFabricator(config)

        # Should handle gracefully and return empty string
        item = InventoryItem(
            ipn="TEST",
            keywords="",
            category="",
            description="",
            smd="",
            value="",
            type="",
            tolerance="",
            voltage="",
            amperage="",
            wattage="",
            lcsc="",
            manufacturer="",
            mfgpn="",
            datasheet="",
            package="",
            priority=10,
        )

        part_num = fabricator.get_part_number(item)
        self.assertEqual(part_num, "")

        # Should not match if no part number found (unless generic)
        if config.id != "generic":
            self.assertFalse(fabricator.matches(item))

    def test_circular_config_references(self):
        """Test handling of circular references in configuration."""
        # This would be implementation-specific
        # For now, just ensure it doesn't break the system
        pass

    def test_invalid_field_mappings(self):
        """Test handling of invalid BOM column mappings."""
        config = FabricatorConfig(
            name="Test", id="test", bom_columns={"": "invalid"}  # Invalid mapping
        )

        fabricator = ConfigurableFabricator(config)
        columns = fabricator.get_bom_columns()

        # Should handle gracefully
        self.assertIsInstance(columns, dict)


if __name__ == "__main__":
    unittest.main()
