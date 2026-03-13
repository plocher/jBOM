# jbom(1) — jBOM CLI Reference

## NAME

jbom — generate Bill of Materials, Placement Files, and Parts Lists from KiCad projects

## SYNOPSIS

```
jbom [-q] [--version]
jbom audit PATH [PATH ...] [--inventory CATALOG_CSV] [--supplier NAME] [--api-key KEY] [--requirements REQ_CSV] [-o REPORT_CSV] [--strict] [-v]
jbom annotate INPUT [--repairs REPORT_CSV] [--normalize] [--dry-run]
jbom bom [PROJECT] [--inventory FILE ...] [-o OUTPUT] [BOM OPTIONS]
jbom pos [PROJECT] [-o OUTPUT] [POS OPTIONS]
jbom inventory [PROJECT] [-o OUTPUT] [INVENTORY OPTIONS]
jbom parts [PROJECT] [-o OUTPUT] [PARTS OPTIONS]
jbom search QUERY [SEARCH OPTIONS]
```

## DESCRIPTION

jBOM provides eight subcommands:

- `audit` — diagnose field-quality issues and inventory coverage gaps in KiCad projects or catalog files
- `annotate` — back-annotate KiCad schematics with approved field values from an audit report
- `bom` — generate a procurement BOM from KiCad schematics matched against an inventory file
- `pos` — generate component placement files (CPL/POS) from KiCad PCB files
- `inventory` — generate an initial inventory template from schematic components
- `parts` — generate an unaggregated parts list (one row per component) from schematics
- `search` — search external distributor catalogs (e.g. Mouser) by keyword or part number

The BOM workflow keeps designs supplier-neutral: components carry generic values in the schematic; an inventory file maps those values to specific supplier part numbers at generation time.

## GLOBAL OPTIONS

**-q, --quiet**
: Suppress informational guidance messages (diagnostics). Errors are still emitted.

**--version**
: Print jBOM version and exit.

## AUDIT COMMAND

```
jbom audit PATH [PATH ...]  [--inventory CATALOG_CSV]  [--supplier NAME] [--api-key KEY]  [-o REPORT_CSV]  [--strict] [-v]
jbom audit CAT.CSV [...]    [--requirements REQ_CSV]   [--supplier NAME] [--api-key KEY]  [-o REPORT_CSV]  [--strict] [-v]
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

**-o, --output REPORT_CSV**
: Write the audit report to this file. If omitted, CSV is written to stdout.

**--strict**
: Treat `WARN`-severity rows as failures: exit code is 1 even if there are no `ERROR` rows.
**-v, --verbose**
: Include a `Debug` column in project-mode output with matcher/supplier diagnostics.
### report.csv schema (stable)

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

### Example workflow

```sh
# 1. Check field quality and inventory coverage for a project
jbom audit ./my_project --inventory catalog.csv -o report.csv
# 2. Review SUGGESTED rows, set Action=SET where you want to apply changes
# 2. Review QUALITY_ISSUE rows, fill ApprovedValue + Action, then annotate
jbom annotate ./my_project --repairs report.csv

# 3. Audit catalog coverage against project requirements
jbom inventory ./my_project -o requirements.csv
jbom audit catalog.csv --requirements requirements.csv -o catalog_report.csv
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

**--list-fields**
: List available fields and presets, then exit (no project needed).

**--include-dnp**
: Include "Do Not Populate" components (excluded by default).

**--include-excluded**
: Include components marked "Exclude from BOM" (excluded by default).

**--include-all**
: Include all components: DNP, excluded from BOM, and virtual symbols.

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

**--include-dnp**
: Include DNP components in the placement file (excluded by default since they are not assembled).

**-v, --verbose**
: Enable verbose diagnostic output.

## INVENTORY COMMAND

```
jbom inventory [PROJECT] [-o OUTPUT] [OPTIONS]
```

Generates an initial inventory template from schematic components. The output is a CSV with IPN, Category, Value, Package, and other fields partially filled, ready for manual editing or distributor enrichment.

**PROJECT** (optional, default: current directory)
: Path to .kicad_sch file, project directory, or base name.

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


**-v, --verbose**
: Show loading and processing diagnostics.

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

**--include-dnp**
: Include DNP components (excluded by default).

**--include-excluded**
: Include BOM-excluded components (excluded by default).

**--include-all**
: Include all components: DNP, excluded, and virtual symbols.

**-v, --verbose**
: Verbose output.

## SEARCH COMMAND

```
jbom search QUERY [OPTIONS]
```

Searches distributor catalogs for parts matching a keyword or part number.

