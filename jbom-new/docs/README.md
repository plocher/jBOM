# Documentation

This directory contains project-wide documentation that doesn't belong to specific code modules.

## Architecture Documentation

### Design Principles
The jBOM architecture follows these key principles established during the Service/Workflow/Command decomposition:

1. **Service-Command Pattern**: Services contain business logic, CLI provides thin command wrappers
2. **Pure Functions**: Services are stateful classes, Common contains stateless utilities
3. **Single Responsibility**: Each service has one clear business purpose
4. **Testability**: Services can be unit tested in isolation, BDD tests validate user workflows

### Service vs Common Axiom
**Key Decision Rule**: Use `__init__` method presence as the differentiator:

- **Services** (in `src/services/`): Have state and behavior
  - Contains `__init__` method with instance variables
  - Examples: `BOMGenerator`, `SchematicReader`, `InventoryMatcher`

- **Common** (in `src/common/`): Stateless utilities and data structures
  - Pure functions, data classes, constants
  - No `__init__` methods (except for data classes)
  - Examples: `ComponentData`, file utilities, formatters

## Project Documentation

### [USER_GUIDE.md](USER_GUIDE.md)
Comprehensive user workflows and examples for BOM generation, inventory management, and component placement.

### [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
Architecture, design patterns, and implementation guide for contributors and maintainers.

## Historical Context

This documentation reflects the simplified architecture achieved after migrating from a complex plugin-based system. The previous architecture required:

- Plugin registries and discovery mechanisms
- Complex workflow abstractions
- Multi-layer indirection for simple operations
- Over 7,000 lines of infrastructure code

The current architecture eliminates this complexity while maintaining all functionality and enabling future GUI/Web/KiCad plugin interfaces.

## Development Documentation Structure

Documentation is distributed throughout the codebase following these patterns:

### Module-Level Documentation
Each significant directory contains a `README.md` with:
- **Purpose**: What this module does
- **Architecture**: How it fits in the overall system
- **Patterns**: Common patterns and conventions
- **Usage**: How to work with the module
- **Examples**: Real code references (not duplicated code)

### API Documentation
Services and functions include docstrings following Python conventions:
```python
def process_components(self, components: List[ComponentData]) -> BOMData:
    """Process components into BOM data structure.

    Args:
        components: List of component data from schematic

    Returns:
        Structured BOM data ready for output formatting

    Raises:
        BOMProcessingError: When component data is invalid
    """
```

### Test Documentation
Tests serve as living documentation:
- **Gherkin tests** document user-facing behavior
- **Unit tests** document service contracts and edge cases

## Documentation Maintenance

### Keeping Documentation Current
- Reference actual code rather than duplicating it
- Update documentation when making architectural changes
- Use examples from the working codebase
- Keep high-level concepts in central docs, implementation details near code

### Documentation Review
When adding features or making changes:
1. Update relevant module README files
2. Add/update docstrings for public APIs
3. Create BDD tests for user-facing changes
4. Update CHANGELOG.md for significant changes

## Future Evolution

As jBOM grows, maintain these documentation principles:
- **Discoverability**: New developers can understand the system quickly
- **Maintainability**: Documentation stays in sync with code
- **Completeness**: All architectural decisions are captured
- **Usability**: Examples and patterns are easy to follow

The Service-Command architecture provides a stable foundation that can support additional interfaces (GUI, Web, KiCad plugins) without requiring architectural changes or documentation restructuring.


## Fetures and Workflows
### DNP and ExcludeFromBOM

In KiCad, attribute to exclude a component from the Bill of Materials (BOM) is labeled "Exclude from bill of materials". This attribute is used for virtual components like mounting holes, fiducials, or logos, rather than for "Do Not Populate" (DNP) parts.
Key details regarding this feature:
Function: It prevents the component from appearing in generated BOM exports.
"Virtual" Attribute: Similar to marking footprints as "Virtual" in the PCB editor.
Difference from DNP: "Exclude from BOM" is different from "Do Not Populate" (DNP); the latter still includes the part in the BOM but marks it as not to be assembled, while the former removes it entirely from the document.


In KiCad, the hash ('#') prefix in a component's reference designator is primarily used for virtual or non-physical components that exist in the schematic but should not be exported to the PCB layout or the Bill of Materials (BOM).
Here are the specific components and scenarios where KiCad uses the '#' prefix:
Power Ports and Power Symbols: When a symbol is defined as a power port (e.g., VCC, GND) in its properties, KiCad often marks it with a '#' (e.g., #PWR01) to indicate it is a global power net connection rather than a physical part.
PWR_FLAG Symbols: Similar to power ports, these are virtual components used to inform the Electrical Rules Check (ERC) that a power net is driven, and they do not represent physical components on the board.
Unannotated or Non-physical Symbols: If a symbol is created that is not meant for the board, or if automatic annotation fails to categorize a symbol properly, it may receive a '#' prefix.
Hierarchical Labels/Pins: Sometimes intermediate connection points within schematic hierarchies can be marked with this prefix.

### MATCH
The match function's scope is to find the inventory items that satisfy the electrical/physical requirements of partially specified kicad components
If it can do that simply (component.IPM == Inventory.IPN), fantastic happy path.  There are other happy paths, and a slew of more focused heuristic paths, each adding their own levels of uncertainty to the algorithm, with the worst case that there isn't enough "specified" in the component to do the match

the inventory workflows supported by jbom are

### INVENTORY

A) produce a bom from a kicad project without an inventory
   This produces a simple table of components found in the project schematics, aggregated (grouped) by component type and value

   KiCad projects have Components with attributes that represent the physical electro-mechanical properties required by the designer.

   In general, a BOM includes the components and their attributes that are needed for purchasing the components used in the design
   (selecting which fields to include is the focus of the --fields functionality in jBOM)

     * Value: (e.g., 10k, 0.1uF)
     * Designator list: (e.g., R1, C1, U1 - separated by commas or spaces)
     * Package/Footprint: (e.g., 0603, SOIC-8)
     * Manufacturer Part Number (MPN): (Crucial for correct component selection)
     * Description: (Short description of the component)
     * Type/Value: (Surface mount, Thru-hole, or Hybrid)
     * Quantity: (Total count per part)

    Note that BOMs can, but do not need to include an IPN, since it we can't expect kicad developers to need, or assign IPN's to every component in their project - although some do...

