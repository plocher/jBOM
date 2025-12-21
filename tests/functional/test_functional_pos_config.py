#!/usr/bin/env python3
"""Functional tests for config-driven POS generation."""
import os
import sys
from pathlib import Path

# Ensure tests directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from .test_functional_base import FunctionalTestBase


class TestPOSConfig(FunctionalTestBase):
    """Test POS command with custom configuration."""

    def test_custom_fabricator_pos_columns(self):
        """Verify custom POS columns from local config."""
        # Create a project-specific config file
        config_path = Path(self.tmp.name) / "jbom.yaml"
        config_path.write_text(
            """
fabricators:
  - name: "Test Fab"
    id: "testfab"
    description: "Custom test fabricator"
    pos_columns:
      "MyRef": "reference"
      "MyX": "x"
      "MySide": "side"
""",
            encoding="utf-8",
        )

        # We need to run jbom from the temp directory so it picks up jbom.yaml
        cwd = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            # Use absolute path to pcb file since we changed cwd
            pcb_file = self.modern_proj / "project.kicad_pcb"
            output = Path("pos_custom.csv")  # Relative to cwd

            # Run with --fabricator testfab (explicit fabricator selection)
            # Note: The first run might fail if config isn't reloaded,
            # but CLI main() usually initializes config fresh.
            # However, jbom.common.config._config_instance is global.
            # We might need to force reload it.
            # CLI commands don't explicit reload, they just get_config().
            # Ideally, we should patch the environment or rely on process isolation?
            # run_jbom runs in the same process. So we MUST force reload config.
            from jbom.common.config import reload_config
            from jbom.common.config_fabricators import reload_fabricators

            reload_config()
            reload_fabricators()

            rc, stdout, stderr = self.run_jbom(
                [
                    "pos",
                    str(pcb_file),
                    "-o",
                    str(output),
                    "--fabricator",
                    "testfab",
                    "--loader",
                    "sexp",
                ]
            )

            self.assertEqual(rc, 0, f"Command failed: {stderr}")
            rows = self.assert_csv_valid(output.resolve())

            # Verify custom headers
            header = rows[0]
            self.assertEqual(header, ["MyRef", "MyX", "MySide"])

            # Verify data
            # Check for any valid ref in the output (e.g. starting with R or C)
            found_ref = False
            for row in rows[1:]:
                if row[0].startswith("R") or row[0].startswith("C"):
                    found_ref = True
                    break
            self.assertTrue(
                found_ref, "Should contain resistor or capacitor references"
            )
            # Side should be TOP or BOTTOM
            self.assertTrue(any(row[2] in ["TOP", "BOTTOM"] for row in rows[1:]))

        finally:
            os.chdir(cwd)
            # Reset config to avoid polluting other tests
            from jbom.common.config import reload_config
            from jbom.common.config_fabricators import reload_fabricators

            reload_config()
            reload_fabricators()
