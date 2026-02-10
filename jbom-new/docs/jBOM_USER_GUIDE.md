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
  - [Journey 6: Supply Chain Adaptation Without Design Changes](#journey-6-supply-chain-adaptation-without-design-changes)
    - [The Problem Without jBOM:](#the-problem-without-jbom-5)
    - [The Solution With jBOM:](#the-solution-with-jbom-5)
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

Alex runs a small electronics consulting company. One day, Alex is designing analog circuits in KiCad. tbe next afternoon, Alex is researching component suppliers and updating inventory spreadsheets. Later, Alex is generating manufacturing files for projects going out to three different fabricators. Once he catches his breath, Alex is updating his inventory stock, adding new components and replacing obsolete and expensive ones.

Some might have the luxury of separate engineering and procurement teams, but Alex needs to wear multiple hats efficiently without getting bogged down in the complexity of each role.

### The Challenge: Context Switching

When Alex is in "circuit design mode," thinking about op-amp slew rates and filter responses, the last thing he wants to worry about is whether JLCPCB stocks a particular resistor value or what the Mouser stock number is for a specific capacitor.

But when Alex switches to "procurement mode," he needs detailed supplier information, current pricing, and availability data to make smart business decisions about which fabricator to use and which components to stock.

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

#### The Problem Without jBOM:
1. Alex could produce a design using standard KiCad libraries without supply chain details. The resulting BOM would lack manufacturer and supplier information needed for fabrication. Someone would need to manually research and add this information for every component, for every fabricator—a time-consuming, error-prone process that must be repeated for each project.
2. Alex could use supplier-specific component libraries, embedding supply chain choices directly in the design. This trades off simple BOM production for premature procurement decisions during circuit design and creates maintenance debt when suppliers or part numbers change.

#### The Solution With jBOM:

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

**Procurement Phase**:
@Scenario: `[Validate.Coverage]`
1. Alex validates a KiCad project's component usage against inventory items
@Steps:
   - `[Identify.Project]` Identify the KiCad project to validate against inventory
   - `[Extract.Components]` Extract component specifications from KiCad project files
   - `[Extract.Inventory]` Extract available items from inventory files
   - `[Match.Components]` Compare KiCad project components with inventory items to identify matches
   - `[Identify.Ambiguous]` Identify ambiguous project components that matched multiple inventory items
   - `[Identify.Orphans]` Identify orphan project components that didn't match inventory items
   - `[Identify.Obsolete]` Identify obsolete project components that matched retired inventory items

@Scenario: `[Research.Components]`
2. Alex researches supplier options for orphan components
@Steps:
   - `[Select.Orphans]` Select orphan components requiring supplier research
   - `[Search.Suppliers]` Search supplier databases for parts matching electrical specifications
   - `[Evaluate.Options]` Evaluate supplier options based on suitability, cost, availability, and lead times
   - `[Add.Items]` Add selected items to inventory files with complete supplier information
   - `[Add.Alternatives]` Add alternative items from multiple suppliers for drop-in replacement if needed

**Manufacturing Phase**:
@Scenario: `[Create.Package]`
1. Alex generates fabricator-specific manufacturing packages for a KiCad project using inventory data
@Steps:
   - `[Identify.Project]` Identify the KiCad project to process for manufacturing
   - `[Extract.Components]` Extract component specifications from KiCad project files
   - `[Extract.Inventory]` Extract available items from inventory files
   - `[Filter.Suppliers]` Filter inventory to match fabricator supplier ecosystem
   - `[Match.Components]` Match project components to filtered inventory items
   - `[Resolve.Conflicts]` Resolve ambiguous matches and missing components
   - `[Generate.BOM]` Generate fabricator-compatible Bill of Materials
   - `[Generate.CPL]` Generate component placement file from KiCad PCB data
   - `[Generate.CAM]` Generate Gerber and drill files for PCB fabrication
   - `[Format.Files]` Format all files according to fabricator specifications
   - `[Validate.Package]` Validate manufacturing package completeness

@Scenario: `[Customize.Profile]`
2. Alex creates and customizes supplier and fabricator profiles as needed
@Steps:
   - `[Identify.Requirements]` Identify specific fabricator or supplier requirements not met by default profiles
   - `[Gather.Specifications]` Gather supply chain information provided by fabricator or supplier
   - `[Create.Profile]` Create new profile configuration for custom fabrication workflow
   - `[Configure.Formats]` Configure file formats and field mappings for custom requirements
   - `[Test.Profile]` Test profile with sample project to verify correct output generation
   - `[Document.Usage]` Document profile usage for team members and future reference

**End Result**: **jBOM's Value**: Alex keeps electrical design decisions (1kΩ resistor, 0603 package) separate from supply chain decisions (UNI-ROYAL vs YAGEO, LCSC vs Mouser). The same electrical design can serve different fabricators and sourcing strategies over the product lifecycle without KiCad file changes.

### Journey 2: Inventory-Driven Component Discovery

**Starting Point**: Alex encounters components in new projects that aren't in the current inventory.

**"When I use a component not in my inventory, I want to quickly find and add suitable supplier options."**

#### The Problem Without jBOM:
1. Alex would manually research each new component for supplier availability and pricing.
2. Without systematic inventory management, Alex would repeatedly research the same components across different projects.

#### The Solution With jBOM:

**Component Discovery Process**:
@Scenario: `[Validate.Coverage]`
1. Alex validates a KiCad project's component usage against inventory items
@Steps:
   - `[Identify.Project]` Identify the KiCad project to validate against inventory
   - `[Extract.Components]` Extract component specifications from KiCad project files
   - `[Extract.Inventory]` Extract available items from inventory files
   - `[Match.Components]` Compare KiCad project components with inventory items to identify matches
   - `[Identify.Ambiguous]` Identify ambiguous project components that matched multiple inventory items
   - `[Identify.Orphans]` Identify orphan project components that didn't match inventory items
   - `[Identify.Obsolete]` Identify obsolete project components that matched retired inventory items
   - `[Report.Coverage]` Generate coverage report showing matches, orphans, and conflicts
   - `[Prioritize.Research]` Prioritize orphan components for supplier research based on project importance

@Scenario: `[Research.Components]`
2. Alex researches supplier options for orphan components
@Steps:
   - `[Select.Orphans]` Select orphan components requiring supplier research
   - `[Define.Specifications]` Define electrical and physical specifications for supplier search
   - `[Search.Suppliers]` Search supplier databases for parts matching specifications
   - `[Compare.Options]` Compare available options across multiple suppliers
   - `[Evaluate.Suitability]` Evaluate supplier options for electrical compatibility
   - `[Assess.Business]` Assess supplier options for cost, availability, and lead times
   - `[Select.Candidates]` Select desirable items for inventory addition
   - `[Add.Items]` Add selected items to inventory files with complete supplier information
   - `[Add.Alternatives]` Add alternative items from multiple suppliers for sourcing flexibility

@Scenario: `[Validate.Completeness]`
3. Alex validates inventory coverage for the KiCad project
@Steps:
   - `[Re-extract.Components]` Re-extract components from KiCad project after inventory updates
   - `[Re-extract.Inventory]` Re-extract updated inventory with newly added items
   - `[Re-match.Components]` Re-match project components against updated inventory
   - `[Verify.Coverage]` Verify all KiCad project components can be matched with inventory items
   - `[Test.Generation]` Test fabricator-specific BOM generation with complete supplier information
   - `[Confirm.Capability]` Confirm manufacturing packages can be generated successfully
   - `[Document.Results]` Document validation results for project records

**End Result**: **jBOM's Value**: Alex systematically builds inventory knowledge through project work. Each new component research effort benefits all future projects that use similar components. The inventory becomes a reusable asset that reduces per-project research time.

### Journey 3: Fabricator-Neutral Design Strategy

**Starting Point**: Alex wants to use different fabricators for different phases of product lifecycle.

**"I want to prototype with JLCPCB but move to PCBWay for production without redesigning."**

#### The Problem Without jBOM:
1. Alex would design without fabricator / supply chain information, choosing to add it later
2. Alex would design specifically for one fabricator (losing flexibility)
3. Alex would maintain separate versions of each design for different fabricators or maintain data for multiple fabrication chains in one design file (adding complexity)

#### The Solution With jBOM:

**Multi-Fabricator Workflow**:
@Scenario: `[Create.Design]`
1. Alex completes a KiCad design with supplier-neutral component specifications
@Steps:
   - `[Select.Symbols]` Select KiCad schematic symbols from standard component libraries
   - `[Annotate.Specifications]` Annotate symbols with electrical specifications (value, tolerance, power rating)
   - `[Associate.Footprints]` Associate KiCad footprints with components based on physical packages
   - `[Verify.Neutrality]` Verify component specifications remain fabricator-neutral
   - `[Document.Requirements]` Document electrical and physical requirements in KiCad project
   - `[Maintain.Independence]` Maintain KiCad design independence from specific supplier or fabricator choices

@Scenario: `[Create.Package]`
2. Alex generates fabricator-specific manufacturing packages for the KiCad project using inventory data
@Steps:
   - `[Identify.Fabricator]` Identify target fabricator for manufacturing package generation
   - `[Extract.Components]` Extract component specifications from KiCad project files
   - `[Extract.Inventory]` Extract available items from inventory files
   - `[Filter.Inventory]` Filter inventory files to match fabricator supplier ecosystem preferences
   - `[Match.Components]` Match project components to fabricator-filtered inventory items
   - `[Resolve.Conflicts]` Resolve component matches for fabricator-specific requirements
   - `[Generate.BOM]` Generate fabricator-compatible BOM using filtered inventory data
   - `[Generate.Files]` Generate complete manufacturing file package for fabricator submission
   - `[Validate.Package]` Validate package meets fabricator specifications and requirements

@Scenario: `[Switch.Fabricators]`
3. Alex switches fabricators based on business needs for the same KiCad project
@Steps:
   - `[Assess.Requirements]` Assess current project requirements for fabricator selection
   - `[Evaluate.Fabricators]` Evaluate available fabricator options based on cost, capability, and schedule
   - `[Select.Fabricator]` Select optimal fabricator for current business needs
   - `[Filter.Inventory]` Filter inventory using different fabricator supplier ecosystem
   - `[Re-match.Components]` Re-match project components against new fabricator's inventory filter
   - `[Generate.Package]` Generate manufacturing package for new fabricator using same KiCad project
   - `[Compare.Options]` Compare fabricator options and validate business decision
   - `[Maintain.Flexibility]` Ensure inventory supports multiple fabricator switching options

**End Result**: **jBOM's Value**: The same KiCad design serves multiple fabricators through inventory-based supply chain mapping. Business decisions about fabricators can be made based on cost, capability, and availability without forcing design changes.

### Journey 4: Automated Manufacturing File Integration

**Starting Point**: Alex's design is ready for fabrication and assembly.

**"I need all manufacturing files that work correctly the first time - fabrication and assembly mistakes are expensive."**

#### The Problem Without jBOM:

1. Alex would manually generate Gerbers in KiCad, export CPL and BOM files BOM, and manually add the required supply chain information to the BOM file.
2. Alex would choose to add LCSC part numbers to his KiCad projects and use the JLC Fabrication Plugin to automatically create all the Gerber, CPL and BOM files required by JLCPCB.
3. Alex would choose to add Manufacture Part Numbers to his KiCad projects and use the PCBWay Fabrication Plugin to automatically create all the Gerber, CPL and BOM files required by PCBWay.

#### The Solution With jBOM:

**Manufacturing Package Generation**:
@Scenario: `[Create.Package]`
1. Alex generates fabricator-specific manufacturing packages for the KiCad project using inventory data
@Steps:
   - `[Identify.Project]` Identify the KiCad project ready for manufacturing package generation
   - `[Identify.Fabricator]` Identify target fabricator and manufacturing requirements
   - `[Extract.Components]` Extract component specifications from KiCad project files
   - `[Extract.Inventory]` Extract available items from inventory files
   - `[Filter.Suppliers]` Filter inventory to match fabricator supplier ecosystem
   - `[Match.Components]` Match project components to fabricator-filtered inventory items
   - `[Resolve.Conflicts]` Resolve component matching conflicts and missing items
   - `[Generate.CAM]` Generate PCB fabrication files (Gerbers, drill files) from KiCad PCB data
   - `[Generate.BOM]` Generate fabricator-compatible BOM combining KiCad and inventory data
   - `[Generate.CPL]` Generate component placement file from KiCad PCB positioning data
   - `[Format.Files]` Format all files according to fabricator specifications and requirements
   - `[Package.Files]` Package all manufacturing files for fabricator submission
   - `[Validate.Package]` Validate manufacturing package completeness and consistency

@Scenario: `[Customize.Profiles]`
2. Alex creates and customizes fabricator profiles as needed
@Steps:
   - `[Assess.Needs]` Assess current fabricator profile coverage against business requirements
   - `[Identify.Gaps]` Identify fabricator or supplier requirements not met by default profiles
   - `[Gather.Specifications]` Gather fabricator specifications for file formats and field requirements
   - `[Design.Profile]` Design profile configuration for custom fabrication workflow
   - `[Configure.Formats]` Configure file formats, field mappings, and naming conventions
   - `[Configure.Filters]` Configure supplier filtering rules for fabricator ecosystem
   - `[Test.Profile]` Test profile with sample project to verify correct output generation
   - `[Validate.Output]` Validate generated files meet fabricator submission requirements
   - `[Document.Usage]` Document profile usage and configuration for future reference

@Scenario: `[Validate.Package]`
3. Alex validates manufacturing package completeness
@Steps:
   - `[Check.Files]` Check all required fabricator files are present in package
   - `[Verify.Formats]` Verify file formats match fabricator specifications exactly
   - `[Validate.Data]` Validate data consistency between BOM, CPL, and CAM files
   - `[Check.Components]` Check all project components have supplier information in BOM
   - `[Verify.Placement]` Verify component placement data matches PCB layout
   - `[Test.Fabrication]` Test package with fabricator validation tools if available
   - `[Confirm.Readiness]` Confirm files are ready for fabricator submission
   - `[Archive.Package]` Archive complete package for project records and resubmission

**End Result**: **jBOM's Value**: jBOM orchestrates KiCad's file generation capabilities with inventory-driven BOMs and fabricator-specific formatting to produce complete, consistent manufacturing packages. What took hours of manual coordination now happens with a single command.

### Journey 5: Supplier Integration and Alternative Sourcing

**Starting Point**: Alex needs to expand supplier options and find alternatives when primary sources have issues.

**"I want to find alternative suppliers for my standard components and detect when primary sources have availability issues."**

#### The Problem Without jBOM:
Alex would manually research alternative suppliers for each component, visit multiple distributor websites, and maintain separate spreadsheets for different supplier ecosystems.

#### The Solution With jBOM:

**Alternative Supplier Development**:
@Scenario: `[Expand.Coverage]`
1. Alex expands supplier coverage for existing inventory Items
@Steps:
   - `[Analyze.Inventory]` Analyze current inventory to identify items with limited sourcing options
   - `[Prioritize.Items]` Prioritize items for supplier expansion based on project usage and business impact
   - `[Define.Criteria]` Define search criteria for alternative suppliers (electrical, mechanical, business requirements)
   - `[Search.Suppliers]` Search additional supplier databases for items with limited sourcing options
   - `[Compare.Specifications]` Compare alternative supplier specifications against existing inventory items
   - `[Evaluate.Business]` Evaluate alternative suppliers based on cost, availability, lead times, and reliability
   - `[Assess.Compatibility]` Assess electrical and mechanical compatibility of alternative supplier options
   - `[Select.Candidates]` Select best alternative supplier candidates for inventory addition
   - `[Add.Items]` Add selected alternative items to inventory files with complete supplier information
   - `[Test.Coverage]` Test expanded supplier coverage with sample projects
   - `[Document.Sources]` Document alternative sourcing strategies for team knowledge

@Scenario: `[Address.Constraints]`
2. Alex addresses supplier availability constraints in inventory
@Steps:
   - `[Monitor.Availability]` Monitor supplier availability and identify constrained or at-risk items
   - `[Identify.Constrained]` Identify inventory items with limited or restricted supplier availability
   - `[Assess.Impact]` Assess business impact of supplier constraints on current and planned projects
   - `[Research.Alternatives]` Research parts catalogs for alternative sources offering equivalent components
   - `[Evaluate.Equivalents]` Evaluate alternative components for electrical and mechanical compatibility
   - `[Assess.Business]` Assess alternative suppliers for business suitability (cost, reliability, lead times)
   - `[Validate.Substitution]` Validate component substitutions meet design requirements
   - `[Update.Inventory]` Update inventory files with suitable alternative items
   - `[Test.Substitutions]` Test substitutions with existing projects to verify compatibility
   - `[Communicate.Changes]` Communicate supplier changes and alternatives to project stakeholders

**End Result**: **jBOM's Value**: jBOM provides systematic alternatives discovery and supplier diversification without requiring changes to KiCad projects. Multiple sourcing options reduce supply chain risk while maintaining design stability.

### Journey 6: Supply Chain Adaptation Without Design Changes

**Starting Point**: Real-world supply chain disruptions require component substitutions.

**"When supply chain issues arise, I want to adapt without touching my validated designs."**

#### The Problem Without jBOM:

When suppliers change or parts become unavailable, Alex would need to update multiple KiCad projects individually, risking introduction of errors and requiring extensive validation.

#### The Solution With jBOM:

**Supply Chain Adaptation**:
@Scenario: `[Handle.Disruptions]`
1. Alex handles component availability disruptions in inventory
@Steps:
   - `[Monitor.Supply]` Monitor supplier announcements and availability status for inventory items
   - `[Identify.Unavailable]` Identify inventory items that become unavailable from current suppliers
   - `[Assess.Impact]` Assess impact of unavailable items on current and planned projects
   - `[Prioritize.Replacements]` Prioritize replacement research based on project criticality and timelines
   - `[Search.Alternatives]` Search parts catalogs for electrically compatible alternatives with equivalent specifications
   - `[Evaluate.Compatibility]` Evaluate alternative components for electrical and mechanical compatibility
   - `[Assess.Business]` Assess alternative suppliers for business suitability (cost, availability, reliability)
   - `[Validate.Substitutions]` Validate component substitutions maintain design integrity
   - `[Add.Replacements]` Add suitable replacement items to inventory files with compatibility notes
   - `[Test.Projects]` Test affected projects with new component substitutions
   - `[Document.Changes]` Document supply chain disruption response for future reference

@Scenario: `[Manage.Changes]`
2. Alex manages supplier relationship changes in inventory
@Steps:
   - `[Track.Relationships]` Track supplier relationship changes, discontinuations, and market developments
   - `[Evaluate.Impact]` Evaluate impact of supplier changes on inventory and project portfolio
   - `[Plan.Adaptation]` Plan inventory adaptation strategy for supplier relationship changes
   - `[Research.Replacements]` Research replacement suppliers and alternative component sources
   - `[Migrate.Sources]` Migrate from discontinued or problematic suppliers to reliable alternatives
   - `[Update.Inventory]` Update inventory files with new supplier relationships and part numbers
   - `[Test.Continuity]` Test component sourcing continuity across affected projects
   - `[Maintain.Quality]` Maintain component quality standards during supplier transitions
   - `[Preserve.Designs]` Preserve KiCad design stability while adapting supply chain relationships
   - `[Communicate.Transitions]` Communicate supplier transitions to project stakeholders

@Scenario: `[Optimize.Components]`
3. Alex optimizes component choices through KiCad design iteration
@Steps:
   - `[Analyze.Usage]` Analyze component usage patterns across project portfolio
   - `[Identify.Opportunities]` Identify optimization opportunities based on supplier relationships
   - `[Evaluate.Alternatives]` Evaluate component alternatives that leverage existing supplier relationships
   - `[Assess.Performance]` Assess performance impact of component specification changes
   - `[Plan.Changes]` Plan component specification changes in KiCad projects
   - `[Modify.Specifications]` Modify component specifications in KiCad project files
   - `[Validate.Coverage]` Validate updated project components against current inventory
   - `[Test.Designs]` Test design changes to ensure electrical and mechanical compatibility
   - `[Leverage.Relationships]` Leverage existing supplier relationships for cost and availability benefits
   - `[Document.Optimization]` Document component optimization decisions and rationale

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
