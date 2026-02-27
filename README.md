# jBOM — KiCad Bill of Materials and Placement Generator

## Why jBOM?

Designing a PCB in KiCad is only half the battle. Before you can manufacture your board, you need a **Bill of Materials (BOM)** and a **Placement file (CPL/POS)**.

Most BOM tools force you to hardcode specific part numbers (like "LCSC:C123456") directly into your KiCad symbols. This locks your design to specific vendors and makes it hard to manage out-of-stock parts or second sources.

**jBOM solves this** by separating part selection from circuit design. You design with generic values ("10kΩ resistor, 0603"), maintain a separate inventory file with your available parts, and jBOM intelligently matches them at BOM generation time.

## Installation
Requires Python 3.10 or newer.

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
jbom inventory MyProject/ -o my_new_inventory.csv
```

This creates a CSV file listing all the parts found in your schematics (Resistors, Capacitors, ICs, etc.) with their values and packages.

### 2. Edit/Update your inventory

This new `my_new_inventory.csv` inventory is missing some fabrication details needed by JLC:

1.  Open the file in Excel, Numbers, or a text editor.
2.  **Crucial**: If your schematic symbols were generic, fill in the missing **Value** and **Package** columns now.
3.  Fill in the **LCSC** column (or **MFGPN**) for the parts you want to buy.
    *   **Pro Tip**: You can export your existing JLC private library into a file and load it alongside your project inventory: `jbom bom ... --inventory project_inv.csv --inventory jlc_private_lib.xlsx`
    *   **Export Instructions**: Login to JLCPCB -> User Center -> My Inventory -> My Parts Lib -> Click "Export".
    *   **Search**: Use `jbom search "part description" --provider mouser` to find parts.
4.  (Optional) Add your own parts from other sources (e.g., local stock).

### 3. Generate your BOM and Placement files

Now run jBOM to verify your inventory and generate the manufacturing files.

**Generate BOM:**
```bash
# BOM with JLCPCB-optimized columns
jbom bom MyProject/ --jlc --inventory my_new_inventory.csv

# Or from within the project directory (defaults to current directory)
cd MyProject
jbom bom --jlc --inventory my_new_inventory.csv
```

**Generate Placement (CPL):**
```bash
# Auto-detects PCB file in project directory
jbom pos MyProject/ --jlc

# Or from within the project directory
cd MyProject
jbom pos --jlc

# Can also pass .kicad_sch - auto-swaps to matching .kicad_pcb
jbom pos MyProject.kicad_sch --jlc
```

**Generate Inventory:**
```bash
# Extract components to initial inventory
jbom inventory MyProject/ -o my_new_inventory.csv
```

**Generate Parts List** (one row per component, no aggregation):
```bash
jbom parts MyProject/ -o parts.csv
```

**Search for Parts:**
```bash
jbom search "10k 0603 resistor" --limit 5
```

**Bulk Inventory Search** (find supplier part numbers for your inventory):
```bash
export MOUSER_API_KEY=your_api_key
jbom inventory-search my_new_inventory.csv -o enriched.csv
```

> **Note:** The `annotate` command (back-annotate schematics from inventory) is available in `legacy/` and is planned for v8.x.

## Quick Start - integrating into KiCad

Refer to the full plugin documentation found in [docs/README.man4.md](docs/README.man4.md).

You can run jBOM directly from KiCad's **Generate BOM** dialog:

1.  In KiCad Eeschema, go to `Tools` → `Generate BOM`.
2.  Add a new plugin with the command:
    ```
    python3 /path/to/kicad_jbom_plugin.py "%I" --inventory /path/to/inventory.csv -o "%O" --jlc
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

- [**docs/README.man1.md**](docs/README.man1.md) — CLI reference (all 6 commands)
- [**docs/README.man3.md**](docs/README.man3.md) — Python library API (planned for v8.x)
- [**docs/README.man4.md**](docs/README.man4.md) — KiCad plugin setup
- [**docs/README.man5.md**](docs/README.man5.md) — Inventory file format
- [**docs/README.developer.md**](docs/README.developer.md) — Technical architecture

## Contributing

Contributions are welcome! jBOM is developed on GitHub at [github.com/plocher/jBOM](https://github.com/plocher/jBOM).

To contribute:
1. Fork the repository
2. Create a feature branch
3. Run tests: `pytest && python -m behave --format progress`
4. Submit a pull request

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for details.

**License**: AGPLv3 — See LICENSE file for full terms.
Author: John Plocher
