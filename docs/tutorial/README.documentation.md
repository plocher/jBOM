# Tutorial 4: Customising for Your Workflow

The built-in fabricator profiles (jlc, pcbway, seeed) and the `generic` defaults profile work well for most projects. This tutorial shows you how to go beyond them:

- Create a custom fabricator profile with your own column names
- Create a defaults profile to set org-wide electrical assumptions
- Share profiles across a team with `JBOM_PROFILE_PATH`

## Part A: Custom fabricator profiles

### Why customise a fabricator profile?

Maybe you want to:
- Use different BOM column headers than the built-in JLC preset
- Add a custom column (e.g., your internal MPN field)
- Set up a house-specific fab that isn't JLCPCB, PCBWay, or Seeed

### Step A1: Create a project `.jbom/` directory

```bash
mkdir -p MyBoard/.jbom
```

Any profile file placed here takes precedence over the built-in profiles for this project.

### Step A2: Create a custom fabricator profile

Create `MyBoard/.jbom/acmefab.fab.yaml`:

```yaml
name: "Acme Fab"
id: "acmefab"          # becomes the --acmefab CLI flag
description: "Internal Acme fabrication format"
based_on: "jlc"       # inherit everything from the built-in JLC profile

# Override only the BOM columns
bom_columns:
  "Ref Des":    "reference"
  "Qty":        "quantity"
  "Part Value": "value"
  "Package":    "i:package"
  "LCSC":       "fabricator_part_number"
  "Internal PN": "mfgpn"    # extra column
```

`based_on: "jlc"` means you inherit the part-number priority list, PCB assembly settings, and everything else from the JLC profile — you only override what you change.

### Step A3: Use it

```bash
jbom bom MyBoard/ --acmefab --inventory inventory.csv
```

jBOM discovers `acmefab.fab.yaml` in `.jbom/` automatically. No configuration file needed.

### Step A4: Make it permanent for your personal setup

If you use the same fab profile across multiple projects, put it in your home directory instead:

```bash
mkdir -p ~/.jbom
copy MyBoard/.jbom/acmefab.fab.yaml ~/.jbom/
```

Now `--acmefab` works from any project directory.

### Fabricator profile fields reference

```yaml
name: "Display Name"
id: "cli-id"           # creates --cli-id flag
description: "..."
based_on: "jlc"        # optional: inherit from built-in profile

pcb_manufacturing:
  website: "https://..."
  gerbers: "kicad"

part_number:
  header: "fabricator_part_number"
  priority_fields:     # search these schematic fields in order
    - "LCSC"
    - "LCSC Part"
    - "MPN"

bom_columns:           # BOM header: jBOM internal field
  "Designator": "reference"
  "Qty":        "quantity"
  ...

pos_columns:           # CPL header: jBOM internal field
  "Designator": "reference"
  "Mid X":      "x"
  "Mid Y":      "y"
  ...
```

For a complete example, look at the built-in `jlc.fab.yaml`:
```bash
python -c "import jbom, pathlib; print(pathlib.Path(jbom.__file__).parent / 'config' / 'fabricators' / 'jlc.fab.yaml')"
```

---

## Part B: Defaults profiles

### Why customise a defaults profile?

The `generic` defaults profile sets conservative, widely-applicable values:
- Resistor tolerance: 5%
- Capacitor dielectric: X7R
- Package voltage/power ratings: consumer-grade

If your organisation designs to different standards — aerospace, automotive, high-precision — you should not have to specify these overrides on every single resistor in every schematic. A defaults profile captures your design culture in one place.

### Step B1: See what the generic profile contains

```bash
python -c "import jbom, pathlib; print(pathlib.Path(jbom.__file__).parent / 'config' / 'defaults' / 'generic.defaults.yaml')" | xargs cat
```

You will see sections like:
```yaml
domain_defaults:
  resistor:
    tolerance: "5%"
  capacitor:
    tolerance: "10%"
    dielectric: "X7R"

package_power:
  "0402": "63mW"
  "0603": "100mW"
  ...

package_voltage:
  "0402": "10V"
  "0603": "25V"
  ...
```

### Step B2: Create an overriding defaults profile

Create `MyBoard/.jbom/precision.defaults.yaml`:

```yaml
extends: generic        # inherit everything from the built-in generic profile

domain_defaults:
  resistor:
    tolerance: "1%"   # override: 1% for all resistors
  capacitor:
    tolerance: "5%"   # override: tighter cap tolerance
    dielectric: "C0G" # override: C0G/NP0 for precision
```

`extends: generic` performs a **deep merge**: every section you include overlays the parent; anything you omit stays as the parent value. You only write what changes.

List sections replace (not merge): if you override `package_power`, your list replaces the entire parent list rather than merging into it.

### Step B3: Use it

Currently defaults profiles are loaded automatically from the search path — jBOM picks up `precision.defaults.yaml` from `.jbom/` and uses it for the parametric search queries in `jbom inventory-search`.

> **Note**: An explicit `--defaults <name>` CLI flag is planned for a future release. For now, the profile is selected by placing it in the search path with the name `generic.defaults.yaml` to override the factory defaults, or by using a custom name in `.jbom/` for project-local overrides.

### Step B4: Share profiles across a team

For a team or organisation, you want everyone to use the same defaults without checking profiles into every project repo. Use `JBOM_PROFILE_PATH`:

```bash
# Set in your shell profile (or in a CI environment variable)
export JBOM_PROFILE_PATH=/shared/jbom-profiles
```

Put your profiles in that directory:
```
/shared/jbom-profiles/
├── aerospace.defaults.yaml   # 1% resistors, C0G caps
├── automotive.defaults.yaml  # AEC-Q ratings
└── acmefab.fab.yaml           # house fab profile
```

All engineers with `JBOM_PROFILE_PATH` pointing to the shared directory automatically get these profiles. No file copying, no checking profiles into individual repos.

The full search path (highest to lowest priority):
```
<project>/.jbom/        project-local (committed or gitignored)
<repo-root>/.jbom/      monorepo shared
$JBOM_PROFILE_PATH      org library (colon-separated dirs)
~/.jbom/                personal
<platform system dir>   IT-managed
<jbom package>          factory built-ins (always present)
```

### Step B5: Verify which profiles are active

To see which profile files jBOM would find for a given name:

```python
from jbom.config.profile_search import profile_search_dirs
for d in profile_search_dirs():
    print(d)
```

---

## Summary

You now have the full jBOM toolkit:

1. **Generate inventory** from your schematic (`jbom inventory`)
2. **Enrich it** with part numbers (`jbom search`, `jbom inventory-search`)
3. **Generate BOM and CPL** for your fab (`jbom bom`, `jbom pos`)
4. **Customise** column names with a fab profile and electrical defaults with a defaults profile
5. **Share** profiles across your team with `JBOM_PROFILE_PATH`

For a complete reference:
- [README.man1.md](../README.man1.md) — all commands and flags
- [README.configuration.md](../README.configuration.md) — profile file formats and search path details
- [README.man5.md](../README.man5.md) — inventory file format
