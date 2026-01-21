# jBOM Feature Tests - Ultra-Simplified BDD Testing

This directory contains Behavior-Driven Development (BDD) tests using Gherkin syntax for jBOM. The test suite was comprehensively refactored in **Issue #27** to follow consistent, maintainable patterns.

## 🎯 Testing Philosophy: Ultra-Simplified Patterns

All core functionality tests follow a **standardized ultra-simplified pattern** that prioritizes:
- **Consistency**: Identical structure across all feature areas
- **Maintainability**: Easy to read, write, and debug
- **Functional focus**: Tests validate behavior, not brittle format details

## 📁 Test Organization

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
├── project_centric/        # Complex project discovery & resolution
│   ├── fixtures/           # Test project files (ONLY for architecture testing)
│   ├── architecture.feature # Project discovery and resolution
│   ├── hierarchical.feature # Multi-schematic projects
│   └── ...                 # Complex architectural scenarios
└── regression/             # Cross-cutting regression tests
    └── ...                 # Issue-specific regression tests
```

## 🔧 Ultra-Simplified Pattern (Issue #27)

### Standard Pattern Structure
All core functionality tests (BOM/POS/Inventory/CLI) use this identical pattern:

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
      | C1        | 100nF | C_0603_1608 |
    When I run jbom command "bom [options]"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "10K"
```

### Key Pattern Elements

#### 1. **Background**: Consistent fabricator selection
```gherkin
Background:
  Given the generic fabricator is selected
```

#### 2. **Component Definition**: Table-driven, inline component creation
```gherkin
Given a schematic that contains:
  | Reference | Value | Footprint   |
  | R1        | 10K   | R_0805_2012 |
```

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

## ✅ Benefits of Ultra-Simplified Pattern

### **Consistency**
- Identical structure across all feature areas
- No guessing about how to write new tests
- Easy to maintain and extend

### **Robustness**
- Tests focus on **functional behavior** instead of **brittle format details**
- Example: `output should contain "R1"` vs `output should contain "R1,10K,0805,1"`
- Less likely to break from minor output formatting changes

### **Maintainability**
- Clear separation between simple component testing and complex architecture testing
- Reduced cognitive load when reading/writing tests
- Consistent Background setup eliminates repetition

### **Developer Experience**
- New contributors can easily follow established patterns
- Canonical assertion steps reduce duplication
- Enhanced error diagnostics when tests fail

## 🏗️ Writing New Tests

### For Core Functionality (BOM/POS/Inventory)
**Always use the ultra-simplified pattern:**

```gherkin
Feature: New BOM Feature
  As a hardware developer
  I want to [new functionality]
  So that I can [benefit]

  Background:
    Given the generic fabricator is selected

  Scenario: [Specific test case]
    Given a schematic that contains:
      | Reference | Value | Footprint |
      | [components for this test]
    When I run jbom command "[command with options]"
    Then the command should succeed
    And the output should contain "[expected component or value]"
```

### For CLI Functionality
Use the same pattern but focus on CLI behavior:

```gherkin
Scenario: Show help
  When I run jbom command "--help"
  Then the command should succeed
  And the output should contain "usage:"
```

### For Complex Architecture Testing
Only use fixtures and complex setup for legitimate architectural concerns:
- Project discovery and resolution
- Cross-command intelligence (BOM finding PCB files)
- Hierarchical schematic processing
- Legacy file format support

## 🚫 Anti-Patterns to Avoid

### ❌ **Don't use fixtures for simple component testing**
```gherkin
# BAD - Unnecessarily complex
Given the sample fixtures under "features/fixtures/kicad_samples"
When I run jbom command "bom flat_project"

# GOOD - Simple and direct
Given a schematic that contains:
  | Reference | Value |
  | R1        | 10K   |
When I run jbom command "bom"
```

### ❌ **Don't test fragile format details**
```gherkin
# BAD - Brittle CSV format assertion
Then the output should contain "\"R1, R2\",10K,R_0805_2012,2"

# GOOD - Functional behavior assertion
Then the output should contain "R1"
And the output should contain "R2"
And the output should contain "10K"
```

### ❌ **Don't create duplicate scenarios**
All duplicate feature files were removed in Issue #27. Each scenario should test a distinct aspect of functionality.

## 🧪 Running Tests

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

## 📚 Available Step Definitions

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

### Legacy Steps (Project-Centric Only)
- `Given the sample fixtures under "[path]"` - Complex project setup
- `Given a KiCad project directory "[name]"` - Project directory creation
- `And the project contains a file "[name]" with content` - File creation with content

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

## 🔄 Migration Notes (Issue #27)

The test suite was comprehensively refactored to achieve:
- ✅ **Consistency**: All core features use identical patterns
- ✅ **Organization**: Logical directory structure, no redundant file names
- ✅ **Quality**: Functional vs format testing, better assertions
- ✅ **Maintainability**: Clear patterns, comprehensive documentation

**For developers**: All new tests should follow the ultra-simplified pattern unless testing complex architectural behavior that genuinely requires fixtures.
