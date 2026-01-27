Feature: KiCad Authenticity Validation
    As a jBOM developer
    I want to ensure our test fixtures are authentic KiCad files
    So that I can trust our test results and avoid circular test patterns

    Background:
        Given KiCad validation is enabled for this scenario

    Scenario: Validate fixture authenticity before jBOM processing
        Given the KiCad fixture "empty_project"
        When I validate the KiCad project with native tools
        Then KiCad should accept all project files
        And KiCad ERC should validate the schematic
        # Note: PCB validation might fail for empty fixtures - that's expected
        When I run jbom with "basic_options.yaml"
        Then jbom should process the project successfully
        And the output should reflect real KiCad project behavior

    @validation
    Scenario: Ensure test artifacts are authentic before jBOM commands
        Given I have a project directory "test_validation"
        And the project contains a schematic with components:
            | Reference | Value | Footprint    |
            | R1        | 10k   | R_0603_1608  |
            | C1        | 100n  | C_0603_1608  |
        When I validate the KiCad project with native tools
        Then KiCad should accept all project files
        And KiCad ERC should validate the schematic
        And KiCad should report 10 or fewer violations
        # Now we know our test data is authentic - proceed with jBOM testing
        When I run jbom with "basic_options.yaml"
        Then the BOM should contain:
            | Reference | Value | Footprint    |
            | R1        | 10k   | R_0603_1608  |
            | C1        | 100n  | C_0603_1608  |

    Scenario: Compare test project structure with real KiCad projects
        Given the KiCad fixture "empty_project"
        When I validate the project structure against real KiCad projects
        Then the project structure should match real KiCad projects
        # This ensures our fixtures have the same structure as real KiCad projects

    @debug
    Scenario: Debug validation results for fixture improvement
        Given the KiCad fixture "empty_project"
        When I validate the KiCad project with native tools
        And I debug KiCad validation results
        Then KiCad should accept all project files

    # This scenario would fail if we had fake/invalid KiCad content
    Scenario Outline: Validate multiple fixture types
        Given the KiCad fixture "<fixture_name>"
        When I validate the KiCad project with native tools
        Then KiCad should accept all project files

        Examples:
            | fixture_name    |
            | empty_project   |
            | project_only    |
            | schematic_only  |
