## Program start up and initialization

### Scenario: `[Profile.Concept]`
**Profile configuration scope and format [TBD - depends on understanding and clarifying functional expectations]**

Profiles capture supply chain context to enable fabricator switching without design changes. Minimum viable profile defines BOM column mapping and basic supplier preferences.

**Future decisions needed:**
- Which component matching rules are configurable vs built-in?
- Profile file format and composition model?
- Granularity of fabricator-specific formatting options?
- Integration with supplier API credentials and search parameters?

**Dependencies:** Results from implementing other scenarios will inform profile requirements.

### Scenario: `[Discover.Profiles]`
System finds and loads supply chain configuration files

Alex needs jBOM to work with Alex's supply chain preferences without hardcoded assumptions. Maybe Alex prefers Mouser over Digikey, or Alex's company mandates specific manufacturers. Maybe Alex's fabricator expects "LCSC Part#" column while another expects "Supplier PN".

jBOM should find configuration files that define these preferences - from the project folder, user settings, or system defaults. This lets Alex (or Alex's team) customize supplier APIs, BOM formatting, component matching rules without code changes.

The system searches multiple locations in priority order: project directory, git repository root, user home directory, system installation. Higher priority profiles can extend or override lower priority ones.

### Scenario: `[Specify.Profile]`
Select which supply chain configuration to use for this operation

Alex operates in different supply chain contexts - hobby projects use LCSC/JLCPCB, client work uses Mouser/PCBWay, company projects have approved vendor lists. Each context needs different supplier preferences, BOM formats, and component matching rules.

The system should let Alex choose Alex's supply chain context explicitly or automatically detect it based on project location. Company projects in shared repositories might automatically use organization-wide profiles. Personal projects use Alex's preferred suppliers.

Profiles define everything from "prefer YAGEO resistors" to "BOM needs LCSC column for JLCPCB" to "search Mouser first, Digikey as backup." Alex shouldn't need to reconfigure these preferences for each project.

### Scenario: `[Specify.Project]`
Identify which KiCad project to process

Alex shouldn't have to remember that BOM generation needs schematic files while CPL generation needs PCB files. When Alex is in a project directory, jBOM should just work. When Alex points to any KiCad file, jBOM should figure out what else it needs.

The system should handle Alex's natural workflow: "I'm in my project directory, generate a BOM" or "Here's my .kicad_pcb file, I need assembly files" or "Process this project folder for fabrication."

jBOM should automatically discover project files, resolve file dependencies (schematic for components, PCB for placement), and handle multi-sheet hierarchical projects without Alex specifying every file.

### Scenario: `[Specify.Inventory]`
Determine which inventory sources to use for component matching

Alex maintains component inventory in spreadsheets - maybe one master CSV file, maybe separate files per supplier, maybe Excel files shared with teammates. Alex's inventory maps design requirements ("1kΩ resistor, 0603") to real parts Alex can actually order ("YAGEO RC0603JR-071KL from Mouser").

The system should find Alex's inventory files automatically or let Alex specify them explicitly. Alex might have multiple inventory sources - Alex's personal parts collection, company-approved parts list, supplier-specific catalogs. The system should combine these intelligently and handle missing or corrupted files gracefully.

When Alex adds new components to projects, the system should help Alex update Alex's inventory with suitable supplier options rather than requiring manual research every time.

## read and extract data from sources

### Scenario: `[Extract.Components]`
Get component specifications from KiCad project files

Alex's KiCad project contains components with design requirements: "R1: 1kΩ resistor, 0603 package, 5% tolerance" or "U1: ESP32-WROOM-32 microcontroller." The system needs to extract these components and their attributes from schematic files to understand what Alex actually needs to build Alex's board.

The system should handle hierarchical schematics, multiple sheets, and all the different ways KiCad stores component information. It should capture reference designators (R1, C5, U3), values (1kΩ, 100nF), footprints (0603, SOIC-8), and any custom fields Alex added.

This gives jBOM the complete component requirements list that can be matched against inventory to generate real BOMs.

### Scenario: `[Extract.Items]`
Load inventory data from Alex's spreadsheets and databases

Alex maintains Alex's component inventory in various formats - maybe a master CSV file, maybe separate Excel sheets per supplier, maybe Apple Numbers files shared with teammates. Each inventory item maps design requirements to real, orderable parts with supplier details.

The system should read Alex's inventory files regardless of format (CSV, Excel, Numbers, KiCad databases) and extract the component specifications, supplier part numbers, manufacturer details, and any custom attributes Alex tracks like "preferred for new designs" or "bulk pricing available."

This gives jBOM the pool of available parts that can satisfy the component requirements extracted from KiCad projects.


### Scenario: `[Search.Suppliers]`
Find parts using configured supplier catalogs

Alex has inventory items missing supplier details or encounters new components not in Alex's inventory. Rather than manually browsing Mouser, Digikey, or LCSC websites, Alex needs the system to search supplier catalogs automatically using component specifications.

The system should use Alex's configured supplier APIs (Mouser REST, Digikey OAuth, LCSC databases) to find parts matching electrical and mechanical requirements. For a "1kΩ, 0603, 5%" resistor, it should return candidate parts with full supplier details, stock levels, and pricing.

This lets Alex quickly expand Alex's inventory with real, orderable parts rather than doing repetitive manual research for every new component.

### Scenario: `[Select.Items]`
Narrow supplier search results to reasonable candidate parts

Supplier catalogs return thousands of parts for "1kΩ resistor" - different manufacturers, packages, tolerances, power ratings, prices. Alex doesn't want to manually review hundreds of options; Alex needs the system to identify a manageable set of good candidates.

The system should apply heuristics to rank and filter results: prefer active parts over obsolete, higher stock quantities suggest popular/reliable parts, reasonable pricing, minimum order quantities that make sense for Alex's typical volumes.

Alex gets a short, ranked list of suitable candidates with clear explanations of why each was selected. Alex can quickly approve good options or reject unsuitable ones, building Alex's inventory efficiently without endless catalog browsing.


## Data processing - Heuristics and filtering
### Scenario: `[Filter.Items]`
Prioritize inventory items based on supply chain context

Alex generates BOMs for different fabricators with different supplier ecosystems. When targeting JLCPCB, Alex wants to prefer LCSC parts and especially "Basic Parts" that are pre-loaded in their assembly lines for faster/cheaper assembly. When targeting PCBWay, Alex wants to prefer Mouser parts for broader selection.

The system should apply supply chain context to prioritize suitable inventory items. For JLCPCB BOMs, rank LCSC parts higher than Mouser parts. For company projects, prioritize approved manufacturers over random alternatives.

This isn't hard filtering (eliminating options) but intelligent ranking so Alex gets the most suitable parts for Alex's chosen fabricator while keeping fallback options available when preferred parts aren't available.

### Scenario: `[Match.Components]`
Find inventory items that can satisfy each KiCad component requirement

Alex's KiCad design specifies "R1: 1kΩ, 0603, 5%" but Alex's inventory contains specific supplier parts with full specifications. The system needs to intelligently match loose design requirements with precise inventory capabilities.

A KiCad "1kΩ, 5%" requirement could be satisfied by inventory items with 1% tolerance (better than required) but not 10% tolerance (worse than required). "1K" in KiCad should match "1000Ω" or "1k0" in inventory through value normalization.

The system orchestrates multiple sub-processes: normalize values for comparison, filter obviously incompatible items, grade how well each candidate meets requirements, and rank equally-suitable options by supply chain preferences. Alex gets clear match results with confidence levels and explanations.


### Scenario: `[Resolve.Conflicts]`
Handle uncertain component matches and missing inventory items

Matching doesn't always produce clear winners. Sometimes Alex gets multiple equally-good candidates, sometimes low-confidence matches that might not be suitable, sometimes no matches at all for components not in Alex's inventory.

The system should present these situations clearly to Alex with actionable options. For ambiguous matches, show the candidates with explanations of differences. For low-confidence matches, explain what requirements aren't well-satisfied. For missing matches, suggest supplier catalog searches to find suitable parts.

This gives Alex the information needed to make informed decisions: update KiCad component specifications, search for better inventory options, or accept suggested matches with understanding of any compromises.



### Scenario: `[Grade.Items]`
Quantify how well inventory items satisfy component requirements

Alex needs to understand match quality when the system suggests inventory items for Alex's components. A "perfect match" means the inventory item meets or exceeds all requirements. Lower grades indicate potential issues that Alex should review.

The system should provide confidence scores with clear explanations. A 1% resistor matching a 5% requirement gets high confidence ("tolerance upgrade"). A 10% resistor matching 5% requirement gets low confidence ("tolerance downgrade - verify if acceptable"). Value mismatches, package incompatibilities, or missing specifications reduce confidence.

This helps Alex make informed decisions about whether suggested matches are suitable for Alex's design or if Alex needs to search for better alternatives.

### Scenario: `[Rank.Items]`
Manage inventory priorities to optimize cost and avoid waste

Alex has real inventory management challenges: expensive parts already purchased that need to be used up before ordering cheaper alternatives, partial reels that shouldn't be wasted, preferred suppliers for consistency, and evolving cost optimization as market conditions change.

For example, Alex bought an expensive reel of resistors from LCSC for JLC assembly, then found cheaper equivalents. Alex wants to rank the expensive reel as Priority 1 (use first) and the basic part as Priority 2 (use after expensive stock is consumed). Later, when the expensive parts are used up, Alex can flip the priorities.

The system should respect Alex's explicit inventory priorities while providing flexibility to adjust rankings as business needs evolve. This prevents waste of already-purchased parts while enabling long-term cost optimization.

## Data classification
### Scenario: `[Identify.Ambiguous]`
Flag components with unclear or multiple inventory matches

Alex needs to know when component matching produces uncertain results that require Alex's attention. Sometimes multiple inventory items match equally well, sometimes the single match has low confidence, sometimes the component specification is too vague or too restrictive.

The system should clearly identify ambiguous situations: "R5 matched 3 equally-suitable 1kΩ resistors - choose preferred supplier" or "C12 has only one low-confidence match - verify 25V rating is sufficient for 12V design" or "U3 found no matches - specifications may be incomplete."

This validation feedback helps Alex decide whether Alex's BOM is fabrication-ready or needs component specification improvements, inventory updates, or supplier searches.


### Scenario: `[Identify.Gaps]`
Audit inventory completeness for fabrication readiness

Alex's inventory may have components that lack critical supply chain details needed for ordering or fabrication. Components might be missing manufacturer part numbers, supplier information, or key specifications that fabricators require.

The system should identify inventory gaps that could block fabrication: "10 components missing supplier part numbers - cannot generate fabricator BOM" or "5 items lack power ratings - verify specifications before high-power applications."

This inventory audit helps Alex prioritize which components need supplier research (`[Search.Suppliers]`) to find complete part specifications and update Alex's inventory for fabrication readiness.


### Scenario: `[Identify.Obsolete]`
Warn about components using discontinued or problematic inventory items

Alex's inventory may contain parts that are no longer suitable - supplier catalogs mark them as obsolete, not recommended for new designs, or they've become too expensive. Alex needs to know which current projects use these problematic parts before committing to fabrication.

The system should identify lifecycle issues: "R12, C5 using discontinued LCSC parts - find alternatives before production" or "U7 marked 'not recommended for new designs' - consider upgrade" or "Q3 price increased 300% - evaluate cheaper alternatives."

This proactive warning helps Alex update Alex's designs and inventory before supply chain problems block fabrication or inflate costs.


### Scenario: `[Identify.Orphans]`
Highlight project components with no inventory matches

Alex needs to know which components in Alex's project have no corresponding inventory items. These orphaned components block BOM generation and fabrication until Alex finds suitable supplier options.

The system should clearly list unmatched components: "5 components need inventory: U4 (STM32F103), C15 (22pF, NP0), D3 (Schottky, SOD-123)" with enough detail for Alex to search supplier catalogs effectively.

This orphan list becomes the input for supplier catalog searches (`[Search.Suppliers]` → `[Select.Items]`) to find suitable parts and expand Alex's inventory to cover all project requirements.



## Create artifacts
### Scenario: `[Create.BOM]`
Generate fabricator-ready bill of materials with supplier details

Alex needs BOMs that fabricators can process directly for assembly - not generic "1kΩ resistor" entries but real supplier part numbers they can order and place. Different fabricators need different formats: JLCPCB wants "LCSC" columns with LCSC part numbers, PCBWay wants "Mouser PN" columns.

The system should generate BOMs using matched inventory data and profile-specific formatting. For JLCPCB assembly, map inventory "Supplier Part Number" to BOM column "LCSC" for LCSC-sourced parts. Include all required fabricator fields: reference designators, quantities, values, footprints, and supplier details.

This produces complete fabrication packages that Alex can submit directly to assembly houses without manual BOM editing or part number lookup.


### Scenario: `[Create.CAM]`
Generate PCB fabrication files using fabricator-specific settings

Alex needs complete, correctly-formatted fabrication file packages for PCB manufacturers. Different fabricators have different requirements: file naming conventions, Gerber format preferences, drill file specifications, and packaging standards.

The system should orchestrate KiCad's plotting capabilities with profile-defined fabricator requirements. For JLCPCB, generate X2 Gerber format with specific layer naming. For PCBWay, use different drill file settings. Package everything in properly-named ZIP archives that fabricators can process directly.

This automates the complex, error-prone process of generating fabrication files, ensuring Alex gets manufacturer-ready packages without remembering dozens of fabricator-specific settings.


### Scenario: `[Create.CPL]`
Generate component placement files for automated assembly

Alex needs accurate component placement files for pick-and-place machines. Different assembly houses have different CPL format requirements: column naming, coordinate systems, file splitting (top/bottom), and units (mm vs inches).

The system should generate CPL files using PCB layout data and profile-specific formatting. Include precise component coordinates, rotations, reference designators, and any custom fields needed for assembly. Handle fabricator differences: JLCPCB wants specific column names, PCBWay uses different coordinate origins.

This ensures Alex's placement files work correctly with automated assembly equipment, preventing costly placement errors and assembly delays.


### Scenario: `[Create.Docs]`
Generate fabricator documentation and special requirements

Alex's projects may have special fabrication requirements beyond standard Gerbers: specific stackup materials, solder mask colors, silkscreen specifications, controlled impedance requirements, or special assembly instructions.

The system should extract documentation from KiCad project files (stackup tables, design rules, special layers) and profile-specific templates to create fabricator documentation. Include stackup specifications, material requirements, color preferences, and any custom assembly notes Alex needs to communicate.

This ensures fabricators have complete project requirements, reducing back-and-forth clarifications and fabrication errors from missing specifications.


### Scenario: `[Manage.Inventory]`
Handle inventory file operations and data management

Alex's inventory files need robust handling: reading/writing multiple formats (CSV, Excel, Numbers), validating data integrity, enforcing schema requirements, generating consistent IPNs for new components, handling file corruption gracefully, and maintaining backups.

The system should provide reliable inventory file operations regardless of format or data completeness. Handle format conversions, data validation, error recovery, and maintain data consistency across all inventory operations.

This foundational capability supports all inventory workflows - creation, updates, repairs, and expansions.

### Scenario: `[Create.Inventory]`
Create new inventory from KiCad projects and supplier sources

Alex needs to bootstrap inventory from scratch or merge multiple sources into new inventory files. Starting with KiCad project components, empty inventory templates, or combining existing inventory sources into consolidated files.

The system should extract unique components from KiCad projects, set up proper inventory file structures, and merge multiple inventory sources intelligently. Uses `[Manage.Inventory]` for all file operations and data handling.

This gives Alex the ability to create inventory foundations from Alex's existing KiCad projects and consolidate inventory sources as Alex's operations grow.

### Scenario: `[Update.Inventory]`
Add supplier details and components to existing inventory

Alex needs to enhance existing inventory with new supplier information, add components from new projects, or fill gaps identified by validation processes. The key is preserving existing inventory data while adding new information.

The system should match new components against existing inventory items, add supplier details from search results (`[Search.Suppliers]` → `[Select.Items]`), and incrementally expand inventory without data loss. Uses `[Manage.Inventory]` for all file operations.

This enables Alex to continuously improve Alex's inventory as Alex encounters new components and finds better supplier options.

### Scenario: `[Update.Inventory.MultiSupplier]`
Enrich one inventory run against multiple suppliers with additive semantics

Alex often needs alternates from more than one supplier for the same project requirements. Running separate commands per supplier is repetitive and makes reconciliation harder. Alex needs one enrichment run that gathers supplier candidates across multiple catalogs.

The system should accept repeatable supplier inputs in one command, execute supplier searches in deterministic order, and merge results into one consolidated inventory output.

Functional expectations:
- supplier passes are additive; existing rows are preserved and new candidate rows are appended
- candidate limit is evaluated independently for each supplier pass
- added rows participate in global same-IPN priority ordering so downstream matching remains deterministic
- no automatic deletion/rotation of rows in this phase; lifecycle cleanup is a separate explicit workflow
- automatic safe-refresh mutation of existing rows is deferred pending edge-condition validation against examples/fixtures
