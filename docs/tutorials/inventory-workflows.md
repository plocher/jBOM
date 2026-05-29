# Inventory Management Workflows

> **Note**: This tutorial is a hypothesis; the full end-to-end workflow has no gherkin scenario yet.
> The individual command invocations are scenario-backed, but the chained journeys described
> here have not been validated by a passing BDD feature. Treat walk-throughs as illustrative
> until an end-to-end scenario lands.

This tutorial guides you through common inventory management patterns in jBOM: building an
inventory from scratch, enhancing it with supplier data, keeping multiple projects in sync,
promoting supplier-export CSVs into canonical inventory shape, and incrementally adding new
components without disrupting existing records.

---

## Why inventory matters

jBOM separates schematic components from their real-world procurement identities. A schematic
knows that R3 is a 10k 0603 resistor; the inventory knows which specific part number from
which supplier to buy, and at what priority when alternatives exist. Keeping that separation
clean means your schematic stays supplier-neutral, and your inventory becomes a reusable asset
across projects.

See the [inventory data model design doc](../design/inventory-data-model.md) for the rationale
behind the IPN/Supplier/SPN structure that these workflows produce and consume.

---

## Basic inventory creation

The simplest starting point is generating an inventory from a KiCad project schematic:

```bash
jbom inventory myproject.kicad_sch -o components.csv
```

This reads every component in the schematic and writes one row per aggregated component
group. The resulting CSV is your starting canvas: at minimum it will contain `IPN`,
`Category`, `Value`, and `Package` columns populated from the schematic properties.

After this first pass, open `components.csv` in your spreadsheet tool and fill in the
procurement columns — `Supplier`, `SPN`, `MPN`, `Cost` — for each part. Those additions
are what make the file useful as an inventory source in subsequent runs.

If your project uses hierarchical sheets, jBOM follows the hierarchy automatically.
You do not need to specify individual sheet files.

---

## Promote a supplier export into canonical inventory shape

When a supplier provides a CSV export, use `jbom promote` to create a deterministic
inventory scaffold before curation:

```bash
jbom promote examples/JLCPCB-INVENTORY.csv --supplier lcsc -o examples/JLCPCB-INVENTORY.promoted.csv
```

The promoted output preserves source columns and adds `SupplierContext`, so downstream
inventory/BOM workflows have an explicit supplier-context marker.

`--jlc` is shorthand for `--supplier lcsc`:

```bash
jbom promote examples/JLCPCB-INVENTORY.csv --jlc -o promoted.csv
```

API key parsing is shape-compatible with `jbom inventory`:

```bash
# single unscoped key
jbom promote examples/JLCPCB-INVENTORY.csv --supplier lcsc --api-key KEY123 -o -

# supplier-scoped key
jbom promote examples/JLCPCB-INVENTORY.csv --supplier lcsc --api-key lcsc=KEY123 -o -
```

Design intent: `promote` and `inventory` share the same supplier-selection and
supplier-key mapping pattern, so promotion and enrichment workflows are modeled with
the same CLI shape.

---

## Inventory enhancement with existing data

Once you have an inventory file (from a previous project, a team shared library, or the
initial creation step above), you can use it to enrich the BOM for any project:

```bash
jbom bom project.kicad_sch --inventory existing_stock.csv -o enhanced_bom.csv
```

jBOM matches each schematic component against the inventory using a scored matching
algorithm. Components that match an inventory row are enhanced with the procurement
data from that row — supplier, part number, cost, and any other columns your inventory
carries.

To see which components matched and which did not, pass `--verbose`:

```bash
jbom bom project.kicad_sch --inventory existing_stock.csv --verbose -o enhanced_bom.csv
```

The verbose output shows each component's match score, the inventory item it resolved to,
and any warnings about ambiguous or low-confidence matches.

To identify components that are not covered by your existing inventory — the ones you
need to source before building — use `--filter-matches` on the inventory command:

```bash
jbom inventory project.kicad_sch --inventory existing_stock.csv --filter-matches
```

This writes (or displays) only the components that did *not* match any inventory item,
giving you a focused list of what still needs to be sourced.

---

## Multi-source inventory management

