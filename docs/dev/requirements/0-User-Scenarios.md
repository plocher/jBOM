## Features and Scenarios
### Meet Alex, an Electronic Product Development Engineer

Alex runs a small electronics consulting company. One day might be spent designing analog circuits in KiCad, while the next, researching component suppliers and updating inventory spreadsheets. Once those tasks are complete, manufacturing files need to be generated for projects going out to three different fabricators. In the midst of all this, choices about suppliers, invoices, inventory management need to be made, all of which impact product production.

Some might have the luxury of separate engineering and procurement teams, but Alex needs to wear multiple hats efficiently without getting bogged down in the complexity of each role.  The following scenarios demonstrate how Alex integrates jBOM into their electronic project workflow.

### @Scenario: `[Generate.Inventory]`
Alex creates an initial inventory from the components used in an existing KiCad project
@Steps:
   - `[Specify.Project]`    Specify the KiCad project to use
   - `[Extract.Components]` Extract component specifications from KiCad project files
   - `[Create.Inventory]`   Create an inventory that includes these new components

@Documentation:
Alex starts with a KiCad project.  Or two.  Or more...  As the number of projects grow, so does the complexity of managing eCAD designs, production needs and product distribution. When old projects becomes popular and orders flood in, the effort needed to update the old KiCad design files and BOMs to reflect current availability and component costs becomes overwhelming.

Alex does not want to modify KiCad project files every time supply chain details change, but would prefer to extract the supply chain details and deal with them seperately.  Once extracted, Alex wants to select parts in supplier catalogs that match the design requirements, and use them to generate the Bill of Materials artifacts used by their fabrication vendor:
  - Specify the KiCad projects of interest
  - Select candidate parts from the supplier catalogs
  - Create an inventory artifact that can be used to create BOMs

The items in an inventory created from a KiCad project will reflect the components and attributes from the KiCad project.
By default, KiCad's component libraries do not include supply chain details, though KiCad users can add supply chain details (e.g., Manufacturer part numbers) to their KiCad projects, either piecemeal, by curating their own libraries with this information added to each component, or by leveraging KiCad's support for Web/Database libraries.

jBOM's inventories add another, less invasive way to manage KiCad supply chain details. Inventory csv/spreadsheets associate Manufacturer and supplier part information with the electronic and mechanical details. jBOM can then match inventory items to KiCad components when constucting the Bill of Materials files for a fabricator.

In this scenario, Alex will create a new spreadsheet from KiCad projects that are missing these supply chain details.

#### Required Inventory columns

**IPN** (Internal Part Number)
: Unique identifier for this inventory item. jBOM uses IPN to group components in the BOM.

**Category**
: Component classification (RES, CAP, IND, LED, DIO, IC, MCU, CON, etc.). jBOM intuits the component type from the schematic component's attribute information. Used as first-stage filter.

**Value**
: Component value in appropriate units. Format depends on category:
  - RES: ohms (330, 330R, 3R3, 10k, 10K0, 2M2, 0R22, etc.)
  - CAP: farads (100nF, 0.1u, 1u0, 220pF, etc.)
  - IND: henrys (10uH, 2m2, 100nH, etc.)
  - DIO: part number or code,
  - LED: Color
  - IC/MCU: part number

**Package**
: Physical package code (0603, 0805, 1206, SOT-23, SOIC-8, QFN-32, etc.). Extracted from schematic and/or pcb footprint.

**Priority**
: Integer ranking (1 = most preferred, higher = less preferred). When multiple parts share the same IPN, those that remain after supplier filtering are chosen based on priority.  This allows you to prefer stocked parts (Priority=1) over others (Priority=2+).

**Manufacturer**
: Component manufacturer name (UNI-ROYAL, YAGEO, WIMA, etc.).

**MFGPN**
: Manufacturer part number.

**Supplier**
: Supplier name. Used to filter items when using a supplier profile.

**SPN**
: Supplier part number.

#### Optional Inventory columns

**Datasheet**
: URL to component datasheet PDF.

**Keywords**
: Comma-separated search keywords for components.

**SMD**
: Surface mount indicator (SMD, Y, YES, TRUE, 1 for SMD; PTH, THT, TH, N, NO, FALSE, 0 for through-hole). If omitted or unclear, jBOM infers from footprint.

**Tolerance**
: Tolerance rating (5%, 1%, ±10%, etc.). Used in conjunction with Value in scoring heuristics when available.

