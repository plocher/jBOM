# jBOM — KiCad Bill of Materials and Placement Generator

## Why jBOM?

Designing a PCB in KiCad is only half the battle. Before you can manufacture your board, you need a **Bill of Materials (BOM)** and a **Placement file (CPL/POS)**.

Most BOM tools force you to hardcode specific part numbers (like "LCSC:C123456") directly into your KiCad symbols. This locks your design to specific vendors and makes it hard to manage out-of-stock parts or second sources.

**jBOM solves this** by separating part selection from circuit design. You design with generic values ("10kΩ resistor, 0603"), maintain a separate inventory file with your available parts, and jBOM intelligently matches them at BOM generation time.

## Installation
Requires Python 3.9 or newer.

**From PyPI (recommended):**

```bash
# Basic installation (CSV inventory support)
pip install jbom

# With Excel support
pip install jbom[excel]

# With Apple Numbers support
pip install jbom[numbers]

# With Mouser Search support
pip install jbom[search]

# Everything
pip install jbom[all]
```

## Quick Start - using the jBOM command
**Scenario: You have a project but no inventory file and wish to have JLC fabricate your design.**

Refer to the full command line documentation found in [docs/README.man1.md](docs/README.man1.md).

### 1. Start with an existing KiCad project

Run jBOM to extract a prototype inventory from the components used in your project:

```bash
jbom inventory --jlc MyProject/ -o my_new_inventory.csv
```

This creates a CSV file listing all the parts found in your schematics (Resistors, Capacitors, ICs, etc.) with their values and packages. Adding `--jlc` ensures the columns for JLCPCB part numbers are included.

### 2. Edit/Update your inventory

This new `my_new_inventory.csv` inventory is missing some fabrication details needed by JLC:

1.  Open the file in Excel, Numbers, or a text editor.
2.  **Crucial**: If your schematic symbols were generic, fill in the missing **Value** and **Package** columns now.
3.  Fill in the **LCSC** column (or **MFGPN**) for the parts you want to buy.
    *   **Pro Tip**: You can export your existing JLC private library into a file and load it alongside your project inventory: `jbom bom ... -i project_inv.csv -i jlc_private_lib.xlsx`
    *   **Export Instructions**: Login to JLCPCB -> User Center -> My Inventory -> My Parts Lib -> Click "Export".
    *   **Search**: Use `jbom search "part description" --provider mouser` to find parts.
4.  (Optional) Add your own parts from other sources (e.g., local stock).

### 3. Generate your BOM and Placement files

Now run jBOM to verify your inventory and generate the manufacturing files.

**Generate BOM:**
```bash
# BOM with JLCPCB-optimized columns
jbom bom --jlc MyProject/ -i my_new_inventory.csv
```

**Generate Placement (CPL):**
```bash
# Auto-detects PCB file in project directory
jbom pos --jlc MyProject/
```

**Generate Inventory:**
```bash
# Extract components to initial inventory
jbom inventory MyProject/ -o my_new_inventory.csv
```

**Search for Parts:**
```bash
# Search Mouser for parts
jbom search "10k 0603 resistor" --limit 5
```

### 4. (Optional) Back-Annotate to KiCad

If you updated component values or packages in your inventory CSV (Step 2), your schematic is now out of sync. You can push these changes back to KiCad to keep your schematic as the single source of truth.

```bash
jbom annotate MyProject/ -i my_new_inventory.csv
```

This updates your `.kicad_sch` files with the correct Value, Footprint, and LCSC part numbers found in your inventory.

## Quick Start - using the Python API

Refer to the full API documentation found in [docs/README.man3.md](docs/README.man3.md).

jBOM exposes a clean Python API for integrating into custom scripts or CI/CD pipelines.

```python
from jbom.api import generate_bom, generate_pos, back_annotate, BOMOptions, POSOptions

# Generate BOM
result = generate_bom(
    input='MyProject/',
    inventory='my_inventory.csv',
    options=BOMOptions(verbose=True)
)

# Generate Placement
pos_result = generate_pos(
    input='MyProject/',
    options=POSOptions(smd_only=True)
)

# Back-Annotate
anno_result = back_annotate(
    project='MyProject/',
    inventory='updated_inventory.csv',
    dry_run=True
)

# Search Parts
parts = search_parts(
    query="10k 0603 resistor",
    limit=5
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

## Configuration

jBOM uses a hierarchical configuration system that makes it easy to customize fabricator settings without hardcoding.

### Built-in Fabricators

jBOM includes built-in support for popular PCB fabricators:

```bash
# Use built-in fabricator configs
jbom bom project/ --jlc        # JLCPCB format
jbom bom project/ --pcbway     # PCBWay format
jbom bom project/ --seeed      # Seeed Studio format
```

### Configuration Hierarchy

Configurations load in order of precedence:

1. **Package Defaults**: Built-in configs (JLC, PCBWay, Seeed)
2. **System Configs**:
   - macOS: `/Library/Application Support/jbom/config.yaml`
   - Windows: `%PROGRAMDATA%\jbom\config.yaml`
   - Linux: `/etc/jbom/config.yaml`
3. **User Home**:
   - macOS: `~/Library/Application Support/jbom/config.yaml`
   - Windows: `%APPDATA%\jbom\config.yaml`
   - Linux: `~/.config/jbom/config.yaml`
4. **Project**: `.jbom/config.yaml` or `jbom.yaml` in project directory

### Customization

To customize a fabricator:

1. **Copy a built-in config**:
   ```bash
   # macOS
   mkdir -p "~/Library/Application Support/jbom/fabricators/"
   cp $(python -c "import jbom; print(jbom.__path__[0])")/config/fabricators/jlc.fab.yaml \
      "~/Library/Application Support/jbom/fabricators/myjlc.fab.yaml"

   # Linux
   mkdir -p ~/.config/jbom/fabricators/
   cp $(python -c "import jbom; print(jbom.__path__[0])")/config/fabricators/jlc.fab.yaml \
      ~/.config/jbom/fabricators/myjlc.fab.yaml

   # Windows (PowerShell)
   mkdir "$env:APPDATA\jbom\fabricators"
   cp (python -c "import jbom; print(jbom.__path__[0])")\config\fabricators\jlc.fab.yaml \
      "$env:APPDATA\jbom\fabricators\myjlc.fab.yaml"
   ```

2. **Edit your copy** (change BOM columns, part number priorities, etc.):
   ```yaml
   name: "My JLC Config"
   based_on: "jlc"  # Optional: inherit from built-in
   bom_columns:
     "Designator": "reference"
     "Comment": "value"        # Changed from "description"
     "LCSC": "fabricator_part_number"
   ```

3. **Add to your configuration**:
   ```yaml
   # In your OS-specific config file:
   # macOS: ~/Library/Application Support/jbom/config.yaml
   # Windows: %APPDATA%\jbom\config.yaml
   # Linux: ~/.config/jbom/config.yaml

   # Entries here are merged with the built-in defaults.
   # New IDs are added; existing IDs override the default.
   fabricators:
     - name: "myjlc"
       file: "fabricators/myjlc.fab.yaml"
   ```

4. **Use your custom config**:
   ```bash
   jbom bom project/ --myjlc
   ```

The `id` field in fabricator configs automatically generates CLI flags (`--{id}`) and presets (`+{id}`).

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

**jBOM v3.0.0** — Major architectural refactoring with data-flow architecture, federated inventory support, and KiCad integration.

**License**: AGPLv3 — See LICENSE file for full terms.
Author: John Plocher
