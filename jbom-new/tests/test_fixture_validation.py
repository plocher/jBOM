"""
Test for fixture validation to ensure we're not creating circular test patterns.

This test validates that our KiCad fixtures are authentic by comparing them
against real KiCad projects and using KiCad's native CLI validation tools.
"""

import json
import subprocess
import unittest
from pathlib import Path


class TestFixtureValidation(unittest.TestCase):
    """Test fixture authenticity to prevent circular test patterns."""

    def setUp(self):
        self.fixtures_dir = Path("features/fixtures/kicad_templates")
        self.real_projects_dir = Path("/Users/jplocher/Dropbox/KiCad/projects")
        self.kicad_cli = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")

    def test_fixture_directory_exists(self):
        """Fixtures directory should exist."""
        self.assertTrue(
            self.fixtures_dir.exists(),
            f"Fixtures directory not found: {self.fixtures_dir}",
        )

    def test_kicad_cli_available(self):
        """KiCad CLI should be available for validation."""
        self.assertTrue(
            self.kicad_cli.exists(), f"KiCad CLI not found at {self.kicad_cli}"
        )

    def test_real_projects_available(self):
        """Real KiCad projects should be available for comparison."""
        self.assertTrue(
            self.real_projects_dir.exists(),
            f"Real projects directory not found: {self.real_projects_dir}",
        )

        real_projects = list(self.real_projects_dir.glob("**/*.kicad_pro"))
        self.assertGreater(
            len(real_projects), 0, "No real KiCad projects found for comparison"
        )

    def test_fixture_structure_authenticity(self):
        """Fixtures should have same structure as real KiCad projects."""
        # Get structure from a known real project
        real_project = self.real_projects_dir / "Brakeman-BLUE/Brakeman.kicad_pro"
        self.assertTrue(
            real_project.exists(), f"Test real project not found: {real_project}"
        )

        with open(real_project) as f:
            real_data = json.load(f)
        real_keys = set(real_data.keys())

        # Check our main fixture has compatible structure
        fixture_project = self.fixtures_dir / "empty_project/empty.kicad_pro"
        self.assertTrue(
            fixture_project.exists(), f"Main fixture not found: {fixture_project}"
        )

        with open(fixture_project) as f:
            fixture_data = json.load(f)
        fixture_keys = set(fixture_data.keys())

        # Both should have the core required keys
        core_keys = {"board", "meta", "net_settings", "pcbnew", "schematic", "sheets"}
        self.assertTrue(
            core_keys.issubset(real_keys),
            f"Real project missing core keys: {core_keys - real_keys}",
        )
        self.assertTrue(
            core_keys.issubset(fixture_keys),
            f"Fixture missing core keys: {core_keys - fixture_keys}",
        )

        # Note: It's OK if fixture has fewer keys than real project (minimal valid structure)
        # But report significant differences for awareness
        missing_from_fixture = real_keys - fixture_keys
        if missing_from_fixture:
            print(
                f"Info: Fixture has minimal structure, missing: {missing_from_fixture}"
            )

    def test_schematic_validates_with_kicad_cli(self):
        """Schematic files should be accepted by KiCad's ERC tool."""
        schematic_file = self.fixtures_dir / "empty_project/empty.kicad_sch"
        self.assertTrue(
            schematic_file.exists(), f"Test schematic not found: {schematic_file}"
        )

        # Run KiCad ERC - it should at least parse the file without error
        try:
            result = subprocess.run(
                [
                    str(self.kicad_cli),
                    "sch",
                    "erc",
                    "--format",
                    "json",
                    str(schematic_file),
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            # ERC should parse the file (even if it finds violations, that's OK)
            # A parsing error would be in stderr and non-zero exit where stdout is empty
            if result.returncode != 0 and not result.stdout:
                self.fail(f"KiCad ERC failed to parse schematic: {result.stderr}")

        except subprocess.TimeoutExpired:
            self.fail("KiCad ERC validation timed out")
        except FileNotFoundError:
            self.skip("KiCad CLI not available for validation")

    def test_project_validates_structure(self):
        """Project files should have valid JSON structure with required fields."""
        project_file = self.fixtures_dir / "empty_project/empty.kicad_pro"
        self.assertTrue(
            project_file.exists(), f"Test project not found: {project_file}"
        )

        # Should parse as valid JSON
        with open(project_file) as f:
            data = json.load(f)

        # Should have meta section with proper version
        self.assertIn("meta", data, "Project missing meta section")
        meta = data["meta"]
        self.assertIn("version", meta, "Project meta missing version")
        self.assertIsInstance(meta["version"], int, "Project version should be integer")

        # Filename should match actual file
        self.assertEqual(
            meta["filename"],
            project_file.name,
            f"Filename mismatch: {meta['filename']} vs {project_file.name}",
        )

    def test_fake_kicad_content_eliminated(self):
        """Verify that fake minimal KiCad content is not present in fixtures."""
        # Check that we don't have the old fake content pattern
        for fixture_dir in self.fixtures_dir.iterdir():
            if fixture_dir.is_dir():
                for kicad_file in fixture_dir.glob("*.kicad_*"):
                    content = kicad_file.read_text()

                    # These were the fake patterns we used to generate
                    fake_patterns = [
                        "(kicad_project (version 1))",  # Old fake project
                        "(kicad_sch (version",  # Minimal fake schematic start
                    ]

                    for pattern in fake_patterns:
                        self.assertNotIn(
                            pattern,
                            content,
                            f"Found fake pattern '{pattern}' in {kicad_file}",
                        )

                    # Files should be substantial (not tiny fake content)
                    self.assertGreater(
                        len(content),
                        100,
                        f"File suspiciously small, may be fake: {kicad_file}",
                    )

    def test_validation_catches_fake_content(self):
        """Test that our validation would catch fake/invalid KiCad content."""
        # Create a temporary fake project to test our validation catches it
        import tempfile

        fake_content = '{"fake": "project", "not": "real_kicad"}'

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".kicad_pro", delete=False
        ) as f:
            f.write(fake_content)
            fake_project = Path(f.name)

        try:
            # Our validation should catch this as invalid
            from scripts.validate_fixtures import KiCadValidator

            validator = KiCadValidator()

            success, message = validator.validate_project_structure(fake_project)
            self.assertFalse(success, "Validation should reject fake project structure")
            self.assertIn(
                "Missing required project keys",
                message,
                f"Validation should identify missing keys, got: {message}",
            )
        finally:
            fake_project.unlink()  # Clean up


if __name__ == "__main__":
    unittest.main()
