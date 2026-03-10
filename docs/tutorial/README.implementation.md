# Tutorial 2: Your First BOM

## What you need

- A KiCad project with at least one `.kicad_sch` file
- jBOM installed (`pip install jbom`)

This tutorial uses a hypothetical project called `MyBoard`. Replace `MyBoard` with your actual project name throughout.

## Step 1: Extract an inventory template

Run jBOM against your project to extract every unique component it finds in your schematics:

```bash
jbom inventory MyBoard/ -o inventory.csv
```

jBOM walks your schematic hierarchy (including sub-sheets) and writes one row per unique Value + Package combination. Open the file and you will see something like:

```
IPN,Category,Keywords,Description,SMD,Value,Type,Tolerance,Voltage,...,LCSC,Priority
R-10K-0603,RES,,Resistor,SMD,10K,,,,,...,,
R-100R-0402,RES,,Resistor,SMD,100R,,,,,...,,
C-100NF-0603,CAP,,Capacitor,SMD,100nF,,,,,...,,
U-AMS1117-SOT223,IC,,LDO regulator,SMD,AMS1117-3.3,,,,,...,,
```

The IPN, Category, Value, Package, and SMD columns are pre-filled from your schematic. Everything else is blank for you to complete.

**Tip**: If you already have an inventory file from a previous project, merge the new components into it:
```bash
jbom inventory MyBoard/ --inventory existing.csv --filter-matches -o new_parts.csv
```
`--filter-matches` shows only components not already covered by your existing inventory.

## Step 2: Fill in part numbers

Open `inventory.csv` in a spreadsheet editor. For each part you want JLCPCB to source and solder:

1. Fill the **LCSC** column with the LCSC part number (e.g., `C25804`)
2. Set **Priority** to `1` (or a higher number for fallback alternatives)
3. Optionally fill **Manufacturer**, **MFGPN**, **Datasheet**

How to find LCSC part numbers:
- Search at [jlcpcb.com/parts](https://jlcpcb.com/parts) or [lcsc.com](https://lcsc.com)
- Use `jbom search` from the terminal, or `jbom inventory --supplier` for bulk auto-population (covered in Tutorial 3)
- Export your JLCPCB private parts library: *User Center → My Inventory → My Parts Lib → Export*

You do not need to fill in every row before generating a BOM. Components without a matching inventory entry will appear in the BOM with an empty part number. You can iterate.

## Step 3: Generate the BOM

```bash
jbom bom MyBoard/ --jlc --inventory inventory.csv
```

This produces `MyBoard.bom.csv` in your project directory, formatted for JLCPCB upload.

**What the flags mean:**
- `--jlc` — use the JLCPCB fabricator profile (column names, part-number field order)
- `--inventory inventory.csv` — the file you just edited

**Check the results:**
```bash
jbom bom MyBoard/ --jlc --inventory inventory.csv -o console
```
Displays the BOM as a table in the terminal. Add `-v` to see `Match_Quality` and `Notes` columns for every row.

If any components did not match, the exit code is `2` and jBOM prints a summary. Use `-v` to investigate:
```bash
jbom bom MyBoard/ --jlc --inventory inventory.csv -v -o console
```
Look at the `Notes` column — it tells you whether the mismatch is in Category, Value, or Package.

## Step 4: Generate the placement file (CPL)

```bash
jbom pos MyBoard/ --jlc
```

This produces `MyBoard.pos.csv`. You can pass the project directory, the `.kicad_pcb` file, or even the `.kicad_sch` file — jBOM finds the matching PCB automatically.

For JLCPCB SMT assembly, you typically want SMD components only:
```bash
jbom pos MyBoard/ --jlc --smd-only
```

Check the placement table:
```bash
jbom pos MyBoard/ --jlc --smd-only -o console
```

## Step 5: Upload to JLCPCB

You now have:
- `MyBoard.bom.csv` — upload as the BOM in the JLCPCB order form
- `MyBoard.pos.csv` — upload as the CPL (Component Placement List)

## Common adjustments

**Different fab house:**
```bash
jbom bom MyBoard/ --pcbway --inventory inventory.csv
jbom bom MyBoard/ --seeed  --inventory inventory.csv
```

**Multiple inventory sources** (e.g., project inventory + JLC private parts library):
```bash
jbom bom MyBoard/ --jlc --inventory project.csv --inventory jlc_library.xlsx
```

**Force overwrite** (if output file already exists):
```bash
jbom bom MyBoard/ --jlc --inventory inventory.csv -F
```

**Output to stdout** for piping or scripting:
```bash
jbom bom MyBoard/ --jlc --inventory inventory.csv -o -
```

**One row per reference** instead of aggregated:
```bash
jbom parts MyBoard/ --jlc --inventory inventory.csv
```

## What to do about unmatched parts

1. Run with `-v` to see match details
2. Check `Notes`: common reasons are wrong Category, value format mismatch ("10K" vs "10k"), or package mismatch ("0603" vs "0603_1608")
3. Add or fix the row in your inventory
4. Re-run — iterate until the exit code is `0`

## Next steps

- [Tutorial 3: Finding and Enriching Parts](README.integration.md) — use `jbom search`, `jbom inventory --supplier`, and `jbom audit --supplier` to find and validate supplier part numbers
- [Tutorial 4: Customising for Your Workflow](README.documentation.md) — custom column names, org-wide tolerances
