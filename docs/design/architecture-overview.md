# Architecture Overview

jBOM is a fabrication tool with two core capabilities: BOM generation and placement
(CPL/POS) generation. BOM generation matches schematic components against inventory
spreadsheets to produce fabrication-ready BOM CSVs; placement generation extracts
pick-and-place coordinates from KiCad PCB files. Both capabilities share a common
layered architecture, unified configuration system, and domain type library.

The architecture is domain-centric, following the commitment in
[ADR 0013 (Domain-Centric Design)](../architecture/adr/0013-domain-centric-design.md).
The core invariant is that dependency flows inward: adapters depend on application
workflows, workflows depend on services, and services depend only on the shared domain
model (`common/`). Nothing in the domain or service layers imports from `cli/` or
`application/`.

## Module Structure

jBOM uses an adapter → application → services layering:

```
src/jbom/
├── application/         # Adapter-neutral workflow orchestration
│   ├── bom_workflow.py             # BOM request/result workflow
│   ├── pos_workflow.py             # POS request/result workflow
│   ├── fabrication_orchestration.py  # End-to-end fabrication workflow
│   └── jobs/                       # Job contracts and runner
│
├── cli/                 # Command-line adapters (thin wrappers over application/services)
│   ├── main.py          # Argparse dispatcher and subcommand registration
│   ├── __main__.py      # python -m jbom entrypoint
│   ├── output.py        # Shared output helpers
│   ├── discovery.py     # Command auto-discovery
│   ├── formatting.py    # Console output formatting
│   ├── bom.py           # bom command
│   ├── fabrication.py   # fabrication command
│   ├── gerbers.py       # gerbers command
│   ├── annotate.py      # annotate command
│   ├── audit.py         # audit command
│   ├── config.py        # config command
│   ├── inventory.py     # inventory command
│   ├── parts.py         # parts command
│   ├── pos.py           # pos command
│   └── search.py        # search command
│
├── common/              # Shared domain types and utilities
│   ├── types.py         # Data classes: Component, InventoryItem, BOMEntry
│   ├── constants.py     # Enums and shared constants
│   ├── fields.py        # Field presets and field-to-header conversion
│   ├── field_parser.py  # Field argument parsing and validation
│   ├── options.py       # GeneratorOptions dataclass
│   ├── cli_fabricator.py        # Fabricator CLI argument helpers
│   ├── component_classification.py  # Component type classification
│   ├── component_filters.py     # DNP/exclude/include-all filtering
│   ├── component_utils.py       # Component utility functions
│   ├── package_matching.py      # Package extraction and matching
│   ├── packages.py              # Package type definitions
│   ├── pcb_types.py             # PCB component data structures
│   ├── sexp_parser.py           # S-expression parsing
│   └── value_parsing.py         # Value parsing (R, C, L numeric comparison)
│
├── config/              # Unified profile loading and schema models
│   ├── unified.py       # *.jbom.yaml merge/extends/search engine
│   ├── profile_search.py  # Search-path resolution (.jbom, env, system, built-ins)
│   ├── fabricators.py   # Fabricator stanza schema + loaders
│   ├── suppliers.py     # Supplier stanza schema + loaders
│   └── defaults.py      # Defaults stanza schema + loaders
│
├── services/            # Business logic
│   ├── schematic_reader.py          # Parse .kicad_sch files (hierarchical)
│   ├── pcb_reader.py                # Parse .kicad_pcb files
│   ├── inventory_reader.py          # Load CSV/Excel/Numbers inventory files
│   ├── inventory_matcher.py         # Match schematic components to inventory
│   ├── sophisticated_inventory_matcher.py  # Heuristic signal-voting matcher for non-passives
│   ├── inventory_validator.py       # Inventory data validation
│   ├── bom_generator.py             # Generate BOM CSV output
│   ├── bom_writer.py                # Persist BOM CSV output
│   ├── pos_generator.py             # Generate CPL/POS placement output
│   ├── pos_writer.py                # Persist POS/CPL CSV output
│   ├── parts_list_generator.py      # Generate parts list output
│   ├── fabricator_inventory_selector.py  # Fabricator-aware part selection
│   ├── gerber_service.py            # Gerber export via kicad-cli/pcbnew
│   ├── gerber_packager.py           # Gerber zip packaging policy
│   ├── backup_service.py            # Production artifact backup archives
│   ├── project_context.py           # Project file context
│   ├── project_discovery.py         # Discover project files in directory
│   ├── project_file_resolver.py     # Resolve input paths to project files
│   ├── project_inventory.py         # Per-project inventory management
│   ├── project_metadata.py          # Title-block/archive metadata extraction
│   ├── supplier_url_resolver.py     # Resolve supplier URLs from part numbers
│   └── search/                      # Online component search
│       ├── models.py                # Search result data models
│       ├── provider.py              # Abstract search provider interface
│       ├── provider_factory.py      # Search provider selection
│       ├── filtering.py             # Search result filtering
│       ├── cache.py                 # Search result caching
│       └── inventory_search_service.py  # Orchestrate inventory-wide search
```

