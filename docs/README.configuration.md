# jBOM Configuration System

## Overview

jBOM uses YAML profile files to configure fabricator formats, supplier connections, and electrical defaults. There is no global config file to maintain — each profile type is resolved independently by name, using the same search path.

## Profile Types

There are three kinds of profiles:

| Profile type | File suffix | Selects | CLI flag |
|---|---|---|---|
| Fabricator | `*.fab.yaml` | BOM/CPL column names, part-number field order | `--fabricator NAME` or `--jlc`, `--pcbway`, etc. |
| Supplier | `*.supplier.yaml` | API endpoint, rate limits, authentication | (internal, no CLI flag yet) |
| Defaults | `*.defaults.yaml` | Electrical defaults for parametric search | (auto-loaded from search path) |

Built-in profiles (always present):
- Fabricators: `jlc`, `pcbway`, `seeed`, `generic`
- Supplier: `lcsc`
- Defaults: `generic`

## Profile Search Path

All three profile types use the same 6-level search path, checked in order (first match wins):

1. `<project>/.jbom/` — project-local, highest priority
2. `<repo-root>/.jbom/` — for monorepos: nearest ancestor directory containing `.git/`
3. Directories in `JBOM_PROFILE_PATH` env var — colon-separated, left to right
4. `~/.jbom/` — personal per-user overrides
5. Platform system directory:
   - macOS: `~/Library/Application Support/jBOM/`
   - Linux: `/usr/local/share/jBOM/` or `/etc/jBOM/`
   - Windows: `%LOCALAPPDATA%\jBOM\`
6. Built-in package directory — factory defaults, always present

Example: if you put `jlc.fab.yaml` in `MyBoard/.jbom/`, that file is used instead of the built-in JLC profile when running from `MyBoard/`.

## Inheritance and Merge Behaviour

### Fabricator profiles: `based_on` field replacement

Fabricator profiles use a **replace** strategy. When you define `based_on: "jlc"` and supply a `bom_columns` section, your section **fully replaces** the parent's `bom_columns`. You must include every column you want — omitted keys are not inherited from the parent.

Fields replaced in their entirety:
- `bom_columns`
- `pos_columns`
- `part_number`
- `pcb_manufacturing`
- `pcb_assembly`

### Defaults profiles: `extends` deep-merge

Defaults profiles use a **deep-merge** strategy. When you supply `extends: generic`, each dict section you include is recursively merged with the parent — only the keys you provide are overridden. Everything you omit is inherited as-is.

Exception: list-valued sections (e.g., `parametric_query_fields`) are **replaced** entirely if you include them — you cannot append to a list, only substitute it.

## Fabricator Profile File Format

### Fabricator Configuration File

Each fabricator can be defined in a separate `.fab.yaml` file:

```yaml
# jlc.fab.yaml
name: "JLCPCB"
id: "jlc"  # Generates --jlc flag and +jlc preset
description: "JLCPCB Fabrication Definitions"

# PCB manufacturing info (optional)
pcb_manufacturing:
  website: "https://jlcpcb.com/help/article/Suggested-Naming-Patterns"
  kicad_dru: "https://github.com/labtroll/KiCad-DesignRules/blob/main/JLCPCB/JLCPCB.kicad_dru"
  gerbers: "kicad"

# PCB assembly info (optional)
pcb_assembly:
  website: "https://jlcpcb.com/help/article/bill-of-materials-for-pcb-assembly"

# Part number matching configuration
part_number:
  header: "fabricator_part_number"  # Internal jBOM field name
  priority_fields:  # Search order (first found wins)
    - "LCSC"
    - "LCSC Part"
    - "LCSC Part #"
    - "JLC"
    - "JLC Part"
    - "JLC Part #"
    - "JLC PCB"
    - "JLC PCB Part"
    - "JLC_PCB Part #"
    - "MPN"
    - "MFGPN"

# BOM column mapping (BOM Header: jBOM internal field)
bom_columns:
  "Designator": "reference"
  "Comment": "description"
  "Footprint": "i:package"           # i: prefix for inventory fields
  "LCSC": "fabricator_part_number"
  "Surface Mount": "smd"
```

## Configuration Inheritance

### based_on Pattern

Create custom fabricators that inherit from existing ones:

```yaml
# myjlc.fab.yaml
name: "My JLC Config"
description: "John's customized JLCPCB configuration"
based_on: "jlc"  # Inherit from built-in JLC config

