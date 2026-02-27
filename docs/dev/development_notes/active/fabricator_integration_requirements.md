# Requirements: Step 6 - Fabricator Integration

## Overview
We have successfully implemented the core enablers for multi-fabricator support:
*   **Federated Inventory**: Ability to load inventory from any source.
*   **Search**: Ability to find parts from Mouser (and others in future).
*   **Fabricator Abstraction**: Ability to generate fabricator-specific BOMs (POC: PCBWay).

Now we must formalize this into a cohesive "Fabrication Integration" strategy (Path B - Evolution) that replaces the need for `kicad-jlcpcb-tools` by offering a superior, generalized workflow.

## Goal
Transform `jbom` into a "Fabrication Platform" that can:
1.  **Select Fabricator**: User chooses target (JLC, PCBWay, Seeed).
2.  **Generate All Artifacts**: BOM + CPL + Gerbers (via `kicad-cli`).
3.  **Package**: Zip everything into a ready-to-upload archive.

## Key Requirements

### 1. Unified `fab` Command
*   New CLI command: `jbom fab [project] --fabricator [name]`
*   Or `jbom fabricator [name] [project]`?
*   Should orchestrate the entire flow:
    1.  Validate Schematic/Inventory (BOM check).
    2.  Generate Gerbers (requires `kicad-cli` integration).
    3.  Generate BOM (CSV).
    4.  Generate CPL (POS).
    5.  Zip it up.

### 2. Gerber Generation Integration
*   Integrate with `kicad-cli pcb export gerbers` and `drill`.
*   Abstract the flags needed for each fabricator (e.g., JLC needs Protel filename extensions, PCBWay might differ).
*   **Constraint**: Must rely on `kicad-cli` (v7/v8/v9), avoiding the fragile internal Python API for plotting if possible.

### 3. Fabricator Configuration
*   Formalize the `Fabricator` class (Step 3.5 POC) into a robust plugin system.
*   Each Fabricator defines:
    *   BOM Column Mapping (Done).
    *   CPL Format (Rotation rules, offsets - partially done).
    *   Gerber/Drill naming conventions (New).
    *   Packaging rules (Zip structure).

### 4. User Workflow
1.  **Design**: KiCad Schematic + Generic Symbols.
2.  **Inventory**: `jbom search` -> `inventory.csv`.
3.  **Annotate**: `jbom annotate` (optional, for LCSC/Electrical props).
4.  **Fabricate**: `jbom fab --target jlc` -> `project_jlc_production.zip`.

## Next Steps (Implementation Plan)
1.  **Prototype `fab` command**: Just wrapping the existing BOM/POS generation + Zip.
2.  **Integrate `kicad-cli`**: Add a `GerberGenerator` class that subprocesses out to KiCad.
3.  **Fabricator Config**: Define the "Gerber Rules" for JLC vs PCBWay.
