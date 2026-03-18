# jBOM — KiCad Bill of Materials and Placement Generator

## Why jBOM?

Designing a PCB in KiCad is only part of the journey that results in a fabricated and assembled electronic product.  The PCB fabrication just needs the KiCad-produced Gerber files, but the assembly process requires a **Bill of Materials (BOM)** and a **Placement file (CPL/POS)**.

The common KiCad workflow has you annotate your KiCad symbols with supply chain details such as "IPN:RES-331-0603", "MFG:Yageo", "MPN:CC0603KRX7R9BB104", "LCSC:C123456", and then use KiCad's fabrication plugins to generate BOM and CPL files.  This mechanism is easy to understand, and, through KiCad's web/database library integration, plugins such as Part-DB, InvenTree, PartsBox and GitPLM connect to extensive parts databases.  While these this workflow has proven sufficient for many developers, it inadvertently makes it difficult to decouple supply chain evolution from a project's electronic and mechanical specifications.

**jBOM solves this** by separating part selection from circuit design. You design with generic values ("10k, 5%, Resistor_SMD:R_0603_1608Metric"), maintain a currated inventory file with your desired parts, and jBOM intelligently matches them at BOM generation time.  Changing suppliers or cost reducing a set of projects is as simple as updating an inventory spreadsheet.

## Documentation
Command line: [docs/README.man1.md](docs/README.man1.md)
Python Library API: [docs/README.man3.md](docs/README.man3.md)
KiCad Eeschema Integration: [docs/README.man4.md](docs/README.man4.md)
jBOM Inventory File Format: [docs/README.man5.md](docs/README.man5.md)

## Installation
Requires Python 3.10 or newer.

**From PyPI (recommended):**

```bash
# Basic installation (with only CSV inventory support)
pip install jbom

# With CSV, Excel and Numbers spreadsheet support
pip install jbom[all]

# With CSV and Excel support
pip install jbom[excel]
# With CSV and Apple Numbers support
pip install jbom[numbers]

# With Mouser Search support
pip install jbom[search]
```

## Quick Start

**Scenario: New KiCad project → JLCPCB manufacturing files.**

### 1. Extract an inventory template

```bash
jbom inventory MyProject/ -o inventory.csv
```

This writes one row per unique Value + Package combination found in your schematics. IPN, Category, Value, and Package are pre-filled; supplier columns (LCSC, Manufacturer, MFGPN) are blank for you to complete.

### 2. Audit schematic field quality

Before filling in part numbers, verify your schematic fields are complete:

```bash
jbom audit MyProject/ -o report.csv
```

This checks every component against jBOM's field taxonomy and writes findings to `report.csv`. Open it in a spreadsheet, fill in `ApprovedValue` for any `QUALITY_ISSUE` rows, set `Action` to `SET`, then apply the fixes back to your schematic:

```bash
jbom annotate MyProject/ --repairs report.csv
```

Once the schematic is clean, verify your inventory covers every component:

```bash
jbom audit MyProject/ --inventory inventory.csv
```

### 3. Fill in part numbers for JLC's LCSC supplier

An inventory file maps your generic schematic values to real parts from a supplier's catalog — in this case LCSC, which JLCPCB uses for sourcing. Open `inventory.csv` and fill in the **LCSC** column for each part you want JLCPCB to source. Set **Priority** to `1` on rows you want matched first.

To find LCSC part numbers:
- Search interactively: `jbom search "10k 0603 resistor" --supplier lcsc`
- Look up manually at [jlcpcb.com/parts](https://jlcpcb.com/parts)
- Export your JLCPCB private parts library (*User Center → My Inventory → My Parts Lib → Export*) and load it alongside: `--inventory project.csv --inventory jlc_library.xlsx`

> **Coming soon**: `jbom inventory MyProject/ --supplier lcsc --limit 3 -o inventory.csv` will search and populate part numbers automatically.

### 4. Generate BOM and placement files

```bash
jbom bom MyProject/ --jlc --inventory inventory.csv
jbom pos MyProject/ --jlc
```

This produces `MyProject.bom.csv` and `MyProject.pos.csv`, ready to upload to JLCPCB.
Preview first without writing files: `jbom bom MyProject/ --jlc --inventory inventory.csv -o console`

---

For the full step-by-step walkthrough, options, and troubleshooting tips, see the **[Tutorial series](docs/tutorial/README.md)**.

## KiCad Integration

Run jBOM directly from KiCad's **Generate BOM** dialog — see [docs/README.man4.md](docs/README.man4.md) for setup.

Quick summary:
1. In Eeschema, go to `Tools` → `Generate BOM`.
2. Add a plugin with the command:
   ```
   python3 /path/to/kicad_jbom_plugin.py "%I" --inventory /path/to/inventory.csv -o "%O" --jlc
   ```
3. Click `Generate`.

## Configuration

Built-in fabricator profiles: `--jlc`, `--pcbway`, `--seeed`.

To create a custom profile or configure organisation-wide defaults, see [docs/tutorial/README.documentation.md](docs/tutorial/README.documentation.md) and [docs/README.configuration.md](docs/README.configuration.md).

## Contributing

Contributions are welcome! jBOM is developed on GitHub at [github.com/plocher/jBOM](https://github.com/plocher/jBOM).

To contribute:
1. Fork the repository
2. Create a feature branch
3. Run tests: `pytest && python -m behave --format progress`
4. Submit a pull request

Regenerate deterministic search parity artifacts (fixture-based):
`python scripts/generate_search_parity_artifacts.py`

Regenerate baseline-vs-candidate parity delta evidence:
`python scripts/generate_search_parity_delta_report.py`

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for details.

**License**: AGPLv3 — See LICENSE file for full terms.
Author: John Plocher
