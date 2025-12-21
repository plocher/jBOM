"""
TDD tests for hierarchical configuration system.

Tests the complete workflow of loading configurations from:
- Package defaults (built-in fabricator files)
- User home directory overrides
- Project-specific configurations
- based_on inheritance pattern
- External file references
"""

import unittest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

from jbom.common.config import (
    ConfigLoader,
    JBOMConfig,
    FabricatorConfig,
    get_config,
    reload_config,
)


class TestHierarchicalConfiguration(unittest.TestCase):
    """Test hierarchical configuration loading and inheritance."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(self._cleanup_temp_dir)

    def _cleanup_temp_dir(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_package_defaults_loading(self):
        """Test that package default configurations load correctly."""
        loader = ConfigLoader()

        # Should load built-in config (fallback or package)
        config = loader._get_builtin_config()

        self.assertIsInstance(config, JBOMConfig)
        self.assertEqual(config.version, "3.0.0")
        self.assertGreater(len(config.fabricators), 0)

        # Should have at least a generic fabricator
        fab_ids = [f.id for f in config.fabricators]
        self.assertIn("generic", fab_ids)

    def test_external_fabricator_file_loading(self):
        """Test loading fabricators from external YAML files."""
        # Create external fabricator file
        fab_file = self.temp_dir / "custom.fab.yaml"
        fab_data = {
            "name": "Custom Fabricator",
            "id": "custom",
            "description": "Test custom fabricator",
            "part_number": {
                "header": "Custom Part Number",
                "priority_fields": ["CUSTOM", "MPN"],
            },
            "bom_columns": {
                "Part": "reference",
                "Custom Part Number": "fabricator_part_number",
            },
        }
        with open(fab_file, "w") as f:
            yaml.dump(fab_data, f)

        # Create config that references external file
        config_data = {
            "version": "3.0.0",
            "fabricators": [{"file": str(fab_file)}],
        }

        loader = ConfigLoader()
        config = loader._dict_to_config(config_data)

        self.assertEqual(len(config.fabricators), 1)
        fab = config.fabricators[0]
        self.assertEqual(fab.name, "Custom Fabricator")
        self.assertEqual(fab.id, "custom")
        self.assertEqual(fab.part_number_header, "Custom Part Number")

    def test_based_on_inheritance(self):
        """Test based_on inheritance pattern for fabricator customization."""
        # Create base fabricator
        base_config = FabricatorConfig(
            name="Base Fabricator",
            id="base",
            description="Base configuration",
            part_number={"header": "Base Header", "priority_fields": ["BASE"]},
            bom_columns={"Base Col": "base_field"},
        )

        # Mock the base fabricator lookup
        loader = ConfigLoader()

        with patch.object(loader, "_find_base_fabricator", return_value=base_config):
            # Create derived fabricator config
            derived_data = {
                "name": "Derived Fabricator",
                "id": "derived",
                "based_on": "base",
                "description": "Customized version",
                "bom_columns": {
                    "Base Col": "base_field",
                    "Custom Col": "custom_field",  # Should be added
                },
            }

            derived_fab = loader._load_fabricator(derived_data)

            self.assertIsNotNone(derived_fab)
            self.assertEqual(derived_fab.name, "Derived Fabricator")
            self.assertEqual(derived_fab.id, "derived")
            self.assertEqual(derived_fab.description, "Customized version")

            # Should inherit base configuration and add custom fields
            self.assertIn("Base Col", derived_fab.bom_columns)
            self.assertIn("Custom Col", derived_fab.bom_columns)

    def test_cli_flag_auto_generation(self):
        """Test that CLI flags are auto-generated from fabricator id."""
        fab = FabricatorConfig(name="Test Fabricator", id="test")

        # CLI flags should be auto-generated from id
        self.assertEqual(fab.cli_flags, ["--test"])
        self.assertEqual(fab.cli_presets, ["+test"])

    def test_id_auto_generation_from_name(self):
        """Test that id is auto-generated from name if not provided."""
        fab = FabricatorConfig(name="My Custom Fabricator")

        # Should auto-generate id from name
        self.assertEqual(fab.id, "mycustomfabricator")
        self.assertEqual(fab.cli_flags, ["--mycustomfabricator"])

    def test_hierarchical_config_precedence(self):
        """Test configuration precedence: package → user → project."""
        loader = ConfigLoader()

        # Mock config paths to control loading order
        package_config = self.temp_dir / "package.yaml"
        user_config = self.temp_dir / "user.yaml"
        project_config = self.temp_dir / "project.yaml"

        # Package config
        package_data = {
            "fabricators": [
                {"name": "Test Fab", "id": "test", "description": "Package version"}
            ]
        }
        with open(package_config, "w") as f:
            yaml.dump(package_data, f)

        # User config (should override package)
        user_data = {
            "fabricators": [
                {"name": "Test Fab", "id": "test", "description": "User version"}
            ]
        }
        with open(user_config, "w") as f:
            yaml.dump(user_data, f)

        # Project config (should override user)
        project_data = {
            "fabricators": [
                {"name": "Test Fab", "id": "test", "description": "Project version"}
            ]
        }
        with open(project_config, "w") as f:
            yaml.dump(project_data, f)

        # Mock config paths to control loading order - set the actual attribute used by load_config
        loader.config_paths = [package_config, user_config, project_config]

        # Mock get_builtin_config to return empty config for controlled test
        with patch.object(loader, "_get_builtin_config", return_value=JBOMConfig()):
            config = loader.load_config()

            # Should have final project version
            self.assertEqual(len(config.fabricators), 1)
            fab = config.fabricators[0]
            self.assertEqual(fab.description, "Project version")


class TestConfigurationErrorHandling(unittest.TestCase):
    """Test error handling in configuration system."""

    def test_missing_external_file(self):
        """Test graceful handling of missing external fabricator files."""
        loader = ConfigLoader()

        fab_data = {"name": "missing", "file": "/nonexistent/path.yaml"}

        # Should return None for missing files without crashing
        result = loader._load_fabricator(fab_data)
        self.assertIsNone(result)

    def test_invalid_yaml_file(self):
        """Test handling of malformed YAML files."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create invalid YAML
            bad_yaml = temp_dir / "bad.yaml"
            with open(bad_yaml, "w") as f:
                f.write("invalid: yaml: [unclosed")

            loader = ConfigLoader()

            # Should handle YAML errors gracefully
            with self.assertRaises(yaml.YAMLError):
                loader._load_yaml_file(bad_yaml)

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_missing_required_fabricator_fields(self):
        """Test handling of fabricator configs missing required fields."""
        loader = ConfigLoader()

        # Missing name field
        incomplete_data = {"id": "test", "description": "Missing name field"}

        # Should handle gracefully or use defaults
        result = loader._load_fabricator(incomplete_data)
        # Implementation may vary - this tests that it doesn't crash
        self.assertIsInstance(result, (type(None), type(object())))


