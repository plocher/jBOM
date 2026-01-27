Feature: Enhanced KiCad Validation Diagnostics
    As a jBOM developer
    I want comprehensive diagnostic information when KiCad validation fails
    So that I can quickly identify and fix validation issues

    Background:
        Given KiCad project validation is enabled
        Given the generic fabricator is selected

    @diagnostic_demo
    Scenario: Comprehensive diagnostics for validation failures
        # This scenario will intentionally create fake KiCad content
        # to demonstrate the enhanced diagnostic output
        Given a KiCad sandbox
        When I run jbom command "bom"
        # This should fail with comprehensive diagnostics showing:
        # - Project file inventory
        # - Detailed validation results
        # - KiCad CLI diagnostics
        # - Resolution guidance
        # - Standard execution context
        Then the output should contain "BOM generation successful"

    @diagnostic_demo @expected_pass
    Scenario: Enhanced diagnostics with authentic KiCad project
        Given the KiCad fixture "empty_project"
        When I run jbom command "bom"
        # This should pass validation but still collect diagnostic data
        Then the output should contain expected BOM content

    @diagnostic_demo @trace
    Scenario: Trace-enabled diagnostics for maximum detail
        Given a schematic that contains:
            | Reference | Value | Footprint     |
            | R1        | 10K   | R_0603_1608   |
        When I run jbom command "bom"
        # With @trace tag, this provides maximum diagnostic detail
        # including file trees, validation results, and execution context
        Then the output should contain "R1"
        And the output should contain "10K"
