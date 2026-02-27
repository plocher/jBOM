"""
Unit tests for configuration system implementation details.

Tests individual methods and classes in the configuration system:
- FabricatorConfig dataclass behavior
- ConfigLoader internal methods
- Property calculations and derivations
- Error handling edge cases
"""

import unittest
import tempfile
import yaml
from pathlib import Path
from copy import deepcopy

from jbom.common.config import (
    ConfigLoader,
    JBOMConfig,
    FabricatorConfig,
)


class TestFabricatorConfig(unittest.TestCase):
    """Unit tests for FabricatorConfig dataclass."""

    def test_fabricator_config_creation_minimal(self):
        """Test creating FabricatorConfig with minimal required fields."""
        fab = FabricatorConfig(name="Test")

        self.assertEqual(fab.name, "Test")
        self.assertEqual(fab.id, "test")  # Auto-generated from name
        self.assertEqual(fab.description, "")
        self.assertEqual(fab.based_on, "")
        self.assertEqual(fab.pcb_manufacturing, {})
        self.assertEqual(fab.pcb_assembly, {})
        self.assertEqual(fab.part_number, {})
        self.assertEqual(fab.bom_columns, {})

    def test_fabricator_config_creation_full(self):
        """Test creating FabricatorConfig with all fields."""
        fab = FabricatorConfig(
            name="Test Fabricator",
            id="custom_id",
            description="Test description",
            based_on="base_fab",
            pcb_manufacturing={"website": "example.com"},
            pcb_assembly={"api": "api.example.com"},
            part_number={"header": "P/N", "priority_fields": ["PN", "MPN"]},
            bom_columns={"Part": "reference", "P/N": "fabricator_part_number"},
        )

        self.assertEqual(fab.name, "Test Fabricator")
        self.assertEqual(fab.id, "custom_id")
        self.assertEqual(fab.description, "Test description")
        self.assertEqual(fab.based_on, "base_fab")
        self.assertEqual(fab.pcb_manufacturing["website"], "example.com")
        self.assertEqual(fab.pcb_assembly["api"], "api.example.com")
        self.assertEqual(fab.part_number["header"], "P/N")
        self.assertEqual(fab.bom_columns["Part"], "reference")

    def test_id_auto_generation(self):
        """Test automatic ID generation from name."""
        test_cases = [
            ("Simple", "simple"),
            ("Two Words", "twowords"),
            ("With-Dashes", "withdashes"),
            ("With Spaces And-Dashes", "withspacesanddashes"),
            ("UPPERCASE", "uppercase"),
            ("MiXeD cAsE", "mixedcase"),
        ]

        for name, expected_id in test_cases:
            with self.subTest(name=name):
                fab = FabricatorConfig(name=name)
                self.assertEqual(fab.id, expected_id)

    def test_cli_flags_property(self):
        """Test CLI flags property generation."""
        # With explicit ID
        fab = FabricatorConfig(name="Test", id="custom")
        self.assertEqual(fab.cli_flags, ["--custom"])

        # With auto-generated ID from name
        fab_auto = FabricatorConfig(name="Test")
        self.assertEqual(fab_auto.cli_flags, ["--test"])

        # Test the actual empty ID case by setting it after creation
        fab_empty = FabricatorConfig(name="Test", id="custom")
        fab_empty.id = ""  # Set to empty after creation
        self.assertEqual(fab_empty.cli_flags, [])

    def test_cli_presets_property(self):
        """Test CLI presets property generation."""
        # With explicit ID
        fab = FabricatorConfig(name="Test", id="custom")
        self.assertEqual(fab.cli_presets, ["+custom"])

        # With auto-generated ID from name
        fab_auto = FabricatorConfig(name="Test")
        self.assertEqual(fab_auto.cli_presets, ["+test"])

        # Test the actual empty ID case by setting it after creation
        fab_empty = FabricatorConfig(name="Test", id="custom")
        fab_empty.id = ""  # Set to empty after creation
        self.assertEqual(fab_empty.cli_presets, [])

    def test_part_number_header_property(self):
        """Test part_number_header property derivation."""
        # With header specified
        fab = FabricatorConfig(name="Test", part_number={"header": "Custom Header"})
        self.assertEqual(fab.part_number_header, "Custom Header")

        # Without header (default)
        fab_default = FabricatorConfig(name="Test")
        self.assertEqual(fab_default.part_number_header, "Fabricator Part Number")

        # With empty part_number dict
        fab_empty = FabricatorConfig(name="Test", part_number={})
        self.assertEqual(fab_empty.part_number_header, "Fabricator Part Number")

    def test_part_number_fields_property(self):
        """Test part_number_fields property derivation."""
        # With priority fields specified
        fab = FabricatorConfig(
            name="Test", part_number={"priority_fields": ["LCSC", "MPN"]}
        )
        self.assertEqual(fab.part_number_fields, ["LCSC", "MPN"])

        # Without priority fields (default empty)
        fab_default = FabricatorConfig(name="Test")
        self.assertEqual(fab_default.part_number_fields, [])

    def test_fabricator_config_immutable_properties(self):
        """Test that properties are read-only and computed dynamically."""
        fab = FabricatorConfig(name="Test", id="original")

        # Properties should be read-only (can't set them)
        with self.assertRaises(AttributeError):
            fab.cli_flags = ["--custom"]

        with self.assertRaises(AttributeError):
            fab.cli_presets = ["+custom"]

        with self.assertRaises(AttributeError):
            fab.part_number_header = "Custom"

    def test_fabricator_config_dynamic_properties(self):
        """Test that properties update when underlying data changes."""
        fab = FabricatorConfig(name="Test", id="original")
        self.assertEqual(fab.cli_flags, ["--original"])

        # Change the underlying data
        fab.id = "changed"
        # Property should reflect the change
        self.assertEqual(fab.cli_flags, ["--changed"])


