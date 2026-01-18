#!/usr/bin/env python3
"""Test fabricator configuration loading."""

import unittest
from jbom.config.fabricators import (
    list_fabricators,
    load_fabricator,
    headers_for_fields,
)


class TestFabricators(unittest.TestCase):
    """Test fabricator configuration functionality."""

    def test_list_fabricators(self):
        """Test that fabricators can be listed."""
        fabricators = list_fabricators()
        self.assertIsInstance(fabricators, list)
        self.assertIn("jlc", fabricators)

    def test_load_fabricator_jlc(self):
        """Test loading JLCPCB fabricator config."""
        jlc = load_fabricator("jlc")
        self.assertEqual(jlc.id, "jlc")
        self.assertEqual(jlc.name, "JLCPCB")
        self.assertIsInstance(jlc.pos_columns, dict)
        self.assertIn("Designator", jlc.pos_columns)
        self.assertEqual(jlc.pos_columns["Designator"], "reference")

    def test_load_unknown_fabricator(self):
        """Test that loading unknown fabricator raises ValueError."""
        with self.assertRaises(ValueError):
            load_fabricator("nonexistent")

    def test_headers_for_fields_with_fabricator(self):
        """Test header mapping with fabricator."""
        jlc = load_fabricator("jlc")
        fields = ["reference", "x", "y", "value"]
        headers = headers_for_fields(jlc, fields)
        expected = ["Designator", "Mid X", "Mid Y", "Comment"]
        self.assertEqual(headers, expected)

    def test_headers_for_fields_without_fabricator(self):
        """Test header mapping without fabricator uses defaults."""
        fields = ["reference", "x", "y", "value"]
        headers = headers_for_fields(None, fields)
        expected = ["Designator", "Mid X", "Mid Y", "Val"]
        self.assertEqual(headers, expected)

    def test_headers_for_fields_unknown_field(self):
        """Test header mapping with unknown field."""
        headers = headers_for_fields(None, ["unknown_field"])
        self.assertEqual(headers, ["unknown_field"])


if __name__ == "__main__":
    unittest.main()
