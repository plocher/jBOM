# Manufacturing Handoff

> **Note**: This tutorial is a hypothesis; the full end-to-end workflow has no gherkin scenario yet.
> The individual command invocations are scenario-backed, but the chained journeys described
> here have not been validated by a passing BDD feature. Treat walk-throughs as illustrative
> until an end-to-end scenario lands.

This tutorial covers taking a KiCad design from schematic and layout through to the
files a PCB fabricator needs: the Bill of Materials, Component Placement List (CPL), and
Gerber/drill archives.

---

## What fabricators need

Most PCB fabricators — JLC PCB, PCBWay, Seeed Studio, and others — require three artifact
types to assemble a board:

- **BOM** — maps reference designators to specific part numbers, suppliers, and quantities.
- **CPL / placement file** — lists every placed component's centroid coordinates, rotation,
  and assembly side. Pick-and-place machines consume this.
- **Gerber archive** — the layer stack (copper, silkscreen, solder mask, drill) for board
  fabrication.

jBOM produces all three. The recommended path is the one-shot `jbom fab` command, which
sequences all three steps into a single `production/` folder. Individual commands
(`jbom bom`, `jbom pos`, `jbom gerbers`) are available when you need fine-grained control
over one step at a time.

---

## One-shot fabrication with `jbom fab`

`jbom fab` is the fastest path from project to submission package. Point it at a KiCad
project directory (or any project file within it), specify your fabricator profile, and
optionally supply an inventory file to enrich the BOM with procurement data:

```bash
jbom fab board/ --jlc --inventory inventory.csv
```

This produces a `production/` folder (created inside the project directory by default)
containing:

- `production/jbom.csv` — the fabricator-formatted BOM
- `production/cpl.csv` — the component placement list
- `production/{title}_{revision}.zip` — Gerber and drill archive
- `production/backups/{title}_{revision}_{timestamp}.zip` — timestamped backup of the
  same Gerbers (created automatically on each run to protect prior revisions)

The `--jlc` flag selects JLC PCB's field set and column naming conventions. Other
fabricator profiles (`--pcbway`, `--seeed`, `--generic`) produce equivalent output
formatted to those fabricators' templates. The `--generic` profile is the default when
no fabricator flag is supplied.

Gerber generation requires `kicad-cli` to be installed and on your `PATH`. If it is absent
or the PCB file cannot be resolved, `jbom fab` still succeeds and writes the BOM and CPL;
the Gerber step is skipped with a diagnostic in the output.

### Dry run

To inspect what `jbom fab` would produce without writing any files:

```bash
jbom fab board/ --jlc --inventory inventory.csv --dry-run
```

A dry run generates BOM and CPL data in memory but performs no file I/O. Gerber generation
is also skipped in dry-run mode. Use this to verify field selection and inventory coverage
before committing to the output.

---

## Individual commands for fine-grained control

When you need to regenerate only one artifact — for example, updating the BOM after a
component swap without re-running Gerbers — use the individual commands.

### BOM generation

```bash
jbom bom board/ --inventory suppliers.csv --jlc -o production/jbom.csv
```

The `--inventory` flag enriches matched components with supplier and part-number data from
your inventory file. Without it, the BOM contains only the schematic-derived fields
(reference, value, footprint, quantity).

To overwrite an existing BOM file:

```bash
jbom bom board/ --inventory suppliers.csv --jlc --force -o production/jbom.csv
```

jBOM creates a timestamped backup of the previous file before overwriting, so using
`--force` is safe.

### Component placement (CPL)

```bash
jbom pos board/ --smd-only --jlc -o production/cpl.csv
```

`--smd-only` restricts output to SMD footprints, which is the typical requirement for
automated assembly. Through-hole components are excluded. Drop `--smd-only` if your
fabricator handles mixed assembly.

Rotation correction (compensating for the 90° or 180° offset that many IPC-standard
footprints have relative to assembly-machine convention) is applied automatically when a
`transformations.csv` file is present in the project directory. Pass `--apply-corrections`
explicitly if you want to ensure the correction step runs.

### Gerbers

```bash
jbom gerbers board/ --jlc -o gerbers/
```

Gerber generation delegates to `kicad-cli` under the hood. The fabricator profile
controls which layers are exported and how the output archive is named and structured.
If `kicad-cli` is not on your PATH, this command will fail with a clear error message.

---

## Submitting to the fabricator

After a successful `jbom fab` run, the `production/` folder contains everything a typical
PCBA order needs:

1. Upload `{title}_{revision}.zip` as your Gerber archive.
2. Upload `jbom.csv` as your Bill of Materials.
3. Upload `cpl.csv` as your Component Placement List.

Most fabricators have a web order flow that accepts these three files in sequence. Verify
that the column names in `jbom.csv` and `cpl.csv` match the fabricator's expected format
before submitting — the fabricator profile (`--jlc`, `--pcbway`, etc.) handles this
mapping for supported fabricators.

---

## Common issues

**Gerbers skipped** — `kicad-cli` is not installed or not on PATH. Install the KiCad
standalone CLI tools (available from kicad.org) and ensure `kicad-cli` is accessible
from your shell.

**BOM has unmatched components** — some schematic components did not match any inventory
row. The BOM will still be written but those rows will be missing supplier and part-number
fields. See the [inventory workflows tutorial](inventory-workflows.md) for how to extend
your inventory to cover new components.

**Rotation offsets look wrong** — if the CPL has assembly orientations that differ from
what you expect, check whether a `transformations.csv` correction file exists for your
footprint library. The [KiCad best practices reference](../reference/kicad-best-practices.md)
covers the footprint-to-assembly rotation convention.

**Backup archive growing large** — each `jbom fab` run appends a timestamped backup.
The `production/backups/` folder is intentional protection; prune old archives manually
once a revision is committed to version control.

---

## Related material

- [Inventory workflows tutorial](inventory-workflows.md) — building and enriching the
  inventory files that `--inventory` consumes.
- [KiCad best practices](../reference/kicad-best-practices.md) — property naming,
  footprint conventions, and the `~` don't-care sentinel.
- [Inventory data model](../design/inventory-data-model.md) — the IPN/Supplier/SPN
  structure and how Priority affects BOM enrichment.
