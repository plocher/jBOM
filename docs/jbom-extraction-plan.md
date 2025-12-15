# Extracting Schematic/Inventory Code Out of jbom.py

Problem
`src/jbom/jbom.py` (~2500 lines) mixes multiple responsibilities: schematic parsing, inventory loading/matching, BOM generation, field systems, and supporting utilities. This increases maintenance cost and obscures logical ownership (schematic vs inventory vs shared).

Current State (Dec 2025)
- KiCad schematic parsing lives in `KiCadParser` within `jbom.py`.
- BOM generation code (BOMEntry, generate_bom flow, field parsing) also lives in `jbom.py`.
- InventoryMatcher is coupled in the same file.
- Shared helpers were partially extracted (common/options.py, common/fields_system.py, common/output.py, common/sexp_parser.py).

Goal
Move schematic-specific and inventory-specific code into their respective packages while keeping backward compatibility via re-exports from `jbom.py`.

Scope & Targets
- Move schematic items to `src/jbom/sch/`:
  - `KiCadParser` → `sch/parser.py`
  - `Component` model → `sch/model.py`
  - BOM types & generator functions (`BOMEntry`, `generate_bom_api`, helpers) → `sch/bom.py` and `sch/api.py`
- Move inventory items to `src/jbom/inventory/`:
  - `InventoryItem`, `InventoryMatcher` → `inventory/model.py`, `inventory/matcher.py`
- Keep `jbom.py` as a thin façade re-exporting public API for compatibility.

Back-compat Strategy
- Public imports that must continue to work:
  - `from jbom import generate_bom_api, GenerateOptions`
  - `from jbom.jbom import InventoryMatcher, BOMEntry, Component`
- `jbom.py` should import from new modules and expose the same names.
- No behavioral changes, only imports/locations.

Phased Plan
1. Create destination modules with code moves but no functional changes.
   - `sch/model.py`, `sch/parser.py`, `sch/bom.py`, `inventory/model.py`, `inventory/matcher.py`.
2. Update internal imports in `jbom.py` to import from the new modules.
3. Add re-exports in package `__init__.py` files to present stable API.
4. Run tests; fix relative import paths and circular deps.
5. Update docs to show canonical imports (keep legacy examples in compatibility notes).

Risk & Mitigations
- Circular imports: keep data classes and pure utilities separate from code with heavy dependencies.
- Test coverage: run unit tests after each move; avoid logic edits during move.
- CLI impact: none expected; CLI imports already decoupled.

Effort Estimate
- Extraction: 6–8 hours
- Import updates: 2–3 hours
- Test stabilization: 3–4 hours

Exit Criteria
- `jbom.py` < 800 LOC and primarily re-exports.
- All tests pass with no API changes for library users.