### Priority within a single inventory file

When an inventory file contains multiple rows for the same IPN (representing supplier
alternatives), jBOM's matcher uses the `Priority` field to rank them. Lower `Priority`
values are preferred. For passive components (resistors, capacitors, inductors) the sort
order is `(Priority asc, score desc)`; for non-passives it is `(score desc, Priority asc)`.

```csv
IPN,Type,Value,Package,Supplier,SPN,Cost,Priority
IPN-10k-0603-RES,resistor,10k,0603,Digikey,311-10KHRCT-ND,$0.10,1
IPN-10k-0603-RES,resistor,10k,0603,Mouser,CRCW060310K0FKEA-ND,$0.12,2
```

In this example the Digikey row (Priority 1) is preferred; the Mouser row (Priority 2)
serves as a backup. jBOM will select the Digikey row when both match, unless a fabricator
preference tier causes the matcher to prefer a different source.

### Multiple inventory files (current limitation)

Supplying multiple `--inventory` flags to `jbom bom` is supported at the CLI level, but
the BOM workflow currently uses only the first file. A diagnostic is emitted at verbose
level when additional files are provided:

```bash
# Second and third files are accepted but currently ignored by the BOM workflow.
# A verbose run will emit: "Note: Using primary inventory file …, multi-file enhancement coming soon"
jbom bom project.kicad_sch \
  --inventory primary_stock.csv \
  --inventory backup_suppliers.csv \
  --verbose \
  -o bom.csv
```

Until multi-file inventory merging lands, the recommended approach for combining sources is
to merge inventory CSVs into a single file manually (or with a spreadsheet tool), keeping
the `Priority` column to express the inter-supplier ranking within that unified file.

---

## Incremental inventory updates

As you add new projects, you want to extend your master inventory with new components
without duplicating entries that already exist.

**Step 1** — generate the new project's raw inventory:

```bash
jbom inventory newproject.kicad_sch -o newproject_raw.csv
```

**Step 2** — filter to components not already in your master:

```bash
jbom inventory newproject.kicad_sch \
  --inventory master_inventory.csv \
  --filter-matches \
  -o additions_needed.csv
```

`additions_needed.csv` now contains only the components that `master_inventory.csv` does
not cover. Fill in their supplier and procurement details, then append those rows to
`master_inventory.csv` (or open both in a spreadsheet and copy-paste the additions block).

**Step 3** — verify the merge by running the BOM for the new project against the updated
master:

```bash
jbom bom newproject.kicad_sch --inventory master_inventory.csv --verbose -o newproject_bom.csv
```

Unmatched components in the verbose output indicate rows that still need supplier data in
the master inventory.

### Multi-project inventory growth

To build a master inventory from several existing projects in sequence:

```bash
# Seed with the first project
jbom inventory projectA.kicad_sch -o master_inventory.csv

# For each subsequent project, find only its new additions
jbom inventory projectB.kicad_sch \
  --inventory master_inventory.csv \
  --filter-matches \
  -o projectB_additions.csv

# Fill supplier data in projectB_additions.csv, then merge manually
# into master_inventory.csv before moving to projectC.
```

The `--filter-matches` flag is what keeps each increment clean: it ensures you only
add rows for components the existing master does not already cover.

---

## What to do with unmatched components

When the BOM run's verbose output shows components with no match, you have three options:

1. **Add them to your inventory** — the most durable fix. Follow the incremental update
   workflow above.
2. **Accept the gap** — if the component is a one-off, you can leave it without an
   inventory entry. The BOM will include it with schematic-only data and no procurement fields.
3. **Use `jbom audit`** — the audit command provides a structured view of coverage gaps
   and can help prioritize which missing components matter most for a given build.

---

## Related material

- [Inventory data model](../design/inventory-data-model.md) — why the IPN/Supplier/SPN
  shape is designed the way it is, and what the `Priority` field means in context.
- [Inventory field semantics](../design/inventory-field-semantics.md) — the two-state
  blank/explicit model, `~` handling, and write-back rules for `jbom annotate`.
- [Manufacturing handoff tutorial](manufacturing-handoff.md) — how to go from an
  enriched BOM to a fabricator submission package.
