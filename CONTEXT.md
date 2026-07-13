# jBOM

Inventory-aware KiCad Bill of Materials generation: matching schematic components against a curated inventory of purchasable parts, and tooling for the shared datasheet document library referenced by that inventory.

## Language

### Inventory

**Item**:
One inventory row — a ranked candidate part for a schematic component. Component→Item is 1:many.
_Avoid_: part row, entry

**Datasheet column**:
The Item's living Canonical Source URL for its datasheet — provenance and acquisition metadata, upgraded during grooming, converging across Items that share a Datasheet Name. Not identity.
_Avoid_: datasheet link

**Datasheet Name column**:
The inventory column carrying a Document's Datasheet Name. Presence means the Item's datasheet is validated and in the Library; empty with a populated Datasheet column means the Item is in the Curation Backlog.
_Avoid_: doc ID column, status column

### Library tooling

**Admit**:
The `jbom inventory admit` batch-manifest gate implementing Admission: propose → human edit → apply, protected by Never-Rename. The sole path into the Library.
_Avoid_: import, ingest, upload

**Audit**:
The read-only hygiene checks run by `jbom audit` over the inventory and Library: Name→URL consistency, case-insensitive name uniqueness, Canonical Token normalization, file presence, and the Backlog Report.
_Avoid_: validation pass, linter (as a noun for the whole surface)

**Backlog Report**:
The Audit output listing the Curation Backlog — rows with a Datasheet URL but no Datasheet Name. Derived from inventory structure; there is no tracked status.
_Avoid_: todo list, dig-deeper list, grading queue

**Recovery Ladder**:
The ordered sequence of URL-recovery steps for supplier datasheet URLs (proven against LCSC), walked by `jbom audit --check-urls` to detect HTML impostors and dead links and to propose Canonical Source URL upgrades. Opt-in only; no re-validation cadence.
_Avoid_: URL fixup, refresh job

### Imported terms

Owned by [SPCoast-inventory's glossary](https://github.com/plocher/SPCoast-inventory/blob/main/CONTEXT.md) — use its definitions; do not redefine here:
**Library**, **Document**, **Datasheet Name**, **Never-Rename**, **Family Document**, **Canonical Token**, **Canonical Source URL**, **Staging**, **Intake**, **Admission**, **Curation Backlog**.