The `application/jobs/` subdirectory holds job contracts described in
[ADR 0014 (Job Contracts)](../architecture/adr/0014-job-contracts.md). The `config/`
layer implements the unified `*.jbom.yaml` profile system described in
[ADR 0008 (Unified Config Schema)](../architecture/adr/0008-unified-jbom-config-schema.md).

## Key Design Principles

**Layered orchestration.** CLI modules and the KiCad plugin are adapters: they
parse arguments and render output, but all orchestration and business rules live in
`application/` workflows and `services/`. This keeps the domain logic testable and
reusable across interfaces.

**Thin adapters.** A CLI module's only responsibilities are argument parsing, calling
`.run(request)` on the appropriate workflow, rendering diagnostics, and mapping
outcomes to exit codes. No CLI module contains matching logic, field resolution, or
output formatting beyond string rendering.

**Shared domain types.** `common/types.py` defines `Component`, `InventoryItem`, and
`BOMEntry`—the three core entities that flow between layers. All layers speak the same
type language; there are no per-layer DTO transformations.

**Configuration-driven behavior.** `config/` profiles (`*.jbom.yaml`) drive
fabricator, supplier, and default behavior without code changes. The `extends:` key
enables profile inheritance; the search path (`.jbom/`, env, system, built-ins)
follows a deterministic resolution order.

**No circular dependencies.** The import hierarchy is strict:
`common` → `config`/`services` → `application` → `cli`. Services never import from
`application/` or `cli/`; common never imports from any other layer.

**Simple CLI registration.** Each CLI subcommand is an explicit module that implements
`register_command(subparsers)`. There is no plugin registry; `cli/main.py` imports
command modules directly, making the set of commands immediately readable from a
single file.

**Naming reflects promise, not mechanism.** Workflow classes are named for what they
produce (`BOMWorkflow`, `POSWorkflow`, `FabricationWorkflow`); private helpers use
functional names (`_list_fields`, `_generate`). The `Service` suffix and the word
`Orchestration` are omitted—the module path already provides that context. See
`src/WARP.md` for the full naming convention.

## Hierarchical Schematic Support

jBOM fully supports KiCad's hierarchical schematic designs. When the input is a
directory, `schematic_reader.py` identifies the hierarchical root (the file that
contains sheet references) and processes all referenced sub-sheets recursively,
combining their component lists. This means a multi-sheet design produces the same
BOM as if all symbols were on a single sheet.

File selection within a directory uses a priority order that avoids false positives
from sub-sheets or mismatched filenames:

1. Hierarchical root files whose name matches the directory name
2. Any hierarchical root file (contains sheet references)
3. Files matching the directory name (without hierarchical content)
4. Alphabetically first file

This order ensures that a directory named `Core-ESP32/` preferentially loads
`Core-ESP32.kicad_sch` rather than one of its sub-sheets, even when autosave files
are present. When an autosave file is the only hierarchical root available, jBOM
loads it with a console warning rather than silently failing.

## Data Flow

The end-to-end BOM workflow follows this sequence:

1. **Adapter normalization.** The CLI or plugin adapter translates user intent (flags,
   paths, fabricator selection) into a typed request dataclass passed to
   `BOMWorkflow.run()`.

2. **Input discovery.** The workflow resolves the schematic path and loads inventory
   files. Inventory rows are normalized and cached in memory for the duration of the
   run; loading is not repeated per-component.

3. **Schematic parsing.** `SchematicReader` parses `.kicad_sch` files via `sexpdata`
   S-expression parsing, extracting `Reference`, `Value`, `Footprint`, `Tolerance`,
   and other properties from each symbol.

4. **Component grouping.** Components are grouped by their best matching inventory
   item (IPN + footprint) so that equivalent notations (e.g., `330R`, `330Ω`,
   `330 ohm`) collapse into a single BOM row.

5. **Primary filtering.** For each candidate group, the component type
   (`RES`/`CAP`/`IND`/`LED`/etc.) is derived from `Footprint`, and the package token
   is extracted. Candidates that fail type, package, or numeric value checks are
   excluded before scoring.

6. **Scoring and ranking.** The primary sort key is the `Priority` field from the
   inventory CSV (1 = most desirable, higher = less desirable). A secondary technical
   score accumulates points for category match, value match, footprint match, and
   property matches such as `Tolerance` and power rating. Tighter tolerances (1%, 5%)
   can substitute for looser requirements (10%).

7. **Selection.** The highest-scoring candidate becomes the main BOM row. Up to two
   additional candidates are emitted as `ALT` rows for visibility.

