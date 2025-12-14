# jbom(1) — KiCad Bill of Materials Generator

## NAME

jbom — generate bill of materials from KiCad schematics

## SYNOPSIS

```
python jbom.py PROJECT_PATH -i INVENTORY [-o OUTPUT] [OPTIONS]
```

## DESCRIPTION

Generates a bill of materials (BOM) for a KiCad project by intelligently matching schematic components against an inventory file. Components are matched by type, value, and package; the result is written to CSV with customizable columns.

**Key design:** Keeps designs supplier-neutral by matching at BOM-generation time rather than hardcoding part numbers in schematics.

## ARGUMENTS

**PROJECT_PATH**
: Path to KiCad project directory or a specific .kicad_sch schematic file. If a directory is given, jBOM will auto-detect and process hierarchical schematics.

**-i, --inventory FILE**
: Path to inventory file (required). Supported formats: .csv, .xlsx, .xls, .numbers

## OPTIONS

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

## OUTPUT

**BOM CSV File**
: Default name `<ProjectName>_bom.csv`. Contains component reference, quantity, and matched supplier info.

**Console Output**
: Summary line with schematic statistics, inventory count, and BOM entry count. Use `-d` to see detailed diagnostics.

**Exit Code**
: 0 on success (all components matched or user accepted matches)
: 2 on warning (one or more components unmatched; BOM written)
: 1 on error (file not found, invalid option, etc.)

## FIELD PRESETS

Presets are activated with the `+` prefix in the `-f` argument (e.g., `-f "+jlc"`).

**+standard** (default if no `-f` given)
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

Basic usage (standard preset):
```
python jbom.py MyProject/ -i SPCoast-INVENTORY.xlsx
```

Use JLC preset:
```
python jbom.py MyProject/ -i inventory.csv -f +jlc
```

Use minimal preset:
```
python jbom.py MyProject/ -i inventory.csv -f +minimal
```

Use all available fields:
```
python jbom.py MyProject/ -i inventory.csv -f +all
```

Custom field list:
```
python jbom.py MyProject/ -i inventory.csv -f "Reference,Quantity,Value,LCSC"
```

Expand preset and add custom fields:
```
python jbom.py MyProject/ -i inventory.csv -f "+standard,I:Tolerance,C:Voltage"
```

With verbose scoring (show Match_Quality and Priority):
```
python jbom.py MyProject/ -i inventory.csv -v
```

Generate both JLC and standard formats:
```
python jbom.py MyProject/ -i inventory.xlsx --multi-format jlc,standard
```

Debug run (show matching details):
```
python jbom.py MyProject/ -i inventory.csv -d
```

Console output (no file):
```
python jbom.py MyProject/ -i inventory.csv -o console
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

- **README.md** — Overview and quick start
- **README.man3.md** — Python library API reference
- **README.man4.md** — KiCad Eeschema plugin integration
- **README.developer.md** — Architecture and matching algorithms
