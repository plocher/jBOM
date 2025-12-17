# Requirements for Step 3.5: Federated Inventory Support

## Problem
jBOM currently assumes a single "Master Inventory" file. This limits flexibility when working with multiple sources of parts data (e.g., Local Stock, JLC Private Library, Mouser Catalog). Users need to federate these sources so that `jBOM` can find the best matching part from *any* available pool.

## Goal
Enable `jBOM` to load and match against multiple inventory files simultaneously, preserving the identity (Source) of each item.

## Plan

### 1. Data Model Updates
- [ ] Update `InventoryItem` to include a `source` field.
- [ ] Update `InventoryItem` to include `source_file` (path) for traceability.

### 2. Loader Architecture
- [ ] Refactor `load_inventory` to accept `List[Path]` instead of `Optional[Path]`.
- [ ] Implement a "Loader Registry" or Sniffer to route files to the correct parser based on content/extension.
    - `csv` -> `CsvInventoryLoader`
    - `xlsx` (Generic) -> `ExcelInventoryLoader`
    - `xlsx` (JLC Format) -> `JLCPrivateInventoryLoader` (New)

### 3. JLC Private Inventory Support
- [ ] Create `JLCPrivateInventoryLoader` to parse the specific JLC Export format.
    - Maps "LCSC Part #" -> `LCSC`
    - Maps "Stock" -> `Stock`
    - Maps "Price" -> `Price`
    - Sets Source = "JLC-Private"

### 4. CLI Updates
- [ ] Update `jbom bom` to accept multiple `-i` arguments: `jbom bom -i local.csv -i jlc.xlsx ...`
- [ ] Update `jbom inventory` to accept multiple inputs (merging them into one output?).

### 5. Matching Logic
- [ ] Ensure `InventoryMatcher` handles candidates from multiple sources correctly.
- [ ] (Future) Add priority logic (e.g., prefer Source A over Source B).

## Verification
- [ ] Unit Test: Load multiple files and verify count.
- [ ] Functional Test: BOM generation using a part found *only* in the second inventory file.



================
summary for the next session.

Topics Summary

This is a summary of a prior sequence of messages in this conversation. You can use it to assist you in your work. Note that the user still sees the full conversation and you should avoid mentioning that the conversation has been summarized.

Overview
The user and agent have completed Step 3.5: Federated Inventory Support. This was a pivotal architectural change allowing jBOM to load and match against multiple inventory files simultaneously (e.g., a local CSV + a JLC "My Parts Lib" export). This enables a "Hybrid Inventory" workflow where the user can prefer parts they already own (in JLC Private Stock) before sourcing new ones.

The previous focus on "Step 4" (Online Search API) revealed that live searching is restricted/unreliable. The strategy shifted to supporting "Offline Search" via a downloaded database (similar to kicad-jlcpcb-tools) to resolve the "Chicken and Egg" problem of finding part numbers for generic components. This work is deferred to the next session.

Topics Summary

Topic: Federated Inventory Support (Step 3.5)
Status: Completed

User messages:
> I believe that there is a new step 3.5: refactor the program to support multiple / federated inventory sources.

> there is a gap - new parts used in a kicad project that are not yet in my JLC parts inventory. We will need a workflow to identify them and close the loop

Progress:
•  Refactored InventoryLoader to accept multiple file paths and auto-detect file types.
•  Implemented JLCPrivateInventoryLoader to parse JLC's "My Parts Lib" export format.
•  Updated InventoryItem data model to track source and source_file.
•  Updated CLI (bom command) to accept multiple -i arguments (e.g., -i local.csv -i jlc_export.xlsx).
•  Verified with unit tests (tests/test_federated_inventory.py) and regression tests.
•  Updated documentation (README.md, README.man1.md) to reflect new capabilities.

Key Technical Details:
•  Loader: src/jbom/loaders/inventory.py now iterates through provided paths.
•  JLC Support: src/jbom/loaders/jlc_loader.py handles the specific headers of JLC exports (JLCPCB Part #, Category, MFR Part #).
•  Source Tracking: Each item knows if it came from "CSV", "Excel", or "JLC-Private".

Next steps:
•  Proceed to Step 4: Implement the workflow to "close the loop" on missing parts. This likely involves:
◦  Implementing the Offline DB Downloader/Searcher (to find candidates for generic parts).
◦  Or implementing the "Gap Analysis" report that highlights parts missing from any loaded inventory.

Topic: Online/Offline Search & API (Step 4)
Status: Pending / Re-scoped

User messages:
> The chicken-and-egg problem is that we don't have LCSC part numbers if we are getting our BOM from the kicad files...

> My thoughts are to plan for a step 3.5, followed by a step 4 that includes the JLC database.

Decisions:
•  "Live Search" API is not feasible due to blocking/auth.
•  "Live Validation" API (by ID) is feasible but only useful if IDs are known.
•  Strategy: To enable true "Search" (finding IDs for generic parts), we likely need to implement the Offline Database approach (downloading the SQLite DB from kicad-jlcpcb-tools). This will be the focus of the next session.



Active Work Priority
•  Next Task: Begin Step 4. Decide whether to integrate the "Heavy" Offline DB directly into jBOM or build a lightweight "Gap Analysis" tool first. The user has expressed interest in "closing the loop" for parts not yet in inventory.
