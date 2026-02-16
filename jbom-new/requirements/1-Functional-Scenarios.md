## Program start up and initialization

### Scenario: `[Discover.Profiles]`
Discover available supply chain profiles
@Steps:
   - enumerate an ordered directory search mechanism where profiles might be found:
   - load and validate profile files
     - Utilize a deterministic hierarchical model where higher profiles can be extended, modified or overridden by lower ones
   - expose profile data structures to rest of jBOM
      - for help/usage text
      - for defining supply chain actors and CLI shortcuts
        - e.g., a JLCPCB profile may define `--jlc` as a CLI flag that defines various BOM, CAM and CPL options
      - integrate into jBOM's argument parsing templates
      - used by `[Specify.Profile]`
@End

### Scenario: `[Specify.Profile]`
Specify the supply chain profile to use
@Steps:
   - Profile Hierarchy (Search Order)
      1. **Common web site**:`JBOM_URL` (if set)
      2. **jBOM installation Directory**: `JBOM_HOME` (or `/Applications/jBOM/` ...)
      3. **KiCad plugins Directory**:
         * Windows: %APPDATA%\kicad\<version>\scripting\plugins (e.g., C:\Users\<username>\AppData\Roaming\kicad\9.0\scripting\plugins).
         * macOS: ~/Documents/KiCad/<version>/scripting/plugins/ or ~/Library/Preferences/kicad/scripting/plugins.
         * Linux: ~/.kicad/<version>/scripting/plugins/ or ~/.config/kicad/scripting/plugins.
      4. **Environment Variable**: `JBOM_DIR` (if set)
      5. **Project Directory**: `.jbom/` in current working directory
      6. **Git Repo Root**: `.jbom/` in repository root (if in git repo)
      7. **User Home**: `~/.jbom/`
   - User Profile Capabilities
      - **Custom Supplier**: Define new supplier (mouser, digikey, LCSC)
      - **Custom Fabricators**: Define new fabricator (JLC, PCBWay, OSHPark)
      - **Custom Catalog**: Define new catalog search configurations (octopart, suppliers, ...)
      - **Override Built-ins**: Customize specific aspects of built-in profiles
      - **Extend Configurations**: Add new fields/presets to existing profiles
      - **Project-Specific**: Per-project customizations
      - **Organization Configs**: Team/company-wide configuration sharing via `JBOM_DIR`
@Documentation:
Of interest are preferred manufacturers, product families, suppliers and fabricators.

Fabricators have specific BOM and CPL names and content they require.
See the jBOM git source tree:  `repo://jBOM/src/jbom/config/fabricators` and `repo://jBOM/jbom-new/src/jbom/config/fabricators`

@End

### Scenario: `[Specify.Project]`
Specify the KiCad project to use
@Steps:
@Documentation:
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

### file.feature
Tests explicit file references (.kicad_pro, .kicad_sch, .kicad_pcb).
- Scenarios: all file types with all commands, file edge cases

### cross_resolution.feature
Tests wrong file type → right file type resolution.
- Scenarios: bom given .pcb, pos given .sch, inventory given wrong files
@End

### Scenario: `[Specify.Inventory]`
Specify the Inventory to use
@Steps:

## Use Case
As a hardware engineer, I want to understand what components I need and what I already have, so I can make informed decisions about ordering parts for manufacturing.

## Core User Needs
1. "I want to see all the components my project needs in a format I can use for ordering"
2. "I want to know which components from my project I don't already have in inventory"
3. "I want to add my project's components to my existing inventory without creating duplicates"
4. "I want to check against multiple inventory sources (suppliers, locations) and get the best matches"
5. "I want the system to handle missing or bad inventory files gracefully"

## Feature Files

### core.feature
Tests basic inventory generation from KiCad projects.
- Scenarios: generate IPNs, categorize components, normalize packaging

### inventory_matching.feature
Tests matching project components against existing inventory.
- Scenarios: basic matching, filtering, error handling for missing files

### IPN_generation.feature
Tests IPN creation logic and formatting consistency.
- Scenarios: category detection, value normalization, IPN patterns
- Supports all user needs through stable component identification

### multi_source.feature
Tests multiple inventory file handling and best match selection.
- Scenarios: multiple sources, duplicate handling, best match logic

### multi_source_edge_cases.feature
Tests complex scenarios with malformed files and error conditions.
- Scenarios: missing files, malformed CSV, duplicate IPNs

### file_safety.feature
Tests file handling and command validation.
- Scenarios: file permissions, invalid combinations

## read and extract data from sources

### Scenario: `[Extract.Components]`
Extract component specifications from KiCad project files
@Steps:
@Documentatation:
Given a KiCad project (see `[Specify.Project]`), find and parse all the project's schematics
extracting the Components (Symbols) and all of their attributes.

