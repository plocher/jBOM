# jBOM User Requirements
## What is jBOM?

jBOM is a tool that bridges the gap between KiCad PCB design and real-world fabrication/assembly. It takes your KiCad project files and generates the manufacturing files that fabricators and assembly houses need.

## Why do I need jBOM?

KiCad has the ability to generate Parts Lists and Bill-of-Materials based solely on the attributes found in the KiCad project files. Without special care, these BOMs are insufficient for fabrication use because the provided KiCad libraries generally do not include component manufacturer and/or supplier details such as Manufacturer and Supplier part numbers.

KiCad users can include this information in their KiCad projects, either piecemeal or by curating their own libraries with this information added to each component.  This is the path taken by most of the KiCad community, usually by way of KiCad's support for Web/Database based component libraries.

The downside of this is two-fold
1. Component libraries explode in complexity.  Instead of having a single "resistor" symbol in a library that includes a footprint pattern for, say, 0805, 0603 and PTH packages, where the user specifies values of "1k" and "220k", along with a choice of an `Resistor_SMD:R_0805_2012Metric` footprint, these inventory-aware libraries now have hundreds of symbols, one for each of the combinatoric expansion of `value`, `footprint` and `supplier`
2. By embedding both the electro-mechanical attributes (`1k`, `Resistor_SMD:R_0805_2012Metric`) along with the supplier details (`JLC`, `LCSC=C25585`, `UNI-ROYAL`, `0603WAJ0102T5E`), the project is now tightly coupled to both the fabricator (JLC) and one out of the 50 or so stocked components there.  If that part number from JLC becomes unavailable in the future, or if the user wishes to use PCBway to fabricate their project, the project file or the BOM will need to be manually updated.

jBOM exists to address this problem in a different way:  it looks to KiCad projects to unambiguously record the project's electro-mechanical component requirements (`1k`, `Resistor_SMD:R_0805_2012Metric`, `10%`, `100mW`, `thick-film`), to external inventory lists to record supplier and fabricator information, and it MATCHES the project components to inventory items using those electro-mechanical attributes, producing BOMS, Parts Lists and CPL files in the forms and with the content required by the chosen fabricator:
  * JLC BOMs include "LCSC" part numbers
  * PCBway BOMs include Mouser or Digikey part numbers along with manufacturer names and part numbers

### MATCH functionality details
The jBOM match function's scope is to find the inventory items that satisfy the electrical/physical requirements of partially specified kicad components
If it can do that simply (say, with matching Inventory Part Numbers: component.IPM == Inventory.IPN), fantastic happy path.  There are other happy paths, and a slew of more focused heuristic paths, each adding their own levels of uncertainty to the algorithm, with the worst case that there isn't enough "specified" in the component to do the match

### Who Uses jBOM?
jBOM users design products using KiCad, and then send project details to Fabricators who turn them into physical products.  Their workflow includes

  - creating and using KiCad component symbol and footprint libraries that contain proven components
  - selecting suppliers for the components they wish to use
  - curating inventory lists of preferred Components
      - Items in an inventory have user-provided Inventory Part Numbers (IPNs)
      - Items with the same IPN are electro-mechanically interchangible, but differ in sourcing or logistical details.
      - Items link components to desirable sources
  - designing KiCad eCAD projects using electro-mechanical knowledge, libraries, and inventories
  - creating and sending project artifacts to a fabricator who creates and assembles products.

Users fill several roles:

- **Electronics Designer**
   - Source of component electro-mechanical requirements
   - Consumes Manufacturer Datasheets
   - Consumes Inventory lists
   - Creates and maintains electronic schematic design files for a project
   - Generates Parts Lists representing the components used in a project

- **PCB Designer**
   - Source of component electro-mechanical requirements
   - Source of component packaging and footprint requirements
   - Consumes Manufacturer Datasheets
   - Consumes Inventory lists
   - Consumes fabricator design rules
   - Creates and maintains printed circuit design files for to a project

- **Project Manager**
   - Source of Fabricator choices
   - Source of Inventory Items and supplier choices
   - Manages inventories, adding, updating and deleting Items as needed
   - Generate project Artifacts that include
      - Gerbers
      - Parts Lists
      - Bill of Materials (BOMs)
      - Component Placement Lists (CPL)

### User stories
## BOM Generation Use Cases

As a PCB designer, I want to generate component lists for my fabricator to source components for and assemble my PCB correctly.

