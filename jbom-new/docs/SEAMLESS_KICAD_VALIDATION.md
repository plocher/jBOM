# Seamless KiCad Validation Integration

This guide shows how to validate KiCad projects **without changing your existing scenario structure**. No "Potemkin scenarios" required!

## The Problem

Your existing test pattern creates components from tables:

```gherkin
Background:
    Given the generic fabricator is selected

Scenario: Generate basic BOM to stdout (human-readable format)
    Given a schematic that contains:
        | Reference | Value | Footprint            |
        | R1        | 10K   | R_0805_2012          |
        | C1        | 100nF | C_0603_1608          |
        | U1        | LM358 | SOIC-8_3.9x4.9mm    |
    When I run jbom command "bom"  # ← How do we know this KiCad project is valid?
    Then the output should contain expected results
```

**Question**: How do we validate the KiCad project before `jbom` processes it, without creating separate "Potemkin validation scenarios"?

## The Solution: Transparent Validation Hooks

The framework automatically intercepts jBOM commands and validates KiCad projects **before** they reach jBOM. Multiple activation options provide flexibility.

### Option 1: Environment Variable (Global Validation)

Enable validation for **all** jBOM tests:

```bash
export JBOM_VALIDATE_KICAD=1
behave  # All scenarios now validate KiCad projects automatically
```

Your scenarios require **zero changes**:

```gherkin
Background:
    Given the generic fabricator is selected

Scenario: Generate basic BOM to stdout (human-readable format)
    Given a schematic that contains:
        | Reference | Value | Footprint            |
        | R1        | 10K   | R_0805_2012          |
        | C1        | 100nF | C_0603_1608          |
        | U1        | LM358 | SOIC-8_3.9x4.9mm    |
    When I run jbom command "bom"  # ← KiCad validation happens HERE automatically
    Then the output should contain "R1"
```

### Option 2: Background Validation (Feature-Specific)

Enable validation for specific features by adding **one line** to Background:

```gherkin
Background:
    Given KiCad project validation is enabled  # ← Add this line
    Given the generic fabricator is selected

Scenario: Generate basic BOM to stdout (human-readable format)
    Given a schematic that contains:
        | Reference | Value | Footprint            |
        | R1        | 10K   | R_0805_2012          |
        | C1        | 100nF | C_0603_1608          |
        | U1        | LM358 | SOIC-8_3.9x4.9mm    |
    When I run jbom command "bom"  # ← KiCad validation happens automatically
    Then the output should contain "R1"
```

### Option 3: Explicit Validation (Visible in Scenario)

If you want to **see** the validation in your scenario:

```gherkin
Scenario: Generate BOM with explicit validation
    Given a schematic that contains:
        | Reference | Value | Footprint     |
        | R1        | 10K   | R_0805_2012   |
    When I validate the KiCad project with native tools
    Then KiCad should accept all project files
    When I run jbom command "bom"
    Then the output should contain "R1"
```

### Option 4: Tag-Based Control

Use tags to control validation per scenario:

```gherkin
@validated
Scenario: Critical scenario with validation
    Given a schematic that contains:
        | Reference | Value | Footprint     |
        | R1        | 10K   | R_0805_2012   |
    When I run jbom command "bom"
    Then the output should contain "R1"

@no_validation @quick
Scenario: Fast development iteration
    Given a schematic that contains:
        | Reference | Value | Footprint     |
        | R1        | 100   | R_0603_1608   |
    When I run jbom command "bom"
    Then the output should contain "100"
```

Then run specific subsets:
```bash
behave --tags @validated    # Only validated scenarios
behave --tags @quick        # Fast scenarios without validation
```

## How It Works

### Automatic Interception

The validation framework **automatically intercepts** these step types:
- `When I run jbom command "bom"`
- `When I run "jbom bom ..."`
- Any jBOM command that processes KiCad files (`bom`, `pos`, `cpl`)

### Validation Process

Before the jBOM command runs, the framework:
1. **Detects** if validation is enabled (env var, context, or explicit steps)
2. **Locates** the KiCad project directory
3. **Validates** using KiCad's native CLI tools:
   - **Project structure** against real KiCad projects
   - **ERC** (Electrical Rules Check) for schematics
   - **DRC** (Design Rules Check) for PCBs
4. **Passes** or **fails** the scenario based on validation results

### What Validation Catches

