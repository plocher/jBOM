## Requirements for KiCad jBOM Inventory Management


## Plan

1. [x] familiarize yourself with the design patterns used in jBOM and this project's norms as found in WARP.md and README files.
   * The jBOM program associates the metadata contained in a project's KiCad Symbols and Footprints with inventory data to produce fabrication specifications known as Bills of Material
   * An inventory is simply a list of items that are available for use in a project
       * Inventory items include fields that describe a component used in the fabrication of an electronic project
       * some fields are common across all items in an inventory
          - `IPN` — internal part number
          - `Category` — Component type (RES, CAP, LED, IC, etc.)
          - `Package` — Physical package type (through hole lead spacing, pitch, size, 0603, SOT-23, etc.)
       * some are specific to the type or source of an item.  Examples include
          - Resistors have values in ohms, tolerance and power ratings
          - Capacitors have values in farads, esr, type, tolerance
          - Connectors have pin arrangement and pitch
          - LEDs have color, wavelength, luminosity, beam angle, voltage drop, current
          - `Manufacturer name` and `Manufacturer part number` are related
          - `Supplier` is a list of distributors and fabricators that stock this item

   * Distributors include Mouser, DigiKey
   * Fabricators include PCBWay, JLC, Seeed, inhouse.  it is a "bug" that jBOM currently has hardcoded knowledge of only jlc...

   * Inventory data can be data found in KiCad schematic and pcb files, a csv file, or (optionally) an Excel or Numbers spreadsheet
       * Use the ./examples/example-INVENTORY.{csv, xlsx,numbers} in the jBOM repo for examples
       * Excel and Numbers spreadsheets support formulas that enhance the usefulness of the inventory

   * Inventory data includes
       * component information from data sheets,
       * manufacturer information,
       * supplier information
       * pricing, desirability and availability information from the user
   * jBOM uses inventory data to generate Bill of Materials (BOM) for a project
       * Fabricators use the BOM data to identify the exact components that must be used when manufacturing the project
       * Fabricators often have access or preference for different suppliers
   * The desirability of a particular item in the inventory is influenced by many factors, including location, price, availability and choice of Fabricator
   * jlcparts and kicad-jlcpcb-tools are APIS that can be used to find parts in JLCPCB's inventory


2. [x] extend inventory workflows to work without an inventory file
    * extract the items found in a kicad project's sch and pcb files and use their metadata to create an in-memory inventory data model
    * the use cases for this are
        * The user has one or more KiCad projects, but no inventory file, and wishes to use the information already in their KiCad project:
            - as the source of inventory data for BOM creation, or
            - to construct an initial (possibly incomplete) inventory csv/spreadsheet, leveraging the -f field list flag to specify the desired inventory fields.  Since there is no existing inventory file from which to collect in-use field names, some of the validation logic may need to be relaxed for this use case
        * The user has an existing inventory, and wishes to:
            - check to see if all its components are already in the inventory, or
            - add new components that are not currently in the inventory to it
3. [x] extend the inventory workflows to include the notion of fabricators and fabricator part numbers
    * Add a fabricator field with values like `JLC`, `Seeed` and `PCBWay`
    * Add associated fabricator-specific component part number fields
        * The JLC fabricator uses the following field names for its component part number:
            - "LCSC Part #" and "JLCPCB Part #"
            - The fallback fields in order of lookup are "JLC Part", "LCSC Part", "LCSC", "JLC"
        * The Seeed fabricator looks for "Seeed SKU" or "Seeed Part"
        * Some fabricators (like PCBWay) use a combination of manufacturer part number ("MFGPN" or "MPN") and a distributer's name ("DigiKey", "Mouser", "local") to source from
    * The use case for these capabilities is
        * The user wishes to fabricate their project from different vendors at different times, yet keep a unified inventory
        * The user wishes to select the supplier or fabricator that they will be using for production

3.5. [x] refactor to support multiple / federated inventory sources
    * Allow loading multiple inventory files simultaneously (-i file1 -i file2)
    * Track "Source" of each item (e.g., "Local", "JLC-Private")
    * Support loading JLC's "My Parts Lib" export format (.xlsx)
    * This enables the workflow: Check "Private Stock" first, then fallback to others.

4. Back-Annotation (Closing the Loop)
    * The user workflow often involves generating a prototype inventory, filling in missing data (Values, LCSC numbers) in the CSV/Excel file.
    * Currently, this data stays in the CSV. The schematic remains "incomplete" (e.g. empty Value fields).
    * We need a way to push these updates BACK to the KiCad schematic to establish it as the Source of Truth.
    * Strategies:
        * `jbom annotate` command.
        * Match rows by UUID (need to ensure UUID is exported in Step 2).
        * Update Symbol Fields (Value, Footprint, LCSC, etc.).
        * Use `sexpdata` to safely patch `.kicad_sch` files (or investigate KiCad IPC if feasible, but file patching is more robust for batch/CI).

5. External/Offline Search (Find parts in Fabricator DB)
    * Once the schematic is complete (thanks to Step 4), we can robustly search for parts.
    * use cases are:
        * find components that match the items in the online inventory (type, values, tolerances, etc, similar to the existing matching algorithm)
        * filter them to remove unsuitable results (non-stocked/long lead time etc)
        * filter them by lack of stock (quantity needed (plus margin) is less than available stock...)
        * sort the resulting list to find the "best" candidates - this will be a heuristic that nay need to evolve, or even be specific to each source
            - manufacturer, manufacturer part number, alternate manufacturing sources, alternate-but-equivalent part numbering schemes
            - quantity on hand is a good indication of popularity/suitability
            - minimum quantity for ordering may filter out some candidates, depending on the quantity discount rates
            - price matters - all things equivalent, pick the lowest price
    * use cases:
        * The user wishes to find prospective items in a distributor or fabricator's product list and associate them to items in their inventory
        * The user wishes to add a new distributor to their inventory and associate existing inventory items with that distributor's offerings
        * The user wishes to audit their inventory against current distributor and fabricator parts lists
        * The user wishes to interactively search, evaluate and select supplier sourcing website data to add to their inventory
