"""Diagnostic utilities for test failure reporting.

This module provides helpers to generate comprehensive diagnostic output
when test assertions fail, making it easier to understand what went wrong.
"""

from typing import Any, Optional


def format_execution_context(context, include_files: bool = True) -> str:
    """Format execution context for diagnostic output.

    Args:
        context: Behave context object
        include_files: Whether to include file listing in output

    Returns:
        Formatted diagnostic string
    """
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("DIAGNOSTIC INFORMATION")
    lines.append("=" * 80)

    # Command executed
    if hasattr(context, "last_command"):
        lines.append("\n--- COMMAND EXECUTED ---")
        lines.append(f"Command: {context.last_command}")

    # Exit code
    if hasattr(context, "last_exit_code"):
        lines.append(f"\nExit Code: {context.last_exit_code}")

    # Output (stdout + stderr combined)
    if hasattr(context, "last_output"):
        output = context.last_output or "(empty)"
        lines.append(f"\n--- OUTPUT ---\n{output}")

    # Working directory
    if hasattr(context, "project_root"):
        lines.append(f"\n--- WORKING DIRECTORY ---\n{context.project_root}")

    # Plugin directory
    plugins_dir = context.src_root / "jbom_new" / "plugins"
    if plugins_dir.exists():
        lines.append("\n--- PLUGINS DIRECTORY ---")
        try:
            plugins = [
                p.name
                for p in plugins_dir.iterdir()
                if p.is_dir() and not p.name.startswith((".", "_"))
            ]
            if plugins:
                for plugin in plugins:
                    lines.append(f"  {plugin}/")
            else:
                lines.append("  (empty)")
        except Exception as e:
            lines.append(f"  (error listing: {e})")

    # Files generated (if any test plugins were created)
    if include_files and hasattr(context, "created_plugins"):
        lines.append("\n--- CREATED TEST PLUGINS ---")
        for plugin_dir in context.created_plugins:
            lines.append(f"  {plugin_dir.name}/")
            if plugin_dir.exists():
                for file in plugin_dir.iterdir():
                    if file.is_file():
                        size = file.stat().st_size
                        lines.append(f"    {file.name} ({size} bytes)")

    lines.append("\n" + "=" * 80 + "\n")
    return "\n".join(lines)


def format_comparison(expected: Any, actual: Any, context_label: str = "") -> str:
    """Format expected vs actual comparison.

    Args:
        expected: Expected value
        actual: Actual value
        context_label: Additional context label

    Returns:
        Formatted comparison string
    """
    lines = []
    if context_label:
        lines.append(f"\n{context_label}:")
    lines.append(f"  Expected: {expected}")
    lines.append(f"  Actual:   {actual}")
    return "\n".join(lines)


def assert_with_diagnostics(
    condition: bool,
    message: str,
    context,
    expected: Optional[Any] = None,
    actual: Optional[Any] = None,
) -> None:
    """Assert with enhanced diagnostic output on failure.

    Args:
        condition: Boolean condition to assert
        message: Base assertion message
        context: Behave context object
        expected: Expected value (optional)
        actual: Actual value (optional)

    Raises:
        AssertionError: If condition is False, with diagnostic information
    """
    if not condition:
        diagnostic_parts = [f"\nASSERTION FAILED: {message}"]

        if expected is not None and actual is not None:
            diagnostic_parts.append(format_comparison(expected, actual))

        diagnostic_parts.append(format_execution_context(context))

        raise AssertionError("\n".join(diagnostic_parts))
