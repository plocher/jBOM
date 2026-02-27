# Requirements for Step 4: Back-Annotation

## Problem
Users generate a prototype inventory from their schematic, then manually fill in missing details (LCSC numbers, corrected Values, Packages) in the CSV. These updates are stranded in the CSV. The schematic remains the "incorrect" source. Users need a way to push these corrections back to the KiCad schematic to make it the Single Source of Truth.

## Goals
1.  **UUID Tracking**: Extract and preserve KiCad Symbol UUIDs in the `jBOM` data model and exported inventory CSV.
2.  **Back-Annotation Tool**: Implement a CLI command to update schematic files based on inventory data, matching by UUID.
3.  **Safety**: Ensure schematic updates do not corrupt the file structure.

## Plan

### 4.1. UUID Support
- [ ] Update `Component` class to include `uuid` field.
- [ ] Update `SchematicLoader` to parse `(uuid "...")` tag.
- [ ] Update `ProjectInventoryLoader` to populate `uuid` in `InventoryItem`.
- [ ] Update `InventoryCommand` to include `UUID` column in the output CSV.

### 4.2. Annotator Logic
- [ ] Create `SchematicPatcher` class.
    - Load `.kicad_sch` as S-Expression list.
    - Helper to find symbol node by UUID.
    - Helper to update/add property nodes.
- [ ] Implement `jbom annotate` command.
    - Inputs: Project, Inventory CSV.
    - Logic: Match inventory rows to schematic symbols by UUID. Update Value, Footprint, and properties (e.g., LCSC).

## Verification
- [ ] Unit Test: Load schematic, verify UUID extraction.
- [ ] Unit Test: Patch a schematic S-expression structure in memory.
- [ ] Functional Test:
    1.  Create dummy schematic.
    2.  Generate inventory.
    3.  Modify inventory (add LCSC).
    4.  Run `jbom annotate`.
    5.  Verify schematic file now contains the LCSC property.
