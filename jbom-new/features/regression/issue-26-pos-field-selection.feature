Feature: Issue #26 - POS Field Selection and Output Control (Regression Canaries)
  As a hardware developer
  I want to control which fields are included in POS output
  So that I can customize placement files for different fabricators and workflows

  # NOTE: These are regression canary scenarios to validate Issue #26 implementation
  #
  # ARCHITECTURE:
  # - Regression canaries (HERE): Core functionality works, fabricator presets work, key error handling
  # - Comprehensive testing (features/pos/fields.feature): Edge cases, integration, all field combinations
  # - This keeps regression focused on "does the feature work" vs "does every edge case work"

  Background:
    Given a jBOM CSV sandbox
    And a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint         | Package      | Value |
      | R1        | 10| 5 | 0        | TOP  | R_0805_2012       | 0805         | 10K   |
      | C1        | 15| 8 | 90       | TOP  | C_0603_1608       | 0603         | 100nF |
      | U1        | 25|12 | 180      | TOP  | SOIC-8_3.9x4.9mm | SOIC-8       | LM358 |

  # Core field selection functionality (REGRESSION CANARIES - these should initially fail)
  Scenario: POS command should support --fields parameter (CANARY - CURRENTLY MISSING)
    When I run jbom command "pos --fields Reference,X,Y,Side"
    Then the command should succeed
    And the output should contain these fields:
      | Reference | X | Y | Side |
    And the output should not contain these fields:
      | Rotation | Footprint | Package |
    And the output should contain these component data rows:
      | R1 | 10.0000 | 5.0000 | TOP |
      | C1 | 15.0000 | 8.0000 | TOP |
      | U1 | 25.0000 | 12.0000 | TOP |

  Scenario: POS command should support fabricator presets like BOM (CANARY - CURRENTLY MISSING)
    When I run jbom command "pos --jlc"
    Then the command should succeed
    And the output should contain these fields:
      | Designator | Mid X | Mid Y | Layer | Rotation | Package |
    And the output should contain these component data rows:
      | R1 | 10.0000 | 5.0000 | TOP | 0.0 | 0805 |

  # Additional field selection patterns

  Scenario: Select minimal fields for basic placement
    When I run jbom command "pos --fields Reference,X,Y,Rotation"
    Then the command should succeed
    And the output should contain these fields:
      | Reference | X | Y | Rotation |
    And the output should not contain these fields:
      | Side | Package |
    And the output should contain these component data rows:
      | R1 | 10.0000 | 5.0000 | 0.0 |
      | C1 | 15.0000 | 8.0000 | 90.0 |

  # Fabricator preset compatibility (TDD - desired behavior)
  Scenario: Generic fabricator preset uses fabricator-specific field names
    When I run jbom command "pos --generic"
    Then the command should succeed
    And the output should contain these fields:
      | Designator | Mid X | Mid Y | Layer | Rotation | Package |
    And the output should contain these component data rows:
      | R1 | 10.0000 | 5.0000 | TOP | 0.0 | 0805 |

  Scenario: JLC fabricator preset uses JLC-specific field names
    When I run jbom command "pos --jlc"
    Then the command should succeed
    And the output should contain these fields:
      | Designator | Mid X | Mid Y | Layer | Rotation | Package |
    And the output should contain these component data rows:
      | R1 | 10.0000 | 5.0000 | TOP | 0.0 | 0805 |

  Scenario: PCBWay fabricator preset for POS
    When I run jbom command "pos --pcbway"
    Then the command should succeed
    And the output should contain the fabricator defined PCBWay POS fields

  Scenario: Seeed fabricator preset for POS
    When I run jbom command "pos --seeed"
    Then the command should succeed
    And the output should contain the fabricator defined Seeed POS fields

  # Fabricator parameter syntax
  Scenario: Using --fabricator parameter with generic
    When I run jbom command "pos --fabricator generic"
    Then the command should succeed
    And the output should contain these fields:
      | Designator | Mid X | Mid Y | Layer | Rotation | Package |

  Scenario: Using --fabricator parameter with JLC
    When I run jbom command "pos --fabricator jlc"
    Then the command should succeed
    And the output should contain these fields:
      | Designator | Mid X | Mid Y | Layer | Rotation | Package |

  # Field addition with + syntax (TDD - desired behavior)
  Scenario: Add field to default field set with + syntax
    When I run jbom command "pos --fields +Value"
    Then the command should succeed
    And the output should contain these fields:
      | Reference | X | Y | Rotation | Side | Footprint | Package | Value |
    And the output should contain these component data rows:
      | R1 | 10.0000 | 5.0000 | 0.0 | TOP | R_0805_2012 | 0805 | 10K |
      | C1 | 15.0000 | 8.0000 | 90.0 | TOP | C_0603_1608 | 0603 | 100nF |

  Scenario: Add fabricator part number field with special alias
    When I run jbom command "pos --fields +fabricator_part_number"
    Then the command should succeed
    And the output should contain these fields:
      | Reference | X | Y | Rotation | Side | Footprint | Package | Fabricator Part Number |
    # fabricator_part_number should be populated from fabricator-specific part number fields

  # Field modification with fabricator presets
  Scenario: Add field to fabricator preset
    When I run jbom command "pos --jlc --fields +Value"
    Then the command should succeed
    And the output should contain these fields:
      | Designator | Mid X | Mid Y | Layer | Rotation | Package | Value |
    And the output should contain these component data rows:
      | U1 | 25.0000 | 12.0000 | TOP | 180.0 | SOIC-8 | LM358 |

  # Output format compatibility (canary - full testing in features/pos/fields.feature)

  # Input validation (TDD - desired error handling behavior)
  Scenario: Invalid field names should be rejected with helpful message
    When I run jbom command "pos --fields Reference,InvalidField,X"
    Then the command should fail
    And the error output should contain "Invalid field: InvalidField"
    And the error output should contain "Available fields:"
    And the error output should list these available fields:
      | Reference | X | Y | Rotation | Side | Footprint | Package | Value |

  Scenario: Empty fields parameter should be rejected
    When I run jbom command "pos --fields ''"
    Then the command should fail
    And the error output should contain "--fields parameter cannot be empty"

  Scenario: Multiple fabricator presets should be rejected
    When I run jbom command "pos --jlc --pcbway"
    Then the command should fail
    And the error output should contain "Cannot specify multiple fabricator presets"

  # Edge cases and integration testing moved to features/pos/fields.feature

  # Documentation canary (comprehensive testing in features/pos/fields.feature)
  Scenario: Help documents field selection options (REGRESSION CANARY)
    When I run jbom command "pos --help"
    Then the command should succeed
    And the help output should contain these options:
      | --fields | Select specific fields for output |
      | --generic | Use Generic preset |
      | --jlc | Use JLC preset |

  # Backward compatibility canary
  Scenario: Default behavior preserved when no field selection specified (REGRESSION CANARY)
    When I run jbom command "pos"
    Then the command should succeed
    # Should maintain current default fields until explicitly changed
