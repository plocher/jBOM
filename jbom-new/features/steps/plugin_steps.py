"""Step definitions for plugin-related tests."""

import json

from behave import given


@given("no plugins have been installed")
def step_no_plugins(context):
    """Ensure plugins directory is empty."""
    plugins_dir = context.src_root / "jbom" / "plugins"

    # Store the current state so we can verify it's empty
    if plugins_dir.exists():
        # Check that only __pycache__ or similar might exist
        real_plugins = [
            p
            for p in plugins_dir.iterdir()
            if p.name != "__pycache__" and not p.name.startswith(".")
        ]
        context.plugin_count = len(real_plugins)
    else:
        context.plugin_count = 0


@given('a core plugin "{plugin_name}" exists with version "{version}"')
def step_plugin_exists(context, plugin_name, version):
    """Create a minimal plugin directory structure for testing."""
    plugins_dir = context.src_root / "jbom" / "plugins"
    plugin_dir = plugins_dir / plugin_name

    # Create plugin directory
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py with version
    init_file = plugin_dir / "__init__.py"
    init_file.write_text(f'"""Plugin: {plugin_name}"""\n\n__version__ = "{version}"\n')

    # Create plugin.json metadata
    metadata = {
        "name": plugin_name,
        "version": version,
        "description": f"Test plugin {plugin_name}",
    }
    metadata_file = plugin_dir / "plugin.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))

    # Track created plugins for cleanup
    if not hasattr(context, "created_plugins"):
        context.created_plugins = []
    context.created_plugins.append(plugin_dir)


def after_scenario(context, scenario):
    """Clean up any created plugins after scenario."""
    if hasattr(context, "created_plugins"):
        import shutil

        for plugin_dir in context.created_plugins:
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
