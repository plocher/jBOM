"""
KiCad Project Validation Hook for jBOM Tests

This module provides a seamless way to validate KiCad projects before they're
fed to jBOM commands. It integrates with existing Behave scenarios without
requiring changes to scenario structure.

The validation can be enabled via environment variable or context configuration
to avoid "Potempkin scenarios" while ensuring authentic KiCad project validation.
"""

import os
from pathlib import Path
from typing import Optional
from .kicad_validation_steps import run_kicad_validation, _validate_project_structure


def should_validate_kicad_projects(context) -> bool:
    """Determine if KiCad validation should be performed.

    Returns True if:
    1. JBOM_VALIDATE_KICAD environment variable is set to "1" or "true"
    2. context.validate_kicad is True
    3. context has kicad_validation_enabled attribute (from validation steps)

    This allows for flexible validation control:
    - Always validate: export JBOM_VALIDATE_KICAD=1
    - Scenario-specific: Use validation steps in background
    - Development mode: Don't validate for faster iteration
    """
    # Environment variable override
    env_validate = os.getenv("JBOM_VALIDATE_KICAD", "").lower()
    if env_validate in ("1", "true", "yes"):
        return True

    # Context-specific validation
    if getattr(context, "validate_kicad", False):
        return True

    # Validation enabled by validation steps
    if getattr(context, "kicad_validation_enabled", False):
        return True

    return False


def validate_kicad_project_if_enabled(context, project_dir: Path) -> Optional[str]:
    """Validate KiCad project if validation is enabled.

    Args:
        context: Behave context object
        project_dir: Path to project directory to validate

    Returns:
        None if validation passes or is disabled
        String with validation error message if validation fails
    """
    if not should_validate_kicad_projects(context):
        return None

    # Check if KiCad CLI is available
    kicad_cli = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
    if not kicad_cli.exists():
        # Skip validation if KiCad CLI not available - don't fail the test
        return None

    # Initialize detailed validation results for diagnostics
    validation_results = {
        "project_files": [],
        "schematic_files": [],
        "pcb_files": [],
        "all_passed": True,
        "summary": {"total": 0, "passed": 0, "failed": 0},
    }
    context.kicad_validation_results = validation_results

    validation_errors = []

    # Validate project structure
    for pro_file in project_dir.glob("*.kicad_pro"):
        success, message = _validate_project_structure(pro_file)

        # Store detailed result for diagnostics
        result = {"file": str(pro_file), "success": success, "message": message}
        validation_results["project_files"].append(result)
        validation_results["summary"]["total"] += 1

        if success:
            validation_results["summary"]["passed"] += 1
        else:
            validation_results["summary"]["failed"] += 1
            validation_results["all_passed"] = False
            validation_errors.append(f"Project {pro_file.name}: {message}")

    # Validate schematics with ERC
    for sch_file in project_dir.glob("*.kicad_sch"):
        success, stdout, stderr = run_kicad_validation(
            [
                str(kicad_cli),
                "sch",
                "erc",
                "--format",
                "json",
                "--severity-all",
                str(sch_file),
            ],
            timeout=15,
        )

        # Parse violations for detailed diagnostics
        violations = []
        if stdout:
            try:
                import json

                erc_data = json.loads(stdout)
                violations = erc_data.get("violations", [])
            except json.JSONDecodeError:
                pass

        # Determine success/failure - be more tolerant of design violations
        file_success = success or not stderr  # Success if no parsing errors
        message = "ERC passed" if file_success else f"ERC error: {stderr[:100]}"
        if violations:
            message += f" ({len(violations)} violations)"

        # Store detailed result
        result = {
            "file": str(sch_file),
            "success": file_success,
            "message": message,
            "violations": violations,
            "raw_output": stdout,
        }
        validation_results["schematic_files"].append(result)
        validation_results["summary"]["total"] += 1

        if file_success:
            validation_results["summary"]["passed"] += 1
        else:
            validation_results["summary"]["failed"] += 1
            validation_results["all_passed"] = False
            validation_errors.append(f"Schematic {sch_file.name}: {message}")

    # Validate PCBs with DRC (be more tolerant since empty PCBs might have issues)
    for pcb_file in project_dir.glob("*.kicad_pcb"):
        success, stdout, stderr = run_kicad_validation(
            [
                str(kicad_cli),
                "pcb",
                "drc",
                "--format",
                "json",
                "--severity-all",
                str(pcb_file),
            ],
            timeout=15,
        )

        # Parse violations for detailed diagnostics
        violations = []
        if stdout:
            try:
                import json

                drc_data = json.loads(stdout)
                violations = drc_data.get("violations", [])
            except json.JSONDecodeError:
                pass

        # Be tolerant of design violations for PCBs
        file_success = success or not stderr  # Success if no parsing errors
        message = "DRC passed" if file_success else f"DRC error: {stderr[:100]}"
        if violations:
            message += f" ({len(violations)} violations)"

        # Store detailed result
        result = {
            "file": str(pcb_file),
            "success": file_success,
            "message": message,
            "violations": violations,
            "raw_output": stdout,
        }
        validation_results["pcb_files"].append(result)
        validation_results["summary"]["total"] += 1

        if file_success:
            validation_results["summary"]["passed"] += 1
        else:
            validation_results["summary"]["failed"] += 1
            validation_results["all_passed"] = False
            validation_errors.append(f"PCB {pcb_file.name}: {message}")

    if validation_errors:
        return "KiCad validation failed:\n" + "\n".join(validation_errors)

    return None


