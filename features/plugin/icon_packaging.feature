Feature: PCM plugin icon packaging integrity
  Scenario: PCM archive includes required toolbar and package icons
    When I build the PCM archive with skip binary fetch
    Then the archive should include the required plugin packaging files
    And "resources/icon.png" in the archive should be a 64x64 PNG
    And "plugins/assets/icons/pcb-fabrication-tool-light-24.png" in the archive should be a 24x24 PNG
    And "plugins/assets/icons/pcb-fabrication-tool-dark-24.png" in the archive should be a 24x24 PNG
    And "plugins/plugin.py" in the archive should contain text "pcb-fabrication-tool-light-24.png"
    And "plugins/plugin.py" in the archive should contain text "dark_icon_file_name"
