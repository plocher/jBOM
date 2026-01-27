Feature: Seamless KiCad Validation Example
    As a jBOM developer
    I want KiCad validation to work transparently with existing scenario patterns
    So that I don't need "Potemkin scenarios" but still ensure authentic KiCad data

    # Option 1: Environment Variable (Global)
    # Set JBOM_VALIDATE_KICAD=1 to validate all KiCad projects automatically
    # No changes to scenario syntax required

    # Option 2: Background Validation (Feature-Specific)
    Background:
        Given KiCad project validation is enabled
        Given the generic fabricator is selected

    # Your exact pattern - no changes to scenario structure!
    Scenario: Generate basic BOM to stdout (human-readable format)
        Given a schematic that contains:
            | Reference | Value | Footprint            |
            | R1        | 10K   | R_0805_2012          |
            | C1        | 100nF | C_0603_1608          |
            | U1        | LM358 | SOIC-8_3.9x4.9mm    |
        When I run jbom command "bom"  # <-- KiCad validation happens HERE automatically
        Then the output should contain "R1"
        And the output should contain "10K"
        And the output should contain "C1"
        And the output should contain "100nF"
        And the output should contain "U1"
        And the output should contain "LM358"

    # Another example with different validation approach
    Scenario: Generate POS file with table-driven components
        Given a schematic that contains:
            | Reference | Value   | Footprint     |
            | R1        | 1k      | R_0603_1608   |
            | R2        | 10k     | R_0603_1608   |
            | C1        | 22pF    | C_0402_1005   |
        When I run jbom command "pos"  # <-- Validation happens automatically here too
        Then the output should contain position data for the components

    # Option 3: Explicit validation in scenario (if you want to see it explicitly)
    Scenario: Explicit validation with standard pattern
        Given a schematic that contains:
            | Reference | Value | Footprint     |
            | R1        | 47k   | R_0603_1608   |
        When I validate the KiCad project with native tools
        Then KiCad should accept all project files
        When I run jbom command "bom"
        Then the output should contain "47k"

    # Option 4: Disabled validation for development speed
    @no_validation
    Scenario: Fast development iteration without validation
        Given a schematic that contains:
            | Reference | Value | Footprint     |
            | R1        | 100   | R_0603_1608   |
        When I run jbom command "bom"
        Then the output should contain "100"
