"""Tests for the component classification engine."""
import unittest
from unittest.mock import patch

from jbom.processors.classifier import ClassificationEngine, Rule, get_engine
from jbom.common.config import ClassifierConfig, JBOMConfig


class TestRuleEvaluation(unittest.TestCase):
    """Test individual rule evaluation logic."""

    def setUp(self):
        self.engine = ClassificationEngine()

    def test_contains(self):
        """Test 'contains' operator."""
        rule = Rule(field="lib_id", op="contains", value="resistor")
        self.assertTrue(self.engine._evaluate_rule(rule, {"lib_id": "device:resistor"}))
        # The engine expects context values to be pre-normalized to lowercase
        self.assertTrue(self.engine._evaluate_rule(rule, {"lib_id": "resistor"}))
        self.assertFalse(
            self.engine._evaluate_rule(rule, {"lib_id": "device:capacitor"})
        )

    def test_startswith(self):
        """Test 'startswith' operator."""
        rule = Rule(field="lib_id", op="startswith", value="device:")
        self.assertTrue(self.engine._evaluate_rule(rule, {"lib_id": "device:resistor"}))
        self.assertFalse(self.engine._evaluate_rule(rule, {"lib_id": "mylib:device"}))

    def test_endswith(self):
        """Test 'endswith' operator."""
        rule = Rule(field="lib_id", op="endswith", value=":r")
        self.assertTrue(self.engine._evaluate_rule(rule, {"lib_id": "device:r"}))
        self.assertFalse(
            self.engine._evaluate_rule(rule, {"lib_id": "device:resistor"})
        )

    def test_eq(self):
        """Test 'eq' operator."""
        rule = Rule(field="lib_id", op="eq", value="r")
        self.assertTrue(self.engine._evaluate_rule(rule, {"lib_id": "r"}))
        self.assertFalse(self.engine._evaluate_rule(rule, {"lib_id": "r1"}))

    def test_matches(self):
        """Test 'matches' regex operator."""
        rule = Rule(field="lib_id", op="matches", value=r"^led_\d+$")
        self.assertTrue(self.engine._evaluate_rule(rule, {"lib_id": "led_0603"}))
        self.assertFalse(self.engine._evaluate_rule(rule, {"lib_id": "led"}))

    def test_case_insensitivity(self):
        """Test that matching is case-insensitive."""
        rule = Rule(field="lib_id", op="eq", value="RES")
        self.assertTrue(self.engine._evaluate_rule(rule, {"lib_id": "res"}))


class TestClassificationEngine(unittest.TestCase):
    """Test the full classification engine with config."""

    def setUp(self):
        # Create a mock config with known rules
        self.mock_config = JBOMConfig()
        self.mock_config.component_classifiers = [
            ClassifierConfig(
                type="RES",
                rules=[
                    "lib_id contains resistor",
                    "footprint contains res",
                ],
            ),
            ClassifierConfig(
                type="LED",
                rules=[
                    "lib_id contains led",
                ],
            ),
        ]

        # Reset global engine
        from jbom.processors import classifier

        classifier._engine = None

    @patch("jbom.processors.classifier.get_config")
    def test_classify_resistor(self, mock_get_config):
        """Test classifying a resistor."""
        mock_get_config.return_value = self.mock_config
        engine = get_engine()

        # Match by lib_id
        self.assertEqual(engine.classify("Device:Resistor", ""), "RES")
        # Match by footprint
        self.assertEqual(engine.classify("Unknown", "MyLib:0603-RES"), "RES")

    @patch("jbom.processors.classifier.get_config")
    def test_classify_led(self, mock_get_config):
        """Test classifying an LED."""
        mock_get_config.return_value = self.mock_config
        engine = get_engine()

        self.assertEqual(engine.classify("Device:LED", ""), "LED")

    @patch("jbom.processors.classifier.get_config")
    def test_classify_no_match(self, mock_get_config):
        """Test when no rules match."""
        mock_get_config.return_value = self.mock_config
        engine = get_engine()

        self.assertIsNone(engine.classify("Device:Unknown", "MyLib:Unknown"))

    @patch("jbom.processors.classifier.get_config")
    def test_rule_precedence(self, mock_get_config):
        """Test that the first matching classifier wins."""
        # Add a conflict: something that matches both RES and LED rules
        # (This is unlikely in practice but tests the logic)
        self.mock_config.component_classifiers.append(
            ClassifierConfig(
                type="LED",
                rules=["lib_id contains resistor"],  # Bogus rule to test conflict
            )
        )
        # RES comes first in the list
        mock_get_config.return_value = self.mock_config
        engine = get_engine()

        self.assertEqual(engine.classify("Device:Resistor", ""), "RES")


if __name__ == "__main__":
    unittest.main()
