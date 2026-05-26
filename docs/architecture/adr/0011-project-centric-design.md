# ADR 0011: Project-Centric Design
Date: 2026-02-25
Status: Accepted

## Context
jBOM now treats a KiCad project (directory + .kicad_pro/.pro + .kicad_sch/.kicad_pcb) as the primary unit. Commands accept project directories and base names in addition to explicit files.

`features/project/README.md` is a related requirements source for the project-centric interface described in this decision.

## Decision

### Examples
- Current directory
  - jbom bom . -o console
  - jbom pos . -o console
- Project directory
  - jbom bom myproj/ -o console
  - jbom pos myproj/ -o console
- Base name (from project dir)
  - jbom bom myproj -o console
  - jbom pos myproj -o console
- Cross-file intelligence
  - jbom bom board.kicad_pcb -o console -v   # finds matching schematic and reports: found matching schematic board.kicad_sch
  - jbom pos board.kicad_sch -o console -v   # finds matching PCB and reports: found matching PCB board.kicad_pcb

### Behavior
- Automatic project discovery: identifies .kicad_pro/.pro, .kicad_sch, .kicad_pcb
- Hierarchical schematics: resolves main + sheet files
- Backward compatibility: explicit .kicad_sch/.kicad_pcb still supported

## Consequences
- Verbose (-v) output reports both remediation action and success (e.g., "found matching schematic …").
- Errors suggest next steps (e.g., missing files and expected names).

## Provenance

Normalized into formal ADR format on 2026-05-25 under issue #300.
Source file(s):

- `docs/dev/architecture/project-centric-design.md` (content preserved verbatim)
