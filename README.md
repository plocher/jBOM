# jBOM — KiCad Bill of Materials and Placement Generator

A comprehensive fabrication tool for KiCad projects, jBOM generates both Bills of Materials (BOM) and Component Placement Lists (CPL/POS) for PCB manufacturing. It matches schematic components against your inventory at generation time rather than hardcoding part numbers in symbols, making your designs supplier-neutral so you can match against current inventory and pricing whenever needed.

jBOM handles multiple inventory formats (CSV, Excel, Apple Numbers), supports KiCad's hierarchical schematics, and provides intelligent component matching with robust numeric parsing for resistors, capacitors, inductors, and other component types. It also generates accurate placement files from PCB layouts with support for multiple coordinate systems and formats.

You can integrate jBOM in three ways: as a KiCad plugin (Eeschema or Pcbnew), via the command line, or as a Python library in your custom tools.

## Installation

You need Python 3.9 or newer and the following packages:

```bash
# For basic operation with csv inventories
pip install sexpdata

# To add support for Microsoft Excel Spreadsheet Inventories
pip install openpyxl

# To add support for Apple Numbers Spreadsheet Inventories
pip install numbers-parser
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

  `Eeschema` → `Tools` → `Generate BOM` → `Select jBOM` → `Generate`

**Via command line:**
```bash
# BOM (schematics → CSV with inventory matching)
python -m jbom bom MyProject/ -i inventory.xlsx

# BOM with JLCPCB-optimized fields
python -m jbom bom MyProject/ -i inventory.xlsx --jlc

# Placement/CPL (PCB → CSV for pick-and-place machines)
python -m jbom pos MyProject/

# Placement with JLCPCB format (auto-detects PCB in project)
python -m jbom pos MyProject/ --jlc

# Or specify PCB file directly
python -m jbom pos MyBoard.kicad_pcb -o MyBoard.pos.csv
```

**Via Python:**
```python
from jbom import generate_bom_api, GenerateOptions
from jbom.pcb import BoardLoader, PositionGenerator

# Generate BOM
opts = GenerateOptions(verbose=True)
result = generate_bom_api('MyProject/', 'inventory.xlsx', options=opts)

# Generate placement file
board = BoardLoader.load('MyBoard.kicad_pcb')
gen = PositionGenerator(board)
gen.write_csv('MyBoard.pos.csv', fields_preset='jlc')
```

That's it! The BOM is written to `MyProject_bom.csv` and placement to `MyBoard.pos.csv`.

## Component Matching

jBOM uses intelligent matching to find inventory parts that fit your schematic components. First, it detects the component type (resistor, capacitor, inductor, LED, IC, etc.) from the schematic symbol. Then it extracts the physical package from the footprint and parses the component value, handling various formats like 10k, 10K0, 10000, 330R, or 3R3.

For each potential match, jBOM scores candidates by comparing properties like tolerance, voltage, and current ratings. Finally, it uses the inventory's Priority column (1 = preferred, higher = less preferred) to break ties and select the best part.

See docs/README.developer.md for detailed information about the matching algorithm.

## Output

**BOM Files:**
jBOM generates a CSV BOM file (`<ProjectName>_bom.csv`) with all matched components and their supplier part numbers. It also prints a summary to the console showing statistics about how many components were found and how many successfully matched. With the `-d` flag, you get detailed diagnostic information about why any components failed to match.

**Placement Files:**
The `pos` command generates CSV placement files (CPL/POS format) with component positions, rotations, and layers for pick-and-place machines. Output includes X/Y coordinates, rotation angle, component side (top/bottom), and footprint information in formats compatible with major PCB assemblers.

**Exit codes:** 0 = success, 2 = warning/unmatched components, 1 = error

## Field Naming & Case-Insensitivity

jBOM accepts field names in any format:
- Snake_case: `match_quality`, `i:package`
- Title Case: `Match Quality`, `I:Package`
- UPPERCASE: `MATCH_QUALITY`, `I:PACKAGE`
- Mixed: `MatchQuality`, `Match-Quality`

All formats are normalized internally, so you can use whichever is most convenient. CSV headers are always output in Title Case for readability.

## Troubleshooting

**Components not matching?**
: Run with `-d` flag to see detailed matching diagnostics.

**Plugin not showing in KiCad?**
: Verify the command path is correct and use absolute paths. See [docs/README.man4.md](docs/README.man4.md).

For more troubleshooting, see the relevant man page:
- CLI issues → [docs/README.man1.md](docs/README.man1.md)
- Plugin issues → [docs/README.man4.md](docs/README.man4.md)
- API issues → [docs/README.man3.md](docs/README.man3.md)
- Inventory format → [docs/README.man5.md](docs/README.man5.md)

## SEE ALSO

- [**docs/README.arch.md**](docs/README.arch.md) — Current architecture and module layout
- [**docs/README.man1.md**](docs/README.man1.md) — CLI reference
- [**docs/README.man3.md**](docs/README.man3.md) — Python library API
- [**docs/README.man4.md**](docs/README.man4.md) — KiCad plugin setup
- [**docs/README.man5.md**](docs/README.man5.md) — Inventory file format
- [**docs/README.developer.md**](docs/README.developer.md) — Technical architecture
- [**docs/**](docs/) — All documentation (user guides, developer guides, changelog, contributing)

## Modules and imports
- Main API: `from jbom import generate_bom_api, GenerateOptions`
- PCB module: `from jbom.pcb import BoardLoader, PositionGenerator`
- Shared utilities: `from jbom.common import normalize_field_name, resolve_output_path`
- Optional convenience: `from jbom.sch import Component, BOMGenerator` (same as importing from jbom)

## Contributing

Contributions are welcome! jBOM is developed on GitHub at [github.com/plocher/jBOM](https://github.com/plocher/jBOM).

To contribute:
1. Fork the repository on GitHub
2. Create a feature branch for your changes
3. Make your changes and add tests
4. Run the test suite: `python -m unittest tests.test_jbom -v`
5. Submit a pull request

For detailed development setup, coding standards, and testing guidelines, see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Version

jBOM v2.1.0 — Feature release with intelligent component matching, comprehensive functional testing, proper acronym handling in CSV headers, improved CLI exception handling, and extensive edge case coverage.

Author: John Plocher

## License

AGPLv3 — See LICENSE file for full terms.
