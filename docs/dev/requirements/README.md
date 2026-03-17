<!-- omit in toc -->
# jBOM User Guide: Real User Stories
<details>
<summary> TOC </summary>

- [The jBOM Story](#the-jbom-story)
  - [The Problem: Conflating electronic design requirements with supply chain choices](#the-problem-conflating-electronic-design-requirements-with-supply-chain-choices)
  - [Meet Alex, an Electronic Product Development Engineer](#meet-alex-an-electronic-product-development-engineer)
  - [The Challenge: Context Switching](#the-challenge-context-switching)
  - [How jBOM Enables Efficient Context Switching](#how-jbom-enables-efficient-context-switching)
- [User Journeys](#user-journeys)
  - [Journey 1: Separating Design from Supply Chain Decisions](#journey-1-separating-design-from-supply-chain-decisions)
    - [The Problem Without jBOM:](#the-problem-without-jbom)
    - [The Solution With jBOM:](#the-solution-with-jbom)
  - [Journey 2: Inventory-Driven Component Discovery](#journey-2-inventory-driven-component-discovery)
    - [The Problem Without jBOM:](#the-problem-without-jbom-1)
    - [The Solution With jBOM:](#the-solution-with-jbom-1)
  - [Journey 3: Fabricator-Neutral Design Strategy](#journey-3-fabricator-neutral-design-strategy)
    - [The Problem Without jBOM:](#the-problem-without-jbom-2)
    - [The Solution With jBOM:](#the-solution-with-jbom-2)
  - [Journey 4: Automated Manufacturing File Integration](#journey-4-automated-manufacturing-file-integration)
    - [The Problem Without jBOM:](#the-problem-without-jbom-3)
    - [The Solution With jBOM:](#the-solution-with-jbom-3)
  - [Journey 5: Supplier Integration and Alternative Sourcing](#journey-5-supplier-integration-and-alternative-sourcing)
    - [The Problem Without jBOM:](#the-problem-without-jbom-4)
    - [The Solution With jBOM:](#the-solution-with-jbom-4)
- [Real-World Scenarios](#real-world-scenarios)
  - [The One-Person Startup](#the-one-person-startup)
  - [The Consulting Engineer](#the-consulting-engineer)
  - [The Hardware Team Lead](#the-hardware-team-lead)
  - [The Maker Business](#the-maker-business)
  - [The Python Developer](#the-python-developer)
- [The Technical Foundation](#the-technical-foundation)
  - [Flexible Inventory Management](#flexible-inventory-management)
  - [Component Matching Intelligence](#component-matching-intelligence)
  - [Fabricator Abstraction](#fabricator-abstraction)
- [Design Principles](#design-principles)
- [Level 0 User Story Summary](#level-0-user-story-summary)
  - [The Core Value Proposition](#the-core-value-proposition)
  - [Core Workflows Covered](#core-workflows-covered)
  - [User Perspectives Addressed](#user-perspectives-addressed)
  - [Key Capabilities Validated](#key-capabilities-validated)
  - [Scope Boundaries Established](#scope-boundaries-established)

</details>

## The jBOM Story

### The Problem: Conflating electronic design requirements with supply chain choices

KiCad has the ability to generate Bill-of-Materials (BOMs) based on the components and their attributes found in the KiCad project files. By default, these BOMs are insufficient for fabrication use because KiCad's component libraries do not include supply chain details.

| Designator                              | Footprint                                                 | Quantity | Value                | Manufacturer Part # |
| --------------------------------------- | --------------------------------------------------------- | -------- | -------------------- | ----------- |
| C1, C2, C4                              | C_0603_1608Metric                                         | 3        | 0.1uF                |             |
| C3                                      | C_0805_2012Metric                                         | 1        | 10uF                 |             |
| C5                                      | CP_Elec_8x10                                              | 1        | 150uF                |             |
| CON1, CON2                              | PhoenixContact_MSTBA_2,5_4-G-5,08_1x04_P5.08mm_Horizontal | 2        | CONNECTOR-M045.08    |             |
| Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8          | SOIC-8_3.9x4.9mm_P1.27mm                                  | 8        | DMN4468              |             |
| R1, R2, R3, R4, R5, R6, R7, R8, R9, R10 | R_0603_1608Metric                                         | 10       | 10k                  |             |
| U1                                      | TSSOP-28_4.4x7.8mm_P0.5mm                                 | 1        | PCA9685PW            |             |
| VR1                                     | TO-252-2                                                  | 1        | 7805                 |             |
|                                         |                                                           |          |                      |             |

KiCad users can add supply chain details (like Manufacturer part numbers) to their KiCad projects, either piecemeal, by curating their own libraries with this information added to each component, or by leveraging KiCad's support for Web/Database libraries.

All these solutions mix design and procurement decisions together and encode the result into the KiCad project files.

While this process obviously works, it has a couple of downsides:
1. Component libraries explode in complexity.
   Instead of having a single "resistor" symbol that encompasses footprint patterns for all the resistor package variations, and having the schematic designer fill in the resistor's electrical properties (`1k`, `5% tolerance`, `100mW`) and the PCB designer choose a footprint, these inventory-aware libraries contain hundreds of "resistor" symbols, one for each combination of [`value`, `footprint` and `supplier`].
2. Supply chain decisions become KiCad Project tech debt
   When supply chains change during a product's lifecycle, the hard coded supply chain decisions become a liability.  Changing a supplier part number means editing every project that used that component, which adds risk and cost.


### Meet Alex, an Electronic Product Development Engineer

Alex runs a small electronics consulting company. One day, Alex is designing analog circuits in KiCad. tbe next afternoon, Alex is researching component suppliers and updating inventory spreadsheets. Later, Alex is generating manufacturing files for projects going out to three different fabricators. Once Alex catches Alex's breath, Alex is updating Alex's inventory stock, adding new components and replacing obsolete and expensive ones.

Some might have the luxury of separate engineering and procurement teams, but Alex needs to wear multiple hats efficiently without getting bogged down in the complexity of each role.

### The Challenge: Context Switching

When Alex is in "circuit design mode," thinking about op-amp slew rates and filter responses, the last thing Alex wants to worry about is whether JLCPCB stocks a particular resistor value or what the Mouser stock number is for a specific capacitor.

But when Alex switches to "procurement mode," Alex needs detailed supplier information, current pricing, and availability data to make smart business decisions about which fabricator to use and which components to stock.

### How jBOM Enables Efficient Context Switching

jBOM lets Alex work in the appropriate context for each task without losing the benefits of integration.

**Design Context**: Alex focuses purely on electrical and mechanical requirements:
- 1k resistor with `R_0603_1608Metric` footprint for the bias network
- 100nF ceramic capacitor with `C_0603_1608Metric` for decoupling
- LM358 op-amp for the input buffer

**Procurement Context**: Alex manages supplier relationships and inventory:
- Multiple 1k options: UNI-ROYAL (5% tolerance, LCSC C25585), YAGEO (1% precision, lower cost)
- Bulk capacitor sourcing from Mouser for consistent supply
- Op-amp alternatives for different fabricators and volume requirements

**Manufacturing Context**: Alex generates complete fabricator-specific packages:
- Gerber files and drill files for PCB fabrication
- JLCPCB BOM with LCSC part numbers for prototype runs
- PCBWay BOM with Mouser alternatives for production volumes
- CPL files with precise component placement data
- Complete packages ready for fabricator submission

## User Journeys

### Journey 1: Separating Design from Supply Chain Decisions

**Starting Point**: Alex has a new circuit design that needs to go to production.

**"I want to focus on getting the circuit right, then deal with manufacturing later."**

**Design Phase**:
1. Alex creates a KiCad project focused on electrical requirements
   - Selects KiCad schematic symbols and annotates them with electrical specifications (value, tolerance, power rating)
   - Associates KiCad footprints with components based on physical packages and board constraints
   - Validates electrical specifications meet design requirements
   - Verifies footprint selections meet board design constraints

2. Alex validates the KiCad project's electrical design through iteration
   - Tests component specifications against circuit requirements
   - Refines component attributes based on testing results
   - Modifies KiCad component specifications in project files
   - Maintains KiCad design focus on electrical and physical requirements

#### The Problem Without jBOM:
Alex could
1. produce a minimal design using the standard KiCad libraries that do not provide supply chain details, or
2. manually fully specify supply chain attributes in the symbols Alex uses, or use custom-curated component libraries that have this information, or Alex could use KiCad's database/Web library integration with `git-plm`'s inventory management system, each of which embeds supply chain choices as component attributes directly into the project's KiCad design files.

After the KiCad project is complete, Alex would use KiCad to generate the artifacts needed for fabrication, including a BOM.
With the first option above, the BOM would **not** contain the manufacturer and supplier information needed for fabrication, so someone would need to manually research and add that information for every component.
With the second, the BOM **would** provide sufficient details, at the cost of requiring premature procurement decisions during circuit design and maintenance debt when suppliers or part numbers change.

#### The Solution With jBOM:

Use the jBOM app to generate a fully specified BOM from a minimal KiCad project and an inventory that contains supply chain information.

**End Result**: **jBOM's Value**: Alex keeps electrical design decisions (1kΩ resistor, 0603 package) separate from supply chain decisions (UNI-ROYAL vs YAGEO, LCSC vs Mouser). The same electrical design can serve different fabricators and sourcing strategies over the product lifecycle without KiCad file changes.

### Journey 2: Inventory-Driven Component Discovery

**Starting Point**: Alex encounters components in projects that aren't in the current inventory.

**"When I use a component not in my inventory, I want to quickly find and add suitable supplier options."**

#### The Problem Without jBOM:
1. Alex would manually research each new component for supplier availability and pricing.
2. Without systematic inventory management, Alex would repeatedly research the same components across different projects.

#### The Solution With jBOM:

Use the jBOM app to identify the new components, search for candidates using supplier catalogs, add results to the Inventory for furute use.
**End Result**: **jBOM's Value**: Alex systematically builds inventory knowledge through project work. Each new component research effort benefits all future projects that use similar components. The inventory becomes a reusable asset that reduces per-project research time.

### Journey 3: Fabricator-Neutral Design Strategy

**Starting Point**: Alex wants to use different fabricators for different phases of product lifecycle.

**"I want to prototype with JLCPCB but move to PCBWay for production without redesigning."**

#### The Problem Without jBOM:
1. Alex would design without fabricator / supply chain information, choosing to add it later
2. Alex would design specifically for one fabricator (losing flexibility)
3. Alex would maintain separate versions of each design for different fabricators or maintain data for multiple fabrication chains in one design file (adding complexity)

#### The Solution With jBOM:
1. Alex would design without fabricator / supply chain information, and then use different fabricator profiles and inventories with jBOM to create the correct files needed for each vendor.

**End Result**: **jBOM's Value**: The same KiCad design serves multiple fabricators through inventory-based supply chain mapping. Business decisions about fabricators can be made based on cost, capability, and availability without forcing design changes.

### Journey 4: Automated Manufacturing File Integration

**Starting Point**: Alex's design is ready for fabrication and assembly.

**"I need all manufacturing files that work correctly the first time - fabrication and assembly mistakes are expensive."**

#### The Problem Without jBOM:

1. Alex would manually generate Gerbers in KiCad, export CPL and BOM files BOM, and manually add the required supply chain information to the BOM file.
2. Alex would choose to add LCSC part numbers to Alex's KiCad projects and use the JLC Fabrication Plugin to automatically create all the Gerber, CPL and BOM files required by JLCPCB.
3. Alex would choose to add Manufacture Part Numbers to Alex's KiCad projects and use the PCBWay Fabrication Plugin to automatically create all the Gerber, CPL and BOM files required by PCBWay.

#### The Solution With jBOM:

jBOM's fabricator specific profiles capture the details specific to each vendor, so that it can offer repeatability and confidence.

**End Result**: **jBOM's Value**: jBOM orchestrates KiCad's file generation capabilities with inventory-driven BOMs and fabricator-specific formatting to produce complete, consistent manufacturing packages. What took hours of manual coordination now happens with a single command.

### Journey 5: Supplier Integration and Alternative Sourcing

**Starting Point**: Alex needs to expand supplier options and find alternatives when primary sources have issues.

**"I want to find alternative suppliers for my standard components and detect when primary sources have availability issues."**

#### The Problem Without jBOM:
Alex would manually research alternative suppliers for each component, visit multiple distributor websites, and maintain separate spreadsheets for different supplier ecosystems.

#### The Solution With jBOM:
Inventories may contain multiple items that are drop-in replacements for unavailable parts;

**End Result**: **jBOM's Value**: Because design requirements are separated from supply chain details, Alex can adapt to market changes, supplier disruptions, and component obsolescence without touching KiCad files. Resilience comes from this architectural separation, not just good planning.

## Real-World Scenarios

### The One-Person Startup
Alex is developing IoT sensors for agriculture. Monday: designing power management circuits. Tuesday: researching battery suppliers. Wednesday: generating BOMs for prototype quotes. Thursday: updating inventory with new sensor options. jBOM enables efficient context switching without losing the benefits of integration across all these activities.

### The Consulting Engineer
Alex handles projects for multiple clients, each with different fabricator preferences and cost constraints. Client A prefers JLCPCB for speed, Client B requires PCBWay for specific capabilities, Client C needs domestic suppliers only. Same design discipline, different procurement strategies - jBOM handles the complexity.

### The Hardware Team Lead
Alex manages three junior engineers' designs while handling all procurement and manufacturing coordination. Engineers focus on circuits, Alex handles supply chain. jBOM enables this division of labor while maintaining integration - engineers' component choices automatically flow into Alex's procurement workflow.

### The Maker Business
Alex sells open-source hardware kits. Designs must work reliably for customers building at home, but Alex needs competitive pricing for kit sales. jBOM enables customer-friendly designs (standard components, multiple sourcing options) while optimizing Alex's procurement costs.

### The Python Developer
Alex is a Python programmer who wants to leverage jBOM's capabilities for custom automation workflows. Using jBOM as a Python package, Alex builds tools that:
- Analyze component usage patterns across multiple project directories
- Generate custom reports combining electrical specifications with business data
- Automate inventory updates by integrating multiple supplier APIs
- Create specialized matching rules for organization-specific component standards
- Build web interfaces for team-based inventory management

Alex doesn't need jBOM's CLI or KiCad plugin directly - the Python package provides the core KiCad file parsing, inventory management, and supplier API capabilities that Alex integrates into larger automation solutions.

## The Technical Foundation

### Flexible Inventory Management
Alex can maintain inventory however works best:
- Single master spreadsheet for small operations
- Separate files per supplier for complex sourcing
- Multiple formats: CSV for automated processing, Excel for manual updates, Numbers for team collaboration
- jBOM combines sources intelligently while preserving Alex's organizational preferences

### Component Matching Intelligence
jBOM handles the complexity of matching circuit requirements to available components:
- Electrical substitution rules: 1% resistor can substitute for 5% requirement
- Format normalization: "1.1K", "1k1", "1100" all match the same inventory item
- Package compatibility: helps Alex understand when footprint changes are needed
- Tolerance analysis: automatically uses higher-precision parts when available

### Fabricator Abstraction
Alex's designs work across fabricators through intelligent adaptation:
- Same electrical specifications, different supplier ecosystems
- Format adaptation: JLCPCB CSV vs PCBWay Excel vs custom formats
- Field mapping: "LCSC" column for JLCPCB, "Mouser" column for PCBWay, same component data

## Design Principles

**Context-Appropriate Tools**: jBOM provides the right information for each phase of work - electrical specs during design, supplier details during procurement, manufacturing data during production.

**Efficient Context Switching**: Alex can move between design, procurement, and manufacturing contexts without losing integration benefits or being forced into premature decisions.

**Institutional Learning**: Inventory files capture Alex's supplier research and component experience, making future projects more efficient.

**Supply Chain Resilience**: Multiple sourcing options and fabricator flexibility protect against supplier disruptions and enable business optimization.

**Real-World Pragmatism**: jBOM works with Alex's existing tools and processes rather than forcing new workflows or data formats.

**API-First Architecture**: jBOM's core capabilities are available as a Python package for custom automation, while CLI and KiCad plugin provide ready-to-use interfaces for common workflows.

## Level 0 User Story Summary

This document captures the complete Level 0 user stories for jBOM, demonstrating how the tool solves the fundamental problem of **conflating electronic design requirements with supply chain choices**.

### The Core Value Proposition
jBOM enables **separation of concerns**: electrical requirements stay in KiCad projects, supply chain intelligence lives in inventory systems, and the two integrate seamlessly for manufacturing. This architectural separation makes designs resilient to supply chain changes and enables efficient context switching between design and procurement activities.

### Core Workflows Covered
1. **Design-Supply Chain Separation**: Maintaining electrical requirements in KiCad while managing supplier details in inventory
2. **Component Discovery**: Systematically researching and adding new components to inventory
3. **Multi-Fabricator Strategy**: Same design serving different fabricators through inventory-based mapping
4. **Manufacturing Package Generation**: Automated creation of complete fabricator submission packages
5. **Alternative Sourcing**: Finding and managing multiple suppliers for supply chain resilience
6. **Supply Chain Adaptation**: Handling component changes without modifying validated designs

### User Perspectives Addressed
- **Single-person operations**: Alex wearing multiple hats (design, procurement, manufacturing)
- **Team scenarios**: Division of labor while maintaining workflow integration
- **Business contexts**: Startup, consulting, maker business, and development automation
- **Python integration**: jBOM as a package for custom automation workflows

### Key Capabilities Validated
- KiCad project processing (schematics, PCBs, hierarchical designs)
- Multi-source inventory management (CSV, Excel, Numbers, supplier APIs)
- Component matching algorithms (direct, fuzzy, tolerance-based)
- Fabricator abstraction (JLCPCB, PCBWay, generic formats)
- Complete manufacturing file generation
- Error handling and graceful degradation

### Scope Boundaries Established
Out of scope: Design rule checking, compliance tracking, production traceability, cost modeling beyond component pricing, assembly documentation generation.

These Level 0 stories provide the foundation for Level 1 feature decomposition and Level 2 functional interface definition.
