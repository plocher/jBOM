# Recipe for Well-Crafted jBOM Gherkin Features

*Working document - evolved during legacy step cleanup*

## Background Layer Architecture

| GIVEN | Purpose | Use Cases |
|-------|---------|-----------|
| `Given a sandbox` | Isolated sandbox directory, no KiCad project | Project discovery edge cases, malformed project testing |
| `Given a KiCad sandbox` | Sandbox + empty KiCad project, no command defaults | Command behavior testing, explicit output format testing |
| `Given a jBOM CSV sandbox` | Sandbox + project + CSV output (`-o -`), uses jBOM's intrinsic defaults | Most business logic testing and fabricator functionality (95% of scenarios) |

## Anti-Patterns Discovered

### 1. DRY Violations
```gherkin
# ❌ BAD: Redundant specification
Background:
  Given a jBOM CSV sandbox    # Already adds -o -
Scenario: Test BOM
  When I run jbom command "bom -o -"  # Repeats defaults!
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

### 5. Verbose Scenario Project Setup
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

### 6. Intentional Test Failures (Diagnostic Anti-Pattern)
```gherkin
# ❌ BAD: Tests designed to fail for manual inspection
Scenario: Check diagnostic output quality
  When I run "jbom --version"
  Then I should see "INTENTIONALLY_WRONG_TEXT"  # Always fails!
  # Requires human to manually verify diagnostic output is "good enough"

# ✅ GOOD: Automated diagnostic validation
Scenario: Test failures provide comprehensive diagnostic context
  When a test fails looking for missing content
  Then I should receive detailed diagnostic information
  And the diagnostic should include the command that was executed
  And the diagnostic should show the exit code
  And the diagnostic should show expected vs actual comparison
  And the diagnostic should be clearly labeled
```

### 7. Component Filtering DRY Violations
```gherkin
# ❌ BAD: Each command implementing inconsistent filtering
# Leads to different flag names and behavior per command
# BOM: --exclude-dnp, --include-virtual
# Parts: --no-dnp, --with-power
# POS: --skip-dnp, --all-components

# ✅ GOOD: Consistent filtering flags across ALL commands
When I run jbom command "bom --include-all"
When I run jbom command "parts --include-all"
When I run jbom command "pos --include-all"
# All commands support: --include-dnp, --include-excluded, --include-all
```

### 8. Premature Data Filtering
```gherkin
# ❌ BAD: Data loading stage filters before user control
# (SchematicReader excluded virtual symbols before user filtering could apply)
# Result: --include-all flag doesn't work for virtual symbols

# ✅ GOOD: Load ALL data, filter at user control stage
# Virtual symbols (#PWR01, #PWR02) loaded, then filtered based on user flags
Given a schematic that contains:
  | Reference | Value | Footprint   |
  | R1        | 10K   | R_0805_2012 |
  | #PWR01    | GND   |             |
  | #PWR02    | VCC   |             |
When I run jbom command "parts --include-all"
Then the CSV output has rows where:
  | Reference | Value |
  | R1        | 10K   |
  | #PWR01    | GND   |
  | #PWR02    | VCC   |
```
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
- Intentional test failures → Use automated diagnostic validation
- Inconsistent component filtering → Use unified filtering flags

### Legacy Project Setup
- `"with basic schematic content"` → Use explicit table data or minimal project
- `"with basic PCB content"` → Use explicit component specifications
- Multi-step manual file creation → Use `"Given a minimal KiCad project"`
- Ambiguous magic strings → Use table-driven component data

**Architectural Issue**: Creating hand-crafted KiCad files that mirror jBOM expectations creates circular validation - proving the validator can read files the validator created.

**Proper Solution**:
1. Use actual KiCad to generate real project files
2. Save them as fixtures in `fixtures/` directory
3. Copy fixture files for test scenarios
4. Tests real-world compatibility, not circular validation

## Command Execution Architecture

### CSV Sandbox Auto-Enhancement

Note: POS outputs mm only and echoes numeric tokens exactly as authored in the PCB. Do not expect step-side formatting or tolerance. If a scenario needs inches, convert in fixtures before authoring; POS will not convert units.
```python
@when('I run jbom command "{command}"')
def step_run_jbom_command(context, command):
    # Anti-pattern detection
    if hasattr(context, 'default_output') and '-o' in command:
        raise AssertionError("DRY VIOLATION: jBOM CSV sandbox + explicit -o")

    # Add CSV output default
    if hasattr(context, 'default_output'):
        command += f" {context.default_output}"
    # Note: No fabricator hardcoding - jBOM uses intrinsic defaults
