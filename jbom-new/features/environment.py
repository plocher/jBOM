"""Behave environment configuration for jBOM testing.

Hard rule: tests must NEVER write into the repo working tree. Every scenario runs in
an isolated temp workspace and all fixture copying targets that sandbox.
"""

import os
import sys
import tempfile
from pathlib import Path


def before_all(context):
    """Set up test environment before all tests."""
    # Repository root (…/jBOM) and jbom-new root (…/jBOM/jbom-new)
    repo_root = Path(__file__).resolve().parents[2]
    jbom_new_root = Path(__file__).resolve().parents[1]

    context.repo_root = repo_root
    context.jbom_new_root = jbom_new_root
    context.src_root = jbom_new_root / "src"

    # Set BEHAVE_STEPS_DIR so plugin features can find core step definitions
    steps_dir = Path(__file__).parent / "steps"
    os.environ["BEHAVE_STEPS_DIR"] = str(steps_dir)

    # Add src to Python path so we can import jbom
    sys.path.insert(0, str(context.src_root))

    # Enable KiCad validation hooks for seamless integration
    try:
        from features.steps.kicad_project_validation_hook import enhance_jbom_steps

        enhance_jbom_steps()
    except ImportError:
        pass  # Validation hooks not available, tests continue without validation


def before_scenario(context, scenario):
    """Set up an isolated temp workspace before each scenario."""
    # Reset command output storage
    context.last_command = None
    context.last_output = None
    context.last_exit_code = None
    context.diagnostics = None

    # Optional trace via tag @trace or env JBOM_BEHAVE_TRACE=1
    import os as _os

    context.trace = ("trace" in getattr(scenario, "effective_tags", set())) or (
        _os.environ.get("JBOM_BEHAVE_TRACE") == "1"
    )

    # Create per-scenario sandbox
    tmp = Path(tempfile.mkdtemp(prefix="jbom_behave_"))
    context.sandbox_root = tmp
    context.project_root = tmp


def after_scenario(context, scenario):
    """Clean up the per-scenario temp workspace."""
    import shutil

    # Only clean up if it's a temp directory we created
    if getattr(context, "project_root", None):
        project_root = Path(context.project_root)
        if project_root.exists() and project_root.name.startswith("jbom_behave_"):
            try:
                shutil.rmtree(project_root)
            except OSError:
                pass  # Ignore cleanup errors

    # Clean up any created plugins
    for plugin_dir in getattr(context, "created_plugins", []):
        if plugin_dir.exists():
            try:
                shutil.rmtree(plugin_dir)
            except OSError:
                pass
