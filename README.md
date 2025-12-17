# jBOM — KiCad Bill of Materials and Placement Generator

## Why jBOM?

Designing a PCB in KiCad is only half the battle. Before you can manufacture your board, you need a **Bill of Materials (BOM)** and a **Placement file (CPL/POS)**.

Most BOM tools force you to hardcode specific part numbers (like "LCSC:C123456") directly into your KiCad symbols. This locks your design to specific vendors and makes it hard to manage out-of-stock parts or second sources.

**jBOM solves this** by separating part selection from circuit design. You design with generic values ("10kΩ resistor, 0603"), maintain a separate inventory file with your available parts, and jBOM intelligently matches them at BOM generation time.

## Quick Start - using the jBOM command

Refer to the full command line documentation found in [docs/README.man1.md](docs/README.man1.md).

### 1. Start with an existing KiCad project

**Scenario: You have a project but no inventory file.**

Run jBOM to extract a prototype inventory from the components used in your project:

```bash
jbom inventory MyProject/ -o my_new_inventory.csv --jlc
```

This creates a CSV file listing all the parts found in your schematics (Resistors, Capacitors, ICs, etc.) with their values and packages. Adding `--jlc` ensures the columns for JLCPCB part numbers are included.

### 2. Edit/Update your inventory

Now that you have a prototype inventory file (`my_new_inventory.csv`), you must fill in the missing details:

1.  Open the file in Excel, Numbers, or a text editor.
2.  **Crucial**: If your schematic symbols were generic (e.g. no value), fill in the **Value** and **Package** columns now.
3.  Fill in the **LCSC** column (or **MFGPN**) for the parts you want to buy.
4.  (Optional) Add a **Priority** (1 = preferred) if you have multiple options for the same part.
4.  (Optional) Add your own parts from other sources (e.g., local stock).

### 3. Generate your BOM and Placement files

Now run jBOM to verify your inventory and generate the manufacturing files.

**Generate BOM:**
```bash
# Basic BOM
jbom bom MyProject/ -i my_new_inventory.csv

# BOM with JLCPCB-optimized columns
jbom bom MyProject/ -i my_new_inventory.csv --jlc
```

**Generate Placement (CPL):**
```bash
# Auto-detects PCB file in project directory
jbom pos MyProject/ --jlc
```

**Verify/Audit:**
If you have multiple inventory sources (e.g., local stock + JLC parts), you can check them all:
```bash
jbom bom MyProject/ -i local_parts.csv -i my_new_inventory.csv
```

## Quick Start - using the Python API

Refer to the full API documentation found in [docs/README.man3.md](docs/README.man3.md).

jBOM exposes a clean Python API for integrating into custom scripts or CI/CD pipelines.

```python
from jbom.api import generate_bom, BOMOptions

result = generate_bom(
    input='MyProject/',
    inventory='my_inventory.csv',
    options=BOMOptions(verbose=True)
)
```

## Quick Start - integrating into KiCad

Refer to the full plugin documentation found in [docs/README.man4.md](docs/README.man4.md).

You can run jBOM directly from KiCad's **Generate BOM** dialog:

1.  In KiCad Eeschema, go to `Tools` → `Generate BOM`.
2.  Add a new plugin with the command:
    ```
    python3 /path/to/kicad_jbom_plugin.py "%I" -i /path/to/inventory.csv -o "%O" --jlc
    ```
3.  Click `Generate`.

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

## Documentation

Detailed documentation is available in the `docs/` directory:

- [**docs/README.man1.md**](docs/README.man1.md) — CLI reference
- [**docs/README.man3.md**](docs/README.man3.md) — Python library API
- [**docs/README.man4.md**](docs/README.man4.md) — KiCad plugin setup
- [**docs/README.man5.md**](docs/README.man5.md) — Inventory file format
- [**docs/README.developer.md**](docs/README.developer.md) — Technical architecture

## Contributing

Contributions are welcome! jBOM is developed on GitHub at [github.com/plocher/jBOM](https://github.com/plocher/jBOM).

To contribute:
1. Fork the repository
2. Create a feature branch
3. Run tests: `python -m unittest discover -s tests -v`
4. Submit a pull request

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for details.

## Version & License

**jBOM v3.0.0** — Major architectural refactoring with data-flow architecture, federated inventory support, and KiCad integration.

**License**: AGPLv3 — See LICENSE file for full terms.
Author: John Plocher
