# KiCad plugin reference

The jBOM KiCad plugin is a thin wrapper script (`kicad_jbom_plugin.py`) that
bridges KiCad's Eeschema BOM-generation interface to the `jbom bom` subcommand.
It supports the same fabricator flags, field presets, and inventory files as the
CLI. For setup instructions (registering the plugin in Eeschema), see the
[kicad-plugin-setup skill](../../.agents/skills/kicad-plugin-setup/SKILL.md).

## Command syntax

```
python3 /absolute/path/to/kicad_jbom_plugin.py SCHEMATIC \
    --inventory INVENTORY \
    -o OUTPUT \
    [--jlc | --pcbway | --seeed | --generic] \
    [-f FIELDS] \
    [-v]
```

`SCHEMATIC` — path to the `.kicad_sch` file (KiCad supplies this as `%I`
at runtime when the plugin is invoked from the Generate BOM dialog).

`--inventory INVENTORY` — path to an inventory file (`.csv`, `.xlsx`,
`.xls`, or `.numbers`). May be specified multiple times to merge inventory
sources. Use an absolute path; the plugin is invoked from an unpredictable
working directory.

`-o OUTPUT` — output CSV path (KiCad supplies this as `%O` at runtime).

`-f FIELDS` — field selection. Accepts a field preset (`+standard`,
`+jlc`, `+minimal`, `+all`) or a comma-separated list of field names.

`-v` — verbose mode; adds `Match_Quality` and `Priority` columns to the
output, useful for diagnosing unmatched components.

## Fabricator flags

Each flag selects a built-in fabricator profile that controls the output
column set, the part-number resolution strategy, and the CPL rotation range.

`--jlc` — JLCPCB. Prioritises LCSC/SPN part numbers; outputs the column
set JLCPCB's upload portal expects.

`--pcbway` — PCBWay. Prioritises manufacturer part numbers; uses the
PCBWay BOM upload format.

`--seeed` — Seeed Studio Fusion. Uses Seeed's upload format.

`--generic` — Generic. Broad supplier scope; outputs manufacturer
and part-number columns suitable for quoting. This is the default when no
fabricator flag is provided.

Profiles can also be specified by name with `--fabricator <id>` when the
built-in shortcut flags are insufficient (e.g. for a custom profile id).

## Output columns

