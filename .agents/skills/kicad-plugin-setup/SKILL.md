---
name: kicad-plugin-setup
description: Register and run jBOM as a KiCad Eeschema BOM plugin. Use when an end user wants to set up kicad_jbom_plugin.py in KiCad's "Tools → Generate BOM → Add plugin" dialog, or when running the plugin interactively from Eeschema.
---

# kicad-plugin-setup

How to register and use jBOM as a BOM plugin in KiCad's Eeschema.

## When to use

Use this skill when setting up `kicad_jbom_plugin.py` in KiCad so that
**Tools → Generate BOM** invokes jBOM without leaving the schematic editor.
For the developer workflow (working on the plugin source itself), see the
[plugin-dev-setup skill](../plugin-dev-setup/SKILL.md).

For a reference of command syntax, output columns, and custom fabricator
configuration, see [docs-new/reference/kicad-plugin.md](../../../docs-new/reference/kicad-plugin.md).

## Prerequisites

- Python 3.10 or newer installed and accessible as `python3`
- jBOM installed: `pip install jbom`
- `kicad_jbom_plugin.py` on disk at a stable, absolute path
- An inventory file (`.csv`, `.xlsx`, or `.numbers`) prepared for your project

Install optional packages for non-CSV inventory files:

```bash
pip install openpyxl       # for .xlsx / .xls
pip install numbers-parser # for .numbers
```

## Registering the plugin in Eeschema

1. Open your project in KiCad and launch **Eeschema** (the schematic editor).
2. Navigate to **Tools → Generate BOM**.
3. Click the **+** (Add plugin) button in the BOM dialog.
4. Enter a display name, for example: `jBOM`.
5. In the **Command line** field, enter the full invocation. Replace the
   placeholder paths with absolute paths on your machine:

   ```
   python3 /absolute/path/to/kicad_jbom_plugin.py %I --inventory /absolute/path/to/INVENTORY.xlsx -o %O
   ```

   KiCad substitutes `%I` with the current schematic path and `%O` with the
   output file path you choose at generation time. Both must be left exactly
   as-is in the command.

6. Click **OK** or **Save**. The `jBOM` entry now appears in the plugin list.

**Important:** use absolute paths for both the script and the inventory file.
The plugin is invoked from an unpredictable working directory, so relative
paths will not resolve correctly.

## Running the plugin

1. With your schematic open in Eeschema, open **Tools → Generate BOM**.
2. Select **jBOM** from the plugin list.
3. Choose an output filename in the file picker (for example,
   `MyProject_bom.csv`).
4. Click **Generate**.
5. Open the resulting CSV in a spreadsheet application or submit it directly
   to your fabricator.

## Choosing a fabricator

Append a fabricator flag to the command line in the plugin registration to
get fabricator-specific column layouts:

```
# JLCPCB (outputs the LCSC column JLCPCB requires)
python3 /path/to/kicad_jbom_plugin.py %I --inventory /path/to/inv.xlsx -o %O --jlc

# PCBWay
python3 /path/to/kicad_jbom_plugin.py %I --inventory /path/to/inv.xlsx -o %O --pcbway

# Seeed Studio Fusion
python3 /path/to/kicad_jbom_plugin.py %I --inventory /path/to/inv.xlsx -o %O --seeed

# Generic (default — broad supplier scope)
python3 /path/to/kicad_jbom_plugin.py %I --inventory /path/to/inv.xlsx -o %O --generic
```

You can register multiple plugin entries in Eeschema — one per fabricator —
if you submit to more than one manufacturer.

## Verbose mode

Add `-v` to the command line to include `Match_Quality` and `Priority`
columns in the output. These are useful when debugging unmatched components:

```
python3 /path/to/kicad_jbom_plugin.py %I --inventory /path/to/inv.xlsx -o %O -v
```

## Testing the plugin manually

If the plugin does not appear or generates an error, run it directly from
the terminal to see the full output:

```bash
python3 /absolute/path/to/kicad_jbom_plugin.py \
    /absolute/path/to/MyProject.kicad_sch \
    --inventory /absolute/path/to/inventory.xlsx \
    -o /tmp/test_bom.csv
```

A successful run writes the CSV and exits with code 0. Errors are printed to
stderr. Common causes of failure:

- Wrong path to `kicad_jbom_plugin.py` or the inventory file
- `python3` not on `PATH` as seen by KiCad (test by opening a terminal and
  running `python3 --version`)
- Missing optional dependency (`openpyxl` for Excel, `numbers-parser` for
  Numbers)

For a full troubleshooting guide, see the
[kicad-plugin reference](../../../docs-new/reference/kicad-plugin.md#troubleshooting).

## Iterative BOM generation

The typical iterative workflow when building up a new design:

1. Place components in Eeschema; set `Reference`, `Value`, and `Footprint`
   properties on each symbol.
2. Run jBOM via **Tools → Generate BOM → jBOM → Generate**.
3. Open the output CSV and identify unmatched components (blank part-number
   column or zero match quality with `-v`).
4. Add or correct inventory rows as needed.
5. Re-run BOM generation without leaving the schematic editor.

For CI or scripted BOM generation, invoke jBOM directly via the CLI
(`jbom bom`) rather than the plugin wrapper.