```
KiCad project validation failed before running jBOM command 'bom':
KiCad validation failed:
Project project.kicad_pro: Missing required keys: {'erc', 'libraries'}
Schematic project.kicad_sch: KiCad ERC error - Invalid file format

This ensures jBOM receives authentic KiCad files, not fake test content.
To disable validation: unset JBOM_VALIDATE_KICAD environment variable.
To fix: ensure project files are authentic KiCad-generated content.
```

## Integration Strategies

### For New Features

Add validation to Background for comprehensive coverage:

```gherkin
Feature: Component Aggregation
    Background:
        Given KiCad project validation is enabled
        Given the generic fabricator is selected

    # All scenarios in this feature now have automatic validation
    Scenario: Aggregate resistors
        Given a schematic that contains:
            | Reference | Value | Footprint     |
            | R1        | 10K   | R_0603_1608   |
            | R2        | 10K   | R_0603_1608   |
        When I run jbom command "bom"
        Then resistors should be aggregated
```

### For Existing Features

**Minimal Impact Approach**: Add environment variable validation
```bash
# In CI/CD or development environment
export JBOM_VALIDATE_KICAD=1
behave features/existing_feature.feature
```

**Selective Approach**: Add Background validation to critical features
```gherkin
# Add one line to existing Background
Background:
    Given KiCad project validation is enabled  # ← Add this
    Given the generic fabricator is selected
```

### For Development Workflow

```bash
# During active development (fast iteration)
behave features/my_feature.feature

# Before committing (thorough validation)
export JBOM_VALIDATE_KICAD=1
behave features/my_feature.feature

# CI/CD (always validate)
export JBOM_VALIDATE_KICAD=1
behave --tags ~@no_validation
```

## Configuration Options

### Environment Variables

- `JBOM_VALIDATE_KICAD=1` - Enable validation globally
- `JBOM_VALIDATE_KICAD=true` - Alternative enable syntax
- `JBOM_VALIDATE_KICAD=0` - Explicitly disable (default)

### Context Attributes

The validation framework checks these context attributes:
- `context.validate_kicad` - Set by Background step
- `context.kicad_validation_enabled` - Set by explicit validation steps

### KiCad CLI Path

The framework looks for KiCad CLI at:
```
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
```

If not found, validation is **silently skipped** (tests continue).

## Benefits

### 1. No Scenario Changes Required
Your existing test patterns work unchanged. Validation happens transparently.

### 2. Prevents Circular Testing
KiCad's own tools validate authenticity, not our test mocks.

### 3. Early Problem Detection
Invalid KiCad content caught before jBOM processing.

### 4. Flexible Control
Multiple activation methods for different development phases.

### 5. Clear Error Messages
KiCad's native error messages guide fixture improvements.

### 6. Development Friendly
Can disable validation for fast iteration, enable for thorough testing.

## Error Examples

### Fake Project Structure
```
KiCad project validation failed:
Project project.kicad_pro: Missing required keys: {'erc', 'libraries', 'cvpcb'}
```

### Invalid Schematic Content
```
KiCad project validation failed:
Schematic project.kicad_sch: KiCad ERC error - Parse error at line 1
```

### Malformed PCB File
```
KiCad project validation failed:
PCB project.kicad_pcb: KiCad DRC error - Invalid file format
```

## Troubleshooting

### Validation Not Running
1. Check environment variable: `echo $JBOM_VALIDATE_KICAD`
2. Verify Background step: `Given KiCad project validation is enabled`
3. Check KiCad CLI availability: `ls /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`

### KiCad CLI Not Found
Validation silently skips if KiCad CLI unavailable. Install KiCad or run without validation.

### Too Many Violations
Use tolerant validation:
```gherkin
When I validate the KiCad project with native tools
Then KiCad should report 10 or fewer violations  # Allow some violations
```

### Performance Impact
Validation adds ~1-2 seconds per scenario. Disable for rapid development:
```bash
unset JBOM_VALIDATE_KICAD  # Fast development mode
```

## Migration Guide

### Step 1: Test Current Features
```bash
export JBOM_VALIDATE_KICAD=1
behave features/your_feature.feature
```

### Step 2: Fix Validation Failures
Replace fake KiCad content with authentic fixtures.

### Step 3: Enable Selectively
Add Background validation to critical features.

### Step 4: CI/CD Integration
```bash
# In CI pipeline
export JBOM_VALIDATE_KICAD=1
behave --tags ~@no_validation
```

This approach gives you authentic KiCad validation **without "Potemkin scenarios"** while maintaining your existing test patterns and development workflow.
