"""
Behave environment configuration for jBOM functional tests.

This module handles test setup, teardown, and environment configuration
for BDD scenarios testing jBOM behaviors.
"""

import os
import tempfile
import shutil
from pathlib import Path


def before_all(context):
    """Set up global test environment before all scenarios."""
    # Set up paths
    context.project_root = Path(__file__).parent.parent
    context.examples_dir = context.project_root / "examples"

    # Create temporary directory for test outputs
    context.temp_dir = Path(tempfile.mkdtemp(prefix="jbom_functional_"))
    context.test_output_dir = context.temp_dir / "outputs"
    context.test_output_dir.mkdir(exist_ok=True)

    # Store original working directory
    context.original_cwd = Path.cwd()

    print("Functional test environment:")
    print(f"  Project root: {context.project_root}")
    print(f"  Examples dir: {context.examples_dir}")
    print(f"  Temp dir: {context.temp_dir}")


def before_scenario(context, scenario):
    """Set up environment before each scenario."""
    # Create scenario-specific temporary directory
    scenario_name = scenario.name.replace(" ", "_").replace("/", "_")
    context.scenario_temp_dir = context.temp_dir / f"scenario_{scenario_name}"
    context.scenario_temp_dir.mkdir(exist_ok=True)

    # Change to scenario directory
    os.chdir(context.scenario_temp_dir)

    # Initialize scenario state
    context.last_command_output = None
    context.last_command_error = None
    context.last_command_exit_code = None
    context.generated_files = []


def after_scenario(context, scenario):
    """Clean up after each scenario."""
    # Return to original directory
    os.chdir(context.original_cwd)

    # Clean up scenario files if test passed
    if scenario.status == "passed" and hasattr(context, "scenario_temp_dir"):
        shutil.rmtree(context.scenario_temp_dir, ignore_errors=True)


def after_all(context):
    """Clean up global test environment after all scenarios."""
    # Return to original directory
    os.chdir(context.original_cwd)

    # Clean up temporary directory
    if hasattr(context, "temp_dir"):
        shutil.rmtree(context.temp_dir, ignore_errors=True)

    print("Cleaned up functional test environment")
