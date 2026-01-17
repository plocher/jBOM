"""Behave environment configuration for jBOM testing."""

import sys
from pathlib import Path


def before_all(context):
    """Set up test environment before all tests."""
    # Store the project root
    context.project_root = Path(__file__).parent.parent
    context.src_root = context.project_root / "src"

    # Add src to Python path so we can import jbom_new
    sys.path.insert(0, str(context.src_root))


def before_scenario(context, scenario):
    """Set up before each scenario."""
    # Reset command output storage
    context.last_command = None
    context.last_output = None
    context.last_exit_code = None


def after_scenario(context, scenario):
    """Clean up after each scenario."""
    # Clean up any created plugins
    if hasattr(context, "created_plugins"):
        import shutil

        for plugin_dir in context.created_plugins:
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
