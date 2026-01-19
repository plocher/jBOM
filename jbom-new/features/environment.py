"""Behave environment configuration for jBOM testing."""

import os
import sys
from pathlib import Path


def before_all(context):
    """Set up test environment before all tests."""
    # Store the project root
    context.project_root = Path(__file__).parent.parent
    context.src_root = context.project_root / "src"

    # Set BEHAVE_STEPS_DIR so plugin features can find core step definitions
    steps_dir = Path(__file__).parent / "steps"
    os.environ["BEHAVE_STEPS_DIR"] = str(steps_dir)

    # Add src to Python path so we can import jbom
    sys.path.insert(0, str(context.src_root))


def before_scenario(context, scenario):
    """Set up before each scenario."""
    # Reset command output storage
    context.last_command = None
    context.last_output = None
    context.last_exit_code = None


def after_scenario(context, scenario):
    """Clean up after each scenario."""
    import shutil

    # Clean up temporary test workspace if it was created
    if hasattr(context, "project_root"):
        # Only clean up if it's a temp directory (contains "jbom_behave_")
        project_root_str = str(context.project_root)
        if "jbom_behave_" in project_root_str and context.project_root.exists():
            try:
                shutil.rmtree(context.project_root)
            except OSError:
                pass  # Ignore cleanup errors

    # Clean up any created plugins
    if hasattr(context, "created_plugins"):
        for plugin_dir in context.created_plugins:
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
