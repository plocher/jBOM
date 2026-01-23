# Recipe for Well-Crafted jBOM Gherkin Features

*Working document - evolved during legacy step cleanup*

## Background Layer Architecture

### Layer 1: Pure Sandbox
```gherkin
Background:
  Given a test environment
```
**Purpose**: Isolated sandbox directory, no KiCad project
**Use cases**: Project discovery edge cases, malformed project testing

### Layer 2: Default jBOM Environment
```gherkin
Background:
  Given a default jBOM environment
```
**Purpose**: Sandbox + empty KiCad project, no command defaults
**Use cases**: Command behavior testing, explicit output format testing

### Layer 3: CSV Testing Environment
```gherkin
Background:
  Given a default jBOM CSV environment
```
**Purpose**: Sandbox + project + standardized I/O (`-o -`, `--fabricator generic`)
**Use cases**: Most business logic testing (95% of scenarios)

## Anti-Patterns Discovered

### 1. DRY Violations in Layer 3
```gherkin
# ❌ BAD: Redundant specification
Background:
  Given a default jBOM CSV environment    # Already adds -o - and --fabricator generic
Scenario: Test BOM
  When I run jbom command "bom -o - --fabricator generic"  # Repeats defaults!
```

### 2. Format Obsession
```gherkin
# ❌ BAD: Testing implementation details
Then the output should be in CSV format
Then the output should contain a formatted table

# ✅ GOOD: Testing business value
Then the output should contain component "R1" with value "10K"
```

### 3. Implicit Project State
```gherkin
# ❌ BAD: Undefined BOM reference
When I run jbom command "bom"
Then the BOM should contain component "R1"    # Which BOM? Where?

# ✅ GOOD: Explicit output testing
When I run jbom command "bom -o -"
Then the CSV should contain "R1,10K"
```

### 4. Legacy Semantic Coupling
```gherkin
# ❌ BAD: Step names imply business logic
Given a primary inventory file "..." with contents:
Given a secondary inventory file "..." with contents:

# ✅ GOOD: Neutral, data-focused
Given an inventory file "A.csv" with contents:
Given an inventory file "B.csv" with contents:
```

### 5. Verbose Project Setup Anti-Patterns
```gherkin
# ❌ BAD: Manual file specification with magic strings
Given a KiCad project directory "test_project"
And the project contains a file "test_project.kicad_pro"
And the project contains a file "test_project.kicad_sch" with basic schematic content
And the project contains a file "test_project.kicad_pcb" with basic PCB content

# ✅ GOOD: Streamlined with clear intent
Given a minimal KiCad project "test_project"

# ✅ GOOD: Explicit component data when needed
Given a KiCad project "test_project" with files:
  | File                   | Reference | Value | Footprint   |
  | test_project.kicad_sch | R1        | 10K   | R_0805_2012 |
  | test_project.kicad_pcb | R1        |       | R_0805_2012 |
```

## Patterns to Eliminate

### Legacy Command Variations
- `"I run jbom with"` → Use `"I run jbom command"`
- `"the fabricator is set to"` → Use Background layer defaults

### Legacy Project Setup
- `"an empty schematic"` → Use `"a schematic that contains:"` with empty table
- `"a minimal schematic"` → Use explicit component data in scenarios
- `"a test workspace"` → Use Background layers

### Legacy Assertions
- `"the output contains BOM headers"` → Test actual data content
- `"the BOM contains"` → Test specific CSV output
- Format checking steps → Focus on business value

### Legacy Project Setup
- `"with basic schematic content"` → Use explicit table data or minimal project
- `"with basic PCB content"` → Use explicit component specifications
- Multi-step manual file creation → Use `"Given a minimal KiCad project"`
- Ambiguous magic strings → Use table-driven component data

### Circular Validation Anti-Pattern
```gherkin
# ❌ BAD: Hand-crafted files that mirror jBOM expectations
Given the project contains a file "test.kicad_sch" with content:
  """
  (kicad_sch (version 20211123)
    (symbol (lib_id "Device:R") (at 50 50 0) (unit 1)
      (property "Reference" "R1" (id 0) (at 52 48 0))
      (property "Value" "10K" (id 1) (at 52 52 0))
    )
  )
  """

# ✅ GOOD: Use fixture-based approach with real KiCad files
Given I copy fixture "fixtures/real_kicad_project" to "test_project"
And I am in directory "test_project"
```

**Architectural Issue**: Creating hand-crafted KiCad files that mirror jBOM expectations creates circular validation - proving the validator can read files the validator created.

**Proper Solution**:
1. Use actual KiCad to generate real project files
2. Save them as fixtures in `fixtures/` directory
3. Copy fixture files for test scenarios
4. Tests real-world compatibility, not circular validation

## Command Execution Architecture

### Layer 3 Auto-Enhancement
```python
@when('I run jbom command "{command}"')
def step_run_jbom_command(context, command):
    # Anti-pattern detection
    if hasattr(context, 'default_output') and '-o' in command:
        raise AssertionError("DRY VIOLATION: Layer 3 background + explicit -o")

    # Add Layer 3 defaults
    if hasattr(context, 'default_output'):
        command += f" {context.default_output}"
    if hasattr(context, 'default_fabricator'):
        command += f" {context.default_fabricator}"
```

## Discovered Transformation Patterns

1. **Background Consolidation**: Most features → Layer 3
2. **Command Simplification**: Remove redundant flags when using Layer 3
3. **Assertion Focus**: Content over format
4. **Project Setup**: Explicit component tables over implicit "minimal" data
5. **Step Colocation**: Single-feature steps belong in feature-specific files, not shared locations
6. **Legacy Elimination**: 44% reduction (50→25 steps) through unused removal and canonical migration
7. **Trailing Space Handling**: Scenario outline edge cases require explicit whitespace pattern handling
8. **Streamlined Project Creation**: Replace verbose multi-step patterns with parameterized single steps
9. **Eliminate Magic Strings**: Replace ambiguous "basic content" with explicit table data

## Legacy Step Cleanup Methodology

### Phase-Based Approach
1. **Usage Analysis**: Systematic search for step patterns in all .feature files
2. **Categorization**: Unused vs. transformable vs. architecturally legitimate
3. **Safe Removal**: Delete completely unused steps after verification
4. **Canonical Migration**: Move legitimate patterns to appropriate step files
5. **Feature Transformation**: Convert legacy step usage to canonical patterns
6. **Verification**: Maintain 0 undefined steps throughout process

### Success Metrics
- **50→25 steps** (44% reduction in legacy technical debt)
- **Zero undefined steps** maintained throughout cleanup
- **Architectural clarity** through Background layer consolidation
- **DRY principle** enforcement via anti-pattern detection

### Critical Discovery: Scenario Outline Edge Cases
Trailing whitespace in step patterns from scenario outlines requires explicit handling:
```python
@when('I run jbom command "{command}" ')  # Note trailing space
def when_run_jbom_command_trailing_space(context, command):
    common_steps.step_run_jbom_command(context, command.strip())
```

---

*This document evolved through systematic legacy step cleanup (2024)*