### Core User Needs
1. "I need a BOM that matches exactly what my fabricator expects"
2. "I want to exclude test points and Do Not Populate components from assembly"
3. "I need supplier part numbers, available quantities and component costs"
4. "I want the same BOM format that worked successfully on my last project"
5. "I need to know if any components are missing critical information"


## CPL Generation Use Cases

As a PCB designer, I want to generate placement files so automated assembly equipment can place components in exactly the right locations and orientations.

### Core User Needs
1. "My pick-and-place machine needs to know exactly where each component goes"
2. "Components must be oriented correctly or my assembly will fail"
3. "Different fabricators use different coordinate systems - I need the right format"
4. "I have components on both sides of my PCB and need proper layer handling"
5. "Test points and mechanical components shouldn't go to the assembly line"

## Inventory Management Use Cases

As a PCB designer and procurement manager, I want to understand what components I need, where to get them, and what they'll cost before I commit to a design.

### Core User Needs
1. "I need to know the total cost impact of my component choices"
2. "I want to use standard parts that are readily available"
3. "I need to identify custom or hard-to-source components early"
4. "I want to compare supplier options for the best price and availability"
5. "I need to know minimum order quantities and lead times"


As an electronic project designer (schematic and/or pcb)...
  * I want an integrated KiCad-aware workflow that supports long-lifetime projects.
  * I want tools that integrate tightly into the KiCad ecosystem I use, and yet are also usable by project managers who don't use KiCad.
  * I want to focus on electronic and mechanical design requirements when developing KiCad projects.
  * When my design constraints permit, I want to select existing components from my organization's preferred components lists; I also need to be able to choose and use components that aren't in those inventory lists
  * I do not want to hardcode supplier or fabricator details into my KiCad projects.
  * As my KiCad projects evolve over their product lifecycle, I want to continue to focus on electro-mechanical improvements
  * I don't want to make production and supply chain decisions about my projects.

As a project manager...
  * I don't want to make electronic or mechanical component design decisions about a product, and I don't want the decisions I do make to impact those areas.
  * I don't want to be forced to use KiCad
  * I want to curate and maintain inventory lists of preferred components
    * I want these lists to be actively used by project designers and project managers.
      * These lists may exist as
        * CSV or Spreadsheet files (Excel and Numbers)
        * REST data sources
        * Databases accessed via an ODBC API
    * I want to add and update items to these lists as conditions dictate
      * Extract new Items from KiCad projects
      * Import invoice and parts list data from suppliers
      * search supplier databases to find candidate components that match the KiCad designer's requirements, filter, prioritize and finally add the selected ones
      * update items' attributes to reflect quantities available and prices from a supplier
    * I want to record manufacturer details
    * I want to record supplier details
    * I want to record multiple manufacturing sources for a component

  * I want to create fabricator-specific artifacts using these lists and a KiCad project
    * Create a Bill of Materials that associates the components used in a KiCad project with specific suppliers and manufacturer's products.
    * Create Parts Lists that enumerate the components used in a KiCad project
    * Create Component Placement Lists that enumerate the pcb location and orientation of every component that will be placed on a printed circuit board

  * I want to create reports based the information in KiCad projects ands these lists, for example:
    * projects that use a particular Component
    * suppliers that provide a particular Component
    * BOM costs for a project with each supplier

  * I want to choose fabricators and suppliers without having to modify KiCad project files or preferred component lists
  * I want to take advantage of multiple supply chains and use multiple fabricators for my products over their lifecycle


## Electronic design and fabrication - Context and definitions
Manufacturers produce physical components and datasheets that describe them
  - Datasheets describe the electro-mechanical details of a component.
  - Product lists enumerate the components produced by a manufacturer with lifecycle, logistical and financial details.

Suppliers maintain business relationships with, and are a source for manufacturer's physical components.  Suppliers may also be called distributers.

Fabricators create products
  - Fabricators may also be Suppliers, or may interact with Suppliers on behalf of their customers.
  - Fabricators consume KiCad-derived artifacts: Gerbers, BOM and Placement files.
  - Fabricators produce physical products.
  - Fabricators are the source of PCB design rules.

