"""
Behave environment configuration for jBOM functional tests.

This module handles test setup, teardown, and environment configuration
for BDD scenarios testing jBOM behaviors.
"""

import os
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any


def before_all(context):
    """Set up global test environment before all scenarios."""
    # Set up paths
    context.project_root = Path(__file__).parent.parent
    context.examples_dir = context.project_root / "examples"
    
    # Add steps directory to Python path for diagnostic_utils imports
    steps_dir = Path(__file__).parent / "steps"
    if str(steps_dir) not in sys.path:
        sys.path.insert(0, str(steps_dir))

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

    # Add context methods for BDD testing
    _add_context_methods(context)


def after_scenario(context, scenario):
    """Clean up after each scenario."""
    # Return to original directory
    os.chdir(context.original_cwd)

    # Clean up scenario files if test passed
    if scenario.status == "passed" and hasattr(context, "scenario_temp_dir"):
        _cleanup_temp_dir(context.scenario_temp_dir)


def after_all(context):
    """Clean up global test environment after all scenarios."""
    # Return to original directory
    os.chdir(context.original_cwd)

    # Clean up temporary directory
    if hasattr(context, "temp_dir"):
        _cleanup_temp_dir(context.temp_dir)

    print("Cleaned up functional test environment")


def _cleanup_temp_dir(temp_dir_path):
    """Clean up temporary directory, handling read-only directories properly.

    Args:
        temp_dir_path: Path to temporary directory to clean up
    """
    if not temp_dir_path or not temp_dir_path.exists():
        return

    try:
        # First, make all directories and files writable
        import stat

        for root, dirs, files in os.walk(temp_dir_path, topdown=False):
            # Make files writable
            for file in files:
                file_path = Path(root) / file
                try:
                    file_path.chmod(stat.S_IWRITE | stat.S_IREAD)
                except (OSError, PermissionError):
                    pass  # Ignore errors, we'll try to delete anyway

            # Make directories writable
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    dir_path.chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
                except (OSError, PermissionError):
                    pass  # Ignore errors, we'll try to delete anyway

        # Make the root directory writable
        try:
            temp_dir_path.chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        except (OSError, PermissionError):
            pass  # Ignore errors, we'll try to delete anyway

        # Now try to remove the directory
        shutil.rmtree(temp_dir_path, ignore_errors=True)

    except Exception:
        # If all else fails, just ignore errors - temporary directories
        # will be cleaned up by the system eventually
        pass


