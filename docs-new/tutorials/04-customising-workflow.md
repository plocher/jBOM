# Tutorial 4: Customising for Your Workflow

> **Note**: This tutorial is a hypothesis; the full end-to-end workflow has no
> gherkin scenario yet. Steps reflect current code behaviour. Where the
> original source document referenced unimplemented CLI flags or non-existent
> config keys those have been corrected or marked as future work (see F-012 in
> the audit, resolved in this rewrite).

The built-in fabricator profiles (`jlc`, `pcbway`, `seeed`) and the `generic`
defaults work well for most projects. This tutorial shows you how to go beyond
them:

- Create a custom fabricator profile with your own BOM column names
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

Any profile file placed here takes precedence over the built-in profiles for
this project.

### Step A2: Create a custom fabricator profile

jBOM's unified profile format uses `.jbom.yaml` files with named stanzas.
Create `MyBoard/.jbom/acmefab.jbom.yaml`:

```yaml
extends: jlc       # inherit everything from the built-in JLC profile

id: acmefab        # becomes the --acmefab CLI flag

fab:
  name: "Acme Fab"
  description: "Internal Acme fabrication format"

  # Override only the BOM columns
  bom_columns:
    "Ref Des":    "reference"
    "Qty":        "jbom:quantity"
    "Part Value": "value"
    "Package":    "inv:package"
    "LCSC":       "jbom:fabricator_part_number"
    "Internal PN": "mpn"    # extra column
```

`extends: jlc` performs a deep merge: jBOM loads the built-in `jlc.jbom.yaml`
first, then overlays your file on top. You inherit the part-number priority
list, PCB assembly settings, supplier configuration, and everything else from
the JLC profile — you only write what changes.

`extends:` is the canonical inheritance key for all profile types (fabricator,
supplier, defaults). It is a top-level key, not nested inside a stanza.

### Step A3: Use it

```bash
jbom bom MyBoard/ --acmefab --inventory inventory.csv
```

jBOM discovers `acmefab.jbom.yaml` in `.jbom/` automatically. No
configuration file needed.

### Step A4: Make it permanent for your personal setup

If you use the same fab profile across multiple projects, put it in your home
directory instead:

```bash
mkdir -p ~/.jbom
cp MyBoard/.jbom/acmefab.jbom.yaml ~/.jbom/
```

Now `--acmefab` works from any project directory.

### Fabricator profile structure reference

A fabricator profile file contains a top-level `fab:` stanza. The `extends:`
key (if present) sits outside any stanza:

```yaml
extends: "jlc"       # optional: inherit from another profile

id: "cli-id"         # creates --cli-id flag; applies to all stanzas by default

fab:
  name: "Display Name"
  description: "..."

  pcb_manufacturing:
    website: "https://..."
    gerbers: "kicad"

  suppliers:          # ordered supplier IDs (first = preferred)
    - lcsc
    - mouser

  part_number:
    header: "fabricator_part_number"

  bom_columns:        # BOM header: jBOM internal field expression
    "Designator": "reference"
    "Qty":        "jbom:quantity"
    ...

  pos_columns:        # CPL header: jBOM internal field expression
    "Designator": "reference"
    "Mid X":      "x"
    "Mid Y":      "y"
    ...
```

For a complete example, look at the built-in `jlc.jbom.yaml`:

```bash
python -c "import jbom, pathlib; print(pathlib.Path(jbom.__file__).parent / 'config' / 'jlc.jbom.yaml')"
```

---

## Part B: Defaults profiles

### Why customise a defaults profile?

The `generic` defaults profile sets conservative, widely-applicable values:
- Resistor tolerance: 5%
- Capacitor dielectric: X7R
- Package voltage/power ratings: consumer-grade

If your organisation designs to different standards — aerospace, automotive,
high-precision — you should not have to specify these overrides on every single
resistor in every schematic. A defaults profile captures your design culture
in one place.

### Step B1: See what the generic profile contains

The built-in `generic.jbom.yaml` holds a `defaults:` stanza with sections
like:

```yaml
defaults:
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

Inspect it with:

```bash
python -c "import jbom, pathlib; print(pathlib.Path(jbom.__file__).parent / 'config' / 'generic.jbom.yaml')" | xargs cat
```

### Step B2: Override factory defaults for a project

To override the generic defaults for a single project, place a
`generic.jbom.yaml` (with a `defaults:` stanza) in the project's `.jbom/`
directory. jBOM resolves the profile search path highest-to-lowest priority, so
your project-local file takes precedence over the built-in one.

Create `MyBoard/.jbom/generic.jbom.yaml`:

```yaml
extends: generic   # inherit everything from the built-in generic profile

defaults:
  domain_defaults:
    resistor:
      tolerance: "1%"   # override: 1% for all resistors
    capacitor:
      tolerance: "5%"   # override: tighter cap tolerance
      dielectric: "C0G" # override: C0G/NP0 for precision
```

`extends: generic` performs a **deep merge**: every section you include
overlays the parent; anything you omit stays as the parent value. You only
write what changes.

List sections replace (not merge): if you override `package_power`, your list
replaces the entire parent list rather than merging into it.

### Step B3: Activate custom defaults

jBOM loads the defaults profile named "generic" by default for all parametric
search and enrichment operations (the active profile name is controlled
internally; see `src/jbom/config/defaults.py`). Placing your overrides in
`MyBoard/.jbom/generic.jbom.yaml` is the recommended way to activate
project-local custom defaults without any extra flags.

For named profiles other than "generic" (e.g., `precision.jbom.yaml`), an
explicit `--defaults <name>` CLI flag is **planned for a future release** but
not yet implemented. Until it lands, use the `generic.jbom.yaml` naming
convention in your search path directory to activate defaults overrides.

### Step B4: Share profiles across a team

For a team or organisation, you want everyone to use the same defaults without
checking profiles into every project repo. Use `JBOM_PROFILE_PATH`:

```bash
# Set in your shell profile (or in a CI environment variable)
export JBOM_PROFILE_PATH=/shared/jbom-profiles
```

Put your profiles in that directory:

```
/shared/jbom-profiles/
├── generic.jbom.yaml          # org-wide defaults override (1% resistors, C0G caps)
└── acmefab.jbom.yaml          # house fab profile
```

All engineers with `JBOM_PROFILE_PATH` pointing to the shared directory
automatically get these profiles. No file copying, no checking profiles into
individual repos.

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

To see which directories jBOM would search for a profile:

```python
from jbom.config.profile_search import profile_search_dirs
for d in profile_search_dirs():
    print(d)
```

---

## Summary

You now have the full jBOM toolkit:

1. **Generate inventory** from your schematic (`jbom inventory`)
2. **Enrich it** with part numbers (`jbom search`, `jbom inventory --supplier`)
3. **Audit supplier PNs** for staleness (`jbom audit inventory.csv --supplier`)
4. **Generate BOM and CPL** for your fab (`jbom bom`, `jbom pos`)
5. **Customise** column names with a fab profile and electrical defaults with a
   defaults profile
6. **Share** profiles across your team with `JBOM_PROFILE_PATH`

For a complete reference:
- [`reference/cli.md`](../reference/cli.md) — all commands and flags (generated; see issue #269)
- [`design/configuration-semantics.md`](../design/configuration-semantics.md) — profile file formats and search path details
- [ADR 0008](../architecture/adr/0008-unified-jbom-config-schema.md) — the unified `*.jbom.yaml` design decision
