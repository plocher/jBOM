"""Step definitions for project-centric fixtures and assertions (Issue #27/24).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from behave import given, then


def _write_schematic_local(
    context, filename: str, components: List[Dict[str, Any]]
) -> None:
    """Write a minimal KiCad schematic file with the provided components.

    Components accept keys: Reference, Value, Footprint, LibID (optional).
    """
    # Use project_placement_dir if available (for projects placed in subdirectories)
    # Otherwise use project_root (for projects in current directory)
    base_dir = getattr(context, "project_placement_dir", context.project_root)
    p = Path(base_dir) / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    symbols = []
    x = 50
    for row in components:
        ref = row.get("Reference", "U1")
        val = row.get("Value", "VAL")
        fp = row.get("Footprint", "")
        lib = row.get("LibID", "Device:Generic")
        dnp = row.get("DNP", "No")
        exclude_from_bom = row.get("ExcludeFromBOM", "No")

        # Build symbol with base properties
        symbol_parts = [f'(symbol (lib_id "{lib}") (at {x} 50 0) (unit 1)']

        # Add DNP and in_bom flags at symbol level if needed
        if dnp.lower() in ["yes", "true", "1"]:
            symbol_parts.append("(dnp yes)")
        if exclude_from_bom.lower() in ["yes", "true", "1"]:
            symbol_parts.append("(in_bom no)")

        # Add properties
        symbol_parts.extend(
            [
                f'(property "Reference" "{ref}" (id 0) (at {x+2} 48 0))',
                f'(property "Value" "{val}" (id 1) (at {x+2} 52 0))',
                f'(property "Footprint" "{fp}" (id 2) (at {x+2} 54 0))',
            ]
        )

        symbol_lines = [f"  {part}" for part in symbol_parts] + ["  )"]
        symbols.append("\n".join(symbol_lines))
        x += 20
    content = """(kicad_sch (version 20211123) (generator eeschema)
  (paper "A4")
{symbols}
)
""".replace(
        "{symbols}", "\n".join(symbols)
    )
    p.write_text(content, encoding="utf-8")


# -------------------------
# Simplified constructors - most tests use ultra-simplified steps below
# Keep minimal set for edge cases that need explicit project/directory control
# -------------------------


@given('a project "{project}" placed in "{dir}"')
def given_project_in_dir(context, project: str, dir: str) -> None:
    """Create a minimal KiCad project under sandbox/<dir> (no cwd change).

    Only use this for tests that specifically need directory resolution testing.
    Most tests should use 'Given a schematic that contains:' instead.
    """
    base = Path(context.sandbox_root)
    target = (base / dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{project}.kicad_pro").write_text(
        "(kicad_project (version 1))\n", encoding="utf-8"
    )
    context.current_project = project
    context.project_placement_dir = target


@given('the schematic "{name}" contains:')
def given_named_schematic_contains(context, name: str) -> None:
    """Write components into <name>.kicad_sch (for hierarchical/multi-schematic tests).

    Only use this for tests that need specific schematic names.
    Most tests should use 'Given a schematic that contains:' instead.
    """
    comps: List[Dict[str, Any]] = [row.as_dict() for row in (context.table or [])]
    filename = f"{name}.kicad_sch" if not name.endswith(".kicad_sch") else name
    _write_schematic_local(context, filename, comps)


@given('the project uses a root schematic "{root}" that contains:')
def given_root_schematic_contains(context, root: str) -> None:
    """Create root schematic named <root> with components from the table."""
    comps: List[Dict[str, Any]] = [row.as_dict() for row in (context.table or [])]
    filename = f"{root}.kicad_sch"
    _write_schematic_local(context, filename, comps)


@given('the root references child schematic "{child}"')
def given_root_references_child(context, child: str) -> None:
    """Append a child sheet reference from <root> to <child>."""
    root = getattr(context, "current_project", None) or "project"
    base_dir = getattr(context, "project_placement_dir", context.project_root)
    main_path = Path(base_dir) / f"{root}.kicad_sch"
    child_file = f"{child}.kicad_sch"
    # Ensure main exists
    if not main_path.exists():
        main_path.write_text("(kicad_sch (version 20211123))\n", encoding="utf-8")
    content = f"""(kicad_sch (version 20211123)
  (sheet (at 50 50) (size 30 20)
    (property "Sheetname" "{child}")
    (property "Sheetfile" "{child_file}")
  )
)
"""
    main_path.write_text(content, encoding="utf-8")


@given('the child schematic "{child}" contains:')
def given_child_contains(context, child: str) -> None:
    comps: List[Dict[str, Any]] = [row.as_dict() for row in (context.table or [])]
    filename = f"{child}.kicad_sch"
    _write_schematic_local(context, filename, comps)


# -------------------------
# Ultra-simplified DRY steps for maximum simplicity
# -------------------------


@given("a schematic that contains:")
def given_simple_schematic(context) -> None:
    """Create a default project with schematic containing the specified components.

    Uses default project name and places in current test workspace.
    Most BOM/POS tests don't care about the specific project name.
    """
    # Create minimal project file
    project_name = "project"  # Default name
    proj_dir = Path(context.project_root)
    (proj_dir / f"{project_name}.kicad_pro").write_text(
        "(kicad_project (version 1))\n", encoding="utf-8"
    )

    # Create schematic with components
    comps: List[Dict[str, Any]] = [row.as_dict() for row in (context.table or [])]
    filename = f"{project_name}.kicad_sch"
    _write_schematic_local(context, filename, comps)

    context.current_project = project_name


@given("a PCB that contains:")
def given_simple_pcb(context) -> None:
    """Create a default project with PCB containing the specified footprints.

    Uses default project name and places in current test workspace.
    Most POS tests don't care about the specific project name.
    """
    # Create minimal project file
    project_name = "project"  # Default name
    proj_dir = Path(context.project_root)
    (proj_dir / f"{project_name}.kicad_pro").write_text(
        "(kicad_project (version 1))\n", encoding="utf-8"
    )

    # Create PCB with footprints
    rows: List[Dict[str, Any]] = [row.as_dict() for row in (context.table or [])]
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
                "Value": r.get("value", r.get("Value", "")),
                "Package": r.get("package", r.get("Package", "")),
                "SMD": r.get("smd", r.get("SMD", "")),
            }
        )
    # Write PCB file directly to avoid import issues
    pcb_file = Path(context.project_root) / f"{project_name}.kicad_pcb"
    footprints = []
    for comp in comps:
        ref = comp["Reference"]
        x = comp["X(mm)"]
        y = comp["Y(mm)"]
        rotation = comp["Rotation"]
        side = comp["Side"]
        footprint = comp["Footprint"]
        value = comp.get("Value", "")
        package = comp.get("Package", "")
        # Map TOP/BOTTOM to KiCad layer names
        layer = "F.Cu" if side == "TOP" else "B.Cu"

        # Use explicit SMD data from table if provided, otherwise apply useful heuristics
        smd_value = comp.get("SMD", "").upper()
        if smd_value in ["SMD", "TRUE", "1"]:
            attr = "(attr smd)"
        elif smd_value in ["PTH", "THROUGH_HOLE", "FALSE", "0"]:
            attr = "(attr through_hole)"
        else:
            # Apply heuristics for real-world footprint patterns (useful for actual usage)
            smd_patterns = [
                "_0603_",
                "_0805_",
                "_1206_",
                "_SOT",
                "_SOIC",
                "_QFN",
                "_BGA",
                "_LGA",
            ]
            through_hole_patterns = ["_Axial_", "_Radial_", "_DIP", "_TO-"]

            attr = "(attr smd)"  # Default assumption
            for pattern in smd_patterns:
                if pattern in footprint:
                    attr = "(attr smd)"
                    break
            for pattern in through_hole_patterns:
                if pattern in footprint:
                    attr = "(attr through_hole)"
                    break

        # Build properties list
        properties = [f'(property "Reference" "{ref}")']
        if value:
            properties.append(f'(property "Value" "{value}")')
        if package:
            properties.append(f'(property "Package" "{package}")')

        properties_str = "\n    ".join(properties)

        # Always include attr since we always determine one (explicit or heuristic)
        footprints.append(
            f'  (footprint "{footprint}" (at {x} {y} {rotation}) (layer "{layer}")\n    {properties_str}\n    {attr}\n  )'
        )

    pcb_content = f"""(kicad_pcb (version 20211014) (generator pcbnew)
  (paper "A4")
{chr(10).join(footprints)}
)
"""
    pcb_file.write_text(pcb_content, encoding="utf-8")

    context.current_project = project_name


@given("the generic fabricator is selected")
def given_generic_fabricator(context) -> None:
    """Set context to use generic fabricator for BOM commands.

    This makes the fabricator selection explicit in Background sections
    rather than having it as a hidden side effect in command execution.
    """
    context.fabricator = "generic"


@given('a KiCad project directory "{name}"')
def given_kicad_project_directory(context, name: str) -> None:
    """Create a KiCad project directory for external testing (without changing cwd).

    Use this for project discovery testing where commands need to reference
    the project directory from outside. Complements 'I am in project directory'
    which changes the working context to inside the directory.

    Part of the Layer 3 testing architecture.
    """
    project_dir = Path(context.project_root) / name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Update context to use this as the working directory
    context.project_root = project_dir
    context.current_project = name


@given('a KiCad project "{name}" with files:')
def given_kicad_project_with_files(context, name: str) -> None:
    """Create a complete KiCad project with specified files and components.

    Uses table data to create project files with explicit component content.
    Replaces ambiguous 'with basic content' patterns with explicit data tables.

    Example:
        Given a KiCad project "test_project" with files:
          | File                     | Component | Reference | Value | Footprint     |
          | test_project.kicad_pro   |           |           |       |               |
          | test_project.kicad_sch   | Resistor  | R1        | 10K   | R_0805_2012   |
          | test_project.kicad_pcb   | Footprint | R1        |       | R_0805_2012   |
    """
    project_dir = Path(context.project_root) / name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Update context
    context.project_root = project_dir
    context.current_project = name

    # Process table to create files
    if context.table:
        files_created = set()
        for row in context.table:
            filename = row.get("File") or row.get("file")
            if not filename:
                continue

            file_path = project_dir / filename

            # Create each file only once
            if filename not in files_created:
                if filename.endswith(".kicad_pro"):
                    file_path.write_text(
                        "(kicad_project (version 1))\n", encoding="utf-8"
                    )
                elif filename.endswith(".kicad_sch"):
                    # Create schematic with component if specified
                    ref = row.get("Reference") or row.get("reference") or "R1"
                    value = row.get("Value") or row.get("value") or "10K"
                    footprint = (
                        row.get("Footprint") or row.get("footprint") or "R_0805_2012"
                    )

                    content = f"""(kicad_sch (version 20211123) (generator eeschema)
  (paper "A4")
  (symbol (lib_id "Device:R") (at 50 50 0) (unit 1)
    (property "Reference" "{ref}" (id 0) (at 52 48 0))
    (property "Value" "{value}" (id 1) (at 52 52 0))
    (property "Footprint" "{footprint}" (id 2) (at 52 54 0))
  )
)
"""
                    file_path.write_text(content, encoding="utf-8")
                elif filename.endswith(".kicad_pcb"):
                    # Create PCB with footprint if specified
                    ref = row.get("Reference") or row.get("reference") or "R1"
                    footprint = (
                        row.get("Footprint") or row.get("footprint") or "R_0805_2012"
                    )

                    content = f"""(kicad_pcb (version 20211014) (generator pcbnew)
  (paper "A4")
  (footprint "{footprint}" (at 76.2 104.14 0) (layer "F.Cu")
    (property "Reference" "{ref}")
  )
)
"""
                    file_path.write_text(content, encoding="utf-8")
                else:
                    file_path.write_text("", encoding="utf-8")

                files_created.add(filename)


@given('a minimal KiCad project "{name}"')
def given_minimal_kicad_project(context, name: str) -> None:
    """Create a minimal KiCad project with empty .pro, .sch, .pcb files.

    Use this for project discovery testing that doesn't need specific component data.
    Creates standard project files with minimal but valid content.
    """
    project_dir = Path(context.project_root) / name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Update context
    context.project_root = project_dir
    context.current_project = name

    # Create minimal project files
    (project_dir / f"{name}.kicad_pro").write_text(
        "(kicad_project (version 1))\n", encoding="utf-8"
    )
    (project_dir / f"{name}.kicad_sch").write_text(
        "(kicad_sch (version 20211123) (generator eeschema))\n", encoding="utf-8"
    )
    (project_dir / f"{name}.kicad_pcb").write_text(
        "(kicad_pcb (version 20211014) (generator pcbnew))\n", encoding="utf-8"
    )


@given('the project contains a file "{filename}"')
def given_project_contains_file(context, filename: str) -> None:
    """Create minimal KiCad project file with appropriate content.

    Automatically generates proper content for .kicad_pro, .kicad_sch, .kicad_pcb files.
    Used for project discovery and architecture testing.
    """
    file_path = Path(context.project_root) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if filename.endswith(".kicad_pro"):
        file_path.write_text("(kicad_project (version 1))\n", encoding="utf-8")
    elif filename.endswith(".kicad_sch"):
        file_path.write_text(
            "(kicad_sch (version 20211123) (generator eeschema))\n", encoding="utf-8"
        )
    elif filename.endswith(".kicad_pcb"):
        file_path.write_text(
            "(kicad_pcb (version 20211014) (generator pcbnew))\n", encoding="utf-8"
        )
    else:
        file_path.write_text("", encoding="utf-8")


@given('the project contains a file "{filename}" with basic schematic content')
def given_project_file_basic_schematic(context, filename: str) -> None:
    """Create schematic file with basic component for testing.

    Contains a simple R1 10K resistor component for project discovery testing.
    """
    file_path = Path(context.project_root) / filename
    content = """(kicad_sch (version 20211123) (generator eeschema)
  (paper "A4")
  (symbol (lib_id "Device:R") (at 50 50 0) (unit 1)
    (property "Reference" "R1" (id 0) (at 52 48 0))
    (property "Value" "10K" (id 1) (at 52 52 0))
    (property "Footprint" "R_0805_2012" (id 2) (at 52 54 0))
  )
)
"""
    file_path.write_text(content, encoding="utf-8")


@given('the project contains a file "{filename}" with basic PCB content')
def given_project_file_basic_pcb(context, filename: str) -> None:
    """Create PCB file with basic footprint for testing.

    Contains a simple R1 footprint at known coordinates for project discovery testing.
    """
    file_path = Path(context.project_root) / filename
    content = """(kicad_pcb (version 20211014) (generator pcbnew)
  (paper "A4")
  (footprint "R_0805_2012" (at 76.2 104.14 0) (layer "F.Cu")
    (property "Reference" "R1")
  )
)
"""
    file_path.write_text(content, encoding="utf-8")


# -------------------------
# Legacy compatibility steps removed - use ultra-simplified pattern:
# - Given a schematic that contains: (replaces all schematic creation steps)
# - Given a PCB that contains: (replaces all PCB creation steps)
# - Given the generic fabricator is selected (replaces fabricator management)
# -------------------------


# -------------------------
# Then assertions (artifact-based)
# -------------------------


@then('the BOM output should contain component "{ref}" with value "{value}"')
def then_bom_contains_ref_value(context, ref: str, value: str) -> None:
    out = getattr(context, "last_output", "")
    assert out.strip(), "No BOM output captured"
    assert (
        ref in out and value in out
    ), f"Expected ref {ref} and value {value} in output.\n{out}"


@then('the POS output should contain component "{ref}" at position "{x}" x "{y}" y')
def then_pos_contains_component_at(context, ref: str, x: str, y: str) -> None:
    out = getattr(context, "last_output", "")
    assert out.strip(), "No POS output captured"
    for line in out.splitlines():
        if ref in line and x in line and y in line:
            return
    raise AssertionError(f"Expected {ref} at ({x},{y}) not found in output.\n{out}")


@then('the inventory file should contain component with value "{value}"')
def then_inventory_file_contains_value(context, value: str) -> None:
    csv_files = list(Path(context.project_root).glob("*.csv"))
    assert csv_files, f"No CSV inventory files found under {context.project_root}"
    content = "\n".join(p.read_text(encoding="utf-8") for p in csv_files)
    assert (
        value in content
    ), f"Expected value '{value}' not present in CSV files: {csv_files}"
