"""
KiCad validation steps for Behave scenarios.

These steps use KiCad's native CLI tools to validate that test artifacts are
authentic KiCad files before feeding them to jBOM. This prevents circular
test patterns and ensures we're testing against real KiCad behavior.

Usage in scenarios:
    When I validate the KiCad project with native tools
    Then KiCad should accept all project files
    And KiCad ERC should validate the schematic
    And KiCad DRC should validate the PCB
"""

import json
import subprocess
from pathlib import Path
from behave import given, when, then
from typing import List, Tuple


KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


class KiCadValidationError(Exception):
    """Raised when KiCad validation fails."""

    pass


def run_kicad_validation(
    command: List[str], timeout: int = 30
) -> Tuple[bool, str, str]:
    """Run KiCad CLI command and return success, stdout, stderr."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"KiCad command timed out: {' '.join(command)}"
    except FileNotFoundError:
        return False, "", f"KiCad CLI not found at {KICAD_CLI}"
    except Exception as e:
        return False, "", f"KiCad validation error: {str(e)}"


@when("I validate the KiCad project with native tools")
def when_validate_kicad_project(context):
    """Validate the current project using KiCad's native CLI tools.

    This step discovers all KiCad files in the current project and validates
    them using the appropriate KiCad CLI tools (ERC for schematics, DRC for PCBs).
    Results are stored in context for later assertion steps.
    """
    if (
        not hasattr(context, "project_placement_dir")
        or not context.project_placement_dir
    ):
        raise KiCadValidationError(
            "No project directory set. Use 'Given a KiCad project' first."
        )

    project_dir = Path(context.project_placement_dir)
    if not project_dir.exists():
        raise KiCadValidationError(f"Project directory not found: {project_dir}")

    # Initialize validation results
    context.kicad_validation_results = {
        "project_files": [],
        "schematic_files": [],
        "pcb_files": [],
        "all_passed": True,
        "summary": {"total": 0, "passed": 0, "failed": 0},
    }

    # Validate project files (.kicad_pro)
    for pro_file in project_dir.glob("*.kicad_pro"):
        success, message = _validate_project_structure(pro_file)
        context.kicad_validation_results["project_files"].append(
            {"file": str(pro_file), "success": success, "message": message}
        )
        context.kicad_validation_results["summary"]["total"] += 1
        if success:
            context.kicad_validation_results["summary"]["passed"] += 1
        else:
            context.kicad_validation_results["summary"]["failed"] += 1
            context.kicad_validation_results["all_passed"] = False

    # Validate schematic files (.kicad_sch)
    for sch_file in project_dir.glob("*.kicad_sch"):
        success, stdout, stderr = run_kicad_validation(
            [
                KICAD_CLI,
                "sch",
                "erc",
                "--format",
                "json",
                "--severity-all",
                str(sch_file),
            ]
        )

        # Parse ERC results for detailed reporting
        violations = []
        if stdout:
            try:
                erc_data = json.loads(stdout)
                violations = erc_data.get("violations", [])
            except json.JSONDecodeError:
                pass

        message = (
            "ERC passed" if success else f"ERC failed: {len(violations)} violations"
        )
        if stderr:
            message += f" (stderr: {stderr[:100]}...)"

        context.kicad_validation_results["schematic_files"].append(
            {
                "file": str(sch_file),
                "success": success,
                "message": message,
                "violations": violations,
                "raw_output": stdout,
            }
        )
        context.kicad_validation_results["summary"]["total"] += 1
        if success:
            context.kicad_validation_results["summary"]["passed"] += 1
        else:
            context.kicad_validation_results["summary"]["failed"] += 1
            context.kicad_validation_results["all_passed"] = False

    # Validate PCB files (.kicad_pcb)
    for pcb_file in project_dir.glob("*.kicad_pcb"):
        success, stdout, stderr = run_kicad_validation(
            [
                KICAD_CLI,
                "pcb",
                "drc",
                "--format",
                "json",
                "--severity-all",
                str(pcb_file),
            ]
        )

        # Parse DRC results
        violations = []
        if stdout:
            try:
                drc_data = json.loads(stdout)
                violations = drc_data.get("violations", [])
            except json.JSONDecodeError:
                pass

        message = (
            "DRC passed" if success else f"DRC failed: {len(violations)} violations"
        )
        if stderr:
            message += f" (stderr: {stderr[:100]}...)"

        context.kicad_validation_results["pcb_files"].append(
            {
                "file": str(pcb_file),
                "success": success,
                "message": message,
                "violations": violations,
                "raw_output": stdout,
            }
        )
        context.kicad_validation_results["summary"]["total"] += 1
        if success:
            context.kicad_validation_results["summary"]["passed"] += 1
        else:
            context.kicad_validation_results["summary"]["failed"] += 1
            context.kicad_validation_results["all_passed"] = False


def _validate_project_structure(project_file: Path) -> Tuple[bool, str]:
    """Validate KiCad project file structure."""
    try:
        with open(project_file) as f:
            data = json.load(f)

        # Required keys for authentic KiCad projects
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

        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            return False, f"Missing required keys: {missing_keys}"

        # Validate meta section
        meta = data.get("meta", {})
        if not isinstance(meta.get("version"), int):
            return False, f"Invalid version: {meta.get('version')}"

        # Check filename consistency
        if meta.get("filename") != project_file.name:
            return (
                False,
                f"Filename mismatch: {meta.get('filename')} vs {project_file.name}",
            )

        return True, "Project structure valid"

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


@then("KiCad should accept all project files")
def then_kicad_accepts_all_files(context):
    """Assert that all KiCad files passed native validation."""
    if not hasattr(context, "kicad_validation_results"):
        raise KiCadValidationError(
            "No validation results found. Run validation step first."
        )

    results = context.kicad_validation_results
    summary = results["summary"]

    if not results["all_passed"]:
        failure_details = []

        # Collect failure details for reporting
        for file_type in ["project_files", "schematic_files", "pcb_files"]:
            for file_result in results[file_type]:
                if not file_result["success"]:
                    failure_details.append(
                        f"{Path(file_result['file']).name}: {file_result['message']}"
                    )

        raise AssertionError(
            f"KiCad validation failed for {summary['failed']}/{summary['total']} files:\n"
            + "\n".join(failure_details)
        )


@then("KiCad ERC should validate the schematic")
def then_kicad_erc_validates(context):
    """Assert that schematic files pass KiCad ERC validation."""
    if not hasattr(context, "kicad_validation_results"):
        raise KiCadValidationError(
            "No validation results found. Run validation step first."
        )

    schematic_results = context.kicad_validation_results["schematic_files"]

    if not schematic_results:
        raise AssertionError("No schematic files found for ERC validation")

    failed_schematics = [r for r in schematic_results if not r["success"]]

    if failed_schematics:
        failure_details = [
            f"{Path(r['file']).name}: {r['message']}" for r in failed_schematics
        ]
        raise AssertionError(
            f"KiCad ERC failed for {len(failed_schematics)} schematic(s):\n"
            + "\n".join(failure_details)
        )


@then("KiCad DRC should validate the PCB")
def then_kicad_drc_validates(context):
    """Assert that PCB files pass KiCad DRC validation."""
    if not hasattr(context, "kicad_validation_results"):
        raise KiCadValidationError(
            "No validation results found. Run validation step first."
        )

    pcb_results = context.kicad_validation_results["pcb_files"]

    if not pcb_results:
        raise AssertionError("No PCB files found for DRC validation")

    failed_pcbs = [r for r in pcb_results if not r["success"]]

    if failed_pcbs:
        failure_details = [
            f"{Path(r['file']).name}: {r['message']}" for r in failed_pcbs
        ]
        raise AssertionError(
            f"KiCad DRC failed for {len(failed_pcbs)} PCB(s):\n"
            + "\n".join(failure_details)
        )


@then("KiCad should report {expected_violations:d} or fewer violations")
def then_kicad_reports_few_violations(context, expected_violations: int):
    """Assert that KiCad validation finds few or no violations.

    This is useful for testing that our fixtures are reasonably well-formed,
    even if they have some expected violations (like unconnected pins in test circuits).
    """
    if not hasattr(context, "kicad_validation_results"):
        raise KiCadValidationError(
            "No validation results found. Run validation step first."
        )

    results = context.kicad_validation_results
    total_violations = 0

    # Count violations from ERC and DRC
    for file_result in results["schematic_files"] + results["pcb_files"]:
        violations = file_result.get("violations", [])
        total_violations += len(violations)

    if total_violations > expected_violations:
        raise AssertionError(
            f"KiCad found {total_violations} violations, expected {expected_violations} or fewer"
        )


@given("KiCad validation is enabled for this scenario")
def given_kicad_validation_enabled(context):
    """Enable KiCad validation for this scenario.

    This step ensures KiCad CLI is available and sets up validation context.
    Use this at the beginning of scenarios that need authentic KiCad validation.
    """
    kicad_cli = Path(KICAD_CLI)
    if not kicad_cli.exists():
        context.scenario.skip("KiCad CLI not available for validation")
        return

    # Test that KiCad CLI is working
    try:
        result = subprocess.run(
            [str(kicad_cli), "--help"], capture_output=True, timeout=10
        )
        if result.returncode != 0:
            context.scenario.skip("KiCad CLI not functioning properly")
            return
    except Exception:
        context.scenario.skip("KiCad CLI test failed")
        return

    context.kicad_validation_enabled = True


@when("I validate the project structure against real KiCad projects")
def when_validate_against_real_projects(context):
    """Validate that our test project structure matches real KiCad projects."""
    if not hasattr(context, "project_placement_dir"):
        raise KiCadValidationError("No project directory set")

    project_dir = Path(context.project_placement_dir)
    project_files = list(project_dir.glob("*.kicad_pro"))

    if not project_files:
        raise KiCadValidationError("No project files found for structure validation")

    # Compare with real projects
    real_projects_dir = Path("/Users/jplocher/Dropbox/KiCad/projects")
    real_project_files = list(real_projects_dir.glob("**/*.kicad_pro"))[:3]

    if not real_project_files:
        raise KiCadValidationError("No real KiCad projects available for comparison")

    # Get structure from real projects
    common_keys = None
    for real_project in real_project_files:
        try:
            with open(real_project) as f:
                real_data = json.load(f)
            real_keys = set(real_data.keys())

            if common_keys is None:
                common_keys = real_keys
            else:
                common_keys &= real_keys
        except Exception:
            continue

    if common_keys is None:
        raise KiCadValidationError("Could not analyze real projects for comparison")

    # Validate our project against real structure
    context.structure_validation_results = []

    for project_file in project_files:
        try:
            with open(project_file) as f:
                test_data = json.load(f)
            test_keys = set(test_data.keys())

            missing_keys = common_keys - test_keys
            success = len(missing_keys) == 0
            message = (
                "Structure matches real projects"
                if success
                else f"Missing keys: {missing_keys}"
            )

            context.structure_validation_results.append(
                {
                    "file": str(project_file),
                    "success": success,
                    "message": message,
                    "missing_keys": missing_keys,
                }
            )

        except Exception as e:
            context.structure_validation_results.append(
                {
                    "file": str(project_file),
                    "success": False,
                    "message": f"Validation error: {str(e)}",
                    "missing_keys": set(),
                }
            )


@then("the project structure should match real KiCad projects")
def then_structure_matches_real_projects(context):
    """Assert that project structure matches real KiCad projects."""
    if not hasattr(context, "structure_validation_results"):
        raise AssertionError("No structure validation results found")

    failed_validations = [
        r for r in context.structure_validation_results if not r["success"]
    ]

    if failed_validations:
        failure_details = [
            f"{Path(r['file']).name}: {r['message']}" for r in failed_validations
        ]
        raise AssertionError(
            "Project structure validation failed:\n" + "\n".join(failure_details)
        )


# Utility step for development/debugging
@when("I debug KiCad validation results")
def when_debug_validation_results(context):
    """Print detailed validation results for debugging."""
    if hasattr(context, "kicad_validation_results"):
        results = context.kicad_validation_results
        print("\n=== KiCad Validation Results ===")
        print(f"Summary: {results['summary']}")

        for file_type in ["project_files", "schematic_files", "pcb_files"]:
            if results[file_type]:
                print(f"\n{file_type.upper()}:")
                for file_result in results[file_type]:
                    status = "✅" if file_result["success"] else "❌"
                    print(
                        f"  {status} {Path(file_result['file']).name}: {file_result['message']}"
                    )
    else:
        print("No KiCad validation results available")
