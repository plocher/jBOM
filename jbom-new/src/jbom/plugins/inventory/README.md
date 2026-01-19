 The use cases for inventory are worth calling out, since they may impact the analysis you did:
1) jbom bom

The BOM plugin right now simply exposes whatever it finds in the user's schematic.  The presumption is that the components in the kicad_sch are fully specified, with sufficient attributes to create an acceptible BOM.
This implies that the schematic content becomes tightly coupled to a fabricator, with fabricator-specific part numbers etc.  It also tightly couples the schematic design to a point in time, with the choice of fabricator and choice of component/part number.

adding --inventory FILE to this plugin adds an indirection based on incompletely specified components in the design file(s).  Each schematic component is matched with items/rows in the inventory based on the provided-by-designer attributes (10k, resistor, 0603 smt, 10% tolerance, ...), and then this set of candidate inventory items is reduced to a single "best match"  by filtering (by a chosen fabricator, by price, by lead-time or stocking, by quantity available, or by a simple priority ranking).  In the case of problems, sufficient context information is provided so the user can resolve issues

With debug/verbosity flags, the inventory feature  documents/exposes its decision process

2) jbom inventory

If the user does not (yet) have an inventory, they can create a csv-file inventory by extracting the components actually used in their existing projects.  It must be possible for the user to iteratively create a new inventory file from a kicad project, and add to it with content from additional kicad projects.

This created inventory will be, by necessity, a mixed set of items.  some will be incompletely specified, some fully, and some will be wrong, obsolete or unavailable.  It would be a great diagnostic to selectively display items based on user-provided filters (show all the resistors that don't have a distributor...).  In this "phase", the user will edit the data in a spreadsheet app to add missing item/cell content


3) jbom search

Another way for the user to get a "better" inventory file is to treat it as a source of incompletely specified components and use a web based distributor search API to match against avbailable items, similar to the BOM matching referenced above. The original jBOM implements the Mouser API, though DigiKey and others are candidates for future support. API searching needs to take into account API rate limits by caching and judicious construction of queries.  An alternative to API searching is to use a downloaded CSV from a distributor - JLC maintains a customer-purchased parts bin that can be exported as a CSV file: /Users/jplocher/Dropbox/KiCad/jBOM/examples/JLCPCB-INVENTORY.csv