# Override specific fields
bom_columns:
  "Designator": "reference"
  "Comment": "value"        # Changed from "description"
  "Package": "i:package"    # Changed from "Footprint"
  "LCSC": "fabricator_part_number"
  "Surface Mount": "smd"
  "Notes": "notes"          # Added custom column
```

The `based_on` field:
1. Loads the base configuration first
2. Overlays your changes on top
3. Provides simple copy-paste-edit workflow

## Dynamic CLI Flag Generation

Fabricator configs automatically generate CLI interface:

```yaml
# In your fabricator config:
name: "My Custom Fab"
id: "mycustom"  # This creates:
                # - CLI flag: --mycustom
                # - Preset: +mycustom
```

Usage:
```bash
jbom bom project/ --mycustom        # Use fabricator
jbom bom project/ -f +mycustom      # Use as preset
```

## Field System

jBOM uses a sophisticated field system to map between different data sources:

### Field Prefixes
- **`reference`**: Component reference (R1, C2, U1)
- **`i:package`**: Inventory field (from inventory file)
- **`c:tolerance`**: Component field (from schematic)
- **`fabricator_part_number`**: Computed field (from part number matching)

### Part Number Matching

The `priority_fields` list defines search order:

```yaml
part_number:
  header: "fabricator_part_number"
  priority_fields:
    - "LCSC"        # Check inventory "LCSC" column first
    - "LCSC Part"   # Then "LCSC Part" column
    - "MPN"         # Then manufacturer part number
    - "MFGPN"       # Finally generic manufacturer P/N
```

**Note:** Part number lookup operates exclusively on the matched **Inventory Item**. It does not have access to the schematic Component, so it cannot retrieve `C:` (Component) properties.
- **Do not use `C:` prefix** in `priority_fields` (it will be ignored with a warning).
- **`I:` prefix is supported** but optional (e.g., `I:LCSC` works same as `LCSC`).

This flexibility allows your inventory to use different column names while still working with fabricator-specific BOM formats.

## Common Customization Patterns

### 1. Change BOM Column Names

```yaml
# Different fabricator, different column names
bom_columns:
  "Part Number": "reference"      # Instead of "Designator"
  "Description": "value"          # Instead of "Comment"
  "Mfg P/N": "mfgpn"             # Add manufacturer part number
```

### 2. Add Custom Columns

```yaml
bom_columns:
  # Standard columns
  "Designator": "reference"
  "LCSC": "fabricator_part_number"

  # Custom additions
  "Tolerance": "i:tolerance"      # From inventory
  "Datasheet": "datasheet"        # From components
  "Notes": "notes"                # Custom field
```

### 3. Modify Part Number Search

```yaml
part_number:
  header: "fabricator_part_number"
  priority_fields:
    - "CompanyXYZ"      # Check your custom field first
    - "LCSC"            # Fallback to standard
    - "MPN"
```

### 4. Multiple Custom Fabricators

```yaml
fabricators:
  - name: "jlc_basic"
    based_on: "jlc"
    bom_columns:
      "Designator": "reference"
      "Qty": "quantity"
      "LCSC": "fabricator_part_number"

  - name: "jlc_detailed"
    based_on: "jlc"
    bom_columns:
      "Designator": "reference"
      "Qty": "quantity"
      "Value": "value"
      "Package": "i:package"
      "Manufacturer": "manufacturer"
      "MPN": "mfgpn"
      "LCSC": "fabricator_part_number"
      "Datasheet": "datasheet"
```

## File Organisation

### Project-local profiles

The simplest way to add a custom profile is to put it directly in `.jbom/` in your project directory. No configuration needed — jBOM finds it automatically.

```
MyProject/
├── MyProject.kicad_pro
├── MyProject.kicad_sch
└── .jbom/
    ├── acmefab.fab.yaml          # custom fabricator
    └── precision.defaults.yaml   # tighter tolerances
