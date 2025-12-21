# jBOM Configuration System

## Overview

jBOM uses a hierarchical YAML-based configuration system that allows complete customization of fabricator settings, BOM formats, and part number priorities without hardcoding.

## Configuration Hierarchy

Configurations are loaded in order of precedence (later configs override earlier ones):

1. **Package Defaults**: Built-in configs distributed with jBOM
   - Location: `<jbom-package>/config/defaults.yaml`
   - Contains: JLC, PCBWay, Seeed, Generic fabricators

2. **System Configs**: System-wide settings (rare)
   - macOS: `/Library/Application Support/jbom/config.yaml`
   - Windows: `%PROGRAMDATA%\jbom\config.yaml` (e.g., `C:\ProgramData\jbom\config.yaml`)
   - Linux: `/etc/jbom/config.yaml` or `/usr/local/etc/jbom/config.yaml`

3. **User Home Configs**: Personal user settings
   - macOS: `~/Library/Application Support/jbom/config.yaml`
   - Windows: `%APPDATA%\jbom\config.yaml` (e.g., `C:\Users\{username}\AppData\Roaming\jbom\config.yaml`)
   - Linux: `~/.config/jbom/config.yaml` (XDG) or `~/.jbom/config.yaml` (legacy)

4. **Project Configs**: Project-specific overrides
   - Location: `.jbom/config.yaml` or `jbom.yaml` in project directory
   - Use for: Project-specific fabricator preferences

## Configuration Replacement Behavior

jBOM uses a **REPLACE** strategy for dictionary fields and list items (like component classifiers) within a configuration. This is critical for allowing users to remove unwanted defaults.

### Fabricator Configuration
When you define an override for a fabricator (same `id`), the following fields are **fully replaced**, not merged key-by-key:
- `bom_columns`
- `pos_columns`
- `part_number`
- `pcb_manufacturing`
- `pcb_assembly`

**Example:**
If the default JLC config has 10 columns, and you define a `bom_columns` section with just 2 columns in your override, the resulting BOM will have **only those 2 columns**. The default columns are discarded.

### Component Classifiers
When you define a component classifier with the same `type` as a built-in one (e.g., `type: "LED"`), your definition **fully replaces** the built-in one.

This means you must include *all* rules you want to apply for that type, including the default ones if you still want them.

## Configuration File Format

### Main Configuration File

```yaml
version: "3.0.0"
schema_version: "2025.12.20"

metadata:
  description: "My custom jBOM configuration"
  author: "John Doe"

# Reference external fabricator files
fabricators:
  - name: "jlc"
    file: "fabricators/jlc.fab.yaml"

  - name: "myjlc"
    file: "fabricators/myjlc.fab.yaml"

  # Inline fabricator definition
  - name: "Custom Fab"
    id: "customfab"
    description: "My custom fabricator"
    part_number:
      header: "Custom P/N"
      priority_fields:
        - "CUSTOM"
        - "MPN"
    bom_columns:
      "Part": "reference"
      "Custom P/N": "fabricator_part_number"

global_presets:
  minimal:
    description: "Minimal BOM fields"
    fields:
      - "reference"
      - "quantity"
      - "description"

component_classifiers:
  - type: "RES"
    rules:
      - "lib_id contains resistor"
      - "footprint contains res"
  - type: "LED"
    rules:
      - "lib_id contains led"
      # Add custom rule for WS2812 which might not match "led"
      - "lib_id contains ws2812"
```

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

## File Organization

### Recommended Structure

**macOS:**
```
~/Library/Application Support/jbom/
├── config.yaml              # Main config file
└── fabricators/
    ├── myjlc.fab.yaml       # Custom JLC config
    ├── mypcbway.fab.yaml    # Custom PCBWay config
    └── company.fab.yaml     # Company-specific config
```

**Windows:**
```
%APPDATA%\jbom\
├── config.yaml              # Main config file
└── fabricators\
    ├── myjlc.fab.yaml       # Custom JLC config
    ├── mypcbway.fab.yaml    # Custom PCBWay config
    └── company.fab.yaml     # Company-specific config
```

**Linux:**
```
~/.config/jbom/
├── config.yaml              # Main config file
└── fabricators/
    ├── myjlc.fab.yaml       # Custom JLC config
    ├── mypcbway.fab.yaml    # Custom PCBWay config
    └── company.fab.yaml     # Company-specific config
```

### Project-Specific Configs

```
MyProject/
├── MyProject.kicad_pro
├── MyProject.kicad_sch
├── jbom.yaml               # Project config (option 1)
└── .jbom/
    ├── config.yaml         # Project config (option 2)
    └── fabricators/
        └── project.fab.yaml
```

## Environment Variables

- `JBOM_CONFIG_DIR`: Override config directory location
- `JBOM_CONFIG_FILE`: Override config file path

## Troubleshooting

### Config Loading Issues

```bash
# Debug config loading
jbom bom --debug project/

# Check what fabricators are loaded
python -c "from jbom.common.config import get_config; c=get_config(); print([f.name for f in c.fabricators])"
```

### Validation Errors

- **Missing required fields**: Fabricator configs must have `name` field minimum
- **Invalid YAML**: Use a YAML validator to check syntax
- **File not found**: Check file paths in `file:` references
- **Circular inheritance**: `based_on` cannot create loops

### CLI Flag Conflicts

- Fabricator `id` values must be unique
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
