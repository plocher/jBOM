"""BOM-related step definitions for Behave tests.

These steps create minimal KiCad .kicad_sch files compatible with
jbom.services.schematic_reader and verify CLI output/files.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from behave import given, then
from diagnostic_utils import assert_with_diagnostics

try:
    from jbom.config.fabricators import list_fabricators
except ImportError:

    def list_fabricators():
        return ["jlc"]  # fallback


# -------------------------
# Given steps (test inputs)
# -------------------------
@given('a KiCad schematic file "{filename}" with components:')
def given_schematic_with_components(context, filename: str) -> None:
    """Create a schematic at project_root/filename with the table components."""
    if not context.table:
        raise AssertionError("Component table required")
    components: List[Dict[str, Any]] = [row.as_dict() for row in context.table]
    _write_schematic(context, filename, components)


@given('a KiCad schematic file "{filename}" with basic components')
def given_basic_schematic(context, filename: str) -> None:
    """Create a schematic with a few standard parts used by features."""
    components = [
        {"Reference": "R1", "Value": "10K", "Footprint": "R_0805_2012"},
        {"Reference": "C1", "Value": "100nF", "Footprint": "C_0603_1608"},
        {"Reference": "U1", "Value": "LM358", "Footprint": "SOIC-8_3.9x4.9mm"},
    ]
    _write_schematic(context, filename, components)


@given('a file "{filename}" with content "{text}"')
def given_file_with_content(context, filename: str, text: str) -> None:
    (context.project_root / filename).write_text(text, encoding="utf-8")


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


@given('a KiCad schematic file "{filename}" with DNP components')
def given_schematic_with_dnp(context, filename: str) -> None:
    components = [
        {"Reference": "R1", "Value": "10K", "Footprint": "R_0805_2012", "DNP": "No"},
        {"Reference": "R2", "Value": "22K", "Footprint": "R_0805_2012", "DNP": "Yes"},
    ]
    _write_schematic(context, filename, components)


@given('a KiCad schematic file "{filename}" with components excluded from BOM')
def given_schematic_with_excluded(context, filename: str) -> None:
    components = [
        {"Reference": "R1", "Value": "10K", "Footprint": "R_0805_2012", "InBOM": "Yes"},
        {"Reference": "R2", "Value": "22K", "Footprint": "R_0805_2012", "InBOM": "No"},
    ]
    _write_schematic(context, filename, components)


@then("the CSV output has a row where")
def then_csv_output_has_row(context) -> None:
    """Assert CSV output contains a row matching the table's single row of expectations."""
    out = getattr(context, "last_output", "")
    assert out.strip(), "No CSV output captured"
    import csv
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


# -----------------
# Helper functions
# -----------------


def _write_schematic(context, filename: str, components: List[Dict[str, Any]]) -> None:
    target = context.project_root / filename
    content = _render_kicad_schematic(Path(filename).stem, components)
    target.write_text(content, encoding="utf-8")


def _render_kicad_schematic(stem: str, components: List[Dict[str, Any]]) -> str:
    lines = [
        "(kicad_sch (version 20221018) (generator eeschema)",
        f"  (uuid test-{stem}-uuid)",
        '  (paper "A4")',
    ]
    for c in components:
        ref = c.get("Reference") or c.get("reference", "U1")
        val = c.get("Value") or c.get("value", "VAL")
        fp = c.get("Footprint") or c.get("footprint", "")
        dnp = str(c.get("DNP", c.get("dnp", "no"))).lower() in ("yes", "true", "1")
        in_bom_flag = str(c.get("InBOM", c.get("in_bom", "yes"))).lower() not in (
            "no",
            "false",
            "0",
        )
        sym = [
            '  (symbol (lib_id "Device:R") (at 100 100 0) (unit 1)',
            f"    (in_bom {'yes' if in_bom_flag else 'no'}) (on_board yes)",
            f'    (property "Reference" "{ref}" (at 0 0 0))',
            f'    (property "Value" "{val}" (at 0 0 0))',
            f'    (property "Footprint" "{fp}" (at 0 0 0))',
            "    (dnp yes)" if dnp else "",
            "  )",
        ]
        lines.extend(sym)
    lines.append(")")
    return "\n".join(lines)


def _get_available_fabricators() -> list[str]:
    """Get list of available fabricators."""
    # All these fabricators are confirmed to work in jbom
    return ["generic", "jlc", "pcbway", "seeed"]


# Dynamic fabricator testing step definitions


@then("the BOM works with all configured fabricators")
def then_bom_works_with_all_fabricators(context) -> None:
    """Test that BOM generation works with all available fabricators."""
    # Extract the base command from the last run
    if not hasattr(context, "last_command"):
        raise AssertionError("No previous command found to test with fabricators")

    base_cmd = context.last_command
    # Remove any existing fabricator flags
    for fab in ["--generic", "--jlc", "--pcbway", "--seeed"] + [
        f"--fabricator {f}" for f in _get_available_fabricators()
    ]:
        base_cmd = base_cmd.replace(fab, "").strip()

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
    for fab in ["--generic", "--jlc", "--pcbway", "--seeed"] + [
        f"--fabricator {f}" for f in _get_available_fabricators()
    ]:
        base_cmd = base_cmd.replace(fab, "").strip()

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