```

## Discovered Transformation Patterns

1. **Background Consolidation**: Most features → jBOM CSV sandbox
2. **Command Simplification**: Remove redundant flags when using jBOM CSV sandbox
3. **Assertion Focus**: Content over format
4. **Project Setup**: Explicit component tables over implicit "minimal" data
5. **Step Colocation**: Single-feature steps belong in feature-specific files, not shared locations
6. **Legacy Elimination**: 44% reduction (50→25 steps) through unused removal and canonical migration
7. **Trailing Space Handling**: Scenario outline edge cases require explicit whitespace pattern handling
8. **Streamlined Project Creation**: Replace verbose multi-step patterns with parameterized single steps
9. **Eliminate Magic Strings**: Replace ambiguous "basic content" with explicit table data
10. **Table-Based Field Validation**: Replace repetitive individual field assertions with reusable table patterns

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
- **100% test success**: Eliminated false failures from intentional diagnostic test failures
- **Component filtering unification**: Consistent filtering flags across all CLI commands
- **Diagnostic test quality**: Infrastructure tests now validate diagnostic output automatically

## Critical Discovery: Scenario Outline Edge Cases
Trailing whitespace in step patterns from scenario outlines requires explicit handling:
```python
@when('I run jbom command "{command}" ')  # Note trailing space
def when_run_jbom_command_trailing_space(context, command):
    common_steps.step_run_jbom_command(context, command.strip())
```

## Empty Project Testing Pattern
When testing "empty project" scenarios, ensure ALL project artifacts are emptied, not just one:
```gherkin
# ❌ BAD: Only empties schematic, PCB/inventory still populated from Background
Scenario: All commands handle empty projects gracefully
  Given a schematic that contains:
    | Reference | Value | Footprint |
  When I run jbom command "pos"  # Still finds PCB components!

# ✅ GOOD: Empties all project artifacts for consistent "empty" state
Scenario: All commands handle empty projects gracefully
  Given a schematic that contains:
    | Reference | Value | Footprint |
  And a PCB that contains:
    | Reference | X | Y | Side |
  And an inventory file "test_inventory.csv" that contains:
    | IPN | Category | Value | Description | Package |
  # Now all commands see truly empty project
```

## Infrastructure Testing Meta-Patterns (NEW)

### Pattern Discovery (Issues #32/#47)
During test infrastructure improvements, we discovered that tests can and should validate their own infrastructure quality automatically, rather than requiring manual inspection or intentional failures.

### Controlled Failure Pattern
```gherkin
# Test the test infrastructure by simulating test failures
# and validating that diagnostic output is complete and helpful
Scenario: Test failures provide comprehensive diagnostic context
  When a test fails looking for missing content
  Then I should receive detailed diagnostic information
  And the diagnostic should include the command that was executed
  And the diagnostic should show the exit code
  And the diagnostic should show the actual output
  And the diagnostic should show expected vs actual comparison
  And the diagnostic should include working directory context
  And the diagnostic should be clearly labeled
