# Features - Gherkin BDD Tests

This directory contains Behavior-Driven Development (BDD) tests using Gherkin syntax. These tests validate user-facing behavior and CLI functionality.

## Test Structure: Hierarchical by Command

Tests are organized hierarchically to mirror the CLI command structure:

```
features/
├── cli_basics.feature          # General CLI behavior
├── bom/                        # jbom bom command tests
│   ├── bom_generation.feature  # Basic BOM generation
│   ├── bom_inventory.feature   # BOM + inventory enhancement
│   └── bom_output.feature      # Output formats & filtering
├── inventory/                  # jbom inventory command tests
│   ├── inventory_generate.feature  # jbom inventory generate
│   └── inventory_list.feature     # jbom inventory list
├── pos/                        # jbom pos command tests
│   ├── pos_generation.feature  # Basic position file generation
│   └── pos_filtering.feature   # Filtering options
└── regression/                 # Cross-cutting regression tests
    └── diagnostic-output-quality.feature
```

## Command-Test Mapping

| CLI Command | Test Location |
|-------------|---------------|
| `jbom --help` | [`cli_basics.feature`](cli_basics.feature) |
| `jbom bom schematic.kicad_sch` | [`bom/bom_generation.feature`](bom/bom_generation.feature) |
| `jbom bom --inventory components.csv` | [`bom/bom_inventory.feature`](bom/bom_inventory.feature) |
| `jbom inventory generate` | [`inventory/inventory_generate.feature`](inventory/inventory_generate.feature) |
| `jbom inventory list` | [`inventory/inventory_list.feature`](inventory/inventory_list.feature) |
| `jbom pos board.kicad_pcb` | [`pos/pos_generation.feature`](pos/pos_generation.feature) |

## Running Tests

### All Tests
```bash
# Run all Gherkin tests
behave

# Run with summary
behave --summary
```

### Command-Specific Tests
```bash
# Test specific command functionality
behave features/bom/
behave features/inventory/
behave features/pos/

# Test specific feature
behave features/bom/bom_generation.feature
```

### Test Configuration
See [`behave.ini`](../behave.ini) for behavior configuration.

## Test Infrastructure

### Environment Setup
- [`environment.py`](environment.py) - Test environment configuration
  - Sets up Python path to include `src/`
  - Initializes test context before scenarios

### Step Definitions
- [`steps/common_steps.py`](steps/common_steps.py) - Common step definitions
  - `When I run "command"` - Execute CLI commands
  - `Then I should see "text"` - Validate output
  - `And the exit code should be 0` - Check return codes
- [`steps/diagnostic_utils.py`](steps/diagnostic_utils.py) - Enhanced error diagnostics

## Writing New Tests

### Adding Tests for Existing Commands
1. Add scenarios to existing feature files in appropriate command directory
2. Use existing step definitions from `steps/common_steps.py`
3. Follow established patterns for Given/When/Then structure

Example:
```gherkin
Scenario: New BOM functionality
  Given a KiCad schematic file "test.kicad_sch" with components:
    | Reference | Value | Footprint   |
    | R1        | 10K   | R_0805_2012 |
  When I run "jbom bom test.kicad_sch --new-option"
  Then the command exits with code 0
  And the output contains "expected result"
```

### Adding Tests for New Commands
1. Create new directory: `features/new-command/`
2. Create feature files following naming pattern: `new_command_functionality.feature`
3. Add step definitions if needed (prefer reusing existing steps)
4. Update this README to document the new command tests

### Feature File Structure
Each feature file follows this structure:
```gherkin
Feature: [Command] [Functionality]
  As a [user type]
  I want to [perform action]
  So that I can [achieve goal]

  Scenario: [Specific behavior description]
    Given [preconditions]
    When I run "jbom command args"
    Then [expected outcomes]
    And [additional validations]
```

## Test Patterns

### File-Based Tests
Tests that work with files follow this pattern:
```gherkin
Given a KiCad schematic file "input.kicad_sch" with components:
  | Reference | Value | Footprint |
  | R1        | 10K   | R_0805    |
When I run "jbom bom input.kicad_sch -o output.csv"
Then the command exits with code 0
And a file named "output.csv" exists
And the file "output.csv" contains valid CSV data
```

### Error Handling Tests
Tests for error conditions:
```gherkin
Scenario: Handle missing input file
  When I run "jbom bom nonexistent.kicad_sch"
  Then the command exits with code 1
  And the error output contains "file not found"
```

### Help and Usage Tests
Tests for command help:
```gherkin
Scenario: Show command help
  When I run "jbom bom --help"
  Then the command exits with code 0
  And the output contains "Generate bill of materials"
```

## BDD vs Unit Testing

### Gherkin Tests (BDD)
- **Purpose**: Validate user-facing behavior
- **Focus**: CLI commands, file I/O, user workflows
- **Audience**: Product owners, users, developers
- **Examples**: "Generate BOM from schematic", "Handle missing files"

### Unit Tests
- **Purpose**: Validate internal service logic
- **Focus**: Business logic, algorithms, edge cases
- **Audience**: Developers
- **Examples**: "BOM aggregation strategies", "Component filtering logic"

Both are valuable and complementary:
- **Gherkin tests** ensure features work as users expect
- **Unit tests** ensure services work correctly in isolation

## Step Definition Reference

Common step definitions available:

### Command Execution
- `When I run "command"` - Execute CLI command
- `When I run "jbom" with no arguments` - Execute without args

### Output Validation
- `Then I should see "text"` - Check output contains text
- `Then I should see usage information` - Validate help output
- `Then the output contains CSV headers "Headers"` - Check CSV format

### Exit Code Validation
- `Then the exit code should be 0` - Success
- `Then the exit code should be non-zero` - Failure
- `Then the command exits with code 1` - Specific code

### File Operations
- `Given a file "name" with content "content"` - Create test file
- `Then a file named "name" exists` - Validate file creation
- `And the file "name" contains valid CSV data` - Validate file content

See [`steps/common_steps.py`](steps/common_steps.py) for complete list and implementation details.