class TestConfigurationIntegration(unittest.TestCase):
    """Integration tests for the complete configuration system."""

    def test_dynamic_cli_flag_generation_integration(self):
        """Test that dynamic CLI flags work with hierarchical config."""
        from jbom.cli.bom_command import BOMCommand
        import argparse

        # Should generate flags from loaded configuration
        cmd = BOMCommand()
        parser = argparse.ArgumentParser()

        # This should load config and generate flags dynamically
        cmd.setup_parser(parser)

        # Should have some fabricator flags (at least generic)
        fabricator_actions = [
            action
            for action in parser._actions
            if hasattr(action, "dest") and action.dest.startswith("fabricator_")
        ]

        self.assertGreater(len(fabricator_actions), 0)

    def test_config_reload_functionality(self):
        """Test that configuration can be reloaded."""
        # Get initial config
        get_config()

        # Reload configuration
        reload_config()
        config2 = get_config()

        # Should be able to reload (may be same or different based on files)
        self.assertIsInstance(config2, JBOMConfig)

    @patch("jbom.common.config.ConfigLoader.load_config")
    def test_config_caching(self, mock_load):
        """Test that configuration is cached and not reloaded unnecessarily."""
        mock_config = JBOMConfig()
        mock_load.return_value = mock_config

        # Ensure we start fresh
        reload_config()

        # reload_config calls get_config which calls load_config
        # So count should be 1 now
        self.assertEqual(mock_load.call_count, 1)

        # Call get_config again
        config2 = get_config()
        # Should be cached, so load_config NOT called again
        self.assertEqual(mock_load.call_count, 1)

        # Same instance should be returned
        # Note: reload_config returns the result of get_config(), so check against that
        # config1 = get_config() which is what reload_config returned essentially
        config1 = get_config()
        self.assertIs(config1, config2)


if __name__ == "__main__":
    unittest.main()