Column sets below reflect the built-in profile configurations. All columns
are configurable; see [Custom fabricator configuration](#custom-fabricator-configuration).

**Generic (default)**

| Column | Source |
|---|---|
| Reference | schematic reference designators |
| Quantity | aggregate count |
| Description | component description |
| Value | component value |
| Package | package code |
| Footprint | KiCad footprint path |
| Manufacturer | manufacturer name from inventory |
| Part Number | resolved fabricator part number (Supplier+SPN) |

**JLC (`--jlc`)**

| Column | Source |
|---|---|
| Designator | schematic reference designators |
| Quantity | aggregate count |
| Value | component value |
| Comment | component description |
| Footprint | KiCad footprint path |
| LCSC | resolved part number — required column name for JLCPCB upload |
| Surface Mount | SMD flag |

Note: The output column is named `LCSC` because that is the column header
JLCPCB's upload portal requires. The value is resolved from the inventory's
`Supplier`+`SPN` fields (or the legacy `LCSC` column; see
[Inventory file requirements](#inventory-file-requirements)).

**PCBWay (`--pcbway`)**

| Column | Source |
|---|---|
| Designator | schematic reference designators |
| Quantity | aggregate count |
| Value | component value |
| Comment | component description |
| Package | package code (from inventory) |
| Manufacturer Part Number | resolved fabricator part number |

**Seeed Studio (`--seeed`)**

| Column | Source |
|---|---|
| Designator | schematic reference designators |
| Quantity | aggregate count |
| Value | component value |
| Package | package code (from inventory) |
| Seeed Part Number | resolved fabricator part number |

## Inventory file requirements

jBOM matches schematic components against the inventory file and resolves a
fabricator part number for each line in the BOM. The inventory must contain
at minimum:

- **IPN** — Internal Part Number; unique identifier for each stock item.
- **Category** — component classification (`RES`, `CAP`, `IC`, `CON`, etc.).
- **Value** — component value in appropriate units.
- **Package** — physical package code (`0603`, `SOT-23`, etc.).
- **Priority** — integer ranking (1 = preferred). Controls which candidate
  wins when multiple inventory rows match the same schematic component.

Supply-chain identity uses the `Supplier`+`SPN` column pair. The legacy
`LCSC` column is still accepted for backward compatibility but is deprecated;
new inventories should use `Supplier` and `SPN` instead:

```
Supplier=lcsc, SPN=C25231  →  equivalent to legacy: LCSC=C25231
Supplier=mouser, SPN=652-CR0603FX-1002ELF  →  Mouser part number
```

When `--jlc` is selected, the resolved `SPN` for supplier `lcsc` becomes the
value in the output `LCSC` column. Parts without an LCSC SPN are left blank;
JLCPCB treats blank `LCSC` entries as consigned parts.

For complete column definitions including optional matching attributes
(`Tolerance`, `Voltage`, `Current`, etc.), see the
[inventory file format reference](./inventory-format.md).

## Custom fabricator configuration

Custom fabricator profiles are `*.jbom.yaml` files placed in any directory
on the profile search path. jBOM resolves profiles using this search order
(highest priority first):

1. `<cwd>/.jbom/`
2. `<repo_root>/.jbom/` (detected by presence of `pyproject.toml` or `.git`)
3. `$JBOM_PROFILE_PATH` entries (colon-separated list of directories)
4. `~/.jbom/`
5. Platform system directory
6. Built-in package configuration

A custom fabricator defined in `~/.jbom/myfab.jbom.yaml` is available as
`--fabricator myfab` in any project. A project-level override in
`<project>/.jbom/myfab.jbom.yaml` takes precedence over the user-level file.

```yaml
# ~/.jbom/myfab.jbom.yaml
extends: generic
fab:
  name: "My Fab"
  id: "myfab"
  description: "Custom fabricator configuration"
  part_number:
    header: "Custom Part Number"
  bom_columns:
    "Reference": "reference"
    "Qty": "jbom:quantity"
    "Custom Part Number": "jbom:fabricator_part_number"
```

For merge semantics, the `extends:` key, and the `common.jbom.yaml`
accumulation model, see [Configuration semantics](../design/configuration-semantics.md)
and [ADR 0008](../architecture/adr/0008-unified-jbom-config-schema.md).

## Plugin installation

jBOM's KiCad integration — both the Pcbnew ActionPlugin (toolbar
button) and the Eeschema BOM-plugin wrapper (`kicad_jbom_plugin.py`)
— is intended to be installed through KiCad's **Plugin and Content
Manager (PCM)**. PCM is the recommended and supported install path:
it handles version upgrades, uninstalls, and dependency tracking, and
it places the package in the correct platform-specific directory
automatically:

| Platform | PCM install directory |
|---|---|
| **macOS** | `~/Library/Preferences/kicad/<ver>/scripting/plugins/` |
| **Linux** | `~/.local/share/kicad/<ver>/scripting/plugins/` |
| **Windows** | `%APPDATA%\kicad\<ver>\scripting\plugins\` |

`<ver>` is the KiCad major.minor version (`9.0`, `10.0`, etc.). The
above paths are informational — users should not need to copy or move
files into these directories themselves. See the
[plugin-dev-setup skill](../../.agents/skills/plugin-dev-setup/SKILL.md)
for the jBOM PCM package layout (how the ActionPlugin and BOM-plugin
wrapper are bundled together).

After PCM installs the package, the Pcbnew toolbar button appears
automatically. The Eeschema BOM plugin requires a one-time
registration via **Eeschema → Tools → Generate BOM → Add plugin**
pointing at the PCM-installed `kicad_jbom_plugin.py`; KiCad's BOM
dialog does not auto-discover plugins. See the
[kicad-plugin-setup skill](../../.agents/skills/kicad-plugin-setup/SKILL.md)
for the dialog walkthrough.

Manual filesystem placement (cloning the repo, copying the script
by hand, or `pip install`'ing the wrapper to an arbitrary path) is
supported for development workflows and edge cases, but is not the
recommended path for end users.

## Environment requirements

- Python 3.10 or newer
- `sexpdata` — S-expression parser for `.kicad_sch` files (`pip install sexpdata`)
- `openpyxl` — optional; required for `.xlsx`/`.xls` inventory files
- `numbers-parser` — optional; required for `.numbers` inventory files

## Troubleshooting

**Plugin does not appear in the Generate BOM list**

Verify that the path to `kicad_jbom_plugin.py` in the registered command is
correct and that Python 3 is accessible from the command line. Test manually:

```bash
python3 /path/to/kicad_jbom_plugin.py /path/to/test.kicad_sch \
    --inventory /path/to/inventory.csv \
    -o /tmp/test_bom.csv
```

**"Inventory file not found"**

Use absolute paths in the plugin command. Relative paths are resolved from
an unpredictable working directory when KiCad invokes the plugin.

**"No .kicad_sch file found"**

Save the schematic in Eeschema before generating the BOM. KiCad must have
written the `.kicad_sch` file to disk before it can be passed to the plugin.

**"Excel support requires openpyxl"** / **"Numbers support requires numbers-parser"**

Install the optional dependency for the inventory format you are using:

```bash
pip install openpyxl       # for .xlsx / .xls
pip install numbers-parser # for .numbers
```

**BOM is empty or components are unmatched**

Run with `-v` to expose `Match_Quality` and `Priority` columns in the
output. Unmatched rows will have blank part-number columns. Common causes:

- `Category` in inventory does not match jBOM's detected category for the
  schematic component (check the `kicad-best-practices` reference for
  category routing signal conventions).
- `Value` format is inconsistent — jBOM normalises units (`10k`, `10K`,
  `10000R` all resolve to 10 kΩ), but spelling must be compatible.
- `Package` mismatch — jBOM extracts the package code from the KiCad
  footprint name; verify against the [kicad-best-practices](./kicad-best-practices.md)
  footprint-to-package mapping rules.

**Hierarchical schematics with missing components**

jBOM automatically detects and processes hierarchical sheets. All
sub-sheet `.kicad_sch` files must be in the same directory as the
top-level schematic or otherwise correctly referenced.

**Debug output not visible in KiCad**

Debug and error messages go to `stderr`. KiCad captures `stdout` for the
BOM output but may display `stderr` in the Eeschema console. Run the
plugin manually from the terminal to see all output.
