# Tutorial 1: Key Concepts

## The problem jBOM solves

KiCad gives you a schematic and a PCB layout. Before you can order boards and parts, you need two more files:

- A **Bill of Materials (BOM)** — what to buy and how many
- A **Placement file (CPL/POS)** — where each component sits on the board

The obvious approach is to put supplier part numbers directly into your KiCad symbols (e.g., `LCSC: C123456`). This works for a one-off board but breaks quickly:
- Out-of-stock parts require editing the schematic
- Different board revisions may use different sources
- Colleagues using a different fab house need different columns
- Sharing a design means sharing your sourcing decisions

jBOM separates **what the circuit needs** (schematic) from **where to get it** (inventory file). Your schematic stays generic (`10kΩ 0603 resistor`). The inventory file maps that to a specific part. jBOM joins them at generation time.

## The three pieces

### 1. Your KiCad project

You already have this. jBOM reads `.kicad_sch` and `.kicad_pcb` files. No schematic modifications required.

### 2. An inventory file

A CSV, Excel, or Numbers spreadsheet with one row per unique part. Required columns:

| Column   | Purpose |
|----------|---------|
| IPN      | Your internal part number (any unique string) |
| Category | Part type: `RES`, `CAP`, `IC`, `LED`, `CONN`, ... |
| Value    | Electrical value: `10K`, `100nF`, `AMS1117-3.3` |
| Package  | Footprint: `0603`, `SOT-23`, `QFN-32` |
| LCSC     | Supplier part number (JLCPCB/LCSC) |
| Priority | Integer. 1 = preferred, higher = fallback |

jBOM matches schematic components to inventory rows by comparing Category + Value + Package. When multiple rows match, the lowest Priority wins.

You do not need to fill every field before you start. Tutorial 2 shows how to bootstrap an inventory from your schematic.

### 3. Profiles

A profile is a small YAML file that configures one aspect of jBOM's behaviour. There are three kinds:

**Fabricator profiles** (`*.fab.yaml`) control BOM and CPL column names, part-number field priority, and any fab-specific requirements. The built-in profiles cover JLCPCB, PCBWay, and Seeed Studio. You select one with `--fabricator jlc` (or `--jlc`).

**Supplier profiles** (`*.supplier.yaml`) configure how jBOM connects to a distributor's API (base URL, rate limits, authentication). The built-in profile covers LCSC/JLCPCB.

**Defaults profiles** (`*.defaults.yaml`) set electrical defaults for the parametric search system — things like default tolerances, voltage ratings, and package power ratings. The built-in `generic` profile uses industry-standard values. Your organisation can override just what differs (e.g., set all resistor tolerances to 1% for aerospace work).

All three profile types use the same search path:
```
<project>/.jbom/      ← project-local (highest priority)
<repo-root>/.jbom/    ← monorepo shared
$JBOM_PROFILE_PATH    ← org library (colon-separated dirs)
~/.jbom/              ← personal overrides
<platform system dir> ← IT-managed org config
<jbom package>        ← built-in factory defaults (always present)
```

You never need to touch a profile to get started. The built-in profiles work out of the box.

## The basic workflow

```
KiCad project
      │
      v
  jbom inventory   ←─ extracts component list from schematic
      │
      v
  Edit inventory   ←─ add LCSC part numbers, set priorities
      │
      v
  jbom bom         ←─ matches inventory to schematic, outputs BOM CSV
  jbom pos         ←─ reads PCB file, outputs placement CSV
```

The BOM and placement files are what you upload to JLCPCB (or your fab of choice).

## What about unmatched components?

When jBOM generates a BOM it tells you about every component that did **not** match your inventory. Run with `-v` to see match quality scores and notes. Unmatched components appear in the BOM with an empty part number — the BOM is still written, so you can iterate.

Exit code `2` (rather than `0`) means "BOM written, but some components are unmatched". Exit code `1` means a hard error.

## Next steps

- [Tutorial 2: Your First BOM](README.implementation.md) — hands-on walkthrough of the core workflow
- [Tutorial 3: Finding and Enriching Parts](README.integration.md) — fill your inventory using `jbom search`, `jbom inventory --supplier`, and `jbom audit --supplier`
- [Tutorial 4: Customising for Your Workflow](README.documentation.md) — create custom fab and defaults profiles
