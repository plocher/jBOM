# jBOM Feature Tests - Ultra-Simplified BDD Testing

This directory contains Behavior-Driven Development (BDD) tests using Gherkin syntax for jBOM. The test suite was comprehensively refactored in **Issue #27** to follow consistent, maintainable patterns.

## Testing Philosophy: Ultra-Simplified Patterns

All core functionality tests follow a **standardized ultra-simplified pattern** that prioritizes:
- **Consistency**: Identical structure across all feature areas
- **Maintainability**: Easy to read, write, and debug
- **Functional focus**: Tests validate behavior, not brittle format details

## Test Organization

```
features/
├── README.md              # This file
├── bom/                    # BOM generation and processing
│   ├── core.feature        # Core BOM functionality
│   ├── output.feature      # Output formats and options
│   ├── filtering.feature   # Component filtering (DNP, etc.)
│   ├── aggregation.feature # Component grouping strategies
│   └── ...                 # Additional BOM features
├── pos/                    # Position/placement file generation
│   ├── core.feature        # Core POS functionality
│   ├── filtering.feature   # Component filtering (SMD, layers)
│   ├── generation.feature  # Basic generation scenarios
│   └── ...                 # Additional POS features
├── inventory/              # Inventory management
│   ├── core.feature        # Core inventory functionality
│   ├── generate.feature    # Inventory generation
│   ├── list.feature        # Inventory listing/filtering
│   └── ...                 # Additional inventory features
├── cli/                    # CLI basics (help, version, errors)
│   └── basics.feature      # Basic CLI functionality
├── project/               # KiCad project reference patterns
│   ├── directory.feature   # Directory-based project references
│   ├── file.feature       # File-based project references
│   ├── cross_resolution.feature # Cross-file type resolution
│   └── fixtures/          # Real KiCad project templates
└── regression/             # Cross-cutting regression tests
    └── ...                 # Issue-specific regression tests
```

## Standard Pattern Structure

```gherkin
Feature: [Functionality Description]
  As a [user type]
  I want to [perform action]
  So that I can [achieve goal]

  Background:
    Given the generic fabricator is selected

  Scenario: [Specific behavior]
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "bom [options]"
    Then the command should succeed
    And the output should contain "R1"
```

### Key Pattern Elements

#### 1. **Background**: Consistent sandbox environment setup
All core functionality tests (BOM/POS/Inventory/CLI) use a Background pattern
that sets up a consistent and predictable sandbox environment for the scenerios.
This sandbox uses default jbom behavior as a baseline, with explicit use of the
generic fabricator from the config system.  This allows features to focus on
**their own** nuances, edge cases and key features without having to also work
through the interaction combinatorics with other features.

With this pattern, the `fabricator test.feature` is expected to iterate through
the various fabricators that have been configured and verify that the capabilities
the user expects are indeed functioning correctly.  This lets `all the other.feature`
files depend on `generic` behavior, which is intended to be predictable and stable.

```gherkin
Background:
  Given the generic fabricator is selected
```

##### **DRY Background Pattern** (DESIGN DECISION)
**When to consolidate component setup into Background:**

If a feature file has **3+ scenarios with repetitive component definitions**, consolidate the setup into Background for maximum maintainability:

```gherkin
# BEFORE: Repetitive setup in each scenario
Scenario: Basic functionality
  Given a schematic that contains:
    | Reference | Value | Footprint   |
    | R1        | 10K   | R_0805_2012 |
    | C1        | 100nF | C_0603_1608 |
  When I run jbom command "bom"

Scenario: File output
  Given a schematic that contains:     # DUPLICATE SETUP
    | Reference | Value | Footprint   |
    | R1        | 10K   | R_0805_2012 |
    | C1        | 100nF | C_0603_1608 |
  When I run jbom command "bom -o file.csv"

# AFTER: DRY Background consolidation
Background:
  Given the generic fabricator is selected
  And a standard test schematic that contains:
    | Reference | Value | Footprint   |
    | R1        | 10K   | R_0805_2012 |
    | C1        | 100nF | C_0603_1608 |

Scenario: Basic functionality
  When I run jbom command "bom"          # Clean focus on behavior

Scenario: File output
  When I run jbom command "bom -o file.csv"   # Clean focus on behavior
```

**Benefits of DRY Background Pattern:**
- ✅ **Single source of truth** for test data
- ✅ **Scenarios focus purely on behavior** rather than setup
- ✅ **Easier maintenance** - change test data once, affects all scenarios
- ✅ **Prevents flaky tests** from inconsistent data
- ✅ **Professional Gherkin** following BDD best practices

**Strategic Background Design:**
Design Background components to support multiple test scenarios:

```gherkin
# Good: Rich data supporting multiple test cases
Background:
  And a comprehensive test schematic that contains:
    | Reference | Value | Footprint   |
    | R1        | 10k   | R_0603_1608 |  # Basic component
    | R2        | 22k   | R_0603_1608 |  # Different value
    | R10       | 10k   | R_0805_2012 |  # Natural sorting test
    | C1        | 100nF | C_0603_1608 |  # Different component type
    | LED1      | RED   | LED_0603    |  # Matching test component
    | U1        | LM358 | SOIC-8      |  # Complex component

# Enables multiple scenarios:
# - Basic functionality (uses R1, C1, U1)
# - Component matching (R1 matches, R2 doesn't)
# - Natural sorting (R1 < R2 < R10)
# - Multi-type testing (R, C, LED, U components)
```

