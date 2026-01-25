Feature: Project Discovery Architecture
  As a KiCad user
  I want jBOM to correctly discover project files from various input types
  So that I can use natural KiCad workflows and get clear errors when things go wrong

  Background:
    Given a sandbox

  # Positive cases - jBOM works correctly when used properly

  Scenario: Discover project from current directory
    Given a KiCad project "current_dir_test" with files:
      | File                           | Component | Reference | Value | Footprint     |
      | current_dir_test.kicad_pro     |           |           |       |               |
      | current_dir_test.kicad_sch     | Resistor  | R1        | 10K   | R_0805_2012   |
    And the generic fabricator is selected
    When I run jbom command "bom ."
    Then the command should succeed
    And the output should contain the following messages:
      | message_type | content |
      | info | current_dir_test - Bill of Materials |

  Scenario: Discover project from project directory name
    Given a KiCad project "named_project" with files:
      | File                        | Component | Reference | Value | Footprint     |
      | named_project.kicad_pro     |           |           |       |               |
      | named_project.kicad_sch     | Resistor  | R1        | 10K   | R_0805_2012   |
    And the generic fabricator is selected
    When I run jbom command "bom ."
    Then the command should succeed
    And the output should contain the following messages:
      | message_type | content |
      | info | named_project - Bill of Materials |

  Scenario: Discover project from explicit schematic file
    Given a KiCad project "explicit_sch" with files:
      | File                      | Component | Reference | Value | Footprint     |
      | explicit_sch.kicad_pro    |           |           |       |               |
      | explicit_sch.kicad_sch    | Resistor  | R1        | 10K   | R_0805_2012   |
    And the generic fabricator is selected
    When I run jbom command "bom explicit_sch.kicad_sch"
    Then the command should succeed
    And the output should contain the following messages:
      | message_type | content |
      | info | explicit_sch - Bill of Materials |

  Scenario: Discover project from explicit PCB file
    Given a KiCad project "explicit_pcb" with files:
      | File                     | Component | Reference | Value | Footprint     |
      | explicit_pcb.kicad_pro   |           |           |       |               |
      | explicit_pcb.kicad_pcb   | Footprint | R1        |       | R_0805_2012   |
    When I run jbom command "pos explicit_pcb.kicad_pcb"
    Then the command should succeed
    And the output should contain the following messages:
      | message_type | content |
      | info | Component Placement Data |

  Scenario: Discover project from project file
    Given a KiCad project "from_pro_file" with files:
      | File                       | Component | Reference | Value | Footprint     |
      | from_pro_file.kicad_pro    |           |           |       |               |
      | from_pro_file.kicad_sch    | Resistor  | R1        | 10K   | R_0805_2012   |
    And the generic fabricator is selected
    When I run jbom command "bom from_pro_file.kicad_pro"
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
    Given a KiCad project "multi_project" with files:
      | File               | Component | Reference | Value | Footprint |
      | first.kicad_pro    |           |           |       |           |
      | second.kicad_pro   |           |           |       |           |
    When I run jbom command "bom ."
    Then the command should fail
    And the error output should contain the following messages:
      | message_type | content |
      | error | No schematic file found |

  Scenario: Derived schematic file missing
    Given a KiCad project "missing_sch" with files:
      | File                   | Component | Reference | Value | Footprint |
      | missing_sch.kicad_pro  |           |           |       |           |
    And the generic fabricator is selected
    When I run jbom command "bom ."
    Then the command should fail
    And the error output should contain the following messages:
      | message_type | content |
      | error | No schematic file found |

  Scenario: Derived PCB file missing
    Given a KiCad project "missing_pcb" with files:
      | File                  | Component | Reference | Value | Footprint |
      | missing_pcb.kicad_pro |           |           |       |           |
    When I run jbom command "pos ."
    Then the command should fail
    And the error output should contain the following messages:
      | message_type | content |
      | error | No PCB file found |

  # TODO: Additional discovery scenarios to implement:
  # - Hierarchical schematic discovery with (sheet ...) tokens
  # - Warning when provided schematic not in project hierarchy
  # - Cross-file intelligence (finding PCB from SCH, etc.)
  # - Legacy .pro file support with real fixtures
