# Changelog

All notable changes to jBOM are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Configurable ComponentID fields per category** (issue #171): optional fields in
  a ComponentID (tolerance, voltage, current, wattage, type) are now controlled by a
  per-category allowlist in `generic.defaults.yaml` under `component_id_fields`.  For
  example, LED ComponentIDs no longer include `V=`/`A=`/`W=` — so two WS2812B
  components where one schematic annotated `Voltage=5V` and the other did not are now
  correctly treated as the same requirement.  Unlisted categories retain the previous
  behavior (all non-empty optional fields included).  The table is overridable per
  project via a `.jbom/generic.defaults.yaml` override without code changes.
- **`OPTIONAL_ID_FIELD_DEFS` / `KNOWN_OPTIONAL_FIELD_NAMES`** in
  `common/component_id.py`: single DRY authority mapping YAML profile names →
  ComponentID keys → `make_component_id` parameter names.  Extending to a new field
  (e.g. wavelength) requires one entry here plus a new `make_component_id` parameter.

### Changed
- `ProjectInventoryGenerator` accepts an optional `cwd: Path | None = None` kwarg;
  the generic defaults profile is loaded lazily from the project directory's
  `.jbom/` search path (no config injection required).

### Migration note
- **Stored ComponentIDs may change** for `led`, `cap`, `ind`, and `res` components
  that previously had partial optional-field annotations in the schematic.  Re-run
  `jbom inventory` to regenerate current IDs.

### Added
- **Catalog-driven supplier assignment** (issue #117): `NullSearchProvider` (`null_api` type) added as the built-in fixture-driven provider always available without credentials. `generic.supplier.yaml` wired with `null_api` as its search provider.
- **Inventory freshness audit** (issue #117): `jbom audit inventory.csv --supplier NAME` checks each `ITEM` row's supplier PN against a fresh catalog search. Emits `STALE_PART / WARN` when the existing PN is no longer findable; `BETTER_AVAILABLE / WARN` when a different PN ranks higher than the recorded one; silent when the existing PN matches the best result.
- **`jbom inventory --supplier NAME`** (issue #117): auto-populates `Supplier` and `SPN` columns when generating an inventory from a schematic. Rows that already have a supplier PN are preserved; new rows get the top search result filled in.
- **`jbom annotate` command** (issue #154): back-annotates KiCad schematics from an audit report. `--repairs REPORT_CSV` applies `Action=SET` rows by UUID; `--normalize` normalizes property formatting; `--dry-run` previews without writing.
- **`jbom audit --supplier NAME`** (issue #154): supplier validation tier checks each component against a distributor catalog (Mouser, LCSC, Generic). Emits `SUPPLIER_MISS / ERROR` when unfindable; `INVENTORY_GAP / INFO` when found at supplier but absent from local `--inventory`. Works standalone or combined with `--inventory`.
- **`jbom audit --api-key KEY`** (issue #154): API key override for `--supplier` catalog searches.
- **`services/search/provider_factory.py`** (issue #154): extracted `create_search_provider()` and `build_search_cache()` as a reusable module (previously embedded in the retired `inventory-search` CLI).
- **Multi-project batch inventory** (issue #144): `jbom inventory` now accepts multiple project paths (`jbom inventory p1 p2 p3 -o combined.csv`). COMPONENT rows are merged and deduplicated on `ComponentID` (first-seen wins); field names are unioned across all projects. Per-project failures are skipped by default with a summary printed at the end; use `--stop-on-error` to abort on first failure. Single-project behaviour is unchanged. `scripts/harvest_combined.py` is superseded by this feature.
- **Harvest fidelity fields** (issue #126): `InventoryItem` now carries first-class `footprint_full`, `symbol_lib`, `symbol_name`, `pins`, and `pitch` fields. KiCad harvest populates them by parsing `NICKNAME:ENTRY_NAME` from `lib_id`. `InventoryReader` round-trips them from CSV; absent columns default to empty string.
- **Phase 4 CAP technology detection** (issue #126): `_build_capacitor_plan` routes to **Aluminum Electrolytic Capacitors** when `C_Polarized` appears in `symbol_name` or the footprint entry name starts with `CP_`; otherwise routes to **Multilayer Ceramic Capacitors (MLCC)**. Dielectric is excluded from electrolytic keyword queries.
- **Phase 4 IND plan** (issue #126): Ferrite beads (`FERRITE` in description), power inductors (`L_Core` symbol or large package), and signal/RF inductors (default) each route to the correct JLCPCB sub-category.
- **Phase 4 CON plan** (issue #126): Uses first-class `pins`/`pitch` fields and parses KLC footprint entry names for pitch, pin count, and series (`PinHeader`, `JST_PH`, etc.).
- **JLCPCB route rules** for `inductor` and `connector` categories in `generic.defaults.yaml`; `capacitor` gains `second_sort_mlcc` and `second_sort_electrolytic`.
- **`docs/kicad-best-practices.md`**: user guide for per-category KiCad property recommendations.
- **Scoring-based component classifier** (issue #149): `_get_component_type_heuristic` replaced with a weighted signal / bidding model. Each `ClassificationSignal` votes for a category; the highest total score wins. No ordering dependency — adding a new signal never requires knowing where to insert it.
- **IPC reference designator signals**: `get_component_type()` now accepts a `reference` parameter (e.g. `"J1"`, `"FB2"`, `"U4"`). Reference prefix signals follow IPC convention and carry high weight: `J`→CON (5.0), `FB`→IND (6.0), `D`→DIO (3.0), `Q`→Q (3.0), `U`→IC (3.0), `K`→RLY (5.0), `Y`→OSC (5.0), `F`→FUS (5.0). `FB` at 6.0 outweighs `F`→FUS for ferrite bead components.
- **Footprint library prefix signals**: footprint strings now vote for passive/discrete categories (`CAPACITOR`→CAP, `RESISTOR`→RES, `LED`→LED, `CONNECTOR`→CON, `DIODE`→DIO, `INDUCTOR`→IND) at weight 4.0, in addition to the existing IC footprint detection.
- **FUSE component type** (`ComponentType.FUSE = "FUS"`): detected via `FUSE` name substring, `F*` RefDes prefix, or exact `FUSE` library name lookup.
- **Per-signal score logging**: `logging.debug` emits the full scores dict and the winning category for each classification, enabling diagnostic tracing at debug log level.
- 23 new unit tests covering: scoring model structure, multi-signal scoring (CLED_RGB, CONNECTOR, CD4011), IC-pattern-vs-prefix precedence, all 8 IPC RefDes prefix signals, FB-vs-F disambiguation, and FUSE detection.

### Removed
- **`inventory-search` command** (issue #154): retired; bulk catalog search is now available via `jbom audit --supplier`. Migrate: `jbom inventory-search inventory.csv --provider mouser` → `jbom audit ./my_project --supplier mouser -o report.csv`.

### Changed
- Component classifier heuristic now checks connector/specific-name patterns before generic single-letter prefixes, preventing `CONNECTOR_*` symbols from being misclassified as capacitors (#145). **Superseded by scoring model** — band-aid ordering no longer needed, but test coverage retained as scoring regression tests.
- Added LED/non-RCL regression coverage to lock stopgap behavior: C-prefixed LED-like symbols are guarded from CAP misclassification (#147). **Superseded by scoring model** — `LED` signal (7.0) reliably beats `C` prefix (1.0).
- Typed parametric decode is now category-gated in both project inventory generation and inventory CSV intake: only the category-matching typed field is decoded, with UNK/Unknown/blank promotion only when exactly one typed attribute is present; ambiguous typed attributes now log a warning and decode none (#146).
- Mouser provider now supports configurable timeout + retry/backoff for transient failures.
- LCSC supplier profile now uses `jlcpcb_api` (live API) instead of the `jlcparts_sqlite` stub.
- Search parametric filtering now supports category-aware value normalization for RES/CAP/IND/REG and uses canonical values as a tertiary sort key.
- `jbom search` console output now includes Description plus up to 2 heuristic parametric columns.
- LCSC search now applies Issue #115 Phase 4 foundation heuristics for RES/CAP parametric query shaping (category/spec/attribute payloads with static defaults and safe keyword fallback).
- `inventory --no-aggregate` now emits canonical `Voltage`, `Current`, and `Power` columns (legacy `V/A/W` aliases are no longer output columns).
- `annotate --normalize` now supports standalone or combined normalize+annotate workflows, with conflict-abort behavior when alias and canonical values disagree.
- Defaults profiles now support `field_synonyms` mappings, and inventory intake resolves electrical aliases exclusively through that profile config (no hardcoded fallback alias mapping).
- Matching now treats component-side `~` attribute values as blank/no-constraint during primary filtering and property scoring.
- Documentation now clarifies that `annotate` writes non-blank CSV values literally (including `~`) while matching interprets component `~` as unconstrained.

## [7.0.0] - 2026-02-27

### Breaking Changes
- **Python 3.10+ required** (dropped 3.9). Union type syntax (`X | Y`) used throughout.
- **Architecture overhaul**: codebase promoted from `jbom-new/` to repo root. Previous
  implementation archived to `legacy/` for reference; full history retained in git.
- **No stable Python API**: `jbom.api` (from legacy) is not exposed in v7.x. The CLI
  is the stable public interface. A clean API for KiCad plugin integration is planned for v8.x.

### Added
- **`parts` command**: generate a per-reference parts list (unaggregated) from a KiCad
  schematic, with optional inventory enrichment.
- **`inventory-search` command**: bulk catalog search against an inventory CSV to find
  candidate supplier part numbers. Includes `--dry-run` for validation without API calls.
- **Service-Command architecture**: clean separation of business logic (`services/`),
  shared types (`common/`), and thin CLI wrappers (`cli/`). No circular imports.
- **Sophisticated inventory matcher**: score-based matching with tolerance-aware substitution,
  priority-based tie-breaking, and category-specific field handling.
- **Supplier profiles**: YAML-defined supplier configs for Mouser, LCSC, DigiKey, and Generic.

### Changed
- All commands now use `--inventory` (repeatable for `bom`; single for `inventory`/`parts`).
- `pos --units` accepts `mm` only (was `mm` and `inch`; inch output removed).
- `bom` always aggregates by value+package (procurement view). Use `parts` for
  per-reference output.

### Deferred
- **`annotate` command** (back-annotation to KiCad schematics): implementation is in
  `legacy/src/jbom/cli/commands/builtin/annotate.py` and is planned for promotion in v8.x.

## [3.6.0] - 2025-12-21

### Added
- **Inventory Search Automation**: Enhanced `inventory` command with automated part search capabilities.
  - New `--search` flag enables automatic part searching from distributors during inventory generation.
  - Search options: `--provider` (mouser), `--api-key` (or MOUSER_API_KEY env var), `--limit` (including 'none' for unlimited), `--interactive`.
  - Priority-based ranking combines technical matching with supplier quality metrics (stock, lifecycle, price).
  - Search statistics reporting shows provider, searches performed, success/failure counts.
- **Enhanced Inventory API**: New `generate_enriched_inventory()` API function with search integration.
  - Consistent keyword-only parameter patterns following jBOM API standards.
  - `InventoryOptions` dataclass for search configuration.
  - Comprehensive error handling and graceful degradation.
- **Core Search Integration Classes**:
  - `SearchResultScorer`: Intelligent scoring algorithm combining InventoryMatcher logic with supplier metrics.
  - `InventoryEnricher`: Batch processing engine with rate limiting and error recovery.
- **Comprehensive Test Coverage**: 100% test coverage for new functionality.
  - Unit tests for all new classes and API functions.
  - Functional tests for CLI integration with mocked search providers.
  - End-to-end workflow testing.

### Changed
- **Inventory Workflow Enhancement**: The `inventory` command now supports search-enhanced workflows that automatically associate inventory items with real-world purchasable parts.
- **Priority System**: Lower priority numbers indicate better choices (1=best match) for consistent ranking.

## [3.4.0] - 2025-12-21

### Added
- **Config-Driven Fabricators**: Both BOM and POS commands now fully use the configuration system for fabricator definitions.
  - POS columns and header mapping now defined in YAML configuration.
  - Fabricator flags (`--jlc`, `--seeed`, etc.) and presets are auto-generated from config.
  - Config merging now uses **REPLACE** strategy for list/dict fields, allowing users to fully override default column sets.
- **Prefix Handling**: Added robust handling for `I:` (Inventory) and `C:` (Component) prefixes in fabricator part number configuration.
  - `I:` prefix is supported and stripped for lookup.
  - `C:` prefix triggers a helpful warning (as component properties are not available during part number resolution).
- **Config-Driven Classification**: Component classification now uses a rule-based engine defined in YAML configuration.
- **Debug Categories**: Added support for granular debug control via `debug_categories`.
- **POS Fabricator Support**: Added `--fabricator` option to `pos` command with presets for JLC, PCBWay, and Seeed.

### Changed
- **POS Command Refactor**: Removed hardcoded field presets from `POSGenerator`; now driven entirely by fabricator config.
- **BOM Command Refactor**: Updated to share common fabricator configuration logic with POS.
- **Configuration Logic**: Changed config merging strategy to REPLACE for dictionary fields (`bom_columns`, `pos_columns`, `part_number`, etc.) to allow removing default fields.
- Refactored `get_component_type` to use the new `ClassificationEngine`.
- Moved hardcoded classification rules to `src/jbom/config/defaults.yaml`.

### Removed
- Removed hardcoded fabricator presets (`jlc`, `seeed`, `pcbway`) from `src/jbom/common/fields.py`.

## [3.3.1] - 2025-12-20

### Fixed
- CI workflow dependency installation to include `pyproject.toml` dependencies.
- Added missing `PyYAML` dependency.
- Code formatting and linting fixes.

## [3.3.0] - 2025-12-18

### Added
- **Search Command**: `jbom search` for parts via Mouser API with smart filtering.
- **Federated Inventory**: Support for loading multiple inventory files.
- **PCBWay Support**: Initial fabricator logic for PCBWay.

## [3.2.0] - 2025-12-18

### Added
- **Search Command**: New `jbom search` CLI for finding parts via Mouser API.
  - Supports smart filtering: `In Stock > 0`, `Active` status, and parametric text matching.
  - Returns curated results table sorted by availability and price.
- **Fabrication Support**: Added dedicated support for **PCBWay**.
  - `jbom bom ... --fabricator pcbway` generates BOMs with specific headers (`Manufacturer Part Number`, `Distributor Part Number`) required by PCBWay assembly service.
  - Prioritizes distributor SKUs (DigiKey/Mouser) over MPNs when available.
- **Federated Inventory**: Full support for loading multiple inventory sources simultaneously.
  - `jbom bom ... -i local.csv -i jlc_export.xlsx` merges items.
  - Conflict resolution prioritizes local user definitions over imported vendor files.
- **Data Model Enhancements**: `InventoryItem` now tracks `source`, `distributor`, and `distributor_part_number`.

### Changed
- **Inventory Loader**: Now auto-maps common CSV columns (e.g., "DigiKey Part Number", "SKU") to standard internal fields.
- **BOM Generation**: Refactored to delegate column mapping to `Fabricator` plugins, enabling per-vendor CSV layouts.

## [3.1.0] - 2025-12-17

### Added
- **Back-Annotation**: New `jbom annotate` command to update KiCad schematics with data from inventory.
  - Pushes `Value`, `Footprint`, `LCSC`, and other fields back to the schematic symbol.
  - Uses UUID matching for reliability even if reference designators change.
  - Includes a "Safety Shim" to abstract S-expression parsing, preparing for future KiCad Python API adoption.
- **Placement Generation**: `jbom pos` command for pick-and-place files.
  - Supports JLC-specific rotation corrections.
  - customizable output formats.

### Changed
- **CLI Architecture**: Complete refactor to subcommand-based CLI (`jbom bom`, `jbom pos`, `jbom inventory`, `jbom annotate`).
- **Python API**: Introduced `jbom.api` as the unified entry point for programmatic use.

## [3.0.0] - 2025-12-16

### Added
- **Data-Flow Architecture**: Major refactoring into `loaders/`, `processors/`, and `generators/` modules.
- **JLCPCB Private Library Support**: Native loader for JLC's Excel export format.
- **Fabricator Abstraction**: Core `Fabricator` base class to support multiple vendors (JLC, Seeed, PCBWay, Generic).

### Changed
- **Breaking**: CLI arguments significantly changed to support subcommands.
- **Breaking**: Python API imports moved to `jbom.api`.

## [1.0.2] - 2025-12-14

### Added
- Pre-commit hook configuration for automated secret detection and code quality
- Comprehensive pre-commit hooks guide: `PRE_COMMIT_SETUP.md`
- Quick reference guide for pre-commit operations: `PRE_COMMIT_QUICK_REFERENCE.md`
- Security incident report documentation: `SECURITY_INCIDENT_REPORT.md`
- GitHub secrets and CI/CD configuration guide: `GITHUB_SECRETS_SETUP.md`

### Changed
- Reorganized documentation for clarity:
  - All user-facing and developer documentation moved to `docs/` folder (included in PyPI)
  - Release management and security documentation moved to `release-management/` folder (excluded from PyPI)
  - `README.man*` files consolidated in `docs/` for consistency
- Simplified MANIFEST.in using `recursive-include docs *` pattern
- Updated cross-references throughout documentation to reflect new structure
- WARP.md now includes updated directory structure

### Improved
- Repository root is now cleaner with only `README.md` at the top level
- Better separation of concerns: user docs vs release/security management
- PyPI package is leaner by excluding release management documentation
- All documentation now properly indexed in `docs/` folder

## [1.0.1] - 2025-12-14

### Added
- Case-insensitive field name handling throughout the system
- `normalize_field_name()` function for canonical snake_case normalization
- `field_to_header()` function for human-readable Title Case output
- Man page documentation files:
  - `README.man1.md` - CLI reference with options, fields, examples, troubleshooting
  - `README.man3.md` - Python library API reference for programmatic use
  - `README.man4.md` - KiCad Eeschema plugin setup and integration guide
  - `README.man5.md` - Inventory file format specification with field definitions
- `README.tests.md` - Comprehensive test suite documentation
- `SEE ALSO` sections with markdown links in all README files
- Python packaging infrastructure:
  - Modern `pyproject.toml` with comprehensive metadata
  - `setup.py` for legacy compatibility
  - `MANIFEST.in` for non-Python files
  - `src/jbom/` package structure following Python best practices
  - Console script entry point for `jbom` command

### Changed
- Enhanced tolerance substitution scoring:
  - Exact tolerance matches always preferred
  - Next-tighter tolerances preferred over tightest available
  - Scoring penalty for over-specification (gap > 1% gets reduced bonus)
- Updated all field processing to use normalized snake_case internally
- CSV output headers now in human-readable Title Case
- Test suite expanded from 46 to 98 tests across 27 test classes
- Project naming standardized to "jBOM" throughout documentation
- Version number updated to 1.0.1 in all files

### Fixed
- Field name matching now handles all formats: snake_case, Title Case, CamelCase, UPPERCASE, spaces, hyphens
- Tolerance substitution now correctly implements preference ordering
- I:/C: prefix disambiguation system fully functional

### Removed
- Redundant Usage Documentation section from README.md
- Duplicate information consolidated into SEE ALSO sections

## [1.0.0] - 2025-12-13

### Added
- Initial stable release of jBOM
- KiCad schematic parsing via S-expression format
- Hierarchical schematic support for multi-sheet designs
- Intelligent component matching using category, package, and numeric value matching
- Multiple inventory formats: CSV, Excel (.xlsx/.xls), Apple Numbers (.numbers)
- Advanced matching algorithms:
  - Type-specific value parsing (resistors, capacitors, inductors)
  - Tolerance-aware substitution
  - Priority-based ranking
  - EIA-style value formatting
- Debug mode with detailed matching information
- SMD filtering capability for Surface Mount Device selection
- Custom field system with I:/C: prefix disambiguation
- Comprehensive test suite (46 tests across 14 test classes)
- Multiple integration options:
  - KiCad Eeschema plugin via `kicad_jbom_plugin.py`
  - Command-line interface with comprehensive options
  - Python library for programmatic use
- Extensive documentation:
  - `README.md` - User-facing overview and quick start
  - `README.developer.md` - Technical architecture and extension points
  - Full docstrings and inline comments throughout

[1.0.2]: https://github.com/SPCoast/jBOM/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/SPCoast/jBOM/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/SPCoast/jBOM/releases/tag/v1.0.0