B) create a new inventory from a kicad project.
   This may require jbom to invent IPN (Inventory Part Numbers) values for the new inventory.
   An inventory is a list of Items that represent the specific supplier, manufacturer, location or desirability of a physical device that satisfies the electro-mechanical requirements from the designer
   In jBOM, the inventory is allowed to have multiple Items with the same IPN, as long as all share the same electro-mechanical details.  This allows the inventory to provide mutiple sources, lots, locations... for the "same" part.
   You can think of IPNs as hash values that represent a specific set of electro-mechanical component attributes - their exact value is immaterial, it is only the equality comparison that matters.
    Inventories contain Items that have attributes; KiCad's Component attributes overlap with Inventory attributes in the electro-mechanical domain; inventory Item's attributes are a superset of the Component's attributes that capture sourcing, pricing and other production-of-product details.

C) produce a BOM from a kicad project and a (set of) inventory file(s)

    Similar to "A", but the source of some BOM fields can now be the inventory file instead of the kicad project.
    A kicad Component is MATCHED with Items in the inventory using heuristics, then the combination of the Component and Item attributes is used to create the BOM
    Often, things like Manufacturer, MPN etc are only in the inventory, making kicad project maintenance easier.
    When multiple Items represent the same part (and thus have the same IPN), other mechanisms must be used to choose a single result.  In jBOM, this is done with the --fabricator feature, which applies filters to the Items before MATCHING is performed.

    The MATCH functionality is important here
        If the Component has an IPN, and the IPN matched an Item (or Items), they are returned as the result.  Otherwise
        various heuristics are used to find and rank candidate Items based on their electro-mechanical attributes
        If there is a high confidence in the resulting Items, they are returned.  Otherwise
        the match fails.

It is important to note that the ONLY time jbom creates IPMs is when it is creating a new inventory from a kicad project.

It appears that jBOM is incorrectly creating IPNs when creating BOMs, and not restricting that effort to the inventory creation use case.

## kicad project references

As a KiCad user, I want to reference my project to jBOM in whatever way feels natural, without having to remember which specific file each jBOM operation needs.

1. "When I'm in a directory with a KiCad project, I shouldn't have to tell ijBOM what to use"
2. "I want to give it the name of a directory that contains a KiCad project"
3. "I want to give it the name of a KiCad file and have it figure out the project it is part of"
4. "I want jBOM to figure out what it needs when I give it a valid KiCad project filename, even if it is the wrong project file for the operation I am using"


The search logic should be similar to this pseudocode/english description:
if no project_argument is provided, set project_argument = "."  (current directory) and continue

if the project_argument directory or file does not exist:
     ERROR: file/directory not found
if !isDir(project_argument) then
     chdir(dirname(project_argument))

     list = glob("*.kicad_pro")
     ERROR if exactly 1 item is not found # there can only be ONE *.kicad_pro file in a valid kicad project directory
     project.kicad_pro = list[0]
     project.kicad_pcb = Path(project.kicad_pro).stem + ".kicad_pcb"
     project.kicad_sch = Path(project.kicad_pro).stem + ".kicad_sch" # this only identifies the root sheet
     project.kicad_child_schematics = ... description below ...

     if filename(project_argument) is not in the project.kicad_child_schematics
         WARNING: the provided schematic {filename(project_argument)} is not part of the kicad project found in {dirname(project_argument)}

Child schematics are hierarchical sheets linked within the root or other parent sheets.
Within the Root File: Open the root .kicad_sch file (which is a text-based S-expression file) and look for the (sheet ...) token.
Extraction: Each (sheet ...) entry contains a (property "Sheetfile" "filename.kicad_sch") field that specifies the child's filename.
Recursive Hierarchy: Subsheets can themselves contain other subsheets. To find all children, you must recursively check every identified .kicad_sch file for further (sheet ...) definitions.



project_steps.py (3 steps):
•  @given("a KiCad project") - Creates anonymous project from template
•  @given("the schematic is deleted") - Removes schematic file
•  @given("the PCB is deleted") - Removes PCB file

project_centric_steps.py (19 steps):
•  @given('a KiCad project directory "{name}"') - Named directory projects
•  @given('a minimal KiCad project "{name}"') - Named minimal projects
•  @given('a project "{project}" placed in "{dir}"') - Directory placement
•  @given("a schematic that contains:") - Core schematic creation
•  @given("a PCB that contains:") - Core PCB creation
•  Many other specialized steps for complex scenarios

Key Findings:•  @given("a KiCad project") (project_steps.py) creates anonymous projects
•  @given('a KiCad project directory "{name}"') (project_centric_steps.py) creates named projects
•  These are complementary, not duplicate

Critical Dependencies ⚠️
The project_centric_steps.py file contains essential core steps used throughout the test suite:
•  @given("a schematic that contains:") - Used by all BOM/inventory features
•  @given("a PCB that contains:") - Used by all POS features
•  Complex project setup steps for multi-file scenarios
