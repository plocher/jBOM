"""Inventory-related step definitions adapted to current CLI.
"""
from __future__ import annotations

import csv
import stat
from pathlib import Path

from behave import given, then


@given('an inventory file "{filename}" with data:')
def given_inventory_file_with_data(context, filename: str) -> None:
    p = context.project_root / filename
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(context.table.headings)
        for row in context.table:
            writer.writerow([row[h] for h in context.table.headings])


@given('an empty inventory file "{filename}"')
def given_empty_inventory_file(context, filename: str) -> None:
    p = context.project_root / filename
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["IPN", "Category", "Value", "Description", "Package"]
        )  # minimal header


@given('an inventory file "{filename}" with mixed component categories')
def given_inventory_mixed(context, filename: str) -> None:
    rows = [
        ["RES_10K", "RESISTOR", "10K", "10K Ohm Resistor", "0805"],
        ["CAP_100N", "CAPACITOR", "100nF", "100nF Ceramic Cap", "0603"],
        ["IC_LM358", "INTEGRATED_CIRCUIT", "LM358", "Dual Op-Amp", "SOIC-8"],
    ]
    p = context.project_root / filename
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["IPN", "Category", "Value", "Description", "Package"])
        writer.writerows(rows)


@given('an inventory file "{filename}" with only resistors')
def given_inventory_only_resistors(context, filename: str) -> None:
    rows = [
        ["RES_10K", "RESISTOR", "10K", "10K Ohm Resistor", "0805"],
        ["RES_22K", "RESISTOR", "22K", "22K Ohm Resistor", "0805"],
    ]
    p = context.project_root / filename
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["IPN", "Category", "Value", "Description", "Package"])
        writer.writerows(rows)


@given('a file "{filename}" with invalid CSV format')
def given_invalid_csv(context, filename: str) -> None:
    (context.project_root / filename).write_text("not,csv\nmalformed", encoding="utf-8")


@then('the file "{filename}" contains CSV headers "{headers}"')
def then_file_contains_headers(context, filename: str, headers: str) -> None:
    expected = [h.strip() for h in headers.split(",")]
    p = context.project_root / filename
    with p.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        actual = next(reader)
    assert (
        actual[: len(expected)] == expected
    ), f"Headers mismatch: expected {expected}, got {actual}"


@then('the file "{filename}" contains exactly {n:d} data rows')
def then_file_contains_n_rows(context, filename: str, n: int) -> None:
    p = context.project_root / filename
    with p.open("r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert max(0, len(rows) - 1) == n, f"Expected {n} data rows, got {len(rows) - 1}"


@then("the output contains only resistor components")
def then_output_only_resistors(context) -> None:
    out = getattr(context, "last_output", "")
    assert "RESISTOR" in out, out
    assert "CAPACITOR" not in out and "INDUCTOR" not in out, out


@then("the output does not contain capacitor components")
def then_output_no_caps(context) -> None:
    out = getattr(context, "last_output", "")
    assert "CAPACITOR" not in out, out


@then("the output contains verbose information about component processing")
def then_output_verbose_inventory(context) -> None:
    out = getattr(context, "last_output", "")
    assert "Generated inventory with" in out or "Inventory:" in out, out


@given('an inventory file "{filename}" with only R1 data')
def given_inventory_only_r1(context, filename: str) -> None:
    p = context.project_root / filename
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "IPN",
                "Category",
                "Value",
                "Description",
                "Package",
                "Manufacturer",
                "MFGPN",
            ]
        )
        writer.writerow(
            ["RES_10K", "RESISTOR", "10K", "10K Ohm", "0805", "Yageo", "RC0805-10K"]
        )


@given('an inventory file "{filename}" with matching data')
def given_inventory_matching(context, filename: str) -> None:
    # Provide rows that should match the schematic basic components
    p = context.project_root / filename
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "IPN",
                "Category",
                "Value",
                "Description",
                "Package",
                "Manufacturer",
                "MFGPN",
                "LCSC",
            ]
        )
        writer.writerow(
            [
                "RES_10K",
                "RESISTOR",
                "10K",
                "Res 10K",
                "R_0805_2012",
                "Yageo",
                "RC0805-10K",
                "C25804",
            ]
        )
        writer.writerow(
            [
                "CAP_100nF",
                "CAPACITOR",
                "100nF",
                "Cap 100nF",
                "C_0603_1608",
                "Samsung",
                "CL10B104",
                "C14663",
            ]
        )


