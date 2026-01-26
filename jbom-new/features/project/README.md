# Project Reference Domain

## Use Case
As a KiCad user, I want to reference my project to jBOM in whatever way feels natural, without having to remember which specific file each jBOM operation needs.

## Core User Needs
1. "When I'm in a directory with a KiCad project, I shouldn't have to tell it what to use"
2. "I want to give it the name of a directory that contains a KiCad project"
3. "I want to give it the name of a KiCad file and have it figure out the project it is part of"
4. "I want jBOM to figure out what it needs if I give it a valid project filename, even if it is the wrong KiCad project file for the operation I am using"

## Feature Files

### directory.feature
Tests implicit current directory references and explicit directory references.
- Scenarios: no project parameter, directory names, directory edge cases
- Covers user needs #1 and #2

### file.feature
Tests explicit file references (.kicad_pro, .kicad_sch, .kicad_pcb).
- Scenarios: all file types with all commands, file edge cases
- Covers user need #3

### cross_resolution.feature
Tests wrong file type → right file type resolution.
- Scenarios: bom given .pcb, pos given .sch, inventory given wrong files
- Covers user need #4

## Step Architecture Decisions

### Common vs Domain-Specific Steps
- **Common steps** (most features): Anonymous projects using `Given a schematic that contains:`
- **Domain-specific steps** (project domain only): Named projects using `Given a project "name" placed in "dir"`

### KiCad Project Foundation
- **Real KiCad templates** used instead of synthetic file creation
- **Complete projects** as foundation: All features start with complete .kicad_pro/.kicad_sch/.kicad_pcb files
- **Degradation testing**: Remove files for negative tests rather than selective creation
- **Name embedding**: KiCad files contain internal project name references requiring content modification

### Step Patterns
```gherkin
# Foundation (domain-specific)
Given a KiCad project                    # Empty complete project
And the schematic is deleted             # Remove for negative tests
When I run jbom command "bom project.kicad_pro"

# vs Common pattern (most features)
Given a schematic that contains:         # Anonymous complete project
When I run jbom command "bom"
```

## Implementation Notes
- All features use GHERKIN_RECIPE patterns with `Given a jBOM CSV sandbox` background
- Domain-specific steps are kept separate from common/reusable ones
- Equal coverage across BOM, POS, and Inventory commands unless there's a specific reason not to
- Template location: `features/fixtures/kicad_templates/empty_project/`