class TestConfigLoader(unittest.TestCase):
    """Unit tests for ConfigLoader internal methods."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(self._cleanup_temp_dir)
        self.loader = ConfigLoader()

    def _cleanup_temp_dir(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_yaml_file(self):
        """Test YAML file loading method."""
        # Create test YAML file
        test_file = self.temp_dir / "test.yaml"
        test_data = {"key1": "value1", "key2": {"nested": "value"}}

        with open(test_file, "w") as f:
            yaml.dump(test_data, f)

        # Load and verify
        result = self.loader._load_yaml_file(test_file)
        self.assertEqual(result, test_data)

    def test_load_yaml_file_empty(self):
        """Test loading empty YAML file."""
        empty_file = self.temp_dir / "empty.yaml"
        empty_file.touch()

        result = self.loader._load_yaml_file(empty_file)
        self.assertEqual(result, {})

    def test_fabricator_to_dict(self):
        """Test fabricator-to-dict conversion."""
        fab = FabricatorConfig(
            name="Test Fab",
            id="test",
            description="Test description",
            pcb_manufacturing={"website": "example.com"},
            part_number={"header": "P/N"},
            bom_columns={"Part": "reference"},
        )

        result = self.loader._fabricator_to_dict(fab)

        expected = {
            "name": "Test Fab",
            "id": "test",
            "description": "Test description",
            "pcb_manufacturing": {"website": "example.com"},
            "pcb_assembly": {},
            "part_number": {"header": "P/N"},
            "bom_columns": {"Part": "reference"},
            "pos_columns": {},
        }

        self.assertEqual(result, expected)

    def test_dict_to_config_minimal(self):
        """Test converting minimal dict to JBOMConfig."""
        data = {"version": "3.0.0"}

        config = self.loader._dict_to_config(data)

        self.assertIsInstance(config, JBOMConfig)
        self.assertEqual(config.version, "3.0.0")
        self.assertEqual(len(config.fabricators), 0)

    def test_dict_to_config_with_fabricators(self):
        """Test converting dict with fabricators to JBOMConfig."""
        data = {
            "version": "3.0.0",
            "fabricators": [
                {"name": "Test Fab", "id": "test", "description": "Test fabricator"}
            ],
        }

        config = self.loader._dict_to_config(data)

        self.assertEqual(len(config.fabricators), 1)
        fab = config.fabricators[0]
        self.assertEqual(fab.name, "Test Fab")
        self.assertEqual(fab.id, "test")

    def test_load_fabricator_inline(self):
        """Test loading fabricator from inline config (no external file)."""
        fab_data = {
            "name": "Inline Fab",
            "id": "inline",
            "description": "Inline fabricator",
            "part_number": {"header": "P/N"},
            "bom_columns": {"Part": "reference"},
        }

        fab = self.loader._load_fabricator(fab_data)

        self.assertIsNotNone(fab)
        self.assertEqual(fab.name, "Inline Fab")
        self.assertEqual(fab.id, "inline")
        self.assertEqual(fab.part_number_header, "P/N")
        self.assertEqual(fab.bom_columns["Part"], "reference")

    def test_load_fabricator_with_external_file(self):
        """Test loading fabricator from external file."""
        # Create external file
        ext_file = self.temp_dir / "external.yaml"
        ext_data = {
            "name": "External Fab",
            "id": "external",
            "description": "From external file",
            "part_number": {"header": "EXT_P/N"},
        }
        with open(ext_file, "w") as f:
            yaml.dump(ext_data, f)

        # Mock the package path resolution to use our temp file
        original_method = self.loader._load_fabricator

        def mock_load_fabricator(fab_data):
            if "file" in fab_data:
                # Replace with our temp file path
                fab_data = deepcopy(fab_data)
                fab_data["file"] = str(ext_file)
            return original_method(fab_data)

        self.loader._load_fabricator = mock_load_fabricator

        fab_data = {"name": "override_name", "file": "external.yaml"}

        fab = self.loader._load_fabricator(fab_data)

        # Should merge external data with overrides
        self.assertIsNotNone(fab)
        self.assertEqual(fab.name, "override_name")  # Override
        self.assertEqual(fab.id, "external")  # From external
        self.assertEqual(fab.part_number_header, "EXT_P/N")  # From external

    def test_get_config_paths(self):
        """Test configuration path resolution."""
        paths = self.loader._get_config_paths()

        # Should return a list of Path objects (may be empty if no configs exist)
        self.assertIsInstance(paths, list)
        for path in paths:
            self.assertIsInstance(path, Path)

        # Test the path generation logic by creating a temp config file
        # and ensuring it would be found
        import platform

        home = Path.home()

        # Create a temporary config file in the user's config directory
        if platform.system() == "Darwin":
            test_config_dir = home / "Library" / "Application Support" / "jbom"
        elif platform.system() == "Windows":
            test_config_dir = home / "AppData" / "Roaming" / "jbom"
        else:  # Linux
            test_config_dir = home / ".config" / "jbom"

        test_config_dir.mkdir(parents=True, exist_ok=True)
        test_config_file = test_config_dir / "config.yaml"

        try:
            # Create temporary config file
            test_config_file.write_text("version: '3.0.0'\n")

            # Now test that it gets found
            new_loader = ConfigLoader()
            new_paths = new_loader._get_config_paths()

            # Should now include our test file
            self.assertIn(test_config_file, new_paths)

        finally:
            # Clean up
            if test_config_file.exists():
                test_config_file.unlink()
            if test_config_dir.exists() and not list(test_config_dir.iterdir()):
                test_config_dir.rmdir()

    def test_builtin_config_fallback(self):
        """Test that builtin config fallback works when package files missing."""
        # This test assumes package files don't exist or can't be loaded
        config = self.loader._get_builtin_config()

        self.assertIsInstance(config, JBOMConfig)
        self.assertEqual(config.version, "3.0.0")
        # Should have at least one fabricator (generic fallback)
        self.assertGreater(len(config.fabricators), 0)

    def test_find_base_fabricator_not_implemented(self):
        """Test that find_base_fabricator returns None (not implemented yet)."""
        result = self.loader._find_base_fabricator("nonexistent")
        self.assertIsNone(result)


class TestJBOMConfig(unittest.TestCase):
    """Unit tests for JBOMConfig methods."""

    def setUp(self):
        """Set up test config."""
        self.config = JBOMConfig()
        self.config.fabricators = [
            FabricatorConfig(name="Test1", id="test1"),
            FabricatorConfig(name="Test2", id="test2"),
        ]

    def test_get_fabricator_by_id(self):
        """Test finding fabricator by ID."""
        fab = self.config.get_fabricator("test1")
        self.assertIsNotNone(fab)
        self.assertEqual(fab.name, "Test1")

        # Case insensitive
        fab2 = self.config.get_fabricator("TEST2")
        self.assertIsNotNone(fab2)
        self.assertEqual(fab2.name, "Test2")

        # Not found
        fab3 = self.config.get_fabricator("nonexistent")
        self.assertIsNone(fab3)

    def test_get_fabricator_by_cli_flag(self):
        """Test finding fabricator by CLI flag."""
        fab = self.config.get_fabricator_by_cli_flag("--test1")
        self.assertIsNotNone(fab)
        self.assertEqual(fab.name, "Test1")

        # Not found
        fab2 = self.config.get_fabricator_by_cli_flag("--nonexistent")
        self.assertIsNone(fab2)

    def test_get_fabricator_by_preset(self):
        """Test finding fabricator by preset name."""
        fab = self.config.get_fabricator_by_preset("+test1")
        self.assertIsNotNone(fab)
        self.assertEqual(fab.name, "Test1")

        # Not found
        fab2 = self.config.get_fabricator_by_preset("+nonexistent")
        self.assertIsNone(fab2)


if __name__ == "__main__":
    unittest.main()