8. **Tolerance warnings.** If the schematic implies 1% precision (trailing digit like
   `10K0`, `47K5`, or explicit `Tolerance ≤ 1%`) but no matched inventory item is
   1%, the `Notes` column records a warning naming the best tolerance found.

9. **Value formatting.** Values are rendered in EIA-style format:
   resistors as `3R3`/`330R`/`10K`/`10K0`/`1M`, capacitors as `100nF`/`1uF`, and
   inductors as `10uH`/`2m2H`. The trailing digit for resistors is driven by
   schematic precision or tolerance.

10. **BOM emission.** The workflow returns a `BOMResult` containing the entries,
    diagnostics, and any excluded-component count. The CLI adapter renders this to
    CSV or stdout; `BOMWriter` handles file-based persistence.

11. **Unmatched component diagnostics.** Components that find no inventory match emit
    structured diagnostics (type detected, package detected, specific issue) as part
    of the result contract. The adapter renders these to stderr and optionally to the
    BOM's `Notes` column.

## Two Matching Strategies

jBOM provides two matching approaches for different component types. `inventory_matcher.py`
implements the standard score-based matcher used by the BOM workflow. `sophisticated_inventory_matcher.py`
provides an alternative with a configurable heuristic signal-voting model: it
preserves strict numeric matching for passives (RES/CAP/IND) while using weighted
signal votes for non-passives, where free-form inventory field relationships make
exact numeric comparison unreliable. The two matchers share the same `Component` and
`InventoryItem` domain types and can be composed without changing the workflow layer.

## PCB Module Architecture

The PCB module extracts component placement data from `.kicad_pcb` files for
pick-and-place assembly. Its key design decision is a dual-mode board loader:

**pcbnew API mode** uses KiCad's native Python API when available (requires a KiCad
Python environment). This is the most complete path, accessing all footprint
properties directly.

**S-expression mode** uses jBOM's own `sexpdata`-based parser. This path works
without any KiCad installation, making jBOM usable in CI and headless environments.
It handles both KiCad 7 and KiCad 8 property formats, with graceful degradation for
malformed files.

**Auto mode** (the default) tries the pcbnew API first and falls back to S-expression
parsing automatically, requiring no configuration from the user.

`PositionGenerator` operates on the `BoardModel` produced by `BoardLoader`,
applying field selection (presets: `+kicad_pos`, `+jlc`, `+minimal`, `+all`),
unit conversion (mm/inch), origin selection (board origin or auxiliary axis), and
layer/SMD filtering before writing the CSV.

## Spreadsheet Support Architecture

All inventory formats converge at a single processing pipeline in `inventory_reader.py`.
Format detection is by file extension (`.csv`, `.xlsx`/`.xls`, `.numbers`). Missing
optional libraries (openpyxl, numbers-parser) produce a clear error message rather
than a silent fallback.

The design intent is that the matching logic above the reader is completely
format-neutral: the reader's job is to normalize any tabular source into a list of
row dicts with consistent field names. All downstream code operates on those dicts,
not on file-format objects.

Excel loading includes intelligent header detection—it searches the first ten
rows and columns for an `IPN` column to accommodate real-world spreadsheets where
data does not start at cell A1. Apple Numbers loading uses the `numbers-parser`
library's proper cell-access API to handle Numbers-specific table structure.

## Component Classification

Component type (`RES`, `CAP`, `IND`, `LED`, etc.) is determined by the
`HeuristicComponentClassifier` in `common/component_classification.py`. The
classifier uses a fixed evaluation order:

1. Direct lookup in `COMPONENT_TYPE_MAPPING` (the authoritative alias table in
   `common/constants.py`)
2. Footprint-based IC detection (recognizes SOIC, QFN, BGA, DIP, etc.)
3. Pattern-based detection on `lib_id` (matches prefixes and keywords: LED, LM\*,
   74\*, R, C, L, D, Q, U, J, SW)
4. Returns `None` if unrecognized (conservative: callers decide how to handle unknown types)

The classifier is accessed through the `get_component_type()` function, which accepts
an optional `classifier=` keyword argument. Any object implementing the
`ComponentClassifier` Protocol (a single `classify(lib_id, footprint) -> str | None`
method) can be injected. This is the stable extension point for projects with
non-standard library naming conventions; see the
[extend-jbom skill](../../.agents/skills/extend-jbom/SKILL.md) for the recipe.

---

*For the layering and pattern decisions behind this structure, see*
*[ADR 0013 (Domain-Centric Design)](../architecture/adr/0013-domain-centric-design.md)*
*and [ADR 0011 (Project-Centric Design)](../architecture/adr/0011-project-centric-design.md).*
*Extension recipes live in the [extend-jbom skill](../../.agents/skills/extend-jbom/SKILL.md).*
*Mutable design rationale for the service/command split is in*
*[service-command-architecture.md](service-command-architecture.md).*
