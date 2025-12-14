# jbom(4) — KiCad Eeschema Integration

## NAME

jbom — jBOM Plugin for KiCad Eeschema

## DESCRIPTION

jBOM integrates with KiCad's Eeschema via the "Generate BOM" plugin system. This allows you to generate a BOM directly from the schematic editor without using the command line.

The integration uses the `kicad_jbom_plugin.py` wrapper script, which translates KiCad's plugin interface to the jBOM library API.

## SETUP

Register jBOM as a BOM plugin in KiCad:

1. Open Eeschema with your project
2. Navigate to **Tools → Generate BOM**
3. Click the **Add plugin** button (or equivalent in your KiCad version)
4. Enter a name: `jBOM` (or similar)
5. Enter the command:
   ```
   python3 /absolute/path/to/kicad_jbom_plugin.py %I -i /absolute/path/to/INVENTORY.xlsx -o %O
   ```

**Important:**
- Replace `/absolute/path/to/...` with your actual paths
- Keep `%I` and `%O` exactly as-is; KiCad substitutes these at runtime:
  - `%I` = input schematic file (from current project)
  - `%O` = output file path (user-selected in dialog)
- Use absolute paths (not relative) for inventory and script

## USAGE

Once registered:

1. In Eeschema, open **Tools → Generate BOM**
2. Select the **jBOM** plugin from the list
3. Click **Generate** or **Cancel BOM**
4. Inspect the output CSV file in your project directory

## COMMAND SYNTAX

```
python3 /path/to/kicad_jbom_plugin.py SCHEMATIC -i INVENTORY -o OUTPUT [FLAGS]
```

**SCHEMATIC** — Input schematic file (provided by KiCad as `%I`)

**-i, --inventory INVENTORY** — Path to inventory file (required)

**-o, --output OUTPUT** — Output CSV path (provided by KiCad as `%O`)

**FLAGS** (optional):
- `-v, --verbose` — Include Match_Quality and Priority columns
- `-d, --debug` — Emit detailed diagnostics to stderr
- `-f, --fields FIELDS` — Field selection: use presets (+standard, +jlc, +minimal, +all) or comma-separated field list

## COMMON CONFIGURATIONS

**Minimal (quick generation - standard preset):**
```
python3 /path/to/kicad_jbom_plugin.py %I -i /path/to/inventory.csv -o %O
```

**With JLC preset:**
```
python3 /path/to/kicad_jbom_plugin.py %I -i /path/to/inventory.csv -o %O -f +jlc
```

**With minimal preset:**
```
python3 /path/to/kicad_jbom_plugin.py %I -i /path/to/inventory.csv -o %O -f +minimal
```

**With matching scores and priorities (verbose):**
```
python3 /path/to/kicad_jbom_plugin.py %I -i /path/to/inventory.csv -o %O -v
```

**For troubleshooting (debug output):**
```
python3 /path/to/kicad_jbom_plugin.py %I -i /path/to/inventory.xlsx -o %O -d
```

**Custom output fields (JLCPCB-friendly):**
```
python3 /path/to/kicad_jbom_plugin.py %I -i /path/to/inventory.csv -o %O -f "Reference,Quantity,LCSC,Value,Footprint"
```

## ENVIRONMENT REQUIREMENTS

- Python 3.9 or newer
- `sexpdata` package (`pip install sexpdata`)
- Optional: `openpyxl` for Excel support (`pip install openpyxl`)
- Optional: `numbers-parser` for Numbers support (`pip install numbers-parser`)

## OUTPUT

The plugin writes a CSV file to the location specified in the KiCad Generate BOM dialog. The file contains:

- **Default columns** (standard preset): Reference, Quantity, Description, Value, Footprint, LCSC, Datasheet, SMD
- **With `-f +jlc`**: Reference, Quantity, LCSC, Value, Footprint, Description, Datasheet, SMD
- **With `-v`**: adds Match_Quality, Priority columns
- **With `-d`**: Notes field contains debugging information

Exit code is returned to KiCad (0=success, non-zero=error). Errors are logged to stderr.

## TROUBLESHOOTING

**Plugin doesn't appear in the list**
: Verify the command path is correct and Python is accessible from the command line. Test manually:
: ```bash
: python3 /path/to/kicad_jbom_plugin.py /path/to/test.kicad_sch -i /path/to/inventory.csv -o /tmp/test_bom.csv
: ```

**"Inventory file not found"**
: Use absolute paths in the command. Check that the file exists:
: ```bash
: ls -la /path/to/inventory.csv
: ```

**"No .kicad_sch file found"**
: Ensure you are running the plugin from within an Eeschema project that has been saved. The schematic path is provided by KiCad.

**"Excel support requires openpyxl"**
: If using .xlsx or .xls files, install the optional dependency:
: ```bash
: pip install openpyxl
: ```

**"Numbers support requires numbers-parser"**
: If using .numbers files, install:
: ```bash
: pip install numbers-parser
: ```

**Debug output not shown**
: Debug messages go to stderr, not stdout. In KiCad, check the Eeschema console or redirect stderr when running manually.

**BOM file is empty or incomplete**
: Verify that:
- Inventory file has required columns (IPN, Category, Value, Package, LCSC, Priority)
- Schematic components have Reference, Value, and Footprint properties set
- Use `-d` flag to see detailed matching diagnostics

**Schematic symbols are hierarchical but BOM is incomplete**
: jBOM automatically detects and processes hierarchical sheets. If some components are missing, verify that:
- All sub-sheets are in the same directory or are correctly referenced
- Sub-sheet files have `.kicad_sch` extension

## WORKFLOW EXAMPLE

### Simple workflow:

1. In Eeschema: **Tools → Generate BOM → Select jBOM → Generate**
2. Choose output filename (e.g., `MyProject_bom.csv`)
3. BOM is generated and saved
4. Open the CSV in your spreadsheet application or submit to manufacturer

### Iterative development:

1. Edit schematic in Eeschema
2. Generate BOM with jBOM plugin
3. Check for unmatched components (empty LCSC column)
4. Update inventory file if needed
5. Re-run BOM generation

### CI/Automation:

For automated BOM generation in build scripts, use the command-line interface directly (see [README.man1.md](README.man1.md)). The plugin is primarily for interactive use in Eeschema.

## INVENTORY FILE REQUIREMENTS

The inventory file must have these columns:
- **IPN** — Internal Part Number (your reference ID)
- **Category** — Component type (RES, CAP, LED, IC, etc.)
- **Value** — Component value or part number
- **Package** — Physical package (0603, SOT-23, DIP-8, etc.)
- **LCSC** — LCSC part number (supplier ID)
- **Priority** — Integer ranking (1 = preferred, higher = less preferred)

Optional columns for enhanced matching:
- Manufacturer, MFGPN, Datasheet, SMD, Tolerance, V, A, W, Type, Frequency, etc.

See [README.man1.md](README.man1.md) (INVENTORY FILE FORMAT section) for complete details.

## SEE ALSO

- [**README.md**](../README.md) — Overview and quick start
- [**README.man1.md**](README.man1.md) — Command-line interface reference
- [**README.man3.md**](README.man3.md) — Python library API reference
- [**README.developer.md**](README.developer.md) — Matching algorithms and internals
- [**kicad_jbom_plugin.py**](../kicad_jbom_plugin.py) — The wrapper script (source code)