**V (Voltage)**
: Working voltage rating (25V, 50V, 75V, 400V, etc.).

**A (Amperage)**
: Current rating (100mA, 1A, 10A, etc.).

**W (Wattage)**
: Power dissipation rating (0.1W, 0.25W, 1W, etc.).

**Type**
: Component type variant (X7R for capacitors, Film for resistors, etc.).

**Form**
: Physical form factor (SPDT, DPDT for switches; Radial, Axial for through-hole resistors, etc.).

**Frequency**
: Operating frequency for oscillators and clocks (12MHz, 32.768kHz, etc.).

**Stability**
: Frequency stability rating for oscillators (±100ppm, ±50ppm, etc.).

**Load**
: Load capacitance for oscillators (20pF, 10pF, etc.).

**Family**
: Product family for microcontrollers and integrated circuits (ESP32, STM32F4, etc.).

**Wavelength**
: LED color or wavelength (Red, Green, Blue, 620nm, etc.).

**Angle**
: LED viewing angle (30°, 120°, etc.).

**mcd (Millicandela)**
: Directional brightness rating for LEDs (100mcd, 500mcd, etc.). Candela measures beam focus or intensity

**Lumens**
: Overall omnidirectional brightness rating for LEDs. Lumens measure total output

**Pitch**
: Connector pin pitch (2.54mm, 1.27mm, 0.5mm, etc.).

**Description**
: Human-readable description (330Ω 5% 0603 resistor, 100nF X7R ceramic capacitor, etc.).

**LCSC**
: Supplier part number from LCSC Electronics.  Deprecated - use **Supplier**=`LCSC` and **SPN**=`LCSC part number`

@End

### @Scenario: `[Search.Inventory]`
Alex resolves supplier options for inventory items that lack supply chain details

Use cases:
    * Find prospective items in a supplier's product catalog and associate them with items in the inventory
    * Add a new distributor to an inventory and associate existing inventory items with that distributor's offerings
    * Run one command that enriches and consolidates an inventory with data from multiple suppliers
    * Audit / update the inventory against current distributor and fabricator parts lists

@Steps:
   - `[Discover.Profiles]`  Discover available supply chain profiles
   - `[Specify.Inventory]`  Specify the existing Inventory to use
   - `[Extract.Items]`      Extract items from inventory files
   - `[Identify.Gaps]`      Identify items that lack supply chain details
   - `[Search.Suppliers]`   Search supplier catalogs for products that match the electro-mechanical attributes of the item
   - `[Select.Items]`       Use heuristics to identify a small pool of candidate parts for that item
   - `[Create.Inventory]`   Create an inventory with supply chain details

@Documentation:
Once Alex has an (incomplete) inventory, Alex would like to search supplier databases for parts that meet project needs:
  * find components that match the items in the online catalog (type, values, tolerances, etc, similar to the component matching BOM algorithm)
  * filter them to remove unsuitable results (non-stocked/long lead time etc)
  * filter them by quantity (is quantity needed (plus margin) more than available stock?  High stock levels can be a proxy for popularity and cost)
  * Heuristically sort the resulting list to find the "best" candidates
      - manufacturer, manufacturer part number, alternate manufacturing sources, alternate-but-equivalent part numbering schemes
      - Consistency with other inventory items, product families, ...
      - minimum quantity for ordering may filter out some candidates, depending on the quantity discount rates
      - price matters - all things equivalent, pick the lowest price

High-level workflow expectations for multi-supplier enrichment:
  * Alex can enrich from multiple suppliers in one run while keeping a single inventory artifact
  * each supplier pass contributes additively to the same IPN requirement pool
  * ranking/priority remains meaningful across all same-IPN items, even when items were discovered from different suppliers
@End

### @Scenario: `[Validate]`
Alex validates a KiCad project's component usage against inventory items
@Steps:
   - `[Discover.Profiles]`  Discover available supply chain profiles at runtime
   - `[Specify.Project]`    Specify the KiCad project to validate against inventory
   - `[Specify.Inventory]`  Specify the Inventory to use
   - `[Extract.Components]` Extract component specifications from KiCad project files
   - `[Extract.Items]`      Extract available items from inventory files
   - `[Match.Components]`   Compare KiCad project components with inventory items to identify matches
   - `[Identify.Ambiguous]` BOM content: Identify ambiguous project components that matched multiple inventory items
   - `[Identify.Orphans]`   BOM content: Identify orphan project components that didn't match inventory items
   - `[Identify.Obsolete]`  BOM content: Identify obsolete project components that matched retired inventory items
   - `[Create.BOM]`         Annotated BOM using inventory data

