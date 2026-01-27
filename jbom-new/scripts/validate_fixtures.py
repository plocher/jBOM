#!/usr/bin/env python3
"""
KiCad Fixture Validation Script

Uses KiCad's native CLI tools to validate that our test fixtures are authentic
KiCad files that would be accepted by KiCad itself. This prevents circular
test/code patterns and ensures we're testing against real KiCad behavior.

Usage:
    python scripts/validate_fixtures.py [fixture_path]
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


class KiCadValidator:
    """Validates KiCad files using native KiCad CLI tools."""

    def __init__(self, kicad_cli_path: str = KICAD_CLI):
        self.kicad_cli = Path(kicad_cli_path)
        if not self.kicad_cli.exists():
            raise FileNotFoundError(f"KiCad CLI not found at {kicad_cli_path}")

    def validate_schematic(self, sch_file: Path) -> Tuple[bool, str]:
        """Validate schematic using KiCad ERC (Electrical Rules Check)."""
        if not sch_file.exists():
            return False, f"Schematic file not found: {sch_file}"

        try:
            # Run ERC with JSON output for programmatic parsing
            result = subprocess.run(
                [
                    str(self.kicad_cli),
                    "sch",
                    "erc",
                    "--format",
                    "json",
                    "--severity-all",
                    "--exit-code-violations",
                    str(sch_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # ERC exit code 0 means no violations, >0 means violations found
            if result.returncode == 0:
                return True, "Schematic validation passed"
            else:
                # Parse JSON output to get violation details
                try:
                    erc_data = json.loads(result.stdout) if result.stdout else {}
                    violations = erc_data.get("violations", [])
                    return (
                        False,
                        f"ERC found {len(violations)} violations: {result.stdout}",
                    )
                except json.JSONDecodeError:
                    return False, f"ERC failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "ERC validation timed out"
        except Exception as e:
            return False, f"ERC validation error: {str(e)}"

    def validate_pcb(self, pcb_file: Path) -> Tuple[bool, str]:
        """Validate PCB using KiCad DRC (Design Rules Check)."""
        if not pcb_file.exists():
            return False, f"PCB file not found: {pcb_file}"

        try:
            # Run DRC with JSON output
            result = subprocess.run(
                [
                    str(self.kicad_cli),
                    "pcb",
                    "drc",
                    "--format",
                    "json",
                    "--severity-all",
                    "--exit-code-violations",
                    str(pcb_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return True, "PCB validation passed"
            else:
                try:
                    drc_data = json.loads(result.stdout) if result.stdout else {}
                    violations = drc_data.get("violations", [])
                    return (
                        False,
                        f"DRC found {len(violations)} violations: {result.stdout}",
                    )
                except json.JSONDecodeError:
                    return False, f"DRC failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "DRC validation timed out"
        except Exception as e:
            return False, f"DRC validation error: {str(e)}"

    def validate_project_structure(self, project_file: Path) -> Tuple[bool, str]:
        """Validate KiCad project file structure against known real projects."""
        if not project_file.exists():
            return False, f"Project file not found: {project_file}"

        try:
            with open(project_file) as f:
                project_data = json.load(f)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON in project file: {str(e)}"
        except Exception as e:
            return False, f"Cannot read project file: {str(e)}"

        # Required top-level keys from authentic KiCad projects
        required_keys = {
            "board",
            "meta",
            "net_settings",
            "pcbnew",
            "schematic",
            "sheets",
            "libraries",
            "cvpcb",
        }

        missing_keys = required_keys - set(project_data.keys())
        if missing_keys:
            return False, f"Missing required project keys: {missing_keys}"

        # Validate meta section
        meta = project_data.get("meta", {})
        if meta.get("version") != 3:
            return False, f"Invalid project version: {meta.get('version')}, expected 3"

        # Validate filename consistency
        expected_filename = project_file.name
        actual_filename = meta.get("filename", "")
        if actual_filename != expected_filename:
            return (
                False,
                f"Filename mismatch: meta.filename='{actual_filename}' vs file='{expected_filename}'",
            )

        return True, "Project structure validation passed"

    def validate_fixture_directory(
        self, fixture_dir: Path
    ) -> Dict[str, List[Tuple[str, bool, str]]]:
        """Validate all KiCad files in a fixture directory."""
        results = {
            "project": [],
            "schematic": [],
            "pcb": [],
            "summary": {"passed": 0, "failed": 0, "total": 0},
        }

        # Find and validate all KiCad files
        for pattern, file_type, validator in [
            ("*.kicad_pro", "project", self.validate_project_structure),
            ("*.kicad_sch", "schematic", self.validate_schematic),
            ("*.kicad_pcb", "pcb", self.validate_pcb),
        ]:
            for file_path in fixture_dir.glob(pattern):
                success, message = validator(file_path)
                results[file_type].append((str(file_path), success, message))
                results["summary"]["total"] += 1
                if success:
                    results["summary"]["passed"] += 1
                else:
                    results["summary"]["failed"] += 1

        return results


def compare_with_real_projects(
    fixture_project: Path, real_projects_dir: Path
) -> Tuple[bool, str]:
    """Compare fixture structure with real KiCad projects to ensure authenticity."""
    if not fixture_project.exists():
        return False, f"Fixture project not found: {fixture_project}"

    try:
        with open(fixture_project) as f:
            fixture_data = json.load(f)
        fixture_keys = set(fixture_data.keys())
    except Exception as e:
        return False, f"Cannot read fixture project: {str(e)}"

    # Compare with multiple real projects
    real_project_files = list(real_projects_dir.glob("**/*.kicad_pro"))[
        :3
    ]  # Check up to 3 real projects

    if not real_project_files:
        return False, f"No real KiCad projects found in {real_projects_dir}"

    common_keys = None
    for real_project in real_project_files:
        try:
            with open(real_project) as f:
                real_data = json.load(f)
            real_keys = set(real_data.keys())

            if common_keys is None:
                common_keys = real_keys
            else:
                common_keys &= (
                    real_keys  # Intersection of keys across all real projects
                )
        except Exception:
            continue  # Skip problematic real projects

    if common_keys is None:
        return False, "Could not read any real projects for comparison"

    # Our fixture should have all keys that are common across real projects
    missing_keys = common_keys - fixture_keys
    extra_keys = fixture_keys - common_keys

    issues = []
    if missing_keys:
        issues.append(f"Missing keys found in real projects: {missing_keys}")
    if extra_keys:
        issues.append(f"Extra keys not found in real projects: {extra_keys}")

    if issues:
        return False, "; ".join(issues)

    return True, f"Structure matches {len(real_project_files)} real projects"


def main():
    """Main validation routine."""
    if len(sys.argv) > 1:
        fixture_path = Path(sys.argv[1])
    else:
        fixture_path = Path("features/fixtures/kicad_templates")

    if not fixture_path.exists():
        print(f"Error: Fixture path not found: {fixture_path}")
        return 1

    validator = KiCadValidator()
    all_passed = True

    print("🔍 KiCad Fixture Validation Report")
    print("=" * 50)

    # Validate each fixture directory
    if fixture_path.is_dir():
        for fixture_dir in fixture_path.iterdir():
            if fixture_dir.is_dir():
                print(f"\n📁 Validating fixture: {fixture_dir.name}")
                print("-" * 30)

                results = validator.validate_fixture_directory(fixture_dir)

                # Display results
                for file_type in ["project", "schematic", "pcb"]:
                    for file_path, success, message in results[file_type]:
                        status = "✅" if success else "❌"
                        print(f"{status} {file_type.upper()}: {Path(file_path).name}")
                        if not success:
                            print(f"   └─ {message}")
                            all_passed = False

                # Compare with real projects for structural authenticity
                project_files = list(fixture_dir.glob("*.kicad_pro"))
                if project_files:
                    real_projects_dir = Path("/Users/jplocher/Dropbox/KiCad/projects")
                    success, message = compare_with_real_projects(
                        project_files[0], real_projects_dir
                    )
                    status = "✅" if success else "❌"
                    print(f"{status} AUTHENTICITY: {message}")
                    if not success:
                        all_passed = False

                # Summary for this fixture
                summary = results["summary"]
                print(f"\n📊 Summary: {summary['passed']}/{summary['total']} passed")

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All fixture validations PASSED!")
        print("✓ Fixtures are authentic KiCad files")
        print("✓ Structure matches real KiCad projects")
        print("✓ KiCad CLI tools accept our test files")
        return 0
    else:
        print("❌ Some fixture validations FAILED!")
        print("⚠️  Review errors above - fixtures may not be authentic")
        return 1


if __name__ == "__main__":
    sys.exit(main())
