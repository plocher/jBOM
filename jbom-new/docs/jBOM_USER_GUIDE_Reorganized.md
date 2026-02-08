# jBOM User Guide
- [jBOM User Guide](#jbom-user-guide)
  - [1. Introduction](#1-introduction)
    - [1.1 What is jBOM?](#11-what-is-jbom)
    - [1.2 The Problems jBOM Solves](#12-the-problems-jbom-solves)
    - [1.3 jBOM's Approach](#13-jboms-approach)
  - [2. User Roles and Workflows](#2-user-roles-and-workflows)
    - [2.1 Electronics Designer](#21-electronics-designer)
    - [2.2 PCB Designer](#22-pcb-designer)
    - [2.3 Project Manager](#23-project-manager)
  - [3. Key Use Cases](#3-key-use-cases)
    - [3.1 KiCad Project Reference](#31-kicad-project-reference)
    - [3.2 Parts Lists, BOM and CPL Generation](#32-parts-lists-bom-and-cpl-generation)
    - [3.3 Inventory Management](#33-inventory-management)
  - [4. Technical Concepts](#4-technical-concepts)
    - [4.1 KiCad Project Structure](#41-kicad-project-structure)
    - [4.2 Inventory Part Numbers (IPNs)](#42-inventory-part-numbers-ipns)
    - [4.3 Component Matching Algorithm](#43-component-matching-algorithm)
    - [4.4 Fabricator Filtering](#44-fabricator-filtering)
  - [5. Core Capabilities](#5-core-capabilities)
    - [5.1 BOM Generation](#51-bom-generation)
    - [5.2 CPL Generation](#52-cpl-generation)
    - [5.3 Inventory Management](#53-inventory-management)
    - [5.4 Validation and Reporting](#54-validation-and-reporting)
  - [6. Design Axioms](#6-design-axioms)
    - [Axiom 1: Unit and Functional tests use real KiCad projects](#axiom-1-unit-and-functional-tests-use-real-kicad-projects)
    - [Axiom 2: No Magic GIVEN and WHEN test statements, Be Explicit](#axiom-2-no-magic-given-and-when-test-statements-be-explicit)
    - [Axiom 3: User Behavior Focus](#axiom-3-user-behavior-focus)
    - [Axiom 4: Fabricator Reality](#axiom-4-fabricator-reality)
    - [Axiom 5: Graceful Degradation, fail safe](#axiom-5-graceful-degradation-fail-safe)
  - [7. Electronic Design and Fabrication Context](#7-electronic-design-and-fabrication-context)
    - [7.1 Key Stakeholders](#71-key-stakeholders)
    - [7.2 Workflow Integration](#72-workflow-integration)
    - [7.3 Key Terminology](#73-key-terminology)

## 1. Introduction

### 1.1 What is jBOM?
jBOM is a KiCad ecosystem tool that bridges the gap between PCB design and fabrication. It generates manufacturing-ready Bill of Materials (BOMs) and Component Placement Lists (CPLs) by matching KiCad project components with inventory databases, enabling fabricator-neutral designs that can be manufactured by multiple suppliers.

### 1.2 The Problems jBOM Solves
KiCad generates Parts Lists and Bill of Materials (BOMs) based on schematic attributes.  The designer is expected to add fabricator- and supplier-specific information (manufacturer part numbers, distributor codes, pricing) to each component in the schematic itself.

Instead of manually entering all this information for each component, KiCad supports the use of databases and web-APIs for access to component libraries that have this information pre-supplied.  The designer then chooses the desired component from the database's list of dozens to hundreds of resistors.

This creates two critical problems:

**1. Library Explosion**: Libraries that provide components with these "pre-supplied" fabrication attributes now need to deal with the fact that a simple resistor `Device:R` symbol becomes dozens of library symbols—one for each combination of value, package, and supplier:
  * `Inventory:RES-0603-0102` =
     * Symbol=`Device:R`,
     * Value=`1k`,
     * Tolerance=`10%`,
     * LCSC=`C25585`
  * `Inventory:RES-0603-0222` =
     * Symbol=`Device:R`,
     * Value=`2k2`,
     * Tolerance=`10%`,
     * Mfg=`Uni-Royal`,
     * MPN=`0603WAJ0222T5E`,
     * LCSC=`C25992`

**2. Tight Coupling**: Projects become locked to specific suppliers and part numbers. When JLCPCB part `LCSC:C25585` becomes unavailable or you switch to PCBWay, the KiCad design files must be manually updated and re-validated.

### 1.3 jBOM's Approach
jBOM separates concerns by keeping KiCad projects focused on electro-mechanical requirements (`1kΩ`, `R_0805_2012Metric`, `10%`) while maintaining separate inventory databases that map these requirements to specific suppliers and manufacturers. The tool heuristically matches project components to inventory items and generates fabricator-specific outputs:

- **JLCPCB**: BOMs with LCSC part numbers
- **PCBWay**: BOMs with Mouser/Digikey part numbers and manufacturer details
- **Other fabricators**: Customizable output formats

## 2. User Roles and Workflows

jBOM focuses on several workflows in the electronics design and manufacturing process. While the same person may perform all these actions at different times, each has distinct needs and interactions with the tool.

### 2.1 Electronics Designer
**Primary Focus**: Circuit design and component selection based on electrical requirements

**Responsibilities**:
- Creates and maintains electronic schematic design files
- Specifies component values and parameters
- Consumes manufacturer datasheets for technical specifications
- Uses inventory lists to select proven components

**Core Needs**:
- Focus on electronic and mechanical KiCad design requirements, not supplier details
- Select components from organization's preferred inventory when possible
- Avoid hardcoding supplier details in KiCad projects
- Maintain focus on electro-mechanical improvements throughout product lifecycle

### 2.2 PCB Designer
**Primary Focus**: Physical board layout and footprint selection

**Responsibilities**:
- Creates and maintains PCB design files
- Selects appropriate component packaging and footprints
- Ensures designs meet fabricator requirements
- Manages component placement for manufacturability

**Core Needs**:
- Generate component lists for fabricators that match exactly what they expect
- Exclude test points and DNP (Do Not Populate) components from assembly
- Ensure pick-and-place machines receive correct component locations and orientations
- Support components on both PCB sides with proper layer handling

### 2.3 Project Manager
**Primary Focus**: Supply chain, fabrication, and production management

**Responsibilities**:
- Curates and maintains inventory lists of preferred components
- Associates inventory Items with suppliers and manufacturers
- Selects fabricators and suppliers
- Generates manufacturing artifacts (BOMs, CPLs, Gerbers)
- Manages product lifecycle across multiple supply chains

**Core Needs**:
- Utilize existing inventory systems rather than inventing something new
   - (databases, spreadsheets, WebAPI...)
- Maintain inventory lists without requiring KiCad expertise
- Update inventory lists with new items from KiCad projects
- Manage inventory item lifecycles as supplier conditions change
- Choose fabricators without modifying KiCad files
- Create fabricator-specific artifacts from KiCad projects and inventory lists
- Generate cost and availability reports

## 3. Key Use Cases

### 3.1 KiCad Project Reference
**Use Case**: As a KiCad user, I want to reference my project to jBOM in whatever way feels natural, without having to remember which specific file each jBOM operation needs.

**Core User Needs**:
1. "When I'm in a directory with a KiCad project, I shouldn't have to tell it what to use"
2. "I want to give it the name of a directory that contains a KiCad project"
3. "I want to give it the name of a KiCad file and have it figure out the project it is part of"
4. "I want jBOM to figure out what it needs if I give it a valid project filename, even if it is the wrong KiCad project file for the operation I am using"

**Expected Behavior**:
- Auto-detection of KiCad projects in the current directory
- Support for directory paths containing KiCad projects
- Intelligent resolution of project files regardless of which specific file is provided
- Validation of edge cases and graceful handling of failures
- Clear error messages with actionable context when a requested operation can't be completed

### 3.2 Parts Lists, BOM and CPL Generation
**Use Case**: As a Kicad designer, I want to generate Parts Lists for project documentation
**Use Case**: As a Project Manager, I want to generate BOMs in the format and with the content required by my chosen fabricator.
**Use Case**: As a Project Manager, I want to generate placement files so automated assembly equipment can place components in exactly the right locations and orientations.
**Use Case**: As a Project Manager, I want to generate CPLs in the format and with the content required by my chosen fabricator.

**Core User Needs**:
1. "I need a BOM that matches exactly what my fabricator expects"
2. "I want the option to include or exclude Exclude from BOM and Do Not Populate components in Parts Lists and BOMs"
3. "BOMS need to include fabricator-specific supply chain details such as supplier part numbers, manufacturer names and MPNs"
4. "I want to define reusable custom BOM, Parts List and CPL formats"
5. "I need to audit my KiCad projects components against inventory lists and supplier databases"
6. "I want to specify the field names and order of the attributes provided in the BOMs, CPLs and Parts Lists"
7. "I want to map the attribute / field names used in KiCad and my Inventory to custom column names output in the BOMs, CPLs and Parts Lists.
8. "I want to map a list of possible attribute names to a custom output column name to support legacy naming conventions" (i.e., I want to map any of [LCSC Part #, JLCPCB Part #, LCSC, JLC, LCSC Part, JLC Part#] to LCSC )
9. "I want to be able to reference multiple inventory sources when using this tool"
10. "My pick-and-place machine needs to know exactly where each component goes"
11. "Components must be oriented correctly or my assembly will fail"
12. "Different fabricators use different coordinate systems - I need the right format"
13. "I have components on both sides of my PCB and need proper layer handling"
14. "Test points and mechanical components marked either DNP or ExcludeFromBOM should not be put into the BOM"
15. "Fiducial Marks should be put into the CPL file"

**Expected Behavior**:
- Generate BOMs in formats compatible with major fabricators (JLC, PCBWay, etc.)
- Use matching heuristics to connect the components used in a KiCad project to items in inventory lists
- Use filtering heuristics to restrict matches to a subset of inventory items
- Use filtering on components' DNP and ExcludeFromBOM attributes to manage components that appear in the Parts Lists, BOMs and CPLs
- Optionally include supplier, pricing, and availability information from inventory
- Save and reuse successful BOM configurations
- Validate component data completeness with clear warnings
- Generate coordinate-accurate placement files with precise positions
- Handle component orientation based on footprint and fabricator requirements
- Support multiple coordinate system conventions
- Process top and bottom layer components correctly
- Filter components based on assembly requirements

### 3.3 Inventory Management
**Use Case**: As a KiCad designer and project manager, I want to understand what components I need, where to get them, and what they'll cost before I commit to a design.

**Core User Needs**:
1. "I need to know the total cost impact of my component choices"
2. "I want to use standard parts that are readily available"
3. "I need to identify custom or hard-to-source components early"
4. "I want to compare supplier options for the best price and availability"
5. "I need to know minimum order quantities and lead times"

**Expected Behavior**:
- Calculate total BOM cost with quantity-based pricing
- Highlight standard vs. custom components
- Flag availability issues early in the design process
- Compare multiple supplier options for the same component
- Include logistics information for procurement planning

## 4. Technical Concepts

### 4.1 KiCad Project Structure
A KiCad project consists of multiple files with consistent naming. For a project named `gizmo`, the structure is:

```
└── MyGizmo                 # The directory name does not need to be the same as the KiCad project name
    ├── gizmo-backups
    │   └── gizmo-2026-01-25_191135.zip
    ├── gizmo.kicad_pcb     # The PCB design file
    ├── gizmo.kicad_pro     # The KiCad Project file
    └── gizmo.kicad_sch     # The Schematic design file(s)
```

- All main KiCad project files share the same base name
- A project may have many hierarchical schematic files, with the root schematic matching the project name.  All schematic files end in `.kicad_sch`
- A project can have only one PCB design file (`.kicad_pcb`)
- A project can have only one project file (`.kicad_pro`)
- The `.kicad_pro` file acts as the primary reference for the project

### 4.2 Inventory Part Numbers (IPNs)
**Core Concept**: An IPN serves as an "electrical specification hash" that represents a specific set of electro-mechanical component attributes.

**Key Principles**:
- The structure and value of IPNs is entirely up to the user.
- When creating a new inventory file from a KiCad project, the user should be able to provide an "IPN template" that can construct an IPN value from the component's attributes, otherwise the IPN field should be left blank.
- Multiple inventory items can share the same IPN if they're electro-mechanically identical
- Items with the same IPN differ in supplier, cost, or availability
- The IPN equality comparison is what matters, not the specific value

**Example**: Two 1kΩ resistors with identical tolerance, power rating, and package from different suppliers would share an IPN, making them interchangeable from a design perspective.

### 4.3 Component Matching Algorithm
The jBOM match function finds inventory items that satisfy the electrical/physical requirements of KiCad components through multiple paths:

1. **Direct IPN Match**: If the KiCad component has an IPN that matches an inventory item's IPN
2. **Attribute-Based Matching**: Using heuristics to match component attributes to inventory items
3. **Confidence Ranking**: Results are scored based on match quality

The matching process makes it possible to maintain supplier-neutral KiCad projects while still generating supplier-specific manufacturing outputs.

### 4.4 Fabricator Filtering
Before component matching occurs, inventory items can be filtered based on the selected fabricator:

Thi

- Each fabricator may have preferred suppliers (i.e., JLC prefers LCSC parts sourcing, but accepts Global Sourcing via Mouser, Digikey etc as well as direct consignment)
- Filtering narrows the inventory to items suitable for the selected fabricator
- Additional criteria like cost, datecode, availability, or priority can be applied if needed to support recurring stock orders with a first-purchased-first-used policy.

## 5. Core Capabilities

### 5.1 BOM Generation
- Create BOMs from KiCad projects with or without inventory data
- Format BOMs to meet specific fabricator requirements
- Include/exclude fields based on fabrication needs
- Optionally calculate quantities, costs, and availability

### 5.2 CPL Generation
- Create placement files from KiCad PCB data
- Support multiple fabricator coordinate systems
- Handle component orientation and layer assignment
- Filter components based on assembly requirements

### 5.3 Inventory Management
- Create, maintain and access multiple inventory databases
- Import component data from multiple sources
- Extract new components from KiCad projects
- Track component costs and availability
- Search supplier databases and web APIs for desired inventory Items

**Example**: A KiCad project uses a `1k`, `0603` resistor.  An Inventory gets created from that project that now contains a `1k`, `0603` Resistor Item, with no supplier information....  -or-

**Example**: The project manager wishes to utilize a new supplier, and needs to add componets from their catalog to the Inventory....

... The project manager needs to search the supplier catalogs to find the missing information (part numbers, data sheet URLs, prices...) and add it to the Inventory.  A matching heuristic can be applied to the Inventory Item (using its electro-mechanical attributes) and the supplier catalog to identify a short list of candidates for each Item.  The project manager can then choose from that smaller set.

### 5.4 Validation and Reporting
- Verify KiCad projects against inventory looking for mismatches
- Identify unused or problematic components by tracking which KiCad projects use which Items
- Generate cost and availability reports
- Track component usage across projects

## 6. Design Axioms

These foundational principles guide jBOM development and testing:

### Axiom 1: Unit and Functional tests use real KiCad projects
**Principle**: jBOM needs to work with authentic KiCad-generated files, never mocked synthetic/fake content.
**Rationale**: In the absence of fully supported KiCad file APIs, the parsing logic in jBOM needs as much validation as the logic built on top of it.

### Axiom 2: No Magic GIVEN and WHEN test statements, Be Explicit
**Principle**: Test case intentions and component specifications should be explicit and visible.
**Rationale**: It is good Design of Experiment practice to say what you mean and measure what you said.

### Axiom 3: User Behavior Focus
**Principle**: Feature tests validate what users actually do, not implementation details.  Unit tests focus on the correctness of implementation details.
**Rationale**: Feature tests rarely change, as they capture user expectations.  Unit tests, on the other hand, must evolve in sync with the implementation it is protecting.

### Axiom 4: Fabricator Reality
**Principle**: Output formats must match what fabricators actually expect and use.
**Rationale**: jBOM's primary value is enabling successful fabrication/assembly.

### Axiom 5: Graceful Degradation, fail safe
**Principle**: Don't make the user remember or do things that the program can figure out on its own.
**Rationale**: Real PCB designs often have missing or evolving component specifications; jBOM exists to make it safe and easy to find and fill those gaps.

## 7. Electronic Design and Fabrication Context

### 7.1 Key Stakeholders
- **Manufacturers**: Produce physical components and provide datasheets describing their electro-mechanical details
- **Suppliers/Distributors**: Maintain business relationships with manufacturers and serve as a source for components
- **Fabricators**: Create physical products using KiCad-derived artifacts, may also act as suppliers

### 7.2 Workflow Integration
jBOM integrates into the typical electronic CAD workflow, as a stand alone application, a python package, and as a KiCad plugin:

1. Designers create a KiCad project focused on electro-mechanical requirements
2. jBOM validates components against inventory, identifying missing items
3. Missing components are either added to inventory or designs are changed
4. Project managers select fabricators based on cost, capabilities, and availability
5. jBOM generates fabricator-specific artifacts (BOMs, CPLs)
6. Fabricators manufacture and assemble the PCB using these artifacts

### 7.3 Key Terminology
- **Authentic KiCad Content**: Files generated by actual KiCad software with proper file content and structure
- **Fabricator-Specific Output**: Formatted manufacturing data for specific fabricators
- **User Workflow**: Complete sequence of actions to accomplish business goals
- **Business Outcome**: The actual value delivered to users
- **Inventory Item**: A specific component from a specific supplier
- **Inventory Part Number (IPN)**: Unique identifier for electro-mechanically equivalent components
