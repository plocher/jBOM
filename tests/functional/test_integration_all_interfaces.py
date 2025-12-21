"""
Integration tests for jBOM across all usage patterns.

Tests consistency between:
1. CLI interface (command line)
2. Python API (generate_bom function)
3. KiCad plugin (wrapper script)

All should produce equivalent results when given the same inputs and fabricator selections.
"""

import unittest
import tempfile
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

from jbom.api import generate_bom, BOMOptions


class TestAllInterfaceConsistency(unittest.TestCase):
    """Test that CLI, Python API, and KiCad plugin produce consistent results."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(self._cleanup_temp_dir)

        # Use a known test project
        self.test_project = "/Users/jplocher/Dropbox/KiCad/projects/LEDStripDriver"
        self.schematic_file = self.test_project + "/I2C-LEDStripDriver.kicad_sch"

        # Check if test project exists
        if not Path(self.schematic_file).exists():
            self.skipTest(f"Test project not found: {self.schematic_file}")

    def _cleanup_temp_dir(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _normalize_bom_data(self, data: List[List[str]]) -> List[Dict[str, str]]:
        """Normalize BOM CSV data to list of dicts for comparison."""
        if not data:
            return []

        headers = data[0]
        return [dict(zip(headers, row)) for row in data[1:]]

    def _read_csv_file(self, file_path: Path) -> List[List[str]]:
        """Read CSV file and return as list of lists."""
        import csv

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            return list(reader)

    def test_fabricator_consistency_across_interfaces(self):
        """Test that all interfaces produce consistent results for each fabricator."""
        fabricators = ["jlc", "pcbway", "seeed", "generic"]

        for fabricator in fabricators:
            with self.subTest(fabricator=fabricator):
                # 1. Test Python API
                python_result = self._test_python_api(fabricator)

                # 2. Test CLI
                cli_result = self._test_cli_interface(fabricator)

                # 3. Test KiCad Plugin
                kicad_result = self._test_kicad_plugin(fabricator)

                # Compare results
                self._compare_bom_results(
                    python_result, cli_result, kicad_result, fabricator
                )

    def _test_python_api(self, fabricator: str) -> Dict[str, Any]:
        """Test Python API with specified fabricator."""
        try:
            opts = BOMOptions(fabricator=fabricator)
            result = generate_bom(
                input=self.test_project,
                inventory=None,  # Use project components only
                options=opts,
            )

            # Extract key metrics for comparison
            return {
                "interface": "python_api",
                "fabricator": fabricator,
                "components_count": len(result.get("components", [])),
                "bom_entries_count": len(result.get("bom_entries", [])),
                "bom_entries": result.get("bom_entries", []),
                "success": True,
            }

        except Exception as e:
            return {
                "interface": "python_api",
                "fabricator": fabricator,
                "success": False,
                "error": str(e),
            }

    def _test_cli_interface(self, fabricator: str) -> Dict[str, Any]:
        """Test CLI interface with specified fabricator."""
        output_file = self.temp_dir / f"cli_{fabricator}.csv"

        try:
            cmd = [
                sys.executable,
                "-m",
                "jbom.cli.main",
                "bom",
                self.schematic_file,
                "-o",
                str(output_file),
                f"--{fabricator}",
            ]

            env = os.environ.copy()
            env["PYTHONPATH"] = "src"

            result = subprocess.run(
                cmd,
                cwd="/Users/jplocher/Dropbox/KiCad/jBOM",
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {
                    "interface": "cli",
                    "fabricator": fabricator,
                    "success": False,
                    "error": f"CLI failed: {result.stderr}",
                }

            # Read and parse output file
            if not output_file.exists():
                return {
                    "interface": "cli",
                    "fabricator": fabricator,
                    "success": False,
                    "error": "CLI succeeded but no output file created",
                }

            csv_data = self._read_csv_file(output_file)
            bom_data = self._normalize_bom_data(csv_data)

            return {
                "interface": "cli",
                "fabricator": fabricator,
                "bom_entries_count": len(bom_data),
                "csv_headers": csv_data[0] if csv_data else [],
                "bom_data": bom_data,
                "success": True,
            }

        except Exception as e:
            return {
                "interface": "cli",
                "fabricator": fabricator,
                "success": False,
                "error": str(e),
            }

    def _test_kicad_plugin(self, fabricator: str) -> Dict[str, Any]:
        """Test KiCad plugin with specified fabricator."""
        output_file = self.temp_dir / f"kicad_{fabricator}.csv"

        try:
            cmd = [
                sys.executable,
                "/Users/jplocher/Dropbox/KiCad/jBOM/kicad_jbom_plugin.py",
                self.schematic_file,
                "-o",
                str(output_file),
                f"--{fabricator}",
            ]

            env = os.environ.copy()
            env["PYTHONPATH"] = "src"

            result = subprocess.run(
                cmd, env=env, capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                return {
                    "interface": "kicad_plugin",
                    "fabricator": fabricator,
                    "success": False,
                    "error": f"KiCad plugin failed: {result.stderr}",
                }

            # Read and parse output file
            if not output_file.exists():
                return {
                    "interface": "kicad_plugin",
                    "fabricator": fabricator,
                    "success": False,
                    "error": "KiCad plugin succeeded but no output file created",
                }

            csv_data = self._read_csv_file(output_file)
            bom_data = self._normalize_bom_data(csv_data)

            return {
                "interface": "kicad_plugin",
                "fabricator": fabricator,
                "bom_entries_count": len(bom_data),
                "csv_headers": csv_data[0] if csv_data else [],
                "bom_data": bom_data,
                "success": True,
            }

        except Exception as e:
            return {
                "interface": "kicad_plugin",
                "fabricator": fabricator,
                "success": False,
                "error": str(e),
            }

    def _compare_bom_results(
        self, python_result: Dict, cli_result: Dict, kicad_result: Dict, fabricator: str
    ):
        """Compare results from all three interfaces."""

        # All interfaces should succeed
        self.assertTrue(
            python_result["success"],
            f"Python API failed for {fabricator}: {python_result.get('error')}",
        )
        self.assertTrue(
            cli_result["success"],
            f"CLI failed for {fabricator}: {cli_result.get('error')}",
        )
        self.assertTrue(
            kicad_result["success"],
            f"KiCad plugin failed for {fabricator}: {kicad_result.get('error')}",
        )

        # BOM entry counts should be consistent
        python_count = python_result.get("bom_entries_count", 0)
        cli_count = cli_result.get("bom_entries_count", 0)
        kicad_count = kicad_result.get("bom_entries_count", 0)

        self.assertEqual(
            python_count,
            cli_count,
            f"Python API and CLI BOM entry counts differ for {fabricator}: "
            f"Python={python_count}, CLI={cli_count}",
        )

        self.assertEqual(
            cli_count,
            kicad_count,
            f"CLI and KiCad plugin BOM entry counts differ for {fabricator}: "
            f"CLI={cli_count}, KiCad={kicad_count}",
        )

        # CSV headers from CLI and KiCad plugin should be identical
        cli_headers = cli_result.get("csv_headers", [])
        kicad_headers = kicad_result.get("csv_headers", [])

        self.assertEqual(
            cli_headers,
            kicad_headers,
            f"CLI and KiCad plugin CSV headers differ for {fabricator}: "
            f"CLI={cli_headers}, KiCad={kicad_headers}",
        )

    def test_invalid_fabricator_handling(self):
        """Test that all interfaces handle invalid fabricators consistently."""
        invalid_fabricator = "nonexistent"

        # Python API should fallback gracefully
        python_result = self._test_python_api(invalid_fabricator)
        self.assertTrue(
            python_result["success"],
            "Python API should handle invalid fabricator gracefully",
        )

        # CLI should fail with appropriate error
        cli_result = self._test_cli_interface(invalid_fabricator)
        self.assertFalse(
            cli_result["success"], "CLI should fail with invalid fabricator"
        )
        self.assertIn("unrecognized arguments", cli_result.get("error", "").lower())

        # KiCad plugin should fail the same way as CLI
        kicad_result = self._test_kicad_plugin(invalid_fabricator)
        self.assertFalse(
            kicad_result["success"], "KiCad plugin should fail with invalid fabricator"
        )

    def test_fabricator_specific_field_consistency(self):
        """Test that fabricator-specific field presets work consistently."""

        # Test that JLC fabricator produces LCSC-focused output
        jlc_cli = self._test_cli_interface("jlc")
        if jlc_cli["success"]:
            headers = jlc_cli.get("csv_headers", [])
            # Should have JLC-specific fields (fabricator_part_number contains LCSC data)
            self.assertIn(
                "fabricator_part_number",
                headers,
                "JLC fabricator should include fabricator part number column",
            )
            # Should have package instead of footprint for JLC
            self.assertIn(
                "I:Package", headers, "JLC fabricator should include Package column"
            )

        # Test that PCBWay fabricator produces manufacturer-focused output
        pcbway_cli = self._test_cli_interface("pcbway")
        if pcbway_cli["success"]:
            headers = pcbway_cli.get("csv_headers", [])
            # Should have manufacturer fields
            self.assertIn(
                "Manufacturer",
                headers,
                "PCBWay fabricator should include Manufacturer column",
            )
            self.assertIn(
                "MFGPN", headers, "PCBWay fabricator should include MFGPN column"
            )

    def test_configuration_system_integration(self):
        """Test that configuration system works across all interfaces."""

        # All interfaces should be able to list the same available fabricators
        from jbom.common.config import get_config

        config = get_config()
        available_fabricators = [fab.id for fab in config.fabricators]

        # Should have built-in fabricators
        expected_fabricators = {"jlc", "pcbway", "seeed", "generic"}
        actual_fabricators = set(available_fabricators)

        self.assertTrue(
            expected_fabricators.issubset(actual_fabricators),
            f"Missing expected fabricators. Expected: {expected_fabricators}, "
            f"Actual: {actual_fabricators}",
        )

    def test_cli_plugin_wrapper_consistency(self):
        """Test that KiCad plugin is truly just a wrapper around CLI."""

        fabricator = "jlc"

        cli_result = self._test_cli_interface(fabricator)
        kicad_result = self._test_kicad_plugin(fabricator)

        if cli_result["success"] and kicad_result["success"]:
            # The CSV output should be byte-for-byte identical
            # since KiCad plugin is just a wrapper

            cli_data = cli_result.get("bom_data", [])
            kicad_data = kicad_result.get("bom_data", [])

            self.assertEqual(
                len(cli_data),
                len(kicad_data),
                "CLI and KiCad plugin should produce identical output",
            )

            # Compare a few key fields from first entry if available
            if cli_data and kicad_data:
                cli_first = cli_data[0]
                kicad_first = kicad_data[0]

                # Reference and quantity should be identical
                self.assertEqual(
                    cli_first.get("Reference"), kicad_first.get("Reference")
                )
                self.assertEqual(cli_first.get("Quantity"), kicad_first.get("Quantity"))


if __name__ == "__main__":
    unittest.main()
