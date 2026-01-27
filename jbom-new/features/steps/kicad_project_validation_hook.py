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

    validation_errors = []

    # Validate project structure
    for pro_file in project_dir.glob("*.kicad_pro"):
        success, message = _validate_project_structure(pro_file)
        if not success:
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

        if (
            not success and stderr
        ):  # Only report if there's an actual error, not just violations
            validation_errors.append(
                f"Schematic {sch_file.name}: KiCad ERC error - {stderr[:100]}"
            )

    # Validate PCBs with DRC (but be more tolerant since empty PCBs might have issues)
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

        if not success and stderr:  # Only report parsing errors, not design violations
            validation_errors.append(
                f"PCB {pcb_file.name}: KiCad DRC error - {stderr[:100]}"
            )

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
        raise AssertionError(
            f"KiCad project validation failed before running jBOM command '{command_args}':\n"
            f"{error_message}\n\n"
            f"This ensures jBOM receives authentic KiCad files, not fake test content.\n"
            f"To disable validation: unset JBOM_VALIDATE_KICAD environment variable.\n"
            f"To fix: ensure project files are authentic KiCad-generated content."
        )


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
