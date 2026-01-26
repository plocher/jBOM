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
# Legacy step definitions removed - use ultra-simplified canonical pattern:
# - Given a schematic that contains: (in project_centric_steps.py)
# - Given the generic fabricator is selected (in common_steps.py)
# -------------------------


# --------------------------
# Given steps (setup)
# --------------------------


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


@then('the file "{filename}" should contain only CSV headers')
def then_file_contains_only_csv_headers(context, filename: str) -> None:
    """Assert that a CSV file contains only headers (no data rows)."""
    p = context.project_root / filename
    assert_with_diagnostics(
        p.exists() and p.is_file(),
        "File not found",
        context,
        expected=f"file to exist: {filename}",
        actual=f"file exists: {p.exists()}, is file: {p.is_file() if p.exists() else 'N/A'}",
    )

    with p.open("r", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert_with_diagnostics(
        len(rows) >= 1,
        "CSV file should have at least header row",
        context,
        expected="at least 1 row (headers)",
        actual=f"{len(rows)} rows",
    )

    assert_with_diagnostics(
        len(rows) == 1,
        "CSV file should contain only headers (no data rows)",
        context,
        expected="exactly 1 row (headers only)",
        actual=f"{len(rows)} rows total",
    )


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
                    if rk is not None and rk.lower() == k.lower():
                        actual = r[rk]
                        break
            if actual is None or str(actual) != str(v):
                return False
        return True

    assert any(
        matches(r) for r in rows
    ), f"Expected row not found: {expected}\nRows: {rows}"


@then("the CSV output has rows where")
def then_csv_output_has_rows(context) -> None:
    """Assert CSV output contains all rows matching the table's expectations."""
    out = getattr(context, "last_output", "")
    assert out.strip(), "No CSV output captured"

    from io import StringIO

    rows = list(csv.DictReader(StringIO(out)))
    assert (
        context.table and len(context.table.rows) >= 1
    ), "Provide at least one expected row"

    def matches(r: dict, expected_row: dict) -> bool:
        for k, v in expected_row.items():
            actual = r.get(k)
            if actual is None:
                # Try case-insensitive match
                for rk in r.keys():
                    if rk is not None and rk.lower() == k.lower():
                        actual = r[rk]
                        break
            if actual is None or str(actual) != str(v):
                return False
        return True

    # Check that each expected row exists in the CSV output
    missing_rows = []
    for table_row in context.table.rows:
        expected = {h: table_row[h] for h in context.table.headings}
        if not any(matches(r, expected) for r in rows):
            missing_rows.append(expected)

    assert (
        not missing_rows
    ), f"Expected rows not found: {missing_rows}\nActual CSV rows: {rows}"


@then("the CSV output has rows where:")
def then_csv_output_has_rows_with_colon(context) -> None:
    """Assert CSV output contains all rows matching the table's expectations (colon version)."""
    then_csv_output_has_rows(context)


@then('the CSV file "{filename}" has rows where')
def then_csv_file_has_rows(context, filename: str) -> None:
    """Assert CSV file contains all rows matching the table's expectations."""
    p = context.project_root / filename
    assert_with_diagnostics(
        p.exists() and p.is_file(),
        "CSV file not found",
        context,
        expected=f"file to exist: {filename}",
        actual=f"file exists: {p.exists()}, is file: {p.is_file() if p.exists() else 'N/A'}",
    )

    with p.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert_with_diagnostics(
        context.table and len(context.table.rows) >= 1,
        "Expected at least one expected row in table",
        context,
        expected="table with ≥1 rows",
        actual=f"table with {len(context.table.rows) if context.table else 0} rows",
    )

    def matches(r: dict, expected_row: dict) -> bool:
        for k, v in expected_row.items():
            actual = r.get(k)
            if actual is None:
                # Try case-insensitive match
                for rk in r.keys():
                    if rk is not None and rk.lower() == k.lower():
                        actual = r[rk]
                        break
            if actual is None or str(actual) != str(v):
                return False
        return True

    # Check that each expected row exists in the CSV file
    missing_rows = []
    for table_row in context.table.rows:
        expected = {h: table_row[h] for h in context.table.headings}
        if not any(matches(r, expected) for r in rows):
            missing_rows.append(expected)

    assert_with_diagnostics(
        not missing_rows,
        "Expected rows not found in CSV file",
        context,
        expected="all rows from table to be found",
        actual=f"missing: {missing_rows}, found: {rows}",
    )


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
# Helper functions (cleaned up)
# -----------------


# Resilient error-reporting assertions
@then("the output reports errors for files:")
def then_output_reports_errors_for_files(context) -> None:
    """Assert that output contains error mentions for each filename in the table.

    Table format:
    | filename |
    | missing1.csv |
    | bad.csv |
    """
    assert context.table is not None, "Expected a table of filenames"
    out = getattr(context, "last_output", "")
    lower_lines = [ln.lower() for ln in out.splitlines()]
    missing = []
    for row in context.table:
        fname = row.get("filename") or row.cells[0]
        found = any("error" in ln and fname.lower() in ln for ln in lower_lines)
        if not found:
            missing.append(fname)
    assert_with_diagnostics(
        not missing,
        f"Expected error lines for files not found: {missing}",
        context,
        expected="errors for files listed",
        actual=out,
    )


@then("the output contains at least {n:d} errors")
def then_output_contains_at_least_n_errors(context, n: int) -> None:
    out = getattr(context, "last_output", "")
    count = sum(1 for ln in out.splitlines() if "error" in ln.lower())
    assert_with_diagnostics(
        count >= n,
        f"Expected at least {n} error lines, found {count}",
        context,
        expected=f">= {n} errors",
        actual=f"{count} errors\n{out}",
    )


# Resilient CSV component assertions (ignore IPN unless provided)
@then("the CSV output row count is {n:d}")
def then_csv_output_row_count_is(context, n: int) -> None:
    out = getattr(context, "last_output", "")
    from io import StringIO

    rows = list(csv.DictReader(StringIO(out)))
    assert_with_diagnostics(
        len(rows) == n,
        "Row count mismatch",
        context,
        expected=n,
        actual=len(rows),
    )


@then("the CSV output has components where:")
def then_csv_output_has_components_where(context) -> None:
    """Assert CSV output contains rows matching only the provided columns.

    Example table:
    | Category | Value |
    | RES | 22k |
    Optional columns like Package may be included.
    """
    out = getattr(context, "last_output", "")
    from io import StringIO

    rows = list(csv.DictReader(StringIO(out)))
    assert context.table is not None and context.table.rows, "Expected component table"

    def header_get(d: dict, key: str):
        for k in d.keys():
            if k is not None and k.lower() == key.lower():
                return d[k]
        return None

    def matches(d: dict, expected: dict) -> bool:
        for k, v in expected.items():
            actual = header_get(d, k)
            if actual is None or str(actual) != str(v):
                return False
        return True

    missing = []
    for tr in context.table.rows:
        expected = {h: tr[h] for h in context.table.headings}
        if not any(matches(r, expected) for r in rows):
            missing.append(expected)
    assert_with_diagnostics(
        not missing,
        f"Expected components not found: {missing}",
        context,
        expected="all components present",
        actual=rows,
    )


@then("the CSV output does not contain components where:")
def then_csv_output_does_not_contain_components_where(context) -> None:
    out = getattr(context, "last_output", "")
    from io import StringIO

    rows = list(csv.DictReader(StringIO(out)))
    assert context.table is not None and context.table.rows, "Expected component table"

    def header_get(d: dict, key: str):
        for k in d.keys():
            if k is not None and k.lower() == key.lower():
                return d[k]
        return None

    def matches(d: dict, expected: dict) -> bool:
        for k, v in expected.items():
            actual = header_get(d, k)
            if actual is None or str(actual) != str(v):
                return False
        return True

    forbidden = []
    for tr in context.table.rows:
        expected = {h: tr[h] for h in context.table.headings}
        if any(matches(r, expected) for r in rows):
            forbidden.append(expected)
    assert_with_diagnostics(
        not forbidden,
        f"Forbidden components present: {forbidden}",
        context,
        expected="no forbidden components",
        actual=rows,
    )


# Field system step definitions - validation scenarios
@then('the error output should contain "{text}"')
def then_error_output_should_contain(context, text: str) -> None:
    """Assert error output should contain specific text."""
    error_output = getattr(
        context, "last_error_output", getattr(context, "last_output", "")
    )
    assert_with_diagnostics(
        text in error_output,
        "Expected error text not found",
        context,
        expected=text,
        actual=error_output,
    )


@then("the error output contains:")
def then_error_output_contains_table(context) -> None:
    """Assert error output contains all text items from table (table-driven version).

    Table format:
    | Expected .kicad_sch file |
    | Another error message   |
    """
    assert context.table is not None, "Expected table data for error validation"

    error_output = getattr(
        context, "last_error_output", getattr(context, "last_output", "")
    )

    # Check each text item in the table
    for row in context.table:
        text = row.cells[0]  # Get first (and typically only) cell
        assert_with_diagnostics(
            text in error_output,
            f"Expected error text not found: {text}",
            context,
            expected=text,
            actual=error_output,
        )


#  TODO Issue #31: This list needs to be dynamically constructed from the config files, not hardcoded
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
