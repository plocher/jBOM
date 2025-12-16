# jBOM — KiCad Bill of Materials and Placement Generator

## Why jBOM?

Designing a PCB in KiCad is only half the battle. Before you can manufacture your board, you need:

1. **A Bill of Materials (BOM)** — telling the assembler which parts to use
2. **A placement file (CPL/POS)** — telling pick-and-place machines where to put them

Most BOM tools force you to hardcode specific part numbers (like "LCSC:C123456") directly into your KiCad symbols. This creates problems:
- Your design becomes **locked to specific vendors** and part numbers
- When parts go out of stock or prices change, you must **manually edit your schematics**
- You can't easily **switch suppliers** or take advantage of bulk pricing
- Design reuse becomes difficult when inventory changes

**jBOM solves this** by separating part selection from circuit design. You design with generic values ("10kΩ resistor, 0603"), maintain a separate inventory file with your available parts, and jBOM intelligently matches them at BOM generation time. Update your inventory whenever you want—your schematics stay clean and vendor-neutral.

## Where jBOM Fits in Your Workflow

```
KiCad Design → jBOM → Manufacturing Files → PCB Assembly
```

**Typical workflow:**
1. Design your circuit in KiCad using generic component values
2. Maintain an inventory spreadsheet with your available parts (or supplier catalogs)
3. **Run jBOM** to generate:
   - BOM with matched supplier part numbers (for ordering/assembly)
   - Placement file (for pick-and-place machines)
4. Send files to your PCB assembler (JLCPCB, PCBWay, etc.)

jBOM integrates directly into KiCad's "Generate BOM" tool, works from the command line for automation, or can be called from Python scripts for custom workflows.

## Installation

**From PyPI (recommended):**

```bash
# Basic installation (CSV inventory support)
pip install jbom

# With Excel support
pip install jbom[excel]

# With Apple Numbers support
pip install jbom[numbers]

# Everything
pip install jbom[all]
```

Requires Python 3.9 or newer.

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
jbom bom MyProject/ -i inventory.xlsx

# BOM with JLCPCB-optimized fields
jbom bom MyProject/ -i inventory.xlsx --jlc

# Placement/CPL (PCB → CSV for pick-and-place machines)
jbom pos MyProject/

# Placement with JLCPCB format (auto-detects PCB in project)
jbom pos MyProject/ --jlc

# Or specify PCB file directly
jbom pos MyBoard.kicad_pcb -o MyBoard.pos.csv
```

**Via Python:**
```python
from jbom.api import generate_bom, generate_pos, BOMOptions, POSOptions

# Generate BOM
opts = BOMOptions(verbose=True)
result = generate_bom(
    input='MyProject/',
    inventory='inventory.xlsx',
    output='MyProject_bom.csv',
    options=opts
)

# Generate placement file
opts = POSOptions(units='mm', smd_only=True)
result = generate_pos(
    input='MyProject/',
    output='MyProject_pos.csv',
    options=opts
)
```

That's it! The BOM is written to `MyProject_bom.csv` and placement to `MyBoard.pos.csv`.

## How Matching Works

jBOM automatically finds the best inventory parts for your schematic components using intelligent matching:

1. **Type detection** — Identifies component type (resistor, capacitor, LED, IC, etc.) from symbol
2. **Value parsing** — Understands various formats: 10k, 10K0, 10000, 330R, 3R3, 100nF, 0.1uF
3. **Package extraction** — Reads physical package (0603, SOT-23, etc.) from footprint
4. **Candidate scoring** — Compares tolerance, voltage, current ratings, and other parameters
5. **Priority ranking** — Uses your inventory's Priority column (1 = most preferred) to break ties

The result: jBOM selects the best matching part from your inventory automatically.

For technical details about the matching algorithm, see [docs/README.developer.md](docs/README.developer.md).

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
- Main API: `from jbom.api import generate_bom, BOMOptions`
- PCB module: `from jbom.loaders.pcb import PCBLoader`
- Position generation: `from jbom.generators.pos import POSGenerator`
- BOM generation: `from jbom.generators.bom import BOMGenerator`
- Shared utilities: `from jbom.common.fields import normalize_field_name`
- Output handling: `from jbom.common.output import resolve_output_path`

## Contributing

Contributions are welcome! jBOM is developed on GitHub at [github.com/plocher/jBOM](https://github.com/plocher/jBOM).

To contribute:
1. Fork the repository on GitHub
2. Create a feature branch for your changes
3. Make your changes and add tests
4. Run the test suite: `python -m unittest discover -s tests -v`
5. Submit a pull request

For detailed development setup, coding standards, and testing guidelines, see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## KiCad Plugin Integration

To use jBOM as a KiCad BOM tool in Eeschema:

1. In KiCad Eeschema, go to `Tools` → `Generate BOM`
2. Click `+` to add a new plugin
3. Enter the full path to `kicad_jbom_plugin.py`
4. In the command line field, add your inventory path and any options:
   ```
   python3 /path/to/kicad_jbom_plugin.py "%I" -i /path/to/inventory.xlsx -o "%O" --jlc
   ```
5. Click `Generate` to create your BOM

The plugin is a thin wrapper that translates KiCad's interface to jBOM CLI calls. All CLI options are supported.

## Version

jBOM v3.0.0 — Major architectural refactoring with data-flow architecture, argparse CLI with Command pattern, comprehensive test coverage (169 tests), and KiCad plugin integration.

Author: John Plocher

## License

AGPLv3 — See LICENSE file for full terms.
