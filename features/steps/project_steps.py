"""Domain-specific step definitions for project reference testing.

These steps are only used by features/project/ domain and handle:
- Named project creation with KiCad templates
- File manipulation for negative testing
- Project reference resolution testing
"""

from pathlib import Path
from behave import given


@given("a KiCad project")
def given_kicad_project(context):
    """Create a complete empty KiCad project using real template.

    Copies template and renames to 'project' with internal content modification.
    Creates: project.kicad_pro, project.kicad_sch, project.kicad_pcb
    """
    template_path = (
        Path(__file__).parent.parent / "fixtures" / "kicad_templates" / "empty_project"
    )

    # Copy template files
    for template_file in template_path.glob("empty.*"):
        if template_file.suffix in [".kicad_pro", ".kicad_sch", ".kicad_pcb"]:
            # Read template content
            content = template_file.read_text(encoding="utf-8")

            # Replace internal project name references
            content = content.replace("empty", "project")

            # Write to sandbox with new name
            target_file = Path(context.sandbox_root) / f"project{template_file.suffix}"
            target_file.write_text(content, encoding="utf-8")

    context.current_project = "project"


@given("the schematic is deleted")
def given_schematic_deleted(context):
    """Remove the schematic file for negative testing."""
    schematic_file = Path(context.sandbox_root) / "project.kicad_sch"
    if schematic_file.exists():
        schematic_file.unlink()


@given("the PCB is deleted")
def given_pcb_deleted(context):
    """Remove the PCB file for negative testing."""
    pcb_file = Path(context.sandbox_root) / "project.kicad_pcb"
    if pcb_file.exists():
        pcb_file.unlink()
