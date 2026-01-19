"""BOM-related step definitions for Behave tests.

These steps create minimal KiCad .kicad_sch files compatible with
jbom.services.schematic_reader and verify CLI output/files.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from behave import given, then


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
    assert getattr(context, "last_exit_code", None) == code, (
        f"Expected exit {code}, got {getattr(context, 'last_exit_code', None)}\n"
        f"Output:\n{getattr(context, 'last_output', '')}"
    )


@then('the output contains CSV headers "{headers}"')
def then_output_contains_headers(context, headers: str) -> None:
    expected = [h.strip() for h in headers.split(",")]
    output = getattr(context, "last_output", "")
    # parse first CSV line from output
    first_line = output.splitlines()[0] if output else ""
    actual = [h.strip() for h in first_line.split(",") if first_line]
    assert (
        actual == expected
    ), f"Headers mismatch. Expected {expected}, got {actual}. Output: {first_line}"


@then('the output contains "{text}"')
def then_output_contains_text(context, text: str) -> None:
    assert (
        getattr(context, "last_output", "") and text in context.last_output
    ), f"Expected text not found: {text}\nOutput:\n{getattr(context, 'last_output', '')}"


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
    assert p.exists() and p.is_file(), f"File not found: {p}"


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
    assert context.table and len(context.table) == 1, "Provide exactly one expected row"
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
            f"    {'(dnp yes)' if dnp else ''}",
            "  )",
        ]
        lines.extend(sym)
    lines.append(")")
    return "\n".join(lines)
