# Project-Centric Migration Notes

Summary
jBOM now treats a KiCad project (directory + .kicad_pro/.pro + .kicad_sch/.kicad_pcb) as the primary unit. Commands accept project directories and base names in addition to explicit files.

Examples
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

Behavior
- Automatic project discovery: identifies .kicad_pro/.pro, .kicad_sch, .kicad_pcb
- Hierarchical schematics: resolves main + sheet files
- Backward compatibility: explicit .kicad_sch/.kicad_pcb still supported

Notes
- Verbose (-v) output reports both remediation action and success (e.g., “found matching schematic …”).
- Errors suggest next steps (e.g., missing files and expected names).