```

With this layout, `jbom bom MyProject/ --acmefab` resolves `acmefab.fab.yaml` from `.jbom/`.

### Personal profiles (apply to all your projects)

```
~/.jbom/
├── acmefab.fab.yaml          # available everywhere
└── generic.defaults.yaml     # overrides the factory defaults
```

### Team / organisation profiles (`JBOM_PROFILE_PATH`)

```bash
export JBOM_PROFILE_PATH=/shared/jbom-profiles
```

```
/shared/jbom-profiles/
├── aerospace.defaults.yaml
├── automotive.defaults.yaml
├── acmefab.fab.yaml
└── lcsc.supplier.yaml
```

All users with `JBOM_PROFILE_PATH` set find these profiles without any per-project setup. Use a colon-separated list for multiple directories:
```bash
export JBOM_PROFILE_PATH=/shared/jbom-profiles:/opt/jbom-legacy-profiles
```

## Defaults Profile File Format

File name: `<name>.defaults.yaml`
Merge strategy: `extends:` deep-merge (see above)

```yaml
extends: generic   # optional: inherit from this profile

# Electrical defaults by component category (used by parametric search)
domain_defaults:
  resistor:
    tolerance: "5%"      # default when no tolerance specified in schematic
  capacitor:
    tolerance: "10%"
    dielectric: "X7R"   # default when no dielectric specified

# SMD resistor power ratings by package
package_power:
  "0402": "63mW"
  "0603": "100mW"
  "0805": "125mW"
  "1206": "250mW"

# SMD capacitor voltage ratings by package
package_voltage:
  "0402": "10V"
  "0603": "25V"
  "0805": "50V"

# Search-scoring package tokens (used for package intent matching)
search:
  package_tokens: ["0201", "0402", "0603", "0805", "1206", "1210", "1812", "2010", "2512"]

# Attributes jBOM surfaces for Mode A interactive confirmation
enrichment_attributes:
  resistor:
    show_in_mode_a: [tolerance, power_rating, voltage_rating, technology]
    suppress: [pricing, stock, lead_time, eia_land_pattern, series]
  capacitor:
    show_in_mode_a: [tolerance, voltage_rating, dielectric]
    suppress: [pricing, stock, lead_time, eia_land_pattern, series]
```

See `src/jbom/config/defaults/generic.defaults.yaml` in the package for the full factory defaults.

## Environment Variables

- `JBOM_PROFILE_PATH`: Colon-separated list of directories to include in the profile search path (org/team shared library).

## Troubleshooting

### Profile not found

Check the search path jBOM is using:
```python
from jbom.config.profile_search import profile_search_dirs
for d in profile_search_dirs():
    print(d)
```
Verify your profile file name matches `<name>.<type>.yaml` exactly (e.g., `acmefab.fab.yaml`, not `acmefab.yaml`).

### Fabricator validation errors

- **Missing required fields**: Fabricator configs must have `name` field minimum
- **Invalid YAML**: Use a YAML validator to check syntax
- **Circular inheritance**: `based_on` cannot create loops

### CLI flag conflicts

- Fabricator `id` values must be unique across all loaded profiles
- CLI flags are auto-generated from `id` (e.g., `id: "test"` → `--test`)
- Avoid common flag names (`help`, `version`, etc.)

## Migration from Hardcoded Configs

### Before (v3.3 and earlier)
```bash
# Hardcoded fabricator flags
jbom bom project/ --jlc
```

### After (v3.4+)
```bash
# Same flags work (backward compatible)
jbom bom project/ --jlc

# But now configurable!
# 1. Copy built-in config
# 2. Customize it
# 3. Reference in your config
# 4. Use your custom flag
jbom bom project/ --myjlc
```

## Schema Versioning

Configuration files use semantic versioning:

- `version`: jBOM version that created the config
- `schema_version`: Configuration schema version (YYYY.MM.DD format)

Current schema: `2025.12.20`

## Advanced Topics

### Programmatic Config Generation

```python
from jbom.common.config import FabricatorConfig, JBOMConfig

# Create fabricator config programmatically
custom_fab = FabricatorConfig(
    name="My Fabricator",
    id="myfab",
    part_number={"header": "Custom P/N", "priority_fields": ["CUSTOM"]},
    bom_columns={"Part": "reference", "Custom P/N": "fabricator_part_number"}
)

# Use in config
config = JBOMConfig(fabricators=[custom_fab])
```

### Config Validation

```python
from jbom.common.config import ConfigLoader

loader = ConfigLoader()
try:
    config = loader.load_config()
    print(f"Loaded {len(config.fabricators)} fabricators")
except Exception as e:
    print(f"Config error: {e}")
```

## Examples

See `examples/` directory for complete configuration examples:
- `examples/user-config-example.yaml`: User customization patterns
- `src/jbom/config/defaults.yaml`: Package defaults reference
- `src/jbom/config/fabricators/*.fab.yaml`: Built-in fabricator configs
