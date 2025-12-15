# jbom(1) — jBOM CLI (BOM and POS)

## NAME

jbom — generate Bill of Materials (BOM) and Component Placement (CPL/POS)

## SYNOPSIS

```
python -m jbom bom PROJECT -i INVENTORY [-o OUTPUT] [BOM OPTIONS]
python -m jbom pos PROJECT [-o OUTPUT] [POS OPTIONS]
```

## DESCRIPTION

jBOM provides two subcommands:
- `bom` — generate a BOM from KiCad schematics by matching components against an inventory file
- `pos` — generate component placement (CPL/POS) from KiCad PCB files for manufacturing

The BOM flow keeps designs supplier-neutral by matching at generation time rather than hardcoding part numbers in schematics.

## BOM ARGUMENTS

**PROJECT**
: KiCad project directory or a specific .kicad_sch file. If a directory is given, jBOM auto-detects the root schematic and processes hierarchical sheets.

**-i, --inventory FILE**
: Inventory file (required). Supported: .csv, .xlsx, .xls, .numbers

## BOM OPTIONS

**--jlc**
Imply `+jlc` field preset (prepends `+jlc` to `-f` if provided, or uses it by default when `-f` is omitted).

**-o, --output FILE**
Output CSV file path. If omitted, generates `<PROJECT>_bom.csv` in the project directory. Special values: `-`, `console`, `stdout` for terminal output.

**--outdir DIR**
Directory for output files when `-o` is not specified. Useful for redirecting BOMs to a separate folder.

**-v, --verbose**
Include Match_Quality and Priority columns. Shows detailed scoring information.

**-d, --debug**
Emit detailed matching diagnostics to stderr. Helpful for troubleshooting missing or mismatched components.

**-f, --fields FIELDS**
Specify output columns. Use either:
- Preset name with `+` prefix: `+standard`, `+jlc`, `+minimal`, or `+all`
- Comma-separated field list: `Reference,Quantity,Value,LCSC,I:Tolerance`
- Mix both: `+jlc,CustomField,I:Tolerance` expands jlc preset then adds custom fields

Default (if omitted): standard preset. Use `--list-fields` to see available fields.

**--multi-format FORMATS**
Emit multiple BOM formats in one run. Pass a comma-separated list (e.g., `jlc,standard`). Output files are named `<project>_bom.FORMAT.csv`. When used with `-f`, the same field list applies to all formats.

**--list-fields**
Print all available fields (standard BOM, inventory, component properties) and exit. Useful for building custom field lists.

**--smd**
Emit only SMD (surface mount device) components in the BOM. Filters out through-hole and mixed components.

**--quiet**
Suppress non-essential console output. Useful for CI pipelines.

**--json-report FILE**
Write a JSON report to FILE with statistics (entry count, unmatched count, format, etc.).

## POS ARGUMENTS

**PROJECT**
: KiCad project directory or a specific .kicad_pcb file. If a directory is given, jBOM auto-detects the PCB file (prefers files matching the directory name).

## POS OPTIONS

**--jlc**
Imply `+jlc` field preset for JLCPCB-compatible placement output. This preset includes: Designator, Mid X, Mid Y, Layer, Rotation columns in the order expected by JLCPCB's assembly service.

**-o, --output FILE**
: Output CSV path. If omitted, generates `<PROJECT>_pos.csv` in the project directory. File will contain component placement data.

**-f, --fields FIELDS**
: Column selection for CPL/POS output. Use presets with `+` prefix or a comma-separated list of field names.
- Presets:
  - `+kicad_pos`: Reference, X, Y, Rotation, Side, Footprint (KiCad-style format)
  - `+jlc`: Designator, Mid X, Mid Y, Layer, Rotation (JLCPCB format)
  - `+minimal`: Reference, X, Y (bare minimum)
  - `+all`: All available fields from PCB
- Custom: `Reference,X,Y,Rotation,Side,Footprint` or any combination
- Fields are case-insensitive and can use various formats

**--units {mm,inch}**
: Output coordinate units. Default: `mm`. Most pick-and-place machines expect millimeters.

**--origin {board,aux}**
: Coordinate origin reference point.
- `board`: Use board's lower-left corner (0,0)
- `aux`: Use auxiliary axis origin if defined in PCB, otherwise falls back to board origin

**--smd-only**
: Include only SMD (surface mount) components in output. Filters out through-hole parts. Uses footprint heuristics to detect component type.

**--layer {TOP,BOTTOM}**
: Filter components by board side. Only include components on specified layer.

**--loader {auto,pcbnew,sexp}**
: PCB file loading method.
- `auto`: Try pcbnew Python API first, fall back to S-expression parser (recommended)
- `pcbnew`: Use KiCad's pcbnew Python API (requires KiCad Python environment)
- `sexp`: Use built-in S-expression parser (works without KiCad installation)

## OUTPUT