#### 2. **Component Definition**: Table-driven, inline component creation
Scenerios should be both minimalist and explicit.  They should follow DRY patterns
so as to not overconstrain or burden the test with unrelated baggage statements,
while at the same time being specific about the details being exercised.

In this example, the scenerio is making sure that the bom feature works with
defaults - that is, with no additional CLI options.

```gherkin
 Scenario: Minimal options, correct behavior
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | C1        | 100nF | C_0603_1608 |
```
All this feature requires is that a KiCad schematic file exists, and that it
contains components.  The `Given` is crafted to provide a KiCad project with
a kicad_sch file in the sandbox directory; the table provided populates the
schematic with two components.

```gherkin
    When I run jbom command "bom"
```
The details of how to execute the jbom command are left to the test framework,
all this scenerio requires is that the `bom` subcommand is invoked in this
specific way.

```gherkin
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "10K"
    And the output should contain "C1"
    And the output should contain "100nF"
```
Finally, the validation `Then` steps are very explicit about what they expect,
that the command does not exit with an error, and the output contains information
about all the components that were placed into the schematic.

This pattern is used throughout jBOM:

For POS tests, use:
```gherkin
Given a PCB that contains:
  | Reference | X | Y | Side | Footprint   |
  | R1        | 10| 5 | TOP  | R_0805_2012 |
```

#### 3. **Command Execution**: Standardized jBOM command invocation
```gherkin
When I run jbom command "bom [options]"
When I run jbom command "pos --smd-only -o console"
When I run jbom command "inventory generate -o inventory.csv"
```

#### 4. **Assertions**: Functional behavior validation (not format-specific)
```gherkin
Then the command should succeed          # or should fail
And the output should contain "R1"       # Component presence
And the output should contain "10K"      # Value presence
And the output should not contain "R2"   # Exclusion testing
And a file named "output.csv" should exist
And the file "output.csv" should contain "R1"
```

## Benefits of Ultra-Simplified Pattern

### **Consistency**
- Identical structure across all feature areas
- No guessing about how to write new tests
- Easy to maintain and extend

### **Robustness**
- Tests focus on **functional behavior** instead of **brittle format details**
- Example: `output should contain "R1"` vs `output should contain "R1,10K,0805,1"`
- Less likely to break from minor output formatting changes

### **Maintainability**
- Clear separation between feature-specific testing and a predictable environment with other features
- Reduced cognitive load when reading/writing tests
- The use of `Background` supports the DRY design pattern


## Anti-Patterns to Avoid

### **Don't test fragile format details**
```gherkin
# BAD - Brittle CSV format assertion
Then the output should contain "\"R1, R2\",10K,R_0805_2012,2"

# GOOD - Functional behavior assertion
Then the output should contain "R1"
And the output should contain "R2"
And the output should contain "10K"
```

### **Don't over-apply DRY Background pattern**
```gherkin
# BAD - Using Background when scenarios need different component setups
Background:
  And a schematic that contains:
    | Reference | Value | Footprint |
    | R1        | 10K   | 0805      |

Scenario: Test with capacitor  # Needs capacitor, not resistor!
  When I run jbom command "bom"
  Then the output should contain "C1"  # Will fail - no C1 in Background

# GOOD - Use individual Given when scenarios have different needs
Scenario: Test with resistor
  Given a schematic that contains:
    | Reference | Value | Footprint |
    | R1        | 10K   | 0805      |
  When I run jbom command "bom"

Scenario: Test with capacitor
  Given a schematic that contains:
    | Reference | Value | Footprint |
    | C1        | 100nF | 0603      |
  When I run jbom command "bom"
```

**Rule of thumb:** Use DRY Background when scenarios share 80%+ of component setup. Otherwise, keep individual `Given` clauses for clarity.

## Running Tests

```bash
# All tests
behave

# Specific feature area
behave features/bom/
behave features/pos/
behave features/inventory/

# Specific feature file
behave features/bom/core.feature

# With verbose output
behave --no-capture

# Dry run to check syntax
behave --dry-run
```

## Available Step Definitions

### Core Steps (Ultra-Simplified Pattern)
- `Given the generic fabricator is selected` - Standard background
- `Given a schematic that contains:` - Table-driven component creation
- `Given a PCB that contains:` - Table-driven PCB component creation
- `When I run jbom command "[args]"` - Command execution
- `Then the command should succeed` / `should fail` - Exit code validation
- `And the output should contain "[text]"` - Output content validation
- `And the output should not contain "[text]"` - Exclusion validation
- `And a file named "[filename]" should exist` - File creation validation
- `And the file "[filename]" should contain "[text]"` - File content validation


See [`steps/common_steps.py`](steps/common_steps.py) for complete implementation.

## 🎯 Test Categories

### **Core Functionality** (Ultra-Simplified Pattern)
- **Purpose**: Validate primary user workflows
- **Pattern**: Background + table components + canonical assertions
- **Examples**: Generate BOM, filter components, output formats

### **Architecture Testing** (Complex Setup)
- **Purpose**: Validate project discovery, file resolution, cross-command behavior
- **Pattern**: Fixtures + specialized steps
- **Examples**: Hierarchical projects, legacy .pro support, path resolution

### **CLI Testing** (Simplified Pattern)
- **Purpose**: Validate command-line interface behavior
- **Pattern**: Direct command execution + output validation
- **Examples**: Help text, version info, error handling
