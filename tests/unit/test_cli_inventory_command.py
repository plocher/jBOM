#!/usr/bin/env python3
"""Unit tests for InventoryCommand with search functionality."""
import unittest
from unittest.mock import Mock, patch
import argparse
import io
from pathlib import Path

from jbom.cli.inventory_command import InventoryCommand
from jbom.api import InventoryOptions


class TestInventoryCommand(unittest.TestCase):
    """Test InventoryCommand CLI functionality."""

    def setUp(self):
        """Set up test environment."""
        self.command = InventoryCommand()
        self.parser = argparse.ArgumentParser()
        self.command.setup_parser(self.parser)

    def test_setup_parser_basic_args(self):
        """Test that basic arguments are set up correctly."""
        args = self.parser.parse_args(["test_project"])

        self.assertEqual(args.project, "test_project")
        self.assertIsNone(args.output)
        self.assertFalse(args.search)
        self.assertEqual(args.provider, "mouser")
        self.assertIsNone(args.api_key)
        self.assertEqual(args.limit, "1")
        self.assertFalse(args.interactive)

    def test_setup_parser_search_args(self):
        """Test that search arguments are parsed correctly."""
        args = self.parser.parse_args(
            [
                "test_project",
                "--search",
                "--provider",
                "mouser",
                "--api-key",
                "test_key",
                "--limit",
                "3",
                "--interactive",
            ]
        )

        self.assertEqual(args.project, "test_project")
        self.assertTrue(args.search)
        self.assertEqual(args.provider, "mouser")
        self.assertEqual(args.api_key, "test_key")
        self.assertEqual(args.limit, "3")
        self.assertTrue(args.interactive)

    def test_setup_parser_limit_none(self):
        """Test parsing limit=none."""
        args = self.parser.parse_args(["test_project", "--limit", "none"])

        self.assertEqual(args.limit, "none")

    def test_setup_parser_output_options(self):
        """Test output argument parsing."""
        args = self.parser.parse_args(["test_project", "-o", "output.csv"])
        self.assertEqual(args.output, "output.csv")

        args = self.parser.parse_args(["test_project", "-o", "console"])
        self.assertEqual(args.output, "console")

    @patch("jbom.cli.inventory_command.generate_enriched_inventory")
    def test_execute_basic_inventory(self, mock_generate):
        """Test basic inventory generation without search."""
        # Mock successful API response
        mock_generate.return_value = {
            "success": True,
            "inventory_items": [Mock(), Mock()],
            "component_count": 2,
            "search_stats": {"search_enabled": False},
        }

        args = self.parser.parse_args(["test_project"])
        result = self.command.execute(args)

        self.assertEqual(result, 0)
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args

        # Check that API was called with correct arguments
        self.assertEqual(call_args[1]["input"], "test_project")
        self.assertIsInstance(call_args[1]["options"], InventoryOptions)
        self.assertFalse(call_args[1]["options"].search)

    @patch("jbom.cli.inventory_command.generate_enriched_inventory")
    def test_execute_with_search(self, mock_generate):
        """Test inventory generation with search enabled."""
        mock_generate.return_value = {
            "success": True,
            "inventory_items": [Mock(), Mock(), Mock()],
            "component_count": 2,
            "search_stats": {
                "provider": "mouser",
                "searches_performed": 2,
                "successful_searches": 2,
                "failed_searches": 0,
            },
        }

        args = self.parser.parse_args(
            ["test_project", "--search", "--limit", "2", "--api-key", "test_key"]
        )

        # Capture stdout to check search statistics output
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            result = self.command.execute(args)

        self.assertEqual(result, 0)
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args

        # Check API call options
        options = call_args[1]["options"]
        self.assertTrue(options.search)
        self.assertEqual(options.provider, "mouser")
        self.assertEqual(options.api_key, "test_key")
        self.assertEqual(options.limit, 2)

        # Check that search statistics were printed
        output = captured_output.getvalue()
        self.assertIn("Search statistics:", output)
        self.assertIn("Provider: mouser", output)
        self.assertIn("Searches performed: 2", output)

    @patch("jbom.cli.inventory_command.generate_enriched_inventory")
    def test_execute_limit_none(self, mock_generate):
        """Test executing with limit=none."""
        mock_generate.return_value = {
            "success": True,
            "inventory_items": [Mock() for _ in range(5)],
            "component_count": 2,
            "search_stats": {"search_enabled": False},
        }

        args = self.parser.parse_args(["test_project", "--limit", "none"])
        result = self.command.execute(args)

        self.assertEqual(result, 0)
        call_args = mock_generate.call_args
        options = call_args[1]["options"]
        self.assertIsNone(options.limit)  # Should be None, not 'none'

    def test_execute_invalid_limit_negative(self):
        """Test error handling for invalid limit values."""
        args = self.parser.parse_args(["test_project", "--limit", "-1"])

        captured_output = io.StringIO()
        with patch("sys.stderr", captured_output):
            result = self.command.execute(args)

        self.assertEqual(result, 1)
        self.assertIn("--limit must be a positive integer", captured_output.getvalue())

    def test_execute_invalid_limit_string(self):
        """Test error handling for non-numeric limit values."""
        args = self.parser.parse_args(["test_project", "--limit", "invalid"])

        captured_output = io.StringIO()
        with patch("sys.stderr", captured_output):
            result = self.command.execute(args)

        self.assertEqual(result, 1)
        self.assertIn("--limit must be a positive integer", captured_output.getvalue())

    @patch("jbom.cli.inventory_command.generate_enriched_inventory")
    def test_execute_api_error(self, mock_generate):
        """Test handling of API errors."""
        mock_generate.return_value = {
            "success": False,
            "error": "Project not found",
            "inventory_items": [],
            "component_count": 0,
            "search_stats": {},
        }

        args = self.parser.parse_args(["nonexistent_project"])

        captured_output = io.StringIO()
        with patch("sys.stderr", captured_output):
            result = self.command.execute(args)

        self.assertEqual(result, 1)
        self.assertIn("Error: Project not found", captured_output.getvalue())

    @patch("jbom.cli.inventory_command.resolve_output_path")
    @patch("jbom.cli.inventory_command.generate_enriched_inventory")
    def test_execute_with_output_file(self, mock_generate, mock_resolve_path):
        """Test execution with file output."""
        mock_generate.return_value = {
            "success": True,
            "inventory_items": [Mock(), Mock()],
            "component_count": 2,
            "search_stats": {"search_enabled": False},
        }
        mock_resolve_path.return_value = Path("test_inventory.csv")

        args = self.parser.parse_args(["test_project", "-o", "inventory.csv"])

        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            result = self.command.execute(args)

        self.assertEqual(result, 0)

        # Check API was called with correct output
        call_args = mock_generate.call_args
        self.assertEqual(str(call_args[1]["output"]), "inventory.csv")

        # Check success message was printed
        output = captured_output.getvalue()
        self.assertIn("Successfully generated 2 inventory items", output)

    @patch("jbom.cli.inventory_command.generate_enriched_inventory")
    def test_execute_console_output(self, mock_generate):
        """Test execution with console output."""
        mock_generate.return_value = {
            "success": True,
            "inventory_items": [Mock(), Mock()],
            "component_count": 2,
            "search_stats": {"search_enabled": False},
        }

        args = self.parser.parse_args(["test_project", "-o", "console"])
        result = self.command.execute(args)

        self.assertEqual(result, 0)

        # Check API was called with console output
        call_args = mock_generate.call_args
        self.assertEqual(call_args[1]["output"], "console")

    @patch("jbom.cli.inventory_command.generate_enriched_inventory")
    def test_execute_stdout_output(self, mock_generate):
        """Test execution with stdout output."""
        mock_generate.return_value = {
            "success": True,
            "inventory_items": [Mock(), Mock()],
            "component_count": 2,
            "search_stats": {"search_enabled": False},
        }

        args = self.parser.parse_args(["test_project", "-o", "-"])
        result = self.command.execute(args)

        self.assertEqual(result, 0)

        # Check API was called with stdout output
        call_args = mock_generate.call_args
        self.assertEqual(call_args[1]["output"], "stdout")

    @patch("jbom.cli.inventory_command.generate_enriched_inventory")
    def test_execute_search_with_multiple_results(self, mock_generate):
        """Test search execution with multiple results and statistics."""
        mock_generate.return_value = {
            "success": True,
            "inventory_items": [
                Mock() for _ in range(6)
            ],  # 3 components, 2 results each
            "component_count": 3,
            "search_stats": {
                "provider": "mouser",
                "searches_performed": 3,
                "successful_searches": 2,
                "failed_searches": 1,
            },
        }

        args = self.parser.parse_args(
            ["test_project", "--search", "--limit", "2", "-o", "enriched.csv"]
        )

        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            result = self.command.execute(args)

        self.assertEqual(result, 0)

        output = captured_output.getvalue()
        self.assertIn("Successfully generated 6 inventory items", output)
        self.assertIn("Search statistics:", output)
        self.assertIn("Successful: 2", output)
        self.assertIn("Failed: 1", output)
        self.assertIn("Output written to: enriched.csv", output)

    def test_provider_choices(self):
        """Test that only valid providers are accepted."""
        # Valid provider should work
        args = self.parser.parse_args(["test_project", "--provider", "mouser"])
        self.assertEqual(args.provider, "mouser")

        # Invalid provider should cause parser error
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["test_project", "--provider", "invalid"])

    def test_help_output(self):
        """Test that help output includes search options."""
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            try:
                self.parser.parse_args(["--help"])
            except SystemExit:
                pass  # Expected for --help

        help_text = captured_output.getvalue()
        self.assertIn("--search", help_text)
        self.assertIn("--provider", help_text)
        self.assertIn("--api-key", help_text)
        self.assertIn("--limit", help_text)
        self.assertIn("--interactive", help_text)
        self.assertIn("Search Enhancement", help_text)


if __name__ == "__main__":
    unittest.main()
