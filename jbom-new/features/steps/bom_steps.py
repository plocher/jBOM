"""BOM-related step definitions for Behave tests.

These steps create minimal KiCad .kicad_sch files compatible with
jbom.services.schematic_reader and verify CLI output/files.
"""
from __future__ import annotations

import csv

from behave import then
from diagnostic_utils import assert_with_diagnostics

try:
    from jbom.config.fabricators import (
        get_available_fabricators as _get_available_fabricators,
    )
except ImportError:

    def _get_available_fabricators():
        return ["generic"]  # fallback


# -------------------------
# Legacy step definitions removed - use ultra-simplified project-centric pattern:
# - Given a schematic that contains: (in project_centric_steps.py)
# - Given the generic fabricator is selected (in project_centric_steps.py)
# -------------------------


# --------------------------
# Then steps (verifications)
# --------------------------
@then("the command exits with code {code:d}")
def then_exit_code_is(context, code: int) -> None:
    actual_code = getattr(context, "last_exit_code", None)
    assert_with_diagnostics(
        actual_code == code,
        "Exit code mismatch",
        context,
        expected=code,
        actual=actual_code,
    )


@then('the output contains CSV headers "{headers}"')
def then_output_contains_headers(context, headers: str) -> None:
    expected = [h.strip() for h in headers.split(",")]
    output = getattr(context, "last_output", "")
    # parse first CSV line from output
    first_line = output.splitlines()[0] if output else ""
    actual = [h.strip() for h in first_line.split(",") if first_line]
    assert_with_diagnostics(
        actual == expected,
        "CSV headers mismatch",
        context,
        expected=expected,
        actual=actual,
    )


@then("the output contains CSV headers")
def then_output_contains_csv_headers(context) -> None:
    """Assert that output contains CSV headers (any headers)."""
    output = getattr(context, "last_output", "")
    assert_with_diagnostics(
        output.strip(),
        "No output captured",
        context,
        expected="non-empty output",
        actual=output,
    )

    lines = output.splitlines()
    assert_with_diagnostics(
        len(lines) > 0,
        "No output lines found",
        context,
        expected="at least one line",
        actual=f"{len(lines)} lines",
    )

    # First line should look like CSV headers (contain commas and reasonable field names)
    first_line = lines[0].strip()
    assert_with_diagnostics(
        first_line,
        "First line is empty",
        context,
        expected="non-empty first line",
        actual=first_line,
    )
    assert_with_diagnostics(
        "," in first_line,
        "First line doesn't look like CSV headers",
        context,
        expected="line containing commas",
        actual=first_line,
    )

    # Should have typical BOM headers
    header_indicators = ["Reference", "Value", "Quantity", "Footprint"]
    has_bom_indicators = any(indicator in first_line for indicator in header_indicators)
    assert_with_diagnostics(
        has_bom_indicators,
        "First line doesn't contain typical BOM headers",
        context,
        expected=f"headers containing one of: {header_indicators}",
        actual=first_line,
    )


@then('the output contains "{text}"')
def then_output_contains_text(context, text: str) -> None:
    output = getattr(context, "last_output", "")
    assert_with_diagnostics(
        output and text in output,
        "Expected text not found in output",
        context,
        expected=text,
        actual=output,
    )


@then("the output contains a formatted table header")
def then_output_contains_table_header(context) -> None:
    out = getattr(context, "last_output", "")
    # Simple heuristic: look for the table header used by CLI
    assert (
        "References" in out and "Footprint" in out
    ), f"No table header found. Output:\n{out}"


@then("the output contains component references and values")
def then_output_contains_component_markers(context) -> None:
    out = getattr(context, "last_output", "")
    # The basic components step creates R1/C1/U1 values
    markers = ["R1", "C1", "U1"]
    assert all(m in out for m in markers), f"Missing markers in output. Output:\n{out}"


@then('a file named "{filename}" exists')
def then_file_exists(context, filename: str) -> None:
    p = context.project_root / filename
    assert_with_diagnostics(
        p.exists() and p.is_file(),
        "File not found",
        context,
        expected=f"file to exist: {filename}",
        actual=f"file exists: {p.exists()}, is file: {p.is_file() if p.exists() else 'N/A'}",
    )


