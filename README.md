# jBOM — KiCad Bill of Materials Generator

A powerful, supplier-neutral BOM generator for KiCad projects. Matches schematic components against your inventory at BOM-generation time rather than hardcoding part numbers in symbols.

**Key Benefits:**
- **Supplier-neutral designs** — No part numbers baked into schematics
- **Current inventory data** — Match against up-to-date stock and pricing
- **Intelligent matching** — Robust numeric parsing for resistors, capacitors, inductors, etc.
- **Multiple inventory formats** — CSV, Excel (.xlsx, .xls), Apple Numbers (.numbers)
- **Three integration options** — KiCad plugin, CLI, or Python library
- **Hierarchical schematics** — Automatically processes multi-sheet designs

## Installation

**Required:**
- Python 3.9 or newer
- `sexpdata` package: `pip install sexpdata`

**Optional (for spreadsheet support):**
```bash
pip install openpyxl          # For .xlsx, .xls files
pip install numbers-parser    # For .numbers files

# Or install all at once:
pip install sexpdata openpyxl numbers-parser
```

## Quick Start

### 1. Prepare your inventory

Create an inventory file (CSV, Excel, or Numbers) with required columns:
- `IPN` — Your internal part number
- `Category` — Component type (RES, CAP, LED, IC, etc.)
- `Value` — Component value (10k, 100nF, etc.)
- `Package` — Physical package (0603, SOT-23, etc.)
- `LCSC` — Supplier part number
- `Priority` — Integer ranking (1 = preferred, higher = less)

Optional: Manufacturer, MFGPN, Datasheet, Tolerance, V, A, W, and component-specific fields.

### 2. Generate your BOM

**Via KiCad (interactive):**
- Eeschema → Tools → Generate BOM → Select jBOM → Generate

**Via command line:**
```bash
python jbom.py MyProject/ -i inventory.xlsx
```

**Via Python:**
```python
from jbom import generate_bom_api, GenerateOptions
opts = GenerateOptions(manufacturer=True)
result = generate_bom_api('MyProject/', 'inventory.xlsx', options=opts)
```

That's it! The BOM is written to `MyProject_bom.csv`.

## Usage Documentation

jBOM documentation is organized as Unix man pages for clarity and reference:

| Document | Purpose |
|----------|---------|
| **README.man1.md** | [CLI reference](README.man1.md) — Options, fields, examples, troubleshooting |
| **README.man3.md** | [Python API reference](README.man3.md) — Classes, functions, library workflows |
| **README.man4.md** | [KiCad plugin setup](README.man4.md) — Eeschema integration, configurations |
| **README.developer.md** | Technical details — Matching algorithms, architecture, extending jBOM |

## Common Tasks

### Generate a standard BOM
```bash
python jbom.py MyProject/ -i inventory.xlsx -o MyProject_bom.csv
```

### Include manufacturer and part numbers
```bash
python jbom.py MyProject/ -i inventory.xlsx -m
```

### Generate JLCPCB-friendly format
```bash
python jbom.py MyProject/ -i inventory.xlsx --format jlc
```

### Generate both JLC and standard formats at once
```bash
python jbom.py MyProject/ -i inventory.xlsx --multi-format jlc,standard
```

### Debug component matching issues
```bash
python jbom.py MyProject/ -i inventory.xlsx -d
```

### List available output columns
```bash
python jbom.py MyProject/ -i inventory.xlsx --list-fields
```

## Integration Methods

### 1. KiCad Eeschema Plugin
Register jBOM in the Generate BOM dialog for interactive use within Eeschema.

**Setup command:**
```
python3 /absolute/path/to/kicad_jbom_plugin.py %I -i /absolute/path/to/inventory.xlsx -o %O -m
```

See [README.man4.md](README.man4.md) for detailed setup and troubleshooting.

### 2. Command-Line Interface
Use in scripts, CI pipelines, or standalone workflows.

```bash
python jbom.py PROJECT/ -i INVENTORY.xlsx [OPTIONS]
```

See [README.man1.md](README.man1.md) for all options and examples.

### 3. Python Library
Embed jBOM in custom tools or workflows.

```python
from jbom import generate_bom_api, GenerateOptions

opts = GenerateOptions(verbose=True, manufacturer=True)
result = generate_bom_api('project/', 'inventory.xlsx', options=opts)

for entry in result['bom_entries']:
    print(f"{entry.reference}: {entry.lcsc}")
```

See [README.man3.md](README.man3.md) for the full API reference.

## Component Matching

jBOM uses intelligent matching to find inventory parts that fit your schematic components:

1. **Type detection** — Identifies resistors, capacitors, inductors, LEDs, ICs, etc.
2. **Package matching** — Matches footprints (0603, SOT-23) to inventory packages
3. **Value parsing** — Handles various formats (10k, 10K0, 10000, 330R, 3R3, etc.)
4. **Property scoring** — Ranks matches by tolerance, voltage, current, and other attributes
5. **Priority ranking** — Selects preferred parts using inventory Priority column

See README.developer.md for matching algorithm details.

## Output

jBOM generates:
- **CSV BOM file** — `<ProjectName>_bom.csv` with matched components
- **Exit code** — 0 (success), 2 (warning/unmatched), 1 (error)
- **Console summary** — Statistics about components and matches
- **Debug info** — Detailed diagnostics (with `-d` flag)

## Troubleshooting

**Components not matching?**
: Run with `-d` flag to see detailed matching diagnostics.

**Import error for Excel/Numbers?**
: Install optional packages: `pip install openpyxl numbers-parser`

**Plugin not showing in KiCad?**
: Verify the command path is correct and use absolute paths. See [README.man4.md](README.man4.md).

**Hierarchical schematics not processing all sheets?**
: Ensure all sub-sheets are in the same directory and have `.kicad_sch` extension.

For more troubleshooting, see the relevant man page:
- CLI issues → [README.man1.md](README.man1.md)
- Plugin issues → [README.man4.md](README.man4.md)
- API issues → [README.man3.md](README.man3.md)

## Project Structure

```
jBOM/
├── jbom.py                    # Main library and CLI (2700+ lines)
├── kicad_jbom_plugin.py       # KiCad plugin wrapper
├── test_jbom.py               # Test suite (64 tests)
├── README.md                  # This file
├── README.man1.md             # CLI man page
├── README.man3.md             # Python API man page
├── README.man4.md             # KiCad plugin man page
├── README.developer.md        # Technical documentation
└── LICENSE                    # License terms
```

## Version

jBOM v1.0.0 — Stable release with intelligent component matching, multiple inventory formats, and comprehensive integration options.

## License

See LICENSE file for terms.

## Support

For detailed information:
- **Using the CLI?** See [README.man1.md](README.man1.md)
- **Integrating with KiCad?** See [README.man4.md](README.man4.md)
- **Using the Python API?** See [README.man3.md](README.man3.md)
- **Understanding the matching logic?** See README.developer.md