**BOM CSV File**
: Default name `<ProjectName>_bom.csv`. Contains component reference, quantity, and matched supplier info with columns like Reference, Quantity, Value, LCSC, Footprint, Description, etc.

**POS CSV File**
: Specified by `-o` option. Contains component placement data with columns like Reference, X, Y, Rotation, Side, Footprint (or Designator, Mid X, Mid Y, Layer, Rotation for JLCPCB format). Coordinates are in specified units (mm or inches).

**Console Output**
: Summary line with schematic statistics, inventory count, and BOM entry count. For POS files, shows component count and layer distribution. Use `-d` to see detailed diagnostics.

**Exit Code**
: 0 on success (all components matched or user accepted matches)
: 2 on warning (one or more components unmatched; BOM written)
: 1 on error (file not found, invalid option, etc.)

## BOM FIELD PRESETS

Use `-f "+PRESET"`.

**+standard**
: Reference, Quantity, Description, Value, Footprint, LCSC, Datasheet, SMD, [Match_Quality], [Notes], [Priority]
: Comprehensive set with all standard BOM fields.

**+jlc**
: Reference, Quantity, LCSC, Value, Footprint, Description, Datasheet, SMD, [Match_Quality], [Notes], [Priority]
: Column set optimized for JLCPCB uploads (LCSC part number first).

**+minimal**
: Reference, Quantity, Value, LCSC
: Bare minimum: reference, quantity, component value, and LCSC part number only.

**+all**
: Includes every available field from inventory and schematic components (sorted alphabetically).
: Useful for debugging or exporting complete data for external tools.

## EXAMPLES

BOM (standard preset):
```
python -m jbom bom MyProject/ -i SPCoast-INVENTORY.xlsx
```

BOM JLC preset:
```
python -m jbom bom MyProject/ -i inventory.csv -f +jlc
```

BOM all fields:
```
python -m jbom bom MyProject/ -i inventory.csv -f +all
```

POS (auto-detect from project directory):
```
python -m jbom pos MyProject/
```

POS (JLCPCB-style with --jlc flag):
```
python -m jbom pos MyProject/ --jlc
```

POS (SMD only, top side):
```
python -m jbom pos MyProject/ --smd-only --layer TOP
```

POS (custom fields and explicit PCB file):
```
python -m jbom pos MyBoard.kicad_pcb -o MyBoard.csv -f "Reference,X,Y,Footprint,Side"
```

POS (specific output location):
```
python -m jbom pos MyProject/ -o fabrication/placement.csv
```

Verbose BOM scoring:
```
python -m jbom bom MyProject/ -i inventory.csv -v
```

Debug BOM run:
```
python -m jbom bom MyProject/ -i inventory.csv -d
```

## FIELDS

Use `--list-fields` to see the complete list. Common fields include:

**Standard BOM fields**
: Reference, Quantity, Description, Value, Footprint, LCSC, Datasheet, SMD, Priority, Match_Quality

**Inventory fields** (prefix with `I:` to disambiguate from component properties)
: Category, Package, Manufacturer, MFGPN, Tolerance, V, A, W, mcd, Wavelength, Angle, Frequency, Stability, Load, Family, Type, Pitch, Form

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
python jbom.py project -i inv.csv -f "Reference,Match Quality,I:PACKAGE"
python jbom.py project -i inv.csv -f "reference,match_quality,i:package"
python jbom.py project -i inv.csv -f "REFERENCE,MATCH_QUALITY,I:PACKAGE"
```

## INVENTORY FILE FORMAT

Detailed inventory file format documentation is in [inventory(5)](README.man5.md).

Required columns:
: IPN, Category, Value, Package, LCSC, Priority

Optional columns:
: Manufacturer, MFGPN, Datasheet, Keywords, SMD, Tolerance, V, A, W, Type, Form, Frequency, Stability, Load, Family, mcd, Wavelength, Angle, Pitch

**Priority** uses integer ranking (1 = preferred, higher = less preferred). When multiple parts match, the lowest Priority is selected.

See [README.man5.md](README.man5.md) for complete column definitions and examples.

## TROUBLESHOOTING

**No schematic files found**
: Ensure the project directory contains `.kicad_sch` files or pass the schematic path directly.

**"Unsupported inventory file format"**
: Check file extension (.csv, .xlsx, .xls, .numbers) and install optional packages if needed:
: `pip install openpyxl numbers-parser`

**Components not matching**
: Run with `-d` to see detailed diagnostics. Check that inventory Category, Package, and Value fields match component attributes.

**Import errors for Excel/Numbers**
: Install: `pip install openpyxl` (for .xlsx, .xls) or `pip install numbers-parser` (for .numbers).

## SEE ALSO

- [**README.md**](../README.md) — Overview and quick start
- [**README.man3.md**](README.man3.md) — Python library API reference
- [**README.man4.md**](README.man4.md) — KiCad Eeschema plugin integration
- [**README.man5.md**](README.man5.md) — Inventory file format
- [**README.developer.md**](README.developer.md) — Architecture and matching algorithms