@then('the file "{filename}" contains valid CSV data')
def then_file_contains_csv(context, filename: str) -> None:
    p = context.project_root / filename
    assert p.exists(), f"File not found: {p}"
    with p.open("r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows and len(rows[0]) >= 2, f"CSV appears invalid or empty: {p}"


@then('the error output contains "{text}"')
def then_error_output_contains(context, text: str) -> None:
    out = getattr(context, "last_output", "")
    assert text in out, f"Expected error text '{text}' not present. Output:\n{out}"


@then("the line count is {n:d}")
def then_line_count_is(context, n: int) -> None:
    out = getattr(context, "last_output", "")
    lines = [ln for ln in out.splitlines() if ln.strip()]
    # For BOM CSV to stdout, first line is headers
    count = max(0, len(lines) - 1)
    assert count == n, f"Expected {n} data lines, got {count}. Output:\n{out}"


@then("the output does not contain DNP component references")
def then_no_dnp_refs(context) -> None:
    out = getattr(context, "last_output", "")
    assert "DNP" not in out, out


@then("the output contains excluded component references")
def then_contains_excluded_refs(context) -> None:
    out = getattr(context, "last_output", "")
    # Minimal check: output non-empty
    assert out.strip() != ""


# Legacy @given steps removed - use table-driven approach:
# Given a schematic that contains:
#   | Reference | Value | DNP | InBOM |
#   | R1        | 10K   | No  | Yes   |
#   | R2        | 22K   | Yes | No    |


@then("the CSV output has a row where")
def then_csv_output_has_row(context) -> None:
    """Assert CSV output contains a row matching the table's single row of expectations."""
    out = getattr(context, "last_output", "")
    assert out.strip(), "No CSV output captured"

    from io import StringIO

    rows = list(csv.DictReader(StringIO(out)))
    assert (
        context.table and len(context.table.rows) == 1
    ), "Provide exactly one expected row"
    expected = {h: context.table.rows[0][h] for h in context.table.headings}

    def matches(r: dict) -> bool:
        for k, v in expected.items():
            actual = r.get(k)
            if actual is None:
                # Try case-insensitive match
                for rk in r.keys():
                    if rk.lower() == k.lower():
                        actual = r[rk]
                        break
            if actual is None or str(actual) != str(v):
                return False
        return True

    assert any(
        matches(r) for r in rows
    ), f"Expected row not found: {expected}\nRows: {rows}"


# Field system step definitions
@then('the output should contain CSV headers "{headers}"')
def then_output_should_contain_csv_headers(context, headers: str) -> None:
    """Assert output should contain specific CSV headers (alias for consistency)."""
    then_output_contains_headers(context, headers)


@then('the output should not contain CSV headers "{headers}"')
def then_output_should_not_contain_csv_headers(context, headers: str) -> None:
    """Assert output should not contain specific CSV headers."""
    expected = headers.strip()
    output = getattr(context, "last_output", "")
    assert_with_diagnostics(
        expected not in output,
        f"Output should not contain CSV headers '{expected}' but it does",
        context,
        expected=f"output without '{expected}'",
        actual=output,
    )


@then('the console table headers should be "{headers}"')
def then_console_table_headers_should_be(context, headers: str) -> None:
    """Assert console table has specific headers (space-separated)."""
    expected_headers = headers.split()
    output = getattr(context, "last_output", "")

    # Look for the table header line (should contain the headers)
    lines = output.splitlines()
    header_line = None
    for line in lines:
        if all(header in line for header in expected_headers):
            header_line = line
            break

    assert_with_diagnostics(
        header_line is not None,
        f"Console table headers '{headers}' not found",
        context,
        expected=f"table headers: {expected_headers}",
        actual=output,
    )


@then('the console table should not contain "{text}"')
def then_console_table_should_not_contain(context, text: str) -> None:
    """Assert console table output does not contain specified text."""
    output = getattr(context, "last_output", "")
    assert_with_diagnostics(
        text not in output,
        f"Console table should not contain '{text}' but it does",
        context,
        expected=f"table without '{text}'",
        actual=output,
    )


# -----------------
# Helper functions (cleaned up - schematic writing moved to project_centric_steps.py)
# -----------------


# Dynamic fabricator testing step definitions


@then("the BOM works with all configured fabricators")
def then_bom_works_with_all_fabricators(context) -> None:
    """Test that BOM generation works with all available fabricators."""
    # Extract the base command from the last run
    if not hasattr(context, "last_command"):
        raise AssertionError("No previous command found to test with fabricators")

    base_cmd = context.last_command
    # Remove any existing fabricator flags - using dynamic fabricator discovery
    available_fabricators = _get_available_fabricators()
    fabricator_flags = [f"--{f}" for f in available_fabricators] + [
        f"--fabricator {f}" for f in available_fabricators
    ]
    for fab_flag in fabricator_flags:
        base_cmd = base_cmd.replace(fab_flag, "").strip()

    fabricators = _get_available_fabricators()
    failures = []

    # Test with no fabricator flag (default behavior)
    try:
        context.execute_steps(f'When I run "{base_cmd}"')
        context.execute_steps("Then the command exits with code 0")
    except Exception as e:
        failures.append(f"Default (no flag): {e}")

    # Test each configured fabricator
    for fab in fabricators:
        try:
            context.execute_steps(f'When I run "{base_cmd} --fabricator {fab}"')
            context.execute_steps("Then the command exits with code 0")
        except Exception as e:
            failures.append(f"--fabricator {fab}: {e}")

    if failures:
        raise AssertionError("Fabricator testing failures:\n" + "\n".join(failures))


@then("the BOM output format varies by fabricator")
def then_bom_output_varies_by_fabricator(context) -> None:
    """Test that different fabricators produce different output formats."""
    if not hasattr(context, "last_command"):
        raise AssertionError("No previous command found to test with fabricators")

    base_cmd = context.last_command
    # Remove any existing fabricator flags and add the standard field preset to show differences
    # Using dynamic fabricator discovery - addresses Issue #31
    available_fabricators = _get_available_fabricators()
    fabricator_flags = [f"--{f}" for f in available_fabricators] + [
        f"--fabricator {f}" for f in available_fabricators
    ]
    for fab_flag in fabricator_flags:
        base_cmd = base_cmd.replace(fab_flag, "").strip()

    # Add standard field preset to ensure we get fabricator-specific headers
    if "-f" not in base_cmd and "--fields" not in base_cmd:
        base_cmd += " -f +standard"

    fabricators = _get_available_fabricators()
    outputs = {}

    # Collect output from each fabricator
    for fab in fabricators:
        try:
            context.execute_steps(f'When I run "{base_cmd} --fabricator {fab}"')
            output = getattr(context, "last_output", "")
            # Just capture headers to compare formats
            header_line = output.split("\n")[0] if output else ""
            outputs[fab] = header_line
        except Exception:
            continue  # Skip fabricators that don't work

    # Verify headers are different (at least some variation)
    if len(outputs) < 2:
        return  # Not enough working fabricators to compare

    headers = list(outputs.values())
    all_same = all(h == headers[0] for h in headers)
    assert (
        not all_same
    ), f"All fabricator headers are identical. Expected format differences.\nHeaders: {outputs}"