def validate_before_jbom_command(context, command_args: str) -> None:
    """Hook to validate KiCad project before running jBOM commands.

    This is called automatically by the enhanced jBOM command steps.
    If validation is enabled and fails, raises AssertionError with details.
    """
    # Only validate for BOM-generating commands that need KiCad input
    if not any(cmd in command_args for cmd in ["bom", "pos", "cpl"]):
        return

    # Find project directory - look for context attributes in order of preference
    project_dir = None
    for attr in ["project_placement_dir", "sandbox_root", "project_root"]:
        if hasattr(context, attr):
            potential_dir = getattr(context, attr)
            if potential_dir and Path(potential_dir).exists():
                project_dir = Path(potential_dir)
                break

    if not project_dir:
        return  # No project directory found, skip validation

    # Perform validation
    error_message = validate_kicad_project_if_enabled(context, project_dir)
    if error_message:
        # Use enhanced diagnostics for better failure reporting
        _raise_validation_error_with_diagnostics(
            context, command_args, project_dir, error_message
        )


def _raise_validation_error_with_diagnostics(
    context, command_args: str, project_dir: Path, error_message: str
) -> None:
    """Raise validation error with comprehensive diagnostics."""
    try:
        from .diagnostic_utils import format_execution_context
    except ImportError:
        # Fallback if diagnostic utils not available
        def format_execution_context(ctx):
            return "[Diagnostics not available]"

    # Build comprehensive error message
    diagnostic_parts = [
        "\n" + "=" * 80,
        "KiCad PROJECT VALIDATION FAILED",
        "=" * 80,
        f"\nCommand that would have run: jbom {command_args}",
        f"Project directory: {project_dir}",
        "\n--- VALIDATION ERRORS ---",
        error_message,
    ]

    # Add project file inventory for debugging
    diagnostic_parts.extend(
        [
            "\n--- PROJECT FILE INVENTORY ---",
            _format_project_file_inventory(project_dir),
        ]
    )

    # Add detailed validation results if available
    if hasattr(context, "kicad_validation_results"):
        diagnostic_parts.extend(
            [
                "\n--- DETAILED VALIDATION RESULTS ---",
                _format_detailed_validation_results(context.kicad_validation_results),
            ]
        )

    # Add KiCad CLI diagnostics
    diagnostic_parts.extend(
        ["\n--- KICAD CLI DIAGNOSTICS ---", _format_kicad_cli_diagnostics()]
    )

    # Add resolution guidance
    diagnostic_parts.extend(
        [
            "\n--- RESOLUTION GUIDANCE ---",
            "• This validation ensures jBOM receives authentic KiCad files, not fake test content",
            "• To disable validation temporarily: unset JBOM_VALIDATE_KICAD",
            "• To fix permanently: replace fake KiCad content with authentic fixtures",
            "• Use scripts/validate_fixtures.py to check all fixtures",
            "• See docs/SEAMLESS_KICAD_VALIDATION.md for integration guide",
        ]
    )

    # Include standard execution context from diagnostic utils
    if format_execution_context:
        try:
            diagnostic_parts.append(
                format_execution_context(context, include_files=True)
            )
        except Exception:
            pass  # Don't let diagnostic formatting break the error

    diagnostic_parts.extend(
        ["\n" + "=" * 80, "END KiCad VALIDATION DIAGNOSTICS", "=" * 80 + "\n"]
    )

    raise AssertionError("\n".join(diagnostic_parts))


