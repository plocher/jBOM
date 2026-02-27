"""Diagnostic utilities for test failure reporting.

This module provides helpers to generate comprehensive diagnostic output
when test assertions fail, making it easier to understand what went wrong.
"""

from typing import Any, Optional
from pathlib import Path


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
    if hasattr(context, "last_command_output") or hasattr(context, "cli_command"):
        lines.append("\n--- COMMAND EXECUTED ---")
        if hasattr(context, "cli_command"):
            lines.append(f"CLI: {context.cli_command}")

    # Exit code
    if hasattr(context, "last_command_exit_code"):
        lines.append(f"\nExit Code: {context.last_command_exit_code}")

    # Standard output
    if hasattr(context, "last_command_output"):
        output = context.last_command_output or "(empty)"
        lines.append(f"\n--- STDOUT ---\n{output}")

    # Standard error
    if hasattr(context, "last_command_error"):
        error = context.last_command_error or "(empty)"
        lines.append(f"\n--- STDERR ---\n{error}")

    # Multi-modal results (CLI, API, Plugin)
    if hasattr(context, "results"):
        lines.append("\n--- MULTI-MODAL RESULTS ---")
        for method, result in context.results.items():
            lines.append(f"\n{method}:")
            lines.append(f"  Exit Code: {result.get('exit_code', 'N/A')}")

            output_text = result.get("output", "(empty)")
            if len(output_text) > 200:
                lines.append(f"  Output: {output_text[:200]}...")
            else:
                lines.append(f"  Output: {output_text}")

            if "error_message" in result:
                error_text = result.get("error_message", "(empty)")
                if len(error_text) > 200:
                    lines.append(f"  Error: {error_text[:200]}...")
                else:
                    lines.append(f"  Error: {error_text}")

    # Working directory
    if hasattr(context, "scenario_temp_dir"):
        lines.append(f"\n--- WORKING DIRECTORY ---\n{context.scenario_temp_dir}")

    # BOM output file (if expected)
    if hasattr(context, "bom_output_file"):
        lines.append("\n--- BOM OUTPUT FILE ---")
        bom_file = Path(context.bom_output_file)
        if bom_file.exists():
            size = bom_file.stat().st_size
            lines.append(f"  {bom_file.name}: EXISTS ({size} bytes)")
        else:
            lines.append(f"  {bom_file.name}: NOT FOUND")
            lines.append(f"  Expected at: {bom_file}")

    # Files generated
    if include_files and hasattr(context, "scenario_temp_dir"):
        lines.append("\n--- FILES GENERATED ---")
        try:
            temp_dir = Path(context.scenario_temp_dir)
            if temp_dir.exists():
                files = list(temp_dir.rglob("*"))
                if files:
                    for file in sorted(files)[:20]:  # Limit to 20 files
                        if file.is_file():
                            size = file.stat().st_size
                            rel_path = file.relative_to(temp_dir)
                            lines.append(f"  {rel_path} ({size} bytes)")
                else:
                    lines.append("  (no files generated)")
        except Exception as e:
            lines.append(f"  (error listing files: {e})")

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
