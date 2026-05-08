# Issue #226: Production Folder, Packaging Services, and Diagnostic Collection
## Context
Branch: `issue-226-output-packaging`
Design reference: `docs/dev/architecture/adr/0006-production-folder-packaging-projectmetadata-diagnostic-collection.md`
Issue: https://github.com/plocher/jBOM/issues/226
## Problem
The `fab` workflow violates service layer boundaries: BOM/POS file I/O lives in `cli/fabrication.py`, `BOMWorkflow` reads `os.environ.get("JBOM_QUIET")` directly, and there is no production folder structure, artifact naming, or packaging service.
## Target Production Structure
```
production/
  jbom.csv
  cpl.csv
  {title}_{revision}.zip
  backups/
    {title}_{revision}_{timestamp}.zip
```
`{title}` and `{revision}` come from KiCad title block metadata; fallback to `.kicad_pro` basename when title is absent.
## Phase A — Foundation ✅ COMPLETE
Entry: branch exists and design is closed.
Exit: title block metadata is available from PCB/schematic readers; `ProjectMetadata` and `ZipArchiver` are independently tested.
### A1: Add title block metadata to readers
Update `src/jbom/services/pcb_reader.py` and `src/jbom/services/schematic_reader.py` to expose `title` and `revision` from the KiCad title block. Tests should validate real title/revision parsing and empty-title cases.
### A2: Introduce `ProjectMetadata`
Add `src/jbom/services/project_metadata.py` with a frozen `ProjectMetadata(name, version, release_timestamp)` dataclass and helper logic that derives metadata from resolved project input using title block values with `.kicad_pro` basename fallback. Include archive-stem normalization helpers and tests for fallback and normalization behavior.
### A3: Introduce `ZipArchiver`
Add `src/jbom/services/zip_archiver.py` with `ZipArchiver.archive(source_paths: list[Path], archive_path: Path) -> None`. The service creates parent directories, archives explicit path lists, and raises on empty input. Unit tests validate archive membership and directory creation.
## Phase B — Packaging Services ✅ COMPLETE
Entry: Phase A complete.
Exit: gerber packaging and dated backup packaging both work in isolation.
### B1: Add `GerberPackager`
Add `src/jbom/services/gerber_packager.py` that accepts explicit gerber artifact paths plus an archive path, delegates to `ZipArchiver`, and removes the intermediate gerber directory unless debug mode requests it be kept. Tests cover archive creation and cleanup behavior.
### B2: Add `BackupService`
Add `src/jbom/services/backup_service.py` that archives explicit production artifact paths into `production/backups/{stem}_{timestamp}.zip`. Timestamp format should be `%Y-%m-%d_%H-%M-%S`. Tests cover naming, archive creation, and backup directory auto-creation.
## Phase C — Friend Serializers ✅ COMPLETE
Entry: design closed and workflow/file-I/O boundary agreed.
Exit: BOM/POS file writing no longer depends on CLI adapter internals.
### C0: Extract field resolvers from CLI adapters ✅ COMPLETE
Moved ~300 LOC of BOM/POS field resolution logic from `cli/bom.py` and `cli/pos.py` into dedicated service modules:
- `src/jbom/services/bom_field_resolver.py` — `resolve_bom_field_value(entry, field, *, fabricator_id, fabricator_config) -> str`
- `src/jbom/services/pos_field_resolver.py` — `resolve_pos_field_value(entry, field, *, fabricator_id, fabricator_config) -> str`
CLI wrappers now delegate to these functions. No behavior change; 1145 tests pass. (commit 46c81f3)
### C1: Add `BOMWriter`
Add `src/jbom/services/bom_writer.py` as a friend serializer that writes a `BOMGenerationPayload` to a target path using the same CSV structure currently emitted by the BOM CLI. It should enforce overwrite policy via `force`. Unit tests should cover headers, row content, and overwrite refusal.
### C2: Add `POSWriter`
Add `src/jbom/services/pos_writer.py` as the placement/CPL counterpart to `BOMWriter`. It writes the `POSGenerationPayload` to a target path using the existing POS CSV shape. Unit tests should mirror the BOM writer tests.
### C3: Remove CLI-layer dependency from `fab`
Refactor `src/jbom/cli/fabrication.py` to stop importing `_output_bom` and `_output_pos` from sibling CLI modules. The fabrication path should use `BOMWriter` and `POSWriter` for file output. Existing CLI commands `bom` and `pos` keep their console/stdout rendering behavior unchanged.
## Phase D — Diagnostic Collection Fix
Entry: can be implemented independently.
Exit: service modules do not gate diagnostic collection on environment or `quiet` flags.
### D1: Fix `BOMWorkflow`
In `src/jbom/application/bom_workflow.py`, remove `import os` and replace `JBOM_QUIET` gates with unconditional diagnostic collection. Resolution notes are always appended to `diagnostics`.
### D2: Fix `POSWorkflow`
In `src/jbom/application/pos_workflow.py`, remove the `quiet` field from `POSRequest` and remove `request.quiet` gates so resolution notes are always appended to `diagnostics`.
### D3: Adjust adapters
Update `cli/bom.py` and `cli/pos.py` so adapters decide what to display. CLI should be able to gate informational notes on `--verbose` without suppressing collection inside the service. Tests should be updated to assert full diagnostic collection at the service layer.
## Phase E — Fabrication Workflow Integration
Entry: Phases A, B, and C complete.
Exit: `jbom fab` produces the full `production/` structure and backup artifact through service-layer composition.
### E1: Extend fabrication request/result contracts
Update `FabricationRequest` with `debug` and production-output-root semantics. Update `FabricationResult` so it can carry `production_dir` and backup archive information.
### E2: Integrate metadata, writers, and packagers
Refactor `src/jbom/application/fabrication_orchestration.py` so the workflow resolves `ProjectMetadata`, writes `production/jbom.csv` and `production/cpl.csv` using the friend serializers, packages gerbers into `production/{title}_{revision}.zip`, and creates the dated backup under `production/backups/`.
### E3: Update CLI surface
Update `src/jbom/cli/fabrication.py` to expose `--debug` and any required production-dir override flag, and to report production and backup paths. Existing `fab` flags should remain compatible unless design decisions require explicit renaming.
## Phase F — Tests, Docs, and Follow-ups
Entry: implementation complete.
Exit: full suite passes, docs updated, and follow-up gaps are tracked.
### F1: Expand tests
Add or update unit and service tests for reader metadata, `ProjectMetadata`, `ZipArchiver`, `GerberPackager`, `BackupService`, `BOMWriter`, `POSWriter`, and end-to-end fabrication orchestration behavior.
### F2: Update docs
Update `docs/CHANGELOG.md` with a concise unreleased entry describing production folder output, packaging services, metadata extraction, and diagnostic collection cleanup.
### F3: Track deferred work
Create follow-up issues for designators-as-service, netlist-as-first-class-service, and typed diagnostic severity entries.
### F4: Finalize PR
Commit with a conventional commit message referencing #226, push the feature branch, open the PR, and reference ADR 0006 in the PR description.
## Handoff Contract
Any successor session should begin by reading this plan and `docs/dev/architecture/adr/0006-production-folder-packaging-projectmetadata-diagnostic-collection.md`. Then read the `Diagnostic Collection Pattern` and `Friend Serializer Pattern` sections in `docs/dev/architecture/design-patterns.md`. Resume at the first incomplete phase and do not revisit the architecture unless new evidence contradicts ADR 0006.