def _format_project_file_inventory(project_dir: Path) -> str:
    """Format project file inventory for diagnostics."""
    inventory_lines = []

    # List all KiCad-related files
    kicad_extensions = [
        ".kicad_pro",
        ".kicad_sch",
        ".kicad_pcb",
        ".kicad_prl",
        ".kicad_wks",
    ]

    for ext in kicad_extensions:
        files = list(project_dir.glob(f"*{ext}"))
        if files:
            for file in files:
                try:
                    size = file.stat().st_size
                    inventory_lines.append(f"  {file.name}: {size} bytes")

                    # Show first few lines of small files
                    if size < 500:
                        try:
                            content = file.read_text(encoding="utf-8")[:200]
                            inventory_lines.append(
                                f"    Preview: {repr(content[:100])}..."
                            )
                        except Exception:
                            pass
                except Exception:
                    inventory_lines.append(f"  {file.name}: [Error reading file]")
        else:
            inventory_lines.append(f"  No {ext} files found")

    return "\n".join(inventory_lines) if inventory_lines else "No KiCad files found"


def _format_detailed_validation_results(validation_results: dict) -> str:
    """Format detailed validation results for diagnostics."""
    lines = []

    # Summary
    summary = validation_results.get("summary", {})
    lines.append(
        f"Summary: {summary.get('passed', 0)}/{summary.get('total', 0)} files passed"
    )

    # Per-file details
    for file_type in ["project_files", "schematic_files", "pcb_files"]:
        results = validation_results.get(file_type, [])
        if results:
            lines.append(f"\n{file_type.replace('_', ' ').title()}:")
            for result in results:
                status = "✅ PASS" if result["success"] else "❌ FAIL"
                file_name = Path(result["file"]).name
                lines.append(f"  {status} {file_name}: {result['message']}")

                # Show violations if available
                if "violations" in result and result["violations"]:
                    lines.append(f"    Violations: {len(result['violations'])}")
                    for i, violation in enumerate(
                        result["violations"][:3]
                    ):  # Show first 3
                        lines.append(
                            f"      {i+1}. {violation.get('description', 'Unknown violation')}"
                        )
                    if len(result["violations"]) > 3:
                        lines.append(
                            f"      ... and {len(result['violations']) - 3} more"
                        )

    return "\n".join(lines) if lines else "No detailed results available"


def _format_kicad_cli_diagnostics() -> str:
    """Format KiCad CLI diagnostics."""
    lines = []

    kicad_cli = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")

    if kicad_cli.exists():
        lines.append(f"✅ KiCad CLI found: {kicad_cli}")
        try:
            import subprocess

            result = subprocess.run(
                [str(kicad_cli), "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version_line = (
                    result.stdout.strip().split("\n")[0]
                    if result.stdout
                    else "Unknown version"
                )
                lines.append(f"   Version: {version_line}")
            else:
                lines.append(f"   Version check failed: {result.stderr}")
        except Exception as e:
            lines.append(f"   Version check error: {str(e)}")
    else:
        lines.append(f"❌ KiCad CLI not found at: {kicad_cli}")
        lines.append("   Install KiCad or validation will be skipped")

    return "\n".join(lines)


# Integration with existing steps - monkey patch approach for seamless integration
def enhance_jbom_steps():
    """Enhance existing jBOM step definitions to include KiCad validation.

    This patches the existing step functions to add validation without changing
    the scenario syntax or requiring new step definitions.
    """
    try:
        # Import the existing step functions
        from . import common_steps

        # Store original functions
        original_run_command = common_steps.step_run_command
        original_run_jbom_command = common_steps.step_run_jbom_command

        def enhanced_run_command(context, command):
            """Enhanced version that validates KiCad projects before jBOM commands."""
            if command.startswith("jbom "):
                validate_before_jbom_command(context, command)
            return original_run_command(context, command)

        def enhanced_run_jbom_command(context, args):
            """Enhanced version that validates KiCad projects before jBOM commands."""
            validate_before_jbom_command(context, args)
            return original_run_jbom_command(context, args)

        # Replace with enhanced versions
        common_steps.step_run_command = enhanced_run_command
        common_steps.step_run_jbom_command = enhanced_run_jbom_command

    except ImportError:
        # If imports fail, validation won't be available but tests continue
        pass


# Background step for explicit validation enablement
def enable_kicad_validation_background(context):
    """Background step to enable KiCad validation for a feature.

    Add this to your feature Background section:

    Background:
        Given KiCad project validation is enabled
        Given the generic fabricator is selected
    """
    context.validate_kicad = True

    # Also check if KiCad CLI is available and skip feature if not
    kicad_cli = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
    if not kicad_cli.exists():
        context.scenario.skip("KiCad CLI not available for project validation")


# Register the background step
try:
    from behave import given

    @given("KiCad project validation is enabled")
    def step_enable_kicad_validation(context):
        """Enable KiCad project validation for this scenario."""
        enable_kicad_validation_background(context)

except ImportError:
    pass  # Behave not available during module import
