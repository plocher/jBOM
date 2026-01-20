"""Step definitions for project-centric fixtures and assertions (Issue #27/24).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from behave import given, when, then
from diagnostic_utils import assert_with_diagnostics


# -------------------------
# Project/fixture Given steps
# -------------------------


@given('a KiCad project directory "{project_name}"')
def given_project_dir(context, project_name: str) -> None:
    p = context.project_root / project_name
    p.mkdir(parents=True, exist_ok=True)


@given('the project contains a file "{filename}" with content:')
def given_project_file_with_docstring(context, filename: str) -> None:
    """Write an arbitrary file content using the feature's docstring."""
    content = context.text or ""
    target = context.project_root / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


@given('the project contains a schematic "{filename}" with components:')
def given_project_schematic_table(context, filename: str) -> None:
    components: List[Dict[str, Any]] = [row.as_dict() for row in (context.table or [])]
    # Reuse BOM helper to render a minimal valid schematic
    from . import bom_steps  # type: ignore

    bom_steps._write_schematic(context, filename, components)


@given('the project contains a PCB "{filename}" with footprints:')
def given_project_pcb_table(context, filename: str) -> None:
    rows: List[Dict[str, Any]] = [row.as_dict() for row in (context.table or [])]
    # Normalize into the POS writer's expected fields
    comps: List[Dict[str, Any]] = []
    for r in rows:
        comps.append(
            {
                "Reference": r.get("reference", r.get("Reference", "U1")),
                "X(mm)": r.get("x", r.get("X", "0")),
                "Y(mm)": r.get("y", r.get("Y", "0")),
                "Rotation": r.get("rotation", r.get("Rotation", "0")),
                "Side": r.get("side", r.get("Side", "TOP")),
                "Footprint": r.get("footprint", r.get("Footprint", "R_0805_2012")),
            }
        )
    from . import pos_steps  # type: ignore

    pos_steps._write_pcb(context, filename, comps)


@given('the main schematic "{main_sch}" references sheet "{child_sch}"')
def given_main_references_child(context, main_sch: str, child_sch: str) -> None:
    # Ensure child exists (empty schematic if not provided elsewhere)
    child_path = context.project_root / child_sch
    if not child_path.exists():
        child_path.write_text("(kicad_sch (version 20211123))\n", encoding="utf-8")

    # Append a sheet reference into main
    main_path = context.project_root / main_sch
    content = """(kicad_sch (version 20211123)
  (sheet (at 50 50) (size 30 20)
    (property "Sheetname" "Child")
    (property "Sheetfile" "{child}")
  )
)
""".format(
        child=child_sch
    )
    main_path.write_text(content, encoding="utf-8")


@when('I am in project directory "{project_name}"')
def when_cd_project(context, project_name: str) -> None:
    new_root = context.project_root / project_name
    assert_with_diagnostics(
        new_root.exists(), "Project directory does not exist", context
    )
    context.project_root = new_root


# -------------------------
# Then assertions
# -------------------------


@then('the BOM output should contain component "{ref}" with value "{value}"')
def then_bom_contains_ref_value(context, ref: str, value: str) -> None:
    out = getattr(context, "last_output", "")
    assert out.strip(), "No BOM output captured"
    assert (
        ref in out and value in out
    ), f"Expected ref {ref} and value {value} in output.\n{out}"


@then('the BOM title should show project name "{name}"')
def then_bom_title_has_name(context, name: str) -> None:
    out = getattr(context, "last_output", "")
    # Heuristic: either header or any output mentions project name
    assert name in out, f"Expected project name '{name}' in output.\n{out}"


@then('the POS output should contain component "{ref}" at position "{x}" x "{y}" y')
def then_pos_contains_component_at(context, ref: str, x: str, y: str) -> None:
    out = getattr(context, "last_output", "")
    assert out.strip(), "No POS output captured"
    # Basic CSV check: ref and x and y present on same line
    for line in out.splitlines():
        if ref in line and x in line and y in line:
            return
    raise AssertionError(f"Expected {ref} at ({x},{y}) not found in output.\n{out}")


@then('the inventory file should contain component with value "{value}"')
def then_inventory_file_contains_value(context, value: str) -> None:
    # Find any .csv created in project_root and scan for value
    csv_files = list(Path(context.project_root).glob("*.csv"))
    assert csv_files, f"No CSV inventory files found under {context.project_root}"
    content = "\n".join(p.read_text(encoding="utf-8") for p in csv_files)
    assert (
        value in content
    ), f"Expected value '{value}' not present in CSV files: {csv_files}"