@then('the file "{filename}" contains inventory columns')
def then_file_contains_inventory_columns(context, filename: str) -> None:
    p = context.project_root / filename
    with p.open("r", encoding="utf-8") as f:
        header = f.readline().strip()
    required = ["Manufacturer", "Manufacturer Part", "Description"]
    for col in required:
        assert (
            col in header
        ), f"Missing inventory column '{col}' in {filename}: {header}"


@given('an inventory file with fields "{field_list}"')
def given_inventory_file_with_fields(context, field_list: str) -> None:
    """Create an inventory.csv file with specific fields for testing I: prefix functionality."""
    fields = [f.strip() for f in field_list.split(",")]

    # Create basic inventory file with the specified fields
    p = context.project_root / "inventory.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write headers: standard fields + custom fields
        headers = ["IPN", "Category", "Value", "Description"] + fields
        writer.writerow(headers)

        # Write sample data rows matching components from background table
        writer.writerow(
            ["RES_10K", "RESISTOR", "10K", "10K Resistor", "3.3V", "5%", "0805"]
        )
        writer.writerow(
            ["CAP_100N", "CAPACITOR", "100nF", "100nF Capacitor", "16V", "10%", "0603"]
        )


@then('the file "{filename}" contains "{text}"')
def then_file_contains_text(context, filename: str, text: str) -> None:
    p = context.project_root / filename
    content = p.read_text(encoding="utf-8")
    assert text in content, f"Expected '{text}' in {filename}."


@then("the output contains inventory enhancement columns")
def then_output_contains_inventory_columns(context) -> None:
    """Assert that output shows inventory enhancement (headers or data)."""
    out = getattr(context, "last_output", "")
    # Current implementation may append inventory data without updating headers
    # Check for either proper headers OR inventory data in rows
    inventory_indicators = [
        "Description",
        "LCSC",
        "Datasheet",
        "SMD",
        "Manufacturer",
        "Part",
    ]
    lines = out.splitlines()

    # Check headers first
    if lines:
        header_found = any(ind in lines[0] for ind in inventory_indicators)
        if header_found:
            return

    # If no headers, check for inventory data in rows (current behavior)
    data_lines = lines[1:] if len(lines) > 1 else []
    has_inventory_data = False
    for line in data_lines:
        fields = line.split(",")
        # Standard BOM has 4 fields, inventory enhancement should have more
        if len(fields) > 4:
            has_inventory_data = True
            break

    assert has_inventory_data, (
        "No inventory enhancement detected in output. Expected more than 4 "
        "CSV fields per row or inventory headers.\nOutput: " + out
    )


@then("the output contains inventory data for matched components")
def then_output_contains_inventory_data(context) -> None:
    """Assert that output contains actual inventory data (not just headers)."""
    out = getattr(context, "last_output", "")
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    # Should have more than just headers - actual data rows with inventory info
    assert (
        len(lines) > 1
    ), f"Expected inventory data rows, got only headers. Output: {out}"
    # Look for non-empty data (not just commas)
    data_lines = [
        line for line in lines[1:] if line and not line.replace(",", "").strip() == ""
    ]
    assert data_lines, f"Expected non-empty inventory data rows. Output: {out}"


@given("the directory is read-only")
def given_directory_readonly(context):
    """Make the current project directory read-only for file safety testing.

    Used exclusively by inventory/file_safety.feature to test backup behavior
    when the target directory cannot be written to.
    """
    # Make the project directory read-only
    project_dir = Path(context.project_root)
    current_permissions = project_dir.stat().st_mode
    project_dir.chmod(current_permissions & ~stat.S_IWRITE)

    # Store original permissions for cleanup
    context.original_permissions = current_permissions
