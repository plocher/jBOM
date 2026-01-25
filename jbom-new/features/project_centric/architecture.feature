Feature: Project Discovery Architecture
  As a KiCad user
  I want jBOM to correctly discover project files from various input types
  So that I can use natural KiCad workflows and get clear errors when things go wrong

  Background:
    Given a sandbox

  # Positive cases - jBOM works correctly when used properly

  Scenario: Discover project from current directory
    Given a project "test" placed in "."
    And the schematic "test" contains:
      | Reference | Value | Footprint     | LibID    |
      | R1        | 10K   | R_0805_2012   | Device:R |
    And the generic fabricator is selected
    When I run jbom command "bom ."
    Then the command should succeed
    And the output should contain the following messages:
      | message_type | content |
      | info | test - Bill of Materials |

  Scenario: Discover project from project directory name
    Given a project "named_project" placed in "named_project"
    And the schematic "named_project" contains:
      | Reference | Value | Footprint     | LibID    |
      | R1        | 10K   | R_0805_2012   | Device:R |
    And the generic fabricator is selected
    When I run jbom command "bom named_project"
    Then the command should succeed
    And the output should contain the following messages:
      | message_type | content |
      | info | named_project - Bill of Materials |

  Scenario: Discover project from explicit schematic file
    Given a project "explicit_sch" placed in "explicit_sch"
    And the schematic "explicit_sch" contains:
      | Reference | Value | Footprint     | LibID    |
      | R1        | 10K   | R_0805_2012   | Device:R |
    And the generic fabricator is selected
    When I run jbom command "bom explicit_sch/explicit_sch.kicad_sch"
    Then the command should succeed
    And the output should contain the following messages:
      | message_type | content |
      | info | explicit_sch - Bill of Materials |

  Scenario: Discover project from explicit PCB file
    Given a project "explicit_pcb" placed in "explicit_pcb"
    And a PCB "explicit_pcb" contains:
      | Reference | X(mm) | Y(mm) | Rotation | Side | Footprint     |
      | R1        | 76.2  | 104.1 | 0        | TOP  | R_0805_2012   |
    When I run jbom command "pos explicit_pcb/explicit_pcb.kicad_pcb"
    Then the command should succeed
    And the output should contain the following messages:
      | message_type | content |
      | info | Component Placement Data |

  Scenario: Discover project from project file
    Given a project "from_pro_file" placed in "from_pro_file"
    And the schematic "from_pro_file" contains:
      | Reference | Value | Footprint     | LibID    |
      | R1        | 10K   | R_0805_2012   | Device:R |
    And the generic fabricator is selected
    When I run jbom command "bom from_pro_file/from_pro_file.kicad_pro"
    Then the command should succeed
    And the output should contain the following messages:
      | message_type | content |
      | info | from_pro_file - Bill of Materials |

  # Negative cases - jBOM fails correctly when used improperly

  Scenario: Directory does not exist
    When I run jbom command "bom nonexistent_directory"
    Then the command should fail
    And the error output should contain the following messages:
      | message_type | content |
      | error | Path does not exist |

  Scenario: File does not exist
    When I run jbom command "bom nonexistent_file.kicad_sch"
    Then the command should fail
    And the error output should contain the following messages:
      | message_type | content |
      | error | No schematic file found |

  Scenario: Empty directory has no project files
    Given a KiCad project directory "empty_dir"
    When I run jbom command "bom empty_dir"
    Then the command should fail
    And the error output should contain the following messages:
      | message_type | content |
      | error | No project files found |

  Scenario: Multiple project files in directory
    Given a project "first" placed in "multi_project"
    And a project "second" placed in "multi_project"
    When I run jbom command "bom multi_project"
    Then the command should fail
    And the error output should contain the following messages:
      | message_type | content |
      | error | No schematic file found |

  Scenario: Derived schematic file missing
    Given a project "missing_sch" placed in "missing_sch"
    And the generic fabricator is selected
    When I run jbom command "bom missing_sch"
    Then the command should fail
    And the error output should contain the following messages:
      | message_type | content |
      | error | No schematic file found |

  Scenario: Derived PCB file missing
    Given a project "missing_pcb" placed in "missing_pcb"
    When I run jbom command "pos missing_pcb"
    Then the command should fail
    And the error output should contain the following messages:
      | message_type | content |
      | error | No PCB file found |

  # TODO: Additional discovery scenarios to implement:
  # - Hierarchical schematic discovery with (sheet ...) tokens
  # - Warning when provided schematic not in project hierarchy
  # - Cross-file intelligence (finding PCB from SCH, etc.)
  # - Legacy .pro file support with real fixtures
