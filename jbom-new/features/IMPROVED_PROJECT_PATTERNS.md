# Improved KiCad Project Creation Patterns

## Problems with Old Patterns

❌ **Ambiguous "basic content" patterns:**
```gherkin
Given a KiCad project directory "test_project"
And the project contains a file "test_project.kicad_pro"
And the project contains a file "test_project.kicad_sch" with basic schematic content
And the project contains a file "test_project.kicad_pcb" with basic PCB content
```

**Issues:**
- "basic schematic content" and "basic PCB content" are magic strings
- Verbose repetition in every scenario
- Not clear what components are actually created
- Manual file specification is error-prone

## New Improved Patterns

### ✅ Pattern 1: Minimal Project (no specific components needed)
```gherkin
Given a minimal KiCad project "test_project"
```
**Creates:**
- `test_project/test_project.kicad_pro` (empty project)
- `test_project/test_project.kicad_sch` (empty schematic)
- `test_project/test_project.kicad_pcb` (empty PCB)
- Sets context to project directory

### ✅ Pattern 2: Explicit Component Data (when components matter)
```gherkin
Given a KiCad project "test_project" with files:
  | File                     | Reference | Value | Footprint     |
  | test_project.kicad_pro   |           |       |               |
  | test_project.kicad_sch   | R1        | 10K   | R_0805_2012   |
  | test_project.kicad_pcb   | R1        |       | R_0805_2012   |
```
**Creates:**
- Project files with explicit component data
- Clear what components exist for testing
- Table-driven, extensible for multiple components

## Migration Example

### Before (verbose, ambiguous):
```gherkin
Scenario: BOM command discovers project files
  Given a KiCad project directory "test_project"
  And the project contains a file "test_project.kicad_pro"
  And the project contains a file "test_project.kicad_sch" with basic schematic content
  And I am in directory "test_project"
  When I run jbom command "bom . -v"
  Then the command should succeed
```

### After (concise, explicit):
```gherkin
Scenario: BOM command discovers project files
  Given a minimal KiCad project "test_project"
  And I am in directory "test_project"
  When I run jbom command "bom . -v"
  Then the command should succeed
```

**Benefits:**
- 60% fewer lines
- Clear intent (project discovery, not component testing)
- No ambiguous magic strings
- Consistent project naming