### Electronic CAD Workflows:

 1. Designers create a KiCad project
 2. Designers use jBOM tooling to ensure that the components used in the project are in the inventory
    * iterate through all the components used in a KiCad project
    * match each with one or more Items in the preferred component lists
       * if the component isn't in these lists, either
          A. manufacturer and sourcing information for this new component needs to collected and the component added to the preferred lists, or
          B. the KiCad project design needs to change to use a different component
 3. Project managers select a production fabricator (and component distributor) from the available fabricators
 4. Project managers use jBOM tooling to generate the project artifacts required by the chosen fabricator
 5. Project managers send the generated artifacts to the fabricator for production
 6. Fabricators validate the provided artifacts, confirm availability of, and acquire the components referenced in the BOM, and manufacture the project.

## jBOM tool high level features

* Create a Parts List from a KiCad project
* Create a BOM from a KiCad project with only the information found in the KiCad project
* Validate a KiCad project's BOM against the organizations' preferred component list(s)
  * Add new components to an existing list
  * Create a new list with only the KiCad project's new components
  * Create a new list with all the KiCad project's components
* Create a BOM from a KiCad project plus preferred component lists
* Create a CPL from a KiCad project

### INVENTORY details

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
   **Core IPN Concept**: In jBOM, the inventory is designed to have multiple Items with the same IPN, as long as all share the same electro-mechanical details. This allows the inventory to provide multiple sources, lots, locations... for the "same" part.
   **IPN as Electrical Specification Hash**: You can think of IPNs as hash values that represent a specific set of electro-mechanical component attributes - their exact value is immaterial, it is only the equality comparison that matters. Multiple suppliers can provide components that satisfy the same electrical specification.
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

### IPN Supplier Alternatives and Deduplication

When reading inventory files, we presume that a virtual inventory data structure is created and inventory IPNs are collected into it.

**Exact Duplicate Handling**: Items that are complete and exact duplicates of an existing virtual inventory Item are silently dropped, so the virtual inventory never has to deal with exact duplicates. Since they are exact duplicates, no information is lost or gained.  If the existence of duplicated Items is itself important, there should be a mechanism to expose this information.

**Supplier Alternatives**: Items with the same IPN but different supplier information (manufacturer, distributor, MPN, priority) are preserved as separate items. This is the intended behavior - IPNs serve as "electrical specification hashes" that allow multiple sourcing options for the same component.

The test case for exact duplicate handling is:
jbom ... --inventory A  => results in N items
jbom ... --inventory A --inventory A  => results in exactly the same N items

**Fabricator Filtering**: The fabricator and related filtering based on non-electro-mechanical attributes (aka fields) deals with how to select specific suppliers from the many that may exist with the same IPN. This is where priority ranking and supplier selection occurs.  In the BOM creation workflow, filtering by selected fabricator or supplier is done first, then attribute matching and related heuristics MATCH against the remaining Items.

## KiCad project structure

A project named `gizmo` consists of files in a directory
```
└── some-project
    ├── gizmo-backups
    │   └── gizmo-2026-01-25_191135.zip
    ├── gizmo.kicad_pcb     # The PCB design file
    ├── gizmo.kicad_pro     # The KiCad Project file
    └── gizmo.kicad_sch     # The Schematic design file(s)
```
  * The main KiCad project files all share the same base name, in this example, `gizmo`.
  * KiCad projects may have several hierarchical schematic files, the `root schematic` is the one with the project's base name.  The Kicad Project file (`gizmo.kicad_pro`) contains the list of schematics associated with the project; KiCad schematics also contain a list of any `child schematics` of their's.
  * KiCad projects may only have one `.kicad_pcb` PCB design file.


### KiCad project references
As a KiCad user, I want to reference my project in whatever way feels natural, without having to remember which specific file each jBOM operation needs.

1. "When I'm in a directory with a KiCad project, I shouldn't have to tell jBOM what to use"
2. "I want to give it the name of a directory that contains a KiCad project"
3. "I want to give it the name of a KiCad file and have it figure out which project it is part of"
4. "I want jBOM to figure out what it needs when I give it a valid KiCad project filename, even if it is the wrong project file for the operation I am using"

### Possible logical decision flow

if no project_argument is provided, assume there might be a KiCad project in the current directory (`project directory = '.'`) and continue.

if the project directory or named file does not exist:
     ERROR: file/directory not found

