"""Functional tests for component classification and inventory generation.

Tests:
1. Custom rules in config (overriding defaults)
2. Blank IPN generation for unknown types
"""
import unittest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

from jbom.common.config import reload_config
from jbom.processors.component_types import get_component_type
from jbom.loaders.project_inventory import ProjectInventoryLoader
from jbom.common.types import Component


class TestFunctionalClassification(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self._cleanup())
        # Reset config before test
        reload_config()

    def _cleanup(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Reset config after test
        reload_config()

    def test_custom_rule_override(self):
        """Test that a custom rule in user config correctly classifies a component."""
        # Define a custom rule for a made-up component type "FLUX_CAPACITOR"
        # that matches lib_id "flux"
        custom_config = {
            "component_classifiers": [
                {"type": "FLUX_CAPACITOR", "rules": ["lib_id contains flux"]}
            ]
        }

        config_file = self.temp_dir / "jbom.yaml"
        with open(config_file, "w") as f:
            yaml.dump(custom_config, f)

        # Mock the config loader to see our file
        with patch("jbom.common.config.ConfigLoader._get_config_paths") as mock_paths:
            mock_paths.return_value = [config_file]
            reload_config()

            # Test classification
            # Should match our custom rule
            comp_type = get_component_type("MyLib:Flux_Core", "Capacitor_SMD")
            self.assertEqual(comp_type, "FLUX_CAPACITOR")

            # Should still match standard rules (e.g. RES)
            comp_type_res = get_component_type("Device:R", "R_0603")
            self.assertEqual(comp_type_res, "RES")

    def test_blank_ipn_for_unknown_type(self):
        """Test that unknown component types result in blank IPNs."""
        # Create a component that won't match any standard rules
        comp = Component(
            reference="U1",
            lib_id="Unknown:Thingamajig",
            value="100",
            footprint="Weird_Footprint",
            uuid="123",
            properties={},
        )

        # Verify it classifies as None
        comp_type = get_component_type(comp.lib_id, comp.footprint)
        self.assertIsNone(comp_type)

        # Generate inventory
        loader = ProjectInventoryLoader([comp])
        items, _ = loader.load()

        self.assertEqual(len(items), 1)
        item = items[0]

        # Check IPN is blank
        self.assertEqual(item.ipn, "")
        self.assertEqual(item.category, "Unknown")

    def test_ws2812_led_classification(self):
        """Verify standard rules classify WS2812 as LED (regression check)."""
        # WS2812B usually has lib_id like "Worldsemi:WS2812B" or footprint "WS2812B"

        # Case 1: lib_id match
        type1 = get_component_type("Worldsemi:WS2812B", "LED_5050")
        self.assertEqual(type1, "LED")

        # Case 2: footprint match
        type2 = get_component_type("Device:LED", "LED_WS2812B")
        self.assertEqual(type2, "LED")


if __name__ == "__main__":
    unittest.main()