def _add_context_methods(context):
    """Add missing context methods needed by BDD step definitions."""

    def execute_shell(command: str) -> Dict[str, Any]:
        """Execute shell command and capture results.

        Args:
            command: Shell command to execute

        Returns:
            Dict with 'exit_code', 'output', 'stderr' keys
        """
        try:
            # Add jBOM to Python path for CLI execution
            env = os.environ.copy()
            project_root = context.project_root
            if "PYTHONPATH" in env:
                env["PYTHONPATH"] = f"{project_root}/src:{env['PYTHONPATH']}"
            else:
                env["PYTHONPATH"] = f"{project_root}/src"

            # Execute command in scenario temp directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=context.scenario_temp_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=60,  # 60 second timeout for BDD tests
            )

            output_dict = {
                "exit_code": result.returncode,
                "output": result.stdout,
                "stderr": result.stderr,
            }

            # Store in context for step verification
            context.last_command_exit_code = result.returncode
            context.last_command_output = result.stdout
            context.last_command_error = result.stderr

            return output_dict

        except subprocess.TimeoutExpired:
            error_dict = {
                "exit_code": 124,  # Standard timeout exit code
                "output": "",
                "stderr": f"Command timed out after 60 seconds: {command}",
            }
            context.last_command_exit_code = 124
            context.last_command_error = error_dict["stderr"]
            return error_dict

        except Exception as e:
            error_dict = {
                "exit_code": 1,
                "output": "",
                "stderr": f"Command execution failed: {str(e)}",
            }
            context.last_command_exit_code = 1
            context.last_command_error = error_dict["stderr"]
            return error_dict

    def api_generate_bom(project=None, inventory=None, output=None, **kwargs) -> Any:
        """Execute BOM generation via Python API.

        Args:
            project: Project directory or schematic file
            inventory: Inventory file path
            output: Output file path
            **kwargs: Additional API options

        Returns:
            API result or raises exception
        """
        try:
            # Import jBOM API
            sys.path.insert(0, str(context.project_root / "src"))
            from jbom.api import generate_bom, BOMOptions

            # Set up options
            options = BOMOptions(
                **{
                    k: v
                    for k, v in kwargs.items()
                    if k in ["verbose", "debug", "smd_only", "fields", "fabricator"]
                }
            )

            # Resolve paths relative to scenario temp dir
            if project and not Path(project).is_absolute():
                project = context.scenario_temp_dir / project
            if inventory and not Path(inventory).is_absolute():
                inventory = context.scenario_temp_dir / inventory
            # Note: Don't resolve output path to preserve original format for error messages
            # The generator will handle relative paths from the current working directory

            result = generate_bom(
                input=project, inventory=inventory, output=output, options=options
            )

            # Store success state
            context.last_command_exit_code = 0
            return result

        except PermissionError as e:
            # Format permission errors consistently with CLI
            import re
            file_match = re.search(r"['\"]([^'\"]+)['\"]", str(e))
            file_path = file_match.group(1) if file_match else "unknown file"
            error_msg = (
                f"Error: Permission denied writing to: {file_path}\n"
                f"Please check that the directory is writable and you have sufficient permissions."
            )
            context.last_command_exit_code = 1
            context.last_command_error = error_msg
            raise PermissionError(error_msg) from e
        except Exception as e:
            # Store error state
            context.last_command_exit_code = 1
            context.last_command_error = str(e)
            raise e

    def api_generate_pos(project=None, output=None, **kwargs) -> Any:
        """Execute POS generation via Python API.

        Args:
            project: Project directory or PCB file
            output: Output file path
            **kwargs: Additional API options

        Returns:
            API result or raises exception
        """
        try:
            # Import jBOM API
            sys.path.insert(0, str(context.project_root / "src"))
            from jbom.api import generate_pos, POSOptions

            # Set up options
            options = POSOptions(
                **{
                    k: v
                    for k, v in kwargs.items()
                    if k
                    in [
                        "units",
                        "origin",
                        "smd_only",
                        "layer_filter",
                        "fields",
                        "fabricator",
                    ]
                }
            )

            # Resolve paths relative to scenario temp dir
            if project and not Path(project).is_absolute():
                project = context.scenario_temp_dir / project
            if output and not Path(output).is_absolute():
                output = context.scenario_temp_dir / output

            result = generate_pos(input=project, output=output, options=options)

            # Store success state
            context.last_command_exit_code = 0
            return result

        except Exception as e:
            # Store error state
            context.last_command_exit_code = 1
            context.last_command_error = str(e)
            raise e

    def api_extract_inventory(project=None, output=None, **kwargs) -> Any:
        """Execute inventory extraction via Python API.

        Args:
            project: Project directory or schematic file
            output: Output file path
            **kwargs: Additional API options

        Returns:
            API result or raises exception
        """
        try:
            # Import jBOM API
            sys.path.insert(0, str(context.project_root / "src"))
            from jbom.api import generate_enriched_inventory, InventoryOptions

            # Set up options
            options = InventoryOptions(
                **{
                    k: v
                    for k, v in kwargs.items()
                    if k
                    in [
                        "search",
                        "provider",
                        "api_key",
                        "limit",
                        "interactive",
                        "fields",
                    ]
                }
            )

            # Resolve paths relative to scenario temp dir
            if project and not Path(project).is_absolute():
                project = context.scenario_temp_dir / project
            if output and not Path(output).is_absolute():
                output = context.scenario_temp_dir / output

            result = generate_enriched_inventory(
                input=project, output=output, options=options
            )

            # Store success state
            context.last_command_exit_code = 0
            return result

        except Exception as e:
            # Store error state
            context.last_command_exit_code = 1
            context.last_command_error = str(e)
            raise e

    def plugin_generate_bom(project=None, inventory=None, output=None, **kwargs) -> Any:
        """Simulate KiCad plugin BOM generation.

        This simulates the KiCad plugin environment by calling the API
        with plugin-appropriate defaults and error handling.

        Args:
            project: Project directory or schematic file
            inventory: Inventory file path
            output: Output file path
            **kwargs: Additional plugin options

        Returns:
            Plugin result or raises exception
        """
        try:
            # Plugin simulation uses same API but with KiCad-like error handling
            return api_generate_bom(
                project=project, inventory=inventory, output=output, **kwargs
            )
        except Exception as e:
            # Plugin-style error formatting
            plugin_error = f"KiCad Plugin Error: {str(e)}"
            context.last_command_error = plugin_error
            context.last_command_exit_code = 1
            raise Exception(plugin_error)

    def plugin_generate_pos(project=None, output=None, **kwargs) -> Any:
        """Simulate KiCad plugin POS generation.

        Args:
            project: Project directory or PCB file
            output: Output file path
            **kwargs: Additional plugin options

        Returns:
            Plugin result or raises exception
        """
        try:
            # Plugin simulation uses same API but with KiCad-like error handling
            return api_generate_pos(project=project, output=output, **kwargs)
        except Exception as e:
            # Plugin-style error formatting
            plugin_error = f"KiCad Plugin Error: {str(e)}"
            context.last_command_error = plugin_error
            context.last_command_exit_code = 1
            raise Exception(plugin_error)

    def plugin_extract_inventory(project=None, output=None, **kwargs) -> Any:
        """Simulate KiCad plugin inventory extraction.

        Args:
            project: Project directory or schematic file
            output: Output file path
            **kwargs: Additional plugin options

        Returns:
            Plugin result or raises exception
        """
        try:
            # Plugin simulation uses same API but with KiCad-like error handling
            return api_extract_inventory(project=project, output=output, **kwargs)
        except Exception as e:
            # Plugin-style error formatting
            plugin_error = f"KiCad Plugin Error: {str(e)}"
            context.last_command_error = plugin_error
            context.last_command_exit_code = 1
            raise Exception(plugin_error)

    # Attach methods to context
    context.execute_shell = execute_shell
    context.api_generate_bom = api_generate_bom
    context.api_generate_pos = api_generate_pos
    context.api_extract_inventory = api_extract_inventory
    context.plugin_generate_bom = plugin_generate_bom
    context.plugin_generate_pos = plugin_generate_pos
    context.plugin_extract_inventory = plugin_extract_inventory