**QUERY**
: Search query (keyword, part number, description). Required.

**--supplier {mouser}**
: Supplier ID to search (default: mouser). Set `MOUSER_API_KEY` environment variable or use `--api-key`.

**--limit N**
: Maximum results to display (default: 10).

**--api-key KEY**
: API key, overrides provider-specific environment variables.

**--all**
: Disable default filters. Shows out-of-stock and obsolete results.

**--no-parametric**
: Disable smart parametric filtering derived from the query text.

**--fields LIST**
: Comma-separated list of output field *registry keys* (applies to console + CSV output). Use `--list-fields` to discover valid keys.

**--list-fields**
: Print available field keys alongside their display names, then exit. Does not require an API key.

**-o, --output OUTPUT**
: Output destination. Default: `console` (formatted table).
  - Use `-o console` (or omit `-o`) for a formatted table.
  - Use `-o -` for CSV to stdout.
  - Otherwise, treat the value as a file path.

**-F, --force, --Force**
: Overwrite an existing output file.

## INVENTORY-SEARCH COMMAND (RETIRED)

The `inventory-search` subcommand has been retired as of this release. Its catalog-search functionality has been consolidated into `jbom audit --supplier`.

**Migration**: replace old `jbom inventory-search ...` usage with:

```sh
jbom audit ./my_project --supplier mouser --api-key YOUR_KEY -o report.csv
```

## OUTPUT

**BOM CSV**
: Default name `${ProjectName}.bom.csv` (written in the project directory when `-o` is omitted). Aggregated by value+package. Columns depend on `-f` and fabricator preset.

**POS CSV**
: Default name `${ProjectName}.pos.csv` (written in the project directory when `-o` is omitted). One row per component. Coordinates in mm.

**Inventory CSV**
: Default name `part-inventory.csv` (written in the current working directory when `-o` is omitted). Template with IPN, Category, Value, Package, and related columns.

**Parts CSV**
: Default name `${ProjectName}.parts.csv` (written in the project directory when `-o` is omitted). One row per electro-mechanical group with a `Refs` column of collapsed references. Use `-o -` for CSV to stdout.

**Exit Codes**
: 0 — success
: 1 — error (file not found, invalid option, etc.)
: 2 — warning (one or more BOM components unmatched; BOM was still written)

## BOM FIELD PRESETS

Use `-f "+PRESET"` or shorthand fabricator flags (`--jlc`, etc.) to imply a preset.

**+default**
: Reference, Quantity, Description, Value, Footprint, Manufacturer, MFGPN, Fabricator, Fabricator Part Number, Datasheet, SMD. Alias: `+standard`.

**+jlc**
: Reference, Quantity, Value, Description, LCSC/Fabricator Part Number, SMD. JLCPCB column order. Enabled by `--jlc`.

**+pcbway**
: PCBWay-compatible column set. Enabled by `--pcbway`.

**+seeed**
: Seeed Studio Fusion PCBA column set. Enabled by `--seeed`.

**+generic**
: Reference, Quantity, Description, Value, Package, Footprint, Manufacturer, Part Number. Enabled by `--generic`.

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

Show only components not yet in an existing inventory:
```
jbom inventory MyProject/ --inventory existing.csv --filter-matches -o new_parts.csv
```

Parts list (electro-mechanical groups with collapsed Refs):
```
jbom parts MyProject/ -o parts.csv
```

Search Mouser for a part:
```
jbom search "10k 0603 resistor" --limit 5
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

Detailed inventory file format documentation is in [inventory(5)](README.man5.md).

Required columns:
: RowType, ComponentID, Category, Value, Package
: Plus `IPN` for ITEM rows

Optional columns:
: Manufacturer, MFGPN, Datasheet, Keywords, SMD, Tolerance, Voltage, Current, Power, Type, Form, Frequency, Stability, Load, Family, mcd, Wavelength, Angle, Pitch

Legacy aliases accepted:
: V/Volts -> Voltage, A/Amperage -> Current, W/Wattage -> Power

**Priority** uses integer ranking (1 = preferred, higher = less preferred). When multiple parts match, the lowest Priority is selected.

See [README.man5.md](README.man5.md) for complete column definitions and examples.

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

## SEE ALSO

- [**README.md**](../README.md) — Overview and quick start
- [**README.man3.md**](README.man3.md) — Python library API (planned for v8.x)
- [**README.man4.md**](README.man4.md) — KiCad Eeschema plugin integration
- [**README.man5.md**](README.man5.md) — Inventory file format
- [**README.developer.md**](README.developer.md) — Architecture and internals
