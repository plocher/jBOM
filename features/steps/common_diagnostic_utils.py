"""Diagnostic utilities for test failure reporting.

This module provides helpers to generate comprehensive diagnostic output
when test assertions fail, making it easier to understand what went wrong.
"""

import csv
from typing import Any, Optional


def csv_contains_fields(content: str, text: str) -> bool:
    """Check whether *content* (text with CSV lines) contains *text*.

    Handles both plain substring matching and QUOTE_ALL-quoted CSV output:
    1. Tries a direct substring match first (fast path, covers plain text).
    2. If *text* contains a comma, parses *text* as a CSV row and checks
       whether those field values appear as a consecutive subsequence in any
       CSV line of *content*.
    """
    # Fast path: literal substring present
    if text in content:
        return True

    # CSV-aware path: only meaningful when text looks like comma-separated values
    if "," not in text:
        return False

    try:
        expected_fields = next(csv.reader([text]))
    except Exception:
        return False

    n = len(expected_fields)
    for line in content.splitlines():
        if not line.strip():
            continue
        try:
            row_fields = next(csv.reader([line]))
        except Exception:
            continue
        # Check if expected_fields appears as any consecutive subsequence
        for i in range(len(row_fields) - n + 1):
            if row_fields[i : i + n] == expected_fields:
                return True
    return False


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
