# ADR 0016: EagleLib2KiCad Adapter Requirements (Service-Surface-First)
Date: 2026-02-25
Status: Accepted (service-API contract)

## Context
Define the jBOM-side preparation boundary for Eagle→KiCad library-management integration while keeping implementation-heavy work in the `EagleLib2KiCad` repository for now.

### Existing jBOM service surfaces intended for reuse
- KiCad project context and component collection (`ProjectContext`, `ProjectComponentCollector`).
- Inventory context ingestion (`InventoryReader` and downstream matching services).
- Supplier context/search (`InventorySearchService` and provider stack).
- Matching/categorization behavior (`SophisticatedInventoryMatcher`, component classification utilities).

### KiCad library-management semantics to be validated in adjacent tool first
- Multi-library-set loading semantics (many symbol libraries + many footprint libraries).
- Nickname-aware environment discovery semantics.
- Footprint reference closure reporting (resolved, unresolved, ambiguous).
- Library lifecycle semantics (add/remove/rename) aligned with KiCad workflows.

## Decision
### Core policy
- jBOM service APIs are the long-term contract model for both in-core workflows and adjacent tools/plugins.
- Do not introduce a parallel adapter model hierarchy.
- Short-term implementation-heavy service evolution for Eagle/KiCad library management is intentionally incubated in `EagleLib2KiCad`.
- Future convergence work can merge mature service APIs into jBOM when semantics stabilize.

### jBOM scope for this prep slice
- Document service-surface-first integration boundary.
- Preserve architecture links and future expansion direction.
- Avoid implementation-heavy importer/library-manager services in jBOM at this time.

### Contract validation strategy for this slice
- Keep jBOM regression focused on existing stable behaviors.
- Adjacent tool (`EagleLib2KiCad`) carries new service-contract behavior scenarios while APIs are still evolving.

## Consequences
### Out of scope in this jBOM slice
- New Eagle parsing services in jBOM.
- New KiCad library environment management services in jBOM.
- Importer analysis/review-queue workflow policy in jBOM.

## Provenance

Normalized into formal ADR format on 2026-05-25 under issue #300.
Source file(s):

- `docs/dev/architecture/eaglelib2kicad-adapter-requirements.md` (content preserved verbatim)