@Description:
Generating a BOM with jBOM will identify components that
  * matched an inventory item exactly
  * matched an alternate item using heuristics and derived data
  * didn't match any items.

A BOM with every component matched is ready for fabrication.

@End

### @Scenario: `[Generate]`
Alex generates fabricator-specific manufacturing packages for a KiCad project using inventory data
@Steps:
   - `[Discover.Profiles]`  Discover available supply chain profiles at runtime
   - `[Specify.Project]`    Specify the KiCad project to validate against inventory
   - `[Specify.Inventory]`  Specify the Inventory to use
   - `[Specify.Profile]`    Specify the supply chain profile to use
   - `[Extract.Components]` Extract component specifications from KiCad project files
   - `[Extract.Items]`      Extract available items from inventory files
   - `[Filter.Items]`       Filter inventory to match profile's supplier ecosystem
   - `[Match.Components]`   Compare KiCad project components with inventory items to identify matches
   - `[Resolve.Conflicts]`  Resolve ambiguous matches and missing components
   - `[Create.BOM]`         Fabricator-compatible Bill of Materials
   - `[Create.CPL]`         Fabricator-compatible component placement file
   - `[Create.CAM]`         Fabricator-compatible Gerber and drill files
   - `[Create.Docs]`        Special instructions, board stack ups, silk screen / mask colors...

@Description:
jBOM uses supplier profiles to generate submission packages for fabricators.  These packages typically include
* Gerber (layout) and Drill files for PCB fabrication
* Bill of Materials (BOM) and Component Placement Lists (CPL) for PCB Assembly
* (Optional) Documentation about the project's special requirements

These artifacts can be generated together as a package, or (in the following scenarios) individually.
@End

### @Scenario: `[Generate.BOM]`
Alex generates fabricator-specific BOM for a KiCad project using inventory data
@Steps:
   - `[Discover.Profiles]`  Discover available supply chain profiles at runtime
   - `[Specify.Project]`    Specify the KiCad project to validate against inventory
   - `[Specify.Inventory]`  Specify the Inventory to use
   - `[Specify.Profile]`    Specify the supply chain profile to use
   - `[Extract.Components]` Extract component specifications from KiCad project files
   - `[Extract.Items]`      Extract available items from inventory files
   - `[Filter.Items]`       Filter inventory to match profile's supplier ecosystem
   - `[Match.Components]`   Compare KiCad project components with inventory items to identify matches
   - `[Resolve.Conflicts]`  Resolve ambiguous matches and missing components
   - `[Create.BOM]`         Fabricator-compatible Bill of Materials

### @Scenario: `[Generate.CPL]`
Alex generates fabricator-specific CPL for a KiCad project using inventory data
@Steps:
   - `[Discover.Profiles]`  Discover available supply chain profiles at runtime
   - `[Specify.Project]`    Specify the KiCad project to validate against inventory
   - `[Specify.Inventory]`  Specify the Inventory to use
   - `[Specify.Profile]`    Specify the supply chain profile to use
   - `[Extract.Components]` Extract component specifications from KiCad project files
   - `[Extract.Items]`      Extract available items from inventory files
   - `[Filter.Items]`       Filter inventory to match profile's supplier ecosystem
   - `[Match.Components]`   Compare KiCad project components with inventory items to identify matches
   - `[Resolve.Conflicts]`  Resolve ambiguous matches and missing components
   - `[Create.CPL]`         Fabricator-compatible component placement file

### @Scenario: `[Generate.CAM]`
Alex generates fabricator-specific CAM packages for a KiCad project using inventory data
@Steps:
   - `[Discover.Profiles]`  Discover available supply chain profiles at runtime
   - `[Specify.Project]`    Specify the KiCad project to validate against inventory
   - `[Specify.Inventory]`  Specify the Inventory to use
   - `[Specify.Profile]`    Specify the supply chain profile to use
   - `[Extract.Components]` Extract component specifications from KiCad project files
   - `[Extract.Items]`      Extract available items from inventory files
   - `[Filter.Items]`       Filter inventory to match profile's supplier ecosystem
   - `[Match.Components]`   Compare KiCad project components with inventory items to identify matches
   - `[Resolve.Conflicts]`  Resolve ambiguous matches and missing components
   - `[Create.CAM]`         Fabricator-compatible Gerber and drill files
