# KiCad Validation Integration Guide

This guide shows how to integrate KiCad's native validation tools into jBOM test scenarios to prevent circular testing patterns and ensure authentic test data.

## Problem Statement

Previously, jBOM tests used minimal artificial KiCad content like:
```
(kicad_project (version 1))  # 26 characters - clearly fake
```

This created circular test patterns where we were essentially "testing our mocks" rather than testing against real KiCad behavior.

## Solution: Native KiCad Validation Steps

We now provide Behave steps that use KiCad's own CLI tools to validate test artifacts before feeding them to jBOM.

## Available Validation Steps

### Setup Steps
```gherkin
Given KiCad validation is enabled for this scenario
```
- Ensures KiCad CLI is available
- Skips scenario if KiCad tools aren't found
- Use at the beginning of scenarios requiring validation

### Validation Actions
```gherkin
When I validate the KiCad project with native tools
```
- Runs KiCad ERC (Electrical Rules Check) on schematics
- Runs KiCad DRC (Design Rules Check) on PCBs
- Validates project file structure against real KiCad projects
- Stores detailed results for assertion steps

```gherkin
When I validate the project structure against real KiCad projects
```
- Compares test project structure with real KiCad projects
- Ensures fixtures have authentic KiCad project keys and structure

### Assertion Steps
```gherkin
Then KiCad should accept all project files
```
- Asserts that all KiCad files passed native validation
- Fails with detailed error messages if any files are invalid

```gherkin
Then KiCad ERC should validate the schematic
```
- Specifically asserts schematic files pass ERC validation
- Provides detailed ERC violation information on failure

```gherkin
Then KiCad DRC should validate the PCB
```
- Specifically asserts PCB files pass DRC validation
- Provides detailed DRC violation information on failure

```gherkin
Then KiCad should report 10 or fewer violations
```
- Allows for some violations while ensuring files are substantially valid
- Useful for test circuits that may have intentional unconnected pins

```gherkin
Then the project structure should match real KiCad projects
```
- Asserts project structure matches real KiCad projects
- Prevents structural authenticity issues

## Integration Patterns

### Pattern 1: Validation Gate Before jBOM Processing
```gherkin
Scenario: Validate authenticity before BOM generation
    Given the KiCad fixture "test_project"
    When I validate the KiCad project with native tools
    Then KiCad should accept all project files
    # Now we know our test data is authentic
    When I run jbom with "basic_options.yaml"
    Then the BOM should contain expected components
```

### Pattern 2: Mixed Validation for Robust Testing
```gherkin
Scenario: Comprehensive validation with tolerance
    Given the project contains components:
        | Reference | Value | Footprint   |
        | R1        | 10k   | R_0603_1608 |
        | C1        | 100n  | C_0603_1608 |
    When I validate the KiCad project with native tools
    Then KiCad should accept all project files
    And KiCad should report 5 or fewer violations
    # Proceed knowing we have authentic, reasonably valid KiCad data
    When I run jbom with various configurations
    Then results should reflect real KiCad project behavior
```

### Pattern 3: Structural Authenticity Check
```gherkin
Scenario: Ensure fixtures match real KiCad projects
    Given the KiCad fixture "empty_project"
    When I validate the project structure against real KiCad projects
    Then the project structure should match real KiCad projects
    # This validates our fixtures aren't missing required KiCad keys
```

## Integration Workflow

### For New Test Scenarios
1. **Start with authenticity**: Use `Given KiCad validation is enabled`
2. **Set up test data**: Create project/components as needed
3. **Validate before testing**: `When I validate the KiCad project with native tools`
4. **Assert authenticity**: `Then KiCad should accept all project files`
5. **Proceed with jBOM testing**: Now you know your test data is authentic

### For Existing Test Scenarios
1. **Add validation step** after project setup but before jBOM commands
2. **Choose appropriate assertion** based on test requirements:
   - Strict: `KiCad should accept all project files`
   - Tolerant: `KiCad should report N or fewer violations`
3. **Run tests** to identify any non-authentic fixtures
4. **Fix or replace** invalid fixtures with authentic ones

## Example Integration

### Before (Risky - Could be circular)
```gherkin
Scenario: Test BOM generation
    Given a simple project with components
    When I run jbom with "basic_options.yaml"
    Then the BOM should contain expected components
```

### After (Safe - Validated authenticity)
```gherkin
Scenario: Test BOM generation with authentic KiCad data
    Given KiCad validation is enabled for this scenario
    And a simple project with components
    When I validate the KiCad project with native tools
    Then KiCad should accept all project files
    # Now we're confident our test data is authentic
    When I run jbom with "basic_options.yaml"
    Then the BOM should contain expected components
    And the results should reflect real KiCad project behavior
```

## Validation Results Structure

The validation steps store detailed results in `context.kicad_validation_results`:

```python
{
    'project_files': [
        {
            'file': '/path/to/project.kicad_pro',
            'success': True,
            'message': 'Project structure valid'
        }
    ],
    'schematic_files': [
        {
            'file': '/path/to/schematic.kicad_sch',
            'success': True,
            'message': 'ERC passed',
            'violations': [],
            'raw_output': '{"violations": []}'
        }
    ],
    'pcb_files': [
        {
            'file': '/path/to/board.kicad_pcb',
            'success': False,
            'message': 'DRC failed: 3 violations',
            'violations': [...],
            'raw_output': '{"violations": [...]}'
        }
    ],
    'summary': {'total': 3, 'passed': 2, 'failed': 1},
    'all_passed': False
}
```

## Debugging Validation Issues

Use the debug step to investigate validation problems:

```gherkin
@debug
Scenario: Debug fixture validation
    Given the KiCad fixture "problematic_fixture"
    When I validate the KiCad project with native tools
    And I debug KiCad validation results
    Then KiCad should accept all project files
```

This will print detailed validation results to help identify why fixtures are failing validation.

## Benefits

1. **Prevents Circular Testing**: We test against real KiCad behavior, not our own mocks
2. **Early Problem Detection**: Invalid fixtures caught before they affect jBOM tests
3. **Confidence in Results**: Results reflect actual jBOM behavior with real KiCad files
4. **Continuous Validation**: Ensures fixtures remain authentic over time
5. **Clear Error Messages**: KiCad's own error messages guide fixture improvements

## Tagging Strategy

Use tags to control when validation runs:

```gherkin
@validation @slow
Scenario: Full authenticity validation
    # Comprehensive validation that might be slower

@quick
Scenario: Fast functional test
    # Skip validation for rapid iteration during development
```

Then run subsets as needed:
- `behave --tags @validation` - Run only validation tests
- `behave --tags ~@slow` - Skip slower validation tests during development
- `behave --tags @quick` - Run only fast tests

This validation framework ensures jBOM tests use authentic KiCad data while maintaining development velocity and test reliability.
