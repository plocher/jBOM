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

---

*This document evolves as we discover more patterns during legacy step cleanup*
