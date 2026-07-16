# jbom(1) — jBOM CLI Reference

<!-- GENERATION CANDIDATE: This file is hand-curated. It is a candidate for
     automated generation from the argparse registry once the extraction
     generator lands (#269). Until then, keep it in sync with
     src/jbom/cli/ manually and verify flags against the source before
     editing. -->

## NAME

jbom — generate Bill of Materials, Placement Files, and Parts Lists from KiCad projects

## SYNOPSIS

```
jbom [-q] [--version]
jbom audit PATH [PATH ...] [--inventory CATALOG_CSV] [--supplier NAME] [--api-key KEY] [--requirements REQ_CSV] [--datasheet-library LIBRARY_DIR] [--check-urls] [-o REPORT_CSV] [--strict] [-v]
jbom annotate INPUT [--repairs REPORT_CSV] [--normalize] [--dry-run]
jbom bom [PROJECT] [--inventory FILE ...] [-o OUTPUT] [BOM OPTIONS]
jbom pos [PROJECT] [-o OUTPUT] [POS OPTIONS]
jbom gerbers [PROJECT] [-o OUTPUT_DIR] [--fabricator NAME] [--no-drill] [--netlist] [--dry-run]
jbom fab [PROJECT] [-o OUTPUT_ROOT] [--fabricator NAME] [--skip-bom] [--skip-pos] [--skip-gerbers] [--debug] [--dry-run]
jbom inventory [PROJECT] [-o OUTPUT] [--supplier SUPPLIER_ID ...] [--api-key KEY_OR_SUPPLIER_KEY ...] [INVENTORY OPTIONS]
jbom inventory admit [--inventory CATALOG_CSV ...] [--manifest PATH] [--staging-dir PATH] [--library-dir PATH]
jbom inventory admit --apply [--manifest PATH] [-o PASTE_CSV] [-F] [-v]
jbom promote SOURCE_INVENTORY [--supplier SUPPLIER_ID ...] [--api-key KEY_OR_SUPPLIER_KEY ...] [--jlc] [-o OUTPUT] [-F] [-v]
jbom parts [PROJECT] [-o OUTPUT] [PARTS OPTIONS]
jbom search QUERY [SEARCH OPTIONS]
```

## DESCRIPTION

jBOM provides ten subcommands:

- `audit` — diagnose field-quality issues and inventory coverage gaps in KiCad projects or catalog files
- `annotate` — back-annotate KiCad schematics with approved field values from an audit report
- `bom` — generate a procurement BOM from KiCad schematics matched against an inventory file
- `pos` — generate component placement files (CPL/POS) from KiCad PCB files
- `gerbers` — generate Gerber/drill files from a KiCad PCB file via kicad-cli
- `fab` — one-shot fabrication: BOM + placement + Gerbers, written to a `production/` folder
- `inventory` — generate an initial inventory template from schematic components
- `promote` — convert a supplier-export CSV into canonical jBOM inventory rows: parse descriptions, derive identity, and optionally enrich via the selected supplier provider
- `parts` — generate an unaggregated parts list (one row per component) from schematics
- `search` — search external distributor catalogs (e.g. LCSC, Mouser) by keyword or part number

The BOM workflow keeps designs supplier-neutral: components carry generic values in the schematic; an inventory file maps those values to specific supplier part numbers at generation time.

## GLOBAL OPTIONS

**-q, --quiet**
: Suppress `info` and `warning` severity diagnostics printed to stderr (e.g. `bom`'s
  "Missing important ... fields" completeness warning, `Selected fields: ...`, and
  similar guidance). `error` severity diagnostics are always printed regardless of
  this flag. Stdout is never affected -- `-o -` CSV output stays pure CSV whether or
  not `-q` is given; diagnostics always go to stderr. This flag operates at the CLI
  adapter level via the shared `print_diagnostics()` helper; service-layer diagnostics
  are always collected and available regardless of this flag.

**--version**
: Print jBOM version and exit.

## AUDIT COMMAND

```
jbom audit PATH [PATH ...]  [--inventory CATALOG_CSV]  [--supplier NAME] [--api-key KEY]  [-o REPORT_CSV]  [--strict] [-v]
jbom audit CAT.CSV [...]    [--requirements REQ_CSV]   [--supplier NAME] [--api-key KEY]  [--datasheet-library LIBRARY_DIR] [--check-urls] [-o REPORT_CSV]  [--strict] [-v]
```

Diagnoses field-quality issues and inventory coverage gaps. Mode is detected automatically from the positional arguments:

- **Project mode** — positionals are KiCad project directories or schematic files.
- **Inventory mode** — all positionals end with `.csv`.

### Checks performed

**Local heuristics (project mode, always)**
: For every in-BOM component, the jBOM field taxonomy is checked:
  - `REQUIRED` (Value, Footprint) — `QUALITY_ISSUE` row with `Severity=ERROR` when absent.
  - `BEST_PRACTICE` (Manufacturer, MFGPN, and category-specific fields such as Tolerance for resistors) — `QUALITY_ISSUE` row with `Severity=WARN` when absent; the `SuggestedValue` column carries an example.

**Coverage dry-run (project mode + `--inventory`)**
: Runs `match()` for every component against the catalog without generating a BOM:
  - No match → `COVERAGE_GAP / ERROR`
  - Match only via heuristics → `MATCH_HEURISTIC / WARN`
  - Multiple equally-qualified candidates → `MATCH_AMBIGUOUS / INFO`
  - Single exact match or IPN/MPN exclusive match → silent

**Coverage check (inventory mode + `--requirements`)**
: Same four-outcome model applied to COMPONENT rows from the requirements file against catalog ITEM rows.
: Catalog items not matched by any requirement → `UNUSED_ITEM / INFO`

**Supplier validation (project mode + `--supplier`)**
: Bulk-searches the named distributor to verify each component is findable:
  - No results → `SUPPLIER_MISS / ERROR`
  - Found at supplier but absent from local `--inventory` → `INVENTORY_GAP / INFO` (only when `--inventory` is also given)
  - Silent when both local inventory and supplier match.

**Supplier freshness checks (inventory mode + `--supplier`)**
: When all positionals are `.csv` files and `--supplier` is given, each `ITEM` row's supplier PN is validated against a fresh catalog search:
  - Existing PN not found by a fresh search → `STALE_PART / WARN`
  - Fresh search returns a better PN than the one recorded → `BETTER_AVAILABLE / WARN`
  - Existing PN matches the best search result → silent
  - Row has no supplier PN → skipped (no check)

**Datasheet document-library hygiene checks (inventory mode, always)**
: Read-only, offline lints against the shared `SPCoast-inventory` datasheet document library (`Datasheet` URL / `Datasheet Name` columns). These run automatically for every inventory-mode audit, with no flag required:
  - `Datasheet` URL populated but `Datasheet Name` empty (dig-deeper backlog) → `DATASHEET_BACKLOG / INFO`
  - No row sharing a `Datasheet Name` carries the canonical-source URL → `DATASHEET_PROVENANCE_MISSING / WARN`
  - More than one row sharing a `Datasheet Name` carries a URL (violates the one-URL-per-Name rule) → `DATASHEET_PROVENANCE_CONFLICT / ERROR`
  - Same `Datasheet Name` spelled with inconsistent casing across rows → `DATASHEET_NAME_CASE_MISMATCH / ERROR`
  - Two distinct `Datasheet Name` values are suspiciously similar (possible spelling drift) → `DATASHEET_NAME_NEAR_COLLISION / WARN`
  - `Manufacturer` (or a `Datasheet Name` token) diverges from the catalog's canonical spelling for that manufacturer/tech token → `DATASHEET_TOKEN_MISMATCH / WARN`

**Datasheet library file-presence checks (inventory mode + `--datasheet-library`)**
: When `--datasheet-library LIBRARY_DIR` is given, curated `Datasheet Name` values are additionally checked against the library checkout's `datasheets/` directory (case-insensitive filename match):
  - A `Datasheet Name` has no matching `datasheets/<name>.pdf` → `DATASHEET_FILE_MISSING / ERROR`
  - A PDF under `datasheets/` is not referenced by any Item's `Datasheet Name` → `DATASHEET_ORPHAN_FILE / WARN`

**Datasheet URL recovery ladder (inventory mode + `--check-urls`, opt-in, NETWORK)**
: See ["Datasheet URL recovery ladder" below](#datasheet-url-recovery-ladder---check-urls-opt-in-network) for the full write-up. Summary: walks each `ITEM` row's `Datasheet` URL through a five-rung recovery ladder (direct fetch, LCSC viewer→CDN transform, LCSC product-detail API, manufacturer-URL retry, signed/ephemeral dead-by-design detection) and proposes upgrades. **Makes real network requests** -- this is the only `jbom audit` check that does so, and only when `--check-urls` is explicitly given (default off).

### Arguments

**PATH** (one or more, required)
: KiCad project directories, `.kicad_sch` files (project mode), or inventory `.csv` files (inventory mode).

**--inventory CATALOG_CSV**
: Inventory catalog for a coverage dry-run (project mode only).

**--supplier NAME**
: Search a distributor catalog to check supplier coverage for each component. Choices: `mouser`, `lcsc`, `generic`. Set `MOUSER_API_KEY` environment variable or use `--api-key`. May be combined with `--inventory` to also detect `INVENTORY_GAP` rows. In inventory mode (all positionals are `.csv` files), runs freshness checks (`STALE_PART`, `BETTER_AVAILABLE`) against each `ITEM` row.

**--api-key KEY**
: API key for the `--supplier` provider, overrides the provider-specific environment variable.

**--requirements REQ_CSV**
: Requirements CSV (output of `jbom inventory proj`) for a coverage check (inventory mode only).

**--datasheet-library LIBRARY_DIR**
: SPCoast-inventory checkout root (containing `datasheets/`) for datasheet document-library file-presence checks (inventory mode only; rejected in project mode). Enables `DATASHEET_FILE_MISSING` / `DATASHEET_ORPHAN_FILE` rows. The other datasheet-library hygiene checks (backlog, name/provenance lints, token normalization) always run in inventory mode regardless of this flag.

**--check-urls**
: Opt-in (default off; inventory mode only). Walks the Datasheet URL recovery ladder for every `ITEM` row and writes a full-sheet-paste CSV of proposed URL upgrades instead of the normal audit report. **Makes network requests** -- see ["Datasheet URL recovery ladder"](#datasheet-url-recovery-ladder---check-urls-opt-in-network) below. Mutually exclusive with `--inventory` and `--requirements`; rejected in project mode.

**-o, --output REPORT_CSV**
: Write the audit report to this file. If omitted, CSV is written to stdout.

**--strict**
: Treat `WARN`-severity rows as failures: exit code is 1 even if there are no `ERROR` rows.

**-v, --verbose**
: Include a `Debug` column in project-mode output with matcher/supplier diagnostics.

### report.csv schema

**Project mode (wide CURRENT/SUGGESTED couplets)**
: Output contains two rows per component (`RowType=CURRENT` and `RowType=SUGGESTED`).
: Identity/context columns include `ProjectPath`, `RefDes`, `UUID`, `Category`, `Value`, `Footprint`, `Package`, `Description`.
: Missing-field columns are emitted as:
  - `MISSING` (no deterministic heuristic value), or
  - `MISSING\n(value)` (deterministic heuristic/default candidate available).
: `Action` defaults:
  - `CURRENT` row: blank
  - `SUGGESTED` row: `SKIP/SET`
: `Notes` defaults:
  - `CURRENT` row: concise audit summary
  - `SUGGESTED` row: blank
: With `-v`, a `Debug` column is added.

**Inventory mode (stable tall schema)**
: Columns: `CheckType`, `Severity`, `ProjectPath`, `RefDes`, `UUID`, `CatalogFile`, `IPN`, `Category`, `Field`, `CurrentValue`, `SuggestedValue`, `ApprovedValue`, `Action`, `Supplier`, `SupplierPN`, `Description`.

### Exit codes

- `0` — no `ERROR`-severity rows (default)
- `1` — one or more `ERROR`-severity rows; or any `WARN`-severity rows when `--strict` is passed

`--check-urls` does not participate in the ERROR/WARN severity model above:
it exits `0` whenever the ladder ran to completion, regardless of how many
URLs came back `manual` (needs human/agent review) or `dead` (signed/
ephemeral, dead by design); it exits `1` only on a hard error (bad input
path, unreadable file, etc.). Per-URL outcomes are summarized on stderr
and reflected in the full-sheet-paste CSV -- see below.

### Datasheet URL recovery ladder (`--check-urls`, opt-in, NETWORK)

Mechanizes the five-rung LCSC URL recovery ladder discovered by the
SPCoast-inventory curation pass (jBOM#351;
`SPCoast-inventory docs/curation-pass-2026-07.md`). For every `ITEM` row
with a populated `Datasheet` URL:

1. **Direct fetch** -- the recorded URL is fetched and checked: a real PDF
   is left as-is; an HTML response (impostor) or fetch error continues to
   the next applicable rung.
2. **LCSC viewer -> CDN transform** -- `www.lcsc.com/datasheet/lcsc_datasheet_...`
   viewer-page URLs (HTML shells; not fetchable by curl) are mechanically
   rewritten to their durable `wmsc.lcsc.com` CDN path and re-fetched.
3. **LCSC product-detail API** -- bare LCSC C-number URLs are looked up via
   the product-detail API, which returns a durable
   `datasheet.lcsc.com/datasheet/pdf/<hash>.pdf` URL.
4. **Manufacturer/distributor retry** -- non-LCSC URLs that failed rung 1
   are retried once; if they still fail, they are reported for manual/agent
   review. **No mirror-guessing or web search is ever attempted** here --
   the curation pass found that locating a canonical mirror is a human/
   agent judgment call, not a mechanizable step, and this ladder never
   invents a URL.
5. **Signed/ephemeral URLs** (e.g. time-limited object-storage tokens) are
   detected up front by URL pattern and reported dead by design -- never
   fetched, never proposed as a recovery target.

**Convergence**: when multiple `ITEM` rows share a `Datasheet Name` but
disagree on `Datasheet` URL, the URL that resolves cleanly (rung 1) or was
mechanically recovered (rungs 2-3) is proposed as the canonical URL for
every disagreeing member. No canonical URL is invented if none of the
members resolve.

**Output**: a full-sheet-paste CSV -- every row from the input inventory,
in original order, with only the `Datasheet` cell rewritten where an
upgrade is proposed. Every other row and column passes through unchanged.
**This command never writes to the inventory file itself** -- a human
reviews the proposals and pastes the upgraded column back into the
spreadsheet by hand.

```sh
# Check Datasheet URLs and write proposed upgrades for human review
jbom audit catalog.csv --check-urls -o url_upgrades.csv
```

### Example workflow

```sh
# 1. Check field quality and inventory coverage for a project
jbom audit ./my_project --inventory catalog.csv -o report.csv
# 2. Review SUGGESTED rows, set Action=SET where you want to apply changes
jbom annotate ./my_project --repairs report.csv

# 3. Audit catalog coverage against project requirements
jbom inventory ./my_project -o requirements.csv
jbom audit catalog.csv --requirements requirements.csv -o catalog_report.csv

# 4. Audit the datasheet document library (offline hygiene + file presence)
jbom audit catalog.csv --datasheet-library ~/Dropbox/workspace/SPCoast-inventory -o datasheet_report.csv

# 5. Check Datasheet URLs and propose upgrades (opt-in, makes network requests)
jbom audit catalog.csv --check-urls -o url_upgrades.csv
```

## ANNOTATE COMMAND

```
jbom annotate INPUT [--repairs REPORT_CSV] [--normalize] [--dry-run]
```

Back-annotates KiCad schematics with approved field values from an audit report, and optionally normalizes schematic property formatting.

**INPUT** (required)
: Path to a KiCad project directory or `.kicad_sch` file.

**--repairs REPORT_CSV**
: Audit report CSV (output of `jbom audit`).
: Supports both:
  - project-mode wide couplets (`RowType=SUGGESTED`, `Action=SET` applies all non-metadata suggestion columns), and
  - legacy/inventory tall rows (`Field` + `ApprovedValue` with `Action=SET`).
: Rows with other `Action` values are skipped. `MISSING` placeholders are not written back. A row with `Action=SET` but no matching UUID is a hard failure.

**--normalize**
: Normalize schematic property formatting (canonical capitalization and field ordering). May be used standalone or combined with `--repairs`.

**--dry-run**
: Parse and validate the input without writing any files. Reports what would change.

### Exit codes

- `0` — annotation applied successfully (or nothing to do)
- `1` — one or more hard failures (UUID not found, file not writable, etc.)

### Example workflow

```sh
# Audit first; in project-mode report set SUGGESTED Action=SET for rows to apply
jbom audit ./my_project --inventory catalog.csv -o report.csv

# Apply approved changes back to schematic
jbom annotate ./my_project --repairs report.csv

# Preview without writing
jbom annotate ./my_project --repairs report.csv --dry-run

# Normalize property formatting only
jbom annotate ./my_project --normalize
```

## BOM COMMAND

```
jbom bom [PROJECT] [--inventory FILE ...] [-o OUTPUT] [OPTIONS]
```

Generates a Bill of Materials aggregated by value+package for procurement. Matches schematic components against an inventory file to produce fabrication-ready output.

**PROJECT** (optional, default: current directory)
: Path to a KiCad project directory, `.kicad_pro`, `.kicad_sch`, or a base name. The project directory must contain exactly one `*.kicad_pro` file. Hierarchical schematics are processed automatically when a project directory is given.

**--inventory FILE**
: Inventory file for BOM matching. Supported: .csv, .xlsx, .xls, .numbers. May be repeated to load from multiple sources: `--inventory project.csv --inventory jlc_export.xlsx`

**-o, --output OUTPUT**
: Output destination.
  - Omit `-o` to write `${project}.bom.csv` in the discovered project directory.
  - Use `-o console` for a formatted table.
  - Use `-o -` for CSV to stdout.
  - Otherwise, treat the value as a file path.

**-F, --force, --Force**
: Overwrite an existing output file.

**--fabricator NAME**
: PCB fabricator for field presets and part number lookup. Choices: `jlc`, `pcbway`, `seeed`, `generic`. Default: `generic`.

**--jlc / --pcbway / --seeed / --generic**
: Shorthand fabricator flags (equivalent to `--fabricator NAME`).

**-f, --fields FIELDS**
: Output columns. Use a preset with `+` prefix (`+standard`, `+jlc`, `+minimal`, `+all`, `+generic`, `+default`), a comma-separated field list, or both: `+jlc,CustomField`.
: When `-f/--fields` is given, jBOM checks the selection against the active fabricator's
  (or generic's) default preset and emits a `warning`-severity diagnostic on stderr if
  important fields (`fabricator_part_number`, `reference`, `quantity`, `value`) are
  missing, e.g. `Warning: Missing important generic fields: value`. This warning applies
  regardless of whether a fabricator was explicitly selected. Use `-q/--quiet` to
  suppress it; stdout CSV output is unaffected either way.

**--list-fields**
: List available fields and presets, then exit (no project needed).

**-v, --verbose**
: Include Match_Quality, Priority, and Notes columns in output.

## POS COMMAND

```
jbom pos [PROJECT] [-o OUTPUT] [OPTIONS]
```

Generates a component placement file (CPL/POS) from a KiCad PCB for pick-and-place assembly.

**PROJECT** (optional, default: current directory)
: Path to .kicad_pcb file, project directory, or base name. If a .kicad_sch file is given, jBOM looks for the matching .kicad_pcb.

**-o, --output OUTPUT**
: Output destination.
  - Omit `-o` to write `${project}.pos.csv` in the discovered project directory.
  - Use `-o console` for a formatted table.
  - Use `-o -` for CSV to stdout.
  - Otherwise, treat the value as a file path.

**-F, --force, --Force**
: Overwrite an existing output file.

**--fabricator NAME**
: Target fabricator for field preset selection. Choices: `jlc`, `pcbway`, `seeed`, `generic`.

**--jlc / --pcbway / --seeed / --generic**
: Shorthand fabricator flags.

**-f, --fields FIELDS**
: Column selection. Use a preset (`+jlc`, `+minimal`, `+standard`, `+all`) or a comma-separated list: `Reference,X,Y,Footprint,Side`.

**--list-fields**
: List available POS fields and presets, then exit.

**--smd-only**
: Include only SMD components. Filters out through-hole parts.

**--layer {TOP,BOTTOM}**
: Filter to components on the specified board side only.

**--units {mm}**
: Output coordinate units. Currently `mm` only.

**--origin {board,aux}**
: Coordinate origin. `board` = board lower-left corner; `aux` = auxiliary axis origin (falls back to board if not defined).

**-v, --verbose**
: Enable verbose diagnostic output.

## INVENTORY COMMAND

```
jbom inventory [PROJECT] [-o OUTPUT] [OPTIONS]
```

Generates an initial inventory template from schematic components. The output is a CSV with IPN, Category, Value, Package, and other fields partially filled, ready for manual editing or distributor enrichment.

**PROJECT** (optional, default: current directory)
: Path to .kicad_sch file, project directory, or base name. Accepts multiple paths for batch mode; multiple projects are merged with COMPONENT rows deduplicated on ComponentID.

**-o, --output OUTPUT**
: Output destination.
  - Omit `-o` to write `part-inventory.csv` in the current working directory.
  - Use `-o console` for a formatted table.
  - Use `-o -` for CSV to stdout.
  - Otherwise, treat the value as a file path.

**-F, --force, --Force**
: Overwrite an existing output file (also creates a timestamped backup if the file exists).

**--inventory FILE**
: Existing inventory file for merge operations. May be repeated.

**--filter-matches**
: When used with `--inventory`, exclude components that already match items in the existing inventory (show only new/unmatched components).

**--per-instance**
: Emit one inventory row per component instance with category sub-header rows. Useful for sparse-fix workflows where you want to review or edit each placement individually.

**--supplier SUPPLIER_ID**
: Auto-populate supplier part numbers during inventory generation. Repeat the flag to enrich from multiple suppliers in one run (for example: `--supplier lcsc --supplier mouser`).

**--api-key KEY**
: Supplier API key mapping input. Repeatable and validated against `--supplier`.
: Supported forms:
  - single unscoped key: `--api-key KEY` (backward-compatible default key)
  - supplier-scoped key: `--api-key SUPPLIER_ID=KEY` (repeat for each supplier)
  - ordered unscoped mapping: repeat unscoped keys and repeat `--supplier` with matching count; keys map by supplier argument order
: Invalid combinations fail fast (mixed scoped/unscoped values, count mismatches, or scoped supplier IDs not present in `--supplier`).

**--limit N**
: Maximum candidates applied per supplier per unmatched seed row (default: `1`). In multi-supplier mode, the limit is evaluated independently for each supplier pass.

**--stop-on-error**
: Abort batch processing on first project failure (default: continue and report).

**-v, --verbose**
: Show loading and processing diagnostics.

### Datasheet staging fetch (side effect)

When `--supplier` is given, every Item's Datasheet URL encountered during
enrichment (freshly populated by a supplier candidate, or already present on
the row) is fetched into a staging directory for later human review. This
rides the same always-on staging fetch as `jbom search` -- see that
command's "Datasheet staging fetch" note above for the full behavior
(idempotency, PDF/HTML verification, fetch budget, profile-based
configuration). Items that already have a `Datasheet Name` (already in the
Library) are skipped for free, without a network call.

### ADMIT SUBCOMMAND (`jbom inventory admit`)

```
jbom inventory admit [--inventory CATALOG_CSV ...] [--manifest PATH] [--staging-dir PATH] [--library-dir PATH]
jbom inventory admit --apply [--manifest PATH] [-o PASTE_CSV] [-F] [-v]
```

The sole gate into the datasheet document library (jBOM#356): a two-phase
**propose → human edit → apply** workflow. Datasheet documents never enter
the library any other way -- neither the staging fetch (`jbom search` /
`jbom inventory --supplier`, above) nor any other command writes into
`datasheets/`.

The staging directory comes exclusively from the
`datasheet_staging.staging_dir` profile key (see
[`configuration.md`](configuration.md#datasheet_staging-sub-stanza-jbom355)) --
the same user-machine binding the staging fetch uses. There is no fallback
path and no environment variable: when it is unconfigured, `admit` reports
an error and there is nothing to admit. `--staging-dir` overrides it for one
invocation; `--library-dir` overrides the library's `datasheets/` directory,
which otherwise defaults to a `datasheets` sibling of the staging directory
(i.e. `<staging_dir>/../datasheets`, matching the SPCoast-inventory layout).

#### Propose (default mode)

Scans the staging directory for verified PDFs (`.pdf`; `.unverified` files
are never proposed) and matches each one back to the inventory backlog --
rows with a populated `Datasheet` URL but no `Datasheet Name` yet, loaded
from `--inventory CATALOG_CSV` (repeatable, required for propose). Items
sharing one Datasheet URL (family members, e.g. several resistor rows
that only differ by tolerance/value) are grouped into a single manifest
candidate. Writes a manifest CSV (default `admit-manifest.csv` inside the
staging directory; override with `--manifest PATH`) with one row per
staged file:

| Column | Meaning |
| --- | --- |
| `Action` | `ADMIT` (accept) or `SKIP` (leave staged). Propose defaults this based on `Disposition`; edit it before `--apply`. |
| `ProposedName` | Curated `Datasheet Name` (no path, no extension) — the library filename stem. A best-effort heuristic derived from `Category`/`Manufacturer`/`MFGPN` (family candidates get a `-series` suffix). **Always review and correct before `--apply`.** |
| `Disposition` | `new` (fresh candidate, `Action=ADMIT`), `dupe-of` (byte-identical to an already-published document, `Action=ADMIT`, idempotent), `collision` (name already published under different content, `Action=SKIP` — resolve by hand), or `unresolvable` (no matching backlog row, `Action=SKIP`). |
| `DupeOf` | For `dupe-of` rows, the existing published name. |
| `StagedFile` | Filename of the verified PDF within the staging directory. |
| `SourceURL` | The Datasheet URL this file was staged from. |
| `MemberIPNs` | Semicolon-separated IPNs of every backlog Item sharing `SourceURL` — the Items this admission will name. |

**--inventory CATALOG_CSV**
: Inventory catalog(s) to resolve the backlog against. Required for propose mode; repeatable.

**--manifest PATH**
: Manifest CSV path. Written by propose; read by `--apply`. Default: `admit-manifest.csv` inside the staging directory.

**--staging-dir PATH**
: Override the configured staging directory for this invocation.

**--library-dir PATH**
: Override the library's `datasheets/` directory.

**-F, --force, --Force**
: Overwrite an existing manifest file.

#### Apply (`--apply`)

Reads the (human-edited) manifest and, for every `Action=ADMIT` row, moves
its staged PDF into `datasheets/<ProposedName>.pdf` and writes one
full-sheet `Datasheet Name` paste-file row (`IPN`, `Datasheet Name`) per
member IPN — ready for the human to paste into the canonical inventory at
the matching rows. jBOM never writes to the inventory itself (per the
human-sole-writer ruling); the paste-file is a proposal, not a write.
Output defaults to stdout CSV; use `-o PATH` for a file, or `-o console`
for a table.

**Never-rename guard**: before moving anything, each `ADMIT` row is checked
against the library. A `ProposedName` that collides (case-insensitively —
library filesystems are case-insensitive) with an already-published
document of *different* content is refused; a published document's name
and content are never silently overwritten or renamed. Re-admitting
byte-identical content under its own published name is a no-op, not a
violation. `ProposedName` is also validated as a bare filename stem —
path separators, `.`/`..` components, and absolute paths are refused
outright, so a manifest can never write outside `datasheets/`.

**Row-by-row commit semantics**: rows commit independently, in manifest
order. A row refused by either guard is skipped without affecting any
other row in the same `--apply` run — rows admitted earlier or later in
the same batch are never rolled back or blocked by one refused row. Refused
rows print an `Error:` line to stderr identifying the row and reason, and
the command exits `1` if any row was refused, even though other rows in
the same run succeeded.

**--apply**
: Switch to apply mode (reads `--manifest` instead of writing it).

**-o, --output PASTE_CSV**
: Paste-file output destination. Default: CSV to stdout. `-o console` prints a table; otherwise treat the value as a file path.

**-v, --verbose**
: Print one line per admitted/already-admitted row to stderr.

### Exit codes (admit)

- `0` — propose: manifest written (or nothing to propose); apply: every `ADMIT` row processed without a guard refusal.
- `1` — propose: no staging directory configured, missing/invalid `--inventory`, or manifest already exists without `--force`; apply: manifest not found, or one or more rows refused by a guard.

### Example workflow

```sh
# 1. Propose: scan staging, write a manifest for review
jbom inventory admit --inventory library.csv --manifest admit-manifest.csv

# 2. Edit admit-manifest.csv by hand: correct ProposedName, set Action=ADMIT/SKIP

# 3. Apply: move accepted PDFs into datasheets/, write the paste-file proposal
jbom inventory admit --apply --manifest admit-manifest.csv -o datasheet-names.csv

# 4. Paste datasheet-names.csv's Datasheet Name column into library.csv by hand
```

## PROMOTE COMMAND

```
jbom promote SOURCE_INVENTORY [-o OUTPUT] [OPTIONS]
```

Converts a supplier-export CSV into canonical jBOM inventory rows. The workflow
is a small pipeline:

1. A source-export *adapter* normalises each row from a known supplier shape
   (for example JLCPCB private parts export) into a canonical seed (SPN, MFGPN,
   manufacturer, description, package, category hint, plus traceability extras).
2. A pure *description parser* extracts EM fields from the description text and
   identity hints: Category, Value, Package, Tolerance, Type (MLCC dielectric),
   V/A/W ratings, Wavelength/mcd/Angle for LEDs, and typed Resistance /
   Capacitance / Inductance.
3. An *identity policy* derives a deterministic `IPN` for supported categories
   (passives + LEDs today) from the parsed identity.
4. When the user selects an explicit supplier context (`--supplier <id>` or
   `--jlc`), a *supplier enrichment* step calls the supplier provider's
   deterministic MPN lookup first, with a keyword search fallback, to fill in
   `Manufacturer`, `MFGPN`, `Datasheet`, and `SPN`.  Without an explicit
   supplier flag, the implicit `generic` context carries no catalog and no
   enrichment is attempted.
5. The result is written as canonical inventory columns first, followed by any
   supplemental source columns (qty, pricing) preserved verbatim for traceability.

**SOURCE_INVENTORY** (required)
: Path to the supplier-export CSV to promote.

**--supplier SUPPLIER_ID**
: Supplier context for promotion. Repeat is accepted and is shape-compatible with
  `jbom inventory` supplier semantics.

**--jlc**
: Shortcut for `--supplier lcsc`.

**--api-key KEY_OR_SUPPLIER_KEY**
: Optional API key argument, parsed with the same shape rules as `jbom inventory`:
  - `--api-key KEY`
  - `--api-key SUPPLIER_ID=KEY`

**-o, --output OUTPUT**
: Output destination.
  - Omit `-o` to write `<input>.promoted.csv` next to the source file.
  - Use `-o console` or `-o -` for CSV to stdout.
  - Otherwise, treat the value as a file path.

**-F, --force, --Force**
: Overwrite an existing output file.

**-v, --verbose**
: Print per-row parse provenance and enrichment outcomes to stderr.

### Design intent

`jbom promote` shares supplier-selection and API-key mapping semantics with
`jbom inventory` so promotion and inventory-enrichment workflows are
interchangeable at the CLI contract level. The canonical-output schema is the
same inventory column shape consumed by downstream `jbom bom`, `jbom audit`,
and `jbom annotate` workflows.

### Exit codes

- `0` — success
- `1` — error

## PARTS COMMAND

```
jbom parts [PROJECT] [-o OUTPUT] [OPTIONS]
```

Generates an electro-mechanically aggregated parts list from schematics. `parts` groups by value/package/type/tolerance/voltage/dielectric and emits a `Refs` column containing collapsed reference designators. Unlike `bom`, this aggregation excludes supply-chain fields and does not require an inventory file.

**PROJECT** (optional, default: current directory)
: Path to .kicad_sch file, project directory, or base name.

**-o, --output OUTPUT**
: Output destination.
  - Omit `-o` to write `${project}.parts.csv` in the discovered project directory.
  - Use `-o console` for a formatted table.
  - Use `-o -` for CSV to stdout.
  - Otherwise, treat the value as a file path.

**-F, --force, --Force**
: Overwrite an existing output file.

**--inventory FILE**
: Optional. Enhance the parts list with inventory data.

**--fabricator NAME**
: Fabricator for field presets. Choices: `jlc`, `pcbway`, `seeed`, `generic`.

**--jlc / --pcbway / --seeed / --generic**
: Shorthand fabricator flags.

**-v, --verbose**
: Verbose output.

## SEARCH COMMAND

```
jbom search QUERY [OPTIONS]
```

Searches distributor catalogs for parts matching a keyword or part number.

**QUERY**
: Search query (keyword, part number, description). Required.

**--supplier ID**
: Supplier ID to search (choices derived from installed supplier profiles; common values: `lcsc`, `mouser`). Set `MOUSER_API_KEY` environment variable or use `--api-key` for suppliers that require a key.

**--limit N**
: Maximum results to display (default: 10).

**--api-key KEY**
: API key, overrides provider-specific environment variables.

**--all**
: Disable default filters. Shows out-of-stock and obsolete results.

**--no-parametric**
: Disable smart parametric filtering derived from the query text.

**--no-cache**
: Disable the persistent disk cache for this run.

**--clear-cache**
: Delete cached results for this supplier before running.

**--fields LIST**
: Comma-separated list of output field *registry keys* (applies to console + CSV output). Use `--list-fields` to discover valid keys.

**--list-fields**
: Print available field keys alongside their display names, then exit. Does not require an API key.

**-o, --output OUTPUT**
: Output destination. Default: `console` (formatted table).
  - Use `-o console` (or omit `-o`) for a formatted table.
  - Use `-o -` for CSV to stdout.
  - Otherwise, treat the value as a file path.

**--inventory CATALOG_CSV**
: Optional. Cross-reference results against an existing inventory catalog so
  already-admitted Datasheet documents (rows with a populated `Datasheet
  Name`) are never re-staged by the datasheet staging fetch (see below).

**-F, --force, --Force**
: Overwrite an existing output file.

### Datasheet staging fetch (side effect, opt-in per machine)

Whenever a search result carries a Datasheet URL, `jbom search` fetches it
into a staging directory for later human review, in addition to printing
results (jBOM#355). This is **inert by default**: `staging_dir` is a
user-machine binding (it names a local SPCoast-inventory checkout) that the
shipped profile never sets, so nothing changes for any invocation until you
configure it once in your own `~/.jbom/common.jbom.yaml` -- see
[`configuration.md`](configuration.md#datasheet_staging-sub-stanza-jbom355).
Once configured:

- Downloads land with a `.unverified` suffix until a `file(1)`-style content
  check confirms the payload is a real PDF; verified files get a plain
  `.pdf` suffix. HTML responses (a common supplier-side "document not
  found" placeholder) stay flagged `.unverified` and print a warning to
  stderr; they are never admitted automatically.
- Idempotent: a URL already staged (verified or flagged) is never re-fetched.
  When `--inventory` is given, a URL already admitted (`Datasheet Name`
  populated on a matching row) is also skipped.
- Bounded: one invocation attempts at most `datasheet_staging.max_fetches_per_run`
  real fetches (shipped default 20) within `fetch_time_budget_seconds`
  (shipped default 30). Once either limit is hit, remaining URLs are
  skipped with a one-line stderr summary; the command still succeeds.
- Never fails the command: fetch errors are reported as stderr warnings only.

`jbom inventory --supplier` has the identical side effect for every Item's
Datasheet URL encountered during supplier enrichment (see the INVENTORY
COMMAND section above); it does not need `--inventory` for admitted-skip
since it already operates on inventory Items directly.

## GERBERS COMMAND

```
jbom gerbers [PROJECT] [-o OUTPUT_DIR] [OPTIONS]
```

Generates Gerber, drill, and optionally IPC-D-356 netlist files from a KiCad PCB file using
`kicad-cli`.  When `kicad-cli` is not installed, generation is skipped and a diagnostic is
emitted — BOM and POS generation are unaffected.

Layer selection, drill splitting, and drill map format are read from the fabricator's
`gerbers:` config stanza when a fabricator is specified.

**PROJECT** (optional, default: current directory)
: Path to a KiCad project directory, `.kicad_pcb`, `.kicad_pro`, or `.kicad_sch` file.

**-o, --output-dir OUTPUT_DIR**
: Directory where Gerber and drill files are written. Default: `<project_dir>/gerbers/`.

**--fabricator NAME**
: Fabricator profile for layer selection and Gerber options. Default: `generic`.

**--jlc / --pcbway / --seeed / --generic**
: Shorthand fabricator flags.

**--no-drill**
: Skip drill file generation.

**--netlist**
: Also generate an IPC-D-356 netlist file (`netlist.ipc`).

**--dry-run**
: Validate inputs without generating any files.

**-v, --verbose**
: Verbose output.

### Exit codes

- `0` — success (or graceful skip with diagnostic when kicad-cli absent)
- `1` — error

## FAB COMMAND

```
jbom fab [PROJECT] [-o OUTPUT_ROOT] [OPTIONS]
```

One-shot fabrication: generates BOM, placement, and Gerber files for a KiCad project and
organizes them into a `production/` folder ready for upload to a PCB fabricator.

Equivalent to running `jbom bom`, `jbom pos`, and `jbom gerbers` in sequence with the same
fabricator profile, then packaging results and creating a dated backup archive.

**Output structure**:
```
production/
  jbom.csv                           ← BOM (fabricator-ready)
  cpl.csv                            ← CPL/placement
  {title}_{revision}.zip             ← Gerber archive for fab upload
  backups/
    {title}_{revision}_{timestamp}.zip   ← dated snapshot containing
                                            jbom.csv, cpl.csv, gerber zip,
                                            and {project}-design-sources.zip
```
`{title}` and `{revision}` are read from the KiCad title block; absent title falls back
to the `.kicad_pro` basename.

**PROJECT** (optional, default: current directory)
: Path to a KiCad project directory, `.kicad_pro`, `.kicad_pcb`, or `.kicad_sch` file.

**-o, --output-dir OUTPUT_ROOT**
: Parent directory for the `production/` folder. Default: project directory.

**--fabricator NAME** / **--jlc** / **--pcbway** / **--seeed** / **--generic**
: Fabricator profile. Controls field presets for BOM and POS, and Gerber layer configuration.
  Default: `generic`.

**--skip-bom**
: Skip BOM generation.

**--skip-pos**
: Skip placement (CPL) generation.

**--skip-gerbers**
: Skip Gerber generation and packaging.

**--inventory FILE**
: Inventory CSV for BOM enhancement (repeatable).

**--smd-only**
: Include only SMD components in placement output.

**--layer {TOP,BOTTOM}**
: Filter placement to the specified board side.

**--origin {board,aux}**
: Coordinate origin for placement output. Default: `board`.

**--netlist**
: Also generate an IPC-D-356 netlist during the Gerber step.

**--debug**
: Preserve the intermediate gerber directory after packaging (useful for inspection).

**--dry-run**
: Generate BOM/POS data but skip all file writes and Gerber generation.

**-v, --verbose**
: Verbose output.

### Exit codes

- `0` — success
- `1` — error

### Example

```bash
# Full fabrication run for JLCPCB
jbom fab MyProject/ --jlc --inventory inventory.csv
# Output: MyProject/production/jbom.csv, cpl.csv, MyProject_1.0.zip, backups/...

# Skip Gerbers (BOM and CPL only)
jbom fab MyProject/ --jlc --inventory inventory.csv --skip-gerbers

# Dry run — check what would be generated
jbom fab MyProject/ --jlc --dry-run
```

## INVENTORY-SEARCH COMMAND (RETIRED)

The `inventory-search` subcommand was retired in release 154. Its catalog-search
functionality has been consolidated into `jbom audit --supplier` (batch coverage and
freshness checks) and `jbom inventory --supplier` (one-pass enrichment during
inventory generation).

**Migration**: replace old `jbom inventory-search ...` usage with:

```sh
# Supplier freshness check against an inventory CSV
jbom audit catalog.csv --supplier lcsc -o report.csv

# Auto-populate supplier PNs while generating an inventory template
jbom inventory ./my_project --supplier lcsc -o inventory.csv
```

## OUTPUT

**BOM CSV**
: Default name `${ProjectName}.bom.csv` (written in the project directory when `-o` is omitted). Aggregated by value+package. Columns depend on `-f` and fabricator preset.

**POS CSV**
: Default name `${ProjectName}.pos.csv` (written in the project directory when `-o` is omitted). One row per component. Coordinates in mm.

**Inventory CSV**
: Defaults to console output when `-o` is omitted. Use `-o <file>` to write a CSV template with IPN, Category, Value, Package, and related columns.

**Promoted CSV**
: Default name `<input>.promoted.csv` (written next to the source file when `-o` is omitted). Canonical inventory columns are written first (`RowType`, `IPN`, `Category`, `Value`, `Package`, `Description`, `Manufacturer`, `MFGPN`, `Supplier`, `SPN`, `Datasheet`, typed EM fields, etc.) with `SupplierContext` carrying the resolved supplier label.  Supplemental source columns from the export (qty, pricing, etc.) are preserved after the canonical block for traceability.

**Parts CSV**
: Default name `${ProjectName}.parts.csv` (written in the project directory when `-o` is omitted). One row per electro-mechanical group with a `Refs` column of collapsed references. Use `-o -` for CSV to stdout.
: DNP rows are included in the default row set. Add `-f dnp` when an explicit DNP marker column is required.

**Exit Codes**
: 0 — success
: 1 — error (file not found, invalid option, etc.)
: 2 — warning (one or more BOM components unmatched; BOM was still written)

## COMPONENT ATTRIBUTE HANDLING

KiCad footprints and schematic symbols carry three flag attributes that control how components
flow through jBOM's three output commands. These flags are fixed at generation time — no CLI
flags override them.

| Attribute | `jbom bom` / `jbom parts` | `jbom pos` | Notes |
|---|---|---|---|
| `exclude_from_board` | not in output | not in output | Symbol-only: no PCB footprint |
| `exclude_from_bom` | not in output | not in output | Board feature: logo, mounting hole, fiducial |
| `dnp` (Do Not Populate) | included (see command notes below) | not in output | Variant/rework spares: pad present, part absent |
| *(none set)* | included | included | Normal populated component |

**BOM**: `exclude_from_bom` components (mounting holes, fiducials, OSHW logos) are always
excluded. DNP components are always included and identified by the `DNP` column value `"DNP"`
(empty string for populated components). This follows IPC J-STD-001: assembly operators must
be able to distinguish intentionally empty pads from omitted line items.

**Parts**: DNP components are always included in the output row set. The default parts projection
does not include a dedicated `DNP` column; include one explicitly via `-f dnp` (or a custom
projection that includes `dnp`) when a marker column is required.

**POS**: DNP components are always excluded. The P&P machine's input contract is strictly
"place these components"; the companion BOM is the authoritative source for DNP declarations.

**Full-board audit**: To enumerate every component regardless of flag — including
`exclude_from_bom` refs, virtual symbols, and all DNP/non-DNP — use `jbom audit`.

**Migration note** (from pre-v8.x): The `--include-dnp`, `--include-excluded`, and
`--include-all` flags have been removed from `jbom bom`, `jbom parts`, and `jbom pos`.
DNP rows now appear in BOM output by default, marked in the `DNP` column.
Parts output includes DNP rows by default; add `-f dnp` to expose an explicit marker column.
Procurement workflows that previously excluded DNP rows should filter on the `DNP` column:

```bash
# Extract only populated (non-DNP) components from the BOM:
awk -F, 'NR==1 || $NF != "DNP"' project.bom.csv > populated.bom.csv
```

## BOM DESIGNATOR CASE POLICY

Designators (reference designators like R1, C2, U3) are preserved exactly as written in the `.kicad_pcb` file.
KiCad allows mixed-case designators by design (e.g., `U$1`, `License1`, `MountingHole1`, `IO_SEL`, `gnd0`).
jBOM does not normalize case.

**Comparison with other tools**: Some tools (e.g., Fabrication-Toolkit) uppercase all designators at read time
(so `License1` becomes `LICENSE1`). jBOM preserves the user's choice of case, which is less surprising and
respects intentional styling.

**If you need uppercase output**: You can post-process the CSV downstream. For example:

```bash
awk -F, 'NR==1{print; next}{ $1=toupper($1) }1' bom.csv > bom_uppercase.csv
```

## FOOTPRINT COLUMN

`jbom bom` reports the canonical PCB FPID for each component: the literal identifier from
the `(footprint "Lib:Name" ...)` form in the `.kicad_pcb` file. That value is the
authoritative record of what was fabricated on the board.

The FPID may differ from:
- the schematic symbol's `Footprint` property,
- Fabrication-Toolkit's BOM footprint column (it resolves schematic-side names through
  KiCad's library system), or
- project-internal library aliases.

In all cases, the PCB FPID wins because the FPID is what was fabricated. If you want a
different identifier to appear in the BOM, change it on the PCB (for example via KiCad's
**Update PCB from Schematic** with **Update attribute content** enabled) and re-run
`jbom bom`.

## BOM FIELD PRESETS

Use `-f "+PRESET"` or shorthand fabricator flags (`--jlc`, etc.) to imply a preset.

**+default**
: Reference, Quantity, Description, Value, Footprint, Manufacturer, MFGPN, Fabricator, Fabricator Part Number, Datasheet, SMD, DNP. Alias: `+standard`.

**+jlc**
: Reference, Quantity, Value, Description, LCSC/Fabricator Part Number, SMD, DNP. JLCPCB column order. Enabled by `--jlc`.

**+pcbway**
: PCBWay-compatible column set including DNP marker column. Enabled by `--pcbway`.

**+seeed**
: Seeed Studio Fusion PCBA column set including DNP marker column. Enabled by `--seeed`.

**+generic**
: Reference, Quantity, Description, Value, Package, Footprint, Manufacturer, Part Number, DNP. Enabled by `--generic`.

**+minimal**
: Reference, Quantity, Value, LCSC. Bare minimum for quick exports.

**+all**
: Every available field from schematic and inventory, sorted alphabetically.

## EXAMPLES

Generate BOM with JLCPCB columns:
```
jbom bom MyProject/ --inventory inventory.csv --jlc
```

BOM from multiple inventory sources:
```
jbom bom MyProject/ --inventory local.csv --inventory jlc_export.xlsx
```

BOM with custom fields:
```
jbom bom MyProject/ --inventory inventory.csv -f "+jlc,CustomField"
```

BOM with verbose match scoring:
```
jbom bom MyProject/ --inventory inventory.csv -v
```

List available BOM fields:
```
jbom bom --list-fields --jlc
```

POS for JLCPCB (auto-detect PCB in project directory):
```
jbom pos MyProject/ --jlc
```

POS SMD-only, top side only:
```
jbom pos MyProject/ --smd-only --layer TOP
```

POS with custom field list:
```
jbom pos MyBoard.kicad_pcb -o placement.csv -f "Reference,X,Y,Footprint,Side"
```

Generate inventory template:
```
jbom inventory MyProject/ -o my_inventory.csv
```

Generate inventory with one-pass multi-supplier enrichment:
```
jbom inventory MyProject/ --supplier lcsc --supplier mouser --limit 2 -o inventory.csv
```

Generate inventory with explicit per-supplier API keys:
```
jbom inventory MyProject/ --supplier lcsc --supplier mouser --api-key lcsc=KEY_LCSC --api-key mouser=KEY_MOUSER -o inventory.csv
```

Generate inventory with repeated unscoped API keys mapped by supplier argument order:
```
jbom inventory MyProject/ --supplier lcsc --supplier mouser --api-key KEY_LCSC --api-key KEY_MOUSER -o inventory.csv
```

Promote a supplier export and stamp explicit supplier context:
```
jbom promote examples/JLCPCB-INVENTORY.csv --supplier lcsc -o examples/JLCPCB-INVENTORY.promoted.csv
```

Promote with shorthand supplier context and scoped API key:
```
jbom promote examples/JLCPCB-INVENTORY.csv --jlc --api-key lcsc=KEY123 -o -
```

Show only components not yet in an existing inventory:
```
jbom inventory MyProject/ --inventory existing.csv --filter-matches -o new_parts.csv
```

Per-instance inventory (one row per placement):
```
jbom inventory MyProject/ --per-instance -o instances.csv
```

Parts list (electro-mechanical groups with collapsed Refs):
```
jbom parts MyProject/ -o parts.csv
```

Search LCSC for a part:
```
jbom search "10k 0603 resistor" --supplier lcsc --limit 5
```

Search with cache bypass:
```
jbom search "100nF 0402" --supplier lcsc --no-cache
```

Audit with supplier coverage check:
```sh
export MOUSER_API_KEY=your_api_key
jbom audit ./my_project --inventory catalog.csv --supplier mouser -o report.csv
```

Apply approved field changes back to schematic:
```sh
jbom annotate ./my_project --repairs report.csv
```

Normalize schematic properties:
```sh
jbom annotate ./my_project --normalize
```

## FIELDS

Use `--list-fields` to see the complete list. Common fields include:

**Standard BOM fields**
: Reference, Quantity, Description, Value, Footprint, LCSC, Datasheet, SMD, Priority, Match_Quality, Fabricator, Fabricator_Part_Number

**Inventory fields** (prefix with `I:` to disambiguate from component properties)
: Category, Package, Manufacturer, MFGPN, Tolerance, Voltage, Current, Power, mcd, Wavelength, Angle, Frequency, Stability, Load, Family, Type, Pitch, Form

**Component properties** (prefix with `C:`)
: Tolerance, Voltage, Current, Power, and component-specific properties from the schematic.

## CASE-INSENSITIVE FIELD NAMES

Field names in the `-f` argument and column names in inventory files accept flexible formatting:

**Accepted formats** (all equivalent):
- Snake_case: `match_quality`, `i:package`, `c:tolerance`
- Title Case: `Match Quality`, `I:Package`, `C:Tolerance`
- UPPERCASE: `MATCH_QUALITY`, `I:PACKAGE`, `C:TOLERANCE`
- Mixed: `MatchQuality`, `Match-Quality`
- Spaced: `Match Quality` (spaces converted to underscores)

All formats are normalized internally. CSV headers in output always use Title Case for readability.

Example (all equivalent):
```bash
jbom bom project --inventory inv.csv -f "Reference,Match Quality,I:PACKAGE"
jbom bom project --inventory inv.csv -f "reference,match_quality,i:package"
jbom bom project --inventory inv.csv -f "REFERENCE,MATCH_QUALITY,I:PACKAGE"
```

## INVENTORY FILE FORMAT

Required columns:
: RowType, ComponentID, Category, Value, Package
: Plus `IPN` for ITEM rows

Optional columns:
: Manufacturer, MFGPN, Datasheet, Keywords, SMD, Tolerance, Voltage, Current, Power, Type, Form, Frequency, Stability, Load, Family, mcd, Wavelength, Angle, Pitch

Legacy aliases accepted:
: V/Volts -> Voltage, A/Amperage -> Current, W/Wattage -> Power

**Priority** uses integer ranking (1 = preferred, higher = less preferred). When multiple parts match, the lowest Priority is selected.

See [`design/inventory-field-semantics.md`](../design/inventory-field-semantics.md) for
the two-state value model, annotate write-back rules, and per-instance sub-header format.

## TROUBLESHOOTING

**No schematic files found**
: Ensure the project directory contains `.kicad_sch` files or pass the schematic path directly.

**"Unsupported inventory file format"**
: Check file extension (.csv, .xlsx, .xls, .numbers) and install optional packages if needed:
: `pip install openpyxl numbers-parser`

**Components not matching**
: Run with `-v` to see Match_Quality and Notes columns. Check that inventory Category, Package, and Value fields match component attributes.

**Import errors for Excel/Numbers**
: Install: `pip install openpyxl` (for .xlsx, .xls) or `pip install numbers-parser` (for .numbers).

**Search commands require API key**
: Set `MOUSER_API_KEY` environment variable or pass `--api-key KEY`.

## RELATED

- [LCSC/JLCPCB provider](lcsc-provider.md) — how jBOM queries the JLCPCB parts catalog
- [KiCad best practices](kicad-best-practices.md) — schematic conventions that improve BOM match quality
- [Inventory field semantics](../design/inventory-field-semantics.md) — two-state value model, annotate write-back rules
- [ADR 0001: Fabricator inventory selection vs matcher](../architecture/adr/0001-fabricator-inventory-selection-vs-matcher.md) — why the BOM workflow is supplier-neutral