```

### Available Diagnostic Testing Steps (diagnostic_steps.py)
#### When Steps (Test Failure Simulation)
- `When a test fails looking for missing content`
- `When a test fails with an invalid command`

#### Then Steps (Diagnostic Validation)
- `Then I should receive detailed diagnostic information`
- `Then the diagnostic should include the command that was executed`
- `Then the diagnostic should show the exit code`
- `Then the diagnostic should show the actual output`
- `Then the diagnostic should show expected vs actual comparison`
- `Then the diagnostic should include working directory context`
- `Then the diagnostic should be clearly labeled`
- `Then the diagnostic should show the actual error output`
- `Then the diagnostic should contain "{text}"` (for specific content validation)

### Benefits of Infrastructure Testing
1. **Automated validation**: No manual inspection required
2. **Regression detection**: Changes to diagnostic output automatically caught
3. **CI/CD friendly**: Tests PASS when infrastructure works, FAIL when broken
4. **Self-documenting**: Test failures show exactly what diagnostic content is missing
5. **Quality assurance**: Ensures test infrastructure provides helpful debugging information

### When to Use Diagnostic Testing
- ✅ **Testing diagnostic output quality** after assertion failures
- ✅ **Validating error message completeness** and helpfulness
- ✅ **Ensuring test infrastructure reliability** across different failure modes
- ✅ **Meta-testing**: Testing that tests provide good debugging information
- ❌ **Regular business logic testing** - use standard assertion patterns
- ❌ **Performance testing** - diagnostic overhead not suitable

## Table-Based Field Validation Meta Pattern (NEW)

### Pattern Introduction
Added during Issue #26 (POS field selection) to eliminate repetitive field validation across BOM, POS, and inventory commands.

### Before: Repetitive Field Validation Anti-Pattern
```gherkin
# ❌ BAD: Individual field assertions (repetitive, hard to maintain)
Then the output should contain "References,Value,Footprint,Quantity"
And the output should contain "R1,10.0000,5.0000,TOP"
And the output should contain "C1,15.0000,8.0000,TOP"
And the output should not contain "Rotation"
And the output should not contain "Package"
```

### After: Table-Based Field Validation
```gherkin
# ✅ GOOD: Clean table-driven field validation
Then the output should contain these fields:
  | Reference | X(mm) | Y(mm) | Side |
And the output should not contain these fields:
  | Rotation | Footprint | Package |
And the output should contain these component data rows:
  | R1 | 10.0000 | 5.0000 | TOP |
  | C1 | 15.0000 | 8.0000 | TOP |
```

### Available Table-Based Steps (common_steps.py)

#### Field Header Validation
- `Then the output should contain these fields:` - Verify CSV headers exist
- `Then the output should not contain these fields:` - Verify CSV headers absent

#### Data Content Validation
- `Then the output should contain these component data rows:` - Verify CSV data rows

#### Help/Error Output Validation
- `Then the help output should contain these options:` - Verify help option documentation
- `Then the error output should list these available fields:` - Verify error field suggestions

#### Fabricator-Specific Validation
- `Then the output should contain the fabricator defined {fabricator_name} POS fields` - Placeholder for fabricator-specific fields

### Usage Guidelines

#### When to Use Table Patterns
- ✅ **Field validation** across multiple commands (BOM, POS, inventory)
- ✅ **Data row validation** for component/part listings
- ✅ **Help text validation** for CLI option documentation
- ✅ **Error message validation** with suggested alternatives

#### When NOT to Use Table Patterns
- ❌ **Single field checks** - use simple `Then the output should contain "field"`
- ❌ **Complex business logic** - use domain-specific step definitions
- ❌ **Format validation** - focus on business value, not output format

### Maintenance Benefits
1. **DRY Principle**: Eliminates repetitive field validation across features
2. **Readability**: Tables are easier to scan than multiple individual assertions
3. **Maintainability**: Easy to add/modify expected fields without step definition changes
4. **Reusability**: Same patterns work across BOM, POS, inventory, and future commands
5. **Consistency**: Uniform validation approach across the entire jBOM test suite

### Migration Strategy
Existing features can migrate incrementally:
1. **New features**: Use table patterns from start
2. **Regression testing**: Use table patterns for field-heavy scenarios
3. **Legacy features**: Migrate when touching existing field validation scenarios
4. **No breaking changes**: Old individual assertion steps remain supported

---

*This document evolved through systematic legacy step cleanup (2024) + table-based field validation patterns (2026) + infrastructure testing meta-patterns and component filtering unification (2026)*