### Scenario: `[Extract.Items]`
Extract items from inventory files
@Steps:
@Documentatation:
Given an inventory file (see `[Specify.Inventory]`), parse it, extracting the items and all of their attributes.

Handles loading inventory data from multiple file formats:
- CSV (.csv)
- Excel (.xlsx, .xls)
- Apple Numbers (.numbers)
- KiCad Database
- jBOM inventory schema
- JLC Parts List schema (no IPN...)  (See repo://examples/JLCPCB-INVENTORY.csv)

@End


### Scenario: `[Search.Suppliers]`
Search supplier catalogs for products that match the electro-mechanical attributes of the item
@Steps:

@Documentation:
 - octopart/Nexar, Digikey, Mouser and LCSC provide official, real-time API for businesses that offers various features including keyword search, item details, and ordering. Access requires an account and API approval.
 - Catalog Profiles provide the details
@End

### Scenario: `[Select.Items]`
Use heuristics to identify a small pool of candidate parts for that item
@Steps:
@Documentation:
Parts catalogs contain thousands of parts from hundreds of manufacturers.
Heuristics and filtering can be used to narrow down desirable candidates, but a human often needs to provide final selection guidance.  A middle ground is to have the search engine select a limited ordered set of qualified candidates and let the user choose to use or discard each.

Some hueristics that may be interesting:
 - Price
 - Quantity in stock - larger implies higher usage, active design usage
 - Minimum order quantity - does the design usage times board quantity meet the MOQ?
 - lifecycle status - prefer active, a negative tiebreaker if not recommended for new design or end-of-life product
@End


## Data processing - Heuristics and filtering
### Scenario: `[Filter.Items]`
Filter inventory to match profile's supplier ecosystem
@Steps:
@Description
If I'm generating a BOM for JLC, I need to use supplier part numbers optimal for JLC.  Same for PCBWay, etc

While all can use manufacturer name and manufacturer part numbers to cross reference into their catalogs, it is sometimes beneficial to use a supplier-specific second-source.  JLC calls these "Basic Parts", common items that are kept loaded into their pick-and-place assembly lines.

While this concept is conceptually named "filtering", in reality it is simply a first order ranking, such that the preferred items (if they exist) are chosen; if their are none, then the non-supplier-specific items are available for use.
@End

### Scenario: `[Match.Components]`
Compare KiCad project components with inventory items to identify matches
@Steps:
@Description
The concept is that the components found in a KiCad project have attributes that describe loosely described design constraints (electrical types, values, tolerances, ratings...), while inventory items have fully described design capabilities AND supply chain details.
(e.g., a KiCad component may be
- [R1, 1k, resistor, 100mW, 10%, 0603]
while an inventory may have several items:
[RES_5%_100mW_0603_1k, SMD, 1k,	thick film, 100mW,  75V, ±100ppm/℃, 5%,	0603,	JLC,	   C25585,	           UNI-ROYAL. 0603WAJ0102T5E,	Device:R_US,	SPCoast:0603-RES]
[RES_5%_100mW_0603_1k, SMD, 1k,	thick film, 100mW,  75V, ±100ppm/℃, 5%,	0603,	Mouser,  603-RC0603JR-071KL,	Yageo, RC0603JR-071KL,   	Device:R_US,	SPCoast:0603-RES]
)

Matching is a fuzzy heuristic that tries to find a "best match" between the incompletely specified component in the design and candidate items in the inventory.  It uses [Filter.Items], [Grade.Items] and [Rank.Items]

Filtering can be used to disqualify obviously incompatable candidates, but can't be used to refine compatable ones - it needs to weed out unsuitable items

Grading is a way of quantifying the answer to "Does this item meet the criteria that the designer articulated via the component's attributes?"

Ranking is a way to show a preference between multiple otherwise interchangible items (such as inventory lots, geographic location...)

@End


### Scenario: `[Resolve.Conflicts]`
Resolve ambiguous matches and missing components
@Steps:
@Description
Matching results in a list of candidate items that have a ranking associated with them that indicates the confidence that this Item matches the component's provided attributes.
In the best case, there is only one candidate, and it has a high confidence match score.
It is good to have a definitive "nothing found" result as well; this list of not-founds is where the supplier catalog search feature comes into play.
In between these two, deciding what to do is difficult, which is the basis for the design audit capability and [Identify.Ambiguous]

The workflows associated with this resolution involve KiCad project rework, supplier catalog searching and Inventory maintenance
@End



## Data processing - Heuristics and filtering
### Scenario: `[Filter.Items]`
Filter inventory to match profile's supplier ecosystem
@Steps:
@Description
Course filtering can be done to triage the candidate pool:
 - a specific IPN attribute
 - the component's type: derived from the Footprint, Symbol or explicit type attribute
 - the package: either explicit or derived from the Footprint name
 - some fabs have in house parts that are beneficial to use, but unavailable to users of other fabs


@End

### Scenario: `[Grade.Items]`
Grading candidate items is a way to quantify confidence in the "electro-mechanical" match between the KiCad component and the Inventory Item's attributes
@Steps:
@Description
A "100%" confidence implies that this Item meets all of the designer's stated requirements.
Less than 100% leads to warnings to the user that there is a potential issue if this item is used in this application.

Fine grained confidence grading comes from nuances relating to value and supply chain preferences
 - values need to be normalized: 1,000 -vs- 1000 -vs- 1K -vs- 1k -vs- 102 ...
 - Tolerances need to be taken into account:  a 10% tolerance component can be substituted with a higher tolerance item (i.e., 5%, 1%); due to volume pricing, it is often true that a 1% resistor is significantly cheaper than a 10%...
 - Resistor values follow an eia decade pattern across the various orders of magnitude: E6 20% tolerance, E12 10%, E24 5%, E96 1%, ...
 - Equivalence may be nuanced:  LEDs emit in a range of wavelengths: is Green the same as Emerald?  How much blue-green is OK?  Brightness may be "similar mcd values", though "beam angle". lumens and mcd ratings are confusing
@End

### Scenario: `[Rank.Items]`
Ranking is a way to show a preference between multiple otherwise interchangible items

@Steps:
@Description
 - old -vs- new stock and first-in-first-out policies
 - geographic location or stock availability
 - taking advantage of pricing incentives

## Data classification
### Scenario: `[Identify.Ambiguous]`
BOM content: Identify ambiguous project components that matched multiple inventory items
@Steps:
@Description
While it is possible to do some good guessing, it is better to inform the user and let them resolve things:
  - Many times an exact match isn't possible; how many and which candidates should be provided?
  - if only 1 candidate exists, but it has a low ranking score, what is the user to make of the result?  There is a good chance that the suggested component isn't really suitable, or that the KiCad component wasn't sufficiently annotated - though it would be good to quantify this with real examples...
  - a small number of candidates may indicate an over-constrained component combined with an incomplete inventory.  Both will require iterating.
  - there should be a way for the user to indicate how many candidates to return.

@End


### Scenario: `[Identify.Gaps]`
Identify items that lack supply chain details
@Steps:
@Description
This is an audit of the inventory itself.
It asks whether the search results for this item contain desirable or required fields that aren't in the inventory: power ratings, max voltages and currents,
@End


### Scenario: `[Identify.Obsolete]`
BOM content: Identify obsolete project components that matched retired inventory items
@Steps:
@Description
Supplier catalogs sometimes indicate whether this item is active, not recommended for new products, or obsolete.  Pruning out unobtaniun is a task that is difficult to do manually, but easy if automated.
Inventory items may become undesirable for many reasons other than obsolescence - price, reliability, etc

This feature is about finding out what KiCad projects are impacted by inventory changes.
@End


### Scenario: `[Identify.Orphans]`
BOM content: Identify orphan project components that didn't match inventory items
@Steps:
@Description
This feature is about finding the components in a KiCad project that `[Match.Components]` fails to find a matching inventory item for
@End



## Create artifacts
### Scenario: `[Create.BOM]`
Annotated BOM using inventory data
@Steps:
@Description
A KiCad BOM (Bill of Materials) is a comprehensive list of all electronic components, footprints, and, often, manufacturer part numbers (like Digi-Key or Mouser) required to assemble a PCB, typically exported as a CSV or HTML file. It acts as a crucial, customized purchasing list generated from either the schematic (Eeschema) or PCB layout.

Purpose: Lists every part needed (reference designators, quantities, values, footprints) to turn a design into a physical board.
Customization:
  - Can expose custom component fields from your schematic, pcb and/or inventory files (e.g., vendor, cost, manufacturer part number) to ensure the generated BOM is ready for procurement.
  - Can order the fields/columns in any arbitrary order
  - Can specify an arbitrary name for columns in the BOM
  - supply chain profiles can provide custom field lists, column naming and remapping  (e.g., a JLC profile may specify that the inventory field named "Supplier Part Number" be presented in the BOM as "LCSC" for components sourced from LCSC)
Integration with KiCad: KiCad provides a robust BOM subsystem under eeschema's "Generate BOM" heading as well as its integrated "Symbol Fields Table".  jBOM's KiCad integration should integrate tightly with these tools.
@End


### Scenario: `[Create.CAM]`
Fabricator-compatible Gerber and drill files
@Steps:
@Description
To fabricate a PCB using KiCad, you primarily need to generate Gerber files (RS-274X or X2 format) for the layers and Excellon Drill files for hole data, usually zipped together. Essential layers include copper, solder mask, silkscreen, and board outline.
Required Files for PCB Fabrication (Bare Board)
Gerber Files: These describe each layer.
 - Copper Layers: Top (.GTL), Bottom (.GBL), and internal layers if applicable.
 - Solder Mask: Top (.GTS) and Bottom (.GBS).
 - Silkscreen: Top (.GTO) and Bottom (.GBO).
 - Board Outline: Edge.Cuts (.gm1 or similar).
 - Drill Files (.drl or .txt): Separate files for plated (PTH) and non-plated (NPTH) holes, often containing "PTH" or "NPTH" in the filename.

Integration with KiCad: KiCad has robust support for creating assembly files:
Open Board Editor: Go to File > Plot.
Select Layers: Ensure F.Cu, B.Cu, F.Paste, B.Paste, F.SilkS, B.SilkS, F.Mask, B.Mask, and Edge.Cuts are selected.
Settings: Use X2 or RS-274X format. Check "Plot footprint references" and "Force plotting invisible values".
Generate Drills: Click "Generate Drill File(s)", ensuring "Map file" is unchecked and "Oval holes" are set to "Use route command".
Archive: Zip all generated files into a single .zip file for the manufacturer.

BOM's KiCad integration should integrate tightly with these tools.

@End


### Scenario: `[Create.CPL]`
Fabricator-compatible component placement file
@Steps:
@Description
A KiCad CPL (Component Placement List) or Position file is a text-based, manufacturing output file that provides the exact X/Y coordinates, rotation, and board side (top/bottom) for every component that will be assembled on a PCB. It is essential for automated assembly, telling pick-and-place machines where to place components.

CPL files follow a naming pattern (that can be defined in a supply chain profile).  Examples include {projectname}.CPL.csv and {projectname}.pos

Key Aspects of CPL Files
Purpose: The file allows assembly houses to automate the placement of surface-mount (SMD) and through-hole components.
Data Included: Usually contains Reference Designator (RefDes), Mid-X, Mid-Y, Rotation, and Layer.
Format: Typically exported as a CSV file for compatibility with manufacturers.
Important Options: When exporting, it is recommended to select "CSV," "mm" units, and "One file per side" (for separate top/bottom files).
Verification: It is crucial to verify the orientation in the manufacturer's preview, as rotation discrepancies (e.g., 180°) can occur. Many fabricators offer an engineering pre-check to identify and remediate this type of problem.

Customization:
  - Can expose custom component fields from your pcb and/or inventory files to ensure the generated CPL is ready for procurement.
  - Can order the fields/columns in any arbitrary order
  - Can specify an arbitrary name for columns in the CPL
  - supply chain profiles can provide custom field lists, column naming and remapping
  -
Integration with KiCad: KiCad's PCB Editor provides a robust CPL subsystem in File > Fabrication Outputs > Footprint Position (.pos) File.
jBOM's KiCad integration should integrate tightly with these tools.

@End


### Scenario: `[Create.Docs]`
Special instructions, board stack ups, silk screen / mask colors...
@Steps:
@Description
KiCad board stackup details are stored within the main .kicad_pcb board file and the project's .kicad_pro project file.

Within the KiCad Project Files
.kicad_pcb file: The physical layer stackup information (material, thickness, etc.) is primarily defined and stored in the board file itself. This file is a human-readable S-expression text file, and the stackup information can be found in a dedicated section.
.kicad_pro file: Some project-specific settings, such as custom layer visibility presets, are stored in the project file.
This project-centric storage method ensures that the stackup details are self-contained within the project, making it easier to share the complete design with others without missing information.

Accessing the Stackup Details
You can access and manage the stackup details through the KiCad interface:
Open the PCB Editor.
Go to File > Board Setup.
Navigate to the Board Stackup section.
From here, you have several options for managing the data:
 - View and edit: You can directly modify the physical stackup, layer names, and types.
 - Export: KiCad provides an "Export to clipboard" button to copy the stackup details as a text/CSV format for use in external documentation for manufacturers. The data is also included in a JSON format in the Gerber job file when you generate fabrication outputs.
 - Import: You can import stackup settings from another KiCad project file using the "Import settings from another board" button in the Board Setup dialog.
 - Place a table on the board: You can use Place > Add Stackup Table to place a visual, automatically-generated table of the stackup on a user-defined layer within the PCB editor itself, which can then be included in fabrication drawings. @End


### Scenario: `[Create.Inventory]`
Create an inventory with supply chain details
@Steps:
@Description
When starting out using jBOM, the user may not have any inventory files.
One way of creating inventory files is to extract the unique components from one or more KiCad projects, interactively search supply chain catalogs for matching and desirable parts, and expoer the resule into an inventory.

After using inventories and jBOM for a while, one might wish to update an existing inventory with unmatched components from a KiCad project, using a method similar to the above.

@End