if project_argument is not a directory then it must be a file name.
     `project directory = dirname(project_argument)`
     `list = glob("*.kicad_pro")`
     ERROR if exactly 1 item is not found because there can only be ONE *.kicad_pro file in a valid kicad project directory
     `project name` = `list[0] without the .kicad_pro suffix`
     `project pcb` = `project name` + `.kicad_pcb`
     `project root schematic` = `project name` + `.kicad_sch`
     `project child schematics` = ... description below ...

if the `project argument` is a filename, and that name is not that of the project's kicad_pro or kicad_pcb and is not in the expanded list of child schematics, generate a
         WARNING: the provided `project argument` is not part of the kicad project `project name` found in `project directory`

Child schematics are hierarchical sheets linked within the root or other parent sheets.
  * Within the Root File: Open the .kicad_sch file (which is a text-based S-expression file) and look for the (sheet ...) token.
  * Extraction: Each (sheet ...) entry contains a (property "Sheetfile" "filename.kicad_sch") field that specifies the child's filename.
  * Recursive Hierarchy: Subsheets can themselves contain other subsheets. To find all children, you must recursively check every identified .kicad_sch file for further (sheet ...) definitions.

### Core Design Axioms

These foundational principles guide all jBOM development and testing decisions:

#### Axiom 1: Real KiCad Artifacts Only
**Principle**: jBOM only processes authentic KiCad-generated files, never synthetic/fake content.
**Rationale**: Users need confidence that jBOM behavior matches real-world KiCad usage.
**Testing Impact**: All test fixtures must use real KiCad project files.
**Validation**: "Does this test use content that KiCad actually generates?"

#### Axiom 2: No Magic, Be Explicit (DRY Principle)
**Principle**: User intentions and component specifications should be explicit and visible.
**Rationale**: Manufacturing errors are expensive; users need to see exactly what's being processed.
**Testing Impact**: Test scenarios should show exactly what components/data are involved.
**Validation**: "Can a user understand exactly what this test is validating by reading the scenario?"

#### Axiom 3: User Behavior Focus
**Principle**: Features and tests validate what users actually do, not implementation details.
**Rationale**: Software exists to solve user problems, not demonstrate technical capabilities.
**Testing Impact**: Scenarios describe user goals and outcomes, not technical mechanics.
**Validation**: "Does this test validate something a real jBOM user cares about?"

#### Axiom 4: Fabricator Reality
**Principle**: Output formats must match what fabricators actually expect and use.
**Rationale**: jBOM's primary value is enabling successful fabrication/assembly.
**Testing Impact**: Test validations should check fabricator compatibility, not arbitrary formats.
**Validation**: "Would a real fabricator accept this output for manufacturing?"

#### Axiom 5: Graceful Degradation
**Principle**: jBOM should work as well as possible with incomplete information, not fail completely.
**Rationale**: Real PCB designs often have missing or evolving component specifications.
**Testing Impact**: Tests should cover partial information scenarios, not just perfect cases.
**Validation**: "Does this handle the messy reality of real-world PCB design?"

### Key Terms

**Authentic KiCad Content**: Files generated by actual KiCad software with proper internal structure, metadata, and cross-references.

**Fabricator-Specific Output**: BOMs, placement files, and other manufacturing data formatted according to specific fabricator requirements (JLCPCB, PCBWay, etc.).

**User Workflow**: A complete sequence of actions a real user performs to accomplish a business goal (e.g., "get my PCB fabricated and assembled").

**Business Outcome**: The user value delivered by jBOM functionality (e.g., "fabricator receives correct component specifications").

**Implementation Detail**: Technical mechanics not directly relevant to user goals (e.g., specific file parsing algorithms, internal data structures).

**Potemkin Scenario**: A test that appears to validate functionality but uses fake/simplified data that doesn't reflect real-world usage.

**DRY Violation in Testing**: Hiding critical test information behind abstractions, making it unclear what's actually being tested.

**Magic in Testing**: Test steps that perform actions without making the user intent or data explicit.

### Design Decision Framework

When making jBOM decisions, test each option against these questions:

1. **Authenticity Check**: "Does this use/produce content that matches real KiCad/fabricator workflows?"
2. **User Value Check**: "Does this solve a problem real jBOM users actually have?"
3. **Explicitness Check**: "Can users understand exactly what's happening without hidden magic?"
4. **Fabrication Check**: "Does this help users successfully manufacture their PCBs?"
5. **Robustness Check**: "Does this work with the messy reality of real PCB designs?"

Decisions that violate these axioms should be reconsidered or require exceptional justification.
