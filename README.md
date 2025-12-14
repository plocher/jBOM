# jBOM — KiCad Bill of Materials Generator

A powerful BOM generator for KiCad projects, jBOM matches schematic components against your inventory at BOM-generation time rather than hardcoding part numbers in eeschema symbols. This makes your designs supplier-neutral, meaning you can match against current inventory and pricing whenever you generate a BOM.

jBOM handles multiple inventory formats (CSV, Excel, Apple Numbers), supports KiCad's hierarchical schematics, and provides intelligent component matching with robust numeric parsing for resistors, capacitors, inductors, and other component types. You can integrate it three ways: as a KiCad Eeschema plugin, via the command line, or as a Python library in your custom tools.

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
python jbom.py MyProject/ -i inventory.xlsx
```

**Via Python:**
```python
from jbom import generate_bom_api, GenerateOptions

opts = GenerateOptions(verbose=True)
result = generate_bom_api('MyProject/', 'inventory.xlsx', options=opts)
```

That's it! The BOM is written to `MyProject_bom.csv`.

## Component Matching

jBOM uses intelligent matching to find inventory parts that fit your schematic components. First, it detects the component type (resistor, capacitor, inductor, LED, IC, etc.) from the schematic symbol. Then it extracts the physical package from the footprint and parses the component value, handling various formats like 10k, 10K0, 10000, 330R, or 3R3.

For each potential match, jBOM scores candidates by comparing properties like tolerance, voltage, and current ratings. Finally, it uses the inventory's Priority column (1 = preferred, higher = less preferred) to break ties and select the best part.

See docs/README.developer.md for detailed information about the matching algorithm.

## Output

jBOM generates a CSV BOM file (`<ProjectName>_bom.csv`) with all matched components and their supplier part numbers. It also prints a summary to the console showing statistics about how many components were found and how many successfully matched. With the `-d` flag, you get detailed diagnostic information about why any components failed to match. The exit code indicates success (0), warning/unmatched components (2), or error (1).

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

- [**docs/README.man1.md**](docs/README.man1.md) — CLI reference
- [**docs/README.man3.md**](docs/README.man3.md) — Python library API
- [**docs/README.man4.md**](docs/README.man4.md) — KiCad plugin setup
- [**docs/README.man5.md**](docs/README.man5.md) — Inventory file format
- [**docs/README.developer.md**](docs/README.developer.md) — Technical architecture
- [**docs/**](docs/) — All documentation (user guides, developer guides, changelog, contributing)

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

jBOM v1.0.1 — Stable release with intelligent component matching, case-insensitive field handling, enhanced tolerance-aware matching, multiple inventory formats, and comprehensive integration options.

Author: John Plocher

## License

AGPLv3 — See LICENSE file for full terms.
